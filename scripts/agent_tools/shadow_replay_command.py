# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Shadow.CommandExecutor import CommandExecutor
from Df.Harness.lib.shadow_command import HARNESS_PY, NO_WINDOW as _NO_WINDOW, _build_command_argv, _copy_native_profile, _harness_repo_head, _iso_cmd_env, _parse_json_stdout, _stage_ag_from_receipt, _stage_folders_json, _stage_shadow_launcher, _verify_shadow_command_post, dfh_persist_shadow_replay_receipt as persist_shadow_replay_receipt, dfh_resolve_shadow_launcher as resolve_shadow_launcher, dfh_run_exec_rename_domain as _run_exec_rename_domain, dfh_run_generic_command as _run_generic_command, dfh_stage_command_shadow_copies as stage_command_shadow_copies
# @used-by :mod:`agent_tools.shadow_replay_command`
def execute_shadow_command(src_project: Path, shadow_project: Path, shadow_launcher: Path | None, shadow_daily: Path | None, shadow_root: Path, *, exec_rename_domain: str | None, command: str | None, checks: dict, verified: list[str], errors: list[str]) -> Path:
	return CommandExecutor(src_project, shadow_project, shadow_launcher, shadow_daily, shadow_root, exec_rename_domain=exec_rename_domain, command=command, checks=checks, verified=verified, errors=errors).run()
__all__ = ['execute_shadow_command', 'persist_shadow_replay_receipt', 'resolve_shadow_launcher', 'stage_command_shadow_copies']
