# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/77
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add isolated git worktree task workflow and worktree-scoped issue gates":
# https://github.com/dmitry-ai/harness/issues/165
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from typing import Any
from .cli_common import add_arg_specs, consume_unchanged_files, dump_json
from .git_gate import is_issue_tracked_code_repo, verify_repo_issue_ready_for_close
from .issues import GitHubIssueService, IssueEvidenceWorkspace, IssueMarkdownLinter
from .issues.linter import REPO_RE
from .issues.service_helpers import dirty_issue_first_files, gh_api_call, pending_similar_peer_slugs
from .runtime import HARNESS_META
_COMMON_TAIL_SPECS = (('--target-locale', {'default': 'en-US', 'help': 'Expected target locale (default: en-US per TEXT-1).'}), ('--project-root', {'help': 'Optional explicit project root directory.'}), ('--repo-root', {'help': 'Optional explicit local Git repository or linked worktree root.'}), ('--consume-input', {'action': 'store_true', 'help': 'Delete input file(s) after verified publication.'}))
_REPO_SPEC = (('--repo', '-R'), {'required': True, 'help': 'Target repository in owner/repo format.'})
_consume_files = consume_unchanged_files
_LINTER = IssueMarkdownLinter()
_WORKSPACE = IssueEvidenceWorkspace()
def _gh_api(endpoint: str, *, method: str='GET', payload: dict[str, Any] | None=None, paginate: bool=False) -> Any:
	return gh_api_call(endpoint, method=method, payload=payload, paginate=paginate, runner=subprocess.run)
def _service() -> GitHubIssueService:
	return GitHubIssueService(api_fn=lambda *a, **kw: _gh_api(*a, **kw), linter=_LINTER, workspace=_WORKSPACE)
def _dirty_issue_first_files(repo: str, *, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, repo_root: str | Path | None=None) -> list[str]:
	return dirty_issue_first_files(_WORKSPACE, repo, project_root=project_root, source_files=source_files, repo_root=repo_root)
def _find_existing_issue_comments(source_files: list[tuple[Path, bytes]], repo: str, issue_num: int, project_root: str | Path | None=None) -> list[int]:
	return _WORKSPACE.find_existing_issue_comments(source_files, repo, issue_num, project_root=project_root)
def _find_local_code_repo(repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, *, repo_root: str | Path | None=None) -> Path | None:
	return _WORKSPACE.find_local_code_repo(repo, project_root=project_root, source_files=source_files, repo_root=repo_root)
def _issue_target_for_path(target_path: Path) -> tuple[Path, Path] | None:
	return _WORKSPACE.issue_target_for_path(target_path)
def _load_saved_issue_container_text(source_files: list[tuple[Path, bytes]], repo: str, issue_num: int | None, project_root: str | Path | None=None) -> str | None:
	return _WORKSPACE.load_saved_issue_container_text(source_files, repo, issue_num, project_root=project_root)
def _meta_dir_for_project_root(proj_root: Path) -> Path | None:
	return _WORKSPACE.meta_dir_for_project_root(proj_root)
def _pending_similar_peer_slugs(code_repo: Path | None, *, repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]]=()) -> list[str]:
	return pending_similar_peer_slugs(_WORKSPACE, code_repo, repo=repo, project_root=project_root, source_files=source_files)
def _persist_issue_evidence(source_files: list[tuple[Path, bytes]], repo: str, fetched: dict[str, Any], *, kind: str='issue', action: str | None=None, project_root: str | Path | None=None, parent_number: int | None=None) -> str | None:
	return _WORKSPACE.persist_issue_evidence(source_files, repo, fetched, kind=kind, action=action, project_root=project_root, parent_number=parent_number)
def _record_issue_in_open_turns(turns_dir: Path, repo: str, record: dict[str, Any], action: str | None) -> None:
	_WORKSPACE.record_issue_in_open_turns(turns_dir, repo, record, action)
def _repo_matches_github_slug(code_repo: Path, repo: str) -> bool:
	return _WORKSPACE.repo_matches_slug(code_repo, repo)
def _resolve_issue_targets(source_files: list[tuple[Path, bytes]], repo: str, project_root: str | Path | None=None) -> list[tuple[Path, Path]]:
	return _WORKSPACE.resolve_issue_targets(source_files, repo, project_root=project_root)
def _saved_issue_parent_number(source_files: list[tuple[Path, bytes]], repo: str, issue_num: int | None, project_root: str | Path | None=None) -> int | None:
	return _WORKSPACE.saved_issue_parent_number(source_files, repo, issue_num, project_root=project_root)
def _validate_repo(repo: str) -> str:
	return _LINTER.validate_repo(repo)
def body_references_parent_issue(body: str, repo: str | None, parent_number: int) -> bool:
	return _LINTER.body_references_parent(body, repo, parent_number)
def build_parser() -> argparse.ArgumentParser:
	r = argparse.ArgumentParser(prog='df_github_issue.py', description='Create, edit, close, comment, and audit GitHub issues with UTF-8 file input and read-back verification.')
	sub = r.add_subparsers(dest='subcommand', required=True)
	sub_defs = (
		('lint', 'Validate issue title/body Markdown offline.', cmd_lint, ((('--repo', '-R'), {'help': 'Optional owner/repo slug for validating parent issue URLs.'}), (('--parent', '-p'), {'help': 'Parent problem issue number or URL for a child subtask issue.'}), ('--title', {'help': 'Issue title string.'}), ('--title-file', {'help': 'UTF-8 file containing issue title.'}), ('--body-file', {'required': True, 'help': 'UTF-8 file containing issue/comment Markdown body.'}), ('--target-locale', {'default': 'en-US', 'help': 'Expected target locale (default: en-US per TEXT-1).'}))),
		('fetch', 'Fetch an existing GitHub issue read-only and persist verified Evidence JSON.', cmd_fetch, (_REPO_SPEC, (('--issue', '-i'), {'type': int, 'required': True, 'help': 'Issue number.'}), ('--project-root', {'help': 'Optional explicit project root directory.'}))),
		('create', 'Create a GitHub issue from a UTF-8 file and verify via API read-back.', cmd_create, (_REPO_SPEC, (('--parent', '-p'), {'help': 'Parent problem issue number or URL for a child subtask issue.'}), (('--title', '-t'), {'help': 'Issue title string.'}), ('--title-file', {'help': 'UTF-8 file containing issue title.'}), (('--body-file', '-F'), {'required': True, 'help': 'UTF-8 file containing issue Markdown body.'}), (('--label', '-l'), {'action': 'append', 'help': 'Issue label(s), repeatable or comma-separated.'}), (('--assignee', '-a'), {'action': 'append', 'help': 'Assignee login(s), repeatable or comma-separated.'}), (('--milestone', '-m'), {'type': int, 'help': 'Milestone number.'}), ('--no-metadata', {'action': 'store_true', 'help': 'Skip automatic prepending of the Harness JSON metadata header.'}), *_COMMON_TAIL_SPECS)),
		('edit', 'Update a GitHub issue from a UTF-8 file and verify via API read-back.', cmd_edit, (_REPO_SPEC, (('--issue', '-i'), {'type': int, 'required': True, 'help': 'Issue number.'}), (('--parent', '-p'), {'help': 'Parent problem issue number or URL for a child subtask issue.'}), (('--title', '-t'), {'help': 'Updated issue title string.'}), ('--title-file', {'help': 'UTF-8 file containing updated issue title.'}), (('--body-file', '-F'), {'help': 'UTF-8 file containing updated issue Markdown body.'}), ('--state', {'choices': ['open', 'closed'], 'help': 'Optional state change.'}), *_COMMON_TAIL_SPECS)),
		('comment', 'Add or edit an issue comment from a UTF-8 file and verify via API read-back.', cmd_comment, (_REPO_SPEC, (('--issue', '-i'), {'type': int, 'help': 'Issue number (for creating a new comment).'}), (('--comment-id', '-c'), {'type': int, 'help': 'Comment ID (for editing an existing comment).'}), (('--body-file', '-F'), {'required': True, 'help': 'UTF-8 file containing comment Markdown body.'}), ('--allow-additional-comment', {'action': 'store_true', 'help': 'Explicitly allow creating an additional comment on an issue that already has a tracked comment.'}), *_COMMON_TAIL_SPECS)),
		('close', 'Close a GitHub issue with optional verified comment from a UTF-8 file.', cmd_close, (_REPO_SPEC, (('--issue', '-i'), {'type': int, 'required': True, 'help': 'Issue number.'}), (('--reason', '-r'), {'choices': ['completed', 'not_planned'], 'default': 'completed', 'help': 'Closure reason.'}), (('--comment-file', '-F'), {'help': 'Optional UTF-8 file containing closing comment Markdown.'}), *_COMMON_TAIL_SPECS)),
		('audit-repo', 'Audit all issues and comments in a repository for syntax/encoding corruption.', cmd_audit_repo, (_REPO_SPEC, ('--state', {'choices': ['all', 'open', 'closed'], 'default': 'all', 'help': 'Issue state filter.'}), ('--include-comments', {'action': 'store_true', 'default': True, 'help': 'Audit issue comments as well.'}), ('--strict-structure', {'action': 'store_true', 'help': 'Also flag historical issues with enumerated titles or bundled subtask bodies.'}), ('--target-locale', {'default': 'en-US', 'help': 'Expected target locale (default: en-US per TEXT-1).'}))),
		('transfer-repo', 'Transfer a GitHub repository to a new owner/organization with read-back verification and Evidence persistence.', cmd_transfer_repo, (_REPO_SPEC, ('--new-owner', {'required': True, 'help': 'Destination GitHub user or organization login.'}), ('--new-name', {'help': 'Optional new repository name after transfer.'}), ('--project-root', {'help': 'Optional explicit project root directory.'}), ('--poll-attempts', {'type': int, 'default': 8, 'help': 'Number of read-back verification attempts.'}), ('--poll-interval', {'type': float, 'default': 1.5, 'help': 'Seconds between read-back verification attempts.'}))),
	)
	for name, help_text, fn, specs in sub_defs:
		p = sub.add_parser(name, help=help_text)
		add_arg_specs(p, specs)
		p.set_defaults(func=fn)
	return r
def cmd_audit_repo(args: argparse.Namespace) -> int:
	return _service().cmd_audit_repo(args)
def cmd_close(args: argparse.Namespace) -> int:
	return _service().cmd_close(args)
def cmd_comment(args: argparse.Namespace) -> int:
	return _service().cmd_comment(args)
def cmd_create(args: argparse.Namespace) -> int:
	return _service().cmd_create(args)
def cmd_edit(args: argparse.Namespace) -> int:
	return _service().cmd_edit(args)
def cmd_fetch(args: argparse.Namespace) -> int:
	return _service().cmd_fetch(args)
def cmd_lint(args: argparse.Namespace) -> int:
	return _service().cmd_lint(args)
def cmd_transfer_repo(args: argparse.Namespace) -> int:
	return _service().cmd_transfer_repo(args)
def extract_parent_issue_number(body: str, repo: str | None=None) -> int | None:
	return _LINTER.extract_parent_number(body, repo)
def extract_unlinked_m_subtask_roots(body: str, *, self_number: int | None=None, parent_number: int | None=None) -> list[str]:
	return _LINTER.extract_unlinked_m_subtasks(body, self_number=self_number, parent_number=parent_number)
find_local_code_repo = _find_local_code_repo
def find_tracked_child_issues(repo: str, parent_number: int, *, project_root: str | Path | None=None, code_repo: Path | None=None) -> list[dict[str, Any]]:
	return _WORKSPACE.find_tracked_child_issues(repo, parent_number, project_root=project_root, code_repo=code_repo)
def has_enumerated_slop_title(title: str) -> bool:
	return _LINTER.has_enumerated_slop_title(title)
def lint_issue_markdown(text: str, *, is_title: bool=False, target_locale: str='en-US', container_text: str | None=None, check_structure_policy: bool=True, parent_number: int | None=None, repo: str | None=None, self_number: int | None=None) -> list[dict[str, Any]]:
	return _LINTER.lint(text, is_title=is_title, target_locale=target_locale, container_text=container_text, check_structure_policy=check_structure_policy, parent_number=parent_number, repo=repo, self_number=self_number)
def main(argv: list[str] | None=None) -> int:
	parser = build_parser()
	try:
		args = parser.parse_args(argv)
		r = args.func(args)
	except Exception as exc:
		dump_json({'ok': False, 'error': str(exc)}, stream=sys.stderr)
		r = 1
	return r
def normalize_newlines(text: str) -> str:
	return _LINTER.normalize_newlines(text)
def parse_parent_issue_arg(raw_parent: str | int | None, repo: str | None=None) -> int | None:
	return _LINTER.parse_parent_arg(raw_parent, repo)
def read_utf8_no_bom_file(path_str: str) -> tuple[Path, bytes, str]:
	return _LINTER.read_utf8_no_bom_file(path_str)
if '__main__' == __name__:
	raise SystemExit(main())
