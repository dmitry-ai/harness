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
    return sorted({p.relative_to(root).as_posix() for directory in (evidence, root / 'KB')
                   for p in directory.rglob('*') if p.is_file() and not p.is_relative_to(evidence / 'Reviews')})


def questions_current(root, state):
    return all(q['status'] in ('complete', 'gap')
               and receipt_current(root, {'inputs': q['inputs'], 'outputs': q['results']})
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
            'detail': 'Stages cover initial analysis only. Continue the same filesystem project in either UI using agent KB, journal and actual proposal files; Context.md is an external export.'}


def publish_progress(root, state):
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
            lines.append(f'  [Сохранённый результат](<{relative}>)')
    lines += ['', '## Профильные модули']
    lines += [f'- [{p.name}]({p.name})' for p in sorted((Path(root) / 'ꘖ/KB').glob('*.md')) if p.name != 'Progress.md']
    lines += ['', 'Перед новым исследованием проверь обзор и профильные модули KB.',
              'Исправления распространяются на связанные утверждения и документы; непроверенное отмечается явно.',
              'Context.md предназначен для передачи внешнему агенту (например Gemini DeepThink), а не для внутренней работы.', '']
    return publish_owned(Path(root) / 'ꘖ/KB/Progress.md', '\n'.join(lines), source=state_path(root))


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


def record_current_answer(root, response):
    from .journal import record_answer
    state = load(root)
    unanswered = [x for x in state['requests'] if not x.get('response_prepared')]
    if not unanswered:
        raise ValueError('No unrecorded current requests; import exact native inputs or save the current request first')
    turn = unanswered[-1]['id']
    # Native IDs may contain colons, which are invalid in Windows group filenames.
    # Keep the original IDs in the receipt and use a stable filename-safe turn key.
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', turn):
        turn = 'native-' + hashlib.sha256(turn.encode('utf-8')).hexdigest()
    steps = record_answer(Path(root) / 'ꙮ/1 - Анализ', [x['text'] for x in unanswered], response, turn, [x['id'] for x in unanswered])
    ids = {x['id'] for x in unanswered}
    def change(state):
        for request in state['requests']:
            if request['id'] in ids:
                request['response_prepared'] = {'turn': turn, 'steps': steps, 'sha256': hashlib.sha256(response.encode()).hexdigest()}
    result = update(root, {'action': 'reply_prepared', 'turn': turn, 'steps': steps}, change)
    return {**result, 'journal_steps': steps, 'delivery_verified': False}


def add_question(root, ident, question, impact, done_when, inputs, outputs):
    if not re.fullmatch(r'[A-Z][A-Z0-9-]*', ident) or not all(isinstance(x, str) and x.strip() for x in (question, impact, done_when)):
        raise ValueError('Question needs a stable ID, question, impact and completion criterion')
    if not inputs:
        raise ValueError('Declare at least the saved capture or relevant KB module as question input')
    input_hashes = hashes(root, inputs)
    permitted = [inside(root, path).relative_to(Path(root).resolve()).as_posix() for path in outputs]
    if not permitted or any(not p.startswith('ꘖ/') or p.startswith('ꘖ/data/workflow') for p in permitted):
        raise ValueError('Declare exact project-owned outputs under ꘖ; not workflow state')
    def change(state):
        if ident in state['questions']:
            raise ValueError('Question already exists; use its saved inputs/results')
        state['questions'][ident] = {'id': ident, 'question': question, 'impact': impact, 'done_when': done_when,
            'inputs': input_hashes, 'allowed_outputs': permitted, 'status': 'pending', 'owner': None, 'searches': [], 'results': {}}
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


def finish_question(root, ident, owner, outputs, gap=None):
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
        q.update(status='gap' if gap else 'complete', results=hashes(root, outputs), gap=gap)
    return update(root, {'action': 'finish_question', 'question_id': ident}, change)


def kb_issues(root):
    from .links import validate_file
    issues = []
    for relative in kb_paths(root):
        file = inside(root, relative)
        if file.suffix.lower() != '.md' and file.name != '.md':
            continue
        for error in validate_file(file, local_anchors=True):
            issues.append(problem('kb.link', relative, error, file=file))
        text = file.read_text(encoding='utf-8')
        if re.search(r'(?im)^\s*\|.*\|\s*$\n\s*\|?\s*:?-{3,}', text) or re.search(r'(?i)<a\s+[^>]*(?:name|id)\s*=', text):
            issues.append(problem('kb.format', relative, 'Markdown tables or HTML anchors conflict with DOC-4/LINK-4', file=file))
    return issues


def check_project(root):
    root = Path(root).resolve()
    issues = kb_issues(root)
    path = root / 'ꘖ/KB/Analysis.json'
    if not path.is_file():
        issues.append(problem('analysis.missing', 'ꘖ/KB/Analysis.json', 'Analysis draft is not saved'))
    else:
        try:
            value = json.loads(path.read_text(encoding='utf-8-sig'))
            issues.extend(analysis_issues(value))
            if isinstance(value, dict):
                issues.extend(evidence_issues(root, value))
        except (OSError, ValueError, TypeError) as exc:
            issues.append(problem('analysis.input', str(path), str(exc)))
    for issue in issues:
        if not issue.get('file'):
            issue['file'] = str(path)
    return {'valid': not issues, 'issues': issues, 'semantic_truth_verified': False}


def record_review(root, report, *, parent_id, reviewer_id, role='AA', risk='routine'):
    if role != 'AA' or not parent_id or not reviewer_id or risk not in ('routine', 'significant'):
        raise ValueError('Observed A.A parent/reviewer IDs and explicit risk required')
    independent = reviewer_id != parent_id
    file = inside(root, report)
    data = json.loads(file.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Review report must be a JSON object')
    if data.get('result') != 'approved' or not isinstance(data.get('findings'), list) or not data.get('scope'):
        raise ValueError('Review needs scope, findings and approved result')
    if not isinstance(data['scope'], list) or not set((*SECTIONS, 'kb_consistency')).issubset(data['scope']):
        raise ValueError('Independent review must cover all five stages and KB consistency')
    package = inside(root, data.get('package', ''))
    package_data = json.loads(package.read_text(encoding='utf-8'))
    if package_data.get('kb_inputs') != hashes(root, kb_paths(Path(root))) or package_data.get('evidence_inputs') != hashes(root, evidence_paths(root)) or package_data.get('parent_id') != parent_id:
        raise ValueError('Review package does not match the present KB and parent')
    proof_paths = [report, data['package']]
    if independent:
        execution = inside(root, data.get('native_evidence', ''))
        native = json.loads(execution.read_text(encoding='utf-8'))
        if native.get('parent_id') != parent_id or native.get('reviewer_id') != reviewer_id or native.get('status') != 'completed':
            raise ValueError('Saved native review identity/status differs')
        from .metrics import verify_native_proof
        verify_native_proof(root, native, package=package.name)
        proof_paths.append(data['native_evidence'])
    else:
        if data.get('review_kind') != 'self_review':
            raise ValueError('Parent review must explicitly say self_review; it is not independent')
        from .platforms import adapter
        adapter().require_current_binding(root, parent_id)  # Observe the current task, not only an earlier matching request.
        native = {'model_verification': 'parent self-review; exact model/High requires session metadata'}
    if package_data.get('risk') == 'significant' or any(f.get('severity') in ('significant', 'critical') for f in data['findings'] if isinstance(f, dict)):
        risk = 'significant'
    for finding in data['findings']:
        if not isinstance(finding, dict) or finding.get('status') not in ('resolved', 'rejected') or not finding.get('disposition') or not finding.get('evidence'):
            raise ValueError('Every finding needs a resolved/rejected disposition with evidence; unresolved findings block review')
        local_file = inside(root, finding['evidence'])
        if not local_file.is_file():
            raise ValueError('Review finding evidence is missing')
    def change(state):
        state['reviews'] = [r for r in state['reviews'] if r['reviewer_id'] != reviewer_id]
        state['reviews'].append({'parent_id': parent_id, 'reviewer_id': reviewer_id, 'role': role, 'risk': risk,
            'report': str(file.relative_to(Path(root).resolve())), 'proof': hashes(root, proof_paths), 'independent': independent,
            'kb_inputs': hashes(root, kb_paths(Path(root))), 'evidence_inputs': hashes(root, evidence_paths(root)),
            'model_verification': native.get('model_verification', 'unverified'), 'time': now()})
    return update(root, {'action': 'review', 'reviewer_id': reviewer_id}, change)


def prepare_review(root, parent_id, risk='routine'):
    if not parent_id or risk not in ('routine', 'significant'):
        raise ValueError('Observed parent ID and routine/significant risk required')
    current = hashes(root, kb_paths(Path(root)))
    data = {'schema_version': 1, 'parent_id': parent_id, 'risk': risk, 'kb_inputs': current, 'evidence_inputs': hashes(root, evidence_paths(root)),
            'scope': [*SECTIONS, 'kb_consistency'], 'knowledge_source': 'agent KB and primary evidence; no Context.md'}
    payload = json_data(data)
    path = Path(root) / 'ꘖ/KB/Evidence/Reviews' / (hashlib.sha256(payload).hexdigest() + '-inputs.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError('Immutable review input package differs')
    else:
        from .storage import create_bytes
        create_bytes(path, payload)
    return {'package': path.relative_to(Path(root).resolve()).as_posix(), **data}


def review_input(root, package):
    """Read and verify an immutable package inside the actual reviewer process."""
    import os
    path = inside(root, package)
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('kb_inputs') != hashes(root, kb_paths(Path(root))) or data.get('evidence_inputs') != hashes(root, evidence_paths(root)):
        raise ValueError('Reviewer package does not match the present KB and primary evidence')
    reviewer = os.environ.get('CODEX_THREAD_ID')
    if not reviewer:
        raise ValueError('Native Codex reviewer thread ID is unavailable')
    return {'upwork_review_input': 1, 'verified': True, 'project_root': str(Path(root).resolve()),
            'job_id': load(root)['job_id'], 'parent_id': data['parent_id'], 'reviewer_id': reviewer,
            'package': path.relative_to(Path(root).resolve()).as_posix(), 'package_sha256': file_hash(path),
            'kb_inputs': data['kb_inputs'], 'evidence_inputs': data['evidence_inputs']}


def complete_stage(root, stage, inputs, outputs, *, note=None):
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
            result = check_project(root)
            if not result['valid']:
                raise ValueError('Resolve project/evidence diagnostics before completing analysis')
            if 'ꘖ/KB/Analysis.json' not in out_hashes:
                raise ValueError('Analysis.json must be a declared stage output')
        if stage in ('review', 'kb_review', 'finalize'):
            current_kb = hashes(root, kb_paths(Path(root)))
            from .metrics import verify_native_proof
            reviews = []
            for review in state['reviews']:
                if review['kb_inputs'] == current_kb and review.get('evidence_inputs') == hashes(root, evidence_paths(root)) and receipt_current(root, {'inputs': review['proof']}):
                    report_data = json.loads(inside(root, review['report']).read_text(encoding='utf-8'))
                    if review.get('independent', True):
                        native = json.loads(inside(root, report_data['native_evidence']).read_text(encoding='utf-8'))
                        verify_native_proof(root, native)
                    reviews.append(review)
            required = 2 if any(r['risk'] == 'significant' for r in state['reviews']) else 1
            eligible = [r for r in reviews if required == 1 or r.get('independent', True)]
            if len({r['reviewer_id'] for r in eligible}) < required:
                raise ValueError('Need current A.A review; significant risk requires two independent reviewers and handled findings')
            if not check_project(root)['valid']:
                raise ValueError('Current KB/evidence checks failed')
        if stage == 'kb_review' and not note:
            raise ValueError('Record the result of the semantic KB consistency review')
        if stage == 'finalize':
            from .journal import get_existing_step_ids, step_errors
            from .context import generate
            journal = Path(root) / 'ꙮ/1 - Анализ'
            ids = get_existing_step_ids(journal)
            if not ids or any(step_errors(journal, ident) for ident in ids):
                raise ValueError('Complete exact req/res journal pairs before external export')
            latest = max(ids)
            reply = journal / 'res' / f'{latest}.md'
            if reply.relative_to(Path(root).resolve()).as_posix() not in out_hashes:
                raise ValueError('Declare the actual final reply file as a finalize output')
            if state['requests'] and (journal / 'req' / f'{latest}.md').read_bytes().decode('utf-8') != state['requests'][-1]['text']:
                raise ValueError('Latest journal request differs from the recorded current continuation request')
            target, _, _ = generate(Path(root), Path(root) / '.agents/context.json')
            out_hashes[target.relative_to(Path(root).resolve()).as_posix()] = file_hash(target)
        state['stages'][stage] = {'status': 'complete', 'time': now(), 'inputs': in_hashes, 'outputs': out_hashes, 'note': note}
        if stage == 'finalize':
            state['stages'][stage]['request_ids'] = [request['id'] for request in state['requests']]
        if stage == 'research':
            from copy import deepcopy
            state['stages'][stage]['research_questions'] = deepcopy(state['questions'])
        if stage in ('review', 'kb_review', 'finalize'):
            state['stages'][stage]['kb_inputs'] = hashes(root, kb_paths(Path(root)))
            state['stages'][stage]['evidence_inputs'] = hashes(root, evidence_paths(root))
        # Derived stages are rechecked after a changed prerequisite, even if their old files still exist.
        for dependent in STAGES[STAGES.index(stage) + 1:]:
            if dependent in state['stages']:
                state['stages'][dependent].update(status='stale', invalidated_by=stage)
    return update(root, {'action': 'complete_stage', 'stage': stage}, change)
