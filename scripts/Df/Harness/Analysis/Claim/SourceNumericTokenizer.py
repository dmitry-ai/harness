# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class SourceNumericTokenizer:
	# @used-by :func:`agent_tools.claims.source_numeric_tokens()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.NumericGrounding.NumericGrounding.__compute()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_numbers()`
	# @used-by :meth:`Df.Harness.Review.ClaimReviewValidator.ClaimReviewValidator.__check_numeric_grounding()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	def __init__(self, raw_text: str) -> None:
		self.__raw_text = raw_text or ''
	# @used-by :func:`agent_tools.claims.source_numeric_tokens()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.NumericGrounding.NumericGrounding.__compute()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_numbers()`
	# @used-by :meth:`Df.Harness.Review.ClaimReviewValidator.ClaimReviewValidator.__check_numeric_grounding()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	def tokenize(self) -> set[str]:
		r: set[str] = set()
		for sp_tok in re.findall('\\d{1,3}(?:[ \\u00a0\\u202f]\\d{3})+(?:[.,]\\d+)?', self.__raw_text):
			compact = re.sub('[ \\u00a0\\u202f]', '', sp_tok)
			r.add(compact.replace(',', '.'))
			r.add(compact.replace(',', ''))
		for tok in re.findall('\\d+(?:[.,]\\d+)*', self.__raw_text):
			norm_dot, no_comma = (tok.replace(',', '.'), tok.replace(',', ''))
			r.update((norm_dot, no_comma))
			r.update(norm_dot.split('.'))
			r.update(no_comma.split('.'))
			if '.' in no_comma:
				r.add(no_comma.rstrip('0').rstrip('.') or '0')
		return r