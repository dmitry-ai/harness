# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from pathlib import Path
from typing import Any
from Df.Harness.Completion.AnswerPreparer import AnswerPreparer as AnswerPreparationRunner
from Df.Harness.Completion.JournalReconciler import JournalReconciler as TurnJournalReconciler
from Df.Harness.lib.completion_checks import GATE_SPECS, VERIFIED_CHECK_KEYS, dfh_budget_status, dfh_delegation_status as _delegation_status, dfh_exec5_status, dfh_factual_kb_note_issues as _factual_kb_note_issues, dfh_gate_resolved as _gate_resolved, dfh_hook_crash_status as _hook_crash_status, dfh_http_fetch_status, dfh_instruction_snapshot, dfh_intermediate_or_language_issues, dfh_is_client_deliverable_path as _is_client_deliverable_path, dfh_issue_first_status as _issue_first_status, dfh_recoverable_step_status, dfh_similar_projects_metadata as _similar_projects_metadata, dfh_tdd_status as _tdd_status, dfh_violation_recovery, dfh_workflow_gate_resolved as _workflow_gate_resolved
from Df.Harness.lib.completion_child_trace import dfh_scan_child_trace_turn as _scan_child_trace_turn
from Df.Harness.lib.completion_commands import dfh_add_completion_parser_arguments as add_parser_arguments, dfh_begin, dfh_check_answer, dfh_execute_completion, dfh_prepare, dfh_prepare_once, dfh_reconcile_unprepared_delivery, dfh_sync
from Df.Harness.lib.completion_compaction import dfh_build_compaction_file_index, dfh_compact_compaction_check as _compact_compaction_check, dfh_compaction_status, dfh_find_evicted_cited_files as _find_evicted_cited_files, dfh_write_compaction_index_file
from Df.Harness.lib.completion_core import BUDGET_MAX_CHECKPOINTS, BUDGET_MAX_TOOL_STEPS, BUDGET_WINDOW_5H_MAX_STEPS, COMMANDS, DEL_MAX_ISSUE_ACTIONS_WITHOUT_SUBAGENTS, DEL_MAX_TOTAL_STEPS_WITHOUT_SUBAGENTS, DEL_MAX_UNPERSISTED_SOURCE_READS, DEL_MAX_UNPERSISTED_STEPS, RULE_REQUIREMENTS, RULES, dfh_active_turn as _active, dfh_conversation_journal_steps, dfh_format_conversation_journal_title as format_conversation_journal_title, dfh_hash as _hash, dfh_journal_lock, dfh_json as _json, dfh_native_scan, dfh_now as _now, dfh_persist, dfh_policy, dfh_read_meta as _read, dfh_recorded as _recorded, dfh_sync_antigravity_conversation_title, dfh_turn_key as _key, dfh_turn_lock, dfh_turns_folder as _folder
from Df.Harness.lib.completion_links import dfh_authored_nonquote_hrefs as _authored_nonquote_hrefs, dfh_response_link_issues as _response_link_issues
from Df.Harness.lib.completion_record import dfh_group, dfh_matches_recorded_response, dfh_record, dfh_same_turn_artifact_path as _same_turn_artifact_path
from Df.Harness.lib.completion_recovery import dfh_handoff_launcher_turn, dfh_issue_first_check_turn, dfh_ratchet_ok, dfh_recover_checkpoint, dfh_recover_turn_violation, dfh_similar_project_exempt, dfh_sync_conversation_title, dfh_tdd_check_turn
from Df.Harness.lib.completion_state import dfh_conflict, dfh_load_turn_state, dfh_new_turn_state, dfh_persist_turn_recovery, dfh_same_saved_request as _same_saved_request, dfh_unchanged
from . import journal
from .issue_lifecycle import code_and_issue_lifecycle_status as _code_and_issue_lifecycle_status, evidence_issue_files as _evidence_issue_files, evidence_issue_state as _evidence_issue_state, origin_repo_slug as _origin_repo_slug
from .journal_sync_all import finalize_conflict_turn, persist_turn_state, reconcile_before_begin, resolve_sync_provenance, sync_all_open
from .platforms import adapter
from .response_grounding import ResponseEvidenceAuditor, response_source_and_kb_issues
from .runtime import PRIMARY, platform_adapter_name, platform_name, settings, skip_shell_violations
from .storage import create_bytes, data_dir_for, locked, replace_bytes, write_immutable_bytes
_find_orphan_or_overwritten_steps = journal.find_orphan_or_overwritten_steps
_norm_journal_response_text = journal.norm_journal_response_text
_norm_journal_text = journal.norm_journal_text
_strip_local_file_scheme = journal.strip_local_file_scheme
# @used-by :func:`_completion_ops()`
def _ag_title_sync(cid: str, title: str, *, backend: Any=None) -> dict[str, Any]:
	from .platforms import antigravity as ag_mod
	return ag_mod.update_conversation_title(cid, title, backend=backend)
# @used-by :func:`_budget_status()`
# @used-by :func:`_conflict()`
# @used-by :func:`_exec5_status()`
# @used-by :func:`_group()`
# @used-by :func:`_http_fetch_status()`
# @used-by :func:`_instruction_snapshot()`
# @used-by :func:`_intermediate_or_language_issues()`
# @used-by :func:`_journal_lock()`
# @used-by :func:`_matches_recorded_response()`
# @used-by :func:`_native()`
# @used-by :func:`_new()`
# @used-by :func:`_persist()`
# @used-by :func:`_persist_turn_recovery()`
# @used-by :func:`_policy()`
# @used-by :func:`_prepare_once()`
# @used-by :func:`_record()`
# @used-by :func:`_recoverable_step_status()`
# @used-by :func:`_state()`
# @used-by :func:`_sync_antigravity_conversation_title()`
# @used-by :func:`_turn_lock()`
# @used-by :func:`_unchanged()`
# @used-by :func:`_violation_recovery()`
# @used-by :func:`begin()`
# @used-by :func:`check_answer()`
# @used-by :func:`conversation_journal_steps()`
# @used-by :func:`execute()`
# @used-by :func:`handoff_launcher_turn()`
# @used-by :func:`issue_first_check_turn()`
# @used-by :func:`prepare()`
# @used-by :func:`ratchet_ok()`
# @used-by :func:`reconcile_unprepared_delivery()`
# @used-by :func:`recover_checkpoint()`
# @used-by :func:`recover_turn_violation()`
# @used-by :func:`similar_project_exempt()`
# @used-by :func:`sync()`
# @used-by :func:`sync_conversation_title()`
# @used-by :func:`tdd_check_turn()`
def _completion_ops() -> dict[str, Any]:
	return {'adapter': adapter, 'begin': begin, 'budget_status': _budget_status, 'check_answer': check_answer, 'code_lifecycle_status': _code_and_issue_lifecycle_status, 'compaction_status': _compaction_status, 'conflict': _conflict, 'directory': _directory, 'folder': _folder, 'group': _group, 'handoff': handoff_launcher_turn, 'hash': _hash, 'issue_first_status': _issue_first_status, 'json': _json, 'key': _key, 'lang_issues': _intermediate_or_language_issues, 'locked': locked, 'native': _native, 'new': _new, 'now': _now, 'persist': _persist, 'platform_name': platform_name, 'policy': _policy, 'prepare': prepare, 'prepare_once': _prepare_once, 'primary': PRIMARY, 'read': _read, 'record': _record, 'settings': settings, 'state': _state, 'sync': sync, 'tdd_status': _tdd_status, 'title_sync_fn': _ag_title_sync}
# @used-by :func:`_completion_ops()`
# @used-by :meth:`test_budget_status_scoping.BudgetStatusScopingTests.test_client_project_ignores_delivered_history_and_triggers_on_active_budget()`
# @used-by :meth:`test_budget_status_scoping.BudgetStatusScopingTests.test_code_project_never_flags_graceful_checkpoint_from_history_or_steps()`
def _budget_status(root, turn):
	return dfh_budget_status(root, turn, ops=_completion_ops())
# @used-by unused
def _build_compaction_file_index(root: Path, pre_reads: list[str], post_reads: list[str], evicted_unreread: list[str]) -> list[dict]:
	return dfh_build_compaction_file_index(root, pre_reads, post_reads, evicted_unreread, hash_fn=_hash)
# @used-by :func:`_completion_ops()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_client_deliverable_grounding_and_evicted_step_output_gate()`
def _compaction_status(root, key, turn):
	return dfh_compaction_status(root, key, turn, folder_fn=_folder, read_fn=_read, is_deliv_fn=_is_client_deliverable_path)
# @used-by :func:`_completion_ops()`
# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_conflict_recording_and_reconciliation_prune_terminal_reservations()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
def _conflict(root, path, value, native, turn, response, detail, *, retryable=False):
	return dfh_conflict(root, path, value, native, turn, response, detail, retryable=retryable, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation()`
def _directory(root, selected=None):
	return journal.resolve_journal_dir(root, selected)
# @used-by unused
def _exec5_status(turn, root=None, key=None):
	return dfh_exec5_status(turn, root, key, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_legacy_complete_group_without_turn_state_exposes_proof_gap_without_readmission()`
def _group(root, native, turn, response, directory, *, allow_reprepare=False):
	return dfh_group(root, native, turn, response, directory, allow_reprepare=allow_reprepare, ops=_completion_ops())
# @used-by unused
def _http_fetch_status(turn, root=None, key=None):
	return dfh_http_fetch_status(turn, root, key, ops=_completion_ops())
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_custom_adapter_platform_keys_and_instruction_snapshot()`
def _instruction_snapshot(root, native, *, stage):
	return dfh_instruction_snapshot(root, native, stage=stage, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_language_neutral_slash_commands_enforce_user_default_locale_without_breaking_english_requests()`
def _intermediate_or_language_issues(requests, response: str) -> list[str]:
	return dfh_intermediate_or_language_issues(requests, response, ops=_completion_ops())
# @used-by unused
def _journal_lock(root):
	return dfh_journal_lock(root, ops=_completion_ops())
# @used-by unused
def _matches_recorded_response(recorded, raw_response: str, raw_sha: str) -> bool:
	return dfh_matches_recorded_response(recorded, raw_response, raw_sha, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :func:`test_turn_completion.completed_tail_is_immutable()`
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.__resolve_turn_key()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_prepared_or_missing_tail_turn_remains_rejected()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_historical_explicit_project_root_receipt_reconciles_without_rewriting_saved_state()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_tdd_and_issue_first_check_skip_shell_violation_scanning()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_legacy_complete_group_without_turn_state_exposes_proof_gap_without_readmission()`
def _native(root, conversation=None, *, platform=None, backend=None):
	return dfh_native_scan(root, conversation, platform=platform, backend=backend, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_prepared_or_missing_tail_turn_remains_rejected()`
def _new(root, native, turn, *, recovered=False, journal_directory=None):
	return dfh_new_turn_state(root, native, turn, recovered=recovered, journal_directory=journal_directory, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_prepared_or_missing_tail_turn_remains_rejected()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_historical_explicit_project_root_receipt_reconciles_without_rewriting_saved_state()`
# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_gate_id_auto_clearing_and_resolve_journal_dir()`
def _persist(path, value):
	return dfh_persist(path, value, ops=_completion_ops())
# @used-by unused
def _persist_turn_recovery(root, conversation, suffix, build_receipt, *, platform=None, backend=None, clear_admission=False):
	return dfh_persist_turn_recovery(root, conversation, suffix, build_receipt, platform=platform, backend=backend, clear_admission=clear_admission, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
def _policy():
	return dfh_policy(ops=_completion_ops())
# @used-by :func:`_completion_ops()`
def _prepare_once(root, response, conversation=None, *, platform=None, backend=None, watch=False, watch_dir=None, journal_directory=None, blocked_report=False):
	return dfh_prepare_once(root, response, conversation, platform=platform, backend=backend, watch=watch, watch_dir=watch_dir, journal_directory=journal_directory, blocked_report=blocked_report, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_steering_during_journal_write_preserves_history_without_granting_readiness()`
def _record(root, native, turn, response, directory, *, existing=None, purpose='publication', allow_reprepare=False):
	return dfh_record(root, native, turn, response, directory, existing=existing, purpose=purpose, allow_reprepare=allow_reprepare, ops=_completion_ops())
# @used-by unused
def _recoverable_step_status(turn, violations_key, covered_key, root=None, key=None):
	return dfh_recoverable_step_status(turn, violations_key, covered_key, root, key, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_prepared_or_missing_tail_turn_remains_rejected()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_historical_explicit_project_root_receipt_reconciles_without_rewriting_saved_state()`
# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_gate_id_auto_clearing_and_resolve_journal_dir()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_doctor_and_turn_begin_exclude_addons_health()`
def _state(root, native, turn, *, recovered=False, allow_extended=False, journal_directory=None, strict_journal=False):
	return dfh_load_turn_state(root, native, turn, recovered=recovered, allow_extended=allow_extended, journal_directory=journal_directory, strict_journal=strict_journal, ops=_completion_ops())
# @used-by unused
def _sync_antigravity_conversation_title(root, native: dict, journal_directory=None, *, dry_run: bool=False) -> dict | None:
	return dfh_sync_antigravity_conversation_title(root, native, journal_directory, dry_run=dry_run, ops=_completion_ops())
# @used-by unused
def _turn_lock(root, key):
	return dfh_turn_lock(root, key, ops=_completion_ops())
# @used-by unused
def _unchanged(root, native, turn):
	return dfh_unchanged(root, native, turn, ops=_completion_ops())
# @used-by unused
def _violation_recovery(root, key):
	return dfh_violation_recovery(root, key, ops=_completion_ops())
# @used-by unused
def _write_compaction_index_file(root: Path, key: str, turn: dict, comp_check: dict, *, step_records: list[dict] | None=None) -> str:
	return dfh_write_compaction_index_file(root, key, turn, comp_check, folder_fn=_folder, now_fn=_now, json_fn=_json, hash_fn=_hash, step_records=step_records)
# @used-by :func:`_completion_ops()`
# @used-by :func:`check_pre_invocation.evaluate_pre_invocation_payload()`
# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
# @used-by :func:`test_stop_emergency_capture_and_foreign_sync._reserve_foreign()`
# @used-by :func:`test_turn_completion.completed_tail_is_immutable()`
# @used-by :meth:`test_ask_question_clarifications_m8.AskQuestionClarificationsM8Tests.test_antigravity_scanner_and_turn_state_preserve_clarifications_without_breaking_user_turns()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_historical_explicit_project_root_receipt_reconciles_without_rewriting_saved_state()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
# @used-by :meth:`test_incomplete_scope_regression_matrix.IncompleteScopeRegressionMatrixTests.test_turn_begin_budget_check_isolates_fresh_code_turn_from_5h_history()`
# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_idle_prepared_turn_transitions_to_delivered_via_foreign_sync_and_all_open_without_mutating_journal()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
# @used-by :meth:`test_stop_emergency_capture_and_foreign_sync.StopEmergencyCaptureAndForeignSyncTests.test_begin_syncs_idle_open_foreign_reservation_and_skips_conflict_failed_and_running()`
# @used-by :meth:`test_stop_emergency_capture_and_foreign_sync.StopEmergencyCaptureAndForeignSyncTests.test_stop_gate_fail_open_persists_emergency_capture_and_sync_avoids_duplicate()`
# @used-by :meth:`test_turn_begin_status_and_auditors.TurnBeginStatusAndAuditorsTests.test_begin_returns_top_level_ok_true_for_primary_dry_run_and_child_with_foreign_reconciliation()`
# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_automatic_journal_only_upgrade_and_cli_subcommand()`
# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_gate_id_auto_clearing_and_resolve_journal_dir()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_antigravity_journal_conversation_auto_titling_and_comma_append()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_compaction_index_offload_stdout_bounds_delivery_cleanup_and_dry_run_non_bypass()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_doctor_and_turn_begin_exclude_addons_health()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_pre_invocation_hook_idempotent_turn_begin_child_skip_terminate_and_dry_run()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_registered_empty_launcher_project_tracks_pre_init_failures_and_hands_off_to_daily_project()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_similar_projects_parity_gate_stop_hook_pre_invocation_and_exemption()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_antigravity_begin_and_prepare_never_register_or_start_background_work()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_issue51_post_finalize_deliverable_decoupling_journal_persistence_and_grounding_cache()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_journal_sync_adopt_conflict_recovers_failed_turn()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_kb_persistence_checks_target_path_not_scratch_content()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_parallel_turn_scratch_isolation_and_budget_gate()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_post_finalize_turn_with_adopted_request_skips_authorize_when_non_substantive()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_universal_gates_m1_to_m6_for_external_writes_dict_issues_and_kb_mutations()`
# @used-by :meth:`test_turn_completion.CompletionCase.begin()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_begin_and_prepare_cannot_register_or_start_a_daemon_even_with_legacy_watch_true()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_begin_reconciles_previous_delivery_in_the_same_foreground_call()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_child_foreign_root_and_foreign_profile_never_create_user_pairs()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_steering_during_begin_invalidates_the_prepared_request_snapshot()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_switching_active_native_turn_during_prepare_records_no_answer()`
def begin(root, conversation=None, *, platform=None, backend=None, watch=False, watch_dir=None, journal_directory=None, dry_run=False):
	return dfh_begin(root, conversation, platform=platform, backend=backend, watch=watch, watch_dir=watch_dir, journal_directory=journal_directory, dry_run=dry_run, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :func:`test_contract_invariants._run_parity_defect_case()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_answer_check_and_prepare_reject_misaligned_pending_without_writing_journal()`
# @used-by :meth:`test_background_wait_and_tdd_inheritance.BackgroundWaitAndTddInheritanceTests.test_unfinished_background_run_command_and_russian_stub_merge_and_preserve_tdd_full_gate()`
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.test_blocked_report_records_journal_despite_hygiene_failures_and_allows_doc5()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.test_blocked_report_records_journal_without_closing_workflow_or_allowing_finalize()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.test_blocked_report_rejects_analytical_hm_claims_and_five_stage_content()`
# @used-by :meth:`test_cli_command_grounding.CliCommandGroundingTests.test_answer_check_blocks_unverified_and_allows_shadow_replay_or_disclaimer()`
# @used-by :meth:`test_df_analysis.DfAnalysisGatesTests.test_markdown_table_blocked_across_doc4_hook_linter_and_grounding()`
# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_four_separate_problem_analyses_validated_independently_ru_and_en()`
# @used-by :meth:`test_doc5_context_trigger.Doc5ContextTriggerTests.test_active_turn_cli_failure_plus_new_parent_issue_forces_doc5_four_tracks()`
# @used-by :meth:`test_doc5_context_trigger.Doc5ContextTriggerTests.test_external_repo_unparented_issues_do_not_force_doc5_while_local_bug_issue_does()`
# @used-by :meth:`test_doc5_context_trigger.Doc5ContextTriggerTests.test_negative_regression_matrix_does_not_force_doc5()`
# @used-by :meth:`test_doc5_context_trigger.Doc5ContextTriggerTests.test_planned_child_issue_turn_with_tdd_red_failure_does_not_force_doc5()`
# @used-by :meth:`test_doc5_golden_feature_turn.Doc5GoldenFeatureTurnTests.test_golden_feature_turn_snapshot_does_not_enable_problem_mode()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_antigravity_issue_first_gate_blocks_retroactive_and_passes_parent_then_tdd()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_codex_apply_patch_and_exec_command_issue_first_gate()`
# @used-by :meth:`test_repo_link_gate.RepoLinkGateTests.test_grounding_accepts_verified_local_repo_tagged_url_and_blocks_fabrications()`
# @used-by :meth:`test_scatter_banner_gate.ScatterBannerGateTests.test_analysis_check_and_answer_check_enforce_file6_banner()`
# @used-by :meth:`test_snapshot_canary_and_hook_crash_audit.SnapshotCanaryAndHookCrashAuditTests.test_answer_check_enforces_hook_crash_gate()`
# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_antigravity_tdd_gate_blocks_violations_and_passes_full_bg_green()`
# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_codex_apply_patch_and_exec_command_tdd_gate()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_answer_check_detects_link5_doc4_verify1_and_exec5_without_disk_side_effects()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_similar_projects_parity_gate_stop_hook_pre_invocation_and_exemption()`
# @used-by :meth:`test_verification_observability.VerificationObservabilityTests.test_failed_shadow_replay_blocks_silent_reply_and_issue_close_and_passes_on_disclosure_or_rerun()`
def check_answer(root, response, conversation=None, *, response_path=None, platform=None, backend=None, journal_directory=None, blocked_report=False):
	return dfh_check_answer(root, response, conversation, response_path=response_path, platform=platform, backend=backend, journal_directory=journal_directory, blocked_report=blocked_report, ops=_completion_ops())
# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.resolve_conversation_steps()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_record_answer_subtracts_overlapping_request_ids_and_excludes_stale_steps_from_title()`
def conversation_journal_steps(root, journal_directory, conversation_id: str) -> list[int]:
	return dfh_conversation_journal_steps(root, journal_directory, conversation_id, ops=_completion_ops())
# @used-by :func:`agent_tools.operations.execute()`
# @used-by :meth:`test_service_finalization_exempt_and_sync_all_open.ServiceFinalizationAndSyncAllOpenTests.test_journal_sync_all_open_reconciles_idle_turns_and_honors_adopt_conflict()`
def execute(args):
	return dfh_execute_completion(args, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__maybe_handoff()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_handoff_launcher_turn_cascades_followup_without_job_url_and_clears_reservation()`
def handoff_launcher_turn(launcher_root, target_root, job_id, *, conversation_id=None) -> list[dict]:
	return dfh_handoff_launcher_turn(launcher_root, target_root, job_id, conversation_id=conversation_id, ops=_completion_ops())
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_tdd_and_issue_first_check_skip_shell_violation_scanning()`
def issue_first_check_turn(root, conversation=None, *, platform=None, backend=None):
	return dfh_issue_first_check_turn(root, conversation, platform=platform, backend=backend, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :func:`test_contract_invariants._run_parity_defect_case()`
# @used-by :func:`test_finalized_project_contract._complete_review_and_finalize()`
# @used-by :func:`test_turn_completion.completed_tail_is_immutable()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_answer_check_and_prepare_reject_misaligned_pending_without_writing_journal()`
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.test_blocked_report_records_journal_despite_hygiene_failures_and_allows_doc5()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.test_blocked_report_records_journal_without_closing_workflow_or_allowing_finalize()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.test_blocked_report_rejects_analytical_hm_claims_and_five_stage_content()`
# @used-by :meth:`test_cli_command_grounding.CliCommandGroundingTests.test_prepare_rejects_unverified_cli_recommendation()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.deliver()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_failed_semantic_admission_is_not_granted_by_a_later_valid_apply()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_new_admission_still_rejects_aged_sources_and_cannot_recover_failed_gate()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_post_checkpoint_res_citation_and_issue48_recursive_subagent_aggregation()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_antigravity_issue_first_gate_blocks_retroactive_and_passes_parent_then_tdd()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_codex_apply_patch_and_exec_command_issue_first_gate()`
# @used-by :meth:`test_journal_clarifications_and_disclosure.JournalClarificationsAndDisclosureTests.test_build_journal_metadata_includes_clarifications_and_preserves_user_input_hash()`
# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_all_open_syncs_idle_prepared_turn()`
# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_idle_prepared_turn_transitions_to_delivered_via_foreign_sync_and_all_open_without_mutating_journal()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_antigravity_prepare_prepends_metadata_and_stop_gate_and_sync_accept_clean_chat_reply()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_codex_prepare_reprepare_and_unprepared_recovery_prepend_metadata()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_bypasses_foreign_lease_on_readonly_and_noncode_turns()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_answer_prepare_wait_timeout_retries_transient_lock_and_recovers()`
# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_antigravity_tdd_gate_blocks_violations_and_passes_full_bg_green()`
# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_codex_apply_patch_and_exec_command_tdd_gate()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_antigravity_journal_conversation_auto_titling_and_comma_append()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_compaction_index_offload_stdout_bounds_delivery_cleanup_and_dry_run_non_bypass()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_registered_empty_launcher_project_tracks_pre_init_failures_and_hands_off_to_daily_project()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_similar_projects_parity_gate_stop_hook_pre_invocation_and_exemption()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.assert_repeated_delivery_is_read_only()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_adhoc_http_fetch_in_shell_blocks_and_collect_http_persists()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_antigravity_begin_and_prepare_never_register_or_start_background_work()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_code_and_issue_lifecycle_gate_blocks_uncommitted_unpushed_and_open_issue_in_prepare()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_crlf_prepared_journal_and_system_message_subagent_completion_do_not_conflict()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_excessive_unpersisted_tool_steps_without_subagent_or_kb_write_blocks()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_external_article_link_requires_kb_grounding_and_matching_observed_title()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_issue51_post_finalize_deliverable_decoupling_journal_persistence_and_grounding_cache()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_local_source_grounding_blocks_fabricated_quotes_identifiers_and_currencies()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_mid_turn_checkpoint_blocks_until_recover_checkpoint()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_post_checkpoint_unreread_source_blocks_analysis_and_response()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_post_finalize_turn_with_adopted_request_skips_authorize_when_non_substantive()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_recover_turn_violation_unblocks_prepare_and_gate_blocks_direct_journal_writes()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_repeated_antigravity_preparation_preserves_all_domain_bytes_and_mtimes()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_repeated_conflict_preserves_all_domain_bytes_and_mtimes()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unadopted_substantive_followup_in_tracked_project_cannot_bypass_review()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unencoded_file_uri_accepted_in_prepare_and_reconciled_in_sync()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unfinished_parallel_subagent_turn_merges_with_next_request_and_blocks_english_stub_on_russian_request()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_universal_gates_m1_to_m6_for_external_writes_dict_issues_and_kb_mutations()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_universal_source_kb_check_blocks_reddit_js_shell_unverified_short_links_missing_anchors_and_fake_quotes()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unpersisted_source_reads_and_af_worker_cannot_bypass_substantive_review()`
# @used-by :meth:`test_turn_completion.CompletionCase.prepare()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_begin_and_prepare_cannot_register_or_start_a_daemon_even_with_legacy_watch_true()`
# @used-by :meth:`test_verification_observability.VerificationObservabilityTests.test_prepare_enforces_verification_observability_check()`
def prepare(root, response, conversation=None, *, platform=None, backend=None, watch=False, watch_dir=None, journal_directory=None, wait_timeout: float=0.0, wait_poll: float=1.0, blocked_report: bool=False):
	return dfh_prepare(root, response, conversation, platform=platform, backend=backend, watch=watch, watch_dir=watch_dir, journal_directory=journal_directory, wait_timeout=wait_timeout, wait_poll=wait_poll, blocked_report=blocked_report, ops=_completion_ops())
# @used-by unused
def ratchet_ok(root, file_path, reason, conversation=None, *, platform=None, backend=None):
	return dfh_ratchet_ok(root, file_path, reason, conversation, platform=platform, backend=backend, ops=_completion_ops())
# @used-by unused
def reconcile_unprepared_delivery(root, conversation=None, *, platform=None, backend=None, from_step=0, journal_directory=None):
	return dfh_reconcile_unprepared_delivery(root, conversation, platform=platform, backend=backend, from_step=from_step, journal_directory=journal_directory, ops=_completion_ops())
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_post_checkpoint_res_citation_and_issue48_recursive_subagent_aggregation()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_compaction_index_offload_stdout_bounds_delivery_cleanup_and_dry_run_non_bypass()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_mid_turn_checkpoint_blocks_until_recover_checkpoint()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_post_checkpoint_unreread_source_blocks_analysis_and_response()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_codex_compaction_and_adhoc_http_fetch_gates()`
def recover_checkpoint(root, conversation=None, *, platform=None, backend=None, dry_run=False):
	return dfh_recover_checkpoint(root, conversation, platform=platform, backend=backend, dry_run=dry_run, ops=_completion_ops())
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_antigravity_issue_first_gate_blocks_retroactive_and_passes_parent_then_tdd()`
# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_antigravity_tdd_gate_blocks_violations_and_passes_full_bg_green()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_recover_turn_violation_unblocks_prepare_and_gate_blocks_direct_journal_writes()`
def recover_turn_violation(root, conversation=None, *, reason=None, platform=None, backend=None):
	return dfh_recover_turn_violation(root, conversation, reason=reason, platform=platform, backend=backend, ops=_completion_ops())
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_similar_projects_parity_gate_stop_hook_pre_invocation_and_exemption()`
def similar_project_exempt(root, peer, reason, conversation=None, *, platform=None, backend=None):
	return dfh_similar_project_exempt(root, peer, reason, conversation, platform=platform, backend=backend, ops=_completion_ops())
# @used-by :func:`_completion_ops()`
# @used-by :func:`test_turn_completion.foreground_sync_preserves_admitted_delivery()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.assert_stable()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.deliver()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_failed_semantic_admission_is_not_granted_by_a_later_valid_apply()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_legacy_record_has_visible_proof_gap_and_unchanged_history()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_new_admission_still_rejects_aged_sources_and_cannot_recover_failed_gate()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_proof_evidence_review_document_and_journal_changes_remain_conflicts()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_real_pre_change_legacy_conflict_remains_conflict_permanently()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_real_pre_change_legacy_record_reports_legacy_proof_gap_and_remains_stable()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_reconciliation_receipt_tampering_or_deletion_remains_conflict()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_replaying_an_older_applied_target_is_not_a_later_legitimate_revision()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_selected_review_entry_mutation_or_deletion_remains_conflict()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_unreconciled_target_edit_temporary_conflict_preserves_original_delivery_provenance()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_cli_issue_first_check_read_only_and_legacy_delivered_immutability()`
# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_all_open_syncs_idle_prepared_turn()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_antigravity_prepare_prepends_metadata_and_stop_gate_and_sync_accept_clean_chat_reply()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_codex_prepare_reprepare_and_unprepared_recovery_prepend_metadata()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_service_finalization_exempt_and_sync_all_open.ServiceFinalizationAndSyncAllOpenTests.test_journal_sync_all_open_reconciles_idle_turns_and_honors_adopt_conflict()`
# @used-by :meth:`test_stop_emergency_capture_and_foreign_sync.StopEmergencyCaptureAndForeignSyncTests.test_stop_gate_fail_open_persists_emergency_capture_and_sync_avoids_duplicate()`
# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_sync_preserves_legacy_delivered_turn_bytes_without_tdd_check()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_compaction_index_offload_stdout_bounds_delivery_cleanup_and_dry_run_non_bypass()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_registered_empty_launcher_project_tracks_pre_init_failures_and_hands_off_to_daily_project()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.sync()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_journal_sync_adopt_conflict_recovers_failed_turn()`
# @used-by :meth:`test_turn_completion.CompletionCase.sync()`
def sync(root, conversation=None, *, platform=None, backend=None, from_step=0, journal_directory=None, adopt_conflict=False, all_open=False, _preloaded_native=None):
	return dfh_sync(root, conversation, platform=platform, backend=backend, from_step=from_step, journal_directory=journal_directory, adopt_conflict=adopt_conflict, all_open=all_open, _preloaded_native=_preloaded_native, ops=_completion_ops())
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_antigravity_journal_conversation_auto_titling_and_comma_append()`
def sync_conversation_title(root, conversation=None, *, platform=None, backend=None, journal_directory=None, dry_run: bool=False) -> dict:
	return dfh_sync_conversation_title(root, conversation, platform=platform, backend=backend, journal_directory=journal_directory, dry_run=dry_run, ops=_completion_ops())
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_tdd_check_reports_uncovered_added_function()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_tdd_and_issue_first_check_skip_shell_violation_scanning()`
def tdd_check_turn(root, conversation=None, *, platform=None, backend=None):
	return dfh_tdd_check_turn(root, conversation, platform=platform, backend=backend, ops=_completion_ops())