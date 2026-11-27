# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from Df.Harness.TestRunner.ProcessTree import ProcessTree
from Df.Harness.TestRunner.PytestWorkstealRunner import PytestWorkstealRunner
from Df.Harness.TestRunner.WorkerSemaphore import WorkerSemaphore
from agent_tools.storage import replace_bytes
import json
import os
import re
import subprocess
import sys
import threading
import time
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class ParallelRunner:
	__RAN_RE = re.compile(r'(?m)^Ran\s+(\d+)\s+tests?\s+in\s+')
	# @used-by :func:`agent_tools.parallel_runner.run_parallel_tests()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_failfast_timeout_and_format_text()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_perf_ag_timesheet_and_parallel_runner_timeout()`
	def __init__(self, tests_dir: Path | str, *, workers: int | None=None, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None, failfast: bool=True, buffer_output: bool=True, module_timeout: float=300.0, timings_file: Path | None=None, runner: str='auto', env_extra: dict[str, str] | None=None, slot_budget_fn=None) -> None:
		self.__tests_dir = tests_dir
		self.__workers = workers
		self.__pattern = pattern
		self.__modules = modules
		self.__failfast = failfast
		self.__buffer_output = buffer_output
		self.__module_timeout = module_timeout
		self.__timings_file = timings_file
		self.__runner = runner
		self.__env_extra = env_extra
		self.__slot_budget_fn = slot_budget_fn
	# @used-by :func:`agent_tools.parallel_runner.run_parallel_tests()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_failfast_timeout_and_format_text()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_perf_ag_timesheet_and_parallel_runner_timeout()`
	def run(self) -> dict:
		root = Path(self.__tests_dir).resolve()
		mod_list = ParallelRunner.discover_modules(root, pattern=self.__pattern, modules=self.__modules, timings=ParallelRunner.__load_timings(self.__timings_file))
		if not mod_list:
			raise ValueError(f'No test modules matched {self.__pattern!r} in {root}')
		req_workers = max(1, int(self.__workers)) if None is not self.__workers else ParallelRunner.default_worker_count(len(mod_list))
		started = time.monotonic()
		budget_fn = self.__slot_budget_fn if None is not self.__slot_budget_fn else WorkerSemaphore.slot_budget
		with budget_fn(req_workers) as lease:
			eff_workers = min(max(1, int(lease['granted'])), len(mod_list))
			if 'pytest' == PytestWorkstealRunner.resolve_runner_mode(self.__runner):
				summary = PytestWorkstealRunner.run_for_parallel(root, mod_list, workers=eff_workers, failfast=self.__failfast, module_timeout=self.__module_timeout, env_extra=self.__env_extra)
			else:
				results = ParallelRunner.__run_unittest_modules(root, mod_list, eff_workers=eff_workers, failfast=self.__failfast, buffer_output=self.__buffer_output, module_timeout=self.__module_timeout, env_extra=self.__env_extra)
				summary = ParallelRunner.__summarize_results(results, total_modules=len(mod_list), workers=eff_workers, elapsed=time.monotonic() - started)
				if summary['ok']:
					ParallelRunner.__save_timings(self.__timings_file, results)
		return summary
	# @used-by :meth:`ParallelRunner.__spawn_and_wait_module()`
	@staticmethod
	def __build_worker_cmd(module: Path, *, failfast: bool, buffer_output: bool) -> list[str]:
		cmd = [sys.executable, '-m', 'unittest']
		if failfast:
			cmd.append('-f')
		if buffer_output:
			cmd.append('-b')
		cmd.append(module.stem)
		return cmd
	# @used-by :meth:`ParallelRunner.__read_proc_output()`
	@staticmethod
	def __close_proc_pipes(proc: subprocess.Popen) -> None:
		for stream in (proc.stdout, proc.stderr):
			if None is not stream:
				try:
					stream.close()
				except OSError:
					pass
	# @used-by :meth:`ParallelRunner.__save_timings()`
	# @used-by :meth:`ParallelRunner.run()`
	@staticmethod
	def __load_timings(cache_path: Path | None) -> dict[str, float]:
		r: dict[str, float] = {}
		if None is not cache_path and cache_path.is_file():
			try:
				raw = json.loads(cache_path.read_text(encoding='utf-8'))
				if isinstance(raw, dict):
					r = {str(k): float(v) for k, v in raw.items() if isinstance(v, (int, float))}
			except (OSError, ValueError):
				r = {}
		return r
	# @used-by :meth:`ParallelRunner.__spawn_and_wait_module()`
	@staticmethod
	def __parse_ran_count(output: str) -> int:
		m = ParallelRunner.__RAN_RE.search(output or '')
		return int(m.group(1)) if m else 0
	# @used-by :meth:`ParallelRunner.__spawn_and_wait_module()`
	@staticmethod
	def __poll_proc(proc: subprocess.Popen, deadline: float, stop_event: threading.Event) -> tuple[bool, bool]:
		timed_out, aborted = (False, False)
		while None is proc.poll():
			if stop_event.is_set():
				aborted = True
				ProcessTree(proc).kill()
				break
			if time.monotonic() >= deadline:
				timed_out = True
				ProcessTree(proc).kill()
				break
			time.sleep(0.05)
		return (timed_out, aborted)
	# @used-by :meth:`ParallelRunner.__spawn_and_wait_module()`
	@staticmethod
	def __read_proc_output(proc: subprocess.Popen) -> str:
		try:
			out, err = proc.communicate(timeout=2.0)
		except (OSError, subprocess.TimeoutExpired):
			ProcessTree(proc).kill()
			ParallelRunner.__close_proc_pipes(proc)
			out, err = ('', '')
		return '\n'.join((p for p in (out, err) if p))
	# @used-by :meth:`ParallelRunner.__run_unittest_modules()`
	@staticmethod
	def __run_single_module(module: Path, tests_dir: Path, *, failfast: bool, buffer_output: bool, timeout: float, stop_event: threading.Event, active_procs: set, active_lock: threading.Lock, env_extra: dict[str, str] | None=None) -> dict:
		if stop_event.is_set():
			r = {'module': module.stem, 'ok': False, 'returncode': -1, 'timed_out': False, 'aborted': True, 'tests': 0, 'duration': 0.0, 'output': ''}
		else:
			r = ParallelRunner.__spawn_and_wait_module(module, tests_dir, failfast=failfast, buffer_output=buffer_output, timeout=timeout, stop_event=stop_event, active_procs=active_procs, active_lock=active_lock, env_extra=env_extra)
		return r
	# @used-by :meth:`ParallelRunner.run()`
	@staticmethod
	def __run_unittest_modules(root: Path, mod_list: list[Path], *, eff_workers: int, failfast: bool, buffer_output: bool, module_timeout: float, env_extra: dict[str, str] | None) -> list[dict]:
		stop_event, active_procs, active_lock, results = (threading.Event(), set(), threading.Lock(), [])
		pool = ThreadPoolExecutor(max_workers=eff_workers)
		try:
			futs = {pool.submit(ParallelRunner.__run_single_module, mod, root, failfast=failfast, buffer_output=buffer_output, timeout=module_timeout, stop_event=stop_event, active_procs=active_procs, active_lock=active_lock, env_extra=env_extra): mod for mod in mod_list}
			for fut in as_completed(futs):
				res = fut.result()
				results.append(res)
				if failfast and (not res['ok']) and (not res['aborted']):
					ParallelRunner.__stop_siblings(stop_event, active_procs, active_lock)
					break
		finally:
			pool.shutdown(wait=True, cancel_futures=True)
		return results
	# @used-by :meth:`ParallelRunner.run()`
	@staticmethod
	def __save_timings(cache_path: Path | None, results: list[dict]) -> None:
		if None is not cache_path:
			existing = ParallelRunner.__load_timings(cache_path)
			for item in results:
				if item.get('ok'):
					existing[item['module']] = float(item['duration'])
			try:
				replace_bytes(cache_path, (json.dumps(existing, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8'))
			except OSError:
				pass
	# @used-by :meth:`ParallelRunner.__run_single_module()`
	@staticmethod
	def __spawn_and_wait_module(module: Path, tests_dir: Path, *, failfast: bool, buffer_output: bool, timeout: float, stop_event: threading.Event, active_procs: set, active_lock: threading.Lock, env_extra: dict[str, str] | None) -> dict:
		started = time.monotonic()
		cmd = ParallelRunner.__build_worker_cmd(module, failfast=failfast, buffer_output=buffer_output)
		env = {'HARNESS_TEST_NO_FSYNC': '1', **os.environ, 'HARNESS_TEST_IN_WORKER': '1', 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'GIT_OPTIONAL_LOCKS': '0', **(env_extra or {})}
		proc = subprocess.Popen(cmd, cwd=str(tests_dir), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', env=env, **ProcessTree.POPEN_TREE_KWARGS)
		with active_lock:
			active_procs.add(proc)
		try:
			timed_out, aborted = ParallelRunner.__poll_proc(proc, started + max(0.1, float(timeout)), stop_event)
			output = ParallelRunner.__read_proc_output(proc)
			rc = proc.returncode if None is not proc.returncode else -1
		finally:
			with active_lock:
				active_procs.discard(proc)
		return {'module': module.stem, 'ok': (0 == rc) and (not timed_out) and (not aborted), 'returncode': rc, 'timed_out': timed_out, 'aborted': aborted, 'tests': ParallelRunner.__parse_ran_count(output), 'duration': round(time.monotonic() - started, 3), 'output': output}
	# @used-by :meth:`ParallelRunner.__run_unittest_modules()`
	@staticmethod
	def __stop_siblings(stop_event: threading.Event, active_procs: set, active_lock: threading.Lock) -> None:
		stop_event.set()
		with active_lock:
			procs = list(active_procs)
		for proc in procs:
			ProcessTree(proc).kill()
	# @used-by :meth:`ParallelRunner.run()`
	@staticmethod
	def __summarize_results(results: list[dict], *, total_modules: int, workers: int, elapsed: float) -> dict:
		passed = sum((1 for item in results if item['ok']))
		total_tests = sum((int(item['tests']) for item in results))
		first_fail = next((item for item in results if (not item['ok']) and (not item['aborted'])), None)
		ok = (None is first_fail) and (passed == total_modules)
		slowest = sorted(({'module': it['module'], 'duration': it['duration'], 'tests': it['tests']} for it in results if not it['aborted']), key=lambda x: -x['duration'])[:10]
		status_line = f'Ran {total_tests} tests in {elapsed:.3f}s\n' + ('OK' if ok else 'FAILED')
		return {'ok': ok, 'valid': ok, 'exit_code': 0 if ok else 1, 'runner': 'unittest', 'workers': workers, 'total_modules': total_modules, 'passed_modules': passed, 'total_tests': total_tests, 'duration_seconds': round(elapsed, 3), 'failed_module': first_fail['module'] if first_fail else None, 'timed_out': bool(first_fail and first_fail['timed_out']), 'failure_output': (first_fail['output'][-4000:] if first_fail else ''), 'slowest_modules': slowest, 'summary': status_line}
	# @used-by :func:`agent_tools.parallel_runner.default_worker_count()`
	# @used-by :meth:`ParallelRunner.run()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_process_tree_watchdog_semaphore_and_pytest_modes()`
	@staticmethod
	def default_worker_count(module_count: int) -> int:
		return max(1, min(max(1, int(module_count)), min(8, os.cpu_count() or 4)))
	# @used-by :func:`agent_tools.parallel_runner.discover_test_modules()`
	# @used-by :meth:`ParallelRunner.run()`
	@staticmethod
	def discover_modules(tests_dir: Path | str, *, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None, timings: dict[str, float] | None=None) -> list[Path]:
		root = Path(tests_dir).resolve()
		if not root.is_dir():
			raise FileNotFoundError(f'Tests directory not found: {root}')
		found = [p for p in sorted(root.glob(pattern)) if p.is_file()]
		if modules:
			wanted = {Path(m).stem.lower() for m in modules if str(m).strip()}
			found = [p for p in found if p.stem.lower() in wanted]
		t_map = timings or {}
		# @used-by :meth:`ParallelRunner.discover_modules()`
		def _sort_key(path: Path) -> tuple[float, int, str]:
			try:
				size = path.stat().st_size
			except OSError:
				size = 0
			return (-float(t_map.get(path.stem, -1.0)), -size, path.stem)
		return sorted(found, key=_sort_key)
