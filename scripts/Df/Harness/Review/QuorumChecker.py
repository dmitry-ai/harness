# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class QuorumChecker:
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.quorum_satisfied()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def __init__(self, evaluator, package: dict, latest: dict, eligible: list[dict], *, allow_falsifier_or_cached: bool=True) -> None:
		self.__evaluator = evaluator
		self.__package = package
		self.__latest = latest
		self.__eligible = eligible
		self.__allow_fast = allow_falsifier_or_cached
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.quorum_satisfied()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def satisfied(self) -> bool:
		required = 1
		if 'significant' == self.__package['risk']:
			required = 2
			if self.__allow_fast:
				has_esc = self.__evaluator.significant_findings(self.__package['subject_sha256']) or any(('approved' != item.get('result') for item in self.__latest.values()))
				delta = self.__package.get('merkle_delta') or {}
				all_cached = bool(delta.get('cached_claim_ids')) and (not bool(delta.get('unverified_claim_ids')))
				if (not has_esc) and (any(('falsifier' == item.get('review_mode') for item in self.__eligible)) or all_cached):
					required = 1
		return len({item['reviewer_id'] for item in self.__eligible}) >= required
