# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify process-tree termination in parallel_runner and enforce AST subprocess hygiene in pre-commit":
# https://github.com/dmitry-ai/harness/issues/206
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Detach inherited stdin pipes in Harness test runners and Git hook helpers":
# https://github.com/dmitry-ai/harness/issues/204
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Deduplicate historical admission fixtures and guard optional temp fsync":
# https://github.com/dmitry-ai/harness/issues/177
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add parallel fail-fast test runner and worktree-aware TDD support":
# https://github.com/dmitry-ai/harness/issues/159
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from .process_tree import POPEN_TREE_KWARGS, kill_process_tree
from .storage import replace_bytes
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_RAN_RE = re.compile(r'(?m)^Ran\s+(\d+)\s+tests?\s+in\s+')
def _build_worker_cmd(module: Path, *, failfast: bool, buffer_output: bool) -> list[str]:
	cmd = [sys.executable, '-m', 'unittest']
	if failfast:
		cmd.append('-f')
	if buffer_output:
		cmd.append('-b')
	cmd.append(module.stem)
	return cmd
def _close_proc_pipes(proc: subprocess.Popen) -> None:
	for stream in (proc.stdout, proc.stderr):
		if None is not stream:
			try:
				stream.close()
			except OSError:
				pass
def _kill_proc_tree(proc: subprocess.Popen) -> None:
	kill_process_tree(proc)
def _load_timings(cache_path: Path | None) -> dict[str, float]:
	r: dict[str, float] = {}
	if None is not cache_path and cache_path.is_file():
		try:
			raw = json.loads(cache_path.read_text(encoding='utf-8'))
			if isinstance(raw, dict):
				r = {str(k): float(v) for k, v in raw.items() if isinstance(v, (int, float))}
		except (OSError, ValueError):
			r = {}
	return r
def _parse_ran_count(output: str) -> int:
	m = _RAN_RE.search(output or '')
	return int(m.group(1)) if m else 0
def _poll_proc(proc: subprocess.Popen, deadline: float, stop_event: threading.Event) -> tuple[bool, bool]:
	timed_out = False
	aborted = False
	while None is proc.poll():
		if stop_event.is_set():
			aborted = True
			_kill_proc_tree(proc)
			break
		if time.monotonic() >= deadline:
			timed_out = True
			_kill_proc_tree(proc)
			break
		time.sleep(0.05)
	return (timed_out, aborted)
def _read_proc_output(proc: subprocess.Popen) -> str:
	try:
		out, err = proc.communicate(timeout=2.0)
	except (OSError, subprocess.TimeoutExpired):
		_kill_proc_tree(proc)
		_close_proc_pipes(proc)
		out, err = ('', '')
	parts = [p for p in (out, err) if p]
	return '\n'.join(parts)
def _run_single_module(module: Path, tests_dir: Path, *, failfast: bool, buffer_output: bool, timeout: float, stop_event: threading.Event, active_procs: set, active_lock: threading.Lock) -> dict:
	started = time.monotonic()
	if stop_event.is_set():
		r = {'module': module.stem, 'ok': False, 'returncode': -1, 'timed_out': False, 'aborted': True, 'tests': 0, 'duration': 0.0, 'output': ''}
	else:
		cmd = _build_worker_cmd(module, failfast=failfast, buffer_output=buffer_output)
		env = {'HARNESS_TEST_NO_FSYNC': '1', **os.environ, 'PYTHONUTF8': '1', 'GIT_OPTIONAL_LOCKS': '0'}
		proc = subprocess.Popen(cmd, cwd=str(tests_dir), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', env=env, **POPEN_TREE_KWARGS)
		with active_lock:
			active_procs.add(proc)
		try:
			timed_out, aborted = _poll_proc(proc, started + max(0.1, float(timeout)), stop_event)
			output = _read_proc_output(proc)
			rc = proc.returncode if None is not proc.returncode else -1
		finally:
			with active_lock:
				active_procs.discard(proc)
		dur = round(time.monotonic() - started, 3)
		r = {'module': module.stem, 'ok': (0 == rc) and (not timed_out) and (not aborted), 'returncode': rc, 'timed_out': timed_out, 'aborted': aborted, 'tests': _parse_ran_count(output), 'duration': dur, 'output': output}
	return r
def _save_timings(cache_path: Path | None, results: list[dict]) -> None:
	if None is not cache_path:
		existing = _load_timings(cache_path)
		for item in results:
			if item.get('ok'):
				existing[item['module']] = float(item['duration'])
		try:
			replace_bytes(cache_path, (json.dumps(existing, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8'))
		except OSError:
			pass
def _stop_siblings(stop_event: threading.Event, active_procs: set, active_lock: threading.Lock) -> None:
	stop_event.set()
	with active_lock:
		procs = list(active_procs)
	for proc in procs:
		_kill_proc_tree(proc)
def _summarize_results(results: list[dict], *, total_modules: int, workers: int, elapsed: float) -> dict:
	passed = sum((1 for item in results if item['ok']))
	total_tests = sum((int(item['tests']) for item in results))
	first_fail = next((item for item in results if (not item['ok']) and (not item['aborted'])), None)
	ok = (None is first_fail) and (passed == total_modules)
	slowest = sorted(({'module': it['module'], 'duration': it['duration'], 'tests': it['tests']} for it in results if not it['aborted']), key=lambda x: -x['duration'])[:10]
	status_line = f'Ran {total_tests} tests in {elapsed:.3f}s\n' + ('OK' if ok else 'FAILED')
	return {'ok': ok, 'valid': ok, 'exit_code': 0 if ok else 1, 'workers': workers, 'total_modules': total_modules, 'passed_modules': passed, 'total_tests': total_tests, 'duration_seconds': round(elapsed, 3), 'failed_module': first_fail['module'] if first_fail else None, 'timed_out': bool(first_fail and first_fail['timed_out']), 'failure_output': (first_fail['output'][-4000:] if first_fail else ''), 'slowest_modules': slowest, 'summary': status_line}
def default_worker_count(module_count: int) -> int:
	cpus = os.cpu_count() or 4
	return max(1, min(max(1, int(module_count)), min(8, cpus)))
def discover_test_modules(tests_dir: Path | str, *, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None, timings: dict[str, float] | None=None) -> list[Path]:
	root = Path(tests_dir).resolve()
	if not root.is_dir():
		raise FileNotFoundError(f'Tests directory not found: {root}')
	found = [p for p in sorted(root.glob(pattern)) if p.is_file()]
	if modules:
		wanted = {Path(m).stem.lower() for m in modules if str(m).strip()}
		found = [p for p in found if p.stem.lower() in wanted]
	t_map = timings or {}
	def _sort_key(path: Path) -> tuple[float, int, str]:
		try:
			size = path.stat().st_size
		except OSError:
			size = 0
		return (-float(t_map.get(path.stem, -1.0)), -size, path.stem)
	return sorted(found, key=_sort_key)
def run_parallel_tests(tests_dir: Path | str, *, workers: int | None=None, pattern: str='test_*.py', modules: list[str] | tuple[str, ...] | None=None, failfast: bool=True, buffer_output: bool=True, module_timeout: float=180.0, timings_file: Path | None=None) -> dict:
	root = Path(tests_dir).resolve()
	timings = _load_timings(timings_file)
	mod_list = discover_test_modules(root, pattern=pattern, modules=modules, timings=timings)
	if not mod_list:
		raise ValueError(f'No test modules matched {pattern!r} in {root}')
	eff_workers = max(1, int(workers)) if None is not workers else default_worker_count(len(mod_list))
	stop_event = threading.Event()
	active_procs: set = set()
	active_lock = threading.Lock()
	results: list[dict] = []
	started = time.monotonic()
	pool = ThreadPoolExecutor(max_workers=eff_workers)
	try:
		futs = {pool.submit(_run_single_module, mod, root, failfast=failfast, buffer_output=buffer_output, timeout=module_timeout, stop_event=stop_event, active_procs=active_procs, active_lock=active_lock): mod for mod in mod_list}
		for fut in as_completed(futs):
			res = fut.result()
			results.append(res)
			if failfast and (not res['ok']) and (not res['aborted']):
				_stop_siblings(stop_event, active_procs, active_lock)
				break
	finally:
		pool.shutdown(wait=True, cancel_futures=True)
	summary = _summarize_results(results, total_modules=len(mod_list), workers=eff_workers, elapsed=time.monotonic() - started)
	if summary['ok']:
		_save_timings(timings_file, results)
	return summary
