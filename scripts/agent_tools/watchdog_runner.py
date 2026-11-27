# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.TestRunner.WatchdogRunner import WatchdogRunner
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
DEFAULT_WATCHDOG_TIMEOUT = WatchdogRunner.DEFAULT_WATCHDOG_TIMEOUT
# 2026-11-24
# "Enforce watchdog timeout and stdin isolation for unittest and pytest in failfast_gate":
# https://github.com/dmitry-ai/harness/issues/205
# @used-by unused
def run_test_watchdog(argv: list[str] | tuple[str, ...], *, timeout: float=DEFAULT_WATCHDOG_TIMEOUT, cwd: Path | str | None=None, env: dict[str, str] | None=None) -> dict:
	res = WatchdogRunner(argv, timeout=timeout, cwd=cwd, env=env).run()
	return {k: v for k, v in res.items() if 'returncode' != k}
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_test_watchdog()`
def run_watchdog_cli(args) -> dict:
	return WatchdogRunner.run_cli(args)
