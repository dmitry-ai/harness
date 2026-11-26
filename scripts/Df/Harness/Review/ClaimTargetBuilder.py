# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Qa.lib.validation.check_strict import df_is_sne
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ClaimTargetBuilder:
	# @used-by :func:`agent_tools.review_alignment.build_claim_targets()`
	# @used-by :meth:`Df.Harness.Review.InputReceiptBuilder.InputReceiptBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
	def __init__(self, claims: list | tuple | None) -> None:
		self.__claims = claims
	# @used-by :func:`agent_tools.review_alignment.build_claim_targets()`
	# @used-by :meth:`Df.Harness.Review.InputReceiptBuilder.InputReceiptBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
	def build(self) -> dict[str, str]:
		return {c['claim_id']: c['essence'] for c in (self.__claims or ()) if isinstance(c, dict) and df_is_sne(c.get('claim_id')) and isinstance(c.get('essence'), str)}
