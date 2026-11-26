# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class UnhandledVerdictChecker:
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.has_unhandled_verdicts()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def __init__(self, state: dict, evaluator, package: dict, latest: dict | None=None) -> None:
		self.__state = state
		self.__evaluator = evaluator
		self.__package = package
		self.__latest = latest
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.has_unhandled_verdicts()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def has_unhandled(self) -> bool:
		active = self.__evaluator.latest_for_subject(self.__package) if None is self.__latest else self.__latest
		ordered = {entry.get('id'): idx for idx, entry in enumerate(self.__state['reviews'])}
		approved = [entry for entry in active.values() if 'approved' == entry.get('result') and entry.get('independent') and self.__evaluator.findings_closed(entry) and self.__evaluator.entry_proof_current(entry)]
		r = False
		for entry in active.values():
			if not ('approved' == entry.get('result') and self.__evaluator.findings_closed(entry)) and (not any((ordered[followup['id']] > ordered[entry['id']] and entry['id'] in followup.get('addresses_reviews', []) for followup in approved))):
				r = True
				break
		return r
