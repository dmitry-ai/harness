# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.Meta.HeaderRenderer import HeaderRenderer
# 2026-11-24
# "Decompose metadata.py into modular metadata collection package":
# https://github.com/dmitry-ai/harness/issues/170
# 2026-11-26
# "Surface ask_question clarifications in journal headers and require deferral disclosure":
# https://github.com/dmitry-ai/harness/issues/376
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
_HARNESS_TOP_KEYS = HeaderRenderer.HARNESS_TOP_KEYS
_LEADING_JSON_FENCE_RE = HeaderRenderer.LEADING_JSON_FENCE_RE
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_headers_submodule_roundtrips_and_ignores_non_harness_json()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _is_harness_metadata_obj(obj: Any) -> bool:
	return HeaderRenderer.is_harness_metadata_obj(obj)
# @used-by :func:`Df.Harness.lib.cleanup_lifecycle_ops._step_response_time()`
# @used-by :func:`Df.Harness.lib.completion_record._maybe_prepend_journal_metadata()`
# @used-by :func:`test_turn_completion.assert_journal_response_body()`
# @used-by :meth:`Df.Harness.Issue.IssueMetadataPrepender.IssueMetadataPrepender.prepend()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_cli_logs_actual_stdin_answer_from_either_platform_without_running_cleanup()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_exact_answer_and_filename_use_the_same_istanbul_time_across_utc_midnight()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_repeated_and_concurrent_answers_never_overwrite_logs_in_the_same_minute()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_cleanup_report_isolates_conflicting_host_a0_and_codex_env()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_cleanup_report_writes_metadata_header_links_manifest_and_consumes_scratch_file()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.test_apply_and_cleanup_report_manifest_and_metadata_roundtrip()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_prepends_tab_indented_json_metadata_header_and_supports_opt_out()`
# @used-by :meth:`test_journal_clarifications_and_disclosure.JournalClarificationsAndDisclosureTests.test_build_journal_metadata_includes_clarifications_and_preserves_user_input_hash()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_antigravity_prepare_prepends_metadata_and_stop_gate_and_sync_accept_clean_chat_reply()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_codex_prepare_reprepare_and_unprepared_recovery_prepend_metadata()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_render_prepend_extract_and_strip_tab_indented_json_header()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_headers_submodule_roundtrips_and_ignores_non_harness_json()`
# @used-by :meth:`test_stop_emergency_capture_and_foreign_sync.StopEmergencyCaptureAndForeignSyncTests.test_stop_gate_fail_open_persists_emergency_capture_and_sync_avoids_duplicate()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def extract_leading_metadata_header(text: str) -> tuple[dict[str, Any] | None, str]:
	return HeaderRenderer.extract_leading(text)
# @used-by :func:`Df.Harness.lib.completion_record._maybe_prepend_journal_metadata()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._build_emergency_response()`
# @used-by :meth:`Df.Harness.Issue.IssueMetadataPrepender.IssueMetadataPrepender.prepend()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_render_prepend_extract_and_strip_tab_indented_json_header()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_headers_submodule_roundtrips_and_ignores_non_harness_json()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def prepend_metadata_header(body: str, data: dict[str, Any]) -> str:
	return HeaderRenderer.prepend(body, data)
# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_record_cleanup_answer_log()`
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_problem_metadata()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_text_core_and_review_authorize_handle_metadata_prefixed_response()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_render_prepend_extract_and_strip_tab_indented_json_header()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_headers_submodule_roundtrips_and_ignores_non_harness_json()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def render_metadata_header(data: dict[str, Any]) -> str:
	return HeaderRenderer(data).render()
# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_record_cleanup_answer_log()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_matches_recorded_response()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_record()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops.dfh_evaluate_prepared_match()`
# @used-by :func:`Df.Harness.lib.journal_core.dfh_norm_journal_response_text()`
# @used-by :func:`agent_tools.statements.validate_df_analysis()`
# @used-by :func:`agent_tools.text_core.check_response()`
# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.authorize()`
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__load_candidate()`
# @used-by :meth:`Df.Harness.Workflow.FinalizeStageRunner.FinalizeStageRunner.__load_latest_reply()`
# @used-by :meth:`Df.Harness.Workflow.RequestAdopter.RequestAdopter.__saved_answers()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_render_prepend_extract_and_strip_tab_indented_json_header()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_headers_submodule_roundtrips_and_ignores_non_harness_json()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def strip_leading_metadata_header(text: str) -> str:
	return HeaderRenderer.strip_leading(text)
