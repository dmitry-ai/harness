# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
from Df.Harness.Completion.NarrowReconciler import NarrowReconciler
from Df.Harness.lib.completion_checks import dfh_budget_status, dfh_delegation_status, dfh_exec5_status, dfh_gate_resolved, dfh_http_fetch_status, dfh_instruction_snapshot, dfh_is_client_deliverable_path, dfh_issue_first_status, dfh_similar_projects_metadata, dfh_tdd_status
from Df.Harness.lib.completion_compaction import dfh_compaction_status
from Df.Harness.lib.completion_core import dfh_active_turn, dfh_hash, dfh_journal_dir, dfh_json, dfh_native_scan, dfh_now, dfh_persist, dfh_policy, dfh_read_meta, dfh_recorded, dfh_turn_key, dfh_turn_lock, dfh_turns_folder
from Df.Harness.lib.journal_core import dfh_same_journal_identity
from Df.Harness.lib.journal_integrity_ops import dfh_finalize_conflict_turn
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_same_project_root
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
from Df.Harness.lib.storage import dfh_locked, dfh_replace_bytes, dfh_write_immutable_bytes
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_refresh_turn_checks()`
def _apply_inactive_check_defaults(value: dict[str, Any], historical_done: bool) -> None:
	if 'code_lifecycle_check' not in value:
		value['code_lifecycle_check'] = {'verified': True, 'touched_repos': {}, 'issues': [], 'similar_projects': {'verified': True, 'peers': []}, 'violations': []}
	if not historical_done and 'issue_first_check' not in value:
		value['issue_first_check'] = {'verified': True, 'repos': {}, 'violations': []}
	if not historical_done and 'tdd_check' not in value:
		value['tdd_check'] = {'verified': True, 'scopes': {}, 'violations': []}
# @used-by :func:`dfh_new_turn_state()`
def _initial_lifecycle_checks(canon_root: Path, turn: dict, recovered: bool, ops: dict[str, Any]) -> tuple[dict, dict, dict]:
	from agent_tools.issue_lifecycle import code_and_issue_lifecycle_status
	if recovered:
		r = ({'verified': True, 'touched_repos': {}, 'issues': [], 'similar_projects': {'verified': True, 'peers': []}, 'violations': []}, {'verified': True, 'repos': {}, 'violations': []}, {'verified': True, 'scopes': {}, 'violations': []})
	else:
		r = ((ops.get('code_lifecycle_status') or code_and_issue_lifecycle_status)(canon_root, turn), (ops.get('issue_first_status') or dfh_issue_first_status)(canon_root, turn), (ops.get('tdd_status') or dfh_tdd_status)(canon_root, turn))
	return r
# @used-by :func:`_refresh_turn_checks()`
def _load_turn_similar_exemptions(root: Path, key: str, value: dict[str, Any], ops: dict[str, Any]) -> None:
	folder_fn = ops.get('folder') or dfh_turns_folder
	read_fn = ops.get('read') or dfh_read_meta
	ex_file = folder_fn(root) / f'{key}-similar-exemptions.json'
	if ex_file.is_file():
		try:
			ex_loaded = read_fn(ex_file)
			ex_list = ex_loaded.get('exemptions') if isinstance(ex_loaded, dict) else ex_loaded
			if isinstance(ex_list, list):
				value['similar_project_exemptions'] = [it for it in ex_list if isinstance(it, dict)]
		except (OSError, ValueError):
			pass
# @used-by :func:`dfh_load_turn_state()`
def _merge_turn_requests(root: Path, native: dict, turn: dict, value: dict, recovered: bool, allow_extended: bool, ops: dict[str, Any]) -> None:
	dir_fn = ops.get('directory') or dfh_journal_dir
	old, current = (value['requests'], turn['requests'])
	merged = NarrowReconciler(root, native, turn, value, recovered=recovered, same_req_fn=dfh_same_saved_request, journal_dir_fn=dir_fn).run()
	if not (value.get('prepared') and len(current) > len(old)):
		value['requests'] = merged
	elif allow_extended:
		value['uncovered_requests'] = current[len(old):]
	else:
		raise ValueError('A prepared answer does not cover the new native request; preserve it and reconcile the turn')
# @used-by :func:`_refresh_turn_checks()`
def _refresh_active_turn_checks(root: Path, turn: dict, value: dict, ops: dict[str, Any]) -> None:
	from agent_tools.issue_lifecycle import code_and_issue_lifecycle_status
	sim_paths, sim_repos = dfh_similar_projects_metadata(root)
	if sim_paths:
		value['similar_projects'] = sim_paths
	else:
		value.pop('similar_projects', None)
	if sim_repos:
		value['similar_project_repos'] = sim_repos
	else:
		value.pop('similar_project_repos', None)
	value['issue_first_check'] = (ops.get('issue_first_status') or dfh_issue_first_status)(root, turn)
	value['code_lifecycle_check'] = (ops.get('code_lifecycle_status') or code_and_issue_lifecycle_status)(root, turn, value)
	value['tdd_check'] = (ops.get('tdd_status') or dfh_tdd_status)(root, turn)
# @used-by :func:`_refresh_turn_checks()`
def _refresh_core_checks(root: Path, key: str, turn: dict, value: dict, active_validation: bool, ops: dict[str, Any]) -> None:
	folder_fn = ops.get('folder') or dfh_turns_folder
	read_fn = ops.get('read') or dfh_read_meta
	comp_fn = ops.get('compaction_status') or (lambda r, k, t: dfh_compaction_status(r, k, t, folder_fn=folder_fn, read_fn=read_fn, is_deliv_fn=dfh_is_client_deliverable_path))
	budget_fn = ops.get('budget_status') or (lambda r, t: dfh_budget_status(r, t, ops=ops))
	checks = (('exec5_check', lambda: dfh_exec5_status(turn, root, key, ops=ops)), ('http_fetch_check', lambda: dfh_http_fetch_status(turn, root, key, ops=ops)), ('compaction_check', lambda: comp_fn(root, key, turn)), ('delegation_check', lambda: dfh_delegation_status(root, turn)), ('budget_check', lambda: budget_fn(root, turn)))
	for name, check in checks:
		if active_validation or name not in value:
			value[name] = check()
# @used-by :func:`dfh_load_turn_state()`
def _refresh_turn_checks(root_p: Path, key: str, turn: dict, value: dict, active_validation: bool, historical_done: bool, ops: dict[str, Any]) -> None:
	_refresh_core_checks(root_p, key, turn, value, active_validation, ops)
	_load_turn_similar_exemptions(root_p, key, value, ops)
	if active_validation:
		_refresh_active_turn_checks(root_p, turn, value, ops)
	else:
		_apply_inactive_check_defaults(value, historical_done)
	if False is value.get('readiness_check', {}).get('verified') and (not value.get('admission_failure')) and dfh_gate_resolved(root_p, turn, value):
		value.pop('readiness_check', None)
	if 'open' == value.get('status'):
		value.pop('addons_health', None)
# @used-by :func:`dfh_same_saved_request()`
def _same_binding_kind(old_b: dict, cur_b: dict) -> bool:
	old_kind, cur_kind = (old_b.get('kind'), cur_b.get('kind'))
	if 'explicit-project-root' == old_kind:
		r = True
	elif old_kind != cur_kind and (not ({old_kind, cur_kind} <= {'antigravity-workspace-uris', 'antigravity-project-id'})):
		r = False
	else:
		r = {k: v for k, v in old_b.items() if k not in ('root', 'kind')} == {k: v for k, v in cur_b.items() if k not in ('root', 'kind')}
	return r
# @used-by :func:`dfh_load_turn_state()`
def _upgrade_turn_defaults(root_p: Path, native: dict, value: dict, active_validation: bool, ops: dict[str, Any]) -> None:
	if 'instruction_snapshot' not in value and active_validation:
		value['instruction_snapshot'] = dfh_instruction_snapshot(root_p, native, stage='existing-state-upgrade', ops=ops)
	if 'applicable_rules' not in value:
		value['applicable_rules'] = (ops.get('policy') or (lambda: dfh_policy(ops=ops)))()
	if 'git_optional_locks_env' not in value:
		value['git_optional_locks_env'] = os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0')
# @used-by :func:`dfh_load_turn_state()`
def _verify_turn_owner_and_journal(root: Path, native: dict, turn: dict, value: dict, journal_directory: Any, strict_journal: bool, historical_done: bool, ops: dict[str, Any]) -> None:
	dir_fn = ops.get('directory') or dfh_journal_dir
	saved_directory = dir_fn(root, value['journal'])
	if strict_journal and None is not journal_directory and saved_directory != dir_fn(root, journal_directory):
		raise ValueError('The native turn already has a different journal; preserve its original binding')
	if not dfh_same_project_root(value.get('project_root'), root):
		raise ValueError('Completion state has a different native owner; preserved')
	for name, expected in [('platform', native['platform']), ('native_backend', native['native_backend']), ('conversation_id', native['conversation_id']), ('native_turn_id', turn['turn_id'])]:
		if value.get(name) != expected:
			raise ValueError('Completion state has a different native owner; preserved')
	if not (historical_done and dfh_same_journal_identity(value.get('journal'), saved_directory)):
		value['journal'] = str(saved_directory)
	if not historical_done:
		value['project_root'] = str(root)
# @used-by :func:`agent_tools.completion._conflict()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__record_conflict()`
def dfh_conflict(root: str | Path, path: Path, value: dict, native: dict, turn: dict, response: str, detail: str, *, retryable: bool=False, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	hash_fn = eff_ops.get('hash') or dfh_hash
	folder_fn = eff_ops.get('folder') or dfh_turns_folder
	dir_fn = eff_ops.get('directory') or dfh_journal_dir
	persist_fn = eff_ops.get('persist') or (lambda p, v: dfh_persist(p, v, ops=eff_ops))
	payload = response.encode('utf-8')
	evidence = dfh_write_immutable_bytes(folder_fn(root_p) / 'conflicts' / (value['key'] + '-' + hash_fn(payload) + '.txt'), payload, diff_error='Immutable native conflict evidence changed')
	if dfh_recorded(value):
		value['journal_record'] = dfh_recorded(value)
	prior_verified = value.get('delivery') if (value.get('delivery') or {}).get('verified') else value.get('prior_verified_delivery')
	if prior_verified:
		value['prior_verified_delivery'] = deepcopy(prior_verified)
	rel_evidence = evidence.relative_to(root_p).as_posix() if evidence.is_relative_to(root_p) else str(evidence)
	value['status'] = 'conflict'
	value['delivery'] = {'verified': False, 'native_response_sha256': hash_fn(payload), 'source_file': native['source_file'], 'final_step': turn['final_step'], 'native_requests': turn['requests'], 'conflict_evidence': rel_evidence, 'detail': detail, 'retryable': retryable}
	dfh_finalize_conflict_turn(root_p, path, value, turn, dir_fn=dir_fn, persist_fn=persist_fn)
	return {'turn_key': value['key'], 'status': 'conflict', 'detail': detail, 'evidence': rel_evidence, 'retryable': retryable}
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_commands._load_check_context()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_begin()`
# @used-by :func:`Df.Harness.lib.completion_recovery._execute_checkpoint_recovery()`
# @used-by :func:`Df.Harness.lib.completion_recovery._persist_similar_exemption()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops.dfh_record_emergency_locked()`
# @used-by :func:`agent_tools.completion._state()`
# @used-by :func:`dfh_persist_turn_recovery()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__init__()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__reconcile_turn()`
def dfh_load_turn_state(root: str | Path, native: dict, turn: dict, *, recovered: bool=False, allow_extended: bool=False, journal_directory: Any=None, strict_journal: bool=False, ops: dict[str, Any] | None=None) -> tuple[Path, dict[str, Any]]:
	eff_ops = ops or {}
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	key = (eff_ops.get('key') or dfh_turn_key)(native, turn)
	path = (eff_ops.get('folder') or dfh_turns_folder)(root_p) / (key + '.json')
	value = (eff_ops.get('read') or dfh_read_meta)(path) if path.exists() else (eff_ops.get('new') or (lambda r, n, t, **kw: dfh_new_turn_state(r, n, t, ops=eff_ops, **kw)))(root_p, native, turn, recovered=recovered, journal_directory=journal_directory)
	historical_done = bool('handed_off' == value.get('status') or (turn.get('completed') and value.get('status') in ('delivered', 'conflict')))
	active_validation = not recovered and not historical_done
	_upgrade_turn_defaults(root_p, native, value, active_validation, eff_ops)
	_refresh_turn_checks(root_p, key, turn, value, active_validation, historical_done, eff_ops)
	_verify_turn_owner_and_journal(root_p, native, turn, value, journal_directory, strict_journal, historical_done, eff_ops)
	_merge_turn_requests(root_p, native, turn, value, recovered, allow_extended, eff_ops)
	return (path, value)
# @used-by :func:`agent_tools.completion._new()`
# @used-by :func:`dfh_load_turn_state()`
def dfh_new_turn_state(root: str | Path, native: dict, turn: dict, *, recovered: bool=False, journal_directory: Any=None, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	canon_root = dfh_canonicalize_root_dir(root, dfh_load_registry())
	key = (eff_ops.get('key') or dfh_turn_key)(native, turn)
	folder_fn = eff_ops.get('folder') or dfh_turns_folder
	read_fn = eff_ops.get('read') or dfh_read_meta
	sim_paths, sim_repos = dfh_similar_projects_metadata(canon_root)
	lifecycle, issue_first_chk, tdd_chk = _initial_lifecycle_checks(canon_root, turn, recovered, eff_ops)
	comp_fn = eff_ops.get('compaction_status') or (lambda r, k, t: dfh_compaction_status(r, k, t, folder_fn=folder_fn, read_fn=read_fn, is_deliv_fn=dfh_is_client_deliverable_path))
	budget_fn = eff_ops.get('budget_status') or (lambda r, t: dfh_budget_status(r, t, ops=eff_ops))
	dir_fn = eff_ops.get('directory') or dfh_journal_dir
	policy_fn = eff_ops.get('policy') or (lambda: dfh_policy(ops=eff_ops))
	r = {'schema_version': 1, 'key': key, 'project_root': str(canon_root), 'platform': native['platform'], 'native_backend': native['native_backend'], 'conversation_id': native['conversation_id'], 'native_turn_id': turn['turn_id'], 'native_start_step': turn['start_step'], 'requests': turn['requests'], 'role': 'primary', 'journal_required': True, 'journal': str(dir_fn(canon_root, journal_directory)), 'applicable_rules': policy_fn(), 'git_optional_locks_env': os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0'), 'exec5_check': dfh_exec5_status(turn, canon_root, key, ops=eff_ops), 'http_fetch_check': dfh_http_fetch_status(turn, canon_root, key, ops=eff_ops), 'compaction_check': comp_fn(canon_root, key, turn), 'delegation_check': dfh_delegation_status(canon_root, turn), 'budget_check': budget_fn(canon_root, turn), 'issue_first_check': issue_first_chk, 'code_lifecycle_check': lifecycle, 'tdd_check': tdd_chk, 'instruction_snapshot': dfh_instruction_snapshot(canon_root, native, stage='recovery' if recovered else 'turn-begin', ops=eff_ops), 'format_independent': True, 'rule_comprehension_verified': False, 'required_completion': ['answer-prepare', 'native-delivery-check'], 'status': 'open', 'prepared': None, 'delivery': None, 'recovered_after_delivery': recovered, 'created_at': (eff_ops.get('now') or dfh_now)()}
	if sim_paths:
		r['similar_projects'] = sim_paths
	if sim_repos:
		r['similar_project_repos'] = sim_repos
	return r
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_recover_turn_violation()`
# @used-by :func:`agent_tools.completion._persist_turn_recovery()`
def dfh_persist_turn_recovery(root: str | Path, conversation: Any, suffix: str, build_receipt, *, platform: Any=None, backend: Any=None, clear_admission: bool=False, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	native = (eff_ops.get('native') or (lambda r, c, **kw: dfh_native_scan(r, c, ops=eff_ops, **kw)))(root_p, conversation, platform=platform, backend=backend)
	turn = dfh_active_turn(native)
	if None is turn:
		raise ValueError('No active primary native turn to recover')
	key = (eff_ops.get('key') or dfh_turn_key)(native, turn)
	receipt, extra = build_receipt(root_p, key, turn, native)
	receipt_path = (eff_ops.get('folder') or dfh_turns_folder)(root_p) / f'{key}-{suffix}.json'
	lock_fn = eff_ops.get('locked') or dfh_locked
	with lock_fn(dfh_turn_lock(root_p, key, ops=eff_ops)):
		dfh_replace_bytes(receipt_path, (eff_ops.get('json') or dfh_json)(receipt))
		path, value = (eff_ops.get('state') or (lambda r, n, t, **kw: dfh_load_turn_state(r, n, t, ops=eff_ops, **kw)))(root_p, native, turn)
		if clear_admission:
			value.pop('admission_failure', None)
		(eff_ops.get('persist') or (lambda p, v: dfh_persist(p, v, ops=eff_ops)))(path, value)
	rel_file = receipt_path.relative_to(root_p).as_posix() if receipt_path.is_relative_to(root_p) else str(receipt_path)
	return {**receipt, **extra(value), 'recovery_file': rel_file}
# @used-by :func:`_merge_turn_requests()`
def dfh_same_saved_request(old_req: Any, cur_req: Any, root: Path) -> bool:
	if old_req == cur_req:
		r = True
	elif not isinstance(old_req, dict) or (not isinstance(cur_req, dict)):
		r = False
	elif {k: v for k, v in old_req.items() if 'project_binding' != k} != {k: v for k, v in cur_req.items() if 'project_binding' != k}:
		r = False
	else:
		old_b, cur_b = (old_req.get('project_binding'), cur_req.get('project_binding'))
		r = isinstance(old_b, dict) and isinstance(cur_b, dict) and _same_binding_kind(old_b, cur_b) and dfh_same_project_root(old_b.get('root'), root) and dfh_same_project_root(cur_b.get('root'), root)
	return r
# @used-by :func:`agent_tools.completion._unchanged()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.run()`
def dfh_unchanged(root: str | Path, native: dict, turn: dict, *, ops: dict[str, Any] | None=None) -> None:
	eff_ops = ops or {}
	native_fn = eff_ops.get('native') or (lambda r, c, **kw: dfh_native_scan(r, c, ops=eff_ops, **kw))
	key_fn = eff_ops.get('key') or dfh_turn_key
	latest = native_fn(root, native['conversation_id'], platform=native['platform'], backend=native['native_backend'])
	current = dfh_active_turn(latest)
	if None is current or key_fn(latest, current) != key_fn(native, turn) or current['requests'] != turn['requests']:
		raise ValueError('The active native turn or requests changed during preparation; readiness was not granted')