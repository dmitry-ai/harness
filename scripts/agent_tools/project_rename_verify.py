# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.Rename.PostRenameVerifier import PostRenameVerifier
from pathlib import Path
from . import review, workflow
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
# @used-by :func:`agent_tools.project_rename.rename_project()`
# @used-by :func:`agent_tools.shadow_replay_command._run_generic_command()`
# @used-by :mod:`agent_tools.project_rename_verify`
def capture_pre_rename_snapshot(old_root: Path) -> dict:
	return PostRenameVerifier.capture_pre_snapshot(old_root, review_auth_fn=review.authorize, stage_statuses_fn=workflow.stage_statuses)
# @used-by :func:`agent_tools.shadow_replay_command.resolve_shadow_launcher()`
# @used-by :mod:`agent_tools.project_rename_verify`
def infer_launcher_root(old_root: Path, daily_root: Path | None, launcher_root: Path | None) -> Path | None:
	return PostRenameVerifier.infer_launcher_root(old_root, daily_root, launcher_root)
# @used-by :func:`agent_tools.project_rename.rename_project()`
# @used-by :func:`agent_tools.shadow_replay_command._verify_shadow_command_post()`
# @used-by :mod:`agent_tools.project_rename_verify`
def verify_post_rename(old_root: Path, new_root: Path, pre: dict, *, launcher_root: Path | None=None) -> dict:
	return PostRenameVerifier(old_root, new_root, pre, launcher_root=launcher_root, review_auth_fn=review.authorize, stage_statuses_fn=workflow.stage_statuses).verify()
__all__ = ['capture_pre_rename_snapshot', 'infer_launcher_root', 'verify_post_rename']
