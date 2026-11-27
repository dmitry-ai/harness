# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.blocked_report_ops import dfh_blocked_report_issues
from Df.Harness.lib.path_resolve import dfh_project_paths
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class BlockedReportAuditor:
	# @used-by :func:`agent_tools.blocked_report.blocked_report_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_completion_subsystem_classes()`
	def __init__(self, pp_or_root: Any, response: str, *, workflow_exists: bool | None=None, is_finalized: bool=False) -> None:
		self.__pp = pp_or_root if hasattr(pp_or_root, 'continuation_md') else dfh_project_paths(Path(pp_or_root), exact_root=True)
		self.__response = response
		self.__workflow_exists = self.__pp.workflow_json.is_file() if None is workflow_exists else bool(workflow_exists)
		self.__is_finalized = bool(is_finalized)
	# @used-by :func:`agent_tools.blocked_report.blocked_report_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_completion_subsystem_classes()`
	def run(self) -> list[str]:
		return dfh_blocked_report_issues(self.__pp, self.__response, workflow_exists=self.__workflow_exists, is_finalized=self.__is_finalized)