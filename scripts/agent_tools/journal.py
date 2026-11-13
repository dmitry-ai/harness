# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
# https://github.com/dmitry-ai/harness/issues/57
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate turn scratch answer files, decouple turn/journal locks, allow pre-delivery re-preparation, and add preemptive step/compaction budget gate":
# https://github.com/dmitry-ai/harness/issues/49
# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
# https://github.com/dmitry-ai/harness/issues/41
import hashlib
import json
from pathlib import Path
import re
import uuid
from .storage import create_bytes, data_dir_for, locked, replace_bytes
def digest(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()
def state_dir(directory: Path) -> Path:
	identity = str(Path(directory).resolve()).casefold()
	r = data_dir_for(directory) / '.journal' / digest(identity.encode('utf-8'))[:24]
	return r
def get_existing_step_ids(directory: Path) -> set[int]:
	directory = Path(directory)
	sources = [(directory / 'req', '.md'), (directory / 'res', '.md'), (state_dir(directory), '.json')]
	ids = {int(p.stem) for folder, suffix in sources if folder.exists() for p in folder.glob(f'*{suffix}') if p.stem.isascii() and p.stem.isdigit()}
	for _, group in iter_answer_group_records(directory):
		if group.get('journal') != str(directory.resolve()) or not isinstance(group.get('steps'), list) or any((int is not type(x) or 1 > x for x in group['steps'])):
			raise ValueError('Damaged answer-group reservation')
		ids.update(group['steps'])
	r = ids
	return r
def _payload(request: str, response: str):
	for label, text in [('request', request), ('response', response)]:
		if not isinstance(text, str) or not text.strip():
			raise ValueError(f'Empty {label}')
		text.encode('utf-8')
		if '�' in text or '/?/KB/' in text or '/?/data/' in text or ('\\?\\KB\\' in text) or ('\\?\\data\\' in text) or re.search('(?:^|[\\s*#(])(?:\\?{2,}\\s+){2,}\\?{2,}', text):
			raise ValueError(f'Corrupted UTF-8 {label} detected (PowerShell pipe OEM/ASCII "?" substitution or U+FFFD); write UTF-8 directly to ꘖ/data/scratch/answer.md via write_file or UTF8Encoding($false) and pass --response-file <path> --consume-input')
def _publish(directory: Path, step: int, state: dict, *, recovering=False):
	for folder, key in [('req', 'request'), ('res', 'response')]:
		path = directory / folder / f'{step}.md'
		data = state[key].encode('utf-8')
		if not path.exists():
			create_bytes(path, data)
		elif not recovering or path.read_bytes() != data:
			raise FileExistsError(f'Conflicting file; preserved without changes: {path}')
		if path.read_bytes() != data:
			raise OSError(f'Read-back mismatch: {path}')
	(state_dir(directory) / f'{step}.json').unlink(missing_ok=True)
# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
def record_step(journal_dir: Path, req_content: str, res_content: str, target_step: int | None=None, allow_overwrite: bool=False) -> int:
	_payload(req_content, res_content)
	if allow_overwrite:
		raise ValueError('Journal overwrite is unsupported; create a new corrective step')
	if None is not target_step and (type(target_step) is not int or target_step < 1):
		raise ValueError('Step must be a positive integer')
	directory = Path(journal_dir).resolve()
	from .text_workflow import gate_requests
	gate_requests([directory], [req_content], res_content)
	journal_state = state_dir(directory)
	for folder in (directory / 'req', directory / 'res', journal_state):
		folder.mkdir(parents=True, exist_ok=True)
	with locked(journal_state / 'writer.lock'):
		used = get_existing_step_ids(directory)
		step = target_step if None is not target_step else max(used, default=0) + 1
		if step in used:
			raise FileExistsError(f'Step {step} is occupied or reserved')
		state = {'version': 2, 'journal': str(directory), 'step': step, 'token': uuid.uuid4().hex, 'status': 'pending', 'request': req_content, 'response': res_content, 'request_sha256': digest(req_content.encode('utf-8')), 'response_sha256': digest(res_content.encode('utf-8'))}
		receipt = journal_state / f'{step}.json'
		create_bytes(receipt, json.dumps(state, ensure_ascii=False, indent=2).encode('utf-8'))
		try:
			_publish(directory, step, state)
		except Exception as exc:
			raise RuntimeError(f"Step {step} pending; recover with token {state['token']}: {exc}") from exc
		r = step
	return r
def recover_step(directory: Path, step: int, token: str):
	if step < 1:
		raise ValueError('Step must be positive')
	directory = Path(directory).resolve()
	journal_state = state_dir(directory)
	with locked(journal_state / 'writer.lock'):
		receipt = journal_state / f'{step}.json'
		state = json.loads(receipt.read_text(encoding='utf-8'))
		if state.get('journal') != str(directory) or state['token'] != token or state['step'] != step:
			raise ValueError('Reservation journal, token or step mismatch')
		_payload(state['request'], state['response'])
		for key in ('request', 'response'):
			if digest(state[key].encode('utf-8')) != state[key + '_sha256']:
				raise ValueError(f'Damaged reservation: {key}')
		_publish(directory, step, state, recovering=True)
def resolve_journal_dir(root: Path, selected=None) -> Path:
	root_p = Path(root).resolve()
	if selected:
		r = (root_p / selected).resolve()
	elif (root_p / '_/\ua66e').is_dir():
		r = (root_p / '_/\ua66e').resolve()
	elif (root_p / '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437').is_dir() and (not (root_p / '\ua66e/1 - Analysis').is_dir()):
		r = (root_p / '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437').resolve()
	elif (root_p / '\ua66e/README.md').is_file() and (not (root_p / '\ua66e/1 - Analysis').is_dir()):
		r = (root_p / '\ua66e').resolve()
	else:
		r = (root_p / '\ua66e/1 - Analysis').resolve()
	return r
def step_errors(directory: Path, step: int) -> list[str]:
	directory = Path(directory)
	if type(step) is not int or step < 1:
		r = ['Step must be a positive integer']
	else:
		errors = []
		for folder in ('req', 'res'):
			path = directory / folder / f'{step}.md'
			try:
				data = path.read_bytes()
				if not data.decode('utf-8').strip():
					errors.append(f'Empty file: {path}')
			except (OSError, UnicodeError) as exc:
				errors.append(f'{path}: {exc}')
		receipt = state_dir(directory) / f'{step}.json'
		if receipt.exists():
			errors.append(f'Incomplete reservation: {receipt}')
		r = errors
	return r
def validate_step(journal_dir, step_num) -> bool:
	errors = step_errors(Path(journal_dir), step_num)
	for error in errors:
		print(error)
	r = not errors
	return r
def verify_answer(directory, requests, response, turn, request_ids=None):
	if not re.fullmatch('[A-Za-z0-9_-]{1,100}', turn):
		raise ValueError('Stable answer-group identity required')
	directory = Path(directory).resolve()
	file = state_dir(directory) / 'answer-groups' / (turn + '.json')
	group = json.loads(file.read_text(encoding='utf-8'))
	if 'complete' != group.get('status') or group.get('journal') != str(directory) or group.get('turn') != turn or group.get('requests') != requests or group.get('request_ids') != request_ids or group.get('response_sha256') != digest(response.encode('utf-8')):
		raise ValueError('Historical answer-group identity changed; preserve it')
	steps = group.get('steps')
	if not isinstance(steps, list) or len(steps) != len(requests) or len(set(steps)) != len(steps) or any((int is not type(step) or 1 > step for step in steps)):
		raise ValueError('Historical answer-group steps changed')
	if not isinstance(group.get('tokens'), list) or len(group['tokens']) != len(steps) or any((not isinstance(token, str) or not token for token in group['tokens'])):
		raise ValueError('Historical answer-group reservation identity changed')
	for step, request in zip(steps, requests):
		if (state_dir(directory) / f'{step}.json').exists():
			raise ValueError('Completed historical answer has an incomplete reservation')
		for folder, expected in (('req', request), ('res', response)):
			if (directory / folder / f'{step}.md').read_bytes() != expected.encode('utf-8'):
				raise ValueError('Historical journal bytes changed; preserve them')
	return steps
def record_answer(directory, requests, response, turn, request_ids=None, *, adopt_steps=None, admission=None, admission_roots=None, allow_reprepare=False):
	if not re.fullmatch('[A-Za-z0-9_-]{1,100}', turn) or not isinstance(requests, list) or (not requests):
		raise ValueError('Stable turn ID and nonempty exact request list required')
	for request in requests:
		_payload(request, response)
	if None is not request_ids and (len(request_ids) != len(requests) or any((not isinstance(x, str) or not x for x in request_ids))):
		raise ValueError('Request IDs must match the exact request list')
	directory = Path(directory).resolve()
	from .admission import binding, capture, require_current
	identity = binding(directory, requests, response, turn, request_ids)
	roots = [Path(p).resolve() for p in (admission_roots or (directory,))]
	capability = capture(roots, requests, response, identity) if None is admission else admission
	proof = require_current(capability, identity)
	journal_state = state_dir(directory)
	groups = journal_state / 'answer-groups'
	for path in (directory / 'req', directory / 'res', groups):
		path.mkdir(parents=True, exist_ok=True)
	file = groups / (turn + '.json')
	with locked(journal_state / 'writer.lock'):
		if file.exists():
			group = json.loads(file.read_text(encoding='utf-8'))
			if group.get('journal') != str(directory) or group.get('requests') != requests or group.get('request_ids') != request_ids:
				raise ValueError('Answer group differs from its original journal/requests/response; preserve it')
			if group.get('response_sha256') != digest(response.encode()):
				if not allow_reprepare:
					raise ValueError('Answer group differs from its original journal/requests/response; preserve it')
				group['response_sha256'] = digest(response.encode())
				group['admission'] = proof
				group['status'] = 'pending'
				for st in group.get('steps') or []:
					res_file = directory / 'res' / f'{st}.md'
					if res_file.exists():
						replace_bytes(res_file, response.encode('utf-8'))
		else:
			if None is not adopt_steps:
				if not isinstance(adopt_steps, list) or len(adopt_steps) != len(requests) or any((int is not type(x) or 1 > x for x in adopt_steps)):
					raise ValueError('Adopted journal steps must match the exact request list')
				steps_to_use = list(adopt_steps)
			else:
				start = max(get_existing_step_ids(directory), default=0) + 1
				steps_to_use = list(range(start, start + len(requests)))
			group = {'version': 1, 'journal': str(directory), 'turn': turn, 'status': 'pending', 'steps': steps_to_use, 'requests': requests, 'response_sha256': digest(response.encode()), 'tokens': [uuid.uuid4().hex for _ in requests], 'request_ids': request_ids, 'admission': proof}
			create_bytes(file, json.dumps(group, ensure_ascii=False, indent=2).encode())
		for step, request, token in zip(group['steps'], requests, group['tokens']):
			receipt = journal_state / f'{step}.json'
			state = {'version': 2, 'journal': str(directory), 'step': step, 'token': token, 'status': 'pending', 'request': request, 'response': response, 'request_sha256': digest(request.encode()), 'response_sha256': digest(response.encode())}
			if 'complete' == group['status']:
				for sub, text in [('req', request), ('res', response)]:
					if (directory / sub / f'{step}.md').read_bytes() != text.encode():
						raise ValueError('Completed answer group changed; journal is preserved')
				continue
			if receipt.exists():
				saved = json.loads(receipt.read_text(encoding='utf-8'))
				if saved != state:
					raise ValueError('Reserved answer step belongs to another payload; preserved')
			else:
				req, res = (directory / 'req' / f'{step}.md', directory / 'res' / f'{step}.md')
				if req.exists() and res.exists():
					if req.read_bytes() == request.encode() and res.read_bytes() == response.encode():
						continue
					raise ValueError('Answer-group step is occupied; preserved')
				create_bytes(receipt, json.dumps(state, ensure_ascii=False, indent=2).encode())
			_publish(directory, step, state, recovering=True)
		if 'complete' != group['status']:
			group['status'] = 'complete'
			replace_bytes(file, json.dumps(group, ensure_ascii=False, indent=2).encode())
	r = group['steps']
	return r
def answer_groups(directory, *, request_ids=None):
	directory = Path(directory).resolve()
	filter_ids = set(request_ids) if None is not request_ids else None
	groups = []
	for _, group in iter_answer_group_records(directory):
		if None is not filter_ids and (not set(group.get('request_ids') or []) & filter_ids):
			continue
		if group.get('journal') != str(directory) or 'complete' != group.get('status'):
			raise ValueError('Incomplete or mismatched answer group; recover it before context export')
		for step, request in zip(group['steps'], group['requests']):
			req_path = directory / 'req' / f'{step}.md'
			res_path = directory / 'res' / f'{step}.md'
			if not req_path.is_file() or not res_path.is_file() or req_path.read_bytes() != request.encode() or (digest(res_path.read_bytes()) != group['response_sha256']):
				if None is not filter_ids:
					break
				raise ValueError('Answer group source bytes changed; preserve context')
		else:
			groups.append(group)
	r = groups
	return r
def completed_request_group_index(directory: Path) -> dict[str, tuple[dict, int]]:
	r: dict[str, tuple[dict, int]] = {}
	for _, group in iter_answer_group_records(directory, ignore_errors=True):
		if 'complete' == group.get('status') and group.get('request_ids'):
			for rid, st in zip(group['request_ids'], group.get('steps') or ()):
				r[rid] = (group, st)
	return r
def find_orphan_or_overwritten_steps(directory: Path, requests: list[str], response: str, native_ids: list[str]):
	directory = Path(directory).resolve()
	n = len(requests or [])
	req_dir, res_dir = (directory / 'req', directory / 'res')
	r = (None, None, None)
	if 0 < n and req_dir.is_dir() and res_dir.is_dir():
		norm_reqs = [norm_journal_text(req) for req in requests]
		norm_resp = norm_journal_text(response)
		claimed_by_step = {st: g_val for _, g_val in iter_answer_group_records(directory, ignore_errors=True) for st in (g_val.get('steps') or ()) if int is type(st)}
		pair_ids = sorted({int(p.stem) for p in req_dir.glob('*.md') if p.stem.isascii() and p.stem.isdigit() and (res_dir / p.name).is_file()})
		pair_set = set(pair_ids)
		overwritten_conflict = None
		j_state = state_dir(directory)
		for start in pair_ids:
			cand_steps = list(range(start, start + n))
			if not all((st in pair_set for st in cand_steps)):
				continue
			try:
				disk_reqs = [(req_dir / f'{st}.md').read_bytes().decode('utf-8') for st in cand_steps]
				disk_resps = [(res_dir / f'{st}.md').read_bytes().decode('utf-8') for st in cand_steps]
			except (OSError, UnicodeDecodeError):
				continue
			if 1 != len(set(disk_resps)) or [norm_journal_text(x) for x in disk_reqs] != norm_reqs or norm_journal_text(disk_resps[0]) != norm_resp:
				continue
			if all((st not in claimed_by_step and (not (j_state / f'{st}.json').exists()) for st in cand_steps)):
				r = (cand_steps, disk_reqs, disk_resps[0])
				overwritten_conflict = None
				break
			for st in cand_steps:
				owner = claimed_by_step.get(st)
				if owner and owner.get('request_ids') != native_ids:
					o_steps = owner.get('steps') or []
					o_reqs = owner.get('requests') or []
					matches_owner = o_steps == cand_steps and len(o_reqs) == len(cand_steps) and all((d_req == o_req for d_req, o_req in zip(disk_reqs, o_reqs))) and (digest(disk_resps[0].encode('utf-8')) == owner.get('response_sha256'))
					if not matches_owner and None is overwritten_conflict:
						overwritten_conflict = (cand_steps, owner.get('turn'))
		if None is not overwritten_conflict:
			c_steps, o_turn = overwritten_conflict
			raise ValueError(f'Journal step(s) {c_steps} match this native turn but are claimed by another answer group ({o_turn}); preserve the conflict')
	return r
def iter_answer_group_records(directory: Path, *, ignore_errors: bool=False) -> list[tuple[Path, dict]]:
	groups_dir = state_dir(Path(directory).resolve()) / 'answer-groups'
	r: list[tuple[Path, dict]] = []
	if groups_dir.is_dir():
		for path in sorted(groups_dir.glob('*.json')):
			try:
				val = json.loads(path.read_bytes().decode('utf-8'))
			except (OSError, UnicodeDecodeError, ValueError):
				if ignore_errors:
					continue
				raise
			if not isinstance(val, dict):
				if ignore_errors:
					continue
				raise ValueError('Completion metadata must be a JSON object: ' + str(path))
			r.append((path, val))
	return r
def matching_group_response(directory: Path, req_ids: list[str], response: str) -> str | None:
	directory = Path(directory).resolve()
	r = None
	for _, group in iter_answer_group_records(directory):
		if group.get('request_ids') == req_ids and group.get('steps'):
			res_path = directory / 'res' / f"{group['steps'][0]}.md"
			res_text = res_path.read_bytes().decode('utf-8') if res_path.is_file() else ''
			if res_text and norm_journal_text(res_text) == norm_journal_text(response):
				r = res_text
			break
	return r
def norm_journal_text(text: str) -> str:
	return strip_local_file_scheme((text or '').replace('\r\n', '\n'))
def strip_local_file_scheme(text: str) -> str:
	return re.sub('file:///+(?=[A-Za-z]:/)', '', text or '', flags=re.IGNORECASE).rstrip('\r\n ')
