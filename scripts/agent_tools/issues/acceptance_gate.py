# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Issue.AcceptanceGate import AcceptanceGate
from ..git_gate import is_issue_tracked_code_repo, verify_repo_issue_ready_for_close
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :mod:`agent_tools.issues.acceptance_gate`
def check_close_acceptance_receipt(code_repo: Path, repo: str, number: int, commit_sha: str, *, project_root: str | Path | None=None) -> str | None:
	return AcceptanceGate(code_repo, repo, number, project_root=project_root).check_receipt(commit_sha)
# @used-by :mod:`agent_tools.issues.acceptance_gate`
def check_close_readiness(workspace: Any, args: Any, repo: str, number: int, consumable: list[tuple[Path, bytes]], project_root: str | Path | None, *, verify_fn=verify_repo_issue_ready_for_close, is_tracked_fn=is_issue_tracked_code_repo) -> tuple[Path | None, str | None, str]:
	return AcceptanceGate(None, repo, number, project_root=project_root).check_readiness(workspace, args, consumable, verify_fn=verify_fn, is_tracked_fn=is_tracked_fn)
__all__ = ('check_close_acceptance_receipt', 'check_close_readiness')
