# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Analysis.Claim.ComparisonContract import ComparisonContract
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ComparisonValidator:
	# @used-by :func:`agent_tools.claims._check_comparison()`
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__verify_claim_evidence()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def __init__(self, claim: dict, index: dict, refs: dict) -> None:
		self.__claim = claim
		self.__index = index
		self.__refs = refs
	# @used-by :meth:`ComparisonValidator.check()`
	def __resolve_pair(self, comp: dict) -> tuple[dict, dict]:
		deps = self.__claim.get('derived_from', []) if isinstance(self.__claim.get('derived_from'), list) else []
		allowed = {self.__claim.get('id')} | {d['claim_id'] for d in deps if isinstance(d, dict) and isinstance(d.get('claim_id'), str) and d['claim_id'].strip()}
		entry_a, entry_b = (self.__refs.get(comp['operand_a_evidence_id']), self.__refs.get(comp['operand_b_evidence_id']))
		if not entry_a or not entry_b:
			raise ValueError('Both operand_a_evidence_id and operand_b_evidence_id must resolve to verified primary evidence')
		if entry_a[0].get('id') not in allowed or entry_b[0].get('id') not in allowed:
			raise ValueError('Comparison operand evidence must belong to the claim or its versioned derived_from dependencies')
		return (entry_a[1], entry_b[1])
	# @used-by :func:`agent_tools.claims._check_comparison()`
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__verify_claim_evidence()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def check(self) -> None:
		comp = self.__claim.get('comparison')
		if ComparisonContract(comp, '/', self.__claim, self.__claim.get('evidence')).issues():
			raise ValueError('Relational comparison does not satisfy its two-operand arity contract')
		ref_a, ref_b = self.__resolve_pair(comp)
		loc_a = (ref_a.get('source'), (ref_a.get('locator') or {}).get('type'), (ref_a.get('locator') or {}).get('value'))
		loc_b = (ref_b.get('source'), (ref_b.get('locator') or {}).get('type'), (ref_b.get('locator') or {}).get('value'))
		if loc_a == loc_b:
			raise ValueError('Relational comparison requires two distinct source/locator operands, not the same source fragment twice')
		hash_equal = ref_a.get('source_sha256') == ref_b.get('source_sha256')
		quote_equal = ' '.join(str(ref_a.get('quote', '')).split()) == ' '.join(str(ref_b.get('quote', '')).split())
		if comp['relation'] in {'differs', 'modified_from'} and hash_equal and quote_equal:
			raise ValueError('Claimed modification/difference between operand_a and operand_b is refuted: primary source hashes and quotes are identical')
		if comp['relation'] in {'equal', 'identical_to'} and (not hash_equal) and (not quote_equal):
			raise ValueError('Claimed identity between operand_a and operand_b is refuted: primary source hashes and quotes differ')