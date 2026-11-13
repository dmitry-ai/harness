# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
# https://github.com/dmitry-ai/harness/issues/57
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
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
	r = result
	return r
def kb_paths(root):
	kb = Path(root) / 'ꘖ/KB'
	r = [p.relative_to(root).as_posix() for p in sorted(kb.rglob('*')) if p.is_file() and (p.suffix.lower() in ('.md', '.json') or '.md' == p.name) and ('Progress.md' != p.name) and (not p.is_relative_to(kb / 'Evidence'))]
	return r
def evidence_paths(root):
	root = Path(root).resolve()
	evidence = root / 'ꘖ/KB/Evidence'
	dirs = [evidence, root / 'KB']
	if (root / 'source').is_dir():
		dirs.append(root / 'source')
	r = sorted({p.relative_to(root).as_posix() for directory in dirs for p in directory.rglob('*') if p.is_file() and (not p.is_relative_to(evidence / 'Reviews'))})
	return r
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
	if any((r.get('status') in ('unverified', 'unavailable') for r in results if isinstance(r, dict))) and (not question.get('gap')):
		issues.append('Unavailable/unverified requirements require an explicit question gap')
	return issues
def questions_current(root, state):
	return all((q['status'] in ('complete', 'gap') and receipt_current(root, {'inputs': q['inputs'], 'outputs': q['results']}) and (not question_contract_issues(root, q)) for q in state['questions'].values()))
def state_path(root):
	return Path(root).resolve() / 'ꘖ/data/workflow.json'
def load(root):
	root = Path(root).resolve()
	pj = root / 'ꘖ/project.json'
	if not pj.is_file():
		raise ValueError('Provide the existing project root from this chat; no project is selected or initialized implicitly')
	project = json.loads(pj.read_text(encoding='utf-8'))
	path = state_path(root)
	if not path.exists():
		r = {'schema_version': 1, 'project_root': str(root), 'job_id': project['job_id'], 'stages': {}, 'questions': {}, 'reviews': [], 'events': [], 'requests': [], 'legacy': True}
	else:
		state = json.loads(path.read_text(encoding='utf-8'))
		if 1 != state.get('schema_version') or state.get('project_root') != str(root) or state.get('job_id') != project['job_id']:
			raise ValueError('Workflow identity/version mismatch; preserve the file for explicit migration')
		r = state
	return r
def receipt_current(root, receipt):
	return all((inside(root, path).is_file() and file_hash(inside(root, path)) == digest for group in ('inputs', 'outputs') for path, digest in receipt.get(group, {}).items())) and ('kb_inputs' not in receipt or receipt['kb_inputs'] == hashes(root, kb_paths(Path(root)))) and ('evidence_inputs' not in receipt or receipt['evidence_inputs'] == hashes(root, evidence_paths(root)))
def _target_complete(target, item):
	import os
	from .runtime import profile_name, registration_profile_name
	if not isinstance(item, dict):
		r = False
	elif not isinstance(item.get('profiles'), dict):
		r = bool(item.get('complete', item.get('project_id') and item.get('folder_id')))
	else:
		prof = profile_name() if 'codex' == target and 'CODEX_HOME' in os.environ else item.get('profile') or registration_profile_name()
		r = bool(item['profiles'].get(prof, {}).get('ready'))
	return r
def registration_status(root):
	from .runtime import settings, platform_name
	root = Path(root).resolve()
	config, platform = (settings(), platform_name())
	path = root / 'ꘖ/data/registrations.json'
	required = path.exists() or root.is_relative_to(Path(config['workspace_root']) / config['daily_root'])
	data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
	receipt = data.get(platform) if isinstance(data, dict) else None
	targets = list(dict.fromkeys((config.get('registration') or {}).get('targets') or [platform]))
	if platform not in targets:
		targets.insert(0, platform)
	targets_status = {}
	for target in targets:
		item = data.get(target) if isinstance(data, dict) else None
		done = not required or _target_complete(target, item)
		targets_status[target] = {'complete': done, 'status': (item.get('status') if isinstance(item, dict) else None) or ('registered' if done else 'pending'), 'attempts': item.get('attempts', 0) if isinstance(item, dict) else 0}
	complete = targets_status[platform]['complete']
	pending_targets = [target for target, info in targets_status.items() if not info['complete']]
	r = {'platform': platform, 'required': required, 'complete': complete, 'all_registered': not pending_targets, 'targets': targets_status, 'pending_targets': pending_targets, 'receipt': receipt}
	return r
def stage_statuses(root, state):
	statuses, dependency_ok = ({}, True)
	for stage in STAGES:
		receipt = state['stages'].get(stage)
		current = bool(receipt and 'complete' == receipt.get('status') and receipt_current(root, receipt))
		if 'identity_init' == stage:
			current = current and registration_status(root)['complete']
		if 'research' == stage and receipt:
			current = current and questions_current(root, state) and (receipt.get('research_questions') == state['questions'])
		if stage in ('review', 'kb_review', 'finalize') and current:
			from .review import approval_current
			current = approval_current(root, state, receipt.get('review_approval'))
		if 'finalize' == stage:
			covered = receipt.get('request_ids') if receipt else None
			current = current and (covered == [request['id'] for request in state['requests']] if None is not covered else all((request.get('response_prepared') for request in state['requests'])))
		statuses[stage] = 'complete' if current and dependency_ok else 'stale' if receipt else 'pending'
		dependency_ok = dependency_ok and current
	r = statuses
	return r
def status(root):
	root = Path(root).resolve()
	state = load(root)
	statuses = stage_statuses(root, state)
	existing = {name: (root / 'ꘖ/KB' / name).is_file() for name in ('Analysis.json', 'Analysis.md', 'Progress.md')}
	proposals = [{'path': inside(root, path).relative_to(root).as_posix(), 'sha256': file_hash(inside(root, path))} for path in sorted((root / 'result').rglob('*.md')) if path.is_file() and path.name in ('draft.md', 'final.md', 'draft.prev.md')]
	checkpoint = root / 'ꘖ/data/continuation.md'
	r = {'project': str(root), 'job_id': state['job_id'], 'legacy': state['legacy'], 'stages': statuses, 'scope': 'initial_analysis', 'proposal_artifacts': proposals, 'continuation': {'file': 'ꘖ/data/continuation.md', 'exists': checkpoint.is_file()}, 'next_stage': next((s for s in STAGES if 'complete' != statuses[s]), None), 'agent_kb': str(root / 'ꘖ/KB'), 'existing_drafts': existing, 'kb_hashes': hashes(root, kb_paths(root)), 'questions': list(state['questions'].values()), 'registration': registration_status(root), 'detail': 'Stages track saved analysis. Every new analytical reply requires current request/answer-bound approval. Continue the same filesystem project in either UI using agent KB, journal and actual proposal files; Context.md is an external export.'}
	return r
def publish_progress(root, state):
	from .links import markdown_link
	statuses = stage_statuses(root, state)
	lines = ['# Analysis Progress', '', 'Service navigation for the agent KB; statuses do not prove the truth of conclusions.', f"Job: {state['job_id']}.", '', '## Stages']
	lines += [f'- {stage}: {statuses[stage]}.' for stage in STAGES if 'finalize' != stage]
	lines += ['Verify completion and external export receipt with the status command.', '']
	if (Path(root) / 'ꘖ/data/continuation.md').is_file():
		lines += ['Current post-analysis instruction: [continuation state](../data/continuation.md).', '']
	lines += ['', '## Questions']
	for question in state['questions'].values():
		lines += [f"- {question['id']}: {question['question']}", f"  Status: {question['status']}; owner: {question.get('owner') or 'unassigned'}.", f"  Completion criterion: {question['done_when']}."]
		if question.get('gap'):
			lines.append('  Gap: ' + question['gap'])
		for ref in question.get('results', {}):
			target = inside(root, ref)
			import os
			relative = Path(os.path.relpath(target, Path(root) / 'ꘖ/KB')).as_posix()
			lines.append('  ' + markdown_link('Saved result', relative))
	lines += ['', '## Topical Modules']
	lines += ['- ' + markdown_link(p.name, p.name) for p in sorted((Path(root) / 'ꘖ/KB').glob('*.md')) if 'Progress.md' != p.name]
	lines += ['', 'Before new research, check the overview and topical KB modules.', 'Corrections propagate to linked claims and documents; anything unverified is marked explicitly.', 'Context.md is intended for handoff to an external agent, not for internal work.', '']
	r = publish_owned(Path(root) / 'ꘖ/KB/Progress.md', '\n'.join(lines), source=state_path(root), history=False)
	return r
def update(root, event, change):
	root = Path(root).resolve()
	with locked(root / 'ꘖ/data/workflow.lock'):
		state = load(root)
		change(state)
		state['events'].append({'id': uuid.uuid4().hex, 'time': now(), **event})
		replace_bytes(state_path(root), json_data(state))
		progress = publish_progress(root, state)
	r = {'workflow': str(state_path(root)), 'progress': progress, **status(root)}
	return r
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
def resume(root, reason, request=None):
	if not isinstance(reason, str) or not reason.strip():
		raise ValueError('Record why the current analysis is being continued')
	if None is not request and (not isinstance(request, str) or not request.strip()):
		raise ValueError('Continuation request must preserve exact nonempty user text')
	def change(state):
		state['legacy'] = False
		if None is not request:
			state['requests'].append({'id': uuid.uuid4().hex, 'time': now(), 'text': request})
		pj = json.loads((Path(root) / 'ꘖ/project.json').read_text(encoding='utf-8'))
		source = inside(root, pj['snapshot'])
		data = json.loads(source.read_text(encoding='utf-8'))
		from .upwork_data import normalize_job_id
		if normalize_job_id(data.get('job_id')) != pj['job_id'] or not data.get('title') or (not data.get('description')):
			raise ValueError('Existing capture does not match this project')
		if re.fullmatch('[a-f0-9]{64}', source.stem) and file_hash(source) != source.stem:
			raise ValueError('Immutable capture hash differs')
		state['stages']['capture'] = {'status': 'complete', 'time': now(), 'inputs': {}, 'outputs': hashes(root, [pj['snapshot']]), 'method': 'verified saved capture'}
	r = update(root, {'action': 'resume', 'reason': reason}, change)
	return r
# 2026-10-30 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
# https://github.com/dmitry-ai/harness/issues/43
def adopt_requests(root, conversation_id, *, allow_finalized=False, backend=None, platform=None):
	from .metrics import native_requests
	from .journal import answer_groups, resolve_journal_dir
	state = load(root)
	is_finalized = state.get('stages', {}).get('finalize', {}).get('status') == 'complete'
	if is_finalized and not allow_finalized:
		raise ValueError('Initial analysis finalize stage is already complete. Post-finalize questions do not require adopt-requests unless explicitly reopening analysis with --allow-finalized')
	requests = native_requests(root, conversation_id, backend=backend, platform=platform)
	req_ids = {x['id'] for x in requests}
	saved_answers = {}
	j_dir = resolve_journal_dir(root)
	for group in answer_groups(j_dir, request_ids=req_ids):
		for ident in group.get('request_ids') or []:
			saved_answers[ident] = {'turn': group['turn'], 'steps': group['steps'], 'sha256': group['response_sha256']}
	def change(state):
		recorded = {x['id']: x for x in state['requests'] if x.get('native_conversation_id')}
		incoming = {x['id'] for x in requests}
		exact_texts = {x['text'] for x in requests}
		state['requests'] = [x for x in state['requests'] if x['id'] not in incoming and (x.get('native_conversation_id') or x['text'] not in exact_texts)]
		for request in requests:
			prepared = saved_answers.get(request['id']) or recorded.get(request['id'], {}).get('response_prepared')
			state['requests'].append({**request, **({'response_prepared': prepared} if prepared else {})})
	r = update(root, {'action': 'adopt_requests', 'conversation_id': conversation_id}, change)
	return r
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate post-finalize turns from authorize gate, reset readiness state, and enable conflict journal recovery":
# https://github.com/dmitry-ai/harness/issues/43
def unadopt_requests(root, conversation_id=None, request_ids=None):
	req_ids = set(request_ids or [])
	if not conversation_id and not req_ids:
		raise ValueError('Provide --conversation or at least one --request-id to unadopt')
	def change(state):
		state['requests'] = [
			x for x in state.get('requests', [])
			if not ((conversation_id and x.get('native_conversation_id') == conversation_id) or (req_ids and x.get('id') in req_ids))
		]
	return update(root, {'action': 'unadopt_requests', 'conversation_id': conversation_id, 'request_ids': sorted(req_ids)}, change)
# 2026-10-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce CommonMark two-space hard line breaks (DOC-4), ban unsolicited bullet lists, and add PreToolUse hook check_markdown_slop.py":
# https://github.com/dmitry-ai/harness/issues/14
def doc4_sentence_issues(text):
	issues = []
	in_fence = False
	fence_marker = ''
	for lineno, raw_line in enumerate((text or '').splitlines(), 1):
		stripped = raw_line.strip()
		m_fence = re.match('^(`{3,}|~{3,})', stripped)
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
		cleaned = re.sub('`[^`]*`', 'code', stripped)
		cleaned = re.sub('\\[([^\\]]+)\\]\\([^)]+\\)', '\\1', cleaned)
		cleaned = re.sub('«[^»]*»', '«quote»', cleaned)
		cleaned = re.sub('\\b(?:\\u0433|\\u0433\\u0433|\\u0442\\.\\u0434|\\u0442\\.\\u043f|\\u0441\\u043c|\\u0438\\u043c|\\u0434\\u0440|\\u043f\\u0440|\\u0443\\u043b|\\u0434|\\u043a\\u0432|\\u0440\\u0438\\u0441|\\u0442\\u0430\\u0431\\u043b|\\u0441\\u0442|\\u043f|\\u0447|\\u0440\\u0443\\u0431|\\u0442\\u044b\\u0441|\\u043c\\u043b\\u043d|\\u043c\\u043b\\u0440\\u0434|\\u0430\\u043d\\u0433\\u043b|\\u0440\\u0443\\u0441|\\u043d\\u0430\\u043f\\u0440|\\u043e\\u043a|vs|Mr|Mrs|Ms|Dr|St|Inc|Ltd|Co|Jr|Sr|e\\.g|i\\.e)\\.', 'abbr', cleaned)
		is_bold_bullet = bool(re.match('^[-*]\\s+\\*\\*[^*]+\\*\\*', stripped))
		if is_bold_bullet and re.search('[A-Za-z\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451]{3,}[.!?]\\s+[A-Z\\u0410-\\u042f\\u0401][a-z\\u0430-\\u044f\\u0451]{2,}\\s+\\S+.*[.!?]\\s*$', cleaned):
			issues.append(f'DOC-4 violation on line {lineno}: multiple sentences on a single bullet line (place each sentence on its own line or use sub-bullets)')
		elif re.search('(?:[\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451A-Za-z0-9«»"(),:-]+\\s+){3,}[\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451A-Za-z]{3,}[.!?]\\s+[A-Z\\u0410-\\u042f\\u0401][a-z\\u0430-\\u044f\\u0451]{2,}\\s+[\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451A-Za-z0-9]+\\s+[\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451A-Za-z0-9]+', cleaned):
			issues.append(f'DOC-4 violation on line {lineno}: multiple sentences on a single line (place each sentence on its own line)')
	r = issues
	return r
def record_current_answer(root, response, *, journal_directory=None, request_ids=None, preauthorized=None, recorded_steps=None, turn_token=None):
	from .journal import record_answer, resolve_journal_dir
	from .links import readable_link_issues
	issues = readable_link_issues(response, allow_unencoded_file_uri=True)
	if issues:
		raise ValueError('\n'.join(issues))
	analysis_path = Path(root).resolve() / '\ua616/KB/Analysis.json'
	if analysis_path.is_file():
		try:
			analysis_val = json.loads(analysis_path.read_text(encoding='utf-8-sig'))
		except Exception:
			analysis_val = None
		if isinstance(analysis_val, dict) and [] == analysis_val.get('red_flags') and re.search('(?im)^\\s*#{1,6}\\s+Red Flags\\b', response):
			raise ValueError('Do not include a Red Flags heading in the response when Analysis.json red_flags is empty (INIT-5)')
	state = load(root)
	from .review import authorize
	filter_ids = set(request_ids) if None is not request_ids else None
	auth_kw = {'response': response, **({'request_ids': filter_ids} if None is not filter_ids else {})}
	approval = authorize(root, state, **auth_kw) if None is preauthorized else preauthorized
	unanswered = [x for x in state['requests'] if not x.get('response_prepared') and (None is filter_ids or x['id'] in filter_ids)]
	if not unanswered:
		raise ValueError('No unrecorded current requests; import exact native inputs or save the current request first')
	directory = resolve_journal_dir(root, journal_directory)
	if None is not recorded_steps:
		turn = turn_token or unanswered[-1]['id']
		steps = list(recorded_steps)
	else:
		turn = turn_token or unanswered[-1]['id']
		if not re.fullmatch('[A-Za-z0-9_-]{1,100}', turn):
			turn = 'native-' + hashlib.sha256(turn.encode('utf-8')).hexdigest()
		steps = record_answer(directory, [x['text'] for x in unanswered], response, turn, [x['id'] for x in unanswered], admission_roots=[root, directory])
	ids = {x['id'] for x in unanswered}
	resp_sha = hashlib.sha256(response.encode()).hexdigest()
	def change(locked_state):
		if locked_state != state:
			authorize(root, locked_state, package_path=approval['package'], **auth_kw)
		for request in locked_state['requests']:
			if request['id'] in ids:
				request['response_prepared'] = {'turn': turn, 'steps': steps, 'journal': str(directory), 'sha256': resp_sha, 'review_approval': approval}
	result = update(root, {'action': 'reply_prepared', 'turn': turn, 'steps': steps}, change)
	r = {**result, 'journal_steps': steps, 'delivery_verified': False}
	return r
# 2026-11-04 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope research questions to active turn, distinguish factual KB notes from hypotheses, and reconcile unprepared chat deliveries":
# https://github.com/dmitry-ai/harness/issues/44
def add_question(root, ident, question, impact, done_when, inputs, outputs, *, requirements=None):
	if not re.fullmatch('[A-Z][A-Z0-9-]*', ident) or not all((isinstance(x, str) and x.strip() for x in (question, impact, done_when))):
		raise ValueError('Question needs a stable ID, question, impact and completion criterion')
	if not inputs:
		raise ValueError('Declare at least the saved capture or relevant KB module as question input')
	from .experiments import requirement_issues
	issues = requirement_issues(requirements)
	if issues:
		raise ValueError('\n'.join(issues))
	input_hashes = hashes(root, inputs)
	permitted = [inside(root, path).relative_to(Path(root).resolve()).as_posix() for path in outputs]
	if not permitted or any((not p.startswith('ꘖ/') or p.startswith('ꘖ/data/workflow') for p in permitted)):
		raise ValueError('Declare exact project-owned outputs under ꘖ; not workflow state')
	def change(state):
		if ident in state['questions']:
			raise ValueError('Question already exists; use its saved inputs/results')
		state['questions'][ident] = {'id': ident, 'question': question, 'impact': impact, 'done_when': done_when, 'inputs': input_hashes, 'allowed_outputs': permitted, 'status': 'pending', 'owner': None, 'searches': [], 'results': {}, 'requirements': requirements, 'requirement_results': [], 'time': now()}
	r = update(root, {'action': 'question', 'question_id': ident}, change)
	return r
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
			if other['id'] != ident and other['owner'] and ('running' == other['status']) and set(other['allowed_outputs']) & set(q['allowed_outputs']):
				raise ValueError('Another active question owns the same output file')
		q.update(owner=owner, status='running')
	r = update(root, {'action': 'claim_question', 'question_id': ident, 'owner': owner}, change)
	return r
def handoff(root, ident, previous_owner, new_owner, reason):
	if not all((isinstance(s, str) and s.strip() for s in (previous_owner, new_owner, reason))):
		raise ValueError('Explicit previous owner, new owner and observed stopping reason required')
	def change(state):
		q = state['questions'][ident]
		if q['owner'] != previous_owner or 'running' != q['status']:
			raise ValueError('Task owner/status changed; refresh native progress before handoff')
		q.update(owner=new_owner, handoff_reason=reason)
	r = update(root, {'action': 'handoff', 'question_id': ident, 'reason': reason}, change)
	return r
def record_search(root, ident, owner, query, useful=False, method_change=None):
	if not isinstance(query, str) or not query.strip():
		raise ValueError('Search query required')
	def change(state):
		q = state['questions'][ident]
		if q['owner'] != owner or 'running' != q['status']:
			raise ValueError('Only current task owner can record searches')
		recent = []
		for attempt in reversed(q['searches']):
			recent.append(attempt)
			if attempt.get('method_change') or 3 == len(recent):
				break
		if 3 == len(recent) and all((not x['useful'] for x in recent)) and (not method_change):
			raise ValueError('Three unsuccessful searches: return a gap or document a different method before continuing')
		q['searches'].append({'query': ' '.join(query.casefold().split()), 'useful': bool(useful), 'method_change': method_change, 'time': now()})
	r = update(root, {'action': 'search', 'question_id': ident}, change)
	return r
def finish_question(root, ident, owner, outputs, gap=None, *, results=None):
	def change(state):
		q = state['questions'][ident]
		if q['owner'] != owner or 'running' != q['status']:
			raise ValueError('Only the current task owner may finish the question')
		if not all((inside(root, p).relative_to(Path(root).resolve()).as_posix() in q['allowed_outputs'] for p in outputs)):
			raise ValueError('Result was not among declared outputs')
		if hashes(root, list(q['inputs'])) != q['inputs']:
			raise ValueError('Question inputs changed; review the result against the new inputs')
		if not outputs or (None is not gap and (not gap.strip())):
			raise ValueError('A saved result/report and explicit gap explanation are required')
		candidate = {**q, 'gap': gap, 'requirement_results': results}
		issues = question_contract_issues(root, candidate)
		if issues:
			raise ValueError('\n'.join(issues))
		q.update(status='gap' if gap else 'complete', results=hashes(root, outputs), gap=gap, requirement_results=results)
	r = update(root, {'action': 'finish_question', 'question_id': ident}, change)
	return r
def kb_issues(root):
	from .links import validate_file
	issues = []
	for relative in kb_paths(root):
		file = inside(root, relative)
		if '.md' != file.suffix.lower() and '.md' != file.name:
			continue
		for error in validate_file(file, local_anchors=True, readable_links=True):
			issues.append(problem('kb.link', relative, error, file=file))
		text = file.read_text(encoding='utf-8')
		if re.search('(?im)^\\s*\\|.*\\|\\s*$\\n\\s*\\|?\\s*:?-{3,}', text) or re.search('(?i)<a\\s+[^>]*(?:name|id)\\s*=', text):
			issues.append(problem('kb.format', relative, 'Markdown tables or HTML anchors conflict with DOC-4/LINK-4', file=file))
		if 'Analysis.md' != file.name:
			for doc4_err in doc4_sentence_issues(text):
				issues.append(problem('kb.doc4_sentence', relative, doc4_err, file=file))
	r = issues
	return r
# 2026-10-17 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
# https://github.com/dmitry-ai/harness/issues/7
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
	for item in snap.get('asset_evidence') or []:
		rel = item.get('file')
		if rel and (kb_dir / rel).is_file():
			target = kb_dir / rel
			sha = item.get('sha256') or file_hash(target)
			if sha not in seen_sha:
				seen_sha.add(sha)
				attachments.append({'filename': target.name, 'sha256': sha, 'evidence_path': target})
	if att_root.is_dir():
		for sha_dir in sorted(att_root.iterdir()):
			if sha_dir.is_dir() and re.fullmatch('[0-9a-f]{64}', sha_dir.name):
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
					issues.append(problem('attachment.evidence_missing', f'source/{f.name}', f'Attached file in source/{f.name} is not synced to ꘖ/KB/Evidence/Attachments/{sha}/{f.name}; run sync-attachments', file=f))
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
			issues.append(problem('attachment.source_missing', f'source/{fname}', f'Attached file {fname} must be saved in the root source/ folder (§2.1); run sync-attachments', file=att['evidence_path']))
		kind = classify_attachment(fname, payload)
		if 'document' == kind:
			doc_md = extract_attachment_markdown(att['evidence_path'], payload)
			doc_markdowns.append(doc_md)
			heading_markers = (f'Description in `{fname}`', f'\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0432 `{fname}`')
			for label, target_file, target_text in (('KB/Project.md', manual_proj, manual_text), ('ꘖ/KB/Project.md', agent_proj, agent_text), ('ꘖ/KB/Projects.md', agent_projects, projects_text)):
				if not any((hm in target_text for hm in heading_markers)):
					issues.append(problem('attachment.kb_missing', label, f'Attached document {fname} is missing from {label} (§2.2); run sync-attachments', file=target_file))
		elif 'image' == kind:
			heading_markers = (f'Description in `{fname}`', f'\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0432 `{fname}`')
			for label, target_file, target_text in (('KB/Project.md', manual_proj, manual_text), ('ꘖ/KB/Project.md', agent_proj, agent_text), ('ꘖ/KB/Projects.md', agent_projects, projects_text)):
				matched_hm = next((hm for hm in heading_markers if hm in target_text), None)
				if not matched_hm:
					issues.append(problem('attachment.image_missing', label, f'Attached image {fname} must be transcribed and analyzed in {label} (§2.4)', file=target_file))
				else:
					sec_match = re.search(f'(?ms){re.escape(matched_hm)}.*?(?:~~~+|```+)markdown\\n(.*?)\\n(?:~~~+|```+)', target_text)
					sec_body = (sec_match.group(1) if sec_match else '').strip()
					if not sec_body or '«' not in sec_body or (not re.search('(?i)confirm|contradict|\\u043f\\u043e\\u0434\\u0442\\u0432\\u0435\\u0440\\u0436\\u0434\\u0435\\u043d\\u0438|\\u043f\\u0440\\u043e\\u0442\\u0438\\u0432\\u043e\\u0440\\u0435\\u0447\\u0438', sec_body)) or (not re.search('(?i)(?:score|\\u043e\\u0446\\u0435\\u043d\\u043a\\u0430).*\\d+\\s*%', sec_body)):
						issues.append(problem('attachment.image_incomplete', label, f'Attached image {fname} in {label} requires verbatim «...» text transcription, exhaustive UI description, and confirmation/contradiction analysis with % score (§2.4)', file=target_file))
	videos = detect_client_videos(snap.get('description') or '', doc_markdowns, [{'filename': a['filename'], 'sha256': a['sha256']} for a in attachments])
	for v in videos:
		v_heading = v['heading']
		for label, target_file, target_text in (('KB/Project.md', manual_proj, manual_text), ('ꘖ/KB/Project.md', agent_proj, agent_text), ('ꘖ/KB/Projects.md', agent_projects, projects_text)):
			if v_heading not in target_text:
				issues.append(problem('attachment.video_missing', label, f'Client video ({v_heading}) must be transcribed in {label} (§2.3)', file=target_file))
			elif '# Full Audio Transcript:' not in target_text and '# \u041f\u043e\u043b\u043d\u0430\u044f \u0440\u0430\u0441\u0448\u0438\u0444\u0440\u043e\u0432\u043a\u0430 \u0430\u0443\u0434\u0438\u043e\u0437\u0430\u043f\u0438\u0441\u0438:' not in target_text or not re.search('\\[\\d{2}:\\d{2}\\]', target_text):
				issues.append(problem('attachment.video_incomplete', label, f'Client video ({v_heading}) in {label} requires # Video:, # Key Spoken Commentary Points..., and # Full Audio Transcript: with [MM:SS] timestamps (§2.3)', file=target_file))
	return issues
def check_project(root):
	root = Path(root).resolve()
	issues = kb_issues(root) + attachment_issues(root)
	for folder in (root / 'ꘖ/data', root / '.agents'):
		if folder.is_dir():
			for script in sorted(folder.rglob('*')):
				if script.is_file() and script.suffix.lower() in ('.py', '.ps1', '.sh', '.bat', '.cmd'):
					issues.append(problem('project.one_off_script', script.relative_to(root).as_posix(), 'Executable one-off scripts are prohibited in project directories (FILE-5/EXEC-1); use shared upwork_project.py commands', file=script))
	from .links import readable_link_issues
	documents = [root / '.md', *sorted((root / 'result').rglob('*'))]
	for document in documents:
		if document.is_file() and 'draft.prev.md' != document.name and ('.md' == document.name or document.suffix.lower() in ('.md', '.markdown', '.txt', '.html', '.htm')):
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
				if value.get('schema_version') in (2, 3) and (not contract_issues):
					from .knowledge import sync_website_card
					website = sync_website_card(root, value, check=True)
					if website['status'] not in ('published', 'unchanged'):
						issues.append(problem('project.website', '.md', 'Publish the explicit evidenced client/target website selection, or null if unidentified', file=root / '.md'))
					established_identity = any((isinstance(c, dict) and ('verified' == c.get('verification_status') or (c.get('probability_percent') or 0) >= 80) and re.search('(?:client|author|artist|owner|customer|founder|\\u043a\\u043b\\u0438\\u0435\\u043d\\u0442|\\u0430\\u0432\\u0442\\u043e\\u0440|\\u0445\\u0443\\u0434\\u043e\\u0436\\u043d\\u0438\\u043a|\\u0432\\u043b\\u0430\\u0434\\u0435\\u043b\\u0435\\u0446|\\u0437\\u0430\\u043a\\u0430\\u0437\\u0447\\u0438\\u043a|\\u043e\\u0441\\u043d\\u043e\\u0432\\u0430\\u0442\\u0435\\u043b\\u044c)[^.]{0,40}?\\b[A-Z\\u0410-\\u042f\\u0401][a-z\\u0430-\\u044f\\u0451]{1,25}\\s+[A-Z\\u0410-\\u042f\\u0401][a-z\\u0430-\\u044f\\u0451]{1,25}\\b', c.get('essence') or '', re.IGNORECASE) for c in value.get('identity') or []))
					if established_identity:
						for rel_proj in ('KB/Project.md', 'ꘖ/KB/Project.md'):
							proj_file = root / rel_proj
							if proj_file.is_file():
								proj_txt = proj_file.read_text(encoding='utf-8')
								if re.search('#\\s*1\\.1\\s+(?:Name|\\u0418\\u043c\\u044f)\\s*\\r?\\n\\s*(?:unknown|\\u043d\\u0435\\u0438\\u0437\\u0432\\u0435\\u0441\\u0442\\u043d\\u043e)\\b', proj_txt, re.IGNORECASE):
									issues.append(problem('kb.identity_mismatch', rel_proj, f'Established client identity in Analysis.json is not synced to {rel_proj} (# 1.1 Name is still unknown)', file=proj_file))
		except (OSError, ValueError, TypeError) as exc:
			issues.append(problem('analysis.input', str(path), str(exc)))
	for issue in issues:
		if not issue.get('file'):
			issue['file'] = str(path)
	r = {'valid': not issues, 'issues': issues, 'semantic_truth_verified': False}
	return r
def record_review(root, report, *, parent_id, reviewer_id, role='AA', native_evidence=None, risk=None):
	from .review import record
	r = record(root, report, parent_id=parent_id, reviewer_id=reviewer_id, role=role, native_evidence=native_evidence, risk=risk)
	return r
def prepare_review(root, parent_id, spec=None, response=None):
	from .review import prepare
	r = prepare(root, parent_id, spec, response)
	return r
def review_input(root, package):
	from .review import input_receipt
	r = input_receipt(root, package)
	return r
def record_review_disposition(root, review_id, finding_id, status, basis, evidence, parent_id):
	from .review import disposition
	r = disposition(root, review_id, finding_id, status, basis, evidence, parent_id)
	return r
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
def complete_stage(root, stage, inputs, outputs, *, note=None):
	root = Path(root).resolve()
	if stage not in STAGES or not inputs or (not outputs):
		raise ValueError('Known stage and explicit nonempty input/output artifacts required')
	if stage in ('identity_init', 'finalize'):
		reg = registration_status(root)
		if reg['required'] and (not reg['all_registered']):
			from .registration import register_projects
			register_projects(root, platform=reg['platform'], targets=[reg['platform'], *reg['pending_targets']])
	in_hashes, out_hashes = (hashes(root, inputs), hashes(root, outputs))
	if set((*in_hashes, *out_hashes)) & {'ꘖ/data/workflow.json', 'ꘖ/data/rendered.json', 'ꘖ/KB/Progress.md'}:
		raise ValueError('Generated workflow/navigation state cannot serve as its own stage proof')
	def change(state):
		statuses = stage_statuses(root, state)
		preceding = STAGES[:STAGES.index(stage)]
		if any(('complete' != statuses[s] for s in preceding)):
			raise ValueError('Complete/check preceding stages before marking this stage complete')
		if 'identity_init' == stage and (not registration_status(root)['complete']):
			raise ValueError('Complete native project/folder registration in the current platform/profile first')
		if 'research' == stage:
			if not questions_current(root, state):
				raise ValueError('A research question is open or its inputs/results changed')
		if 'analysis' == stage:
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
		if 'kb_review' == stage and (not note):
			raise ValueError('Record the result of the semantic KB consistency review')
		if 'finalize' == stage:
			from .journal import get_existing_step_ids, resolve_journal_dir, step_errors
			from .text_workflow import gate_paths
			gate_paths([Path(root) / name for name in outputs])
			from .context import generate
			scratch_dir = Path(root) / 'ꘖ/data/scratch'
			if scratch_dir.is_dir() and any((p.is_file() for p in scratch_dir.rglob('*'))):
				raise ValueError('Clean or consume all temporary files in ꘖ/data/scratch before finalizing')
			prepared = state['requests'][-1].get('response_prepared', {}) if state['requests'] else {}
			journal = resolve_journal_dir(root, prepared.get('journal'))
			ids = get_existing_step_ids(journal)
			if not ids or any((step_errors(journal, ident) for ident in ids)):
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
			if any((not request.get('response_prepared') for request in state['requests'])) or not state['requests'] or state['requests'][-1]['response_prepared'].get('sha256') != approval['response_sha256']:
				raise ValueError('Record the exact approved answer for current requests before finalizing')
			target, _, _ = generate(Path(root), Path(root) / '.agents/context.json')
			out_hashes[target.relative_to(Path(root).resolve()).as_posix()] = file_hash(target)
		state['stages'][stage] = {'status': 'complete', 'time': now(), 'inputs': in_hashes, 'outputs': out_hashes, 'note': note}
		if 'finalize' == stage:
			state['stages'][stage]['request_ids'] = [request['id'] for request in state['requests']]
		if 'research' == stage:
			from copy import deepcopy
			state['stages'][stage]['research_questions'] = deepcopy(state['questions'])
		if stage in ('review', 'kb_review', 'finalize'):
			state['stages'][stage]['review_approval'] = approval
			state['stages'][stage]['kb_inputs'] = hashes(root, kb_paths(Path(root)))
			state['stages'][stage]['evidence_inputs'] = hashes(root, evidence_paths(root))
		for dependent in STAGES[STAGES.index(stage) + 1:]:
			if dependent in state['stages']:
				state['stages'][dependent].update(status='stale', invalidated_by=stage)
	r = update(root, {'action': 'complete_stage', 'stage': stage}, change)
	return r
