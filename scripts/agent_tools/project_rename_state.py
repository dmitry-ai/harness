# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.text.source import df_text_rewrite_pairs
from Df.Harness.lib.project import dfh_rewrite_value
from Df.Harness.Project.Rename.RenameLineage import RenameLineage
from Df.Harness.Project.Rename.StateRewriter import StateRewriter
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
# @used-by :mod:`agent_tools.project_rename_state`
def _path_pairs(old_root: Path, new_root: Path, old_state: Path | None, new_state: Path | None) -> list[tuple[str, str]]:
	return RenameLineage.path_pairs(old_root, new_root, old_state, new_state)
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
# @used-by :mod:`agent_tools.project_rename_state`
def _rewrite_text(text: str, pairs: list[tuple[str, str]]) -> str:
	return df_text_rewrite_pairs(text, pairs)
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
# @used-by :mod:`agent_tools.project_rename_state`
def _rewrite_value(value, pairs: list[tuple[str, str]]):
	return dfh_rewrite_value(value, pairs)
# @used-by :mod:`agent_tools.project_rename_state`
def capture_file_sha(path: Path) -> str | None:
	return RenameLineage.capture_file_sha(path)
# @used-by :func:`agent_tools.platforms.trace_common.reviewer_isolation_issues()`
# @used-by :mod:`agent_tools.project_rename_state`
def find_sibling_project_path(raw_val: str, project_root: Path, daily_root: Path) -> Path | None:
	return RenameLineage.find_sibling_project_path(raw_val, project_root, daily_root)
# @used-by :mod:`agent_tools.project_rename_state`
def migrate_journal_state(old_root: Path, new_root: Path, *, backups: list[tuple[Path, bytes | None]] | None=None, state_moves: list[tuple[Path, Path]] | None=None) -> tuple[Path, Path]:
	return StateRewriter.migrate_journal_state(old_root, new_root, backups=backups, state_moves=state_moves)
# @used-by :mod:`agent_tools.project_rename_state`
def refresh_workflow_file_hash(new_root: Path, target_file: Path, old_sha: str | None) -> None:
	StateRewriter.refresh_workflow_file_hash(new_root, target_file, old_sha)
# @used-by :mod:`agent_tools.project_rename_state`
def rewrite_launcher_handoffs(launcher_root: Path, old_root: Path, new_root: Path, *, backups: list[tuple[Path, bytes | None]] | None=None) -> int:
	return StateRewriter.rewrite_launcher_handoffs(launcher_root, old_root, new_root, backups=backups)
# @used-by :mod:`agent_tools.project_rename_state`
def rewrite_project_internal_state(old_root: Path, new_root: Path, new_label: str, new_label_kind: str, *, backups: list[tuple[Path, bytes | None]] | None=None, state_moves: list[tuple[Path, Path]] | None=None) -> dict:
	return StateRewriter(old_root, new_root, new_label, new_label_kind, backups=backups, state_moves=state_moves).rewrite()
# @used-by :func:`agent_tools.journal.same_journal_identity()`
# @used-by :mod:`agent_tools.project_rename_state`
def same_journal_identity_with_rename(first: str | Path | None, second: str | Path | None, canon_fn) -> bool:
	return RenameLineage.same_journal_identity_with_rename(first, second, canon_fn)
# @used-by :func:`agent_tools.path_registry.same_project_root()`
# @used-by :mod:`agent_tools.project_rename_state`
def same_project_root_check(first: str | Path | None, second: str | Path | None, canon_fn, key_fn) -> bool:
	return RenameLineage.same_project_root_check(first, second, canon_fn, key_fn)
__all__ = ['_path_pairs', '_rewrite_text', '_rewrite_value', 'capture_file_sha', 'find_sibling_project_path', 'migrate_journal_state', 'refresh_workflow_file_hash', 'rewrite_launcher_handoffs', 'rewrite_project_internal_state', 'same_journal_identity_with_rename', 'same_project_root_check']
