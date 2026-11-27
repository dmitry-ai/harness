# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.journal_core import dfh_digest, dfh_iter_side_step_files, dfh_journal_pair_dirs, dfh_norm_journal_response_text, dfh_norm_journal_text, dfh_same_journal_identity, dfh_state_dir, dfh_step_file
from Df.Harness.lib.journal_reservations import dfh_reserved_step_ids
from Df.Harness.lib.storage import dfh_create_bytes, dfh_locked
import json
import re
import uuid
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_answer_groups()`
def _check_group_files(directory: Path, req_dir: Path, res_dir: Path, group: dict, filter_ids: set | None) -> bool:
	r = True
	for step, request in zip(group['steps'], group['requests']):
		req_path = dfh_step_file(req_dir, step, directory=directory)
		res_path = dfh_step_file(res_dir, step, directory=directory)
		if not req_path.is_file() or (not res_path.is_file()) or req_path.read_bytes() != request.encode() or dfh_digest(res_path.read_bytes()) != group['response_sha256']:
			if None is filter_ids:
				raise ValueError('Answer group source bytes changed; preserve context')
			r = False
			break
	return r
# @used-by :func:`_scan_orphan_candidates()`
def _check_overwritten_conflict(cand_steps: list[int], disk_reqs: list[str], disk_resps: list[str], claimed_by_step: dict[int, dict], native_ids: list[str]) -> tuple[list[int], Any] | None:
	r: tuple[list[int], Any] | None = None
	for st in cand_steps:
		owner = claimed_by_step.get(st)
		if owner and owner.get('request_ids') != native_ids:
			o_steps, o_reqs = (owner.get('steps') or [], owner.get('requests') or [])
			matches_owner = o_steps == cand_steps and len(o_reqs) == len(cand_steps) and all((d_req == o_req for d_req, o_req in zip(disk_reqs, o_reqs))) and dfh_digest(disk_resps[0].encode('utf-8')) == owner.get('response_sha256')
			if not matches_owner:
				r = (cand_steps, owner.get('turn'))
				break
	return r
# @used-by :func:`_scan_orphan_candidates()`
def _match_orphan_window(cand_steps: list[int], req_map: dict[int, Path], res_map: dict[int, Path], norm_reqs: list[str], norm_resp: str) -> tuple[list[str], list[str]] | None:
	r: tuple[list[str], list[str]] | None = None
	try:
		disk_reqs = [req_map[st].read_bytes().decode('utf-8') for st in cand_steps]
		disk_resps = [res_map[st].read_bytes().decode('utf-8') for st in cand_steps]
	except (OSError, UnicodeDecodeError):
		disk_reqs, disk_resps = ([], [])
	if disk_reqs and 1 == len(set(disk_resps)) and [dfh_norm_journal_text(x) for x in disk_reqs] == norm_reqs and dfh_norm_journal_response_text(disk_resps[0]) == norm_resp:
		r = (disk_reqs, disk_resps)
	return r
# @used-by :func:`dfh_record_step()`
def _reserve_and_publish_step(directory: Path, journal_state: Path, req_content: str, res_content: str, target_step: int | None, *, create_bytes_fn: Any, publish_fn: Any) -> int:
	used = dfh_get_existing_step_ids(directory) | dfh_reserved_step_ids(directory)
	step = target_step if None is not target_step else max(used, default=0) + 1
	if step in used:
		raise FileExistsError(f'Step {step} is occupied or reserved')
	tok = uuid.uuid4().hex
	state = {'journal': str(directory), 'request': req_content, 'request_sha256': dfh_digest(req_content.encode('utf-8')), 'response': res_content, 'response_sha256': dfh_digest(res_content.encode('utf-8')), 'status': 'pending', 'step': step, 'token': tok, 'version': 2}
	create_bytes_fn(journal_state / f'{step}.json', json.dumps(state, ensure_ascii=False, indent=2).encode('utf-8'))
	try:
		publish_fn(directory, step, state)
	except Exception as exc:
		raise RuntimeError(f'Step {step} pending; recover with token {tok}: {exc}') from exc
	return step
# @used-by :func:`dfh_find_orphan_or_overwritten_steps()`
def _scan_orphan_candidates(directory: Path, req_dir: Path, res_dir: Path, norm_reqs: list[str], norm_resp: str, native_ids: list[str]) -> tuple:
	claimed_by_step = {st: g_val for _, g_val in dfh_iter_answer_group_records(directory, ignore_errors=True) for st in (g_val.get('steps') or ()) if int is type(st)}
	req_map, res_map = (dict(dfh_iter_side_step_files(req_dir)), dict(dfh_iter_side_step_files(res_dir)))
	pair_ids = sorted(set(req_map) & set(res_map))
	pair_set, j_state, n = (set(pair_ids), dfh_state_dir(directory), len(norm_reqs))
	r, overwritten = ((None, None, None), None)
	for start in pair_ids:
		cand_steps = list(range(start, start + n))
		if all((st in pair_set for st in cand_steps)):
			matched = _match_orphan_window(cand_steps, req_map, res_map, norm_reqs, norm_resp)
			if None is not matched:
				disk_reqs, disk_resps = matched
				if all((st not in claimed_by_step and (not (j_state / f'{st}.json').exists()) for st in cand_steps)):
					r, overwritten = ((cand_steps, disk_reqs, disk_resps[0]), None)
					break
				if None is overwritten:
					overwritten = _check_overwritten_conflict(cand_steps, disk_reqs, disk_resps, claimed_by_step, native_ids)
	if None is not overwritten:
		raise ValueError(f'Journal step(s) {overwritten[0]} match this native turn but are claimed by another answer group ({overwritten[1]}); preserve the conflict')
	return r
# @used-by :func:`dfh_verify_answer()`
def _validate_answer_group_files(directory: Path, steps: list[int], requests: list[str], response: str) -> None:
	req_dir, res_dir = dfh_journal_pair_dirs(directory)
	for step, request in zip(steps, requests):
		if (dfh_state_dir(directory) / f'{step}.json').exists():
			raise ValueError('Completed historical answer has an incomplete reservation')
		for folder_dir, expected in ((req_dir, request), (res_dir, response)):
			if dfh_step_file(folder_dir, step, directory=directory).read_bytes() != expected.encode('utf-8'):
				raise ValueError('Historical journal bytes changed; preserve them')
# @used-by :func:`dfh_verify_answer()`
def _validate_answer_group_meta(directory: Path, group: dict, requests: list[str], response: str, turn: str, request_ids: Any) -> list[int]:
	if 'complete' != group.get('status') or (not dfh_same_journal_identity(group.get('journal'), directory)) or group.get('turn') != turn or group.get('requests') != requests or group.get('request_ids') != request_ids or group.get('response_sha256') != dfh_digest(response.encode('utf-8')):
		raise ValueError('Historical answer-group identity changed; preserve it')
	steps = group.get('steps')
	if not isinstance(steps, list) or len(steps) != len(requests) or len(set(steps)) != len(steps) or any((int is not type(step) or 1 > step for step in steps)):
		raise ValueError('Historical answer-group steps changed')
	if not isinstance(group.get('tokens'), list) or len(group['tokens']) != len(steps) or any((not isinstance(token, str) or (not token) for token in group['tokens'])):
		raise ValueError('Historical answer-group reservation identity changed')
	return steps
# @used-by :func:`agent_tools.context.assemble()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.adopt_requests()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_group_crash_reserves_all_numbers_and_preserves_previous_context()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_adopt_requests_isolates_foreign_answer_group_mismatch()`
def dfh_answer_groups(directory: str | Path, *, request_ids: Any=None) -> list[dict]:
	eff = Path(directory).resolve()
	req_dir, res_dir = dfh_journal_pair_dirs(eff)
	filter_ids = set(request_ids) if None is not request_ids else None
	groups: list[dict] = []
	for _, group in dfh_iter_answer_group_records(eff):
		if None is not filter_ids and (not set(group.get('request_ids') or []) & filter_ids):
			continue
		if not dfh_same_journal_identity(group.get('journal'), eff) or 'complete' != group.get('status'):
			raise ValueError('Incomplete or mismatched answer group; recover it before context export')
		if _check_group_files(eff, req_dir, res_dir, group, filter_ids):
			groups.append(group)
	return groups
# @used-by :func:`Df.Harness.lib.journal_reservations.dfh_reserve_turn_steps()`
# @used-by :meth:`Df.Harness.Journal.IntegrityAuditor.IntegrityAuditor.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__load_statuses_and_journal()`
# @used-by :meth:`test_turn_completion.TurnJournalReconcilerTests.test_compacted_status5_steps_single_pass_authorize_and_group_helpers()`
def dfh_completed_request_group_index(directory: Path) -> dict[str, tuple[dict, int]]:
	r: dict[str, tuple[dict, int]] = {}
	for _, group in dfh_iter_answer_group_records(directory, ignore_errors=True):
		if 'complete' == group.get('status') and group.get('request_ids'):
			for rid, st in zip(group['request_ids'], group.get('steps') or ()):
				r[rid] = (group, st)
	return r
# @used-by :func:`Df.Harness.lib.completion_record._resolve_record_payload()`
# @used-by :mod:`agent_tools.completion`
def dfh_find_orphan_or_overwritten_steps(directory: Path, requests: list[str], response: str, native_ids: list[str]):
	eff = Path(directory).resolve()
	req_dir, res_dir = dfh_journal_pair_dirs(eff)
	r = (None, None, None)
	if requests and req_dir.is_dir() and res_dir.is_dir():
		norm_reqs = [dfh_norm_journal_text(req) for req in requests]
		r = _scan_orphan_candidates(eff, req_dir, res_dir, norm_reqs, dfh_norm_journal_response_text(response), native_ids)
	return r
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_check_project_journal_problems()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_journal_validation_errors()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_prune_terminal_conflict_reservations()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_validate_finalize_journal()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_validate_step_cli()`
# @used-by :func:`Df.Harness.lib.journal_reservations.dfh_reserve_turn_steps()`
# @used-by :func:`_reserve_and_publish_step()`
# @used-by :func:`agent_tools.context.assemble()`
# @used-by :func:`agent_tools.project_rename_verify._collect_journal_errors()`
# @used-by :meth:`Df.Harness.Journal.IntegrityAuditor.IntegrityAuditor.run()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__resolve_steps()`
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__find_reply_path()`
# @used-by :meth:`test_agent_tools.JournalTests.test_concurrent_real_processes_same_request_get_distinct_pairs()`
# @used-by :meth:`test_agent_tools.JournalTests.test_o_journal_20_entry_bucketing_and_partial_range_normalization()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_group_crash_reserves_all_numbers_and_preserves_previous_context()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_antigravity_journal_conversation_auto_titling_and_comma_append()`
def dfh_get_existing_step_ids(directory: Path) -> set[int]:
	eff = Path(directory)
	req_dir, res_dir = dfh_journal_pair_dirs(eff)
	ids = {st for side in (req_dir, res_dir) for st, _ in dfh_iter_side_step_files(side)}
	s_dir = dfh_state_dir(eff)
	if s_dir.exists():
		ids.update((int(p.stem) for p in s_dir.glob('*.json') if p.stem.isascii() and p.stem.isdigit()))
	for _, group in dfh_iter_answer_group_records(eff):
		if not dfh_same_journal_identity(group.get('journal'), eff.resolve()) or (not isinstance(group.get('steps'), list)) or any((int is not type(x) or 1 > x for x in group['steps'])):
			raise ValueError('Damaged answer-group reservation')
		ids.update(group['steps'])
	return ids
# @used-by :func:`Df.Harness.lib.completion_core.dfh_conversation_journal_steps()`
# @used-by :func:`Df.Harness.lib.completion_record._find_matching_groups()`
# @used-by :func:`_scan_orphan_candidates()`
# @used-by :func:`dfh_answer_groups()`
# @used-by :func:`dfh_completed_request_group_index()`
# @used-by :func:`dfh_get_existing_step_ids()`
# @used-by :func:`dfh_matching_group_response()`
def dfh_iter_answer_group_records(directory: Path, *, ignore_errors: bool=False) -> list[tuple[Path, dict]]:
	groups_dir = dfh_state_dir(Path(directory).resolve()) / 'answer-groups'
	r: list[tuple[Path, dict]] = []
	if groups_dir.is_dir():
		for path in sorted(groups_dir.glob('*.json')):
			try:
				val = json.loads(path.read_bytes().decode('utf-8'))
			except (OSError, UnicodeDecodeError, ValueError):
				if not ignore_errors:
					raise
				continue
			if not isinstance(val, dict):
				if not ignore_errors:
					raise ValueError('Completion metadata must be a JSON object: ' + str(path))
				continue
			r.append((path, val))
	return r
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__resolve_effective_response()`
# @used-by :meth:`test_turn_completion.TurnJournalReconcilerTests.test_compacted_status5_steps_single_pass_authorize_and_group_helpers()`
def dfh_matching_group_response(directory: Path, req_ids: list[str], response: str) -> str | None:
	eff = Path(directory).resolve()
	_, res_dir = dfh_journal_pair_dirs(eff)
	r: str | None = None
	for _, group in dfh_iter_answer_group_records(eff):
		if group.get('request_ids') == req_ids and group.get('steps'):
			res_path = dfh_step_file(res_dir, group['steps'][0], directory=eff)
			res_text = res_path.read_bytes().decode('utf-8') if res_path.is_file() else ''
			if res_text and dfh_norm_journal_response_text(res_text) == dfh_norm_journal_response_text(response):
				r = res_text
			break
	return r
# @used-by :func:`agent_tools.journal._publish()`
# @used-by :func:`dfh_record_step()`
# @used-by :func:`dfh_recover_step()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__write_pending_step()`
def dfh_publish_step(directory: Path, step: int, state: dict, *, recovering: bool=False, create_bytes_fn: Any=dfh_create_bytes) -> None:
	req_dir, res_dir = dfh_journal_pair_dirs(directory)
	for folder_dir, key in [(req_dir, 'request'), (res_dir, 'response')]:
		path = dfh_step_file(folder_dir, step, directory=directory)
		data = state[key].encode('utf-8')
		path.parent.mkdir(parents=True, exist_ok=True)
		if not path.exists():
			create_bytes_fn(path, data)
		elif not recovering or path.read_bytes() != data:
			raise FileExistsError(f'Conflicting file; preserved without changes: {path}')
		if path.read_bytes() != data:
			raise OSError(f'Read-back mismatch: {path}')
	(dfh_state_dir(directory) / f'{step}.json').unlink(missing_ok=True)
# @used-by :func:`agent_tools.journal.record_step()`
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_record_step()`
def dfh_record_step(journal_dir: Path, req_content: str, res_content: str, target_step: int | None=None, allow_overwrite: bool=False, *, create_bytes_fn: Any=dfh_create_bytes, publish_fn: Any=None) -> int:
	from agent_tools.text_workflow import gate_requests
	dfh_validate_payload(req_content, res_content)
	if allow_overwrite:
		raise ValueError('Journal overwrite is unsupported; create a new corrective step')
	if None is not target_step and (int is not type(target_step) or 1 > target_step):
		raise ValueError('Step must be a positive integer')
	directory = Path(journal_dir).resolve()
	gate_requests([directory], [req_content], res_content)
	journal_state = dfh_state_dir(directory)
	req_dir, res_dir = dfh_journal_pair_dirs(directory)
	for folder in (req_dir, res_dir, journal_state):
		folder.mkdir(parents=True, exist_ok=True)
	pub = publish_fn if None is not publish_fn else (lambda d, st, s: dfh_publish_step(d, st, s, create_bytes_fn=create_bytes_fn))
	with dfh_locked(journal_state / 'writer.lock'):
		r = _reserve_and_publish_step(directory, journal_state, req_content, res_content, target_step, create_bytes_fn=create_bytes_fn, publish_fn=pub)
	return r
# @used-by :func:`agent_tools.journal.recover_step()`
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_record_step()`
def dfh_recover_step(directory: Path, step: int, token: str, *, publish_fn: Any=None) -> None:
	if 1 > step:
		raise ValueError('Step must be positive')
	eff = Path(directory).resolve()
	journal_state = dfh_state_dir(eff)
	pub = publish_fn if None is not publish_fn else dfh_publish_step
	with dfh_locked(journal_state / 'writer.lock'):
		state = json.loads((journal_state / f'{step}.json').read_text(encoding='utf-8'))
		if not dfh_same_journal_identity(state.get('journal'), eff) or state['token'] != token or state['step'] != step:
			raise ValueError('Reservation journal, token or step mismatch')
		dfh_validate_payload(state['request'], state['response'])
		for key in ('request', 'response'):
			if dfh_digest(state[key].encode('utf-8')) != state[key + '_sha256']:
				raise ValueError(f'Damaged reservation: {key}')
		pub(eff, step, state, recovering=True)
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_validate_finalize_journal()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_validate_step_cli()`
# @used-by :func:`agent_tools.context.assemble()`
# @used-by :func:`agent_tools.project_rename_verify._collect_journal_errors()`
# @used-by :func:`dfh_validate_step()`
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_record_step()`
# @used-by :meth:`test_agent_tools.JournalTests.test_concurrent_real_processes_same_request_get_distinct_pairs()`
# @used-by :meth:`test_agent_tools.JournalTests.test_exact_bytes_and_no_keyword_authorization()`
# @used-by :meth:`test_agent_tools.JournalTests.test_failed_second_write_recovers_with_token()`
# @used-by :meth:`test_agent_tools.JournalTests.test_o_journal_20_entry_bucketing_and_partial_range_normalization()`
# @used-by :meth:`test_agent_tools.JournalTests.test_process_crash_releases_lock_and_reservation_is_recoverable()`
# @used-by :meth:`test_agent_tools.JournalTests.test_recovery_does_not_overwrite_conflict()`
def dfh_step_errors(directory: Path, step: int) -> list[str]:
	eff = Path(directory)
	if int is not type(step) or 1 > step:
		r = ['Step must be a positive integer']
	else:
		errors: list[str] = []
		req_dir, res_dir = dfh_journal_pair_dirs(eff)
		for folder_dir in (req_dir, res_dir):
			path = dfh_step_file(folder_dir, step, directory=eff)
			try:
				if not path.read_bytes().decode('utf-8').strip():
					errors.append(f'Empty file: {path}')
			except (OSError, UnicodeError) as exc:
				errors.append(f'{path}: {exc}')
		receipt = dfh_state_dir(eff) / f'{step}.json'
		if receipt.exists():
			errors.append(f'Incomplete reservation: {receipt}')
		r = errors
	return r
# @used-by :func:`dfh_record_step()`
# @used-by :func:`dfh_recover_step()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__validate_inputs()`
def dfh_validate_payload(request: str, response: str) -> None:
	for label, text in [('request', request), ('response', response)]:
		if not isinstance(text, str) or (not text.strip()):
			raise ValueError(f'Empty {label}')
		text.encode('utf-8')
		if '\ufffd' in text or '/?/KB/' in text or '/?/data/' in text or '\\?\\KB\\' in text or '\\?\\data\\' in text or re.search('(?:^|[\\s*#(])(?:\\?{2,}\\s+){2,}\\?{2,}', text):
			raise ValueError(f'Corrupted UTF-8 {label} detected (PowerShell pipe OEM/ASCII "?" substitution or U+FFFD); write UTF-8 directly to \ua616/data/scratch/answer.md via write_file or UTF8Encoding($false) and pass --response-file <path> --consume-input')
# @used-by unused
def dfh_validate_step(journal_dir: str | Path, step_num: int) -> bool:
	errors = dfh_step_errors(Path(journal_dir), step_num)
	for error in errors:
		print(error)
	return not errors
# @used-by :func:`Df.Harness.lib.completion_record._commit_or_verify_journal_group()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
def dfh_verify_answer(directory: str | Path, requests: list[str], response: str, turn: str, request_ids: Any=None) -> list[int]:
	if not re.fullmatch('[A-Za-z0-9_-]{1,100}', turn):
		raise ValueError('Stable answer-group identity required')
	eff = Path(directory).resolve()
	group = json.loads((dfh_state_dir(eff) / 'answer-groups' / (turn + '.json')).read_text(encoding='utf-8'))
	steps = _validate_answer_group_meta(eff, group, requests, response, turn, request_ids)
	_validate_answer_group_files(eff, steps, requests, response)
	return steps
