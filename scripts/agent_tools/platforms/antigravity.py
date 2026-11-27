# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Platform.Antigravity.ExecutorMetadataReader import ExecutorMetadataReader
from Df.Harness.Platform.Antigravity.ProjectRegistrar import ProjectRegistrar
from Df.Harness.Platform.Antigravity.ProofVerifier import ProofVerifier
from Df.Harness.Platform.Antigravity.ReviewProver import ReviewProver
from Df.Harness.Platform.Antigravity.TitleSyncer import TitleSyncer
from Df.Harness.Platform.Antigravity.ToolTraceReader import ToolTraceReader
from Df.Harness.Platform.Antigravity.TurnScanner import TurnScanner as AntigravityTurnScanner
from Df.Harness.lib.ag_daemon import dfh_default_folders_json, dfh_discover_live_daemon, dfh_is_live_language_server_pid as _is_live_language_server_pid, dfh_parse_pbtxt_title as _parse_pbtxt_title, dfh_project_item_matches_root as _project_item_matches_root, dfh_read_current_conversation_title as _read_current_conversation_title, dfh_resolve_folders_json
from Df.Harness.lib.ag_inputs import ANTIGRAVITY_MODEL_TIERS as _ANTIGRAVITY_MODEL_TIERS, COMPLETED_STEP_STATUSES, dfh_antigravity_paths, dfh_conversation_db_path as _conversation_db_path, dfh_extract_subagent_uuids as _extract_subagent_uuids, dfh_find_subagent_invocations as _find_subagent_invocations, dfh_load_transcript_inputs as _load_transcript_inputs, dfh_native_inputs as _native_inputs, dfh_native_requests, dfh_project_roots as _project_roots, dfh_request_scope, dfh_require_current_binding, dfh_transcript_path as _transcript_path, dfh_workspace_context
from Df.Harness.lib.ag_metadata import dfh_apply_requested_config as _apply_requested_config, dfh_model_metadata as _model_metadata, dfh_native_invocation, dfh_proof_paths, dfh_query_step_model_ids as _query_step_model_ids
from Df.Harness.lib.ag_wire import dfh_configuration as _configuration, dfh_decode_user_step_entry as _decode_user_step_entry, dfh_extract_step_text as _extract_step_text, dfh_extract_transcript_user_input as _extract_transcript_user_input, dfh_generation_matches_executor as _generation_matches_executor, dfh_wire_fields as wire_fields, dfh_wire_path as _wire_path
from Df.Harness.lib.path_discovery import dfh_default_platform_paths as _default_platform_paths
from Df.Harness.lib.trace_common import dfh_extract_resource_uri as resource_uri, dfh_local_uri_to_path as folder_path, dfh_read_jsonl_objects as read_jsonl_objects
from Df.Harness.lib.trace_review import dfh_reviewer_isolation_issues as reviewer_isolation_issues
from ..runtime import platform_instances, platform_key_for_adapter, platform_settings, request_day, resolve_antigravity_backend, resolve_antigravity_paths, settings
from . import trace_common as _trace_common
ANTIGRAVITY_PROJECTS_DIR = Path(_default_platform_paths('antigravity')['projects_dir'])
try:
	_ag_init_all = settings()
	_ag_init_key = platform_key_for_adapter('antigravity', _ag_init_all) or 'antigravity'
	_ag_init_cfg = (_ag_init_all.get('platforms') or {}).get(_ag_init_key) or {}
	ANTIGRAVITY_FOLDERS_JSON = Path(_ag_init_cfg['folders_json']) if _ag_init_cfg.get('folders_json') else None
except (OSError, ValueError, KeyError, TypeError):
	ANTIGRAVITY_FOLDERS_JSON = None
_INITIAL_ANTIGRAVITY_FOLDERS_JSON = ANTIGRAVITY_FOLDERS_JSON
# @used-by :func:`native_answers()`
# @used-by :func:`native_executor_metadata()`
# @used-by :func:`native_review_proof()`
# @used-by :func:`native_tool_trace()`
# @used-by :func:`register()`
# @used-by :func:`register_antigravity_project()`
# @used-by :func:`update_conversation_title()`
# @used-by :func:`verify_native_proof()`
def _ag_ops() -> dict[str, Any]:
	return {'default_projects_dir': ANTIGRAVITY_PROJECTS_DIR, 'discover_live_daemon': discover_live_daemon, 'initial_folders': _INITIAL_ANTIGRAVITY_FOLDERS_JSON, 'is_live_pid': _is_live_language_server_pid, 'module_folders': ANTIGRAVITY_FOLDERS_JSON, 'native_review_proof': native_review_proof, 'platform_instances': platform_instances, 'platform_settings': platform_settings, 'proof_paths': _proof_paths, 'read_jsonl_objects': read_jsonl_objects, 'settings': settings, 'shell_violations_fn': _trace_common.collect_shell_violations}
# @used-by unused
def _antigravity_paths(backend=None, *, instance=None, conversation_id=None):
	return dfh_antigravity_paths(backend=backend, instance=instance, conversation_id=conversation_id, settings_fn=settings)
# @used-by unused
def _decode_user_step(payload, status, index, load_transcript):
	return _decode_user_step_entry(payload, status, index, load_transcript)[0]
# @used-by unused
def _default_folders_json():
	return dfh_default_folders_json(settings_fn=settings, instances_fn=platform_instances)
# @used-by unused
def _native_invocation(backend, parent_id, conversation_id, role, *, paths=None):
	return dfh_native_invocation(backend, parent_id, conversation_id, role, paths=paths, platform_settings_fn=platform_settings, settings_fn=settings)
# @used-by unused
def _proof_backend(native):
	return Path(_proof_paths(native)['backend_dir'])
# @used-by :func:`_ag_ops()`
# @used-by :func:`_proof_backend()`
def _proof_paths(native):
	return dfh_proof_paths(native, settings_fn=settings, instances_fn=platform_instances, default_paths_fn=_default_platform_paths)
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_antigravity_scope_uses_workspace_only_for_text()`
def _request_scope(root, conversation_id, backend, *, inputs=None, until=None, identifier=None, paths=None, contexts=None):
	return dfh_request_scope(root, conversation_id, backend, inputs=inputs, until=until, identifier=identifier, paths=paths, contexts=contexts, settings_fn=settings)
# @used-by unused
def _resolve_folders_json(folders_json_path=None, sp=None):
	return dfh_resolve_folders_json(folders_json_path, sp, module_folders=ANTIGRAVITY_FOLDERS_JSON, initial_folders=_INITIAL_ANTIGRAVITY_FOLDERS_JSON, settings_fn=settings, instances_fn=platform_instances)
# @used-by unused
def _workspace_context(backend, conversation_id, *, paths=None):
	return dfh_workspace_context(backend, conversation_id, paths=paths, settings_fn=settings)
# @used-by :func:`_ag_ops()`
def discover_live_daemon(backend=None, *, instance=None, conversation_id=None, paths=None) -> dict | None:
	return dfh_discover_live_daemon(backend=backend, instance=instance, conversation_id=conversation_id, paths=paths, settings_fn=settings, is_live_pid_fn=_is_live_language_server_pid)
# @used-by :meth:`test_ask_question_clarifications_m8.AskQuestionClarificationsM8Tests.test_antigravity_scanner_and_turn_state_preserve_clarifications_without_breaking_user_turns()`
# @used-by :meth:`test_background_wait_and_tdd_inheritance.BackgroundWaitAndTddInheritanceTests.test_unfinished_background_run_command_and_russian_stub_merge_and_preserve_tdd_full_gate()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_post_checkpoint_res_citation_and_issue48_recursive_subagent_aggregation()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue48_antigravity_multiturn_subagent_isolation_mid_invocation()`
# @used-by :meth:`test_multiturn_handoff_stop_guard_and_schedule_m1.MultiturnHandoffStopGuardAndScheduleM1Tests.test_schedule_timers_and_stdout_prose_do_not_merge_completed_turn1_into_turn2()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unfinished_parallel_subagent_turn_merges_with_next_request_and_blocks_english_stub_on_russian_request()`
# @used-by :meth:`test_turn_completion.TurnJournalReconcilerTests.test_compacted_status5_steps_single_pass_authorize_and_group_helpers()`
def native_answers(root, conversation_id, *, backend=None, instance=None):
	return AntigravityTurnScanner(root, conversation_id, backend=backend, instance=instance, _ops=_ag_ops()).scan()
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.ag_read()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, backend=None, instance=None):
	return ExecutorMetadataReader(root, conversation_id, role=role, parent_id=parent_id, backend=backend, instance=instance, _ops=_ag_ops()).run()
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_exact_native_workspace_allows_plain_continuation_and_independent_review()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_explicit_upwork_init_binds_generic_workspace_without_rewriting_user_text()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_foreign_job_does_not_claim_parent_or_self_review_while_text_root_preserves_workspace()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_foreign_or_multiple_native_workspaces_cannot_claim_identical_request()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_git_folder_project_id_fallback_and_relocated_root_canonicalization()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_legacy_job_mention_after_foreign_init_cannot_reactivate_old_project()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_native_workspace_supports_self_review_and_empty_metadata_keeps_legacy_job_id()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_status_five_compacted_step_recovers_nested_protobuf_and_transcript_fallback()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_text_root_labels_neither_break_valid_workspace_nor_claim_foreign_workspace()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
def native_requests(root, conversation_id, *, backend=None, instance=None):
	return dfh_native_requests(root, conversation_id, backend=backend, instance=instance, settings_fn=settings)
# @used-by :func:`_ag_ops()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_antigravity_arch_record_review_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_antigravity_native_review_proof_supports_arch_auditor_role()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_cli_prepare_input_record_needs_changes_and_check_text_roundtrip()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_exact_native_workspace_allows_plain_continuation_and_independent_review()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_explicit_upwork_init_binds_generic_workspace_without_rewriting_user_text()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_foreign_job_does_not_claim_parent_or_self_review_while_text_root_preserves_workspace()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_native_review_binding_m4.NativeReviewBindingM4Tests.test_native_review_proof_binds_launcher_chat_with_user_request_and_uses_native_meta()`
# @used-by :meth:`test_review_target_claim_and_wait_m5.ReviewTargetClaimAndWaitM5Tests.test_native_review_proof_retryable_flag_and_bounded_wait_for_final_response()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_antigravity_native_review_for_text_uses_actual_workspace_binding()`
def native_review_proof(root, parent_id, reviewer_id, *, backend=None, instance=None, write=True, wait_timeout=0.0, role='AA'):
	return ReviewProver(root, parent_id, reviewer_id, backend=backend, instance=instance, write=write, wait_timeout=wait_timeout, role=role, _ops=_ag_ops()).run()
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
def native_tool_trace(root, request):
	return ToolTraceReader(root, request, _ops=_ag_ops()).run()
# @used-by :func:`agent_tools.project_rename._build_ag_registrar()`
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests._make_old_project()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests._init_and_register()`
# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests._make_project()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_per_instance_folders_json_uninitialized_instance_and_stop_gate_a6()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_skips_disabled_codex_and_checks_all_enabled_antigravity_instances()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_dynamic_folders_json_and_cleanup_without_homes()`
def register(project_dir, domain_or_topic, date_str=None, *, projects_dir=None, folders_json_path=None):
	return ProjectRegistrar(project_dir, domain_or_topic, date_str, projects_dir=projects_dir, folders_json_path=folders_json_path, multi_instance=True, _ops=_ag_ops()).run()
# @used-by :func:`agent_tools.project_rename._build_ag_registrar()`
# @used-by :func:`test_project_rename._dual_ag_registrar()`
# @used-by :meth:`test_cleanup.CleanupTests.project()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
# @used-by :meth:`test_onboarding.RegistrationTests.test_branch_is_reused_by_parent_and_date_with_other_assignments_preserved()`
# @used-by :meth:`test_onboarding.RegistrationTests.test_existing_native_file_uri_is_matched_without_replacing_settings()`
# @used-by :meth:`test_onboarding.RegistrationTests.test_missing_or_wrong_folders_store_does_not_publish_ungrouped_project()`
# @used-by :meth:`test_onboarding.RegistrationTests.test_parallel_registration_retains_all_assignments()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_registration_portability.RegistrationTests.ag()`
def register_antigravity_project(project_dir, domain_or_topic, date_str=None, projects_dir=ANTIGRAVITY_PROJECTS_DIR, folders_json_path=None, preferred_id=None):
	return ProjectRegistrar(project_dir, domain_or_topic, date_str, projects_dir=projects_dir, folders_json_path=folders_json_path, preferred_id=preferred_id, multi_instance=False, _ops=_ag_ops()).run()
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_foreign_job_does_not_claim_parent_or_self_review_while_text_root_preserves_workspace()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_legacy_job_mention_after_foreign_init_cannot_reactivate_old_project()`
def require_current_binding(root, conversation_id, *, backend=None, instance=None, inputs=None, until=None, role='AA'):
	return dfh_require_current_binding(root, conversation_id, backend=backend, instance=instance, inputs=inputs, until=until, role=role, settings_fn=settings)
# @used-by :func:`agent_tools.completion._ag_title_sync()`
# @used-by :func:`agent_tools.shadow_replay_clone._legacy_shadow_patch_ctx()`
def update_conversation_title(conversation_id: str, title: str, *, backend=None, instance=None, paths=None, timeout: float=2.0) -> dict:
	return TitleSyncer(conversation_id, title, backend=backend, instance=instance, paths=paths, timeout=timeout, _ops=_ag_ops()).run()
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_antigravity_arch_record_review_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_reused_reviewer_and_metadata_drift_m5.ReusedReviewerAndMetadataDriftM5Tests.test_verify_native_proof_accepts_reused_reviewer_send_message_and_rejects_self_mention()`
def verify_native_proof(root, native, package=None):
	return ProofVerifier(root, native, package, _ops=_ag_ops()).run()
