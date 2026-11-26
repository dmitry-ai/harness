# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class TddPreToolGate:
	NAME = 'EXEC-2-TDD-GATE'
	PRIORITY = 110
	TOOLS = frozenset({'run_command', 'write_file', 'edit_file'})
	# @used-by :func:`agent_tools.gates.tdd.check()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		from agent_tools.tdd.service_exempt import is_service_finalization_call
		if is_service_finalization_call(name, args, payload):
			r = None
		else:
			from agent_tools.tdd_gate import evaluate_pre_tool_use_tdd
			r = evaluate_pre_tool_use_tdd(name, args, payload or {})
		return r
