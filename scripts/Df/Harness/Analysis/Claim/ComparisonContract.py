# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.Diagnostics import Diagnostics
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ComparisonContract:
	# @used-by :func:`agent_tools.claims._comparison_structure()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ComparisonValidator.ComparisonValidator.check()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_impact_and_ops()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
	def __init__(self, value, field: str, claim: dict, evidence) -> None:
		self.__value = value
		self.__field = field
		self.__claim = claim
		self.__evidence = evidence
	# @used-by :meth:`ComparisonContract.issues()`
	def __own_ev_ids(self) -> set[str]:
		ev = self.__evidence if isinstance(self.__evidence, list) else ()
		return {ref['id'] for ref in ev if isinstance(ref, dict) and isinstance(ref.get('id'), str) and ref['id'].strip()}
	# @used-by :func:`agent_tools.claims._comparison_structure()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ComparisonValidator.ComparisonValidator.check()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_impact_and_ops()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
	def issues(self) -> list[dict]:
		v = self.__value
		has_dep = isinstance(self.__claim.get('derived_from'), list) and bool(self.__claim['derived_from'])
		if not isinstance(v, dict) or not isinstance(v.get('relation'), str) or v['relation'] not in {'equal', 'differs', 'modified_from', 'identical_to'}:
			msg: str | None = 'A relational or modification claim requires comparison metadata with relation in {equal, differs, modified_from, identical_to}'
		elif not (isinstance(v.get('operand_a_evidence_id'), str) and v['operand_a_evidence_id'].strip()) or not (isinstance(v.get('operand_b_evidence_id'), str) and v['operand_b_evidence_id'].strip()):
			msg = 'Relational comparison requires two primary evidence IDs: operand_a_evidence_id and operand_b_evidence_id'
		elif v['operand_a_evidence_id'] == v['operand_b_evidence_id']:
			msg = 'Relational comparison requires two distinct primary evidence operands (operand_a_evidence_id != operand_b_evidence_id)'
		elif (not has_dep) and (v['operand_a_evidence_id'] not in self.__own_ev_ids() or v['operand_b_evidence_id'] not in self.__own_ev_ids()):
			msg = 'Relational comparison operands must reference primary evidence IDs present on the claim or its derived_from dependencies'
		else:
			msg = None
		return [Diagnostics().problem('claim.relational_arity', self.__field, msg, claim_id=self.__claim.get('id'))] if msg else []