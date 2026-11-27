# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Grounding.ScopeDeferralEvaluator import ScopeDeferralEvaluator
# @used-by :func:`Df.Harness.lib.blocked_report_ops.dfh_evaluate_runner_code_hygiene()`
# @used-by :meth:`test_clarification_stop_consent.ClarificationStopConsentTests.test_runner_scope_deferral_and_raw_output_fallback()`
def check_runner_scope_deferral(runner, lifecycle_chk: dict[str, Any]) -> None:
	ScopeDeferralEvaluator.check_runner(runner, lifecycle_chk)
# @used-by :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__scope_deferral_messages()`
# @used-by :meth:`test_journal_clarifications_and_disclosure.JournalClarificationsAndDisclosureTests.test_deferral_disclosure_gate_rejects_silent_response_and_accepts_disclosed_rationale()`
def evaluate_scope_deferral(turn: dict[str, Any] | None, turn_state: dict[str, Any] | None, lifecycle_chk: dict[str, Any] | None, response: str | None=None, *, blocked_report: bool=False) -> dict[str, Any]:
	return ScopeDeferralEvaluator(turn, turn_state, lifecycle_chk, response, blocked_report=blocked_report).evaluate()
# @used-by unused
def find_explicit_stop_consent(turn: dict[str, Any] | None, turn_state: dict[str, Any] | None=None) -> dict[str, Any] | None:
	return ScopeDeferralEvaluator.find_explicit_stop_consent(turn, turn_state)