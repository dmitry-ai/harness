# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Harden follow-up launcher handoff and journal reservation integrity":
# https://github.com/dmitry-ai/harness/issues/269
# "Add transactional rename-project command with automatic domain promotion":
# https://github.com/dmitry-ai/harness/issues/267
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Accelerate project_paths and overlay link resolution with fast-path caching":
# https://github.com/dmitry-ai/harness/issues/174
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prepend JSON metadata headers to new journal responses":
# https://github.com/dmitry-ai/harness/issues/151
# 2026-11-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Auto-name Antigravity conversations from project journal step numbers":
# https://github.com/dmitry-ai/harness/issues/120
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
# https://github.com/dmitry-ai/harness/issues/113
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement versioned 20-entry journal bucketing and journal-only upgrade engine":
# https://github.com/dmitry-ai/harness/issues/108
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
# https://github.com/dmitry-ai/harness/issues/101
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
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
import os
from pathlib import Path
import re
import uuid
from .storage import create_bytes, data_dir_for, journal_data_dir_for, locked, replace_bytes
V1_PAIR = ('req', 'res')
V2_PAIR = ('\u227b', '\u227a')
JOURNAL_BUCKET_SIZE = 20
JOURNAL_RANGE_SEP = '\u2013'
TURN_RESERVATIONS_FILE = 'turn-reservations.json'
_BUCKET_DIR_RE = re.compile('^(\\d+)[-\\u2013](\\d+)$')
_LEGACY_ANALYSIS_NAMES = ('1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437')
def digest(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()
def is_bucket_dir_name(name: str) -> bool:
	return bool(_BUCKET_DIR_RE.fullmatch(str(name or '')))
def journal_bucket_bounds(step: int, bucket_size: int=JOURNAL_BUCKET_SIZE) -> tuple[int, int]:
	if int is not type(step) or 1 > step:
		raise ValueError('Step must be a positive integer')
	start = ((step - 1) // bucket_size) * bucket_size + 1
	return (start, start + bucket_size - 1)
def journal_bucket_name(step: int, bucket_size: int=JOURNAL_BUCKET_SIZE) -> str:
	start, end = journal_bucket_bounds(step, bucket_size)
	return f'{start}{JOURNAL_RANGE_SEP}{end}'
def _is_step_md(path: Path) -> bool:
	return path.is_file() and '.md' == path.suffix.lower() and path.stem.isascii() and path.stem.isdigit() and 1 <= int(path.stem)
def iter_side_step_files(side_dir: Path) -> list[tuple[int, Path]]:
	side_p = Path(side_dir)
	if not side_p.is_dir():
		return []
	found: dict[int, Path] = {}
	for child in sorted(side_p.iterdir(), key=lambda p: p.name):
		if _is_step_md(child):
			st = int(child.stem)
			found[st] = child
		elif child.is_dir() and is_bucket_dir_name(child.name):
			for sub_f in sorted(child.iterdir(), key=lambda p: p.name):
				if _is_step_md(sub_f):
					st = int(sub_f.stem)
					if st in found and found[st].read_bytes() != sub_f.read_bytes():
						raise ValueError(f'Conflicting duplicate journal step {st} in {side_p}: {found[st]} vs {sub_f}')
					if st not in found or child.name == journal_bucket_name(st):
						found[st] = sub_f
	return sorted(found.items(), key=lambda item: item[0])
def find_step_file(side_dir: Path, step: int) -> Path | None:
	if int is not type(step) or 1 > step:
		return None
	side_p = Path(side_dir)
	if not side_p.is_dir():
		return None
	canon = side_p / journal_bucket_name(step) / f'{step}.md'
	if canon.is_file():
		return canon
	flat = side_p / f'{step}.md'
	if flat.is_file():
		return flat
	target_name = f'{step}.md'
	for child in sorted(side_p.iterdir(), key=lambda p: p.name):
		if child.is_dir() and is_bucket_dir_name(child.name):
			cand = child / target_name
			if cand.is_file():
				return cand
	return None
def canonicalize_journal_dir_identity(journal_path: str | Path) -> Path:
	p = Path(journal_path).resolve()
	if p.is_dir():
		return p
	if '\ua66e' == p.parent.name and p.name in _LEGACY_ANALYSIS_NAMES and ((p.parent / V2_PAIR[0]).is_dir() or (p.parent / V2_PAIR[1]).is_dir()):
		return p.parent.resolve()
	cand_proj_root = None
	if '\ua66e' == p.parent.name and p.name in _LEGACY_ANALYSIS_NAMES:
		cand_proj_root = p.parent.parent
	elif '_' == p.parent.name and '\ua66e' == p.name:
		cand_proj_root = p.parent.parent
	elif '\ua66e' == p.name:
		cand_proj_root = p.parent
	if None is not cand_proj_root:
		from .path_registry import canonicalize_root_dir, project_paths
		try:
			canon_root = canonicalize_root_dir(cand_proj_root)
			if canon_root.is_dir():
				pp = project_paths(canon_root, exact_root=True)
				if canon_root != cand_proj_root.resolve() or 2 <= pp.fs_version:
					if pp.journal_dir.is_dir():
						return pp.journal_dir.resolve()
		except (OSError, ValueError):
			pass
	return p
def same_journal_identity(first: str | Path | None, second: str | Path | None) -> bool:
	from .project_rename_state import same_journal_identity_with_rename
	return same_journal_identity_with_rename(first, second, canonicalize_journal_dir_identity)
def journal_pair_names(directory: Path) -> tuple[str, str]:
	directory = Path(directory)
	has_v2 = (directory / V2_PAIR[0]).is_dir() or (directory / V2_PAIR[1]).is_dir()
	has_v1 = (directory / V1_PAIR[0]).is_dir() or (directory / V1_PAIR[1]).is_dir()
	if has_v2 and has_v1:
		v2_files = any((bool(iter_side_step_files(directory / sub)) for sub in V2_PAIR if (directory / sub).is_dir()))
		v1_files = any((bool(iter_side_step_files(directory / sub)) for sub in V1_PAIR if (directory / sub).is_dir()))
		if v2_files and v1_files:
			raise ValueError(f'Conflicting V1 (req/res) and V2 (\u227b/\u227a) journal entries in {directory}')
		return V2_PAIR if v2_files or (not v1_files) else V1_PAIR
	if has_v2:
		return V2_PAIR
	if has_v1 or directory.name in _LEGACY_ANALYSIS_NAMES:
		return V1_PAIR
	if '\ua66e' == directory.name:
		return V2_PAIR
	from .path_registry import project_paths
	try:
		pp = project_paths(directory)
		if 2 <= pp.fs_version or (directory.resolve() == pp.journal_dir.resolve() and 2 <= pp.journal_version):
			return V2_PAIR
	except (OSError, ValueError):
		pass
	return V1_PAIR
def detect_journal_version(directory: Path) -> int:
	d = Path(directory)
	pair = journal_pair_names(d)
	if V1_PAIR == pair:
		return 1
	for side_name in V2_PAIR:
		side_p = d / side_name
		if not side_p.is_dir():
			continue
		for child in side_p.iterdir():
			if _is_step_md(child):
				return 2
			if child.is_dir() and is_bucket_dir_name(child.name):
				b_steps = [int(bf.stem) for bf in child.iterdir() if _is_step_md(bf)]
				if not b_steps or any((child.name != journal_bucket_name(st) for st in b_steps)):
					return 2
	return 3
def journal_pair_dirs(directory: Path) -> tuple[Path, Path]:
	d = Path(directory)
	req_name, res_name = journal_pair_names(d)
	return (d / req_name, d / res_name)
def step_file(side_dir: Path, step: int, *, directory: Path | None=None) -> Path:
	side_p = Path(side_dir)
	found = find_step_file(side_p, step)
	if None is not found:
		return found
	eff_dir = Path(directory) if None is not directory else side_p.parent
	if 3 <= detect_journal_version(eff_dir):
		return side_p / journal_bucket_name(step) / f'{step}.md'
	return side_p / f'{step}.md'
def parse_step_file_path(path: str | Path) -> tuple[Path, str, int] | None:
	p = Path(path)
	if '.md' != p.suffix.lower() or (not p.stem.isascii()) or (not p.stem.isdigit()):
		return None
	step = int(p.stem)
	if 1 > step:
		return None
	parent = p.parent
	if parent.name in (*V1_PAIR, *V2_PAIR):
		return (parent.parent, parent.name, step)
	if is_bucket_dir_name(parent.name) and parent.parent.name in (*V1_PAIR, *V2_PAIR):
		return (parent.parent.parent, parent.parent.name, step)
	return None
def resolve_migrated_step_file(path: str | Path) -> Path:
	p = Path(path)
	if p.is_file():
		return p.resolve()
	parsed = parse_step_file_path(p)
	if None is parsed:
		return p
	old_jdir, old_side, step = parsed
	eff_jdir = canonicalize_journal_dir_identity(old_jdir)
	if not eff_jdir.is_dir():
		return p
	try:
		req_dir, res_dir = journal_pair_dirs(eff_jdir)
	except ValueError:
		return p
	target_side = req_dir if old_side in ('req', '\u227b') else res_dir
	found = find_step_file(target_side, step)
	return found.resolve() if None is not found else p
def _raw_state_dir(eff: Path, *, data_root: Path | None=None) -> Path:
	identity = str(eff.resolve()).casefold()
	base = Path(data_root) if None is not data_root else journal_data_dir_for(eff)
	return base / '.journal' / digest(identity.encode('utf-8'))[:24]
def state_dir(directory: Path) -> Path:
	eff = canonicalize_journal_dir_identity(directory)
	return _raw_state_dir(eff)
def get_existing_step_ids(directory: Path) -> set[int]:
	directory = Path(directory)
	req_dir, res_dir = journal_pair_dirs(directory)
	ids = {st for side in (req_dir, res_dir) for st, _ in iter_side_step_files(side)}
	s_dir = state_dir(directory)
	if s_dir.exists():
		ids.update((int(p.stem) for p in s_dir.glob('*.json') if p.stem.isascii() and p.stem.isdigit()))
	for _, group in iter_answer_group_records(directory):
		if not same_journal_identity(group.get('journal'), directory.resolve()) or not isinstance(group.get('steps'), list) or any((int is not type(x) or 1 > x for x in group['steps'])):
			raise ValueError('Damaged answer-group reservation')
		ids.update(group['steps'])
	return ids
def _read_turn_reservations(directory: Path) -> dict[str, dict]:
	res_file = state_dir(Path(directory).resolve()) / TURN_RESERVATIONS_FILE
	if not res_file.is_file():
		return {}
	try:
		raw = json.loads(res_file.read_bytes().decode('utf-8'))
	except (OSError, UnicodeDecodeError, ValueError):
		return {}
	if not isinstance(raw, dict) or not isinstance(raw.get('reservations'), dict):
		return {}
	out: dict[str, dict] = {}
	for key, entry in raw['reservations'].items():
		if not isinstance(key, str) or not key.strip() or not isinstance(entry, dict):
			continue
		steps = [st for st in (entry.get('steps') or ()) if int is type(st) and 1 <= st]
		if not steps:
			continue
		rids = [str(rid) for rid in (entry.get('request_ids') or ()) if isinstance(rid, str) and rid]
		out[key] = {'conversation_id': str(entry.get('conversation_id') or ''), 'request_ids': rids, 'steps': steps}
	return out
def _write_turn_reservations(directory: Path, reservations: dict[str, dict]) -> None:
	eff = Path(directory).resolve()
	res_file = state_dir(eff) / TURN_RESERVATIONS_FILE
	if not reservations:
		res_file.unlink(missing_ok=True)
		return
	payload = (json.dumps({'version': 1, 'journal': str(eff), 'reservations': reservations}, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
	if res_file.is_file():
		try:
			if res_file.read_bytes() == payload:
				return
		except OSError:
			pass
	res_file.parent.mkdir(parents=True, exist_ok=True)
	replace_bytes(res_file, payload)
def iter_turn_reservations(directory: Path) -> dict[str, dict]:
	return _read_turn_reservations(directory)
def reserved_step_ids(directory: Path, *, exclude_turn: str | None=None) -> set[int]:
	r: set[int] = set()
	for key, entry in _read_turn_reservations(directory).items():
		if None is not exclude_turn and key == exclude_turn:
			continue
		r.update((st for st in (entry.get('steps') or ()) if int is type(st) and 1 <= st))
	return r
def reserve_turn_steps(directory: Path, turn_key: str, conversation_id: str, request_ids: list[str]) -> list[int]:
	if not isinstance(turn_key, str) or not turn_key.strip() or not isinstance(request_ids, list) or (not request_ids) or any((not isinstance(x, str) or not x for x in request_ids)):
		raise ValueError('Stable turn key and nonempty exact request ID list required for step reservation')
	eff = Path(directory).resolve()
	journal_state = state_dir(eff)
	journal_state.mkdir(parents=True, exist_ok=True)
	with locked(journal_state / 'writer.lock'):
		committed_index = completed_request_group_index(eff)
		existing_ids = get_existing_step_ids(eff)
		reservations = _read_turn_reservations(eff)
		old_entry = reservations.get(turn_key) if isinstance(reservations.get(turn_key), dict) else {}
		old_map = {rid: st for rid, st in zip(old_entry.get('request_ids') or (), old_entry.get('steps') or ()) if isinstance(rid, str) and int is type(st) and 1 <= st}
		other_reserved = {st for k, e in reservations.items() if k != turn_key for st in (e.get('steps') or ()) if int is type(st) and 1 <= st}
		assigned: list[int] = []
		assigned_set: set[int] = set()
		all_committed = True
		for rid in request_ids:
			if rid in committed_index:
				st = int(committed_index[rid][1])
				assigned.append(st)
				assigned_set.add(st)
			else:
				all_committed = False
				prev = old_map.get(rid)
				if None is not prev and prev not in existing_ids and prev not in other_reserved and prev not in assigned_set:
					st = prev
				else:
					st = max(existing_ids | other_reserved | assigned_set, default=0) + 1
				assigned.append(st)
				assigned_set.add(st)
		if all_committed:
			if turn_key in reservations:
				del reservations[turn_key]
				_write_turn_reservations(eff, reservations)
		else:
			new_entry = {'conversation_id': str(conversation_id or ''), 'request_ids': list(request_ids), 'steps': list(assigned)}
			if old_entry != new_entry:
				reservations[turn_key] = new_entry
				_write_turn_reservations(eff, reservations)
		return assigned
def release_turn_steps(directory: Path, turn_key: str, *, request_ids: list[str] | None=None) -> bool:
	eff = Path(directory).resolve()
	journal_state = state_dir(eff)
	if not (journal_state / TURN_RESERVATIONS_FILE).is_file():
		return False
	with locked(journal_state / 'writer.lock'):
		from .journal_integrity import prune_overlapping_reservations
		reservations = _read_turn_reservations(eff)
		removed = prune_overlapping_reservations(reservations, turn_key, set(request_ids or ()), set())
		if removed:
			_write_turn_reservations(eff, reservations)
		return removed
def _payload(request: str, response: str):
	for label, text in [('request', request), ('response', response)]:
		if not isinstance(text, str) or not text.strip():
			raise ValueError(f'Empty {label}')
		text.encode('utf-8')
		if '\ufffd' in text or '/?/KB/' in text or '/?/data/' in text or ('\\?\\KB\\' in text) or ('\\?\\data\\' in text) or re.search('(?:^|[\\s*#(])(?:\\?{2,}\\s+){2,}\\?{2,}', text):
			raise ValueError(f'Corrupted UTF-8 {label} detected (PowerShell pipe OEM/ASCII "?" substitution or U+FFFD); write UTF-8 directly to \ua616/data/scratch/answer.md via write_file or UTF8Encoding($false) and pass --response-file <path> --consume-input')
def _publish(directory: Path, step: int, state: dict, *, recovering=False):
	req_dir, res_dir = journal_pair_dirs(directory)
	for folder_dir, key in [(req_dir, 'request'), (res_dir, 'response')]:
		path = step_file(folder_dir, step, directory=directory)
		data = state[key].encode('utf-8')
		path.parent.mkdir(parents=True, exist_ok=True)
		if not path.exists():
			create_bytes(path, data)
		elif not recovering or path.read_bytes() != data:
			raise FileExistsError(f'Conflicting file; preserved without changes: {path}')
		if path.read_bytes() != data:
			raise OSError(f'Read-back mismatch: {path}')
	(state_dir(directory) / f'{step}.json').unlink(missing_ok=True)
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
	req_dir, res_dir = journal_pair_dirs(directory)
	for folder in (req_dir, res_dir, journal_state):
		folder.mkdir(parents=True, exist_ok=True)
	with locked(journal_state / 'writer.lock'):
		used = get_existing_step_ids(directory) | reserved_step_ids(directory)
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
		if not same_journal_identity(state.get('journal'), directory) or state['token'] != token or state['step'] != step:
			raise ValueError('Reservation journal, token or step mismatch')
		_payload(state['request'], state['response'])
		for key in ('request', 'response'):
			if digest(state[key].encode('utf-8')) != state[key + '_sha256']:
				raise ValueError(f'Damaged reservation: {key}')
		_publish(directory, step, state, recovering=True)
def resolve_journal_dir(root: Path, selected=None) -> Path:
	from .path_registry import project_paths
	root_p = Path(root).resolve()
	pp = project_paths(root_p, exact_root=True)
	if selected:
		sel_str = pp.expand(str(selected)) if '${' in str(selected) else str(selected)
		r = canonicalize_journal_dir_identity((pp.root / sel_str).resolve())
	else:
		r = pp.journal_dir.resolve()
	return r
def step_errors(directory: Path, step: int) -> list[str]:
	directory = Path(directory)
	if type(step) is not int or step < 1:
		r = ['Step must be a positive integer']
	else:
		errors = []
		req_dir, res_dir = journal_pair_dirs(directory)
		for folder_dir in (req_dir, res_dir):
			path = step_file(folder_dir, step, directory=directory)
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
	if 'complete' != group.get('status') or (not same_journal_identity(group.get('journal'), directory)) or group.get('turn') != turn or group.get('requests') != requests or group.get('request_ids') != request_ids or group.get('response_sha256') != digest(response.encode('utf-8')):
		raise ValueError('Historical answer-group identity changed; preserve it')
	steps = group.get('steps')
	if not isinstance(steps, list) or len(steps) != len(requests) or len(set(steps)) != len(steps) or any((int is not type(step) or 1 > step for step in steps)):
		raise ValueError('Historical answer-group steps changed')
	if not isinstance(group.get('tokens'), list) or len(group['tokens']) != len(steps) or any((not isinstance(token, str) or not token for token in group['tokens'])):
		raise ValueError('Historical answer-group reservation identity changed')
	req_dir, res_dir = journal_pair_dirs(directory)
	for step, request in zip(steps, requests):
		if (state_dir(directory) / f'{step}.json').exists():
			raise ValueError('Completed historical answer has an incomplete reservation')
		for folder_dir, expected in ((req_dir, request), (res_dir, response)):
			if step_file(folder_dir, step, directory=directory).read_bytes() != expected.encode('utf-8'):
				raise ValueError('Historical journal bytes changed; preserve them')
	return steps
def record_answer(directory, requests, response, turn, request_ids=None, *, adopt_steps=None, admission=None, admission_roots=None, allow_reprepare=False, reserved_turn_key=None):
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
	req_dir, res_dir = journal_pair_dirs(directory)
	for path in (req_dir, res_dir, groups):
		path.mkdir(parents=True, exist_ok=True)
	file = groups / (turn + '.json')
	eff_res_key = reserved_turn_key if None is not reserved_turn_key else (turn[7:] if turn.startswith('native-') else turn)
	with locked(journal_state / 'writer.lock'):
		if file.exists():
			group = json.loads(file.read_text(encoding='utf-8'))
			if not same_journal_identity(group.get('journal'), directory) or group.get('requests') != requests or group.get('request_ids') != request_ids:
				raise ValueError('Answer group differs from its original journal/requests/response; preserve it')
			if group.get('response_sha256') != digest(response.encode()):
				if not allow_reprepare:
					raise ValueError('Answer group differs from its original journal/requests/response; preserve it')
				group['response_sha256'] = digest(response.encode())
				group['admission'] = proof
				group['status'] = 'pending'
				for st in group.get('steps') or []:
					res_file = step_file(res_dir, st, directory=directory)
					if res_file.exists():
						replace_bytes(res_file, response.encode('utf-8'))
		else:
			if None is not adopt_steps:
				if not isinstance(adopt_steps, list) or len(adopt_steps) != len(requests) or any((int is not type(x) or 1 > x for x in adopt_steps)):
					raise ValueError('Adopted journal steps must match the exact request list')
				steps_to_use = list(adopt_steps)
			else:
				existing_ids = get_existing_step_ids(directory)
				reservations = _read_turn_reservations(directory)
				cand_entry = reservations.get(eff_res_key)
				if None is cand_entry and None is not request_ids:
					cand_entry = next((e for e in reservations.values() if e.get('request_ids') == request_ids), None)
				cand_steps = list(cand_entry.get('steps') or ()) if isinstance(cand_entry, dict) else []
				cand_rids = cand_entry.get('request_ids') if isinstance(cand_entry, dict) else None
				if cand_steps and len(cand_steps) == len(requests) and len(set(cand_steps)) == len(cand_steps) and all((int is type(x) and 1 <= x and x not in existing_ids for x in cand_steps)) and (None is request_ids or cand_rids == request_ids):
					steps_to_use = cand_steps
				else:
					used = existing_ids | reserved_step_ids(directory, exclude_turn=eff_res_key)
					start = max(used, default=0) + 1
					steps_to_use = list(range(start, start + len(requests)))
			group = {'version': 1, 'journal': str(directory), 'turn': turn, 'status': 'pending', 'steps': steps_to_use, 'requests': requests, 'response_sha256': digest(response.encode()), 'tokens': [uuid.uuid4().hex for _ in requests], 'request_ids': request_ids, 'admission': proof}
			create_bytes(file, json.dumps(group, ensure_ascii=False, indent=2).encode())
		for step, request, token in zip(group['steps'], requests, group['tokens']):
			receipt = journal_state / f'{step}.json'
			state = {'version': 2, 'journal': str(directory), 'step': step, 'token': token, 'status': 'pending', 'request': request, 'response': response, 'request_sha256': digest(request.encode()), 'response_sha256': digest(response.encode())}
			if 'complete' == group['status']:
				for folder_dir, text in [(req_dir, request), (res_dir, response)]:
					if step_file(folder_dir, step, directory=directory).read_bytes() != text.encode():
						raise ValueError('Completed answer group changed; journal is preserved')
				continue
			if receipt.exists():
				saved = json.loads(receipt.read_text(encoding='utf-8'))
				if saved != state:
					raise ValueError('Reserved answer step belongs to another payload; preserved')
			else:
				req, res = (step_file(req_dir, step, directory=directory), step_file(res_dir, step, directory=directory))
				if req.exists() and res.exists():
					if req.read_bytes() == request.encode() and res.read_bytes() == response.encode():
						continue
					raise ValueError('Answer-group step is occupied; preserved')
				create_bytes(receipt, json.dumps(state, ensure_ascii=False, indent=2).encode())
			_publish(directory, step, state, recovering=True)
		if 'complete' != group['status']:
			group['status'] = 'complete'
			replace_bytes(file, json.dumps(group, ensure_ascii=False, indent=2).encode())
		if (journal_state / TURN_RESERVATIONS_FILE).is_file():
			from .journal_integrity import prune_overlapping_reservations
			reservations = _read_turn_reservations(directory)
			if prune_overlapping_reservations(reservations, eff_res_key, set(request_ids or ()), set(group.get('steps') or ())):
				_write_turn_reservations(directory, reservations)
	r = group['steps']
	return r
def answer_groups(directory, *, request_ids=None):
	directory = Path(directory).resolve()
	req_dir, res_dir = journal_pair_dirs(directory)
	filter_ids = set(request_ids) if None is not request_ids else None
	groups = []
	for _, group in iter_answer_group_records(directory):
		if None is not filter_ids and (not set(group.get('request_ids') or []) & filter_ids):
			continue
		if not same_journal_identity(group.get('journal'), directory) or 'complete' != group.get('status'):
			raise ValueError('Incomplete or mismatched answer group; recover it before context export')
		for step, request in zip(group['steps'], group['requests']):
			req_path = step_file(req_dir, step, directory=directory)
			res_path = step_file(res_dir, step, directory=directory)
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
	req_dir, res_dir = journal_pair_dirs(directory)
	r = (None, None, None)
	if 0 < n and req_dir.is_dir() and res_dir.is_dir():
		norm_reqs = [norm_journal_text(req) for req in requests]
		norm_resp = norm_journal_response_text(response)
		claimed_by_step = {st: g_val for _, g_val in iter_answer_group_records(directory, ignore_errors=True) for st in (g_val.get('steps') or ()) if int is type(st)}
		req_map = dict(iter_side_step_files(req_dir))
		res_map = dict(iter_side_step_files(res_dir))
		pair_ids = sorted(set(req_map) & set(res_map))
		pair_set = set(pair_ids)
		overwritten_conflict = None
		j_state = state_dir(directory)
		for start in pair_ids:
			cand_steps = list(range(start, start + n))
			if not all((st in pair_set for st in cand_steps)):
				continue
			try:
				disk_reqs = [req_map[st].read_bytes().decode('utf-8') for st in cand_steps]
				disk_resps = [res_map[st].read_bytes().decode('utf-8') for st in cand_steps]
			except (OSError, UnicodeDecodeError):
				continue
			if 1 != len(set(disk_resps)) or [norm_journal_text(x) for x in disk_reqs] != norm_reqs or norm_journal_response_text(disk_resps[0]) != norm_resp:
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
	_, res_dir = journal_pair_dirs(directory)
	r = None
	for _, group in iter_answer_group_records(directory):
		if group.get('request_ids') == req_ids and group.get('steps'):
			res_path = step_file(res_dir, group['steps'][0], directory=directory)
			res_text = res_path.read_bytes().decode('utf-8') if res_path.is_file() else ''
			if res_text and norm_journal_response_text(res_text) == norm_journal_response_text(response):
				r = res_text
			break
	return r
def norm_journal_text(text: str) -> str:
	return strip_local_file_scheme((text or '').replace('\r\n', '\n'))
def norm_journal_response_text(text: str) -> str:
	from .metadata import strip_leading_metadata_header
	return norm_journal_text(strip_leading_metadata_header(text or ''))
def strip_local_file_scheme(text: str) -> str:
	return re.sub('file:///+(?=[A-Za-z]:/)', '', text or '', flags=re.IGNORECASE).rstrip('\r\n ')
def _assert_not_linked_tree(path: Path) -> None:
	for cur in (path, *path.parents):
		try:
			if os.path.lexists(cur) and (cur.is_symlink() or cur.is_junction()):
				raise ValueError(f'Linked journal path refused: {cur}')
		except OSError:
			pass
		if cur.parent == cur:
			break
def _discover_upgrade_units(j_root: Path) -> list[tuple[Path, Path]]:
	has_direct = any(((j_root / n).is_dir() for n in (*V1_PAIR, *V2_PAIR)))
	subjournals: list[Path] = []
	for child in sorted(j_root.iterdir(), key=lambda p: p.name):
		if child.is_dir() and child.name not in (*V1_PAIR, *V2_PAIR, 'source', '0', '0 - Context', '1 - Context') and (not is_bucket_dir_name(child.name)):
			if any(((child / n).is_dir() for n in (*V1_PAIR, *V2_PAIR))):
				subjournals.append(child)
	if 1 == len(subjournals) and (not has_direct) and subjournals[0].name in _LEGACY_ANALYSIS_NAMES:
		return [(subjournals[0], j_root)]
	if subjournals and (not has_direct):
		return [(sub, sub) for sub in subjournals]
	return [(j_root, j_root)]
def _collect_side_sources(src_jdir: Path, side_names: tuple[str, ...]) -> list[tuple[int, Path]]:
	entries: list[tuple[int, Path]] = []
	by_step: dict[int, Path] = {}
	for s_name in side_names:
		s_dir = src_jdir / s_name
		if not s_dir.is_dir():
			continue
		for child in sorted(s_dir.iterdir(), key=lambda p: p.name):
			if _is_step_md(child):
				st = int(child.stem)
				if st in by_step and by_step[st].read_bytes() != child.read_bytes():
					raise FileExistsError(f'Conflicting duplicate step {st} during journal upgrade: {by_step[st]} vs {child}')
				by_step.setdefault(st, child)
				entries.append((st, child))
			elif child.is_dir() and is_bucket_dir_name(child.name):
				for bf in sorted(child.iterdir(), key=lambda p: p.name):
					if _is_step_md(bf):
						st = int(bf.stem)
						if st in by_step and by_step[st].read_bytes() != bf.read_bytes():
							raise FileExistsError(f'Conflicting duplicate step {st} during journal upgrade: {by_step[st]} vs {bf}')
						by_step.setdefault(st, bf)
						entries.append((st, bf))
	return entries
def _rewrite_journal_readme(readme_path: Path) -> bool:
	if not readme_path.is_file():
		return False
	orig = readme_path.read_text(encoding='utf-8')
	updated = orig.replace('{req,res}', '{\u227b,\u227a}')
	def _rep_req(m: re.Match) -> str:
		st = int(m.group(1))
		return f'(\u227b/{journal_bucket_name(st)}/{st}.md)'
	def _rep_res(m: re.Match) -> str:
		st = int(m.group(1))
		return f'(\u227a/{journal_bucket_name(st)}/{st}.md)'
	updated = re.sub('\\((?:req|\\u227b)/(\\d+)\\.md\\)', _rep_req, updated)
	updated = re.sub('\\((?:res|\\u227a)/(\\d+)\\.md\\)', _rep_res, updated)
	if updated != orig:
		replace_bytes(readme_path, updated.encode('utf-8'))
		return True
	return False
def _migrate_journal_state_dir(src_jdir: Path, dst_jdir: Path, data_root: Path) -> bool:
	if src_jdir.resolve() == dst_jdir.resolve():
		return False
	old_sdir = _raw_state_dir(src_jdir, data_root=data_root)
	new_sdir = _raw_state_dir(dst_jdir, data_root=data_root)
	if not old_sdir.is_dir() or old_sdir.resolve() == new_sdir.resolve():
		return False
	(old_sdir / 'writer.lock').unlink(missing_ok=True)
	if not new_sdir.exists():
		new_sdir.parent.mkdir(parents=True, exist_ok=True)
		os.replace(old_sdir, new_sdir)
		return True
	moved = False
	for rel_sub in ('answer-groups', ''):
		src_sub = old_sdir / rel_sub if rel_sub else old_sdir
		dst_sub = new_sdir / rel_sub if rel_sub else new_sdir
		if not src_sub.is_dir():
			continue
		dst_sub.mkdir(parents=True, exist_ok=True)
		for f in sorted(src_sub.glob('*.json')):
			dst_f = dst_sub / f.name
			raw = f.read_bytes()
			if dst_f.exists():
				if dst_f.read_bytes() != raw:
					raise FileExistsError(f'Conflicting journal state file during upgrade: {dst_f}')
				f.unlink()
			else:
				os.replace(f, dst_f)
			moved = True
		if rel_sub and not any(src_sub.iterdir()):
			src_sub.rmdir()
	if not any(old_sdir.iterdir()):
		old_sdir.rmdir()
	return moved
def _sync_overlay_journal_slot(project_root: Path, dst_jdir: Path) -> bool:
	from .path_registry import clear_registry_cache, discover_overlay_file, project_paths
	ov_file = discover_overlay_file(project_root)
	if None is ov_file or not ov_file.is_file():
		return False
	raw_text = ov_file.read_text(encoding='utf-8-sig')
	raw_obj = json.loads(raw_text)
	if not isinstance(raw_obj, dict) or not isinstance(raw_obj.get('paths'), dict):
		return False
	cur_val = raw_obj['paths'].get('journal_dir')
	legacy_vals = ('${JOURNAL_ROOT_DIR}/1 - Analysis', '${JOURNAL_ROOT_DIR}/1 - \u0410\u043d\u0430\u043b\u0438\u0437', '\ua66e/1 - Analysis', '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437')
	if cur_val not in legacy_vals:
		return False
	pp = project_paths(project_root, exact_root=True)
	if dst_jdir.resolve() != pp.journal_root_dir.resolve():
		return False
	indent = '\t' if '\n\t"' in raw_text else 2
	raw_obj['paths']['journal_dir'] = '${JOURNAL_ROOT_DIR}'
	trailing = '\n' if raw_text.endswith('\n') else ''
	replace_bytes(ov_file, (json.dumps(raw_obj, ensure_ascii=False, indent=indent) + trailing).encode('utf-8'))
	clear_registry_cache()
	return True
def _unit_needs_upgrade(src_jdir: Path, dst_jdir: Path) -> bool:
	if src_jdir.resolve() != dst_jdir.resolve():
		return True
	if (dst_jdir / 'req').is_dir() or (dst_jdir / 'res').is_dir():
		return True
	if 3 > detect_journal_version(dst_jdir):
		return True
	readme = dst_jdir / 'README.md'
	if readme.is_file():
		txt = readme.read_text(encoding='utf-8', errors='replace')
		if '{req,res}' in txt or re.search('\\((?:req|res|\\u227b|\\u227a)/\\d+\\.md\\)', txt):
			return True
	return False
def upgrade_journal(journal_root: str | Path, *, project_root: str | Path | None=None, dry_run: bool=False) -> dict:
	from .path_registry import clear_registry_cache, discover_overlay_file, project_paths
	j_root = Path(journal_root).resolve()
	proj_root = Path(project_root).resolve() if None is not project_root else None
	if not j_root.exists():
		return {'valid': True, 'upgraded': False, 'exists': False, 'journal_dir': str(j_root), 'from_version': 3, 'to_version': 3, 'moved_files': 0, 'buckets': [], 'verified_steps': 0}
	_assert_not_linked_tree(j_root)
	units_preview = _discover_upgrade_units(j_root)
	ov_needs_sync = False
	if None is not proj_root:
		ov_f = discover_overlay_file(proj_root)
		if None is not ov_f and ov_f.is_file():
			try:
				ov_obj = json.loads(ov_f.read_text(encoding='utf-8-sig'))
				if isinstance(ov_obj, dict) and isinstance(ov_obj.get('paths'), dict) and ov_obj['paths'].get('journal_dir') in ('${JOURNAL_ROOT_DIR}/1 - Analysis', '${JOURNAL_ROOT_DIR}/1 - \u0410\u043d\u0430\u043b\u0438\u0437', '\ua66e/1 - Analysis', '\ua66e/1 - \u0410\u043d\u0430\u043b\u0438\u0437'):
					ov_needs_sync = True
			except (OSError, ValueError):
				pass
	if not ov_needs_sync and not any((_unit_needs_upgrade(src_u, dst_u) for src_u, dst_u in units_preview)):
		primary_dst = units_preview[0][1]
		b_names = sorted({child.name for s_name in V2_PAIR if (primary_dst / s_name).is_dir() for child in (primary_dst / s_name).iterdir() if child.is_dir() and is_bucket_dir_name(child.name)}, key=lambda s: int(_BUCKET_DIR_RE.match(s).group(1)))
		step_cnt = len({st for s_name in V2_PAIR for st, _ in iter_side_step_files(primary_dst / s_name)})
		return {'valid': True, 'upgraded': False, 'exists': True, 'journal_dir': str(primary_dst), 'from_version': 3, 'to_version': 3, 'moved_files': 0, 'buckets': b_names, 'verified_steps': step_cnt}
	data_root = project_paths(proj_root, exact_root=True).data_dir if None is not proj_root else data_dir_for(j_root)
	def _execute() -> dict:
		units = _discover_upgrade_units(j_root)
		from_versions = [detect_journal_version(src_u) for src_u, _ in units]
		from_ver = min(from_versions) if from_versions else 1
		plans: list[tuple[Path, Path, str, int, Path, Path, bytes]] = []
		for src_u, dst_u in units:
			for side_label, src_names, dst_name in (('req', ('req', '\u227b'), '\u227b'), ('res', ('res', '\u227a'), '\u227a')):
				for st, src_f in _collect_side_sources(src_u, src_names):
					dst_f = dst_u / dst_name / journal_bucket_name(st) / f'{st}.md'
					raw = src_f.read_bytes()
					if dst_f.exists() and dst_f.resolve() != src_f.resolve() and dst_f.read_bytes() != raw:
						raise FileExistsError(f'Conflicting destination file during journal upgrade; preserved: {dst_f}')
					plans.append((src_u, dst_u, side_label, st, src_f, dst_f, raw))
		moved_count = sum((1 for _, _, _, _, sf, df, _ in plans if sf.resolve() != df.resolve()))
		if dry_run:
			primary_dst = units[0][1]
			b_set = sorted({journal_bucket_name(st) for _, _, _, st, _, _, _ in plans}, key=lambda s: int(_BUCKET_DIR_RE.match(s).group(1)))
			step_cnt = len({(dst_u, st) for _, dst_u, _, st, _, _, _ in plans})
			return {'valid': True, 'upgraded': False, 'dry_run': True, 'exists': True, 'journal_dir': str(primary_dst), 'from_version': from_ver, 'to_version': 3, 'moved_files': moved_count, 'buckets': b_set, 'verified_steps': step_cnt}
		for _, dst_u, _, _, src_f, dst_f, raw in plans:
			if src_f.resolve() == dst_f.resolve():
				continue
			dst_f.parent.mkdir(parents=True, exist_ok=True)
			if dst_f.exists():
				if dst_f.read_bytes() != raw:
					raise FileExistsError(f'Conflicting destination file during journal upgrade: {dst_f}')
				src_f.unlink()
			else:
				os.replace(src_f, dst_f)
			if dst_f.read_bytes() != raw:
				raise OSError(f'Journal upgrade SHA-256 read-back mismatch: {dst_f}')
		readme_updated = False
		state_migrated = False
		for src_u, dst_u in units:
			(dst_u / '\u227b').mkdir(parents=True, exist_ok=True)
			(dst_u / '\u227a').mkdir(parents=True, exist_ok=True)
			for dir_cand in (src_u, dst_u):
				for s_name in (*V1_PAIR, *V2_PAIR):
					s_dir = dir_cand / s_name
					if not s_dir.is_dir():
						continue
					for child in list(s_dir.iterdir()):
						if child.is_dir() and is_bucket_dir_name(child.name) and (not any(child.iterdir())):
							child.rmdir()
					if s_name in V1_PAIR and (not any(s_dir.iterdir())):
						s_dir.rmdir()
			if src_u.resolve() != dst_u.resolve() and src_u.is_dir() and (not any(src_u.iterdir())):
				src_u.rmdir()
			if _migrate_journal_state_dir(src_u, dst_u, data_root):
				state_migrated = True
			if _rewrite_journal_readme(dst_u / 'README.md'):
				readme_updated = True
		overlay_updated = _sync_overlay_journal_slot(proj_root, units[0][1]) if None is not proj_root else False
		clear_registry_cache()
		primary_dst = units[0][1]
		b_names = sorted({child.name for s_name in V2_PAIR if (primary_dst / s_name).is_dir() for child in (primary_dst / s_name).iterdir() if child.is_dir() and is_bucket_dir_name(child.name)}, key=lambda s: int(_BUCKET_DIR_RE.match(s).group(1)))
		step_cnt = len({st for s_name in V2_PAIR for st, _ in iter_side_step_files(primary_dst / s_name)})
		did_upgrade = 0 < moved_count or readme_updated or state_migrated or overlay_updated or 3 > from_ver
		return {'valid': True, 'upgraded': did_upgrade, 'exists': True, 'journal_dir': str(primary_dst), 'from_version': from_ver, 'to_version': detect_journal_version(primary_dst), 'moved_files': moved_count, 'buckets': b_names, 'verified_steps': step_cnt, 'state_migrated': state_migrated, 'readme_updated': readme_updated, 'overlay_updated': overlay_updated}
	if dry_run:
		return _execute()
	with locked(data_root / 'journal-upgrade.lock'):
		return _execute()
def ensure_project_journal_upgraded(root: str | Path, *, selected: str | Path | None=None) -> dict:
	from .path_registry import project_paths
	pp = project_paths(Path(root).resolve(), exact_root=True)
	if None is not selected:
		sel_str = pp.expand(str(selected)) if '${' in str(selected) else str(selected)
		sel_p = (pp.root / sel_str).resolve()
		if '\ua66e' == sel_p.name and sel_p.exists():
			return upgrade_journal(sel_p, project_root=pp.root)
		if sel_p.parent.name == '\ua66e' and sel_p.name in _LEGACY_ANALYSIS_NAMES and sel_p.parent.exists():
			return upgrade_journal(sel_p.parent, project_root=pp.root)
		return {'valid': True, 'upgraded': False, 'exists': sel_p.exists(), 'journal_dir': str(sel_p), 'from_version': detect_journal_version(sel_p), 'to_version': detect_journal_version(sel_p), 'moved_files': 0}
	target = pp.journal_dir if pp.journal_glob else pp.journal_root_dir
	return upgrade_journal(target, project_root=pp.root)
