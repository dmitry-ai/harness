# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-flight comment grounding and add batch GitHub issue commands":
# https://github.com/dmitry-ai/harness/issues/353
from __future__ import annotations
from pathlib import Path
from typing import Any
from ..cli_common import dump_json
from ..source_grounding import local_source_grounding_issues, read_only_grounding
import argparse
# @used-by :func:`check_comment_grounding()`
def _resolve_grounding_root(workspace, repo: str, project_root: str | Path | None, consumable: list[tuple[Path, bytes]], repo_root: str | Path | None) -> Path | None:
	if None is not project_root and str(project_root).strip():
		r: Path | None = Path(project_root).resolve()
	else:
		code_repo = workspace.find_local_code_repo(repo, project_root=project_root, source_files=consumable, repo_root=repo_root)
		if None is not code_repo:
			try:
				from ..path_registry import project_paths
				r = project_paths(code_repo).root
			except (OSError, ValueError):
				r = code_repo
		else:
			try:
				from ..path_registry import resolve_project_root
				r = resolve_project_root(Path.cwd().resolve())
			except (OSError, ValueError):
				r = Path.cwd().resolve()
	return r
# @used-by :func:`check_comment_preflight()`
# @used-by :func:`validate_close_comment()`
def check_comment_grounding(workspace, repo: str, text: str | None, consumable: list[tuple[Path, bytes]], project_root: str | Path | None=None, *, repo_root: str | Path | None=None) -> list[str]:
	r: list[str] = []
	if isinstance(text, str) and text.strip():
		ground_root = _resolve_grounding_root(workspace, repo, project_root, consumable, repo_root)
		if None is not ground_root:
			with read_only_grounding():
				r = local_source_grounding_issues(ground_root, text)
	return r
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService.cmd_comment()`
def check_comment_preflight(service, args: argparse.Namespace, repo: str, body: str, consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> int | None:
	existing_cids = service.workspace.find_existing_issue_comments(consumable, repo, args.issue, project_root=project_root) if None is args.comment_id and None is not args.issue and (not getattr(args, 'allow_additional_comment', False)) else []
	if existing_cids:
		dump_json({'ok': False, 'action': 'comment', 'stage': 'idempotent_comment_gate', 'repo': repo, 'issue': args.issue, 'existing_comment_ids': existing_cids, 'error': f'EXEC-5 / SCOPE-2: Issue #{args.issue} already has tracked comment(s) {existing_cids} in KB/Evidence/GitHub; use --comment-id {existing_cids[-1]} to update the existing comment in place instead of posting a duplicate comment (or pass --allow-additional-comment if explicitly instructed)'})
		r: int | None = 2
	else:
		g_errors = check_comment_grounding(service.workspace, repo, body, consumable, project_root, repo_root=getattr(args, 'repo_root', None))
		r = emit_grounding_failure('comment', repo, g_errors, number=getattr(args, 'issue', None), comment_id=getattr(args, 'comment_id', None)) if g_errors else None
	return r
# @used-by :func:`check_comment_preflight()`
# @used-by :func:`validate_close_comment()`
def emit_grounding_failure(action: str, repo: str, errors: list[str], *, number: int | None=None, comment_id: int | None=None) -> int:
	out: dict[str, Any] = {'ok': False, 'action': action, 'stage': 'pre_flight_grounding', 'repo': repo, 'grounding_errors': errors}
	if None is not number:
		out['number'] = number
	if None is not comment_id:
		out['comment_id'] = comment_id
	dump_json(out)
	return 2
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._verify_close_prereqs()`
def validate_close_comment(service, args: argparse.Namespace, repo: str, number: int, consumable: list[tuple[Path, bytes]], target_locale: str, container_text: str | None, project_root: str | Path | None) -> tuple[str | None, int | None]:
	comment_body: str | None = None
	err_rc: int | None = None
	if args.comment_file:
		c_path, c_raw, comment_body = service.linter.read_utf8_no_bom_file(args.comment_file)
		consumable.append((c_path, c_raw))
		c_errors = service.linter.lint(comment_body, is_title=False, target_locale=target_locale, container_text=container_text, check_structure_policy=False)
		if c_errors:
			dump_json({'ok': False, 'action': 'close', 'stage': 'pre_flight_comment_lint', 'repo': repo, 'number': number, 'comment_errors': c_errors})
			err_rc = 2
		else:
			g_errors = check_comment_grounding(service.workspace, repo, comment_body, consumable, project_root, repo_root=getattr(args, 'repo_root', None))
			if g_errors:
				err_rc = emit_grounding_failure('close', repo, g_errors, number=number)
	return (comment_body, err_rc)
