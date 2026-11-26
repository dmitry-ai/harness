# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ContractBinder:
	# @used-by :func:`agent_tools.review_alignment.bind_contract_envelope()`
	# @used-by :meth:`Df.Harness.Review.InputReceiptBuilder.InputReceiptBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
	def __init__(self, contract: dict, package_path: str, package_sha: str, review_mode: str | None=None) -> None:
		self.__contract = contract
		self.__pkg_path = package_path
		self.__pkg_sha = package_sha
		self.__mode = review_mode
	# @used-by :func:`agent_tools.review_alignment.bind_contract_envelope()`
	# @used-by :meth:`Df.Harness.Review.InputReceiptBuilder.InputReceiptBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
	def bind(self) -> dict:
		r = dict(self.__contract)
		if 'falsifier' == self.__mode and isinstance(r.get('falsifier_required_top_level_fields'), list):
			r['required_top_level_fields'] = list(r['falsifier_required_top_level_fields'])
		r['expected_package'] = self.__pkg_path
		r['expected_package_sha256'] = self.__pkg_sha
		return r
