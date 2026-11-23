# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add harness perf-profile-tests CLI for test suite and subprocess profiling":
# https://github.com/dmitry-ai/harness/issues/192
from __future__ import annotations
from pathlib import Path
from typing import Any
import cProfile
import json
import os
import pstats
import subprocess
import sys
import time
import unittest
_STAT_KEYS = ('popen_count', 'popen_s', 'git_count', 'git_s', 'python_count', 'python_s', 'other_proc_count', 'other_proc_s', 'sleep_count', 'sleep_s')
def _blank_stats() -> dict[str, Any]:
	return {k: 0 if k.endswith('_count') else 0.0 for k in _STAT_KEYS}
def _classify_proc_args(args: Any) -> str:
	first = args[0] if isinstance(args, (list, tuple)) and args else (str(args or '').split()[0] if str(args or '').strip() else '')
	low = Path(str(first).strip('"\'')).name.lower()
	if low in ('git', 'git.exe', 'git.cmd'):
		r = 'git'
	elif low.startswith(('python', 'py.exe', 'pytest')):
		r = 'python'
	else:
		r = 'other_proc'
	return r
def _diff_stats(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
	return {k: (after[k] - before[k]) if k.endswith('_count') else round(max(0.0, after[k] - before[k]), 4) for k in _STAT_KEYS}
def _extract_cprofile(prof: cProfile.Profile, top_n: int) -> list[dict[str, Any]]:
	st = pstats.Stats(prof)
	rows = []
	for (fname, lineno, func), (_cc, nc, tt, ct, _callers) in st.stats.items():
		rows.append({'file': Path(fname).as_posix() if fname else '', 'line': int(lineno), 'func': str(func), 'ncalls': int(nc), 'tottime': round(float(tt), 5), 'cumtime': round(float(ct), 5)})
	rows.sort(key=lambda item: (-item['cumtime'], -item['tottime']))
	return rows[:max(1, int(top_n))]
def _install_hooks(stats: dict[str, Any]) -> tuple[Any, Any]:
	orig_popen, orig_sleep = (subprocess.Popen, time.sleep)
	class _TrackedPopen(orig_popen):
		def __init__(self, args, *a, **kw):
			self._perf_cat = _classify_proc_args(args)
			self._perf_t0 = time.perf_counter()
			self._perf_done = False
			super().__init__(args, *a, **kw)
		def _perf_finish(self) -> None:
			if not self._perf_done:
				self._perf_done = True
				dt = max(0.0, time.perf_counter() - self._perf_t0)
				stats['popen_count'] += 1
				stats['popen_s'] += dt
				stats[f'{self._perf_cat}_count'] += 1
				stats[f'{self._perf_cat}_s'] += dt
		def communicate(self, *a, **kw):
			try:
				return super().communicate(*a, **kw)
			finally:
				self._perf_finish()
		def wait(self, *a, **kw):
			try:
				return super().wait(*a, **kw)
			finally:
				self._perf_finish()
	def _tracked_sleep(secs: float) -> None:
		t0 = time.perf_counter()
		try:
			orig_sleep(secs)
		finally:
			stats['sleep_count'] += 1
			stats['sleep_s'] += max(0.0, time.perf_counter() - t0)
	subprocess.Popen = _TrackedPopen
	time.sleep = _tracked_sleep
	return (orig_popen, orig_sleep)
class _TimedResult(unittest.TestResult):
	def __init__(self, stats: dict[str, Any], rel_file: str) -> None:
		super().__init__()
		self._stats = stats
		self._rel_file = rel_file
		self._t0 = 0.0
		self._snap: dict[str, Any] = {}
		self._status = 'ok'
		self.records: list[dict[str, Any]] = []
	def addError(self, test, err) -> None:
		self._status = 'error'
		super().addError(test, err)
	def addFailure(self, test, err) -> None:
		self._status = 'fail'
		super().addFailure(test, err)
	def addSkip(self, test, reason) -> None:
		self._status = 'skip'
		super().addSkip(test, reason)
	def startTest(self, test) -> None:
		self._status = 'ok'
		self._t0 = time.perf_counter()
		self._snap = dict(self._stats)
		super().startTest(test)
	def stopTest(self, test) -> None:
		super().stopTest(test)
		dt = round(max(0.0, time.perf_counter() - self._t0), 4)
		delta = _diff_stats(self._snap, self._stats)
		self.records.append({'test_id': test.id(), 'file': self._rel_file, 'status': self._status, 'dur_s': dt, **delta})
def main(argv: list[str] | None=None) -> int:
	args = list(sys.argv[1:] if None is argv else argv)
	mod_p, top_p, out_p = (Path(args[0]).resolve(), Path(args[1]).resolve(), Path(args[2]).resolve())
	cp_top = int(args[3]) if 3 < len(args) else 0
	if str(top_p) not in sys.path:
		sys.path.insert(0, str(top_p))
	os.environ.setdefault('HARNESS_TEST_NO_FSYNC', '1')
	data = run_module_profile(mod_p, top_p, cprofile_top=cp_top)
	out_p.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
	return 0
def run_module_profile(mod_path: Path, top_dir: Path, *, cprofile_top: int=0) -> dict[str, Any]:
	rel = mod_path.relative_to(top_dir).as_posix()
	stats = _blank_stats()
	orig_popen, orig_sleep = _install_hooks(stats)
	try:
		t_load0 = time.perf_counter()
		suite = unittest.defaultTestLoader.discover(str(mod_path.parent), pattern=mod_path.name, top_level_dir=str(top_dir))
		load_s = round(max(0.0, time.perf_counter() - t_load0), 4)
		import_stats = _diff_stats(_blank_stats(), stats)
		result = _TimedResult(stats, rel)
		prof = cProfile.Profile() if 0 < cprofile_top else None
		t_run0 = time.perf_counter()
		suite.run(result) if None is prof else prof.runcall(suite.run, result)
		run_s = round(max(0.0, time.perf_counter() - t_run0), 4)
	finally:
		subprocess.Popen, time.sleep = (orig_popen, orig_sleep)
	cp_rows = _extract_cprofile(prof, cprofile_top) if None is not prof else []
	return {'file': rel, 'load_s': load_s, 'run_s': run_s, 'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped), 'import_stats': import_stats, 'tests': result.records, 'cprofile': cp_rows}
if '__main__' == __name__:
	raise SystemExit(main())
