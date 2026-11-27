# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.Perf.AntigravityTimesheetAnalyzer import AntigravityTimesheetAnalyzer
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _add_cat(cats: dict[str, dict[str, Any]], cat: str, wall_s: float) -> None:
	AntigravityTimesheetAnalyzer.add_cat(cats, cat, wall_s)
# 2026-11-24
# "Add harness perf-timesheet CLI for deterministic turn chronometry":
# https://github.com/dmitry-ai/harness/issues/191
# @used-by unused
def analyze_antigravity_rows(rows: list[dict[str, Any]], *, last_user_ts: str | None=None, last_mod_ts: str | None=None, top_gaps_limit: int=10) -> dict[str, Any]:
	return AntigravityTimesheetAnalyzer(rows, last_user_ts=last_user_ts, last_mod_ts=last_mod_ts, top_gaps_limit=top_gaps_limit).analyze()
