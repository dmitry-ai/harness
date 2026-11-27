# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.journal_core import dfh_resolve_journal_dir, dfh_same_journal_identity
from Df.Harness.lib.journal_integrity_ops import dfh_collect_conversation_journal_steps
from Df.Harness.lib.journal_records import dfh_iter_answer_group_records
from Df.Harness.lib.journal_reservations import dfh_iter_turn_reservations
from Df.Harness.lib.journal_sync_ops import dfh_persist_turn_state
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_project_paths, dfh_var_value
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
from Df.Harness.lib.request_binding import dfh_format_binding_diagnostic
from Df.Harness.lib.runtime_context import dfh_platform_name
from Df.Harness.lib.runtime_instances import dfh_platform_adapter_name
import hashlib
import json
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
BUDGET_MAX_CHECKPOINTS = 2
BUDGET_MAX_TOOL_STEPS = 120
BUDGET_WINDOW_5H_MAX_STEPS = 400
COMMANDS = ('turn-begin', 'answer-check', 'answer-prepare', 'recover-checkpoint', 'recover-turn-violation', 'similar-project-exempt', 'ratchet-ok', 'tdd-check', 'issue-first-check', 'journal-sync', 'reconcile-unprepared-delivery', 'sync-conversation-title')
DEL_MAX_ISSUE_ACTIONS_WITHOUT_SUBAGENTS = 3
DEL_MAX_TOTAL_STEPS_WITHOUT_SUBAGENTS = 60
DEL_MAX_UNPERSISTED_SOURCE_READS = 10
DEL_MAX_UNPERSISTED_STEPS = 40
NON_TURN_STATE_SUFFIXES = ('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json', '-mechanical-exempt.json', 'pending-sync.json')
RULE_REQUIREMENTS = {'FILE-3': 'Before publication, the primary agent saves the exact request and complete final response via answer-prepare.', 'EXEC-5': 'Run read-only Git checks with `--no-optional-locks` to avoid updating the index as a side effect.', 'DOC-2': 'Frame any unknown or unproven explanation as a hypothesis with arguments for/against and an expert score in %.'}
RULES = {'FILE-3': ('rules/01-file-boundaries.md', 'file-3'), 'EXEC-5': ('rules/08-execution-and-tools.md', 'exec-5'), 'DOC-2': ('rules/04-statement-structure.md', 'doc-2')}
# @used-by :func:`dfh_sync_antigravity_conversation_title()`
def _run_ag_title_sync(cid: str, title: str, steps: list[int], backend: Any, ops: dict[str, Any]) -> dict[str, Any]:
	try:
		sync_fn = ops.get('title_sync_fn')
		if None is not sync_fn:
			res = sync_fn(cid, title, backend=backend)
		else:
			from Df.Harness.Platform.Antigravity.TitleSyncer import TitleSyncer
			res = TitleSyncer(cid, title, backend=backend).run()
		r = {**res, 'steps': steps}
	except Exception as exc:
		r = {'synced': False, 'changed': False, 'title': title, 'steps': steps, 'conversation_id': cid, 'reason': 'sync_error', 'error': str(exc)}
	return r
# @used-by :func:`dfh_native_scan()`
def _scan_native_for_platform(root_p: Path, platform: str, conversation: str, backend: Any, ops: dict[str, Any]) -> dict[str, Any]:
	adapter_fn = ops.get('adapter')
	if None is not adapter_fn:
		r = adapter_fn(platform).native_answers(root_p, conversation, backend=backend)
	else:
		settings_fn = ops.get('settings') or (lambda: SettingsLoader().run())
		plat_cfg = (settings_fn().get('platforms') or {}).get(platform)
		kind = dfh_platform_adapter_name(platform, plat_cfg, settings_fn=settings_fn)
		if 'codex' == kind:
			from Df.Harness.Platform.Codex.TurnScanner import TurnScanner as CxScanner
			r = CxScanner(root_p, conversation, backend=backend).scan()
		else:
			from Df.Harness.Platform.Antigravity.TurnScanner import TurnScanner as AgScanner
			r = AgScanner(root_p, conversation, backend=backend).scan()
	return r
# @used-by :func:`Df.Harness.lib.completion_commands._load_check_context()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_begin()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare_once()`
# @used-by :func:`Df.Harness.lib.completion_recovery._load_active_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery._scan_readonly_turn()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_persist_turn_recovery()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_unchanged()`
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.__resolve_turn_key()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_historical_explicit_project_root_receipt_reconciles_without_rewriting_saved_state()`
def dfh_active_turn(native: dict[str, Any]) -> dict[str, Any] | None:
	if not native['primary']:
		r: dict[str, Any] | None = None
	else:
		turn = next((t for t in native['turns'] if t['turn_id'] == native['active_turn_id']), None)
		if None is turn or not turn['owned'] or turn['aborted']:
			diag = native.get('binding_diagnostic') if isinstance(native.get('binding_diagnostic'), dict) else {}
			detail = dfh_format_binding_diagnostic(diag.get('expected_root'), diag.get('binding'), expected_job_id=diag.get('expected_job_id'))
			suffix = f' ({detail})' if detail else ''
			raise ValueError(f'No active native user turn belonging entirely to this project{suffix}')
		r = turn
	return r
# @used-by :func:`Df.Harness.lib.completion_record._maybe_prepend_journal_metadata()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_sync_conversation_title()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :func:`agent_tools.completion.conversation_journal_steps()`
# @used-by :func:`dfh_sync_antigravity_conversation_title()`
def dfh_conversation_journal_steps(root: str | Path, journal_directory: Any, conversation_id: str, *, ops: dict[str, Any] | None=None) -> list[int]:
	eff_ops = ops or {}
	cid = str(conversation_id or '').strip().lower()
	if not cid:
		r: list[int] = []
	else:
		root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
		folder_fn = eff_ops.get('folder') or dfh_turns_folder
		dir_fn = eff_ops.get('directory') or dfh_journal_dir
		read_fn = eff_ops.get('read') or dfh_read_meta
		r = dfh_collect_conversation_journal_steps(folder_fn(root_p), dir_fn(root_p, journal_directory), cid, iter_groups_fn=dfh_iter_answer_group_records, iter_res_fn=dfh_iter_turn_reservations, read_fn=read_fn, same_j_fn=dfh_same_journal_identity)
	return r
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_sync_conversation_title()`
# @used-by :func:`dfh_sync_antigravity_conversation_title()`
# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.conversation_label()`
def dfh_format_conversation_journal_title(steps: Any) -> str:
	ordered = sorted({st for st in (steps or ()) if int is type(st) and 1 <= st})
	return ', '.join((str(st) for st in ordered))
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_instruction_snapshot()`
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_commands._build_begin_result()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_check_answer()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare_once()`
# @used-by :func:`Df.Harness.lib.completion_record._build_record_receipt()`
# @used-by :func:`Df.Harness.lib.completion_record._resolve_existing_group_payload()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_group()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_matches_recorded_response()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_record()`
# @used-by :func:`Df.Harness.lib.completion_recovery._build_dry_run_checkpoint()`
# @used-by :func:`Df.Harness.lib.completion_recovery._execute_checkpoint_recovery()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_conflict()`
# @used-by :func:`agent_tools.completion._build_compaction_file_index()`
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :func:`agent_tools.completion._write_compaction_index_file()`
# @used-by :func:`dfh_policy()`
# @used-by :func:`dfh_turn_key()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__finalize_prepared_state()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__init__()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__verify_delivered_fast_path()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__reconcile_turn()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_instruction_snapshot_inventories_sources_without_claiming_model_delivery()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_malformed_local_rule_registration_is_retained_as_an_inventory_error()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_tracked_prepare_preserves_finalizer_receipt_without_duplicate_pair()`
def dfh_hash(value: bytes) -> str:
	return hashlib.sha256(value).hexdigest()
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_sync()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_record()`
# @used-by :func:`Df.Harness.lib.completion_recovery._handoff_single_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_sync_conversation_title()`
# @used-by :func:`Df.Harness.lib.completion_state._merge_turn_requests()`
# @used-by :func:`Df.Harness.lib.completion_state._verify_turn_owner_and_journal()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_conflict()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops.dfh_record_emergency_locked()`
# @used-by :func:`dfh_conversation_journal_steps()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__complete_turn_delivery()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__resolve_effective_response()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_completion_checks_and_admission_guard()`
def dfh_journal_dir(root: str | Path, selected: Any=None) -> Path:
	return dfh_resolve_journal_dir(root, selected)
# @used-by :func:`agent_tools.completion._journal_lock()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.run()`
def dfh_journal_lock(root: str | Path, *, ops: dict[str, Any] | None=None) -> Path:
	folder_fn = (ops or {}).get('folder') or dfh_turns_folder
	return folder_fn(root) / 'journal.lock'
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_commands._build_begin_result()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare_once()`
# @used-by :func:`Df.Harness.lib.completion_recovery._execute_checkpoint_recovery()`
# @used-by :func:`Df.Harness.lib.completion_recovery._persist_similar_exemption()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_ratchet_ok()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_persist_turn_recovery()`
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :func:`agent_tools.completion._write_compaction_index_file()`
# @used-by :func:`dfh_persist()`
# @used-by :func:`dfh_turn_key()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__finalize_prepared_state()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_cli_issue_first_check_read_only_and_legacy_delivered_immutability()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_sync_preserves_legacy_delivered_turn_bytes_without_tdd_check()`
def dfh_json(value: Any) -> bytes:
	return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
# @used-by :func:`Df.Harness.lib.completion_commands._load_check_context()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_begin()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare_once()`
# @used-by :func:`Df.Harness.lib.completion_recovery._load_active_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery._scan_readonly_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_sync_conversation_title()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_persist_turn_recovery()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_unchanged()`
# @used-by :func:`agent_tools.completion._native()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__init__()`
# @used-by :meth:`Df.Harness.Hook.EmergencyCapturer.EmergencyCapturer.run()`
def dfh_native_scan(root: str | Path, conversation: str | None=None, *, platform: str | None=None, backend: Any=None, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	settings_fn = eff_ops.get('settings')
	plat_fn = eff_ops.get('platform_name') or (lambda p: dfh_platform_name(p, settings_fn=settings_fn))
	eff_plat = plat_fn(platform)
	eff_conv = conversation or (os.environ.get('CODEX_THREAD_ID') if 'codex' == eff_plat else None)
	if not eff_conv:
		raise ValueError('Select the actual current native conversation; no summary or neighbouring chat fallback')
	return _scan_native_for_platform(Path(root).resolve(), eff_plat, eff_conv, backend, eff_ops)
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_instruction_snapshot()`
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_record._build_record_receipt()`
# @used-by :func:`Df.Harness.lib.completion_recovery._execute_checkpoint_recovery()`
# @used-by :func:`Df.Harness.lib.completion_recovery._handoff_single_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_ratchet_ok()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_recover_turn_violation()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_similar_project_exempt()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :func:`agent_tools.completion._write_compaction_index_file()`
# @used-by :func:`dfh_persist()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__authorize_and_sync_workflow()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__finalize_prepared_state()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer._fail_gate()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__build_delivery()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__complete_turn_delivery()`
def dfh_now() -> str:
	return datetime.now(timezone.utc).isoformat()
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_recovery._execute_checkpoint_recovery()`
# @used-by :func:`Df.Harness.lib.completion_recovery._handoff_single_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery._persist_similar_exemption()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_conflict()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_persist_turn_recovery()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._persist_emergency_state()`
# @used-by :func:`agent_tools.completion._persist()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__finalize_prepared_state()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer._fail_gate()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__complete_turn_delivery()`
def dfh_persist(path: Path, value: dict[str, Any], *, ops: dict[str, Any] | None=None) -> None:
	eff_ops = ops or {}
	read_fn = eff_ops.get('read') or dfh_read_meta
	now_fn = eff_ops.get('now') or dfh_now
	json_fn = eff_ops.get('json') or dfh_json
	if not (path.exists() and read_fn(path) == value):
		value['updated_at'] = now_fn()
		dfh_persist_turn_state(path, json_fn(value), value)
# @used-by :func:`Df.Harness.lib.completion_state._upgrade_turn_defaults()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`agent_tools.completion._policy()`
def dfh_policy(*, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	primary = Path(eff_ops.get('primary') or dfh_var_value('HARNESS_CODE')).resolve()
	hash_fn = eff_ops.get('hash') or dfh_hash
	return {ident: {'source': rel, 'anchor': anchor, 'sha256': hash_fn((primary / rel).read_bytes()), 'requirement': RULE_REQUIREMENTS[ident]} for ident, (rel, anchor) in RULES.items()}
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_budget_status()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_violation_recovery()`
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_commands._child_check_value()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_sync()`
# @used-by :func:`Df.Harness.lib.completion_record._commit_or_verify_journal_group()`
# @used-by :func:`Df.Harness.lib.completion_record._resolve_existing_group_payload()`
# @used-by :func:`Df.Harness.lib.completion_record._validate_record_preconditions()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_group()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_record()`
# @used-by :func:`Df.Harness.lib.completion_recovery._build_dry_run_checkpoint()`
# @used-by :func:`Df.Harness.lib.completion_recovery._handoff_single_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery._persist_similar_exemption()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_handoff_launcher_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_ratchet_ok()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_sync_conversation_title()`
# @used-by :func:`Df.Harness.lib.completion_state._load_turn_similar_exemptions()`
# @used-by :func:`Df.Harness.lib.completion_state._refresh_core_checks()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_load_turn_state()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :func:`agent_tools.completion._compaction_status()`
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :func:`dfh_conversation_journal_steps()`
# @used-by :func:`dfh_persist()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__sync_delivered_title()`
def dfh_read_meta(path: Path) -> dict[str, Any]:
	value = json.loads(path.read_bytes().decode('utf-8'))
	if not isinstance(value, dict):
		raise ValueError('Completion metadata must be a JSON object: ' + str(path))
	return value
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_recovery._safe_read_open_turn()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_conflict()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops.dfh_record_emergency_locked()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__verify_delivered_fast_path()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer._record_journal_entry()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__complete_turn_delivery()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__reconcile_turn()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__try_record_turn()`
def dfh_recorded(value: dict[str, Any]) -> dict[str, Any] | None:
	return next((rec for rec in (value.get('prepared'), value.get('journal_record'), value.get('delivery')) if isinstance(rec, dict) and 'journal_steps' in rec), None)
# @used-by :func:`Df.Harness.lib.completion_commands._apply_reconcile_and_title()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_sync_conversation_title()`
# @used-by :func:`agent_tools.completion._sync_antigravity_conversation_title()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__finalize_prepared_state()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__sync_delivered_title()`
def dfh_sync_antigravity_conversation_title(root: str | Path, native: dict[str, Any], journal_directory: Any=None, *, dry_run: bool=False, ops: dict[str, Any] | None=None) -> dict[str, Any] | None:
	eff_ops = ops or {}
	settings_fn = eff_ops.get('settings')
	cid = str(native.get('conversation_id') or '').strip().lower() if isinstance(native, dict) else ''
	if not isinstance(native, dict) or (not native.get('primary')) or 'antigravity' != dfh_platform_adapter_name(native.get('platform'), settings_fn=settings_fn) or (not cid):
		r: dict[str, Any] | None = None
	else:
		steps = dfh_conversation_journal_steps(root, journal_directory, cid, ops=eff_ops)
		title = dfh_format_conversation_journal_title(steps)
		if not title:
			r = {'synced': False, 'changed': False, 'title': '', 'steps': [], 'conversation_id': cid, 'reason': 'no_journal_steps'}
		elif dry_run:
			r = {'synced': False, 'changed': False, 'dry_run': True, 'title': title, 'steps': steps, 'conversation_id': cid}
		else:
			r = _run_ag_title_sync(cid, title, steps, native.get('native_backend'), eff_ops)
	return r
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_commands._load_check_context()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare_once()`
# @used-by :func:`Df.Harness.lib.completion_record._commit_or_verify_journal_group()`
# @used-by :func:`Df.Harness.lib.completion_record._maybe_prepend_journal_metadata()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_group()`
# @used-by :func:`Df.Harness.lib.completion_recovery._load_active_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery._scan_readonly_turn()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_load_turn_state()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_persist_turn_recovery()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_unchanged()`
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.run()`
# @used-by :meth:`Df.Harness.Hook.EmergencyCapturer.EmergencyCapturer.run()`
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.__resolve_turn_key()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_prepared_or_missing_tail_turn_remains_rejected()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_doctor_and_turn_begin_exclude_addons_health()`
def dfh_turn_key(native: dict[str, Any], turn: dict[str, Any]) -> str:
	identity = [native['platform'], native['native_backend'], native['conversation_id'], turn['turn_id']]
	return dfh_hash(dfh_json(identity))[:40]
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare_once()`
# @used-by :func:`Df.Harness.lib.completion_recovery._execute_checkpoint_recovery()`
# @used-by :func:`Df.Harness.lib.completion_recovery._persist_similar_exemption()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_handoff_launcher_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_ratchet_ok()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_persist_turn_recovery()`
# @used-by :func:`agent_tools.completion._turn_lock()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.run()`
# @used-by :meth:`Df.Harness.Hook.EmergencyCapturer.EmergencyCapturer.run()`
def dfh_turn_lock(root: str | Path, key: str, *, ops: dict[str, Any] | None=None) -> Path:
	folder_fn = (ops or {}).get('folder') or dfh_turns_folder
	return folder_fn(root) / f'turn-{key}.lock'
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_budget_status()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_violation_recovery()`
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_commands._child_check_value()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_sync()`
# @used-by :func:`Df.Harness.lib.completion_record._maybe_prepend_journal_metadata()`
# @used-by :func:`Df.Harness.lib.completion_recovery._build_dry_run_checkpoint()`
# @used-by :func:`Df.Harness.lib.completion_recovery._execute_checkpoint_recovery()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_handoff_launcher_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_ratchet_ok()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_similar_project_exempt()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_sync_conversation_title()`
# @used-by :func:`Df.Harness.lib.completion_state._load_turn_similar_exemptions()`
# @used-by :func:`Df.Harness.lib.completion_state._refresh_core_checks()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_conflict()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_load_turn_state()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_persist_turn_recovery()`
# @used-by :func:`agent_tools.completion._compaction_status()`
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :func:`agent_tools.completion._write_compaction_index_file()`
# @used-by :func:`dfh_conversation_journal_steps()`
# @used-by :func:`dfh_journal_lock()`
# @used-by :func:`dfh_turn_lock()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__finalize_prepared_state()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__prune_delivered_checkpoint_recovery()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__sync_delivered_title()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_prepared_or_missing_tail_turn_remains_rejected()`
def dfh_turns_folder(root: str | Path) -> Path:
	pp = dfh_project_paths(root, exact_root=True)
	return pp.turns_dir if pp.has_explicit_path('turns_dir') else (pp.data_dir / 'turns')