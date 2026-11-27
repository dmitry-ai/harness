# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.state import df_is_windows
import os
import signal
import subprocess
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class ProcessTree:
	NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
	POPEN_TREE_KWARGS: dict = {'creationflags': NO_WINDOW} if df_is_windows() else {'start_new_session': True}
	# @used-by :func:`agent_tools.process_tree.kill_process_tree()`
	# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.__poll_proc()`
	# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.__read_proc_output()`
	# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.__stop_siblings()`
	# @used-by :meth:`Df.Harness.TestRunner.PytestWorkstealRunner.PytestWorkstealRunner.run()`
	# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.__poll_module_proc()`
	# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.__terminate_active()`
	# @used-by :meth:`Df.Harness.TestRunner.WatchdogRunner.WatchdogRunner.__poll_until_exit()`
	def __init__(self, proc: subprocess.Popen, *, wait_timeout: float=5.0) -> None:
		self.__proc = proc
		self.__wait_timeout = wait_timeout
	# @used-by :func:`agent_tools.addon_observability._is_pid_alive()`
	# @used-by :func:`agent_tools.landing_lease._pid_is_alive()`
	# @used-by :func:`agent_tools.platforms.antigravity._is_live_language_server_pid()`
	# @used-by :func:`agent_tools.process_tree.kill_process_tree()`
	# @used-by :func:`test_hook_runner_watchdog._is_pid_alive()`
	# @used-by :func:`test_hook_trace_cache_and_watchdog._is_pid_alive()`
	# @used-by :func:`test_parallel_test_runner._is_pid_alive()`
	# @used-by :func:`test_stdin_detachment._kill_tree()`
	# @used-by :func:`test_subprocess_hygiene_and_tree_kill._is_pid_alive()`
	# @used-by :func:`test_subprocess_hygiene_and_tree_kill._kill_pid()`
	# @used-by :func:`test_watchdog_and_timeout_gate._is_pid_alive()`
	# @used-by :func:`test_watchdog_and_timeout_gate._kill_pid()`
	# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.__poll_proc()`
	# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.__read_proc_output()`
	# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.__stop_siblings()`
	# @used-by :meth:`Df.Harness.TestRunner.PytestWorkstealRunner.PytestWorkstealRunner.run()`
	# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.__poll_module_proc()`
	# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.__terminate_active()`
	# @used-by :meth:`Df.Harness.TestRunner.WatchdogRunner.WatchdogRunner.__poll_until_exit()`
	# @used-by :meth:`ProcessTree.__finish_kill()`
	# @used-by :meth:`agent_tools.text_browser.CDPSession.close()`
	# @used-by :meth:`agent_tools.text_browser.ManagedHeadlessShell.close()`
	def kill(self) -> None:
		if None is self.__proc.poll():
			if df_is_windows():
				subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.__proc.pid)], stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=15, creationflags=ProcessTree.NO_WINDOW)
			else:
				ProcessTree.__kill_posix_group(self.__proc.pid)
			ProcessTree.__finish_kill(self.__proc, self.__wait_timeout)
	# @used-by :meth:`ProcessTree.kill()`
	@staticmethod
	def __finish_kill(proc: subprocess.Popen, wait_timeout: float) -> None:
		try:
			proc.kill()
		except OSError:
			pass
		try:
			proc.wait(timeout=wait_timeout)
		except (OSError, subprocess.TimeoutExpired):
			pass
	# @used-by :meth:`ProcessTree.kill()`
	@staticmethod
	def __kill_posix_group(pid: int) -> None:
		try:
			os.killpg(os.getpgid(pid), signal.SIGKILL)
		except OSError:
			pass
