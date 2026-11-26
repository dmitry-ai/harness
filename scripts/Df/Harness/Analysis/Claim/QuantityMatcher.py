# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import json
import re
import unicodedata
_UNIT_MAP = {'EUR': ('EUR', '\u20ac'), 'GBP': ('GBP', '\u00a3'), 'USD': ('USD', 'US$'), 'CAD': ('CAD', 'CA$', 'C$'), 'AUD': ('AUD', 'AU$', 'A$'), 'JPY': ('JPY', 'JP\u00a5'), 'CNY': ('CNY', 'CN\u00a5', 'RMB'), 'percent': ('percent', '%')}
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class QuantityMatcher:
	# @used-by :func:`agent_tools.claims._quantity_matches()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.CalculationValidator.CalculationValidator.__load_operands()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def __init__(self, reference: dict, decimal_value: str, unit: str, source_context: str | None=None) -> None:
		self.__ref = reference
		self.__dec_str = decimal_value
		self.__unit = unit
		self.__ctx = source_context
	# @used-by :meth:`QuantityMatcher.__check_json()`
	def __check_json_pair(self, pairs: list[tuple]) -> bool:
		r = False
		if 1 == len(pairs):
			amount, currency = pairs[0]
			if type(amount) in (str, Decimal) and currency == self.__unit:
				try:
					r = Decimal(amount).is_finite() and Decimal(amount) == Decimal(self.__dec_str)
				except InvalidOperation:
					r = False
		return r
	# @used-by :meth:`QuantityMatcher.matches()`
	def __check_json(self) -> bool | None:
		r: bool | None = None
		if 'json_pointer' == self.__ref.get('locator', {}).get('type'):
			try:
				selected = json.loads(self.__ctx if None is not self.__ctx else self.__ref['quote'], parse_float=Decimal, parse_int=Decimal)
			except (TypeError, ValueError):
				selected = None
			if isinstance(selected, dict):
				pairs = [(selected[v], selected[u]) for v, u in (('amount', 'currency'), ('value', 'unit')) if v in selected and u in selected]
				if pairs:
					r = self.__check_json_pair(pairs)
		return r
	# @used-by :meth:`QuantityMatcher.__check_text()`
	def __check_excerpt(self, exc: re.Match, text: str, tokens: list[re.Match], expected: Decimal, unit_tokens: tuple[str, ...]) -> bool:
		nums = [n for n in tokens if exc.start() <= n.start() and n.end() <= exc.end() and Decimal(n[0]) == abs(expected)]
		if 1 != len(nums):
			r = False
		else:
			cands = self.__quantities(text, nums[0], unit_tokens)
			r = bool(cands) and (not any((a != expected or st < exc.start() or en > exc.end() for a, st, en in cands)))
		return r
	# @used-by :meth:`QuantityMatcher.matches()`
	def __check_text(self) -> bool:
		if re.search('<\\s*/?\\s*[A-Za-z][^>]*>', self.__ref['quote']):
			raise ValueError('Raw markup excerpts are ambiguous numeric provenance; use a complete signed quantity in parsed source text or a structured JSON value/unit object')
		norm = lambda s: ' '.join(s.replace(',', '.').replace('\u2212', '-').split())
		quote = norm(self.__ref['quote'])
		text = norm(self.__ctx if None is not self.__ctx else self.__ref['quote'])
		excerpts = list(re.finditer(re.escape(quote), text))
		if not excerpts:
			r = False
		else:
			expected = Decimal(self.__dec_str)
			tokens = list(re.finditer('(?<![\\d.])[0-9]+(?:\\.[0-9]+)?(?![\\d.])', text))
			unit_tokens = _UNIT_MAP.get(self.__unit, (self.__unit,))
			r = all((self.__check_excerpt(exc, text, tokens, expected, unit_tokens) for exc in excerpts))
		return r
	# @used-by :meth:`QuantityMatcher.__quantities()`
	def __collect_unit_cands(self, text: str, number: re.Match, token: str, cands: list[tuple]) -> None:
		escaped = re.escape(token)
		b_pre = '(?<!\\w)' if token[0].isalnum() else ''
		prefix = re.search(b_pre + escaped + '\\s*([+-]?)\\s*$', text[:number.start()])
		if prefix:
			leading, start = self.__sign_before(text, prefix.start())
			if None is not leading and (not (leading and prefix[1])):
				cands.append((leading or prefix[1], start, number.end()))
		b_suf = '(?!\\w)' if token[-1].isalnum() else ''
		suffix = re.match('\\s*' + escaped + b_suf, text[number.end():])
		if suffix:
			sign, start = self.__sign_before(text, number.start())
			prec = text[:start]
			ambig = (not sign) and (prec[-1:].isalnum() or bool(re.search('[0-9.]\\s+$', prec)))
			if None is not sign and (not ambig):
				cands.append((sign, start, number.end() + suffix.end()))
	# @used-by :meth:`QuantityMatcher.__check_excerpt()`
	def __quantities(self, text: str, number: re.Match, unit_tokens: tuple[str, ...]) -> list[tuple[Decimal, int, int]]:
		cands: list[tuple] = []
		for token in unit_tokens:
			self.__collect_unit_cands(text, number, token, cands)
		valid: list[tuple[Decimal, int, int]] = []
		for sign, start, end in cands:
			if not (text[:start].rstrip().endswith('(') and text[end:].lstrip().startswith(')')):
				valid.append((Decimal(number[0]) * (-1 if '-' == sign else 1), start, end))
		return valid
	# @used-by :meth:`QuantityMatcher.__collect_unit_cands()`
	def __sign_before(self, text: str, start: int) -> tuple[str | None, int]:
		marks = re.search('([+-](?:\\s*[+-])*)\\s*$', text[:start])
		if marks:
			signs = ''.join(marks[1].split())
			r = (signs, marks.start()) if 1 == len(signs) else (None, start)
		else:
			prev = text[:start].rstrip()[-1:]
			r = (None, start) if prev and (unicodedata.category(prev) in {'Pd', 'Cf'} or 'MINUS' in unicodedata.name(prev, '')) else ('', start)
		return r
	# @used-by :func:`agent_tools.claims._quantity_matches()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.CalculationValidator.CalculationValidator.__load_operands()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def matches(self) -> bool:
		json_res = self.__check_json()
		return json_res if None is not json_res else self.__check_text()