# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP, localcontext
from Df.Harness.Analysis.Claim.CalculationContract import CalculationContract
from Df.Harness.Analysis.Claim.QuantityMatcher import QuantityMatcher
from Df.Harness.Analysis.Claim.SafeArithmetic import SafeArithmetic
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class CalculationValidator:
	# @used-by :func:`agent_tools.claims._check_calculation()`
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__verify_claim_evidence()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def __init__(self, claim: dict, index: dict, refs: dict) -> None:
		self.__claim = claim
		self.__index = index
		self.__refs = refs
	# @used-by :meth:`CalculationValidator.check()`
	def __compute_expected(self, value: dict, operands: dict[str, Decimal]) -> Decimal:
		op = value.get('operation')
		if 'percent_change' == op:
			if 0 == operands['old']:
				raise ValueError('Percentage change denominator old must be nonzero')
			with localcontext() as ctx:
				ctx.prec = 50
				r = ((operands['new'] - operands['old']) / operands['old'] * Decimal(100)).quantize(Decimal(1).scaleb(-value['rounding_places']), rounding=ROUND_HALF_UP)
		else:
			raw_eval, _ = SafeArithmetic(value.get('formula', ''), env=operands).evaluate()
			if None is raw_eval:
				raise ValueError(f"Arithmetic formula {value.get('formula')!r} could not be evaluated safely over operands {sorted(operands)}")
			with localcontext() as ctx:
				ctx.prec = 50
				r = raw_eval.quantize(Decimal(1).scaleb(-value['rounding_places']), rounding=ROUND_HALF_UP)
		return r
	# @used-by :meth:`CalculationValidator.check()`
	def __load_operands(self, value: dict) -> dict[str, Decimal]:
		deps = {d.get('claim_id') for d in (self.__claim.get('derived_from', []) if isinstance(self.__claim.get('derived_from'), list) else []) if isinstance(d, dict)}
		operands: dict[str, Decimal] = {}
		for name, operand in value['operands'].items():
			if operand['claim_id'] not in deps or operand['claim_id'] not in self.__index:
				raise ValueError('Calculation operands must name versioned source claims')
			entry = self.__refs.get(operand['evidence_id'])
			if not entry or entry[0].get('id') != operand['claim_id']:
				raise ValueError('Operand evidence must belong to its declared source claim')
			if not re.fullmatch('-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?', operand['value']):
				raise ValueError('Use exact finite base-10 decimal strings for operands')
			if not QuantityMatcher(entry[1], operand['value'], operand['unit'], entry[2]['quantity_context']).matches():
				raise ValueError('Operand value and unit must identify the same unambiguous primary quantity; use an adjacent value-unit quote or a JSON value/unit object')
			operands[name] = Decimal(operand['value'])
		return operands
	# @used-by :func:`agent_tools.claims._check_calculation()`
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__verify_claim_evidence()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def check(self) -> None:
		value = self.__claim['calculation']
		if CalculationContract(value, '/', self.__claim).issues():
			raise ValueError('Calculation does not satisfy its explicit contract')
		operands = self.__load_operands(value)
		expected = self.__compute_expected(value, operands)
		actual = Decimal(value['result'])
		if not actual.is_finite() or actual != expected:
			label = 'Percentage change' if 'percent_change' == value.get('operation') else 'Calculation result'
			raise ValueError(f"{label} is {expected}, not {value['result']}; formula includes the declared denominator and rounding")