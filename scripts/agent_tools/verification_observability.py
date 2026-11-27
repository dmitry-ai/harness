# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Hook.VerificationObserver import VerificationObserver
from Df.Harness.lib.hook_verif_ops import dfh_check_runner_verification_observability as check_runner_verification_observability, dfh_classify_shadow_output as _classify_shadow_output, dfh_closed_issues_after as _closed_issues_after, dfh_detect_shadow_replay_runs as detect_shadow_replay_runs, dfh_is_shadow_replay_cmd as _is_shadow_replay_cmd, dfh_latest_unresolved_failure as _latest_unresolved_failure, dfh_response_discloses_shadow_failure as _response_discloses_shadow_failure
from Df.Harness.lib.trace import dfh_cmd_from_call, dfh_row_outputs
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
# @used-by :mod:`agent_tools.verification_observability`
def _cmd_from_call(call: dict[str, Any]) -> str:
	return dfh_cmd_from_call(call)
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
# @used-by :mod:`agent_tools.verification_observability`
def _row_outputs(rows: list[dict[str, Any]], pos: int) -> list[str]:
	return dfh_row_outputs(rows, pos)
# @used-by :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__verification_obs_messages()`
# @used-by :meth:`test_observability_diagnostics.ObservabilityDiagnosticsTests.test_detect_shadow_replay_ignores_cli_arguments_and_matches_real_invocations()`
# @used-by :mod:`agent_tools.verification_observability`
def evaluate_verification_observability(root: Path, native: dict[str, Any] | None, turn: dict[str, Any] | None, value: dict[str, Any] | None, response: str | None) -> dict[str, Any]:
	return VerificationObserver(root, native, turn, value, response).run()
__all__ = ['_classify_shadow_output', '_closed_issues_after', '_cmd_from_call', '_is_shadow_replay_cmd', '_latest_unresolved_failure', '_response_discloses_shadow_failure', '_row_outputs', 'check_runner_verification_observability', 'detect_shadow_replay_runs', 'evaluate_verification_observability']