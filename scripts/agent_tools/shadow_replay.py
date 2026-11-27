# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Shadow.ReplayRunner import NOT_RUN_STAGES, ReplayRunner
from .shadow_replay_clone import _legacy_shadow_patch_ctx
# @used-by unused
def run_shadow_replay(project: str | Path, conversation_id: str | None=None, *, launcher: str | Path | None=None, workspace: str | Path | None=None, platform: str='antigravity', backend: str | Path | None=None, response_file: str | Path | None=None, keep: bool=False, exec_rename_domain: str | None=None, command: str | None=None) -> dict:
	return ReplayRunner(project, conversation_id, launcher=launcher, workspace=workspace, platform=platform, backend=backend, response_file=response_file, keep=keep, exec_rename_domain=exec_rename_domain, command=command, legacy_ctx=_legacy_shadow_patch_ctx).run()
