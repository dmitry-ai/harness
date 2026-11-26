# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Analysis.IssueHintAnnotator import IssueHintAnnotator
from Df.Harness.Review.ClaimReviewValidator import ClaimReviewValidator
from Df.Harness.Review.EnvelopeValidator import EnvelopeValidator
from Df.Harness.Review.FalsifierValidator import FalsifierValidator
from Df.Harness.Review.FindingValidator import FindingValidator
from Df.Qa.lib.validation.check_strict import df_is_sne
REVIEW_SCHEMA = 2
SCOPES = ('identity', 'concerns', 'misconceptions', 'causes', 'methods', 'kb_consistency', 'response')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ReportValidator:
	# @used-by :func:`agent_tools.review.report_issues()`
	# @used-by :func:`agent_tools.text_review._issues()`
	# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__load_and_check()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_report_validator_classes()`
	# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_report_validator_covers_falsifier_and_text_checks()`
	# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_validators_emit_actionable_hints()`
	def __init__(self, package: dict, *, candidate=None, text_checks=(), source_reviewer=None, require_envelope: bool=False) -> None:
		from agent_tools.path_registry import canonicalize_root_dir
		self.candidate = candidate
		self.expected = {c['claim_id'] for c in package['claims']}
		self.package = package
		self.package_claims = {c['claim_id']: c for c in package['claims']}
		self.pkg_root = canonicalize_root_dir(package['project_root']) if df_is_sne(package.get('project_root')) else None
		self.require_envelope = require_envelope
		self.source_reviewer = source_reviewer
		self.targets = {c['claim_id']: c['essence'] for c in package['claims']}
		self.text_checks = tuple(text_checks)
	# @used-by :meth:`ReportValidator.validate()`
	def __check_text_checks(self, data: dict, issues: list[str]) -> None:
		if self.text_checks:
			for item in data.get('claim_reviews', []):
				if isinstance(item, dict):
					checks = item.get('text_checks')
					if not isinstance(checks, dict) or any((not df_is_sne(checks.get(key)) for key in self.text_checks)):
						issues.append(str(item.get('claim_id')) + ': assess source applicability, scope, role, relevance, deduplication and numerical provenance')
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`ReportValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_report_validator_classes()`
	# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_report_validator_covers_falsifier_and_text_checks()`
	@staticmethod
	def is_falsifier_report(data: dict) -> bool:
		return 'falsifier' == data.get('review_mode') or ('disproved_claims' in data and 'claim_reviews' not in data)
	# @used-by :func:`agent_tools.review.report_issues()`
	# @used-by :func:`agent_tools.text_review._issues()`
	# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__load_and_check()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_report_validator_classes()`
	# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_report_validator_covers_falsifier_and_text_checks()`
	# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_validators_emit_actionable_hints()`
	def validate(self, data: dict) -> list[str]:
		r = EnvelopeValidator(data, self.package, review_schema=REVIEW_SCHEMA, scopes=SCOPES, require_envelope=self.require_envelope).issues()
		if self.is_falsifier_report(data):
			FalsifierValidator(self.package, self.expected, self.pkg_root).check(data, r)
		else:
			ClaimReviewValidator(self.package, self.expected, self.package_claims, self.targets, self.candidate).check(data, r)
		FindingValidator(self.package, self.expected).check(data, r)
		self.__check_text_checks(data, r)
		if None is not self.source_reviewer:
			try:
				self.source_reviewer(data, self.package)
			except (OSError, ValueError, KeyError, TypeError) as exc:
				r.append(str(exc))
		return IssueHintAnnotator('review', r).annotate()
