# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Perf.SuiteProfiler import SuiteProfiler
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _default_workers() -> int:
	return SuiteProfiler.default_workers()
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_format_perf_profile_tests()`
# @used-by :mod:`agent_tools.perf`
def format_profile_text(report: dict[str, Any]) -> str:
	return SuiteProfiler.format_text(report)
# 2026-11-24
# "Add harness perf-profile-tests CLI for test suite and subprocess profiling":
# https://github.com/dmitry-ai/harness/issues/192
# @used-by :meth:`test_perf_profile_tests.PerfProfileTestsSuiteTests.test_profile_test_suite_measures_files_tests_popen_sleep_and_cprofile()`
# @used-by :mod:`agent_tools.perf`
def profile_test_suite(tests_dir: Path | str | None=None, *, workers: int | None=None, module_timeout: float=300.0, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None, enable_cprofile: bool=False, top_n: int=15, cprofile_top: int=25) -> dict[str, Any]:
	return SuiteProfiler(tests_dir, workers=workers, module_timeout=module_timeout, pattern=pattern, modules=modules, enable_cprofile=enable_cprofile, top_n=top_n, cprofile_top=cprofile_top).profile()
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_perf_profile_tests()`
def run_perf_profile_cli(args) -> dict[str, Any]:
	return SuiteProfiler.run_cli(args)
