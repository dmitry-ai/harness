# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import json
import re
# 2026-11-24
# "Decompose metadata.py into modular metadata collection package":
# https://github.com/dmitry-ai/harness/issues/170
_HARNESS_TOP_KEYS = frozenset(('Time', 'Issue', 'Project', 'Journal', 'Agent', 'Trace'))
_LEADING_JSON_FENCE_RE = re.compile(r'^```json[ \t]*\r?\n([\s\S]*?)\r?\n```[ \t]*(?:\r?\n\r?\n|\r?\n|$)')
# @used-by :func:`extract_leading_metadata_header()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_headers_submodule_roundtrips_and_ignores_non_harness_json()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _is_harness_metadata_obj(obj: Any) -> bool:
	proj = obj.get('Project') if isinstance(obj, dict) else None
	has_proj = isinstance(proj, dict) and isinstance(proj.get('Path'), str) and bool(proj['Path'].strip())
	return bool(obj) and isinstance(obj, dict) and set(obj).issubset(_HARNESS_TOP_KEYS) and has_proj and any((k in obj for k in ('Time', 'Issue', 'Journal', 'Agent', 'Trace')))
# @used-by :func:`agent_tools.cleanup_lifecycle._step_response_time()`
# @used-by :func:`agent_tools.completion._record()`
# @used-by :func:`strip_leading_metadata_header()`
# @used-by :func:`test_turn_completion.assert_journal_response_body()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._prepend_issue_metadata()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_cli_logs_actual_stdin_answer_from_either_platform_without_running_cleanup()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_exact_answer_and_filename_use_the_same_istanbul_time_across_utc_midnight()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_repeated_and_concurrent_answers_never_overwrite_logs_in_the_same_minute()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_cleanup_report_writes_metadata_header_links_manifest_and_consumes_scratch_file()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.test_apply_and_cleanup_report_manifest_and_metadata_roundtrip()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_prepends_tab_indented_json_metadata_header_and_supports_opt_out()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_antigravity_prepare_prepends_metadata_and_stop_gate_and_sync_accept_clean_chat_reply()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_codex_prepare_reprepare_and_unprepared_recovery_prepend_metadata()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_render_prepend_extract_and_strip_tab_indented_json_header()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_headers_submodule_roundtrips_and_ignores_non_harness_json()`
# @used-by :meth:`test_stop_emergency_capture_and_foreign_sync.StopEmergencyCaptureAndForeignSyncTests.test_stop_gate_fail_open_persists_emergency_capture_and_sync_avoids_duplicate()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def extract_leading_metadata_header(text: str) -> tuple[dict[str, Any] | None, str]:
	r: tuple[dict[str, Any] | None, str] = (None, text)
	m = _LEADING_JSON_FENCE_RE.match(text) if isinstance(text, str) and text.startswith('```json') else None
	if None is not m:
		try:
			parsed = json.loads(m.group(1))
		except ValueError:
			parsed = None
		if _is_harness_metadata_obj(parsed):
			r = (parsed, text[m.end():])
	return r
# @used-by :func:`agent_tools.completion._record()`
# @used-by :func:`agent_tools.stop_emergency_capture._build_emergency_response()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._prepend_issue_metadata()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_render_prepend_extract_and_strip_tab_indented_json_header()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_headers_submodule_roundtrips_and_ignores_non_harness_json()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def prepend_metadata_header(body: str, data: dict[str, Any]) -> str:
	return render_metadata_header(data) + strip_leading_metadata_header(body)
# @used-by :func:`agent_tools.cleanup_audit.record_cleanup_answer_log()`
# @used-by :func:`agent_tools.cli_registry._exec_problem_metadata()`
# @used-by :func:`prepend_metadata_header()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_text_core_and_review_authorize_handle_metadata_prefixed_response()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_render_prepend_extract_and_strip_tab_indented_json_header()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_headers_submodule_roundtrips_and_ignores_non_harness_json()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def render_metadata_header(data: dict[str, Any]) -> str:
	return '```json\n' + json.dumps(data, ensure_ascii=False, indent='\t') + '\n```\n\n'
# @used-by :func:`agent_tools.cleanup_audit.record_cleanup_answer_log()`
# @used-by :func:`agent_tools.completion._matches_recorded_response()`
# @used-by :func:`agent_tools.completion._record()`
# @used-by :func:`agent_tools.journal.norm_journal_response_text()`
# @used-by :func:`agent_tools.review.authorize()`
# @used-by :func:`agent_tools.shadow_replay._load_candidate()`
# @used-by :func:`agent_tools.statements.validate_df_analysis()`
# @used-by :func:`agent_tools.stop_emergency_capture._record_emergency_files()`
# @used-by :func:`agent_tools.text_core.check_response()`
# @used-by :func:`check_stop_gate._evaluate_prepared_match()`
# @used-by :func:`prepend_metadata_header()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._finalize_stage()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.adopt_requests()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_render_prepend_extract_and_strip_tab_indented_json_header()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_headers_submodule_roundtrips_and_ignores_non_harness_json()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def strip_leading_metadata_header(text: str) -> str:
	return extract_leading_metadata_header(text)[1]
