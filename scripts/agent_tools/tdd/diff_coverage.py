# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import subprocess
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.DiffCoverage import DiffCoverage
from .diff_coverage_hook import prepare_single_pass_coverage_env, resolve_trace_backend
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_gates_and_classifiers_recognize_dotpy_files()`
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def _prod_match_tokens(changed_prod_rels: list[str]) -> set[str]:
	return DiffCoverage.prod_match_tokens(changed_prod_rels)
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_tdd_check_turn()`
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def enrich_tdd_check_report(root_p: Path, role: str, turn_key: str, turn_obj: dict[str, Any], tdd_chk: dict[str, Any]) -> dict[str, Any]:
	return DiffCoverage.enrich_tdd_check_report(root_p, role, turn_key, turn_obj, tdd_chk)
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def evaluate_collected_diff_coverage(repo_root: Path, added_funcs: dict[str, list[dict[str, Any]]], cov_dir: Path, *, exit_code: int=0, timed_out: bool=False, trace_backend: str='auto', targeted_modules: list[str] | None=None) -> dict[str, Any]:
	return DiffCoverage.evaluate_collected(repo_root, added_funcs, cov_dir, exit_code=exit_code, timed_out=timed_out, trace_backend=trace_backend, targeted_modules=targeted_modules)
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_decorated_methods_covered_under_sys_monitoring()`
# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_diff_coverage_sys_monitoring_matches_settrace_and_supports_single_pass()`
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def find_added_production_functions(repo_root: Path, *, base_ref: str='HEAD', include_working_tree: bool=False) -> dict[str, list[dict[str, Any]]]:
	return DiffCoverage.find_added_production_functions(repo_root, base_ref=base_ref, include_working_tree=include_working_tree)
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_run_trace_diff_coverage_handles_timeout_gracefully()`
# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_diff_coverage_sys_monitoring_matches_settrace_and_supports_single_pass()`
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def run_trace_diff_coverage(repo_root: Path, added_funcs: dict[str, list[dict[str, Any]]], test_modules: list[Path], *, timeout: float=240.0, trace_backend: str='auto') -> dict[str, Any]:
	return DiffCoverage.run_trace(repo_root, added_funcs, test_modules, timeout=timeout, trace_backend=trace_backend)
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_select_targeted_falls_back_to_direct_when_large_diff_has_no_token_match()`
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_select_targeted_narrows_large_cross_cutting_test_diffs_to_prod_stems_and_packages()`
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_select_targeted_prefers_changed_tests_over_unrelated_stem_matches()`
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def select_targeted_test_modules(repo_root: Path, changed_prod_rels: list[str], *, base_ref: str='HEAD', include_working_tree: bool=False) -> list[Path]:
	return DiffCoverage.select_targeted_test_modules(repo_root, changed_prod_rels, base_ref=base_ref, include_working_tree=include_working_tree)
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_decorated_methods_covered_under_sys_monitoring()`
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def verify_repo_diff_coverage(repo_root: Path, *, base_ref: str='HEAD') -> dict[str, Any]:
	return DiffCoverage.verify_repo(repo_root, base_ref=base_ref)
# @used-by :meth:`Df.Harness.Git.WorktreeRebaseVerifier.WorktreeRebaseVerifier.__check_diff_coverage()`
# @used-by :mod:`agent_tools.tdd.diff_coverage`
def verify_worktree_diff_coverage(wt_path: Path, target_branch: str) -> dict[str, Any]:
	return DiffCoverage.verify_worktree(wt_path, target_branch)
__all__ = ['_prod_match_tokens', 'enrich_tdd_check_report', 'evaluate_collected_diff_coverage', 'find_added_production_functions', 'prepare_single_pass_coverage_env', 'resolve_trace_backend', 'run_trace_diff_coverage', 'select_targeted_test_modules', 'verify_repo_diff_coverage', 'verify_worktree_diff_coverage']
