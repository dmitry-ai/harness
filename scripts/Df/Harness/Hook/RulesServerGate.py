# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class RulesServerGate:
	# @used-by :func:`check_rules_and_server_gate._evaluate_payload()`
	# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
	def __init__(self, payload: dict) -> None:
		self.__payload = payload
	# @used-by :meth:`RulesServerGate.run()`
	@staticmethod
	def __apply_failfast(name: str, args: dict, decision: dict) -> dict:
		r = decision
		if 'run_command' == name and 'allow' == decision.get('decision'):
			from agent_tools.failfast_gate import evaluate_pre_tool_use_test_failfast
			ff_err, ff_overwrite = evaluate_pre_tool_use_test_failfast(name, args)
			if ff_err:
				r = {'decision': 'deny', 'reason': f'REJECTED (EXEC-2-TEST-FAILFAST-GATE): {ff_err}'}
			elif ff_overwrite:
				r = {'decision': 'allow', 'overwrite': ff_overwrite, 'reason': 'EXEC-2-TEST-FAILFAST-GATE: Normalized test command fail-fast and WaitMsBeforeAsync.'}
		return r
	# @used-by :func:`check_rules_and_server_gate._evaluate_payload()`
	# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
	def run(self) -> dict:
		from agent_tools.gates import run_pre_tool_gates
		tool_call = self.__payload.get('toolCall', {})
		name, args = (tool_call.get('name', ''), tool_call.get('args', {}))
		return self.__apply_failfast(name, args, run_pre_tool_gates(name, args, self.__payload))