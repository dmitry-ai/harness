# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add software design pattern specification validator and trigger checks":
# https://github.com/dmitry-ai/harness/issues/349
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
from Df.Harness.Arch.Evaluator import Evaluator
# @used-by :func:`Df.Harness.lib.blocked_report_ops._run_runner_audits()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_runner_architecture_check_records_state_and_fails_gate_on_missing_patterns()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_evaluator_checks_response_receipts_and_runner()`
# @used-by :mod:`agent_tools.arch.evaluator`
# @used-by :mod:`agent_tools.arch`
def check_runner_architecture(runner) -> None:
	Evaluator.check_runner(runner)
# @used-by :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__architecture_messages()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_answer_and_stop_gates_enforce_significant_response_receipt_and_open_findings()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_evaluator_checks_response_receipts_and_runner()`
# @used-by :mod:`agent_tools.arch.evaluator`
# @used-by :mod:`agent_tools.arch`
def evaluate_response_architecture(root: Path | None, turn: dict[str, Any] | None, response: str | None, *, blocked_report: bool=False) -> dict[str, Any]:
	return Evaluator().evaluate_response(root, turn, response, blocked_report=blocked_report)
__all__ = ['check_runner_architecture', 'evaluate_response_architecture']
