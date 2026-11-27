# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# Accumulate command count and rounded wall-clock duration for a timesheet category.
# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.add_cat()`
# @used-by :meth:`Df.Harness.Perf.CodexTimesheetAnalyzer.CodexTimesheetAnalyzer.add_cat()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_trace_and_timesheet_helpers()`
def dfh_timesheet_add_cat(cats: dict[str, dict[str, Any]], cat: str, wall_s: float) -> None:
	slot = cats.setdefault(cat, {'count': 0, 'wall_s': 0.0})
	slot['count'] += 1
	slot['wall_s'] = round(slot['wall_s'] + max(0.0, wall_s), 3)