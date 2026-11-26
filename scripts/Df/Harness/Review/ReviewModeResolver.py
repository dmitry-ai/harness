# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ReviewModeResolver:
	# @used-by :func:`agent_tools.review_alignment.resolve_package_review_mode()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
	def __init__(self, spec: object, package: dict, evaluator) -> None:
		self.__spec = spec
		self.__package = package
		self.__evaluator = evaluator
	# @used-by :func:`agent_tools.review_alignment.resolve_package_review_mode()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
	def resolve(self) -> str | None:
		if isinstance(self.__spec, dict) and self.__spec.get('review_mode') in ('standard', 'falsifier'):
			r: str | None = self.__spec['review_mode']
		elif 'significant' == self.__package.get('risk'):
			has_esc = self.__evaluator.significant_findings(self.__package['subject_sha256']) or any(('approved' != item.get('result') for item in self.__evaluator.latest_for_subject(self.__package).values()))
			r = 'standard' if has_esc else 'falsifier'
		else:
			r = None
		return r
