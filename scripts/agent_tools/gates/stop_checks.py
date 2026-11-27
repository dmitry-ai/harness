# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.StopChecksGate import StopChecksGate
STOP_GATES = StopChecksGate.STOP_GATES
# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__evaluate_matched_state()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_answer_and_stop_gates_enforce_significant_response_receipt_and_open_findings()`
# @used-by :meth:`test_gate_registry.GateRegistryTests.test_stop_gates_evaluate_in_priority_order()`
# @used-by :mod:`agent_tools.gates.stop_checks`
# @used-by :mod:`agent_tools.gates`
def run_stop_gates(state: dict) -> dict | None:
	return StopChecksGate().run(state)
__all__ = ['STOP_GATES', 'run_stop_gates']
