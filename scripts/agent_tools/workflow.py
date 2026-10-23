"""Durable continuation of the current project's analysis; agent KB is the workspace."""

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import uuid

from .analysis import analysis_issues, publish_owned, SECTIONS
from .diagnostics import problem
from .evidence import evidence_issues
from .research import inside, json_data
from .storage import locked, replace_bytes

STAGES = ('capture', 'identity_init', 'research', 'analysis', 'review', 'kb_review', 'finalize')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hashes(root, paths):
    result = {}
    for path in paths:
        target = inside(root, path)
        if not target.is_file():
            raise FileNotFoundError(f'Missing stage artifact: {path}')
        result[target.relative_to(Path(root).resolve()).as_posix()] = file_hash(target)
    return result


def kb_paths(root):
    kb = Path(root) / 'ꘖ/KB'
    # Progress is a generated navigation view; facts and analysis are reviewed separately.
    return [p.relative_to(root).as_posix() for p in sorted(kb.rglob('*'))
            if p.is_file() and (p.suffix.lower() in ('.md', '.json') or p.name == '.md')
            and p.name != 'Progress.md' and not p.is_relative_to(kb / 'Evidence')]


def evidence_paths(root):
    """Pin primary evidence and manual inputs; reviewer reports are separate receipts."""
    root = Path(root).resolve()
    evidence = root / 'ꘖ/KB/Evidence'
    dirs = [evidence, root / 'KB']
    if (root / 'source').is_dir():
        dirs.append(root / 'source')
    return sorted({p.relative_to(root).as_posix() for directory in dirs
                   for p in directory.rglob('*') if p.is_file() and not p.is_relative_to(evidence / 'Reviews')})


def question_contract_issues(root, question):
    from .experiments import requirement_issues, result_issues
    requirements = question.get('requirements')
    issues = requirement_issues(requirements)
    results = question.get('requirement_results', [])
    if not isinstance(results, list):
        return [*issues, 'Structured requirement_results list is required']
    expected = {r['id']: r for r in requirements if isinstance(r, dict) and isinstance(r.get('id'), str)} if isinstance(requirements, list) else {}
    seen = set()
    for result in results:
        ident = result.get('requirement_id') if isinstance(result, dict) else None
        if ident not in expected or ident in seen:
            issues.append('Each declared requirement must have one structured result')
            continue
        seen.add(ident)
        issues.extend(result_issues(root, expected[ident], result))
    if seen != set(expected):
        issues.append('Research requirement results are incomplete')
    if any(r.get('status') in ('unverified', 'unavailable') for r in results if isinstance(r, dict)) and not question.get('gap'):
        issues.append('Unavailable/unverified requirements require an explicit question gap')
    return issues


def questions_current(root, state):
    return all(q['status'] in ('complete', 'gap')
               and receipt_current(root, {'inputs': q['inputs'], 'outputs': q['results']})
               and not question_contract_issues(root, q)
               for q in state['questions'].values())

def state_path(root):
    return Path(root).resolve() / 'ꘖ/data/workflow.json'


def load(root):
    root = Path(root).resolve()
    pj = root / 'ꘖ/project.json'
    if not pj.is_file():
        raise ValueError('Provide the existing project root from this chat; no project is selected or initialized implicitly')
    project = json.loads(pj.read_text(encoding='utf-8'))
    path = state_path(root)
    if path.exists():
        state = json.loads(path.read_text(encoding='utf-8'))
        if state.get('schema_version') != 1 or state.get('project_root') != str(root) or state.get('job_id') != project['job_id']:
            raise ValueError('Workflow identity/version mismatch; preserve the file for explicit migration')
        return state
    return {'schema_version': 1, 'project_root': str(root), 'job_id': project['job_id'],
            'stages': {}, 'questions': {}, 'reviews': [], 'events': [], 'requests': [], 'legacy': True}


def receipt_current(root, receipt):
    return (all(inside(root, path).is_file() and file_hash(inside(root, path)) == digest
               for group in ('inputs', 'outputs') for path, digest in receipt.get(group, {}).items())
            and ('kb_inputs' not in receipt or receipt['kb_inputs'] == hashes(root, kb_paths(Path(root))))
            and ('evidence_inputs' not in receipt or receipt['evidence_inputs'] == hashes(root, evidence_paths(root))))


def registration_status(root):
    from .runtime import settings, platform_name, profile_name
    root = Path(root).resolve()
    config, platform = settings(), platform_name()
    path = root / 'ꘖ/data/registrations.json'
    required = path.exists() or root.is_relative_to(Path(config['workspace_root']) / config['daily_root'])
    receipt = json.loads(path.read_text(encoding='utf-8')).get(platform) if path.exists() else None
    complete = not required
    if receipt:
        complete = receipt.get('complete', bool(receipt.get('project_id') and receipt.get('folder_id')))
        if receipt.get('profiles'):
            complete = bool(receipt['profiles'].get(profile_name(), {}).get('ready'))
    return {'platform': platform, 'required': required, 'complete': complete, 'receipt': receipt}


def stage_statuses(root, state):
    statuses, dependency_ok = {}, True
    for stage in STAGES:
        receipt = state['stages'].get(stage)
        current = bool(receipt and receipt.get('status') == 'complete' and receipt_current(root, receipt))
        if stage == 'identity_init':
            current = current and registration_status(root)['complete']
        if stage == 'research' and receipt:
            current = current and questions_current(root, state) and receipt.get('research_questions') == state['questions']
        if stage in ('review', 'kb_review', 'finalize') and current:
            from .review import approval_current
            current = approval_current(root, state, receipt.get('review_approval'))
        if stage == 'finalize':
            covered = receipt.get('request_ids') if receipt else None
            current = current and (covered == [request['id'] for request in state['requests']] if covered is not None
                                   else all(request.get('response_prepared') for request in state['requests']))
        statuses[stage] = 'complete' if current and dependency_ok else ('stale' if receipt else 'pending')
        dependency_ok = dependency_ok and current
    return statuses


def status(root):
    root = Path(root).resolve(); state = load(root)
    statuses = stage_statuses(root, state)
    existing = {name: (root / 'ꘖ/KB' / name).is_file() for name in ('Analysis.json', 'Analysis.md', 'Progress.md')}
    proposals = [{'path': inside(root, path).relative_to(root).as_posix(), 'sha256': file_hash(inside(root, path))}
                 for path in sorted((root / 'result').rglob('*.md'))
                 if path.is_file() and path.name in ('draft.md', 'final.md', 'draft.prev.md')]
    checkpoint = root / 'ꘖ/data/continuation.md'
    return {'project': str(root), 'job_id': state['job_id'], 'legacy': state['legacy'], 'stages': statuses,
            'scope': 'initial_analysis', 'proposal_artifacts': proposals,
            'continuation': {'file': 'ꘖ/data/continuation.md', 'exists': checkpoint.is_file()},
            'next_stage': next((s for s in STAGES if statuses[s] != 'complete'), None),
            'agent_kb': str(root / 'ꘖ/KB'), 'existing_drafts': existing,
            'kb_hashes': hashes(root, kb_paths(root)),
            'questions': list(state['questions'].values()),
            'registration': registration_status(root),
            'detail': 'Stages track saved analysis. Every new analytical reply requires current request/answer-bound approval. Continue the same filesystem project in either UI using agent KB, journal and actual proposal files; Context.md is an external export.'}


def publish_progress(root, state):
    from .links import markdown_link
    statuses = stage_statuses(root, state)
    lines = ['# Ход анализа', '', 'Служебная навигация агентской KB; статусы не доказывают истинность выводов.',
             f'Вакансия: {state["job_id"]}.', '', '## Этапы']
    lines += [f'- {stage}: {statuses[stage]}.' for stage in STAGES if stage != 'finalize']
    lines += ['Завершение и квитанцию внешнего экспорта проверяй командой status.', '']
    if (Path(root) / 'ꘖ/data/continuation.md').is_file():
        lines += ['Текущее поручение после анализа: [состояние продолжения](../data/continuation.md).', '']
    lines += ['', '## Вопросы']
    for question in state['questions'].values():
        lines += [f'- {question["id"]}: {question["question"]}',
                  f'  Статус: {question["status"]}; исполнитель: {question.get("owner") or "не назначен"}.',
                  f'  Критерий окончания: {question["done_when"]}.']
        if question.get('gap'):
            lines.append('  Неизвестное: ' + question['gap'])
        for ref in question.get('results', {}):
            target = inside(root, ref)
            import os
            relative = Path(os.path.relpath(target, Path(root) / 'ꘖ/KB')).as_posix()
            lines.append('  ' + markdown_link('Сохранённый результат', relative))
    lines += ['', '## Профильные модули']
    lines += ['- ' + markdown_link(p.name, p.name) for p in sorted((Path(root) / 'ꘖ/KB').glob('*.md')) if p.name != 'Progress.md']
    lines += ['', 'Перед новым исследованием проверь обзор и профильные модули KB.',
              'Исправления распространяются на связанные утверждения и документы; непроверенное отмечается явно.',
              'Context.md предназначен для передачи внешнему агенту, а не для внутренней работы.', '']
    return publish_owned(Path(root) / 'ꘖ/KB/Progress.md', '\n'.join(lines), source=state_path(root), history=False)


def update(root, event, change):
    root = Path(root).resolve()
    with locked(root / 'ꘖ/data/workflow.lock'):
        state = load(root)
        change(state)
        state['events'].append({'id': uuid.uuid4().hex, 'time': now(), **event})
        replace_bytes(state_path(root), json_data(state))
        progress = publish_progress(root, state)
    return {'workflow': str(state_path(root)), 'progress': progress, **status(root)}


def resume(root, reason, request=None):
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('Record why the current analysis is being continued')
    if request is not None and (not isinstance(request, str) or not request.strip()):
        raise ValueError('Continuation request must preserve exact nonempty user text')
    def change(state):
        state['legacy'] = False
        if request is not None:
            state['requests'].append({'id': uuid.uuid4().hex, 'time': now(), 'text': request})
        # Validate only the saved capture mechanically. Analysis/review are not inferred from file presence.
        pj = json.loads((Path(root) / 'ꘖ/project.json').read_text(encoding='utf-8'))
        source = inside(root, pj['snapshot'])
        data = json.loads(source.read_text(encoding='utf-8'))
        from .upwork_data import normalize_job_id
        if normalize_job_id(data.get('job_id')) != pj['job_id'] or not data.get('title') or not data.get('description'):
            raise ValueError('Existing capture does not match this project')
        if re.fullmatch(r'[a-f0-9]{64}', source.stem) and file_hash(source) != source.stem:
            raise ValueError('Immutable capture hash differs')
        state['stages']['capture'] = {'status': 'complete', 'time': now(), 'inputs': {}, 'outputs': hashes(root, [pj['snapshot']]), 'method': 'verified saved capture'}
    return update(root, {'action': 'resume', 'reason': reason}, change)


def adopt_requests(root, conversation_id):
    from .metrics import native_requests
    from .journal import answer_groups
    requests = native_requests(root, conversation_id)
    saved_answers = {}
    for group in answer_groups(Path(root) / 'ꙮ/1 - Анализ'):
        for ident in group.get('request_ids') or []:
            saved_answers[ident] = {'turn': group['turn'], 'steps': group['steps'], 'sha256': group['response_sha256']}
    def change(state):
        recorded = {x['id']: x for x in state['requests'] if x.get('native_conversation_id')}
        # Native exact inputs replace unverified manual continuation copies, preserving native IDs/statuses.
        incoming = {x['id'] for x in requests}
        exact_texts = {x['text'] for x in requests}
        state['requests'] = [x for x in state['requests'] if x['id'] not in incoming
                             and (x.get('native_conversation_id') or x['text'] not in exact_texts)]
        for request in requests:
            prepared = saved_answers.get(request['id']) or recorded.get(request['id'], {}).get('response_prepared')
            state['requests'].append({**request, **({'response_prepared': prepared} if prepared else {})})
    return update(root, {'action': 'adopt_requests', 'conversation_id': conversation_id}, change)


def doc4_sentence_issues(text):
    """Detect DOC-4 single-sentence-per-line violations in bullet items and Russian prose."""
    issues = []
    in_fence = False
    fence_marker = ''
    for lineno, raw_line in enumerate((text or '').splitlines(), 1):
        stripped = raw_line.strip()
        m_fence = re.match(r'^(`{3,}|~{3,})', stripped)
        if m_fence:
            marker = m_fence.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif stripped.startswith(fence_marker * 3):
                in_fence = False
                fence_marker = ''
            continue
        if in_fence or not stripped or stripped.startswith(('#', '>', '|')):
            continue
        cleaned = re.sub(r'`[^`]*`', 'code', stripped)
        cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
        cleaned = re.sub(r'«[^»]*»', '«цитата»', cleaned)
        cleaned = re.sub(
            r'\b(?:г|гг|т\.д|т\.п|см|им|др|пр|ул|д|кв|рис|табл|ст|п|ч|руб|тыс|млн|млрд|англ|рус|напр|ок|vs|Mr|Mrs|Ms|Dr|St|Inc|Ltd|Co|Jr|Sr|e\.g|i\.e)\.',
            'abbr',
            cleaned,
        )
        is_bold_bullet = bool(re.match(r'^[-*]\s+\*\*[^*]+\*\*', stripped))
        if is_bold_bullet and re.search(r'[A-Za-zА-Яа-яЁё]{3,}[.!?]\s+[A-ZА-ЯЁ][a-zа-яё]{2,}\s+\S+.*[.!?]\s*$', cleaned):
            issues.append(f'DOC-4 violation on line {lineno}: multiple sentences on a single bullet line (place each sentence on its own line or use sub-bullets)')
        elif re.search(r'(?:[А-Яа-яЁёA-Za-z0-9«»"(),:-]+\s+){3,}[А-Яа-яЁё]{3,}[.!?]\s+[А-ЯЁ][а-яё]{2,}\s+[А-Яа-яЁёA-Za-z0-9]+\s+[А-Яа-яЁёA-Za-z0-9]+', cleaned):
            issues.append(f'DOC-4 violation on line {lineno}: multiple sentences on a single line (place each sentence on its own line)')
    return issues


def record_current_answer(root, response, *, journal_directory=None):
    from .journal import record_answer
    from .links import readable_link_issues
    issues = readable_link_issues(response)
    if issues:
        raise ValueError('\n'.join(issues))
    analysis_path = Path(root).resolve() / 'ꘖ/KB/Analysis.json'
    if analysis_path.is_file():
        try:
            analysis_val = json.loads(analysis_path.read_text(encoding='utf-8-sig'))
        except Exception:
            analysis_val = None
        if isinstance(analysis_val, dict) and analysis_val.get('red_flags') == [] and re.search(r'(?im)^\s*#{1,6}\s+Red Flags\b', response):
            raise ValueError('Do not include a Red Flags heading in the response when Analysis.json red_flags is empty (INIT-5)')
    state = load(root)
    from .review import authorize
    approval = authorize(root, state, response=response)
    unanswered = [x for x in state['requests'] if not x.get('response_prepared')]
    from .text_workflow import gate_requests
    gate_requests([root], [x['text'] for x in unanswered], response)
    if not unanswered:
        raise ValueError('No unrecorded current requests; import exact native inputs or save the current request first')
    turn = unanswered[-1]['id']
    # Native IDs may contain colons, which are invalid in Windows group filenames.
    # Keep the original IDs in the receipt and use a stable filename-safe turn key.
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', turn):
        turn = 'native-' + hashlib.sha256(turn.encode('utf-8')).hexdigest()
    directory = (Path(root).resolve() / (journal_directory or 'ꙮ/1 - Анализ')).resolve()
    steps = record_answer(directory, [x['text'] for x in unanswered], response, turn, [x['id'] for x in unanswered])
    ids = {x['id'] for x in unanswered}
    def change(state):
        authorize(root, state, response=response, package_path=approval['package'])
        for request in state['requests']:
            if request['id'] in ids:
                request['response_prepared'] = {'turn': turn, 'steps': steps, 'journal': str(directory),
                                                'sha256': hashlib.sha256(response.encode()).hexdigest(), 'review_approval': approval}
    result = update(root, {'action': 'reply_prepared', 'turn': turn, 'steps': steps}, change)
    return {**result, 'journal_steps': steps, 'delivery_verified': False}


def add_question(root, ident, question, impact, done_when, inputs, outputs, *, requirements=None):
    if not re.fullmatch(r'[A-Z][A-Z0-9-]*', ident) or not all(isinstance(x, str) and x.strip() for x in (question, impact, done_when)):
        raise ValueError('Question needs a stable ID, question, impact and completion criterion')
    if not inputs:
        raise ValueError('Declare at least the saved capture or relevant KB module as question input')
    from .experiments import requirement_issues
    issues = requirement_issues(requirements)
    if issues:
        raise ValueError('\n'.join(issues))
    input_hashes = hashes(root, inputs)
    permitted = [inside(root, path).relative_to(Path(root).resolve()).as_posix() for path in outputs]
    if not permitted or any(not p.startswith('ꘖ/') or p.startswith('ꘖ/data/workflow') for p in permitted):
        raise ValueError('Declare exact project-owned outputs under ꘖ; not workflow state')
    def change(state):
        if ident in state['questions']:
            raise ValueError('Question already exists; use its saved inputs/results')
        state['questions'][ident] = {'id': ident, 'question': question, 'impact': impact, 'done_when': done_when,
            'inputs': input_hashes, 'allowed_outputs': permitted, 'status': 'pending', 'owner': None, 'searches': [], 'results': {}, 'requirements': requirements, 'requirement_results': []}
    return update(root, {'action': 'question', 'question_id': ident}, change)


def claim_question(root, ident, owner):
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError('Owner must be an observed session/subagent ID')
    def change(state):
        q = state['questions'][ident]
        if q['status'] in ('complete', 'gap'):
            raise ValueError('Use the existing result; reopening requires a new documented question')
        if q['owner'] and q['owner'] != owner:
            raise ValueError('Question already has an owner; inspect native subagent status before explicit handoff')
        for other in state['questions'].values():
            if other['id'] != ident and other['owner'] and other['status'] == 'running' and set(other['allowed_outputs']) & set(q['allowed_outputs']):
                raise ValueError('Another active question owns the same output file')
        q.update(owner=owner, status='running')
    return update(root, {'action': 'claim_question', 'question_id': ident, 'owner': owner}, change)


def handoff(root, ident, previous_owner, new_owner, reason):
    if not all(isinstance(s, str) and s.strip() for s in (previous_owner, new_owner, reason)):
        raise ValueError('Explicit previous owner, new owner and observed stopping reason required')
    def change(state):
        q = state['questions'][ident]
        if q['owner'] != previous_owner or q['status'] != 'running':
            raise ValueError('Task owner/status changed; refresh native progress before handoff')
        q.update(owner=new_owner, handoff_reason=reason)
    return update(root, {'action': 'handoff', 'question_id': ident, 'reason': reason}, change)


def record_search(root, ident, owner, query, useful=False, method_change=None):
    if not isinstance(query, str) or not query.strip():
        raise ValueError('Search query required')
    def change(state):
        q = state['questions'][ident]
        if q['owner'] != owner or q['status'] != 'running':
            raise ValueError('Only current task owner can record searches')
        recent = []
        for attempt in reversed(q['searches']):
            recent.append(attempt)
            if attempt.get('method_change') or len(recent) == 3:
                break
        if len(recent) == 3 and all(not x['useful'] for x in recent) and not method_change:
            raise ValueError('Three unsuccessful searches: return a gap or document a different method before continuing')
        q['searches'].append({'query': ' '.join(query.casefold().split()), 'useful': bool(useful), 'method_change': method_change, 'time': now()})
    return update(root, {'action': 'search', 'question_id': ident}, change)


def finish_question(root, ident, owner, outputs, gap=None, *, results=None):
    def change(state):
        q = state['questions'][ident]
        if q['owner'] != owner or q['status'] != 'running':
            raise ValueError('Only the current task owner may finish the question')
        if not all(inside(root, p).relative_to(Path(root).resolve()).as_posix() in q['allowed_outputs'] for p in outputs):
            raise ValueError('Result was not among declared outputs')
        if hashes(root, list(q['inputs'])) != q['inputs']:
            raise ValueError('Question inputs changed; review the result against the new inputs')
        if not outputs or (gap is not None and not gap.strip()):
            raise ValueError('A saved result/report and explicit gap explanation are required')
        candidate = {**q, 'gap': gap, 'requirement_results': results}
        issues = question_contract_issues(root, candidate)
        if issues:
            raise ValueError('\n'.join(issues))
        q.update(status='gap' if gap else 'complete', results=hashes(root, outputs), gap=gap, requirement_results=results)
    return update(root, {'action': 'finish_question', 'question_id': ident}, change)


def kb_issues(root):
    from .links import validate_file
    issues = []
    for relative in kb_paths(root):
        file = inside(root, relative)
        if file.suffix.lower() != '.md' and file.name != '.md':
            continue
        for error in validate_file(file, local_anchors=True, readable_links=True):
            issues.append(problem('kb.link', relative, error, file=file))
        text = file.read_text(encoding='utf-8')
        if re.search(r'(?im)^\s*\|.*\|\s*$\n\s*\|?\s*:?-{3,}', text) or re.search(r'(?i)<a\s+[^>]*(?:name|id)\s*=', text):
            issues.append(problem('kb.format', relative, 'Markdown tables or HTML anchors conflict with DOC-4/LINK-4', file=file))
        if file.name != 'Analysis.md':
            for doc4_err in doc4_sentence_issues(text):
                issues.append(problem('kb.doc4_sentence', relative, doc4_err, file=file))
    return issues


def attachment_issues(root):
    from .upwork_data import classify_attachment, detect_client_videos, extract_attachment_markdown
    root = Path(root).resolve()
    issues = []
    pj_file = root / 'ꘖ/project.json'
    if not pj_file.is_file():
        return issues
    try:
        pj = json.loads(pj_file.read_text(encoding='utf-8'))
        snap_path = root / pj.get('snapshot', '')
        snap = json.loads(snap_path.read_text(encoding='utf-8')) if snap_path.is_file() else {}
    except Exception:
        return issues

    kb_dir = root / 'ꘖ/KB'
    att_root = kb_dir / 'Evidence/Attachments'
    source_dir = root / 'source'

    attachments = []
    seen_sha = set()
    for item in (snap.get('asset_evidence') or []):
        rel = item.get('file')
        if rel and (kb_dir / rel).is_file():
            target = kb_dir / rel
            sha = item.get('sha256') or file_hash(target)
            if sha not in seen_sha:
                seen_sha.add(sha)
                attachments.append({'filename': target.name, 'sha256': sha, 'evidence_path': target})
    if att_root.is_dir():
        for sha_dir in sorted(att_root.iterdir()):
            if sha_dir.is_dir() and re.fullmatch(r'[0-9a-f]{64}', sha_dir.name):
                for f in sorted(sha_dir.iterdir()):
                    if f.is_file() and sha_dir.name not in seen_sha:
                        seen_sha.add(sha_dir.name)
                        attachments.append({'filename': f.name, 'sha256': sha_dir.name, 'evidence_path': f})
    if source_dir.is_dir():
        for f in sorted(source_dir.iterdir()):
            if f.is_file():
                sha = file_hash(f)
                ev_target = att_root / sha / f.name
                if not ev_target.is_file():
                    issues.append(problem(
                        'attachment.evidence_missing',
                        f'source/{f.name}',
                        f'Attached file in source/{f.name} is not synced to ꘖ/KB/Evidence/Attachments/{sha}/{f.name}; run sync-attachments',
                        file=f,
                    ))
                if sha not in seen_sha:
                    seen_sha.add(sha)
                    attachments.append({'filename': f.name, 'sha256': sha, 'evidence_path': f})

    manual_proj = root / 'KB/Project.md'
    agent_proj = root / 'ꘖ/KB/Project.md'
    agent_projects = root / 'ꘖ/KB/Projects.md'
    manual_text = manual_proj.read_text(encoding='utf-8') if manual_proj.is_file() else ''
    agent_text = agent_proj.read_text(encoding='utf-8') if agent_proj.is_file() else ''
    projects_text = agent_projects.read_text(encoding='utf-8') if agent_projects.is_file() else ''

    doc_markdowns = []
    for att in attachments:
        fname = att['filename']
        sha = att['sha256']
        payload = att['evidence_path'].read_bytes()
        src_candidates = [p for p in (source_dir.iterdir() if source_dir.is_dir() else []) if p.is_file() and file_hash(p) == sha]
        if not src_candidates:
            issues.append(problem(
                'attachment.source_missing',
                f'source/{fname}',
                f'Attached file {fname} must be saved in the root source/ folder (§2.1); run sync-attachments',
                file=att['evidence_path'],
            ))
        kind = classify_attachment(fname, payload)
        if kind == 'document':
            doc_md = extract_attachment_markdown(att['evidence_path'], payload)
            doc_markdowns.append(doc_md)
            heading_marker = f'Описание в `{fname}`'
            for label, target_file, target_text in (
                ('KB/Project.md', manual_proj, manual_text),
                ('ꘖ/KB/Project.md', agent_proj, agent_text),
                ('ꘖ/KB/Projects.md', agent_projects, projects_text),
            ):
                if heading_marker not in target_text:
                    issues.append(problem(
                        'attachment.kb_missing',
                        label,
                        f'Attached document {fname} is missing from {label} (§2.2); run sync-attachments',
                        file=target_file,
                    ))
        elif kind == 'image':
            heading_marker = f'Описание в `{fname}`'
            for label, target_file, target_text in (
                ('KB/Project.md', manual_proj, manual_text),
                ('ꘖ/KB/Project.md', agent_proj, agent_text),
                ('ꘖ/KB/Projects.md', agent_projects, projects_text),
            ):
                if heading_marker not in target_text:
                    issues.append(problem(
                        'attachment.image_missing',
                        label,
                        f'Attached image {fname} must be transcribed and analyzed in {label} (§2.4)',
                        file=target_file,
                    ))
                else:
                    sec_match = re.search(rf'(?ms){re.escape(heading_marker)}.*?(?:~~~+|```+)markdown\n(.*?)\n(?:~~~+|```+)', target_text)
                    sec_body = (sec_match.group(1) if sec_match else '').strip()
                    if (not sec_body or '«' not in sec_body
                            or not re.search(r'(?i)подтверждени|противоречи', sec_body)
                            or not re.search(r'(?i)оценка.*\d+\s*%', sec_body)):
                        issues.append(problem(
                            'attachment.image_incomplete',
                            label,
                            f'Attached image {fname} in {label} requires verbatim «...» text transcription, exhaustive UI description, and confirmation/contradiction analysis with % score (§2.4)',
                            file=target_file,
                        ))

    videos = detect_client_videos(snap.get('description') or '', doc_markdowns,
                                  [{'filename': a['filename'], 'sha256': a['sha256']} for a in attachments])
    for v in videos:
        v_heading = v['heading']
        for label, target_file, target_text in (
            ('KB/Project.md', manual_proj, manual_text),
            ('ꘖ/KB/Project.md', agent_proj, agent_text),
            ('ꘖ/KB/Projects.md', agent_projects, projects_text),
        ):
            if v_heading not in target_text:
                issues.append(problem(
                    'attachment.video_missing',
                    label,
                    f'Client video ({v_heading}) must be transcribed in {label} (§2.3)',
                    file=target_file,
                ))
            else:
                if ('# Полная расшифровка аудиозаписи:' not in target_text
                        or not re.search(r'\[\d{2}:\d{2}\]', target_text)):
                    issues.append(problem(
                        'attachment.video_incomplete',
                        label,
                        f'Client video ({v_heading}) in {label} requires # Видео:, # Ключевые моменты..., and # Полная расшифровка аудиозаписи: with [MM:SS] timestamps (§2.3)',
                        file=target_file,
                    ))
    return issues


def check_project(root):
    root = Path(root).resolve()
    issues = kb_issues(root) + attachment_issues(root)
    for folder in (root / 'ꘖ/data', root / '.agents'):
        if folder.is_dir():
            for script in sorted(folder.rglob('*')):
                if script.is_file() and script.suffix.lower() in ('.py', '.ps1', '.sh', '.bat', '.cmd'):
                    issues.append(problem('project.one_off_script', script.relative_to(root).as_posix(),
                        'Executable one-off scripts are prohibited in project directories (FILE-5/EXEC-1); use shared upwork_project.py commands', file=script))
    from .links import readable_link_issues
    documents = [root / '.md', *sorted((root / 'result').rglob('*'))]
    for document in documents:
        if document.is_file() and document.name != 'draft.prev.md' and (document.name == '.md' or document.suffix.lower() in ('.md', '.markdown', '.txt', '.html', '.htm')):
            for error in readable_link_issues(document.read_text(encoding='utf-8')):
                issues.append(problem('document.link_style', document.relative_to(root).as_posix(), error, file=document))
    path = root / 'ꘖ/KB/Analysis.json'
    if not path.is_file():
        issues.append(problem('analysis.missing', 'ꘖ/KB/Analysis.json', 'Analysis draft is not saved'))
    else:
        try:
            value = json.loads(path.read_text(encoding='utf-8-sig'))
            contract_issues = analysis_issues(value)
            issues.extend(contract_issues)
            if isinstance(value, dict):
                issues.extend(evidence_issues(root, value))
                if value.get('schema_version') in (2, 3) and not contract_issues:
                    from .knowledge import sync_website_card
                    website = sync_website_card(root, value, check=True)
                    if website['status'] not in ('published', 'unchanged'):
                        issues.append(problem('project.website', '.md',
                            'Publish the explicit evidenced client/target website selection, or null if unidentified', file=root / '.md'))
                    established_identity = any(
                        isinstance(c, dict)
                        and (c.get('verification_status') == 'verified' or (c.get('probability_percent') or 0) >= 80)
                        and re.search(
                            r'(?:клиент|автор|художник|владелец|заказчик|основатель)[^.]{0,40}?\b[A-ZА-ЯЁ][a-zа-яё]{1,25}\s+[A-ZА-ЯЁ][a-zа-яё]{1,25}\b',
                            c.get('essence') or '',
                        )
                        for c in (value.get('identity') or [])
                    )
                    if established_identity:
                        for rel_proj in ('KB/Project.md', 'ꘖ/KB/Project.md'):
                            proj_file = root / rel_proj
                            if proj_file.is_file():
                                proj_txt = proj_file.read_text(encoding='utf-8')
                                if re.search(r'#\s*1\.1\s+Имя\s*\r?\n\s*неизвестно\b', proj_txt, re.IGNORECASE):
                                    issues.append(problem(
                                        'kb.identity_mismatch',
                                        rel_proj,
                                        f'Established client identity in Analysis.json is not synced to {rel_proj} (# 1.1 Имя is still неизвестно)',
                                        file=proj_file,
                                    ))
        except (OSError, ValueError, TypeError) as exc:
            issues.append(problem('analysis.input', str(path), str(exc)))
    for issue in issues:
        if not issue.get('file'):
            issue['file'] = str(path)
    return {'valid': not issues, 'issues': issues, 'semantic_truth_verified': False}


def record_review(root, report, *, parent_id, reviewer_id, role='AA', native_evidence=None, risk=None):
    from .review import record
    return record(root, report, parent_id=parent_id, reviewer_id=reviewer_id, role=role,
                  native_evidence=native_evidence, risk=risk)


def prepare_review(root, parent_id, spec=None, response=None):
    from .review import prepare
    return prepare(root, parent_id, spec, response)


def review_input(root, package):
    """Verify exact requests, response, claim versions and evidence in the reviewer."""
    from .review import input_receipt
    return input_receipt(root, package)


def record_review_disposition(root, review_id, finding_id, status, basis, evidence, parent_id):
    from .review import disposition
    return disposition(root, review_id, finding_id, status, basis, evidence, parent_id)

def complete_stage(root, stage, inputs, outputs, *, note=None):
    root = Path(root).resolve()
    if stage not in STAGES or not inputs or not outputs:
        raise ValueError('Known stage and explicit nonempty input/output artifacts required')
    in_hashes, out_hashes = hashes(root, inputs), hashes(root, outputs)
    if set((*in_hashes, *out_hashes)) & {'ꘖ/data/workflow.json', 'ꘖ/data/rendered.json', 'ꘖ/KB/Progress.md'}:
        raise ValueError('Generated workflow/navigation state cannot serve as its own stage proof')
    def change(state):
        statuses = stage_statuses(root, state)
        preceding = STAGES[:STAGES.index(stage)]
        if any(statuses[s] != 'complete' for s in preceding):
            raise ValueError('Complete/check preceding stages before marking this stage complete')
        if stage == 'identity_init' and not registration_status(root)['complete']:
            raise ValueError('Complete native project/folder registration in the current platform/profile first')
        if stage == 'research':
            if not questions_current(root, state):
                raise ValueError('A research question is open or its inputs/results changed')
        if stage == 'analysis':
            from .analysis import require_current_contract
            require_current_contract(json.loads((Path(root) / 'ꘖ/KB/Analysis.json').read_text(encoding='utf-8-sig')))
            result = check_project(root)
            if not result['valid']:
                raise ValueError('Resolve project/evidence diagnostics before completing analysis')
            if 'ꘖ/KB/Analysis.json' not in out_hashes:
                raise ValueError('Analysis.json must be a declared stage output')
        if stage in ('review', 'kb_review', 'finalize'):
            from .review import authorize
            approval = authorize(root, state)
            if not check_project(root)['valid']:
                raise ValueError('Current KB/evidence checks failed')
        if stage == 'kb_review' and not note:
            raise ValueError('Record the result of the semantic KB consistency review')
        if stage == 'finalize':
            from .journal import get_existing_step_ids, step_errors
            from .text_workflow import gate_paths
            gate_paths([Path(root) / name for name in outputs])
            from .context import generate
            scratch_dir = Path(root) / 'ꘖ/data/scratch'
            if scratch_dir.is_dir() and any(p.is_file() for p in scratch_dir.rglob('*')):
                raise ValueError('Clean or consume all temporary files in ꘖ/data/scratch before finalizing')
            prepared = state['requests'][-1].get('response_prepared', {}) if state['requests'] else {}
            journal = Path(root) / prepared.get('journal', 'ꙮ/1 - Анализ')
            ids = get_existing_step_ids(journal)
            if not ids or any(step_errors(journal, ident) for ident in ids):
                raise ValueError('Complete exact req/res journal pairs before external export')
            latest = max(ids)
            reply = journal / 'res' / f'{latest}.md'
            from .links import readable_link_issues
            link_issues = readable_link_issues(reply.read_text(encoding='utf-8'))
            if link_issues:
                raise ValueError('\n'.join(link_issues))
            if reply.relative_to(Path(root).resolve()).as_posix() not in out_hashes:
                raise ValueError('Declare the actual final reply file as a finalize output')
            if state['requests'] and (journal / 'req' / f'{latest}.md').read_bytes().decode('utf-8') != state['requests'][-1]['text']:
                raise ValueError('Latest journal request differs from the recorded current continuation request')
            from .review import authorize
            approval = authorize(root, state, response=reply.read_bytes().decode('utf-8'))
            if (any(not request.get('response_prepared') for request in state['requests']) or
                    not state['requests'] or state['requests'][-1]['response_prepared'].get('sha256') != approval['response_sha256']):
                raise ValueError('Record the exact approved answer for current requests before finalizing')
            target, _, _ = generate(Path(root), Path(root) / '.agents/context.json')
            out_hashes[target.relative_to(Path(root).resolve()).as_posix()] = file_hash(target)
        state['stages'][stage] = {'status': 'complete', 'time': now(), 'inputs': in_hashes, 'outputs': out_hashes, 'note': note}
        if stage == 'finalize':
            state['stages'][stage]['request_ids'] = [request['id'] for request in state['requests']]
        if stage == 'research':
            from copy import deepcopy
            state['stages'][stage]['research_questions'] = deepcopy(state['questions'])
        if stage in ('review', 'kb_review', 'finalize'):
            state['stages'][stage]['review_approval'] = approval
            state['stages'][stage]['kb_inputs'] = hashes(root, kb_paths(Path(root)))
            state['stages'][stage]['evidence_inputs'] = hashes(root, evidence_paths(root))
        # Derived stages are rechecked after a changed prerequisite, even if their old files still exist.
        for dependent in STAGES[STAGES.index(stage) + 1:]:
            if dependent in state['stages']:
                state['stages'][dependent].update(status='stale', invalidated_by=stage)
    return update(root, {'action': 'complete_stage', 'stage': stage}, change)
