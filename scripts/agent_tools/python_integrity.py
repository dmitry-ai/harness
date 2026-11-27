# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.git import df_git_read_text
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.PythonIntegrity import PythonIntegrity
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
def _git_read_text(repo: Path, *args: str) -> str | None:
	return df_git_read_text(repo, *args)
# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_python_integrity_catches_syntax_and_undefined_globals_zero_fp_on_harness()`
# @used-by :mod:`agent_tools.python_integrity`
def check_python_integrity(path: str | Path, source: str) -> list[str]:
	return PythonIntegrity.check(path, source)
# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_python_integrity_catches_syntax_and_undefined_globals_zero_fp_on_harness()`
# @used-by :mod:`agent_tools.python_integrity`
def verify_directory_python_integrity(root_dir: Path) -> list[str]:
	return PythonIntegrity.verify_directory(root_dir)
# @used-by :mod:`agent_tools.python_integrity`
def verify_python_file_integrity(path: Path, *, rel_label: str | None=None) -> list[str]:
	return PythonIntegrity.verify_file(path, rel_label=rel_label)
# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__check_repo_commits_and_files()`
# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_snapshot_promotion_and_auditor_reject_undefined_global()`
# @used-by :mod:`agent_tools.python_integrity`
def verify_touched_python_files(repo_root: Path, rel_paths: list[str] | set[str]) -> list[str]:
	return PythonIntegrity.verify_touched(repo_root, rel_paths)
# @used-by :meth:`Df.Harness.Git.WorktreeRebaseVerifier.WorktreeRebaseVerifier.verify()`
# @used-by :mod:`agent_tools.python_integrity`
def verify_worktree_python_changes(wt_path: Path, target_branch: str) -> list[str]:
	return PythonIntegrity.verify_worktree(wt_path, target_branch)
__all__ = ['check_python_integrity', 'verify_directory_python_integrity', 'verify_python_file_integrity', 'verify_touched_python_files', 'verify_worktree_python_changes']
