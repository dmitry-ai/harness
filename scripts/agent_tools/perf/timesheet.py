# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Perf.TimesheetBuilder import TimesheetBuilder
from .timesheet_common import format_timesheet_text
# 2026-11-24
# "Add harness perf-timesheet CLI for deterministic turn chronometry":
# https://github.com/dmitry-ai/harness/issues/191
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :meth:`test_perf_timesheet.PerfTimesheetTests.test_antigravity_parallel_tool_calls_match_bg_task_result()`
# @used-by :meth:`test_perf_timesheet.PerfTimesheetTests.test_antigravity_timesheet_computes_chronometry_switches_checkpoints_and_bg_waits()`
# @used-by :meth:`test_perf_timesheet.PerfTimesheetTests.test_codex_rollout_timesheet_and_step_slicing()`
# @used-by :mod:`agent_tools.perf.timesheet`
# @used-by :mod:`agent_tools.perf`
def build_timesheet(trace_path: str | Path, *, conversation_id: str | None=None, summary_db: str | Path | None=None, turn_start_step: int | None=None, turn_end_step: int | None=None, top_gaps_limit: int=10) -> dict[str, Any]:
	return TimesheetBuilder(trace_path, conversation_id=conversation_id, summary_db=summary_db, turn_start_step=turn_start_step, turn_end_step=turn_end_step, top_gaps_limit=top_gaps_limit).build()
# @used-by :func:`agent_tools.cli_registry._exec_perf_timesheet()`
# @used-by :mod:`agent_tools.perf.timesheet`
def run_perf_timesheet_cli(args) -> dict[str, Any]:
	return TimesheetBuilder.run_cli(args)
__all__ = ['build_timesheet', 'format_timesheet_text', 'run_perf_timesheet_cli']
