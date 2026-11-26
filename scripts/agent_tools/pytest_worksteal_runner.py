# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add host test-worker semaphore and worksteal pytest mode":
# https://github.com/dmitry-ai/harness/issues/354
from __future__ import annotations
from pathlib import Path
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import time
from .process_tree import POPEN_TREE_KWARGS, kill_process_tree
_FAILED_RE = re.compile(r'\b(\d+)\s+(?:failed|errors?)\b')
_PASSED_RE = re.compile(r'\b(\d+)\s+passed\b')
_SKIPPED_RE = re.compile(r'\b(\d+)\s+skipped\b')
# @used-by :func:`run_pytest_worksteal()`
def _build_pytest_cmd(modules: list[Path], *, workers: int, failfast: bool) -> list[str]:
	cmd = [sys.executable, '-m', 'pytest', '-q', '--no-header', '-o', 'addopts=', '-p', 'no:cacheprovider']
	if 1 < int(workers) and 1 < len(modules):
		cmd.extend(['-n', str(int(workers)), '--dist', 'worksteal'])
	if failfast:
		cmd.append('-x')
	cmd.extend((str(m) for m in modules))
	return cmd
# @used-by :func:`_parse_pytest_counts()`
def _last_count(pattern: re.Pattern, text: str) -> int:
	matches = list(pattern.finditer(text or ''))
	return int(matches[-1].group(1)) if matches else 0
# @used-by :func:`run_pytest_worksteal()`
def _parse_pytest_counts(output: str) -> tuple[int, int, int]:
	return (_last_count(_PASSED_RE, output), _last_count(_FAILED_RE, output), _last_count(_SKIPPED_RE, output))
# @used-by :func:`agent_tools.parallel_runner.run_parallel_tests()`
# @used-by :func:`agent_tools.suite_runner.run_test_suite()`
def resolve_runner_mode(runner: str='auto') -> str:
	req = str(runner or 'auto').strip().lower()
	return 'pytest' if 'pytest' == req and xdist_available() else 'unittest'
# @used-by :func:`agent_tools.parallel_runner.run_parallel_tests()`
def run_pytest_for_parallel(tests_dir: Path, modules: list[Path], *, workers: int, failfast: bool=True, module_timeout: float=300.0, env_extra: dict[str, str] | None=None) -> dict:
	raw = run_pytest_worksteal(tests_dir, modules, workers=workers, failfast=failfast, timeout=module_timeout, env_extra=env_extra)
	ok = bool(raw['ok'])
	status_line = f"Ran {raw['total_tests']} tests in {raw['elapsed']:.3f}s\n" + ('OK' if ok else 'FAILED')
	return {'duration_seconds': raw['elapsed'], 'exit_code': 0 if ok else 1, 'failed_module': None if ok else 'pytest-xdist', 'failure_output': '' if ok else raw['output'][-4000:], 'ok': ok, 'passed_modules': len(modules) if ok else 0, 'runner': 'pytest', 'slowest_modules': [], 'summary': status_line, 'timed_out': raw['timed_out'], 'total_modules': len(modules), 'total_tests': raw['total_tests'], 'valid': ok, 'workers': workers}
# @used-by :func:`agent_tools.suite_runner.run_test_suite()`
def run_pytest_for_suite(base: Path, ordered: list[Path], *, workers: int, failfast: bool=True, module_timeout: float=300.0, env_extra: dict[str, str] | None=None) -> dict:
	raw = run_pytest_worksteal(base, ordered, workers=workers, failfast=failfast, timeout=module_timeout, env_extra=env_extra)
	ok = bool(raw['ok'])
	st = 'timeout' if raw['timed_out'] else ('passed' if ok else 'failed')
	res = [{'elapsed': raw['elapsed'], 'module': 'pytest-xdist', 'output': raw['output'], 'returncode': raw['returncode'], 'skipped': raw['skipped_tests'], 'status': st, 'tests': raw['total_tests']}]
	return {'cancelled_modules': 0, 'elapsed': raw['elapsed'], 'exit_code': 0 if ok else 1, 'failed_modules': 0 if ok or raw['timed_out'] else 1, 'failfast': bool(failfast), 'module_timeout': float(module_timeout), 'ok': ok, 'passed_modules': len(ordered) if ok else 0, 'results': res, 'runner': 'pytest', 'scheduled_order': [m.relative_to(base).as_posix() for m in ordered], 'skipped_tests': raw['skipped_tests'], 'tests_dir': base.as_posix(), 'timed_out_modules': 1 if raw['timed_out'] else 0, 'total_modules': len(ordered), 'total_tests': raw['total_tests'], 'workers': workers}
# @used-by :func:`run_pytest_for_parallel()`
# @used-by :func:`run_pytest_for_suite()`
def run_pytest_worksteal(tests_dir: Path, modules: list[Path], *, workers: int, failfast: bool=True, timeout: float=300.0, env_extra: dict[str, str] | None=None) -> dict:
	cmd = _build_pytest_cmd(modules, workers=workers, failfast=failfast)
	run_cwd = tests_dir.parent if 'tests' == tests_dir.name else tests_dir
	env = {'HARNESS_TEST_NO_FSYNC': '1', **os.environ, 'HARNESS_TEST_IN_WORKER': '1', 'PYTHONUTF8': '1', 'GIT_OPTIONAL_LOCKS': '0', **(env_extra or {})}
	started, timed_out = (time.monotonic(), False)
	with tempfile.TemporaryFile() as out_file:
		proc = subprocess.Popen(cmd, cwd=str(run_cwd), stdin=subprocess.DEVNULL, stdout=out_file, stderr=subprocess.STDOUT, env=env, **POPEN_TREE_KWARGS)
		try:
			rc = proc.wait(timeout=max(0.1, float(timeout)))
		except subprocess.TimeoutExpired:
			timed_out = True
			kill_process_tree(proc)
			rc = proc.returncode if None is not proc.returncode else -1
		out_file.seek(0)
		output = out_file.read().decode('utf-8', errors='replace')
	elapsed = round(time.monotonic() - started, 3)
	passed, failed, skipped = _parse_pytest_counts(output)
	total = passed + failed + skipped
	return {'elapsed': elapsed, 'failed_tests': failed, 'ok': (0 == rc) and (not timed_out) and (0 < total), 'output': output, 'passed_tests': passed, 'returncode': rc, 'runner': 'pytest', 'skipped_tests': skipped, 'timed_out': timed_out, 'total_tests': total}
# @used-by :func:`resolve_runner_mode()`
def xdist_available() -> bool:
	return None is not importlib.util.find_spec('pytest') and None is not importlib.util.find_spec('xdist')
