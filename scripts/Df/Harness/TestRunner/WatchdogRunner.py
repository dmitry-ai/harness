# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.state import df_is_windows
from Df.Harness.TestRunner.ProcessTree import ProcessTree
import subprocess
import sys
import time
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class WatchdogRunner:
	DEFAULT_WATCHDOG_TIMEOUT = 300.0
	# @used-by :func:`agent_tools.watchdog_runner.run_test_watchdog()`
	# @used-by :meth:`WatchdogRunner.run_cli()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	def __init__(self, argv: list[str] | tuple[str, ...], *, timeout: float=DEFAULT_WATCHDOG_TIMEOUT, timeout_sec: float | None=None, cwd: Path | str | None=None, env: dict[str, str] | None=None) -> None:
		self.__argv = argv
		self.__timeout = timeout_sec if None is not timeout_sec else timeout
		self.__cwd = cwd
		self.__env = env
	# @used-by :func:`agent_tools.watchdog_runner.run_test_watchdog()`
	# @used-by :meth:`WatchdogRunner.run_cli()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	def run(self) -> dict:
		cmd = WatchdogRunner.__normalize_cmd(self.__argv)
		eff_timeout = max(0.1, float(self.__timeout))
		started = time.monotonic()
		proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, **WatchdogRunner.__build_popen_kwargs(self.__cwd, self.__env))
		timed_out, rc = WatchdogRunner.__poll_until_exit(proc, started + eff_timeout)
		elapsed = round(time.monotonic() - started, 3)
		if timed_out:
			sys.stderr.write(f'TIMEOUT: test command exceeded --timeout={eff_timeout:g}s ({elapsed:.3f}s); process tree terminated.\n')
			sys.stderr.flush()
		return {'ok': (not timed_out) and (0 == rc), 'timed_out': timed_out, 'exit_code': rc, 'returncode': rc, 'timeout': eff_timeout, 'elapsed': elapsed, 'command': cmd}
	# @used-by :meth:`WatchdogRunner.run()`
	@staticmethod
	def __build_popen_kwargs(cwd: Path | str | None, env: dict[str, str] | None) -> dict:
		kwargs: dict = {'cwd': str(Path(cwd).resolve()) if None is not cwd else None, 'env': env}
		if df_is_windows():
			kwargs['creationflags'] = ProcessTree.NO_WINDOW
		else:
			kwargs['start_new_session'] = True
		return kwargs
	# @used-by :meth:`WatchdogRunner.run()`
	@staticmethod
	def __normalize_cmd(argv: list[str] | tuple[str, ...]) -> list[str]:
		cmd = [str(tok) for tok in argv if None is not tok]
		if cmd and '--' == cmd[0]:
			cmd = cmd[1:]
		if not cmd:
			raise ValueError('test-watchdog requires a command to execute')
		return cmd
	# @used-by :meth:`WatchdogRunner.run()`
	@staticmethod
	def __poll_until_exit(proc: subprocess.Popen, deadline: float) -> tuple[bool, int]:
		timed_out = False
		while None is proc.poll():
			if time.monotonic() >= deadline:
				timed_out = True
				ProcessTree(proc).kill()
				break
			time.sleep(0.05)
		try:
			rc = proc.wait(timeout=5)
		except (OSError, subprocess.TimeoutExpired):
			rc = 124 if timed_out else -1
		return (timed_out, 124 if timed_out else int(rc))
	# @used-by :func:`agent_tools.watchdog_runner.run_watchdog_cli()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_process_tree_watchdog_semaphore_and_pytest_modes()`
	@staticmethod
	def run_cli(args) -> dict:
		res = WatchdogRunner(list(args.cmd or ()), timeout=args.timeout, cwd=args.cwd).run()
		return {k: v for k, v in res.items() if 'returncode' != k}
