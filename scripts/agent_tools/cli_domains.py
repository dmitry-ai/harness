# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.lib.cli import dfh_collect_urls
from Df.Harness.lib.cli_domain_ops import OPERATION_HANDLERS, _load_consumed, _op_adopt_requests, _op_capture_dom, _op_check_project, _op_collect, _op_collect_browser, _op_collect_http, _op_evidence_query, _op_extract, _op_extract_file, _op_git_read, _op_metrics, _op_native_executor_metadata, _op_native_review_proof, _op_prepare_experiment, _op_prepare_review, _op_question_add, _op_question_claim, _op_question_finish, _op_question_handoff, _op_question_search, _op_record_answer, _op_record_experiment, _op_record_review, _op_render_analysis, _op_resume, _op_review_disposition, _op_review_input, _op_save_analysis, _op_source_ref, _op_stage, _op_status, _op_sync_attachments, _op_unadopt_requests, _resolve_project_input
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _collect_urls(args, *, require_nonempty: bool=True) -> list[str]:
	return dfh_collect_urls(args, require_nonempty=require_nonempty)