# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.TestRunner.SuiteRunner import SuiteRunner
from .worker_semaphore import worker_slot_budget
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _default_workers() -> int:
	return SuiteRunner.default_workers()
# @used-by unused
def discover_test_modules(tests_dir: Path | str | None=None, *, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None) -> tuple[Path, list[Path]]:
	return SuiteRunner.discover_modules(tests_dir, pattern=pattern, modules=modules)
# @used-by :func:`agent_tools.cli_registry._format_run_tests()`
def format_text_report(report: dict) -> str:
	return SuiteRunner.format_text(report)
# 2026-11-23
# "Add parallel fail-fast run-tests runner with module timeouts and TDD gate registration":
# https://github.com/dmitry-ai/harness/issues/160
# @used-by :func:`agent_tools.cli_registry._exec_run_tests()`
# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_nested_worker_slot_budget_skips_self_throttling_against_parent_lease()`
# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_pytest_worksteal_runner_and_cli_runner_option()`
def run_test_suite(tests_dir: Path | str | None=None, *, workers: int | None=None, module_timeout: float=300.0, failfast: bool=True, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None, runner: str='auto') -> dict:
	return SuiteRunner(tests_dir, workers=workers, module_timeout=module_timeout, failfast=failfast, pattern=pattern, modules=modules, runner=runner, slot_budget_fn=worker_slot_budget).run()
