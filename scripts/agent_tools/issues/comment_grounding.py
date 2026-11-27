# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Issue.CloseCommentValidator import CloseCommentValidator
from Df.Harness.Issue.CommentGrounder import CommentGrounder
from Df.Harness.lib.issue import dfh_emit_grounding_failure
import argparse
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by unused
def check_comment_grounding(workspace: Any, repo: str, text: str | None, consumable: list[tuple[Path, bytes]], project_root: str | Path | None=None, *, repo_root: str | Path | None=None) -> list[str]:
	return CommentGrounder(workspace, repo, consumable, project_root=project_root, repo_root=repo_root).check_grounding(text)
# @used-by unused
def check_comment_preflight(service: Any, args: argparse.Namespace, repo: str, body: str, consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> int | None:
	return CommentGrounder(service.workspace, repo, consumable, project_root=project_root, repo_root=getattr(args, 'repo_root', None)).check_preflight(args, body)
# @used-by unused
def emit_grounding_failure(action: str, repo: str, errors: list[str], *, number: int | None=None, comment_id: int | None=None) -> int:
	return dfh_emit_grounding_failure(action, repo, errors, number=number, comment_id=comment_id)
# @used-by unused
def validate_close_comment(service: Any, args: argparse.Namespace, repo: str, number: int, consumable: list[tuple[Path, bytes]], target_locale: str, container_text: str | None, project_root: str | Path | None) -> tuple[str | None, int | None]:
	return CloseCommentValidator(service, args, repo, number, consumable, target_locale, container_text, project_root).validate()
