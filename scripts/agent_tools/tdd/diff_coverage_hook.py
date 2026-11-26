# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.DiffCoverageHook import DiffCoverageHook
SITE_HOOK_CODE = DiffCoverageHook.SITE_HOOK_CODE
# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_diff_coverage_sys_monitoring_matches_settrace_and_supports_single_pass()`
# @used-by :mod:`agent_tools.tdd.diff_coverage_hook`
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def prepare_single_pass_coverage_env(repo_root: Path, added_funcs: dict[str, list[dict[str, Any]]], work_dir: Path, *, trace_backend: str='auto') -> tuple[dict[str, str], Path]:
	return DiffCoverageHook(repo_root, added_funcs, work_dir, trace_backend=trace_backend).prepare_env()
# @used-by :mod:`agent_tools.tdd.diff_coverage_hook`
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def resolve_trace_backend(trace_backend: str='auto') -> str:
	return DiffCoverageHook.resolve_trace_backend(trace_backend)
__all__ = ['SITE_HOOK_CODE', 'prepare_single_pass_coverage_env', 'resolve_trace_backend']
