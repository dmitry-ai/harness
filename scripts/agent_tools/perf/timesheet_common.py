# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Perf.TimesheetCommon import TimesheetCommon
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by unused
def classify_command(cmd: str) -> str:
	return TimesheetCommon.classify_command(cmd)
# @used-by unused
def compute_top_gaps(events: list[tuple[int, float | None, str, str | None, str]], *, limit: int=10) -> list[dict[str, Any]]:
	return TimesheetCommon.compute_top_gaps(events, limit=limit)
# @used-by :func:`agent_tools.cli_registry._format_perf_timesheet()`
# @used-by :mod:`agent_tools.perf.timesheet`
# @used-by :mod:`agent_tools.perf`
def format_timesheet_text(report: dict[str, Any]) -> str:
	return TimesheetCommon.format_text(report)
# @used-by unused
def load_jsonl_rows(path: Path) -> tuple[str, list[dict[str, Any]]]:
	return TimesheetCommon(path).load_jsonl_rows()
# @used-by unused
def parse_iso_ts(raw: str | None) -> float | None:
	return TimesheetCommon.parse_iso_ts(raw)
# @used-by unused
def parse_test_output(text: str) -> tuple[int | None, float | None]:
	return TimesheetCommon.parse_test_output(text)
# @used-by unused
def read_summary_timestamps(db_path: Path | None, conversation_id: str | None) -> tuple[str | None, str | None]:
	return TimesheetCommon.read_summary_timestamps(db_path, conversation_id)
# @used-by unused
def resolve_journal_step_meta(project_root: Path, step_num: int) -> dict[str, Any]:
	return TimesheetCommon.resolve_journal_step_meta(project_root, step_num)
# 2026-11-24
# "Add harness perf-timesheet CLI for deterministic turn chronometry":
# https://github.com/dmitry-ai/harness/issues/191
# @used-by :meth:`test_observability_diagnostics.ObservabilityDiagnosticsTests.test_resolve_trace_source_populates_summary_db_from_journal_step()`
def resolve_trace_source(*, trace: Path | None=None, conversation: str | None=None, project: Path | None=None, journal_step: int | None=None, instance: str | None=None, platform: str | None=None, summary_db: Path | None=None, turn_start_step: int | None=None) -> dict[str, Any]:
	return TimesheetCommon.resolve_trace_source(trace=trace, conversation=conversation, project=project, journal_step=journal_step, instance=instance, platform=platform, summary_db=summary_db, turn_start_step=turn_start_step)
# @used-by unused
def round_opt(val: float | None, digits: int=3) -> float | None:
	return TimesheetCommon.round_opt(val, digits)
