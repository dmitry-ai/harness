# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.DiffExecutability import DiffExecutability
from .diff_contract import DIFF_EXECUTABILITY_GATES, MIXED_COMMIT_COMMENT_THRESHOLD, check_staged_mixed_commit_warning, check_touched_mixed_commit_warning, detect_mixed_commit_warning, should_run_snapshot_canary
DEFAULT_MAX_REPORTED_FILES = DiffExecutability.DEFAULT_MAX_REPORTED_FILES
NON_EXECUTABLE_CATEGORIES = DiffExecutability.NON_EXECUTABLE_CATEGORIES
# @used-by :mod:`agent_tools.tdd.diff_executability`
def _summarize_categories(file_categories: dict[str, str]) -> dict[str, Any]:
	return DiffExecutability.summarize_categories(file_categories)
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def classify_git_path(repo_root: Path, rel_posix: str, *, disk_text: str | None=None, use_index: bool=False, message: str | None=None, project_root: Path | None=None) -> str:
	return DiffExecutability.classify_git_path(repo_root, rel_posix, disk_text=disk_text, use_index=use_index, message=message, project_root=project_root)
# @used-by :func:`resolve_land_test_plan()`
# @used-by :meth:`Df.Harness.Git.PolyglotTestRunner.PolyglotTestRunner.run()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def classify_git_range(repo_root: Path, base_ref: str, head_ref: str='HEAD', *, message: str | None=None, project_root: Path | None=None) -> dict[str, Any]:
	return DiffExecutability.classify_git_range(repo_root, base_ref, head_ref, message=message, project_root=project_root)
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_whitespace_only_and_indentation_sensitive_fail_closed()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def classify_text_diff(path: str | Path, old_text: str | None, new_text: str | None, *, repo_root: Path | None=None, message: str | None=None, project_root: Path | None=None) -> str:
	return DiffExecutability.classify_text_diff(path, old_text, new_text, repo_root=repo_root, message=message, project_root=project_root)
# @used-by :func:`Df.Harness.lib.worktree.dfh_attach_land_telemetry()`
# @used-by :meth:`test_diff_executability_telemetry.DiffExecutabilityTelemetryTests.test_format_land_diff_telemetry_truncates_and_preserves_counts()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def format_land_diff_telemetry(plan: dict[str, Any] | None, *, max_files: int=DEFAULT_MAX_REPORTED_FILES) -> dict[str, Any]:
	return DiffExecutability.format_land_diff_telemetry(plan, max_files=max_files)
# @used-by :func:`agent_tools.tdd.exemption.is_git_path_exempt()`
# @used-by :func:`agent_tools.tdd.exemption.is_write_event_exempt()`
# @used-by :func:`test_diff_executability_contract._verify_tdd_gate_delegation()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_git_path_non_executable(repo_root: Path, rel_posix: str, *, disk_text: str | None=None, use_index: bool=False, message: str | None=None, project_root: Path | None=None) -> bool:
	return DiffExecutability.is_git_path_non_executable(repo_root, rel_posix, disk_text=disk_text, use_index=use_index, message=message, project_root=project_root)
# @used-by :func:`agent_tools.tdd.exemption.is_diff_exempt()`
# @used-by :func:`test_diff_executability_contract._verify_tdd_gate_delegation()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_non_executable_diff(path: str | Path, old_text: str | None, new_text: str | None, *, repo_root: Path | None=None, message: str | None=None, project_root: Path | None=None) -> bool:
	return DiffExecutability.is_non_executable_diff(path, old_text, new_text, repo_root=repo_root, message=message, project_root=project_root)
# @used-by :meth:`Df.Harness.Git.WorktreeRebaseVerifier.WorktreeRebaseVerifier.__run_land_checks()`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def resolve_land_test_plan(wt_path: Path, target_branch: str, *, run_tests: bool, no_tests_reason: str | None=None, project_root: Path | None=None) -> dict[str, Any]:
	return DiffExecutability.resolve_land_test_plan(wt_path, target_branch, run_tests=run_tests, no_tests_reason=no_tests_reason, project_root=project_root, classify_range_fn=classify_git_range)
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def validate_no_tests_override_reason(reason: str | None) -> tuple[bool, str | None]:
	return DiffExecutability.validate_no_tests_override_reason(reason)
__all__ = ['DEFAULT_MAX_REPORTED_FILES', 'DIFF_EXECUTABILITY_GATES', 'MIXED_COMMIT_COMMENT_THRESHOLD', 'NON_EXECUTABLE_CATEGORIES', '_summarize_categories', 'check_staged_mixed_commit_warning', 'check_touched_mixed_commit_warning', 'classify_git_path', 'classify_git_range', 'classify_text_diff', 'detect_mixed_commit_warning', 'format_land_diff_telemetry', 'is_git_path_non_executable', 'is_non_executable_diff', 'resolve_land_test_plan', 'should_run_snapshot_canary', 'validate_no_tests_override_reason']
