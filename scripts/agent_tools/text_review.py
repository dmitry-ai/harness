# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Text.ApprovalIntegrityChecker import ApprovalIntegrityChecker
from Df.Harness.Text.ReviewAuthorizer import ReviewAuthorizer
from Df.Harness.Text.ReviewPackageReader import ReviewPackageReader
from Df.Harness.Text.ReviewPreparer import ReviewPreparer
from Df.Harness.Text.ReviewRecorder import ReviewRecorder
from Df.Harness.lib.text_review import SCOPES, TEXT_CHECKS, dfh_source_reviews as _source_reviews, dfh_text_report_contract as report_contract, dfh_text_review_issues as _issues, dfh_text_review_state as _state
from .review import register_package_handler
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_historical_successor_lineage_preserves_history_when_later_reviewer_trace_is_unverified()`
def approval_integrity(root, approval, *, versioned_inputs=(), require_live_proof=True):
	return ApprovalIntegrityChecker(root, approval, versioned_inputs=versioned_inputs, require_live_proof=require_live_proof).check()
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_aged_real_source_and_nested_semantic_approval_preserve_both_platforms()`
# @used-by :mod:`agent_tools.text_review`
def authorize(root, check, *, applied=False):
	return ReviewAuthorizer(root, check, applied=applied).authorize()
authorize._df_default_review_facade = True
# @used-by :meth:`test_text_integration.TextReviewTests.package()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_same_rejected_subject_cannot_be_reset_by_a_new_operation_path()`
def prepare(root, check, parent_id, spec=None):
	return ReviewPreparer(root, check, parent_id, spec).prepare()
# @used-by :mod:`agent_tools.text_review`
def read_package(root, reference, *, require_current=True, applied=False):
	return ReviewPackageReader(root, reference, require_current=require_current, applied=applied).read()
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.check_and_review()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_full_native_review_fixture_requires_and_preserves_source_assessments()`
# @used-by :meth:`test_text_integration.TextReviewTests.record_fixture()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_parent_cannot_authorize_its_own_text()`
def record(root, report, *, parent_id, reviewer_id, native_evidence):
	return ReviewRecorder(root, report, parent_id=parent_id, reviewer_id=reviewer_id, native_evidence=native_evidence).record()
register_package_handler('client_text', package_reader=read_package, contract_factory=report_contract)
