# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add host test-worker semaphore and worksteal pytest mode":
# https://github.com/dmitry-ai/harness/issues/354
from __future__ import annotations
from pathlib import Path
from Df.Harness.TestRunner.PytestWorkstealRunner import PytestWorkstealRunner
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by unused
def resolve_runner_mode(runner: str='auto') -> str:
	return PytestWorkstealRunner.resolve_runner_mode(runner)
# @used-by unused
def run_pytest_for_parallel(tests_dir: Path, modules: list[Path], *, workers: int, failfast: bool=True, module_timeout: float=300.0, env_extra: dict[str, str] | None=None) -> dict:
	return PytestWorkstealRunner.run_for_parallel(tests_dir, modules, workers=workers, failfast=failfast, module_timeout=module_timeout, env_extra=env_extra)
# @used-by unused
def run_pytest_for_suite(base: Path, ordered: list[Path], *, workers: int, failfast: bool=True, module_timeout: float=300.0, env_extra: dict[str, str] | None=None) -> dict:
	return PytestWorkstealRunner.run_for_suite(base, ordered, workers=workers, failfast=failfast, module_timeout=module_timeout, env_extra=env_extra)
# @used-by unused
def run_pytest_worksteal(tests_dir: Path, modules: list[Path], *, workers: int, failfast: bool=True, timeout: float=300.0, env_extra: dict[str, str] | None=None) -> dict:
	return PytestWorkstealRunner(tests_dir, modules, workers=workers, failfast=failfast, timeout=timeout, env_extra=env_extra).run()
# @used-by unused
def xdist_available() -> bool:
	return PytestWorkstealRunner.xdist_available()
