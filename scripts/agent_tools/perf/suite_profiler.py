# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from ..suite_runner import discover_test_modules
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_SUM_KEYS = ('dur_s', 'popen_count', 'popen_s', 'git_count', 'git_s', 'python_count', 'python_s', 'other_proc_count', 'other_proc_s', 'sleep_count', 'sleep_s')
# @used-by :func:`_assemble_report()`
def _aggregate_cprofile(file_rows: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
	merged: dict[tuple[str, int, str], dict[str, Any]] = {}
	for fitem in file_rows:
		for row in fitem.get('cprofile') or ():
			key = (row['file'], int(row['line']), row['func'])
			slot = merged.setdefault(key, {'file': row['file'], 'line': int(row['line']), 'func': row['func'], 'ncalls': 0, 'tottime': 0.0, 'cumtime': 0.0})
			slot['ncalls'] += int(row['ncalls'])
			slot['tottime'] = round(slot['tottime'] + float(row['tottime']), 5)
			slot['cumtime'] = round(slot['cumtime'] + float(row['cumtime']), 5)
	ordered = sorted(merged.values(), key=lambda x: (-x['cumtime'], -x['tottime']))
	return ordered[:max(1, int(top_n))]
# @used-by :func:`_assemble_report()`
# @used-by :func:`_file_summary()`
def _aggregate_totals(tests: list[dict[str, Any]]) -> dict[str, Any]:
	totals = {k: 0 if k.endswith('_count') else 0.0 for k in _SUM_KEYS}
	for item in tests:
		for k in _SUM_KEYS:
			val = item.get(k, 0)
			totals[k] = (totals[k] + int(val)) if k.endswith('_count') else round(totals[k] + float(val), 4)
	return totals
# @used-by :func:`profile_test_suite()`
def _assemble_report(base: Path, file_rows: list[dict[str, Any]], eff_workers: int, wall_s: float, top_n: int, cp_limit: int) -> dict[str, Any]:
	file_rows.sort(key=lambda item: (-item['run_s'], item['file']))
	all_tests = sorted((t for item in file_rows for t in (item.get('tests') or ())), key=lambda item: (-item['dur_s'], item['test_id']))
	sum_run = round(sum((float(x['run_s']) for x in file_rows)), 4)
	sum_load = round(sum((float(x['load_s']) for x in file_rows)), 4)
	n_fail = sum((int(x['failures']) for x in file_rows))
	n_err = sum((int(x['errors']) for x in file_rows))
	n_skip = sum((int(x['skipped']) for x in file_rows))
	n_tests = sum((int(x['tests_run']) for x in file_rows))
	top_files = [_file_summary(item, sum_run) for item in file_rows[:max(1, int(top_n))]]
	cp_top = _aggregate_cprofile(file_rows, cp_limit) if 0 < cp_limit else []
	clean_files = [{k: v for k, v in item.items() if 'cprofile' != k} for item in file_rows]
	return {'schema_version': 1, 'valid': 0 == n_fail and 0 == n_err, 'tests_dir': base.as_posix(), 'workers': eff_workers, 'cpu_count': os.cpu_count(), 'python_version': platform.python_version(), 'platform': platform.platform(), 'parallel_wall_s': wall_s, 'sum_file_run_s': sum_run, 'sum_file_load_s': sum_load, 'total_files': len(file_rows), 'total_tests': n_tests, 'total_failures': n_fail, 'total_errors': n_err, 'total_skipped': n_skip, 'totals': _aggregate_totals(all_tests), 'top_files': top_files, 'top_tests': all_tests[:max(1, int(top_n))], 'cprofile_top': cp_top, 'files': clean_files}
# @used-by :func:`profile_test_suite()`
def _default_workers() -> int:
	return min(max(2, (os.cpu_count() or 4) // 2), 6)
# @used-by :func:`_assemble_report()`
def _file_summary(item: dict[str, Any], total_run_s: float) -> dict[str, Any]:
	sums = _aggregate_totals(item.get('tests') or [])
	share = round(100.0 * item['run_s'] / total_run_s, 2) if 0.0 < total_run_s else 0.0
	return {'file': item['file'], 'run_s': item['run_s'], 'load_s': item['load_s'], 'share_pct': share, 'tests_run': item['tests_run'], 'failures': item['failures'], 'errors': item['errors'], 'skipped': item['skipped'], 'popen_count': sums['popen_count'], 'popen_s': sums['popen_s'], 'git_count': sums['git_count'], 'python_count': sums['python_count'], 'sleep_s': sums['sleep_s']}
# @used-by :func:`profile_test_suite()`
def _run_worker(mod_path: Path, top_dir: Path, *, timeout_s: float, cprofile_top: int, tmp_dir: Path, idx: int) -> dict[str, Any]:
	out_json = tmp_dir / f'worker-{idx}.json'
	scripts_dir = Path(__file__).resolve().parents[2]
	env = {'HARNESS_TEST_NO_FSYNC': '1', **os.environ}
	py_path = env.get('PYTHONPATH', '')
	env['PYTHONPATH'] = f'{scripts_dir}{os.pathsep}{py_path}' if py_path else str(scripts_dir)
	cmd = [sys.executable, '-m', 'agent_tools.perf.suite_worker', str(mod_path), str(top_dir), str(out_json), str(cprofile_top)]
	try:
		# 2026-11-24
		# "Detach inherited stdin pipes in Harness test runners and Git hook helpers":
		# https://github.com/dmitry-ai/harness/issues/204
		proc = subprocess.run(cmd, cwd=str(top_dir.parent), env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=timeout_s, creationflags=_NO_WINDOW)
		r = json.loads(out_json.read_text(encoding='utf-8')) if 0 == proc.returncode and out_json.is_file() else _worker_error(mod_path, top_dir, f'exit {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:300]}')
	except subprocess.TimeoutExpired:
		r = _worker_error(mod_path, top_dir, f'timeout after {timeout_s}s')
	return r
# @used-by :func:`_run_worker()`
def _worker_error(mod_path: Path, top_dir: Path, msg: str) -> dict[str, Any]:
	return {'file': mod_path.relative_to(top_dir).as_posix(), 'load_s': 0.0, 'run_s': 0.0, 'tests_run': 0, 'failures': 0, 'errors': 1, 'skipped': 0, 'import_stats': {}, 'tests': [], 'cprofile': [], 'worker_error': msg}
# @used-by :func:`agent_tools.cli_registry._format_perf_profile_tests()`
# @used-by :mod:`agent_tools.perf`
def format_profile_text(report: dict[str, Any]) -> str:
	tot = report.get('totals') or {}
	lines = [
		f"Tests dir: {report.get('tests_dir')}",
		f"Parallel wall: {report.get('parallel_wall_s')}s (sum_run: {report.get('sum_file_run_s')}s, workers: {report.get('workers')}/{report.get('cpu_count')})",
		f"Files: {report.get('total_files')} Tests: {report.get('total_tests')} Failures: {report.get('total_failures')} Errors: {report.get('total_errors')} Skipped: {report.get('total_skipped')}",
		f"Popen: count={tot.get('popen_count')} s={tot.get('popen_s')} (git={tot.get('git_count')}/{tot.get('git_s')}s python={tot.get('python_count')}/{tot.get('python_s')}s other={tot.get('other_proc_count')}/{tot.get('other_proc_s')}s) Sleep: {tot.get('sleep_count')}/{tot.get('sleep_s')}s",
	]
	for item in report.get('top_files') or ():
		lines.append(f"TopFile: {item['file']} run_s={item['run_s']} ({item['share_pct']}%) tests={item['tests_run']} popen={item['popen_count']}/{item['popen_s']}s")
	return '\n'.join(lines) + '\n'
# 2026-11-24
# "Add harness perf-profile-tests CLI for test suite and subprocess profiling":
# https://github.com/dmitry-ai/harness/issues/192
# @used-by :func:`run_perf_profile_cli()`
# @used-by :meth:`test_perf_profile_tests.PerfProfileTestsSuiteTests.test_profile_test_suite_measures_files_tests_popen_sleep_and_cprofile()`
# @used-by :mod:`agent_tools.perf`
def profile_test_suite(tests_dir: Path | str | None=None, *, workers: int | None=None, module_timeout: float=300.0, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None, enable_cprofile: bool=False, top_n: int=15, cprofile_top: int=25) -> dict[str, Any]:
	base, ordered = discover_test_modules(tests_dir, pattern=pattern, modules=modules)
	if not ordered:
		raise ValueError(f'No test modules matched pattern {pattern!r} in {base}')
	eff_workers = min(max(1, int(workers)) if None is not workers else _default_workers(), len(ordered))
	cp_limit = max(1, int(cprofile_top)) if enable_cprofile else 0
	t0 = time.perf_counter()
	with tempfile.TemporaryDirectory() as td:
		tmp_dir = Path(td)
		with ThreadPoolExecutor(max_workers=eff_workers) as pool:
			futs = [pool.submit(_run_worker, mod, base, timeout_s=float(module_timeout), cprofile_top=cp_limit, tmp_dir=tmp_dir, idx=i) for i, mod in enumerate(ordered)]
			file_rows = [f.result() for f in futs]
	wall_s = round(max(0.0, time.perf_counter() - t0), 4)
	return _assemble_report(base, file_rows, eff_workers, wall_s, top_n, cp_limit)
# @used-by :func:`agent_tools.cli_registry._exec_perf_profile_tests()`
def run_perf_profile_cli(args) -> dict[str, Any]:
	report = profile_test_suite(args.target, workers=args.workers, module_timeout=args.module_timeout, pattern=args.pattern, modules=args.module, enable_cprofile=bool(args.cprofile), top_n=args.top, cprofile_top=args.cprofile_top)
	if None is not args.output:
		out_p = Path(args.output).resolve()
		out_p.parent.mkdir(parents=True, exist_ok=True)
		out_p.write_text(json.dumps(report, ensure_ascii=False, indent='\t') + '\n', encoding='utf-8')
		report['output_file'] = out_p.as_posix()
	return report
