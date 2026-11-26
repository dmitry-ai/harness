# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Git.WorktreeCommandGuard import WorktreeCommandGuard
from Df.Harness.Git.WorktreeLockFinder import WorktreeLockFinder
from Df.Harness.Git.WorktreeRemovalGuard import WorktreeRemovalGuard
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :func:`agent_tools.worktree_flow.worktree_cleanup()`
# @used-by :func:`remove_worktree_fail_closed()`
# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_worktree_cleanup_fails_closed_with_lock_holders_on_locked_dir()`
# @used-by :mod:`agent_tools.worktree_guard`
def find_worktree_lock_holders(wt_path: Path, *, process_rows: list[dict[str, Any]] | None=None) -> list[dict[str, Any]]:
	return WorktreeLockFinder(wt_path, process_rows=process_rows).find()
# @used-by :meth:`Df.Harness.Gate.GitWriteGate.GitWriteGate.check()`
# @used-by :mod:`agent_tools.worktree_guard`
def prohibited_worktree_remove_commands(command_line: str) -> list[str]:
	return WorktreeCommandGuard(command_line).check(mode='remove')
# @used-by :meth:`Df.Harness.Gate.WorktreeIsolationGate.WorktreeIsolationGate.check()`
# @used-by :mod:`agent_tools.worktree_guard`
def prohibited_worktree_shell_deletions(command_line: str) -> list[str]:
	return WorktreeCommandGuard(command_line).check(mode='delete')
# @used-by :mod:`agent_tools.worktree_guard`
def remove_worktree_fail_closed(main_repo: Path, wt_path: Path, *, force: bool, git_exec_fn) -> dict[str, Any]:
	return WorktreeRemovalGuard(main_repo, wt_path, force=force, git_exec_fn=git_exec_fn, lock_finder_fn=find_worktree_lock_holders).remove()
__all__ = ['find_worktree_lock_holders', 'prohibited_worktree_remove_commands', 'prohibited_worktree_shell_deletions', 'remove_worktree_fail_closed']
