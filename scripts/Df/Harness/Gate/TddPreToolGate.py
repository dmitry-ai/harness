# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class TddPreToolGate:
	NAME = 'EXEC-2-TDD-GATE'
	PRIORITY = 110
	TOOLS = frozenset({'run_command', 'write_file', 'edit_file'})
	# @used-by :func:`agent_tools.gates.tdd.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_thin_pretool_shims_and_checkers()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		from Df.Harness.Tdd.ServiceExempt import ServiceExempt
		if ServiceExempt().is_exempt(name, args, payload):
			r = None
		else:
			from Df.Harness.Tdd.Enforcement import Enforcement
			r = Enforcement().evaluate_pre_tool_use(name, args, payload or {})
		return r
