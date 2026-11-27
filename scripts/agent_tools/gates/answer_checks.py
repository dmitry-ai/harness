# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.AnswerChecksGate import AnswerChecksGate
ANSWER_GATES = AnswerChecksGate.ANSWER_GATES
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_check_answer()`
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_answer_gates_enforce_architecture_pattern_specs()`
# @used-by :meth:`test_clarification_stop_consent.ClarificationStopConsentTests.test_explicit_user_stop_consent_in_clarifications_unblocks_deferral()`
# @used-by :meth:`test_clarification_stop_consent.ClarificationStopConsentTests.test_step_100_102_real_clarifications_rejected_with_open_deferred_children()`
# @used-by :meth:`test_gate_registry.GateRegistryTests.test_answer_gates_collect_issues_and_checks_map()`
# @used-by :meth:`test_incomplete_scope_regression_matrix.IncompleteScopeRegressionMatrixTests.test_step_281_scope_deferral_matrix_blocks_open_children_allows_unrelated_bugs_and_consent()`
# @used-by :meth:`test_journal_clarifications_and_disclosure.JournalClarificationsAndDisclosureTests.test_deferral_disclosure_gate_rejects_silent_response_and_accepts_disclosed_rationale()`
# @used-by :meth:`test_open_child_deferral_gate.OpenChildDeferralGateTests.test_open_deferred_child_blocks_lifecycle_and_answer_gates()`
# @used-by :mod:`agent_tools.gates.answer_checks`
# @used-by :mod:`agent_tools.gates`
def run_answer_gates(ctx: dict) -> tuple[list[dict], dict[str, bool]]:
	return AnswerChecksGate().run(ctx)
__all__ = ['ANSWER_GATES', 'run_answer_gates']
