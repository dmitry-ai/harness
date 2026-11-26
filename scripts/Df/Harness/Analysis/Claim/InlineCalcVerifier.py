# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from Df.Harness.Analysis.Claim.SafeArithmetic import SafeArithmetic
import re
_ALLOWED_CONSTANTS = frozenset({'100', '1000', '1024', '60', '24', '3600'})
_NUM_EXPR_TOK = '-?\\d+(?:[ \\u00a0\\u202f]\\d{3})*(?:[.,]\\d+)*'
_INLINE_EQ_RE = re.compile('(?<![A-Za-z0-9_./])' + f'((?:\\(\\s*)*{_NUM_EXPR_TOK}(?:\\s*\\))*(?:\\s*[+\\-*/\\u2212\\u00d7\\u00f7]\\s*(?:\\(\\s*)*{_NUM_EXPR_TOK}(?:\\s*\\))*)+)' + '\\s*(=|\\u2248|~=|\\u2245)\\s*' + f'({_NUM_EXPR_TOK})(\\s*%)?')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class InlineCalcVerifier:
	# @used-by :func:`agent_tools.claims.extract_verified_inline_calc_numbers()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.NumericGrounding.NumericGrounding.__compute()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_numbers()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	def __init__(self, text: str, grounded_nums: set[str]) -> None:
		self.__text = text
		self.__grounded = grounded_nums
	# @used-by :meth:`InlineCalcVerifier.__process_match()`
	def __decimal_matches(self, computed: Decimal, stated_raw: str, is_approx: bool, is_pct: bool) -> bool:
		clean = re.sub('(?<=\\d)[ \\u00a0\\u202f](?=\\d{3}(?!\\d))', '', stated_raw.strip())
		clean = re.sub('(?<=\\d),(?=\\d{3}(?!\\d))', '', clean).replace(',', '.')
		r = False
		try:
			stated = Decimal(clean)
		except InvalidOperation:
			stated = None
		if None is not stated:
			q = Decimal(1).scaleb(-(len(clean.split('.')[1]) if '.' in clean else 0))
			cands = [computed, computed * Decimal(100)] if is_pct else [computed]
			with localcontext() as ctx:
				ctx.prec = 50
				r = any((cand.quantize(q, rounding=ROUND_HALF_UP) == stated or cand == stated or (is_approx and abs(cand - stated) <= q) for cand in cands))
		return r
	# @used-by :meth:`InlineCalcVerifier.__process_match()`
	def __expand_lhs(self, lhs: str, expanded: set[str]) -> None:
		for sp_m in re.finditer('\\b(\\d{1,3}(?:[ \\u00a0\\u202f]\\d{3})+(?:[.,]\\d+)?)\\b', lhs):
			sp_parts = re.findall('\\d+(?:[.,]\\d+)?', sp_m.group(1))
			if sp_parts and all((p.replace(',', '.') in expanded or p.replace(',', '') in expanded for p in sp_parts)):
				expanded.add(re.sub('[ \\u00a0\\u202f]', '', sp_m.group(1)).replace(',', '.'))
	# @used-by :meth:`InlineCalcVerifier.extract()`
	def __process_match(self, m: re.Match, expanded: set[str], verified: set[str], errors: list[str]) -> None:
		lhs, op_sym, rhs_raw, pct_suf = (m.group(1), m.group(2), m.group(3), bool(m.group(4)))
		self.__expand_lhs(lhs, expanded)
		val, lit_tokens = SafeArithmetic(lhs).evaluate()
		if None is not val and 2 <= len(lit_tokens) and all((tok in expanded or tok.replace(',', '') in expanded or tok in _ALLOWED_CONSTANTS for tok in lit_tokens)):
			if self.__decimal_matches(val, rhs_raw, '=' != op_sym, pct_suf):
				self.__record_rhs(rhs_raw, verified)
			elif '=' == op_sym:
				with localcontext() as ctx:
					ctx.prec = 28
					exp_s = str(val.normalize())
				errors.append(f'derived_calc mismatch: "{lhs.strip()} = {rhs_raw}" evaluates to {exp_s}, not {rhs_raw}')
	# @used-by :meth:`InlineCalcVerifier.__process_match()`
	def __record_rhs(self, rhs_raw: str, verified: set[str]) -> None:
		clean_rhs = re.sub('(?<=\\d)[ \\u00a0\\u202f](?=\\d{3}(?!\\d))', '', rhs_raw.strip())
		norm_dot = clean_rhs.replace(',', '.')
		no_comma = re.sub('(?<=\\d),(?=\\d{3}(?!\\d))', '', clean_rhs).replace(',', '.')
		verified.update((norm_dot, no_comma))
		verified.update(norm_dot.split('.'))
		verified.update(no_comma.split('.'))
		for sub_tok in re.findall('\\d+(?:[.,]\\d+)*', rhs_raw):
			verified.add(sub_tok.replace(',', '.'))
			verified.add(sub_tok.replace(',', ''))
	# @used-by :func:`agent_tools.claims.extract_verified_inline_calc_numbers()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.NumericGrounding.NumericGrounding.__compute()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_numbers()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	def extract(self) -> tuple[set[str], list[str]]:
		verified: set[str] = set()
		errors: list[str] = []
		if isinstance(self.__text, str) and self.__text:
			expanded = set(self.__grounded)
			for g in list(self.__grounded):
				expanded.add(g.replace(',', ''))
				expanded.add(g.replace(',', '.'))
			for m in _INLINE_EQ_RE.finditer(self.__text):
				self.__process_match(m, expanded, verified, errors)
		return (verified, errors)