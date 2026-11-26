# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Analysis.Claim.InlineCalcVerifier import InlineCalcVerifier
from Df.Harness.Analysis.Claim.SourceNumericTokenizer import SourceNumericTokenizer
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class NumericGrounding:
	# @used-by :func:`agent_tools.claims.grounded_numbers_for_claim()`
	# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.__resolve_claim()`
	# @used-by :meth:`NumericGrounding.__compute()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	def __init__(self, claim, index=None, visited=None, memo=None) -> None:
		self.__claim = claim
		self.__index = index
		self.__visited = set() if None is visited else visited
		self.__memo = {} if None is memo else memo
	# @used-by :meth:`NumericGrounding.__corpus()`
	def __append_evidence(self, texts: list[str]) -> None:
		ev = self.__claim.get('evidence', [])
		for ref in ev if isinstance(ev, list) else ():
			if isinstance(ref, dict):
				texts.append(str(ref.get('quote', '')))
				loc = ref.get('locator')
				if isinstance(loc, dict):
					texts.append(str(loc.get('value', '')))
	# @used-by :meth:`NumericGrounding.__corpus()`
	def __append_sides(self, texts: list[str]) -> None:
		for side in ('for', 'against'):
			args = self.__claim.get(side, [])
			for arg in args if isinstance(args, list) else ():
				if isinstance(arg, dict):
					texts.extend((str(arg.get('argument', '')), str(arg.get('quote', ''))))
	# @used-by :meth:`NumericGrounding.grounded_numbers()`
	def __compute(self, ident, has_id: bool) -> set[str]:
		next_visited = self.__visited | ({ident} if isinstance(ident, str) else set())
		corpus = self.__corpus()
		numbers = SourceNumericTokenizer(corpus).tokenize()
		if isinstance(self.__index, dict):
			for cid in self.__linked_ids():
				if cid in self.__index:
					numbers.update(NumericGrounding(self.__index[cid], self.__index, next_visited, self.__memo).grounded_numbers())
		derived_nums, _ = InlineCalcVerifier(corpus, numbers).extract()
		numbers.update(derived_nums)
		if has_id and (not self.__visited):
			self.__memo[ident] = set(numbers)
		return numbers
	# @used-by :meth:`NumericGrounding.__compute()`
	def __corpus(self) -> str:
		texts = [self.__claim[k] for k in ('essence', 'assessment_basis', 'discriminating_check', 'validation', 'criterion') if isinstance(self.__claim.get(k), str)]
		texts.extend((str(self.__claim[k]) for k in ('probability_percent', 'score_percent') if isinstance(self.__claim.get(k), int)))
		if isinstance(self.__claim.get('scope'), dict):
			sc = self.__claim['scope']
			texts.append(str(sc.get('description', '')))
			texts.extend((str(x) for x in sc.get('sample') or []))
			texts.extend((str(x) for x in sc.get('limitations') or []))
		if isinstance(self.__claim.get('calculation'), dict):
			texts.append(json.dumps(self.__claim['calculation'], ensure_ascii=False))
		self.__append_evidence(texts)
		self.__append_sides(texts)
		return '\n'.join(texts)
	# @used-by :meth:`NumericGrounding.__compute()`
	def __linked_ids(self) -> list[str]:
		deps = self.__claim.get('derived_from', [])
		ids = [d['claim_id'] for d in (deps if isinstance(deps, list) else ()) if isinstance(d, dict) and d.get('claim_id')]
		addrs = self.__claim.get('addresses', [])
		ids.extend((a for a in (addrs if isinstance(addrs, list) else ()) if isinstance(a, str)))
		return ids
	# @used-by :func:`agent_tools.claims.grounded_numbers_for_claim()`
	# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.__resolve_claim()`
	# @used-by :meth:`NumericGrounding.__compute()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	def grounded_numbers(self) -> set[str]:
		ident = self.__claim.get('id') if isinstance(self.__claim, dict) else None
		has_id = isinstance(ident, str) and bool(ident.strip())
		if not isinstance(self.__claim, dict) or ident in self.__visited:
			r: set[str] = set()
		elif has_id and ident in self.__memo:
			r = set(self.__memo[ident])
		else:
			r = self.__compute(ident, has_id)
		return r