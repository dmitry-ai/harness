# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Completion.AnswerPreparer import AnswerPreparer
from Df.Harness.Completion.JournalReconciler import JournalReconciler
from Df.Harness.Journal.OpenTurnSyncer import OpenTurnSyncer
from Df.Harness.lib.blocked_report_ops import dfh_evaluate_check_workflow_errors
from Df.Harness.lib.cli_input import dfh_add_arg_specs, dfh_consume_scratch_input, dfh_load_operation_input
from Df.Harness.lib.completion_checks import dfh_delegation_status, dfh_exec5_status, dfh_factual_kb_note_issues, dfh_hook_crash_status, dfh_http_fetch_status, dfh_intermediate_or_language_issues, dfh_is_client_deliverable_path, dfh_issue_first_status, dfh_tdd_status
from Df.Harness.lib.completion_child_trace import dfh_scan_child_trace_turn
from Df.Harness.lib.completion_compaction import dfh_compact_compaction_check, dfh_compaction_status, dfh_find_evicted_cited_files, dfh_write_compaction_index_file
from Df.Harness.lib.completion_core import dfh_active_turn, dfh_hash, dfh_journal_dir, dfh_json, dfh_native_scan, dfh_now, dfh_persist, dfh_read_meta, dfh_recorded, dfh_sync_antigravity_conversation_title, dfh_turn_key, dfh_turn_lock, dfh_turns_folder
from Df.Harness.lib.completion_links import dfh_response_link_issues
from Df.Harness.lib.completion_recovery import dfh_handoff_launcher_turn, dfh_issue_first_check_turn, dfh_ratchet_ok, dfh_recover_checkpoint, dfh_recover_turn_violation, dfh_similar_project_exempt, dfh_sync_conversation_title, dfh_tdd_check_turn
from Df.Harness.lib.completion_state import dfh_load_turn_state
from Df.Harness.lib.hook_markdown_ops import dfh_markdown_slop_issues
from Df.Harness.lib.journal_integrity_ops import dfh_sync_begin_turn_state
from Df.Harness.lib.journal_reservations import dfh_reserve_turn_steps
from Df.Harness.lib.journal_sync_ops import dfh_reconcile_before_begin
from Df.Harness.lib.journal_upgrade import dfh_ensure_project_journal_upgraded
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_project_paths, dfh_same_project_root
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
from Df.Harness.lib.request_binding import dfh_native_project_id
from Df.Harness.lib.runtime_context import dfh_platform_name
from Df.Harness.lib.storage import dfh_locked
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_COMMAND_ARG_SPECS: dict[str, tuple[tuple[str, dict[str, Any]], ...]] = {
	'answer-check': (('--response-file', {'type': Path, 'required': True, 'help': 'Candidate UTF-8 response file to validate, or - for stdin'}), ('--expected-sha256', {'help': 'Optional expected SHA-256 hex digest of response file'}), ('--blocked-report', {'action': 'store_true', 'help': 'Validate as a pre-finalize blocker report requiring continuation.md and forbidding H-*/M-* claims'})),
	'answer-prepare': (('--no-watch', {'action': 'store_true', 'help': 'Compatibility option; all completion operations are foreground-only'}), ('--response-file', {'type': Path, 'required': True, 'help': 'Exact UTF-8 final response, or - for stdin'}), ('--consume-input', {'action': 'store_true'}), ('--expected-sha256', {'help': 'Optional expected SHA-256 hex digest of response file'}), ('--wait-timeout', {'type': float, 'default': 180.0, 'help': 'Seconds to wait reactively on transient repo/journal contention (default: 180)'}), ('--blocked-report', {'action': 'store_true', 'help': 'Record a pre-finalize blocker report in the journal without closing workflow review/finalize gates'})),
	'journal-sync': (('--from-step', {'type': int, 'default': 0}), ('--adopt-conflict', {'action': 'store_true', 'help': 'Adopt turns that experienced preparation or admission failures into the journal as recovered deliveries'}), ('--all-open', {'action': 'store_true', 'help': 'Reconcile all eligible idle open turn reservations across conversations in this project'})),
	'ratchet-ok': (('--file', {'required': True, 'help': 'Relative path or filename of the tracked test file whose expectation is intentionally changing'}), ('--reason', {'required': True, 'help': 'Audited justification (>= 30 chars) citing the requirement/user decision behind the test change'})),
	'reconcile-unprepared-delivery': (('--from-step', {'type': int, 'default': 0}),),
	'recover-checkpoint': (('--dry-run', {'action': 'store_true', 'help': 'Inspect read-only pre-checkpoint file SHA-256/line index and step summary without writing receipts or bypassing COMPACT-1'}),),
	'recover-turn-violation': (('--reason', {'help': 'Audit note for retrospective turn violation recovery'}),),
	'similar-project-exempt': (('--peer', {'required': True, 'help': 'Declared similar project root or GitHub owner/repo slug'}), ('--reason', {'required': True, 'help': 'Technical justification (>= 30 chars) why peer changes do not apply'})),
	'sync-conversation-title': (('--dry-run', {'action': 'store_true', 'help': 'Compute target journal-numbered conversation title without calling Antigravity UpdateConversationAnnotations'}),),
	'turn-begin': (('--no-watch', {'action': 'store_true', 'help': 'Compatibility option; all completion operations are foreground-only'}), ('--dry-run', {'action': 'store_true', 'help': 'Validate native turn ownership and hygiene checks without writing receipts or upgrading journals'})),
}
_NO_JOURNAL_COMMANDS = frozenset({'issue-first-check', 'ratchet-ok', 'recover-checkpoint', 'recover-turn-violation', 'similar-project-exempt', 'tdd-check'})
# @used-by :func:`_attach_begin_extras()`
def _apply_reconcile_and_title(result: dict[str, Any], root: Path, native: dict[str, Any], value: dict[str, Any], native_rec: dict | None, ops: dict[str, Any]) -> None:
	if None is not native_rec:
		result['native_reconciliation'] = native_rec
		current = next((item for item in (native_rec.get('turns') or ()) if item.get('turn_key') == value['key']), None)
		if current:
			result['status'] = current['status']
	title_sync = None if 'handed_off' == value.get('status') else dfh_sync_antigravity_conversation_title(root, native, value['journal'], ops=ops)
	if None is not title_sync:
		result['conversation_title_sync'] = title_sync
# @used-by :func:`_begin_live()`
def _attach_begin_extras(result: dict[str, Any], root: Path, native: dict[str, Any], value: dict[str, Any], launcher_handoff: list[dict], foreign_rec: list[dict], native_rec: dict | None, ops: dict[str, Any]) -> dict[str, Any]:
	optional = (('reserved_journal_steps', list(value['reserved_journal_steps']) if value.get('reserved_journal_steps') else None), ('handed_off_to', value.get('handed_off_to')), ('launcher_handoff', launcher_handoff), ('foreign_reconciliation', foreign_rec))
	for field, item in optional:
		if item:
			result[field] = item
	_apply_reconcile_and_title(result, root, native, value, native_rec, ops)
	return result
# @used-by :func:`dfh_begin()`
def _begin_live(root: Path, native: dict[str, Any], turn: dict[str, Any], journal_directory: Any, ops: dict[str, Any]) -> dict[str, Any]:
	launcher_handoff = _try_launcher_handoff(root, native, ops)
	dfh_ensure_project_journal_upgraded(root, selected=journal_directory)
	key_fn, folder_fn, dir_fn, read_fn = (ops.get('key') or dfh_turn_key, ops.get('folder') or dfh_turns_folder, ops.get('directory') or dfh_journal_dir, ops.get('read') or dfh_read_meta)
	sync_fn = ops.get('sync') or (lambda r, c=None, **kw: dfh_sync(r, c, ops=ops, **kw))
	key = key_fn(native, turn)
	native_rec, foreign_rec = dfh_reconcile_before_begin(root, native, turn, key, journal_directory, folder_fn=folder_fn, dir_fn=dir_fn, read_fn=read_fn, sync_fn=sync_fn, key_fn=key_fn)
	with (ops.get('locked') or dfh_locked)(dfh_turn_lock(root, key, ops=ops)):
		path, value = (ops.get('state') or (lambda r, n, t, **kw: dfh_load_turn_state(r, n, t, ops=ops, **kw)))(root, native, turn, journal_directory=journal_directory, strict_journal=True)
		if 'handed_off' != value.get('status'):
			dfh_sync_begin_turn_state(root, value, native, turn, native_rec, dir_fn=dir_fn, recorded_fn=dfh_recorded, reserve_fn=dfh_reserve_turn_steps)
			if value['compaction_check'].get('occurred') and (not turn.get('completed')) and value.get('status') not in ('delivered', 'conflict'):
				value['compaction_check']['index_file'] = dfh_write_compaction_index_file(root, value['key'], turn, value['compaction_check'], folder_fn=folder_fn, now_fn=ops.get('now') or dfh_now, json_fn=ops.get('json') or dfh_json, hash_fn=ops.get('hash') or dfh_hash)
			(ops.get('persist') or (lambda p, v: dfh_persist(p, v, ops=ops)))(path, value)
	result = _build_begin_result(root, path, value, turn, dry_run=False, ops=ops)
	return _attach_begin_extras(result, root, native, value, launcher_handoff, foreign_rec, native_rec, ops)
# @used-by :func:`_begin_live()`
# @used-by :func:`dfh_begin()`
def _build_begin_result(root: Path, path: Path, value: dict[str, Any], turn: dict[str, Any], *, dry_run: bool, ops: dict[str, Any]) -> dict[str, Any]:
	hash_fn, json_fn = (ops.get('hash') or dfh_hash, ops.get('json') or dfh_json)
	state_rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
	r: dict[str, Any] = {'ok': True, 'turn_key': value['key'], 'state': state_rel, 'role': 'primary', 'journal_required': True, 'status': value['status'], 'native_requests_sha256': hash_fn(json_fn(turn['requests'])), 'applicable_rules': value['applicable_rules'], 'git_optional_locks_env': value['git_optional_locks_env'], 'exec5_check': value['exec5_check'], 'http_fetch_check': value['http_fetch_check'], 'compaction_check': dfh_compact_compaction_check(value['compaction_check']), 'delegation_check': value['delegation_check'], 'budget_check': value['budget_check'], 'issue_first_check': value.get('issue_first_check', {'verified': True, 'repos': {}, 'violations': []}), 'code_lifecycle_check': value['code_lifecycle_check'], 'tdd_check': value.get('tdd_check', {'verified': True, 'scopes': {}, 'violations': []}), 'rule_comprehension_verified': False, 'required_completion': value['required_completion'], 'execution_mode': 'foreground-only'}
	if dry_run:
		r['dry_run'] = True
	for field in ('similar_projects', 'similar_project_repos'):
		if value.get(field):
			r[field] = list(value[field])
	return r
# @used-by :func:`_load_check_context()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_completion_tail()`
def _child_check_value(root_p: Path, native: dict[str, Any], turn_key: str, turn_obj: dict[str, Any], ops: dict[str, Any]) -> dict[str, Any]:
	folder_fn, read_fn = (ops.get('folder') or dfh_turns_folder, ops.get('read') or dfh_read_meta)
	comp_fn = ops.get('compaction_status') or (lambda r, k, t: dfh_compaction_status(r, k, t, folder_fn=folder_fn, read_fn=read_fn, is_deliv_fn=dfh_is_client_deliverable_path))
	return {'key': turn_key, 'platform': native['platform'], 'conversation_id': native['conversation_id'], 'exec5_check': dfh_exec5_status(turn_obj, root_p, turn_key, ops=ops), 'http_fetch_check': dfh_http_fetch_status(turn_obj, root_p, turn_key, ops=ops), 'compaction_check': comp_fn(root_p, turn_key, turn_obj), 'delegation_check': dfh_delegation_status(root_p, turn_obj)}
# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
# @used-by :func:`dfh_check_answer()`
def _collect_check_payload(root_p: Path, pp: Any, role: str, turn_key: str | None, native: dict | None, turn_obj: dict[str, Any], value_obj: dict[str, Any], response: str, response_path: Any, journal_directory: Any, blocked_report: bool, ops: dict[str, Any]) -> dict[str, Any]:
	from Df.Harness.Grounding.ProblemReportEvaluator import ProblemReportEvaluator
	from agent_tools.causal_checks import unsupported_probability_claims
	from agent_tools.issue_lifecycle import code_and_issue_lifecycle_status
	from agent_tools.response_grounding import response_source_and_kb_issues
	requests_list = list(turn_obj.get('requests') or []) if 'primary' == role else []
	has_trace = role in ('primary', 'child')
	lang_fn = ops.get('lang_issues') or (lambda reqs, resp: dfh_intermediate_or_language_issues(reqs, resp, ops=ops))
	if_fn = ops.get('issue_first_status') or dfh_issue_first_status
	lc_fn = ops.get('code_lifecycle_status') or code_and_issue_lifecycle_status
	tdd_fn = ops.get('tdd_status') or dfh_tdd_status
	comp_chk, del_chk = (value_obj['compaction_check'], value_obj['delegation_check'])
	wf_errs = dfh_evaluate_check_workflow_errors(root_p, pp, role, response, requests_list, turn_obj, value_obj, del_chk, blocked_report=bool(blocked_report), journal_directory=journal_directory, factual_kb_fn=dfh_factual_kb_note_issues, is_deliv_fn=dfh_is_client_deliverable_path, dir_fn=ops.get('directory') or dfh_journal_dir)
	prob_rep_chk = ProblemReportEvaluator(root_p, turn_obj, value_obj, response, requests=requests_list, native=native).evaluate()
	return {'root': root_p, 'native': native, 'turn': turn_obj, 'value': value_obj, 'response': response, 'role': role, 'blocked_report': bool(blocked_report), 'doc4_errs': dfh_markdown_slop_issues(response), 'link_errs': dfh_response_link_issues(root_p, response, response_path=response_path, scratch_dir=pp.scratch_dir), 'prob_errs': [f'DOC-2: Unsupported causal probability basis: {item}' for item in unsupported_probability_claims(response)], 'source_errs': response_source_and_kb_issues(root_p, response, requests_list, touched_files=turn_obj.get('touched_files'), turn=turn_obj, native=native, turn_state=value_obj, skip_df_analysis=True), 'problem_report_chk': prob_rep_chk, 'lang_errs': lang_fn(requests_list, response), 'exec5_chk': value_obj['exec5_check'], 'hook_crash_chk': dfh_hook_crash_status(root_p, native, turn_obj, value_obj, response), 'http_chk': value_obj['http_fetch_check'], 'comp_chk': comp_chk, 'evicted_cited': dfh_find_evicted_cited_files(root_p, pp, turn_key, comp_chk, response) if has_trace else [], 'del_chk': del_chk, 'issue_first_chk': if_fn(root_p, turn_obj) if has_trace else {'verified': True, 'repos': {}, 'violations': []}, 'lifecycle_chk': lc_fn(root_p, turn_obj, value_obj if 'primary' == role else None, response=response), 'tdd_chk': tdd_fn(root_p, turn_obj) if has_trace else {'verified': True, 'scopes': {}, 'violations': []}, 'wf_errs': wf_errs}
# @used-by :func:`dfh_execute_completion()`
def _dispatch_completion_table(args: Any, ops: dict[str, Any]) -> dict[str, Any]:
	begin_fn = ops.get('begin') or (lambda r, c=None, **kw: dfh_begin(r, c, ops=ops, **kw))
	sync_fn = ops.get('sync') or (lambda r, c=None, **kw: dfh_sync(r, c, ops=ops, **kw))
	return {
		'answer-check': lambda: _execute_prepare_or_check(args, ops),
		'answer-prepare': lambda: _execute_prepare_or_check(args, ops),
		'issue-first-check': lambda: dfh_issue_first_check_turn(args.project, args.conversation, ops=ops),
		'journal-sync': lambda: sync_fn(args.project, args.conversation, from_step=args.from_step, journal_directory=args.journal, adopt_conflict=getattr(args, 'adopt_conflict', False), all_open=bool(getattr(args, 'all_open', False))),
		'ratchet-ok': lambda: dfh_ratchet_ok(args.project, args.file, args.reason, args.conversation, ops=ops),
		'reconcile-unprepared-delivery': lambda: dfh_reconcile_unprepared_delivery(args.project, args.conversation, from_step=args.from_step, journal_directory=args.journal, ops=ops),
		'recover-checkpoint': lambda: dfh_recover_checkpoint(args.project, args.conversation, dry_run=bool(getattr(args, 'dry_run', False)), ops=ops),
		'recover-turn-violation': lambda: dfh_recover_turn_violation(args.project, args.conversation, reason=args.reason, ops=ops),
		'similar-project-exempt': lambda: dfh_similar_project_exempt(args.project, args.peer, args.reason, args.conversation, ops=ops),
		'sync-conversation-title': lambda: dfh_sync_conversation_title(args.project, args.conversation, journal_directory=args.journal, dry_run=bool(getattr(args, 'dry_run', False)), ops=ops),
		'tdd-check': lambda: dfh_tdd_check_turn(args.project, args.conversation, ops=ops),
		'turn-begin': lambda: begin_fn(args.project, args.conversation, watch=not args.no_watch, journal_directory=args.journal, dry_run=bool(getattr(args, 'dry_run', False))),
	}
# @used-by :func:`_dispatch_completion_table()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_completion_tail()`
def _execute_prepare_or_check(args: Any, ops: dict[str, Any]) -> dict[str, Any]:
	payload = dfh_load_operation_input(args, args.response_file)
	if 'answer-check' == args.command:
		check_fn = ops.get('check_answer') or (lambda r, resp, conv, **kw: dfh_check_answer(r, resp, conv, ops=ops, **kw))
		r = check_fn(args.project, payload.decode('utf-8'), args.conversation, response_path=args.response_file, journal_directory=args.journal, blocked_report=bool(getattr(args, 'blocked_report', False)))
	else:
		prep_fn = ops.get('prepare') or (lambda r, resp, conv, **kw: dfh_prepare(r, resp, conv, ops=ops, **kw))
		result = prep_fn(args.project, payload.decode('utf-8'), args.conversation, watch=not args.no_watch, journal_directory=args.journal, wait_timeout=float(getattr(args, 'wait_timeout', 180.0)), blocked_report=bool(getattr(args, 'blocked_report', False)))
		r = dfh_consume_scratch_input(args, args.response_file, payload, result)
	return r
# @used-by :func:`dfh_check_answer()`
def _load_check_context(root_p: Path, eff_conv: str | None, eff_plat: str, backend: Any, journal_directory: Any, ops: dict[str, Any]) -> tuple[str, str | None, dict | None, dict[str, Any], dict[str, Any]]:
	if not eff_conv:
		turn_obj: dict[str, Any] = {'turn_id': 'standalone', 'start_step': 0, 'requests': [], 'touched_files': [], 'issue_actions': [], 'exec5_violations': [], 'http_fetch_violations': [], 'compaction': {}, 'delegation': {}}
		value_obj: dict[str, Any] = {'key': None, 'exec5_check': {'verified': True, 'violations': []}, 'http_fetch_check': {'verified': True, 'violations': []}, 'compaction_check': {'verified': True, 'occurred': False, 'evicted_unreread_files': [], 'unreread_analysis_sources': []}, 'delegation_check': {'verified': True, 'aa_partial_read_violations': []}}
		r = ('standalone', None, None, turn_obj, value_obj)
	else:
		native = (ops.get('native') or (lambda r, c, **kw: dfh_native_scan(r, c, ops=ops, **kw)))(root_p, eff_conv, platform=eff_plat, backend=backend)
		if native['primary']:
			turn_obj = dfh_active_turn(native)
			_, value_obj = (ops.get('state') or (lambda r, n, t, **kw: dfh_load_turn_state(r, n, t, ops=ops, **kw)))(root_p, native, turn_obj, journal_directory=journal_directory, strict_journal=True)
			r = ('primary', value_obj['key'], native, turn_obj, value_obj)
		else:
			turn_obj = dfh_scan_child_trace_turn(root_p, eff_conv, native)
			turn_key = (ops.get('key') or dfh_turn_key)(native, turn_obj)
			r = ('child', turn_key, native, turn_obj, _child_check_value(root_p, native, turn_key, turn_obj, ops))
	return r
# @used-by :func:`_begin_live()`
def _try_launcher_handoff(root: Path, native: dict[str, Any], ops: dict[str, Any]) -> list[dict[str, Any]]:
	r: list[dict[str, Any]] = []
	ws_origin = native.get('workspace_root')
	if ws_origin and (not dfh_same_project_root(ws_origin, root)) and dfh_project_paths(root, exact_root=True).project_json.is_file():
		handoff_fn = ops.get('handoff') or (lambda lr, tr, jid, **kw: dfh_handoff_launcher_turn(lr, tr, jid, ops=ops, **kw))
		try:
			r = handoff_fn(ws_origin, root, dfh_native_project_id(root), conversation_id=native['conversation_id'])
		except (OSError, ValueError):
			r = []
	return r
# @used-by :func:`dfh_prepare_once()`
def _validate_prepare_response(response: Any) -> None:
	if not isinstance(response, str) or (not response.strip()):
		raise ValueError('An exact nonempty UTF-8 final response is required')
	from agent_tools.causal_checks import unsupported_probability_claims
	issues = unsupported_probability_claims(response)
	if issues:
		raise ValueError('Unsupported causal probability basis: ' + '; '.join(issues))
# @used-by :func:`Df.Harness.lib.cli_operation_defs._add_single_operation_parser()`
# @used-by :func:`agent_tools.operations.add_parsers()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_commands_parser_and_dispatch()`
# @used-by :meth:`test_service_finalization_exempt_and_sync_all_open.ServiceFinalizationAndSyncAllOpenTests.test_journal_sync_all_open_reconciles_idle_turns_and_honors_adopt_conflict()`
def dfh_add_completion_parser_arguments(parser: Any, command: str) -> None:
	specs: list[tuple[str, dict[str, Any]]] = [('project', {'type': Path}), ('--conversation', {'help': 'Actual current native conversation UUID; Codex can use CODEX_THREAD_ID'})]
	if command not in _NO_JOURNAL_COMMANDS:
		specs.append(('--journal', {'type': Path, 'help': 'User-selected journal; otherwise preserve the turn binding or use \ua66e/1 - Analysis'}))
	specs.extend(_COMMAND_ARG_SPECS.get(command, ()))
	dfh_add_arg_specs(parser, specs)
# @used-by :func:`_dispatch_completion_table()`
# @used-by :func:`agent_tools.completion.begin()`
# @used-by :func:`dfh_prepare_once()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__run_begin()`
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__run_turn_begin()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_commands_parser_and_dispatch()`
def dfh_begin(root: Any, conversation: Any=None, *, platform: Any=None, backend: Any=None, watch: bool=False, watch_dir: Any=None, journal_directory: Any=None, dry_run: bool=False, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	native = (eff_ops.get('native') or (lambda r, c, **kw: dfh_native_scan(r, c, ops=eff_ops, **kw)))(root_p, conversation, platform=platform, backend=backend)
	turn = dfh_active_turn(native)
	if None is turn:
		r: dict[str, Any] = {'ok': True, 'role': 'child', 'journal_required': False, 'reason': 'The primary conversation owns the user journal'}
		if dry_run:
			r['dry_run'] = True
	elif dry_run:
		from agent_tools.source_grounding import read_only_grounding
		with read_only_grounding():
			path, value = (eff_ops.get('state') or (lambda r, n, t, **kw: dfh_load_turn_state(r, n, t, ops=eff_ops, **kw)))(root_p, native, turn, journal_directory=journal_directory, strict_journal=True)
		r = _build_begin_result(root_p, path, value, turn, dry_run=True, ops=eff_ops)
	else:
		r = _begin_live(root_p, native, turn, journal_directory, eff_ops)
	return r
# @used-by :func:`_execute_prepare_or_check()`
# @used-by :func:`agent_tools.completion.check_answer()`
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__run_answer_check()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_commands_parser_and_dispatch()`
def dfh_check_answer(root: Any, response: Any, conversation: Any=None, *, response_path: Any=None, platform: Any=None, backend: Any=None, journal_directory: Any=None, blocked_report: bool=False, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	if not isinstance(response, str) or (not response.strip()):
		raise ValueError('An exact nonempty UTF-8 candidate response is required')
	from agent_tools.gates import run_answer_gates
	from agent_tools.source_grounding import read_only_grounding
	eff_ops = ops or {}
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	pp = dfh_project_paths(root_p, exact_root=True)
	sha = (eff_ops.get('hash') or dfh_hash)(response.encode('utf-8'))
	eff_plat = (eff_ops.get('platform_name') or (lambda p: dfh_platform_name(p, settings_fn=eff_ops.get('settings'))))(platform)
	eff_conv = conversation or (os.environ.get('CODEX_THREAD_ID') if 'codex' == eff_plat else None)
	with read_only_grounding():
		role, turn_key, native, turn_obj, value_obj = _load_check_context(root_p, eff_conv, eff_plat, backend, journal_directory, eff_ops)
		payload = _collect_check_payload(root_p, pp, role, turn_key, native, turn_obj, value_obj, response, response_path, journal_directory, blocked_report, eff_ops)
		all_issues, checks = run_answer_gates(payload)
	return {'valid': not all_issues, 'read_only': True, 'role': role, 'turn_key': turn_key, 'response_sha256': sha, 'issue_count': len(all_issues), 'issues': all_issues, 'checks': checks}
# @used-by :func:`agent_tools.completion.execute()`
# @used-by :meth:`Df.Harness.Cli.DomainExecutor.DomainExecutor.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_commands_parser_and_dispatch()`
def dfh_execute_completion(args: Any, *, ops: dict[str, Any] | None=None) -> Any:
	handler = _dispatch_completion_table(args, ops or {}).get(args.command)
	if None is handler:
		raise ValueError('Unknown completion operation')
	return handler()
# @used-by :func:`_execute_prepare_or_check()`
# @used-by :func:`agent_tools.completion.prepare()`
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__run_answer_prepare()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_commands_parser_and_dispatch()`
def dfh_prepare(root: Any, response: Any, conversation: Any=None, *, platform: Any=None, backend: Any=None, watch: bool=False, watch_dir: Any=None, journal_directory: Any=None, wait_timeout: float=0.0, wait_poll: float=1.0, blocked_report: bool=False, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	from agent_tools.repo_wait import run_with_transient_wait
	eff_ops = ops or {}
	once_fn = eff_ops.get('prepare_once') or (lambda r, resp, conv, **kw: dfh_prepare_once(r, resp, conv, ops=eff_ops, **kw))
	return run_with_transient_wait(Path(root), lambda: once_fn(root, response, conversation, platform=platform, backend=backend, watch=watch, watch_dir=watch_dir, journal_directory=journal_directory, blocked_report=blocked_report), wait_timeout=wait_timeout, poll_interval=wait_poll, conversation=conversation, platform=platform, backend=backend)
# @used-by :func:`agent_tools.completion._prepare_once()`
# @used-by :func:`dfh_prepare()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_commands_parser_and_dispatch()`
def dfh_prepare_once(root: Any, response: Any, conversation: Any=None, *, platform: Any=None, backend: Any=None, watch: bool=False, watch_dir: Any=None, journal_directory: Any=None, blocked_report: bool=False, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	_validate_prepare_response(response)
	eff_ops = ops or {}
	begin_fn = eff_ops.get('begin') or (lambda r, c=None, **kw: dfh_begin(r, c, ops=eff_ops, **kw))
	result = begin_fn(root, conversation, platform=platform, backend=backend, watch=watch, watch_dir=watch_dir, journal_directory=journal_directory)
	if not result['journal_required']:
		raise ValueError('A child executor cannot prepare the primary user journal')
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	key_fn, hash_fn, json_fn = (eff_ops.get('key') or dfh_turn_key, eff_ops.get('hash') or dfh_hash, eff_ops.get('json') or dfh_json)
	with (eff_ops.get('locked') or dfh_locked)(dfh_turn_lock(root_p, result['turn_key'], ops=eff_ops)):
		native = (eff_ops.get('native') or (lambda r, c, **kw: dfh_native_scan(r, c, ops=eff_ops, **kw)))(root_p, conversation, platform=platform, backend=backend)
		turn = dfh_active_turn(native)
		if None is turn or key_fn(native, turn) != result['turn_key'] or hash_fn(json_fn(turn['requests'])) != result['native_requests_sha256']:
			raise ValueError('The active native turn changed during preparation; no answer was recorded')
		r = AnswerPreparer(root_p, response, result, native, turn, blocked_report=blocked_report, _ops=eff_ops).run()
	return r
# @used-by :func:`_dispatch_completion_table()`
# @used-by :func:`agent_tools.completion.reconcile_unprepared_delivery()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_commands_parser_and_dispatch()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_completion_tail()`
def dfh_reconcile_unprepared_delivery(root: Any, conversation: Any=None, *, platform: Any=None, backend: Any=None, from_step: int=0, journal_directory: Any=None, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	sync_fn = eff_ops.get('sync') or (lambda r, c=None, **kw: dfh_sync(r, c, ops=eff_ops, **kw))
	return sync_fn(root, conversation, platform=platform, backend=backend, from_step=from_step, journal_directory=journal_directory, adopt_conflict=True)
# @used-by :func:`_begin_live()`
# @used-by :func:`_dispatch_completion_table()`
# @used-by :func:`agent_tools.completion.sync()`
# @used-by :func:`dfh_reconcile_unprepared_delivery()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_commands_parser_and_dispatch()`
def dfh_sync(root: Any, conversation: Any=None, *, platform: Any=None, backend: Any=None, from_step: int=0, journal_directory: Any=None, adopt_conflict: bool=False, all_open: bool=False, _preloaded_native: dict | None=None, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	if all_open:
		sync_fn = eff_ops.get('sync') or (lambda r, c=None, **kw: dfh_sync(r, c, ops=eff_ops, **kw))
		r = OpenTurnSyncer(root, journal_directory=journal_directory, adopt_conflict=adopt_conflict, from_step=from_step, folder_fn=eff_ops.get('folder') or dfh_turns_folder, dir_fn=eff_ops.get('directory') or dfh_journal_dir, read_fn=eff_ops.get('read') or dfh_read_meta, sync_fn=sync_fn).run()
	else:
		r = JournalReconciler(root, conversation, platform=platform, backend=backend, from_step=from_step, journal_directory=journal_directory, adopt_conflict=adopt_conflict, preloaded_native=_preloaded_native, _ops=eff_ops).run()
	return r
