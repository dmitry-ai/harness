# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any, override
import subprocess
import time
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class TrackedPopen(subprocess.Popen):
	__ACTIVE_STATS: dict[str, Any] | None = None
	__ORIG_SLEEP = time.sleep
	# @used-by unused
	# @see :meth:`subprocess.Popen.__init__()`
	@override
	def __init__(self, args, *a, **kw) -> None:
		self.__perf_cat = TrackedPopen.classify_proc_args(args)
		self.__perf_t0 = time.perf_counter()
		self.__perf_done = False
		super().__init__(args, *a, **kw)
	# @used-by :meth:`TrackedPopen.communicate()`
	# @used-by :meth:`TrackedPopen.wait()`
	def __perf_finish(self) -> None:
		stats = TrackedPopen.__ACTIVE_STATS
		if (not self.__perf_done) and None is not stats:
			self.__perf_done = True
			dt = max(0.0, time.perf_counter() - self.__perf_t0)
			stats['popen_count'] += 1
			stats['popen_s'] += dt
			stats[f'{self.__perf_cat}_count'] += 1
			stats[f'{self.__perf_cat}_s'] += dt
	# @used-by :meth:`TrackedPopen.install()`
	@staticmethod
	def __tracked_sleep(secs: float) -> None:
		t0 = time.perf_counter()
		try:
			TrackedPopen.__ORIG_SLEEP(secs)
		finally:
			stats = TrackedPopen.__ACTIVE_STATS
			if None is not stats:
				stats['sleep_count'] += 1
				stats['sleep_s'] += max(0.0, time.perf_counter() - t0)
	# @used-by :meth:`TrackedPopen.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_perf_classes_profile_and_build_timesheets()`
	@staticmethod
	def classify_proc_args(args: Any) -> str:
		first = args[0] if isinstance(args, (list, tuple)) and args else (str(args or '').split()[0] if str(args or '').strip() else '')
		low = Path(str(first).strip('"\'')).name.lower()
		if low in ('git', 'git.exe', 'git.cmd'):
			r = 'git'
		elif low.startswith(('python', 'py.exe', 'pytest')):
			r = 'python'
		else:
			r = 'other_proc'
		return r
	# @used-by :meth:`Df.Harness.Perf.SuiteWorker.SuiteWorker.run()`
	@staticmethod
	def install(stats: dict[str, Any]) -> tuple[Any, Any]:
		orig_popen, orig_sleep = (subprocess.Popen, time.sleep)
		TrackedPopen.__ACTIVE_STATS = stats
		TrackedPopen.__ORIG_SLEEP = orig_sleep
		subprocess.Popen = TrackedPopen
		time.sleep = TrackedPopen.__tracked_sleep
		return (orig_popen, orig_sleep)
	# @used-by :meth:`Df.Harness.Perf.SuiteWorker.SuiteWorker.run()`
	@staticmethod
	def restore(orig_popen: Any, orig_sleep: Any) -> None:
		subprocess.Popen, time.sleep = (orig_popen, orig_sleep)
		TrackedPopen.__ACTIVE_STATS = None
	# @used-by :func:`test_stdin_detachment._run_with_open_stdin()`
	# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.__read_proc_output()`
	# @used-by :meth:`subprocess.Popen.communicate()`
	# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_single_process_watchdog_and_hung_timeout_lkg_fallback()`
	# @used-by :meth:`test_watchdog_and_timeout_gate.WatchdogAndTimeoutGateTests.test_watchdog_cli_detaches_open_stdin_pipe_and_preserves_exit_code()`
	# @see :meth:`subprocess.Popen.communicate()`
	@override
	def communicate(self, *a, **kw):
		try:
			r = super().communicate(*a, **kw)
		finally:
			self.__perf_finish()
		return r
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_land_acquire()`
	# @used-by :func:`test_stdin_detachment._kill_tree()`
	# @used-by :meth:`Df.Harness.TestRunner.ProcessTree.ProcessTree.__finish_kill()`
	# @used-by :meth:`Df.Harness.TestRunner.PytestWorkstealRunner.PytestWorkstealRunner.run()`
	# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.__poll_module_proc()`
	# @used-by :meth:`Df.Harness.TestRunner.WatchdogRunner.WatchdogRunner.__poll_until_exit()`
	# @used-by :meth:`agent_tools.text_browser.CDPSession.close()`
	# @used-by :meth:`agent_tools.text_browser.ManagedHeadlessShell.close()`
	# @used-by :meth:`subprocess.Popen.wait()`
	# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_locked_concurrent_fresh_files_succeed_without_permission_error()`
	# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_locked_create_on_held_zero_byte_lock_waits_without_permission_error()`
	# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_path_cache_rlock_handles_concurrent_eviction_and_clear()`
	# @used-by :meth:`test_registration_portability.RegistrationTests.test_slow_previous_success_does_not_erase_a_newer_failed_attempt()`
	# @see :meth:`subprocess.Popen.wait()`
	@override
	def wait(self, *a, **kw):
		try:
			r = super().wait(*a, **kw)
		finally:
			self.__perf_finish()
		return r
