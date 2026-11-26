# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.Diagnostics import Diagnostics
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class CalculationContract:
	# @used-by :func:`agent_tools.claims._calculation_structure()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.CalculationValidator.CalculationValidator.check()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_impact_and_ops()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def __init__(self, value, field: str, claim: dict) -> None:
		self.__value = value
		self.__field = field
		self.__claim = claim
	# @used-by :meth:`CalculationContract.__check_meta()`
	def __check_operands(self, op: str) -> str | None:
		msg: str | None = None
		for operand in self.__value['operands'].values():
			if not isinstance(operand, dict) or not all((isinstance(operand.get(k), str) and operand[k].strip() for k in ('value', 'unit', 'claim_id', 'evidence_id'))):
				msg = 'Each operand needs decimal string value, explicit unit, claim_id and evidence_id'
				break
			if operand['unit'] != operand['unit'].strip():
				msg = 'Operand units must be canonical strings without surrounding whitespace'
				break
		if None is msg and 'percent_change' == op and self.__value['operands']['old']['unit'] != self.__value['operands']['new']['unit']:
			msg = 'Percent change requires matching operand units; perform and source any conversion as a separate claim first'
		if not (isinstance(self.__value.get('result'), str) and self.__value['result'].strip()):
			msg = 'Calculation result must be an explicit decimal string'
		return msg
	# @used-by :meth:`CalculationContract.issues()`
	def __check_meta(self, v: dict, op: str) -> str | None:
		bad_unit = ('percent_change' == op and 'percent' != v.get('result_unit')) or (op in {'formula', 'derived_calc'} and (not (isinstance(v.get('result_unit'), str) and v['result_unit'].strip())))
		if int is not type(v.get('rounding_places')) or not 0 <= v['rounding_places'] <= 12 or 'ROUND_HALF_UP' != v.get('rounding'):
			r: str | None = 'Choose explicit ROUND_HALF_UP and 0..12 decimal places'
		elif not isinstance(v.get('operands'), dict) or not v['operands'] or ('percent_change' == op and set(v['operands']) != {'old', 'new'}):
			r = 'Supply old/new operands with exact decimal value, unit, claim_id and evidence_id'
		elif bad_unit:
			r = 'Percentage change requires explicit result_unit percent'
		else:
			r = self.__check_operands(op)
		return r
	# @used-by :func:`agent_tools.claims._calculation_structure()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.CalculationValidator.CalculationValidator.check()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_impact_and_ops()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def issues(self) -> list[dict]:
		v = self.__value
		op = v.get('operation') if isinstance(v, dict) else None
		if not isinstance(v, dict) or op not in {'percent_change', 'formula', 'derived_calc'}:
			msg: str | None = 'Supported calculation operations are percent_change, formula, or derived_calc'
		elif 'percent_change' == op and '(new - old) / old * 100' != v.get('formula'):
			msg = 'Supported calculation is percent_change with formula (new - old) / old * 100'
		elif op in {'formula', 'derived_calc'} and (not (isinstance(v.get('formula'), str) and v['formula'].strip())):
			msg = 'Formula calculation requires a nonempty arithmetic formula'
		else:
			msg = self.__check_meta(v, op)
		return [Diagnostics().problem('calculation.contract', self.__field, msg, claim_id=self.__claim.get('id'))] if msg else []