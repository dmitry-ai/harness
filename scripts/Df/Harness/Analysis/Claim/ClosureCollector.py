# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ClosureCollector:
	# @used-by :func:`agent_tools.claims.collect_claim_closure()`
	# @used-by :meth:`Df.Harness.Review.ClaimEvidenceCollector.ClaimEvidenceCollector.pairs()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	def __init__(self, seed_ids, index: dict, *, include_addresses: bool=False, unknown_prefix: str | None=None) -> None:
		self.__seed_ids = seed_ids
		self.__index = index
		self.__include_addresses = include_addresses
		self.__unknown_prefix = unknown_prefix
		self.__out: list[str] = []
		self.__seen: set[str] = set()
	# @used-by :meth:`ClosureCollector.__visit()`
	def __child_ids(self, item: dict) -> list:
		deps = item.get('derived_from', [])
		ids = [d.get('claim_id') for d in (deps if isinstance(deps, list) else ()) if isinstance(d, dict)]
		if self.__include_addresses:
			addrs = item.get('addresses', [])
			ids.extend(addrs if isinstance(addrs, list) else ())
		return ids
	# @used-by :meth:`ClosureCollector.__visit()`
	# @used-by :meth:`ClosureCollector.collect()`
	def __should_visit(self, val) -> bool:
		return None is not self.__unknown_prefix or (isinstance(val, str) and bool(val.strip()))
	# @used-by :meth:`ClosureCollector.collect()`
	def __visit(self, ident) -> None:
		if None is not self.__unknown_prefix and ident not in self.__index:
			raise ValueError(self.__unknown_prefix + str(ident))
		if isinstance(ident, str) and bool(ident.strip()) and ident not in self.__seen and ident in self.__index:
			self.__seen.add(ident)
			self.__out.append(ident)
			for cid in self.__child_ids(self.__index[ident]):
				if self.__should_visit(cid):
					self.__visit(cid)
	# @used-by :func:`agent_tools.claims.collect_claim_closure()`
	# @used-by :meth:`Df.Harness.Review.ClaimEvidenceCollector.ClaimEvidenceCollector.pairs()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	def collect(self) -> list[str]:
		for seed in self.__seed_ids:
			if self.__should_visit(seed):
				self.__visit(seed)
		return list(self.__out)