# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.TestRunner.ParallelRunner import ParallelRunner
from .worker_semaphore import worker_slot_budget
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by unused
def default_worker_count(module_count: int) -> int:
	return ParallelRunner.default_worker_count(module_count)
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_discover_orders_heaviest_modules_first()`
def discover_test_modules(tests_dir: Path | str, *, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None, timings: dict[str, float] | None=None) -> list[Path]:
	return ParallelRunner.discover_modules(tests_dir, pattern=pattern, modules=modules, timings=timings)
# 2026-11-23
# "Add parallel fail-fast test runner and worktree-aware TDD support":
# https://github.com/dmitry-ai/harness/issues/159
# @used-by :func:`agent_tools.worktree_flow._run_land_tests()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_parallel_runner_failfast_kills_slow_siblings()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_parallel_runner_module_timeout_terminates_stalled_worker()`
# @used-by :meth:`test_subprocess_hygiene_and_tree_kill.SubprocessHygieneAndTreeKillTests.test_parallel_runner_kills_grandchild_holding_stdout_on_timeout()`
# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_pytest_worksteal_runner_and_cli_runner_option()`
def run_parallel_tests(tests_dir: Path | str, *, workers: int | None=None, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None, failfast: bool=True, buffer_output: bool=True, module_timeout: float=300.0, timings_file: Path | None=None, runner: str='auto', env_extra: dict[str, str] | None=None) -> dict:
	return ParallelRunner(tests_dir, workers=workers, pattern=pattern, modules=modules, failfast=failfast, buffer_output=buffer_output, module_timeout=module_timeout, timings_file=timings_file, runner=runner, env_extra=env_extra, slot_budget_fn=worker_slot_budget).run()
