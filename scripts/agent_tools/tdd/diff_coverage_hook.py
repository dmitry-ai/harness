# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add RLock to path_cache and migrate diff_coverage to sys.monitoring":
# https://github.com/dmitry-ai/harness/issues/352
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import os
import sys
SITE_HOOK_CODE = """import atexit, json, os, sys, threading, uuid
_raw_t = os.environ.get('HARNESS_DIFF_COV_TARGETS') or ''
_out_d = os.environ.get('HARNESS_DIFF_COV_DIR') or ''
_req_b = (os.environ.get('HARNESS_DIFF_COV_BACKEND') or 'auto').strip().lower()
if _raw_t and _out_d:
	_targets = set(json.loads(_raw_t))
	_cache = {}
	_hits = set()
	_mon_id = None
	def _norm(p):
		v = _cache.get(p)
		if None is v:
			v = os.path.normcase(os.path.realpath(p))
			_cache[p] = v
		return v
	def _line_tr(frame, event, _arg):
		if 'line' == event:
			_hits.add((_norm(frame.f_code.co_filename), frame.f_lineno))
		return _line_tr
	def _call_tr(frame, event, _arg):
		r = None
		if 'call' == event and '<module>' != frame.f_code.co_name:
			fn = frame.f_code.co_filename
			if fn and _norm(fn) in _targets:
				np = _norm(fn)
				_hits.add((np, frame.f_code.co_firstlineno))
				_hits.add((np, frame.f_lineno))
				r = _line_tr
		return r
	def _install_monitoring():
		global _mon_id
		ok = False
		mon = getattr(sys, 'monitoring', None)
		if None is not mon and 'settrace' != _req_b:
			for tid in (2, 3, 4, 5):
				if None is mon.get_tool(tid):
					try:
						mon.use_tool_id(tid, 'harness_diff_cov')
						_mon_id = tid
						break
					except ValueError:
						continue
			if None is not _mon_id:
				def _on_start(code, _offset):
					if '<module>' != code.co_name:
						fn = code.co_filename
						if fn and _norm(fn) in _targets:
							_hits.add((_norm(fn), code.co_firstlineno))
					return mon.DISABLE
				mon.register_callback(_mon_id, mon.events.PY_START, _on_start)
				mon.set_events(_mon_id, mon.events.PY_START)
				ok = True
		return ok
	def _flush():
		if None is not _mon_id:
			try:
				mon = sys.monitoring
				mon.set_events(_mon_id, 0)
				mon.register_callback(_mon_id, mon.events.PY_START, None)
				mon.free_tool_id(_mon_id)
			except Exception:
				pass
		if _hits:
			dest = os.path.join(_out_d, f'{os.getpid()}-{uuid.uuid4().hex[:8]}.json')
			with open(dest, 'w', encoding='utf-8') as fh:
				json.dump(sorted(_hits), fh)
	atexit.register(_flush)
	if not _install_monitoring():
		sys.settrace(_call_tr)
		threading.settrace(_call_tr)
"""
# @used-by :func:`agent_tools.tdd.diff_coverage.evaluate_collected_diff_coverage()`
# @used-by :func:`prepare_single_pass_coverage_env()`
# @used-by :mod:`agent_tools.tdd.diff_coverage_hook`
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def resolve_trace_backend(trace_backend: str='auto') -> str:
	req = (trace_backend or 'auto').strip().lower()
	if 'settrace' == req:
		r = 'sys.settrace'
	else:
		r = 'sys.monitoring' if hasattr(sys, 'monitoring') else 'sys.settrace'
	return r
# @used-by :func:`agent_tools.tdd.diff_coverage.run_trace_diff_coverage()`
# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_diff_coverage_sys_monitoring_matches_settrace_and_supports_single_pass()`
# @used-by :mod:`agent_tools.tdd.diff_coverage_hook`
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def prepare_single_pass_coverage_env(repo_root: Path, added_funcs: dict[str, list[dict[str, Any]]], work_dir: Path, *, trace_backend: str='auto') -> tuple[dict[str, str], Path]:
	targets = [os.path.normcase(os.path.realpath(str(repo_root / rel))) for rel in sorted(added_funcs)]
	site_dir = work_dir / 'site'
	cov_dir = work_dir / 'cov'
	site_dir.mkdir(parents=True, exist_ok=True)
	cov_dir.mkdir(parents=True, exist_ok=True)
	(site_dir / 'sitecustomize.py').write_text(SITE_HOOK_CODE, encoding='utf-8')
	prev_pp = os.environ.get('PYTHONPATH', '')
	backend_tag = 'settrace' if 'sys.settrace' == resolve_trace_backend(trace_backend) else 'monitoring'
	env = {**os.environ, 'PYTHONPATH': f'{site_dir}{os.pathsep}{prev_pp}' if prev_pp else str(site_dir), 'HARNESS_DIFF_COV_TARGETS': json.dumps(targets), 'HARNESS_DIFF_COV_DIR': str(cov_dir), 'HARNESS_DIFF_COV_BACKEND': backend_tag, 'HARNESS_TEST_NO_FSYNC': '1', 'GIT_OPTIONAL_LOCKS': '0', 'PYTHONDONTWRITEBYTECODE': '1'}
	return (env, cov_dir)
__all__ = ['SITE_HOOK_CODE', 'prepare_single_pass_coverage_env', 'resolve_trace_backend']
