# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# 2026-11-28
# "Build ProblemReportFixtureBuilder and hierarchical DOC-5 regression test matrix":
# https://github.com/dmitry-ai/harness/issues/431
from Df.Harness.Completion.BlockedReportAuditor import BlockedReportAuditor
from Df.Harness.lib.blocked_report_ops import _BLOCKER_HINT_RE, _CLIENT_HM_CLAIM_RE, _FENCED_RE, _HM_CLAIM_RE, _STAGE_HEADING_RE, _authorize_workflow_errors, _continuation_blocker_issue, _is_doc5_blocker_analysis, _run_runner_audits, _standard_workflow_errors, dfh_audit_runner_workflow_scope as audit_runner_workflow_scope, dfh_evaluate_check_workflow_errors as evaluate_check_workflow_errors, dfh_evaluate_runner_code_hygiene as evaluate_runner_code_hygiene, dfh_pending_workflow_alignment_issues as pending_workflow_alignment_issues, dfh_prepare_and_sync_authorized_workflow as prepare_and_sync_authorized_workflow, dfh_record_blocked_report_entry as record_blocked_report_entry, dfh_sync_authorized_workflow_requests as sync_authorized_workflow_requests
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.test_blocked_report_still_rejects_client_claim_ids_inside_doc5()`
def blocked_report_issues(pp, response: str, *, workflow_exists: bool, is_finalized: bool) -> list[str]:
	return BlockedReportAuditor(pp, response, workflow_exists=workflow_exists, is_finalized=is_finalized).run()