# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.trace_review import dfh_reviewer_isolation_issues
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class TraceAnalyzer:
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_platform_subsystem_classes()`
	def __init__(self, rows: list, *, root: str | Path | None=None) -> None:
		self.__rows = rows
		self.__root = Path(root).resolve() if None is not root else Path.cwd().resolve()
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_platform_subsystem_classes()`
	def run(self) -> list[str]:
		return dfh_reviewer_isolation_issues(self.__root, self.__rows)
