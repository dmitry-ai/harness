# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# Return True iff `v` is an `int` instance and not a `bool`.
# @used-by :func:`Df.Harness.lib.hook_addon_ops._runtime_issues_from_data()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_text_source_and_strict_validation_helpers()`
def df_is_int_strict(v: Any) -> bool:
	return isinstance(v, int) and (not isinstance(v, bool))
# Return True iff `v` is a string with non-whitespace characters.
# @used-by :func:`agent_tools.review.is_nonempty_text()`
# @used-by :func:`agent_tools.review_alignment._nonempty()`
# @used-by :meth:`Df.Harness.Experiment.BrowserStepAuditor.BrowserStepAuditor.__check_phase()`
# @used-by :meth:`Df.Harness.Experiment.NativeGeoExtractor.NativeGeoExtractor.extract_verified_country()`
# @used-by :meth:`Df.Harness.Experiment.PlanPreparer.PlanPreparer.__resolve_previous()`
# @used-by :meth:`Df.Harness.Experiment.RequirementValidator.RequirementValidator.__check_fields()`
# @used-by :meth:`Df.Harness.Experiment.RequirementValidator.RequirementValidator.__check_method_and_scope()`
# @used-by :meth:`Df.Harness.Experiment.ResultValidator.ResultValidator.issues()`
# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.__check_admin()`
# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.__check_header()`
# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.__check_serp()`
# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__init_run()`
# @used-by :meth:`Df.Harness.Review.AddressedReviewResolver.AddressedReviewResolver.__resolve_one()`
# @used-by :meth:`Df.Harness.Review.AlignmentValidator.AlignmentValidator.issues()`
# @used-by :meth:`Df.Harness.Review.ClaimEvidenceCollector.ClaimEvidenceCollector.__collect_claim()`
# @used-by :meth:`Df.Harness.Review.ClaimEvidenceCollector.ClaimEvidenceCollector.claim_index()`
# @used-by :meth:`Df.Harness.Review.ClaimEvidenceCollector.ClaimEvidenceCollector.pairs()`
# @used-by :meth:`Df.Harness.Review.ClaimEvidenceCollector.ClaimEvidenceCollector.section_map()`
# @used-by :meth:`Df.Harness.Review.ClaimReviewValidator.ClaimReviewValidator.__check_item()`
# @used-by :meth:`Df.Harness.Review.ClaimReviewValidator.ClaimReviewValidator.__check_qualified()`
# @used-by :meth:`Df.Harness.Review.ClaimTargetBuilder.ClaimTargetBuilder.build()`
# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.__check_omitted()`
# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.__process_item()`
# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.__validate_spec()`
# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
# @used-by :meth:`Df.Harness.Review.EnvelopeValidator.EnvelopeValidator.__package_issues()`
# @used-by :meth:`Df.Harness.Review.EnvelopeValidator.EnvelopeValidator.issues()`
# @used-by :meth:`Df.Harness.Review.FalsifierValidator.FalsifierValidator.__check_disproved()`
# @used-by :meth:`Df.Harness.Review.FalsifierValidator.FalsifierValidator.__check_tier0_source()`
# @used-by :meth:`Df.Harness.Review.FindingValidator.FindingValidator.__check_fields()`
# @used-by :meth:`Df.Harness.Review.FindingValidator.FindingValidator.__check_one()`
# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.update()`
# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.prepare()`
# @used-by :meth:`Df.Harness.Review.ReportAuthenticator.ReportAuthenticator.__auth_independent()`
# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.__check_text_checks()`
# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.__init__()`
# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__load_and_check()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_text_source_and_strict_validation_helpers()`
def df_is_sne(v: Any) -> bool:
	return isinstance(v, str) and bool(v.strip())