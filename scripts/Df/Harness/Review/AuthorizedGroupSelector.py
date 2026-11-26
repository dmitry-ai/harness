# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AuthorizedGroupSelector:
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.select_authorized_group()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def __init__(self, evaluator, groups: dict, *, allow_routine_self: bool=True, allow_falsifier_or_cached: bool=True) -> None:
		self.__evaluator = evaluator
		self.__groups = groups
		self.__allow_self = allow_routine_self
		self.__allow_fast = allow_falsifier_or_cached
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.select_authorized_group()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def select(self):
		r = None
		for path, (package, reviews) in reversed(list(self.__groups.items())):
			eligible = [item for item in reviews if (self.__allow_self and 'routine' == package['risk']) or item.get('independent')]
			latest = self.__evaluator.latest_for_subject(package)
			if not self.__evaluator.has_unhandled_verdicts(package, latest):
				eligible = [item for item in eligible if latest[item['reviewer_id']]['id'] == item['id']]
				if self.__evaluator.quorum_satisfied(package, latest, eligible, allow_falsifier_or_cached=self.__allow_fast):
					r = (path, package, eligible)
					break
		return r
