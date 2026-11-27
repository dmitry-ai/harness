# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from Df.Harness.TestRunner.ProcessTree import ProcessTree
from Df.Harness.TestRunner.PytestWorkstealRunner import PytestWorkstealRunner
from Df.Harness.TestRunner.WorkerSemaphore import WorkerSemaphore
from Df.Harness.lib.cli import dfh_default_workers
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class SuiteRunner:
	__RAN_RE = re.compile(r'(?m)^Ran\s+(\d+)\s+tests?\s+in\s+')
	__SKIP_DIRS = frozenset({'.git', '__pycache__', 'node_modules', 'venv', '.venv', '\ua616', '\ua66e', '\U0001f56e'})
	__SKIPPED_RE = re.compile(r'\bskipped=(\d+)\b')
	# @used-by :func:`agent_tools.suite_runner.run_test_suite()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_failfast_timeout_and_format_text()`
	def __init__(self, tests_dir: Path | str | None=None, *, workers: int | None=None, module_timeout: float=300.0, failfast: bool=True, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None, runner: str='auto', slot_budget_fn=None) -> None:
		self.__tests_dir = tests_dir
		self.__workers = workers
		self.__module_timeout = module_timeout
		self.__failfast = failfast
		self.__pattern = pattern
		self.__modules = modules
		self.__runner = runner
		self.__slot_budget_fn = slot_budget_fn
	# @used-by :func:`agent_tools.suite_runner.run_test_suite()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_failfast_timeout_and_format_text()`
	def run(self) -> dict:
		base, ordered = SuiteRunner.discover_modules(self.__tests_dir, pattern=self.__pattern, modules=self.__modules)
		if not ordered:
			raise ValueError(f'No test modules matched pattern {self.__pattern!r} in {base}')
		req_workers = min(max(1, int(self.__workers)) if None is not self.__workers else SuiteRunner.default_workers(), len(ordered))
		started = time.monotonic()
		budget_fn = self.__slot_budget_fn if None is not self.__slot_budget_fn else WorkerSemaphore.slot_budget
		with budget_fn(req_workers) as lease:
			eff_workers = min(max(1, int(lease['granted'])), len(ordered))
			if 'pytest' == PytestWorkstealRunner.resolve_runner_mode(self.__runner):
				r = PytestWorkstealRunner.run_for_suite(base, ordered, workers=eff_workers, failfast=self.__failfast, module_timeout=self.__module_timeout)
			else:
				results = SuiteRunner.__run_unittest_suite(base, ordered, eff_workers=eff_workers, failfast=self.__failfast, module_timeout=self.__module_timeout)
				r = SuiteRunner.__summarize_suite(base, ordered, results, eff_workers=eff_workers, failfast=self.__failfast, module_timeout=self.__module_timeout, elapsed=round(time.monotonic() - started, 3))
		return r
	# @used-by :meth:`SuiteRunner.__run_module_worker()`
	@staticmethod
	def __execute_module_proc(mod_path: Path, top_dir: Path, rel: str, *, failfast: bool, module_timeout: float, stop_event: threading.Event, active_lock: threading.Lock, active_procs: set[subprocess.Popen]) -> dict:
		cmd = [sys.executable, '-m', 'unittest', 'discover', '-s', str(mod_path.parent), '-t', str(top_dir), '-p', mod_path.name, '-b'] + (['-f'] if failfast else [])
		started = time.monotonic()
		with tempfile.TemporaryFile() as out_file:
			proc = subprocess.Popen(cmd, cwd=str(top_dir.parent), stdin=subprocess.DEVNULL, stdout=out_file, stderr=subprocess.STDOUT, env={'HARNESS_TEST_NO_FSYNC': '1', **os.environ, 'HARNESS_TEST_IN_WORKER': '1'}, **ProcessTree.POPEN_TREE_KWARGS)
			with active_lock:
				active_procs.add(proc)
			try:
				timed_out, cancelled, rc = SuiteRunner.__poll_module_proc(proc, started, module_timeout, stop_event)
			finally:
				with active_lock:
					active_procs.discard(proc)
			out_file.seek(0)
			output = out_file.read().decode('utf-8', errors='replace')
		tests, skipped = SuiteRunner.__parse_unittest_counts(output)
		status = 'timeout' if timed_out else 'cancelled' if cancelled else 'passed' if 0 == rc else 'failed'
		return {'module': rel, 'status': status, 'returncode': rc, 'elapsed': round(time.monotonic() - started, 3), 'tests': tests, 'skipped': skipped, 'output': output}
	# @used-by :meth:`SuiteRunner.format_text()`
	@staticmethod
	def __format_item_lines(item: dict, module_timeout: float) -> list[str]:
		lines: list[str] = []
		st = item.get('status')
		if 'timeout' == st:
			lines.append(f"TIMEOUT: {item['module']} exceeded --module-timeout={module_timeout}s ({item['elapsed']:.3f}s)")
		elif 'failed' == st:
			lines.append(f"FAIL: {item['module']} (exit {item['returncode']}, {item['elapsed']:.3f}s)")
		if lines and item.get('output'):
			lines.append(item['output'].rstrip())
		return lines
	# @used-by :meth:`SuiteRunner.format_text()`
	@staticmethod
	def __format_status_line(report: dict) -> str:
		if report['ok']:
			skip_part = f" (skipped={report['skipped_tests']})" if report['skipped_tests'] else ''
			r = f'OK{skip_part}'
		else:
			parts = [f"failures={report['failed_modules']}"] if report['failed_modules'] else []
			if report['timed_out_modules']:
				parts.append(f"timeouts={report['timed_out_modules']}")
			r = f"FAILED ({', '.join(parts) or 'error'})"
		return r
	# @used-by :meth:`SuiteRunner.discover_modules()`
	@staticmethod
	def __module_matches_filters(mod: Path, base_dir: Path, filters: list[str]) -> bool:
		rel, name, stem = (mod.relative_to(base_dir).as_posix().lower(), mod.name.lower(), mod.stem.lower())
		return any((f in (rel, name, stem) or rel.endswith('/' + f) for f in filters))
	# @used-by :meth:`SuiteRunner.__execute_module_proc()`
	@staticmethod
	def __parse_unittest_counts(text: str) -> tuple[int, int]:
		ran = sum((int(m.group(1)) for m in SuiteRunner.__RAN_RE.finditer(text or '')))
		skipped = sum((int(m.group(1)) for m in SuiteRunner.__SKIPPED_RE.finditer(text or '')))
		return (ran, skipped)
	# @used-by :meth:`SuiteRunner.__execute_module_proc()`
	@staticmethod
	def __poll_module_proc(proc: subprocess.Popen, started: float, module_timeout: float, stop_event: threading.Event) -> tuple[bool, bool, int]:
		timed_out, cancelled = (False, False)
		while None is proc.poll():
			if stop_event.is_set():
				cancelled = True
				ProcessTree(proc).kill()
				break
			if (time.monotonic() - started) >= module_timeout:
				timed_out = True
				ProcessTree(proc).kill()
				break
			time.sleep(0.05)
		return (timed_out, cancelled, proc.wait(timeout=5))
	# @used-by :meth:`SuiteRunner.discover_modules()`
	@staticmethod
	def __resolve_tests_dir(raw_dir: Path | str | None) -> Path:
		base = Path(raw_dir).resolve() if None is not raw_dir else (Path(__file__).resolve().parents[4] / 'tests').resolve()
		if not base.is_dir():
			raise FileNotFoundError(f'Test directory not found: {base}')
		sub_tests = base / 'tests'
		if sub_tests.is_dir() and (not any(base.glob('test_*.py'))):
			base = sub_tests.resolve()
		return base
	# @used-by :meth:`SuiteRunner.__run_unittest_suite()`
	@staticmethod
	def __run_module_worker(mod_path: Path, top_dir: Path, *, failfast: bool, module_timeout: float, stop_event: threading.Event, active_lock: threading.Lock, active_procs: set[subprocess.Popen]) -> dict:
		rel = mod_path.relative_to(top_dir).as_posix()
		if stop_event.is_set():
			r = {'module': rel, 'status': 'cancelled', 'returncode': None, 'elapsed': 0.0, 'tests': 0, 'skipped': 0, 'output': ''}
		else:
			r = SuiteRunner.__execute_module_proc(mod_path, top_dir, rel, failfast=failfast, module_timeout=module_timeout, stop_event=stop_event, active_lock=active_lock, active_procs=active_procs)
		return r
	# @used-by :meth:`SuiteRunner.run()`
	@staticmethod
	def __run_unittest_suite(base: Path, ordered: list[Path], *, eff_workers: int, failfast: bool, module_timeout: float) -> list[dict]:
		stop_event, active_lock, active_procs, results, aborted = (threading.Event(), threading.Lock(), set(), [], False)
		executor = ThreadPoolExecutor(max_workers=eff_workers)
		try:
			pending = {executor.submit(SuiteRunner.__run_module_worker, mod, base, failfast=failfast, module_timeout=float(module_timeout), stop_event=stop_event, active_lock=active_lock, active_procs=active_procs): mod for mod in ordered}
			while pending and (not aborted):
				done, pending = wait(pending, return_when=FIRST_COMPLETED)
				for fut in done:
					res = fut.result()
					results.append(res)
					if failfast and res['status'] in ('failed', 'timeout'):
						aborted = True
						break
		finally:
			if aborted:
				stop_event.set()
				SuiteRunner.__terminate_active(active_lock, active_procs)
			executor.shutdown(wait=True, cancel_futures=aborted)
		return results
	# @used-by :meth:`SuiteRunner.run()`
	@staticmethod
	def __summarize_suite(base: Path, ordered: list[Path], results: list[dict], *, eff_workers: int, failfast: bool, module_timeout: float, elapsed: float) -> dict:
		passed = sum((1 for x in results if 'passed' == x['status']))
		failed = sum((1 for x in results if 'failed' == x['status']))
		timed_out = sum((1 for x in results if 'timeout' == x['status']))
		total_tests = sum((int(x['tests']) for x in results))
		skipped_tests = sum((int(x['skipped']) for x in results))
		ok = (0 == failed) and (0 == timed_out) and (passed == len(ordered)) and (0 < total_tests)
		return {'cancelled_modules': len(ordered) - passed - failed - timed_out, 'elapsed': elapsed, 'exit_code': 0 if ok else 1, 'failed_modules': failed, 'failfast': bool(failfast), 'module_timeout': float(module_timeout), 'ok': ok, 'passed_modules': passed, 'results': results, 'runner': 'unittest', 'scheduled_order': [m.relative_to(base).as_posix() for m in ordered], 'skipped_tests': skipped_tests, 'tests_dir': base.as_posix(), 'timed_out_modules': timed_out, 'total_modules': len(ordered), 'total_tests': total_tests, 'workers': eff_workers}
	# @used-by :meth:`SuiteRunner.__run_unittest_suite()`
	@staticmethod
	def __terminate_active(active_lock: threading.Lock, active_procs: set[subprocess.Popen]) -> None:
		with active_lock:
			procs = list(active_procs)
		for proc in procs:
			ProcessTree(proc).kill()
	# @used-by :func:`agent_tools.suite_runner._default_workers()`
	# @used-by :meth:`SuiteRunner.run()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_process_tree_watchdog_semaphore_and_pytest_modes()`
	@staticmethod
	def default_workers() -> int:
		return dfh_default_workers(8)
	# @used-by :func:`agent_tools.suite_runner.discover_test_modules()`
	# @used-by :meth:`Df.Harness.Perf.SuiteProfiler.SuiteProfiler.profile()`
	# @used-by :meth:`SuiteRunner.run()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_process_tree_watchdog_semaphore_and_pytest_modes()`
	@staticmethod
	def discover_modules(tests_dir: Path | str | None=None, *, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None) -> tuple[Path, list[Path]]:
		base = SuiteRunner.__resolve_tests_dir(tests_dir)
		found = [cand.resolve() for cand in base.rglob(pattern) if cand.is_file() and (not any((part in SuiteRunner.__SKIP_DIRS for part in cand.relative_to(base).parts[:-1])))]
		norm_filters = [str(m).strip().replace('\\', '/').lower() for m in (modules or ()) if str(m).strip()]
		if norm_filters:
			found = [m for m in found if SuiteRunner.__module_matches_filters(m, base, norm_filters)]
		return (base, sorted(found, key=lambda p: (-p.stat().st_size, p.relative_to(base).as_posix())))
	# @used-by :func:`agent_tools.suite_runner.format_text_report()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_failfast_timeout_and_format_text()`
	@staticmethod
	def format_text(report: dict) -> str:
		lines = [line for item in (report.get('results') or ()) for line in SuiteRunner.__format_item_lines(item, report['module_timeout'])]
		lines.extend(['-' * 70, f"Ran {report['total_tests']} tests in {report['elapsed']:.3f}s ({report['passed_modules']}/{report['total_modules']} modules, workers={report['workers']})", '', SuiteRunner.__format_status_line(report)])
		return '\n'.join(lines) + '\n'
