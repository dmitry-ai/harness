# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.WorktreeScope import WorktreeScope
# @used-by :mod:`agent_tools.tdd.worktree_scope`
def canonical_scope_path(scope_key: str) -> Path:
	return WorktreeScope.canonical_scope_path(scope_key)
# @used-by :mod:`agent_tools.tdd.worktree_scope`
def extract_command_worktree_ids(event: dict) -> set[str]:
	return WorktreeScope.extract_command_worktree_ids(event)
# @used-by :mod:`agent_tools.tdd.worktree_scope`
def extract_worktree_scope_id(path: str | Path | None) -> str | None:
	return WorktreeScope.extract_worktree_scope_id(path)
# @used-by :mod:`agent_tools.tdd.worktree_scope`
def resolve_tdd_scope_key(path: str | Path, scope: str | Path) -> str:
	return WorktreeScope.resolve_key(path, scope)
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset()`
# @used-by :mod:`agent_tools.tdd.worktree_scope`
def scope_matches_commit(scope_key: str, commit_scope: str | None, event: dict | None=None) -> bool:
	return WorktreeScope.scope_matches_commit(scope_key, commit_scope, event)
# @used-by :mod:`agent_tools.tdd.worktree_scope`
def split_tdd_scope_key(scope_key: str) -> tuple[Path, str | None]:
	return WorktreeScope.split_key(scope_key)
# @used-by :mod:`agent_tools.tdd.worktree_scope`
def worktree_command_matches(event: dict, scope_key: str, is_full_cmd: bool) -> bool | None:
	return WorktreeScope.worktree_command_matches(event, scope_key, is_full_cmd)
__all__ = ['canonical_scope_path', 'extract_command_worktree_ids', 'extract_worktree_scope_id', 'resolve_tdd_scope_key', 'scope_matches_commit', 'split_tdd_scope_key', 'worktree_command_matches']
