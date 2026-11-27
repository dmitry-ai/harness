# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Platform.Codex.ExecutorMetadataReader import ExecutorMetadataReader
from Df.Harness.Platform.Codex.ProjectRegistrar import ProjectRegistrar
from Df.Harness.Platform.Codex.ProofVerifier import ProofVerifier
from Df.Harness.Platform.Codex.ReviewProver import ReviewProver
from Df.Harness.Platform.Codex.TokenSummarizer import TokenSummarizer
from Df.Harness.Platform.Codex.ToolTraceReader import ToolTraceReader
from Df.Harness.Platform.Codex.TurnScanner import TurnScanner as CodexTurnScanner
from Df.Harness.lib.codex_control import dfh_shared_control
from Df.Harness.lib.codex_metadata import dfh_codex_assignment_source as _assignment_source, dfh_codex_model as _model, dfh_codex_review_inputs as _review_inputs, dfh_codex_selection as _selection, dfh_codex_spawn as _spawn
from Df.Harness.lib.codex_trace import SUBAGENT_PARENT_CACHE as _SUBAGENT_PARENT_CACHE, dfh_actual_user_input as _actual_user_input, dfh_codex_messages as _messages, dfh_codex_native_requests, dfh_codex_paths, dfh_codex_request_scope as _request_scope, dfh_codex_require_current_binding, dfh_codex_trace, dfh_extract_codex_spawn_output_uuids as _extract_codex_spawn_output_uuids, dfh_extract_codex_target_subagents as _extract_codex_target_subagents, dfh_state_db_files as _state_db_files
from Df.Harness.lib.storage import dfh_iter_embedded_json_objects
from Df.Harness.lib.trace_common import dfh_local_uri_to_path as _local_path
from Df.Harness.lib.trace_review import dfh_reviewer_isolation_issues as reviewer_isolation_issues
from ..runtime import extract_platform_homes, platform_settings, profile_name, registration_profile_name, request_day, resolve_codex_home, resolve_codex_paths, settings
from . import trace_common as _trace_common
import subprocess
# @used-by :func:`native_answers()`
# @used-by :func:`native_executor_metadata()`
# @used-by :func:`native_review_proof()`
# @used-by :func:`native_tool_trace()`
# @used-by :func:`register()`
# @used-by :func:`verify_native_proof()`
def _cx_ops() -> dict[str, Any]:
	return {'extract_platform_homes': extract_platform_homes, 'native_review_proof': native_review_proof, 'platform_settings': platform_settings, 'registration_profile_name': registration_profile_name, 'request_day': request_day, 'settings': settings, 'shared_control': shared_control, 'shell_violations_fn': _trace_common.collect_shell_violations, 'subprocess_run': subprocess.run}
# @used-by unused
def _home(backend=None, profile=None, *, conversation_id=None):
	return _paths(backend, profile=profile, conversation_id=conversation_id)['home']
# @used-by unused
def _json_objects(value):
	return dfh_iter_embedded_json_objects(value, parse_root=False)
# @used-by :func:`_home()`
def _paths(backend=None, profile=None, *, conversation_id=None):
	return dfh_codex_paths(backend, profile=profile, conversation_id=conversation_id, platform_settings_fn=platform_settings)
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_existing_codex_review_model_gate_still_rejects_missing_actual_context()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_dynamic_folders_json_and_cleanup_without_homes()`
def _trace(home, conversation_id, *, paths=None):
	return dfh_codex_trace(home, conversation_id, paths=paths, platform_settings_fn=platform_settings)
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_codex_custom_system_paths_trace_requests_metadata_and_answers()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_instance_flag_and_codex_auto_lookup_for_handoff_and_audit()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue48_codex_subagent_aggregation_ignores_read_output_uuids()`
# @used-by :meth:`test_turn_completion.CodexTurnScannerTests.test_service_steps_parity_subagent_cache_and_bfs_depth_cap()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_external_journal_cannot_bypass_the_current_client_document_gate()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_matching_native_request_ids_reuse_an_existing_record_answer_group()`
# @used-by :meth:`test_turn_completion.CompletionCase.tracked()`
def native_answers(root, conversation_id, *, backend=None, instance=None):
	return CodexTurnScanner(root, conversation_id, backend=backend, instance=instance, _ops=_cx_ops()).scan()
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_codex_aa_and_af_use_actual_spawn_selection()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_codex_explicit_requested_actual_model_mismatch_is_reported()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_codex_missing_native_context_is_explicitly_unverified()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_codex_primary_distinguishes_requested_unknown_from_observed()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_codex_custom_system_paths_trace_requests_metadata_and_answers()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_instance_flag_and_codex_auto_lookup_for_handoff_and_audit()`
def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, backend=None, instance=None):
	return ExecutorMetadataReader(root, conversation_id, role=role, parent_id=parent_id, backend=backend, instance=instance, _ops=_cx_ops()).run()
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_changed_cwd_before_and_after_user_input_does_not_import_foreign_turn()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_injected_rules_and_environment_are_excluded_but_user_text_is_unchanged()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_missing_native_root_keeps_legacy_job_id_but_foreign_root_does_not()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_same_words_in_another_native_root_do_not_establish_ownership()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_codex_custom_system_paths_trace_requests_metadata_and_answers()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_exact_user_text_job_scope_and_cross_platform_request_merge()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_codex_requests_preserve_exact_text_without_analysis_project()`
def native_requests(root, conversation_id, *, backend=None, instance=None):
	return dfh_codex_native_requests(root, conversation_id, backend=backend, instance=instance, platform_settings_fn=platform_settings)
# @used-by :func:`_cx_ops()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_arch_native_review_proof_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_native_review_proof_and_verify_support_arch_role()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_encrypted_assignment_or_missing_native_package_execution_cannot_prove_a_review()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_native_windows_extended_path_keeps_the_profile_boundary()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_review_provenance_checks_parent_completion_model_and_assignment()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_codex_native_review_for_text_has_no_fabricated_upwork_job()`
def native_review_proof(root, parent_id, reviewer_id, *, backend=None, instance=None, write=True, wait_timeout=0.0, role='AA'):
	return ReviewProver(root, parent_id, reviewer_id, backend=backend, instance=instance, write=write, wait_timeout=wait_timeout, role=role, _ops=_cx_ops()).run()
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_codex_custom_system_paths_trace_requests_metadata_and_answers()`
def native_tool_trace(root, request):
	return ToolTraceReader(root, request, _ops=_cx_ops()).run()
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.test_codex_adapter_uses_fallback_and_rejects_wrong_native_name_without_rename()`
def register(project_dir, domain_or_topic, date_str=None):
	return ProjectRegistrar(project_dir, domain_or_topic, date_str, _ops=_cx_ops()).run()
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_missing_native_root_keeps_legacy_job_id_but_foreign_root_does_not()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_same_words_in_another_native_root_do_not_establish_ownership()`
def require_current_binding(root, conversation_id, *, backend=None, instance=None, rows=None, until=None, role='AA'):
	return dfh_codex_require_current_binding(root, conversation_id, backend=backend, instance=instance, rows=rows, until=until, role=role, platform_settings_fn=platform_settings)
# @used-by :func:`_cx_ops()`
def shared_control(request):
	return dfh_shared_control(request, platform_settings_fn=platform_settings, run_fn=subprocess.run)
# @used-by :func:`agent_tools.metrics.summarize()`
def summarize(paths, bindings=None):
	return TokenSummarizer(paths, bindings=bindings).run()
# @used-by :func:`agent_tools.platforms.adapter()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_arch_native_review_proof_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_native_review_proof_and_verify_support_arch_role()`
def verify_native_proof(root, native, package=None):
	return ProofVerifier(root, native, package, _ops=_cx_ops()).run()
