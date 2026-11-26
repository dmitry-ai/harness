# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Qa.lib.validation.check_strict import df_is_sne
TARGET_CLAIM_RULE = 'Copy claims[i].essence verbatim in its original language without translating or paraphrasing (see claim_targets)'
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AlignmentValidator:
	# @used-by :func:`agent_tools.review_alignment.alignment_issues()`
	# @used-by :meth:`Df.Harness.Review.ClaimReviewValidator.ClaimReviewValidator.__check_alignment()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
	def __init__(self, ident: str, alignment, expected_target: str | None) -> None:
		self.__ident = ident
		self.__alignment = alignment
		self.__expected = expected_target
	# @used-by :func:`agent_tools.review_alignment.alignment_issues()`
	# @used-by :meth:`Df.Harness.Review.ClaimReviewValidator.ClaimReviewValidator.__check_alignment()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
	def issues(self) -> list[str]:
		r: list[str] = []
		if not isinstance(self.__alignment, dict):
			r.append(f'{self.__ident}: test_alignment must be an object binding target_claim, tested_claim, relationship, rationale and a concrete counterexample')
		else:
			actual = self.__alignment.get('target_claim')
			if actual != self.__expected:
				r.append(f'{self.__ident}: test_alignment.target_claim mismatch (copy claims[i].essence verbatim without translation): expected {self.__expected!r}, got {actual!r}')
			missing = [k for k in ('tested_claim', 'rationale', 'counterexample') if not df_is_sne(self.__alignment.get(k))]
			if missing:
				r.append(f"{self.__ident}: test_alignment missing nonempty field(s): {', '.join(missing)}")
			rel = self.__alignment.get('relationship')
			if rel not in ('direct', 'proxy', 'irrelevant'):
				r.append(f'{self.__ident}: test_alignment.relationship must be direct, proxy or irrelevant, got {rel!r}')
		return r
