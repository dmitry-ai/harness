# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Grounding.CliCommandAuditor import CliCommandAuditor
from Df.Harness.lib.trace import dfh_cmd_from_call, dfh_row_outputs
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _cmd_from_tool_call(call: dict[str, Any]) -> str:
	return dfh_cmd_from_call(call)
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _collect_row_outputs(rows: list[dict[str, Any]], pos: int) -> list[str]:
	return dfh_row_outputs(rows, pos)
# @used-by :meth:`test_turn_begin_status_and_auditors.TurnBeginStatusAndAuditorsTests.test_all_trace_auditors_ignore_nested_foreign_reconciliation_and_flag_top_level_failure()`
def _is_passing_output(text: str) -> bool:
	return CliCommandAuditor.is_passing_output(text)
# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
# @used-by :mod:`agent_tools.cli_command_grounding`
def response_turn_gate_issues(root: Path, response: str, *, requests: list | tuple=(), turn: dict[str, Any] | None=None, native: dict[str, Any] | None=None, turn_state: dict[str, Any] | None=None, skip_df_analysis: bool=False) -> list[str]:
	return CliCommandAuditor.response_turn_gate_issues(root, response, requests=requests, turn=turn, native=native, turn_state=turn_state, skip_df_analysis=skip_df_analysis)
# @used-by :mod:`agent_tools.cli_command_grounding`
def unverified_cli_command_issues(response: str, *, turn: dict[str, Any] | None=None, native: dict[str, Any] | None=None) -> list[str]:
	return CliCommandAuditor(response, turn=turn, native=native).audit()
__all__ = ['response_turn_gate_issues', 'unverified_cli_command_issues']