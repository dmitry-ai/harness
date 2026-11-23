# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Deduplicate historical admission fixtures and guard optional temp fsync":
# https://github.com/dmitry-ai/harness/issues/177
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add parallel fail-fast run-tests runner with module timeouts and TDD gate registration":
# https://github.com/dmitry-ai/harness/issues/160
from __future__ import annotations
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_RAN_RE = re.compile(r'(?m)^Ran\s+(\d+)\s+tests?\s+in\s+')
_SKIP_DIRS = frozenset({'.git', '__pycache__', 'node_modules', 'venv', '.venv', '\ua616', '\ua66e', '\U0001f56e'})
_SKIPPED_RE = re.compile(r'\bskipped=(\d+)\b')
def _default_workers() -> int:
	return min(max(2, (os.cpu_count() or 4) // 2), 8)
def _kill_process_tree(proc: subprocess.Popen) -> None:
	if None is proc.poll():
		if 'nt' == os.name:
			subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True, check=False, creationflags=_NO_WINDOW)
		try:
			proc.kill()
		except OSError:
			pass
		try:
			proc.wait(timeout=5)
		except (OSError, subprocess.TimeoutExpired):
			pass
def _module_matches_filters(mod: Path, base_dir: Path, filters: list[str]) -> bool:
	rel = mod.relative_to(base_dir).as_posix().lower()
	name = mod.name.lower()
	stem = mod.stem.lower()
	return any((f in (rel, name, stem) or rel.endswith('/' + f) for f in filters))
def _parse_unittest_counts(text: str) -> tuple[int, int]:
	ran = sum((int(m.group(1)) for m in _RAN_RE.finditer(text or '')))
	skipped = sum((int(m.group(1)) for m in _SKIPPED_RE.finditer(text or '')))
	return (ran, skipped)
def _resolve_tests_dir(raw_dir: Path | str | None) -> Path:
	base = Path(raw_dir).resolve() if None is not raw_dir else (Path(__file__).resolve().parents[2] / 'tests').resolve()
	if not base.is_dir():
		raise FileNotFoundError(f'Test directory not found: {base}')
	sub_tests = base / 'tests'
	if sub_tests.is_dir() and (not any(base.glob('test_*.py'))):
		base = sub_tests.resolve()
	return base
def _run_module_worker(mod_path: Path, top_dir: Path, *, failfast: bool, module_timeout: float, stop_event: threading.Event, active_lock: threading.Lock, active_procs: set[subprocess.Popen]) -> dict:
	rel = mod_path.relative_to(top_dir).as_posix()
	if stop_event.is_set():
		r = {'module': rel, 'status': 'cancelled', 'returncode': None, 'elapsed': 0.0, 'tests': 0, 'skipped': 0, 'output': ''}
	else:
		cmd = [sys.executable, '-m', 'unittest', 'discover', '-s', str(mod_path.parent), '-t', str(top_dir), '-p', mod_path.name, '-b']
		if failfast:
			cmd.append('-f')
		started = time.monotonic()
		timed_out, cancelled = (False, False)
		with tempfile.TemporaryFile() as out_file:
			proc = subprocess.Popen(cmd, cwd=str(top_dir.parent), stdout=out_file, stderr=subprocess.STDOUT, env={'HARNESS_TEST_NO_FSYNC': '1', **os.environ}, creationflags=_NO_WINDOW)
			with active_lock:
				active_procs.add(proc)
			try:
				while None is proc.poll():
					if stop_event.is_set():
						cancelled = True
						_kill_process_tree(proc)
						break
					if (time.monotonic() - started) >= module_timeout:
						timed_out = True
						_kill_process_tree(proc)
						break
					time.sleep(0.05)
				rc = proc.wait(timeout=5)
			finally:
				with active_lock:
					active_procs.discard(proc)
			out_file.seek(0)
			output = out_file.read().decode('utf-8', errors='replace')
		elapsed = round(time.monotonic() - started, 3)
		tests, skipped = _parse_unittest_counts(output)
		status = 'timeout' if timed_out else 'cancelled' if cancelled else 'passed' if 0 == rc else 'failed'
		r = {'module': rel, 'status': status, 'returncode': rc, 'elapsed': elapsed, 'tests': tests, 'skipped': skipped, 'output': output}
	return r
def _terminate_active(active_lock: threading.Lock, active_procs: set[subprocess.Popen]) -> None:
	with active_lock:
		procs = list(active_procs)
	for proc in procs:
		_kill_process_tree(proc)
def discover_test_modules(tests_dir: Path | str | None=None, *, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None) -> tuple[Path, list[Path]]:
	base = _resolve_tests_dir(tests_dir)
	found: list[Path] = []
	for cand in base.rglob(pattern):
		if cand.is_file() and (not any((part in _SKIP_DIRS for part in cand.relative_to(base).parts[:-1]))):
			found.append(cand.resolve())
	norm_filters = [str(m).strip().replace('\\', '/').lower() for m in (modules or ()) if str(m).strip()]
	if norm_filters:
		found = [m for m in found if _module_matches_filters(m, base, norm_filters)]
	ordered = sorted(found, key=lambda p: (-p.stat().st_size, p.relative_to(base).as_posix()))
	return (base, ordered)
def format_text_report(report: dict) -> str:
	lines: list[str] = []
	for item in report.get('results') or []:
		st = item.get('status')
		if 'timeout' == st:
			lines.append(f"TIMEOUT: {item['module']} exceeded --module-timeout={report['module_timeout']}s ({item['elapsed']:.3f}s)")
			if item.get('output'):
				lines.append(item['output'].rstrip())
		elif 'failed' == st:
			lines.append(f"FAIL: {item['module']} (exit {item['returncode']}, {item['elapsed']:.3f}s)")
			if item.get('output'):
				lines.append(item['output'].rstrip())
	lines.append('-' * 70)
	lines.append(f"Ran {report['total_tests']} tests in {report['elapsed']:.3f}s ({report['passed_modules']}/{report['total_modules']} modules, workers={report['workers']})")
	lines.append('')
	if report['ok']:
		skip_part = f" (skipped={report['skipped_tests']})" if report['skipped_tests'] else ''
		lines.append(f'OK{skip_part}')
	else:
		parts = []
		if report['failed_modules']:
			parts.append(f"failures={report['failed_modules']}")
		if report['timed_out_modules']:
			parts.append(f"timeouts={report['timed_out_modules']}")
		lines.append(f"FAILED ({', '.join(parts) or 'error'})")
	return '\n'.join(lines) + '\n'
def run_test_suite(tests_dir: Path | str | None=None, *, workers: int | None=None, module_timeout: float=300.0, failfast: bool=True, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None) -> dict:
	base, ordered = discover_test_modules(tests_dir, pattern=pattern, modules=modules)
	if not ordered:
		raise ValueError(f'No test modules matched pattern {pattern!r} in {base}')
	eff_workers = max(1, int(workers)) if None is not workers else _default_workers()
	eff_workers = min(eff_workers, len(ordered))
	stop_event = threading.Event()
	active_lock = threading.Lock()
	active_procs: set[subprocess.Popen] = set()
	started = time.monotonic()
	results: list[dict] = []
	executor = ThreadPoolExecutor(max_workers=eff_workers)
	aborted = False
	try:
		pending = {executor.submit(_run_module_worker, mod, base, failfast=failfast, module_timeout=float(module_timeout), stop_event=stop_event, active_lock=active_lock, active_procs=active_procs): mod for mod in ordered}
		while pending:
			done, pending = wait(pending, return_when=FIRST_COMPLETED)
			for fut in done:
				res = fut.result()
				results.append(res)
				if failfast and res['status'] in ('failed', 'timeout'):
					aborted = True
					stop_event.set()
					_terminate_active(active_lock, active_procs)
					break
			if aborted:
				break
	finally:
		if aborted:
			stop_event.set()
			_terminate_active(active_lock, active_procs)
			executor.shutdown(wait=True, cancel_futures=True)
		else:
			executor.shutdown(wait=True, cancel_futures=False)
	elapsed = round(time.monotonic() - started, 3)
	passed = sum((1 for x in results if 'passed' == x['status']))
	failed = sum((1 for x in results if 'failed' == x['status']))
	timed_out = sum((1 for x in results if 'timeout' == x['status']))
	cancelled = len(ordered) - passed - failed - timed_out
	total_tests = sum((int(x['tests']) for x in results))
	skipped_tests = sum((int(x['skipped']) for x in results))
	ok = (0 == failed) and (0 == timed_out) and (passed == len(ordered)) and (0 < total_tests)
	return {
		'ok': ok,
		'exit_code': 0 if ok else 1,
		'tests_dir': base.as_posix(),
		'workers': eff_workers,
		'failfast': bool(failfast),
		'module_timeout': float(module_timeout),
		'scheduled_order': [m.relative_to(base).as_posix() for m in ordered],
		'total_modules': len(ordered),
		'passed_modules': passed,
		'failed_modules': failed,
		'timed_out_modules': timed_out,
		'cancelled_modules': cancelled,
		'total_tests': total_tests,
		'skipped_tests': skipped_tests,
		'elapsed': elapsed,
		'results': results,
	}
