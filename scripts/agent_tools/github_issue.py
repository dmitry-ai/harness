# 2026-10-30 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from typing import Any
# 2026-11-14
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
from .cli_common import add_arg_specs, consume_unchanged_files, dump_json
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
from .git_gate import is_issue_tracked_code_repo, verify_repo_issue_ready_for_close
# 2026-11-24
# "Decompose github_issue.py and issue_lifecycle.py into IssueMarkdownLinter, IssueEvidenceWorkspace, GitHubIssueService, and TurnIssueLifecycleAuditor with locked turn updates":
# https://github.com/dmitry-ai/harness/issues/77
from .issues import GitHubIssueService, IssueEvidenceWorkspace, IssueMarkdownLinter
from .issues.linter import REPO_RE
from .issues.service_helpers import dirty_issue_first_files, gh_api_call, pending_similar_peer_slugs
# 2026-10-31
# "Prevent rogue ꘖ directory outside harness meta repo, remove mirror logic, and recognize GIT_OPTIONAL_LOCKS in git gate":
# https://github.com/dmitry-ai/harness/issues/28
from .runtime import HARNESS_META
# 2026-11-14
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
# 2026-11-23
# "Add isolated git worktree task workflow and worktree-scoped issue gates":
# https://github.com/dmitry-ai/harness/issues/165
# 2026-11-24
# "Isolate per-conversation github_issues recording and turn-state filtering":
# https://github.com/dmitry-ai/harness/issues/195
_COMMON_TAIL_SPECS = (('--target-locale', {'default': 'en-US', 'help': 'Expected target locale (default: en-US per TEXT-1).'}), ('--project-root', {'help': 'Optional explicit project root directory.'}), ('--repo-root', {'help': 'Optional explicit local Git repository or linked worktree root.'}), ('--conversation', {'help': 'Optional explicit active conversation UUID for turn-state attribution.'}), ('--consume-input', {'action': 'store_true', 'help': 'Delete input file(s) after verified publication.'}))
# 2026-11-14
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
_REPO_SPEC = (('--repo', '-R'), {'required': True, 'help': 'Target repository in owner/repo format.'})
_consume_files = consume_unchanged_files
# 2026-11-24
# "Decompose github_issue.py and issue_lifecycle.py into IssueMarkdownLinter, IssueEvidenceWorkspace, GitHubIssueService, and TurnIssueLifecycleAuditor with locked turn updates":
# https://github.com/dmitry-ai/harness/issues/77
_LINTER = IssueMarkdownLinter()
_WORKSPACE = IssueEvidenceWorkspace()
# 2026-10-30
# "Implement /df-github-issue skill and df_github_issue.py CLI with UTF-8 file input and mandatory API read-back verification":
# https://github.com/dmitry-ai/harness/issues/20
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-24
# "Decompose github_issue.py and issue_lifecycle.py into IssueMarkdownLinter, IssueEvidenceWorkspace, GitHubIssueService, and TurnIssueLifecycleAuditor with locked turn updates":
# https://github.com/dmitry-ai/harness/issues/77
# @used-by :func:`_service()`
# @used-by :meth:`test_issue_decomposition.IssueDecompositionTests.test_gh_api_paginates_concatenated_json_via_shared_decoder()`
# @used-by :meth:`test_issue_decomposition.IssueDecompositionTests.test_service_cmd_close_routes_through_module_gh_api_and_checks_readback()`
def _gh_api(endpoint: str, *, method: str='GET', payload: dict[str, Any] | None=None, paginate: bool=False) -> Any:
	return gh_api_call(endpoint, method=method, payload=payload, paginate=paginate, runner=subprocess.run)
# 2026-11-24
# "Decompose github_issue.py and issue_lifecycle.py into IssueMarkdownLinter, IssueEvidenceWorkspace, GitHubIssueService, and TurnIssueLifecycleAuditor with locked turn updates":
# https://github.com/dmitry-ai/harness/issues/77
# 2026-11-24
# "Isolate per-conversation github_issues recording and turn-state filtering":
# https://github.com/dmitry-ai/harness/issues/195
# @used-by :func:`cmd_audit_repo()`
# @used-by :func:`cmd_close()`
# @used-by :func:`cmd_comment()`
# @used-by :func:`cmd_create()`
# @used-by :func:`cmd_edit()`
# @used-by :func:`cmd_fetch()`
# @used-by :func:`cmd_lint()`
# @used-by :func:`cmd_transfer_repo()`
def _service(args: argparse.Namespace | None=None) -> GitHubIssueService:
	return GitHubIssueService(api_fn=lambda *a, **kw: _gh_api(*a, **kw), linter=_LINTER, workspace=_WORKSPACE, conversation_id=getattr(args, 'conversation', None))
# 2026-11-23
# "Add fetch subcommand and Issue-First pre-flight guards to df_github_issue.py":
# https://github.com/dmitry-ai/harness/issues/144
# 2026-11-23
# "Add isolated git worktree task workflow and worktree-scoped issue gates":
# https://github.com/dmitry-ai/harness/issues/165
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_worktree_scoped_issue_first_ignores_dirty_main_checkout()`
def _dirty_issue_first_files(repo: str, *, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, repo_root: str | Path | None=None) -> list[str]:
	return dirty_issue_first_files(_WORKSPACE, repo, project_root=project_root, source_files=source_files, repo_root=repo_root)
# 2026-11-02
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
# @used-by unused
def _find_existing_issue_comments(source_files: list[tuple[Path, bytes]], repo: str, issue_num: int, project_root: str | Path | None=None) -> list[int]:
	return _WORKSPACE.find_existing_issue_comments(source_files, repo, issue_num, project_root=project_root)
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-23
# "Add isolated git worktree task workflow and worktree-scoped issue gates":
# https://github.com/dmitry-ai/harness/issues/165
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_post_checkpoint_evicted_citation_gate_and_issue48_defect_filing_gate()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_worktree_scoped_issue_first_ignores_dirty_main_checkout()`
# @used-by :mod:`agent_tools.github_issue`
def _find_local_code_repo(repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, *, repo_root: str | Path | None=None) -> Path | None:
	return _WORKSPACE.find_local_code_repo(repo, project_root=project_root, source_files=source_files, repo_root=repo_root)
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# @used-by unused
def _issue_target_for_path(target_path: Path) -> tuple[Path, Path] | None:
	return _WORKSPACE.issue_target_for_path(target_path)
# 2026-11-02
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
# @used-by unused
def _load_saved_issue_container_text(source_files: list[tuple[Path, bytes]], repo: str, issue_num: int | None, project_root: str | Path | None=None) -> str | None:
	return _WORKSPACE.load_saved_issue_container_text(source_files, repo, issue_num, project_root=project_root)
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# @used-by unused
def _meta_dir_for_project_root(proj_root: Path) -> Path | None:
	return _WORKSPACE.meta_dir_for_project_root(proj_root)
# 2026-11-22
# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
# https://github.com/dmitry-ai/harness/issues/123
# @used-by unused
def _pending_similar_peer_slugs(code_repo: Path | None, *, repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]]=()) -> list[str]:
	return pending_similar_peer_slugs(_WORKSPACE, code_repo, repo=repo, project_root=project_root, source_files=source_files)
# 2026-10-31
# "Extract universal harness.py CLI, add CDP browser fallback on port 9222, and harden source/quote/anchor verification in answer-prepare":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-11-24
# "Isolate per-conversation github_issues recording and turn-state filtering":
# https://github.com/dmitry-ai/harness/issues/195
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
def _persist_issue_evidence(source_files: list[tuple[Path, bytes]], repo: str, fetched: dict[str, Any], *, kind: str='issue', action: str | None=None, project_root: str | Path | None=None, parent_number: int | None=None, conversation_id: str | None=None) -> str | None:
	return _WORKSPACE.persist_issue_evidence(source_files, repo, fetched, kind=kind, action=action, project_root=project_root, parent_number=parent_number, conversation_id=conversation_id)
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-24
# "Isolate per-conversation github_issues recording and turn-state filtering":
# https://github.com/dmitry-ai/harness/issues/195
# @used-by unused
def _record_issue_in_open_turns(turns_dir: Path, repo: str, record: dict[str, Any], action: str | None, *, conversation_id: str | None=None) -> None:
	_WORKSPACE.record_issue_in_open_turns(turns_dir, repo, record, action, conversation_id=conversation_id)
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# @used-by unused
def _repo_matches_github_slug(code_repo: Path, repo: str) -> bool:
	return _WORKSPACE.repo_matches_slug(code_repo, repo)
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# @used-by unused
def _resolve_issue_targets(source_files: list[tuple[Path, bytes]], repo: str, project_root: str | Path | None=None) -> list[tuple[Path, Path]]:
	return _WORKSPACE.resolve_issue_targets(source_files, repo, project_root=project_root)
# 2026-11-18
# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/84
# @used-by unused
def _saved_issue_parent_number(source_files: list[tuple[Path, bytes]], repo: str, issue_num: int | None, project_root: str | Path | None=None) -> int | None:
	return _WORKSPACE.saved_issue_parent_number(source_files, repo, issue_num, project_root=project_root)
# 2026-10-30
# "Implement /df-github-issue skill and df_github_issue.py CLI with UTF-8 file input and mandatory API read-back verification":
# https://github.com/dmitry-ai/harness/issues/20
# @used-by unused
def _validate_repo(repo: str) -> str:
	return _LINTER.validate_repo(repo)
# 2026-11-18
# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/84
# @used-by unused
def body_references_parent_issue(body: str, repo: str | None, parent_number: int) -> bool:
	return _LINTER.body_references_parent(body, repo, parent_number)
# 2026-10-30
# "Implement /df-github-issue skill and df_github_issue.py CLI with UTF-8 file input and mandatory API read-back verification":
# https://github.com/dmitry-ai/harness/issues/20
# 2026-11-14
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
# @used-by :func:`main()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_declarative_arg_specs_and_routers_parse_expected_flags()`
# @used-by :meth:`test_issue_conversation_isolation.IssueConversationIsolationTests.test_cli_parser_accepts_optional_conversation_flag()`
def build_parser() -> argparse.ArgumentParser:
	r = argparse.ArgumentParser(prog='df_github_issue.py', description='Create, edit, close, comment, and audit GitHub issues with UTF-8 file input and read-back verification.')
	sub = r.add_subparsers(dest='subcommand', required=True)
	sub_defs = (
		# 2026-11-18
		# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
		# https://github.com/dmitry-ai/harness/issues/84
		('lint', 'Validate issue title/body Markdown offline.', cmd_lint, ((('--repo', '-R'), {'help': 'Optional owner/repo slug for validating parent issue URLs.'}), (('--parent', '-p'), {'help': 'Parent problem issue number or URL for a child subtask issue.'}), ('--title', {'help': 'Issue title string.'}), ('--title-file', {'help': 'UTF-8 file containing issue title.'}), ('--body-file', {'required': True, 'help': 'UTF-8 file containing issue/comment Markdown body.'}), ('--target-locale', {'default': 'en-US', 'help': 'Expected target locale (default: en-US per TEXT-1).'}))),
		# 2026-11-23
		# "Add fetch subcommand and Issue-First pre-flight guards to df_github_issue.py":
		# https://github.com/dmitry-ai/harness/issues/144
		# 2026-11-24
		# "Isolate per-conversation github_issues recording and turn-state filtering":
		# https://github.com/dmitry-ai/harness/issues/195
		('fetch', 'Fetch an existing GitHub issue read-only and persist verified Evidence JSON.', cmd_fetch, (_REPO_SPEC, (('--issue', '-i'), {'type': int, 'required': True, 'help': 'Issue number.'}), ('--project-root', {'help': 'Optional explicit project root directory.'}), ('--conversation', {'help': 'Optional explicit active conversation UUID for turn-state attribution.'}))),
		# 2026-11-23
		# "Prepend structured JSON metadata header to new GitHub issues in df_github_issue.py":
		# https://github.com/dmitry-ai/harness/issues/150
		('create', 'Create a GitHub issue from a UTF-8 file and verify via API read-back.', cmd_create, (_REPO_SPEC, (('--parent', '-p'), {'help': 'Parent problem issue number or URL for a child subtask issue.'}), (('--title', '-t'), {'help': 'Issue title string.'}), ('--title-file', {'help': 'UTF-8 file containing issue title.'}), (('--body-file', '-F'), {'required': True, 'help': 'UTF-8 file containing issue Markdown body.'}), (('--label', '-l'), {'action': 'append', 'help': 'Issue label(s), repeatable or comma-separated.'}), (('--assignee', '-a'), {'action': 'append', 'help': 'Assignee login(s), repeatable or comma-separated.'}), (('--milestone', '-m'), {'type': int, 'help': 'Milestone number.'}), ('--no-metadata', {'action': 'store_true', 'help': 'Skip automatic prepending of the Harness JSON metadata header.'}), *_COMMON_TAIL_SPECS)),
		('edit', 'Update a GitHub issue from a UTF-8 file and verify via API read-back.', cmd_edit, (_REPO_SPEC, (('--issue', '-i'), {'type': int, 'required': True, 'help': 'Issue number.'}), (('--parent', '-p'), {'help': 'Parent problem issue number or URL for a child subtask issue.'}), (('--title', '-t'), {'help': 'Updated issue title string.'}), ('--title-file', {'help': 'UTF-8 file containing updated issue title.'}), (('--body-file', '-F'), {'help': 'UTF-8 file containing updated issue Markdown body.'}), ('--state', {'choices': ['open', 'closed'], 'help': 'Optional state change.'}), *_COMMON_TAIL_SPECS)),
		('comment', 'Add or edit an issue comment from a UTF-8 file and verify via API read-back.', cmd_comment, (_REPO_SPEC, (('--issue', '-i'), {'type': int, 'help': 'Issue number (for creating a new comment).'}), (('--comment-id', '-c'), {'type': int, 'help': 'Comment ID (for editing an existing comment).'}), (('--body-file', '-F'), {'required': True, 'help': 'UTF-8 file containing comment Markdown body.'}), ('--allow-additional-comment', {'action': 'store_true', 'help': 'Explicitly allow creating an additional comment on an issue that already has a tracked comment.'}), *_COMMON_TAIL_SPECS)),
		('close', 'Close a GitHub issue with optional verified comment from a UTF-8 file.', cmd_close, (_REPO_SPEC, (('--issue', '-i'), {'type': int, 'required': True, 'help': 'Issue number.'}), (('--reason', '-r'), {'choices': ['completed', 'not_planned'], 'default': 'completed', 'help': 'Closure reason.'}), (('--comment-file', '-F'), {'help': 'Optional UTF-8 file containing closing comment Markdown.'}), *_COMMON_TAIL_SPECS)),
		# 2026-11-18
		# "Reject enumerated multi-item issue titles in df_github_issue.py and active turn lifecycle checks":
		# https://github.com/dmitry-ai/harness/issues/83
		('audit-repo', 'Audit all issues and comments in a repository for syntax/encoding corruption.', cmd_audit_repo, (_REPO_SPEC, ('--state', {'choices': ['all', 'open', 'closed'], 'default': 'all', 'help': 'Issue state filter.'}), ('--include-comments', {'action': 'store_true', 'default': True, 'help': 'Audit issue comments as well.'}), ('--strict-structure', {'action': 'store_true', 'help': 'Also flag historical issues with enumerated titles or bundled subtask bodies.'}), ('--target-locale', {'default': 'en-US', 'help': 'Expected target locale (default: en-US per TEXT-1).'}))),
		# 2026-11-22
		# "Add audited transfer-repo subcommand to df_github_issue.py":
		# https://github.com/dmitry-ai/harness/issues/126
		('transfer-repo', 'Transfer a GitHub repository to a new owner/organization with read-back verification and Evidence persistence.', cmd_transfer_repo, (_REPO_SPEC, ('--new-owner', {'required': True, 'help': 'Destination GitHub user or organization login.'}), ('--new-name', {'help': 'Optional new repository name after transfer.'}), ('--project-root', {'help': 'Optional explicit project root directory.'}), ('--poll-attempts', {'type': int, 'default': 8, 'help': 'Number of read-back verification attempts.'}), ('--poll-interval', {'type': float, 'default': 1.5, 'help': 'Seconds between read-back verification attempts.'}))),
	)
	for name, help_text, fn, specs in sub_defs:
		p = sub.add_parser(name, help=help_text)
		add_arg_specs(p, specs)
		p.set_defaults(func=fn)
	return r
# 2026-11-24
# "Decompose github_issue.py and issue_lifecycle.py into IssueMarkdownLinter, IssueEvidenceWorkspace, GitHubIssueService, and TurnIssueLifecycleAuditor with locked turn updates":
# https://github.com/dmitry-ai/harness/issues/77
# 2026-11-24
# "Isolate per-conversation github_issues recording and turn-state filtering":
# https://github.com/dmitry-ai/harness/issues/195
# @used-by :func:`build_parser()`
def cmd_audit_repo(args: argparse.Namespace) -> int:
	return _service(args).cmd_audit_repo(args)
# @used-by :func:`build_parser()`
def cmd_close(args: argparse.Namespace) -> int:
	return _service(args).cmd_close(args)
# @used-by :func:`build_parser()`
def cmd_comment(args: argparse.Namespace) -> int:
	return _service(args).cmd_comment(args)
# @used-by :func:`build_parser()`
def cmd_create(args: argparse.Namespace) -> int:
	return _service(args).cmd_create(args)
# @used-by :func:`build_parser()`
def cmd_edit(args: argparse.Namespace) -> int:
	return _service(args).cmd_edit(args)
# 2026-11-23
# "Add fetch subcommand and Issue-First pre-flight guards to df_github_issue.py":
# https://github.com/dmitry-ai/harness/issues/144
# @used-by :func:`build_parser()`
def cmd_fetch(args: argparse.Namespace) -> int:
	return _service(args).cmd_fetch(args)
# @used-by :func:`build_parser()`
def cmd_lint(args: argparse.Namespace) -> int:
	return _service(args).cmd_lint(args)
# 2026-11-22
# "Add audited transfer-repo subcommand to df_github_issue.py":
# https://github.com/dmitry-ai/harness/issues/126
# @used-by :func:`build_parser()`
def cmd_transfer_repo(args: argparse.Namespace) -> int:
	return _service(args).cmd_transfer_repo(args)
# 2026-11-18
# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/84
# @used-by :func:`agent_tools.issue_first_gate._load_evidence_issue_info()`
# @used-by :func:`agent_tools.issue_first_inherit._evidence_parent_number()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_workflow()`
def extract_parent_issue_number(body: str, repo: str | None=None) -> int | None:
	return _LINTER.extract_parent_number(body, repo)
# 2026-11-18
# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/84
# 2026-11-18
# "Fix post-audit edge cases in parent-child issue validation and turn-scoped lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/87
# @used-by unused
def extract_unlinked_m_subtask_roots(body: str, *, self_number: int | None=None, parent_number: int | None=None) -> list[str]:
	return _LINTER.extract_unlinked_m_subtasks(body, self_number=self_number, parent_number=parent_number)
# 2026-11-13
# "Extract issue_lifecycle.py from completion.py, fix open backlog-issue lifecycle gating, and consolidate Git/issue helpers in git_gate.py":
# https://github.com/dmitry-ai/harness/issues/53
find_local_code_repo = _find_local_code_repo
# 2026-11-18
# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/84
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_ready_for_close()`
def find_tracked_child_issues(repo: str, parent_number: int, *, project_root: str | Path | None=None, code_repo: Path | None=None) -> list[dict[str, Any]]:
	return _WORKSPACE.find_tracked_child_issues(repo, parent_number, project_root=project_root, code_repo=code_repo)
# 2026-11-18
# "Reject enumerated multi-item issue titles in df_github_issue.py and active turn lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/83
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_enumerated_slop_titles_rejected_and_clean_titles_accepted()`
def has_enumerated_slop_title(title: str) -> bool:
	return _LINTER.has_enumerated_slop_title(title)
# 2026-10-30
# "Implement /df-github-issue skill and df_github_issue.py CLI with UTF-8 file input and mandatory API read-back verification":
# https://github.com/dmitry-ai/harness/issues/20
# 2026-11-02
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
# 2026-11-18
# "Fix post-audit edge cases in parent-child issue validation and turn-scoped lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/87
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_clean_markdown_passes()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_detects_all_seven_powershell_corruption_classes()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_enumerated_slop_titles_rejected_and_clean_titles_accepted()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_parent_child_issue_linking_bundled_subtasks_and_parent_closure()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_universal_locale_gate_blocks_cyrillic_and_greek_prose_while_allowing_fenced_logs()`
# @used-by :meth:`test_issue_decomposition.IssueDecompositionTests.test_issue_markdown_linter_and_service_classes_exist()`
def lint_issue_markdown(text: str, *, is_title: bool=False, target_locale: str='en-US', container_text: str | None=None, check_structure_policy: bool=True, parent_number: int | None=None, repo: str | None=None, self_number: int | None=None) -> list[dict[str, Any]]:
	return _LINTER.lint(text, is_title=is_title, target_locale=target_locale, container_text=container_text, check_structure_policy=check_structure_policy, parent_number=parent_number, repo=repo, self_number=self_number)
# 2026-10-30
# "Implement /df-github-issue skill and df_github_issue.py CLI with UTF-8 file input and mandatory API read-back verification":
# https://github.com/dmitry-ai/harness/issues/20
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`test_issue_close_acceptance._run_close_cli()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_close_requires_committed_issue_url_in_local_code_repo()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_and_consume_input_with_readback_verification()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_prepends_tab_indented_json_metadata_header_and_supports_opt_out()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_enumerated_slop_titles_rejected_and_clean_titles_accepted()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_idempotent_comment_gate_blocks_duplicate_comment_without_comment_id()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_parent_child_issue_linking_bundled_subtasks_and_parent_closure()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_transfer_repo_verifies_readback_and_persists_evidence()`
# @used-by :meth:`test_issue_first_github_cli.IssueFirstGitHubCliTests.test_create_parent_issue_blocked_on_dirty_tree_while_open_parent_child_create_allowed()`
# @used-by :meth:`test_issue_first_github_cli.IssueFirstGitHubCliTests.test_fetch_persists_open_issue_and_parent_evidence_and_rejects_pull_requests()`
# @used-by :mod:`agent_tools.github_issue`
# @used-by :mod:`df_github_issue`
def main(argv: list[str] | None=None) -> int:
	parser = build_parser()
	try:
		args = parser.parse_args(argv)
		r = args.func(args)
	except Exception as exc:
		# 2026-11-14
		# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
		# https://github.com/dmitry-ai/harness/issues/69
		dump_json({'ok': False, 'error': str(exc)}, stream=sys.stderr)
		r = 1
	return r
# 2026-10-30
# "Implement /df-github-issue skill and df_github_issue.py CLI with UTF-8 file input and mandatory API read-back verification":
# https://github.com/dmitry-ai/harness/issues/20
# @used-by unused
def normalize_newlines(text: str) -> str:
	return _LINTER.normalize_newlines(text)
# 2026-11-18
# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/84
# @used-by unused
def parse_parent_issue_arg(raw_parent: str | int | None, repo: str | None=None) -> int | None:
	return _LINTER.parse_parent_arg(raw_parent, repo)
# 2026-10-30
# "Implement /df-github-issue skill and df_github_issue.py CLI with UTF-8 file input and mandatory API read-back verification":
# https://github.com/dmitry-ai/harness/issues/20
# @used-by unused
def read_utf8_no_bom_file(path_str: str) -> tuple[Path, bytes, str]:
	return _LINTER.read_utf8_no_bom_file(path_str)
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
if '__main__' == __name__:
	raise SystemExit(main())
