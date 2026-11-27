# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
from Df.Harness.Git.AgentContextDetector import AGENT_ENV_KEYS, AGENT_PROCESS_NAMES, AgentContextDetector
from Df.Harness.Git.BlobSizeValidator import EXTRACTED_MAX_BYTES, GITHUB_MAX_BLOB_BYTES, BlobSizeValidator, _EXTRACTED_DERIVED_RE
from Df.Harness.Git.CredentialLockCleaner import CredentialLockCleaner
from Df.Harness.Git.RepoGate import RepoGate as GitRepoGate
from Df.Harness.Git.RepoResolver import RepoResolver
from Df.Harness.Git.WorktreeTransaction import WorktreeTransaction as WorktreeCommitTransaction
from .path_registry import tool_path
from .shell_audit import READ_SUBCOMMANDS, ShellCommandInspector, _COMMIT_MESSAGE_ISSUE_URL_RE, _CYGDRIVE_RE, _GITHUB_ISSUE_URL_RE, _ISSUE_LINKED_CODE_SUFFIXES, _VALUE_GLOBAL_OPTS, _iter_shell_git_segments, _parse_commit_subcommand_args, _scan_git_global_opts, _split_shell_segments, _unquote, classify_git_argv, extract_comment_issue_urls, extract_issue_actions_from_outputs, extract_issue_urls, is_code_file, normalize_commit_message, normalize_host_path, parse_issue_url, prohibited_git_write_commands, unflagged_git_read_commands, unpersisted_http_fetch_commands
import os
import subprocess
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
HOOKS_DIR = tool_path('git_hooks_dir')
# @used-by unused
def _check_blob_size_limits(rel_posix: str, size: int, *, kind: str, sha: str='') -> None:
	BlobSizeValidator(GitRepoGate(Path.cwd()), extracted_max=EXTRACTED_MAX_BYTES, github_max=GITHUB_MAX_BLOB_BYTES).validate(single=(rel_posix, size, kind, sha))
# @used-by unused
def _extract_added_diff_urls(root: Path, rel_name: str) -> tuple[set[str], set[str]]:
	return GitRepoGate(root).extract_added_diff_urls(rel_name)
# @used-by unused
def _main_repo_for_worktree(root: Path) -> Path:
	return GitRepoGate(root).main_repo()
# @used-by unused
def _normalize_repo_paths(root: Path, paths: list[str]) -> list[str]:
	return GitRepoGate(root).normalize_paths(paths)
# @used-by :meth:`test_agent_tools.GitTests.test_unrelated_staged_change_is_rejected()`
# @used-by :meth:`test_agent_tools.GitTests.test_unstaged_change_rejected_and_explicit_commit_works()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_git_gate_verify_issue_workflow_enforces_slug_and_saved_evidence_in_github_code_repo()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_git_gate_allows_comment_only_commit_and_blocks_code_change()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_agent_commit_requires_behavioral_test_for_production_code()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_doc_only_agent_commit_allowed_without_tests()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_ratchet_enforced_on_staged_test_edits_and_unlocked_by_ratchet_ok()`
def check_commit(root: Path, paths: list[str], *, message: str | None=None) -> list[str]:
	return GitRepoGate(root, strict=True).check_commit(paths, message=message)
# @used-by :func:`run_git_hook()`
# @used-by :func:`verify_git_write_invocation()`
# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__run_main()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def cleanup_stale_credential_locks(max_age_seconds: float=10.0, *, candidates: list[Path] | tuple[Path, ...] | None=None, check_running: bool=True) -> list[str]:
	return CredentialLockCleaner(max_age_seconds, candidates=candidates, check_running=check_running).clean()
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_safe_commit()`
# @used-by :meth:`test_agent_tools.GitTests.test_unstaged_change_rejected_and_explicit_commit_works()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_git_gate_verify_issue_workflow_enforces_slug_and_saved_evidence_in_github_code_repo()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_agent_commit_requires_behavioral_test_for_production_code()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_ratchet_enforced_on_staged_test_edits_and_unlocked_by_ratchet_ok()`
def commit(root: Path, paths: list[str], message: str, execute: bool=False, *, worktree: bool=False):
	return GitRepoGate(root, strict=True).commit(paths, message, execute=execute, worktree=worktree)
# @used-by unused
def commit_in_worktree(root: Path, paths: list[str], message: str) -> list[str]:
	return WorktreeCommitTransaction(GitRepoGate(root, strict=True)).commit(paths, message)
# @used-by unused
def create_isolated_worktree(root: Path, label: str='isolated') -> Path:
	return WorktreeCommitTransaction(GitRepoGate(root, strict=True), label=label).create()
# @used-by unused
def ensure_repo_hooks(root: Path) -> Path | None:
	return GitRepoGate(root).ensure_hooks(hooks_dir=HOOKS_DIR)
# @used-by unused
def git(root: Path, *args) -> bytes:
	return GitRepoGate(root).git(*args)
# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__run_main()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def is_agent_git_context(env: dict[str, str] | None=None, *, ancestor_names: list[str] | tuple[str, ...] | None=None) -> bool:
	return AgentContextDetector(env, ancestor_names=ancestor_names).detect()
# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_readiness()`
# @used-by :meth:`Df.Harness.Tdd.DiffCoverage.DiffCoverage.__touched_git_repos()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message()`
# @used-by :mod:`agent_tools.github_issue`
def is_issue_tracked_code_repo(root: Path) -> bool:
	return GitRepoGate(root).is_issue_tracked()
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_git_read()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_read_git_and_git_shim_and_unflagged_detector()`
def read_git(root: Path, subcommand: str='status', args: tuple[str, ...] | list[str]=()) -> dict:
	if subcommand not in READ_SUBCOMMANDS:
		raise ValueError(f'Unsupported read-only Git subcommand: {subcommand}')
	return GitRepoGate(root, strict=True).read_git(subcommand, args)
# @used-by unused
def remove_isolated_worktree(root: Path, wt_dir: Path) -> None:
	WorktreeCommitTransaction(GitRepoGate(root, strict=True)).remove(wt_dir)
# @used-by :func:`run_git_hook()`
# @used-by :func:`verify_git_write_invocation()`
# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.is_git_commit_command()`
def resolve_git_repo_from_argv(argv: list[str] | tuple[str, ...], cwd: Path | None=None) -> Path | None:
	return RepoResolver(argv, cwd=cwd).resolve()
# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__run_main()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_git_gate_verify_issue_workflow_enforces_slug_and_saved_evidence_in_github_code_repo()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_pre_commit_emits_non_blocking_mixed_warning_to_stderr()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_git_gate_allows_comment_only_commit_and_blocks_code_change()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_agent_commit_requires_behavioral_test_for_production_code()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_doc_only_agent_commit_allowed_without_tests()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_ratchet_enforced_on_staged_test_edits_and_unlocked_by_ratchet_ok()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_git_gate_enforces_exact_recipe_issue_binding_and_mixed_m2_commit()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def run_git_hook(hook_name: str, argv: list[str] | tuple[str, ...]=(), cwd: Path | None=None, *, stdin_text: str | None=None, agent_context: bool | None=None) -> int:
	cleanup_stale_credential_locks()
	repo_root = resolve_git_repo_from_argv((), cwd=cwd)
	return GitRepoGate(repo_root).run_hook(hook_name, argv, stdin_text=stdin_text, agent_context=agent_context) if None is not repo_root else 0
# @used-by :func:`agent_tools.issues.repo_locator.find_local_code_repo()`
# @used-by :func:`agent_tools.issues.repo_locator.origin_repo_slug()`
# @used-by :func:`agent_tools.issues.repo_locator.repo_matches_slug()`
# @used-by :func:`agent_tools.repo_tags.commit_date_day()`
# @used-by :func:`agent_tools.repo_tags.list_repo_tags()`
# @used-by :func:`agent_tools.repo_tags.remote_has_tag()`
# @used-by :func:`agent_tools.repo_tags.tags_at_commit()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__read_staged_markdown()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.__cat_file_type()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.__load_blob_text()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.__repo_has_tag()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.is_gitignored()`
# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.__has_upstream()`
# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.__read_local_tag_map()`
# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.__read_remote_tags()`
def run_git_read(root: Path, args: list[str] | tuple[str, ...], *, check: bool=True, input_bytes: bytes | None=None):
	return subprocess.run(['git', '--no-optional-locks', '-C', str(normalize_host_path(root)), *args], **({'input': input_bytes} if None is not input_bytes else {'stdin': subprocess.DEVNULL}), capture_output=True, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}, check=check, creationflags=_NO_WINDOW)
# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__prepare()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_git_gate_allows_comment_only_commit_and_blocks_code_change()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_agent_commit_requires_behavioral_test_for_production_code()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_git_gate_enforces_exact_recipe_issue_binding_and_mixed_m2_commit()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def verify_git_write_invocation(argv: list[str] | tuple[str, ...], cwd: Path | None=None, *, agent_context: bool | None=None) -> None:
	cleanup_stale_credential_locks()
	subcommand, _ = classify_git_argv(argv)
	if subcommand in ('commit', 'push', 'filter-branch', 'merge', 'rebase', 'cherry-pick'):
		repo_root = resolve_git_repo_from_argv(argv, cwd=cwd)
		if None is not repo_root:
			GitRepoGate(repo_root).verify_write_invocation(argv, subcommand=subcommand, cwd=cwd, agent_context=agent_context)
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_git_gate_verify_issue_workflow_enforces_slug_and_saved_evidence_in_github_code_repo()`
def verify_issue_workflow(root: Path, relative: list[str], message: str | None=None, *, agent_context: bool=True) -> None:
	GitRepoGate(root).verify_issue_workflow(relative, message=message, agent_context=agent_context)
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def verify_push_blob_sizes(root: Path, stdin_lines: list[str] | None=None) -> None:
	GitRepoGate(root).verify_push_blob_sizes(stdin_lines=stdin_lines, extracted_max=EXTRACTED_MAX_BYTES, github_max=GITHUB_MAX_BLOB_BYTES)
# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_readiness()`
# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_verify_issue_ready_for_close_allows_committed_header_issue_during_sibling_edit()`
# @used-by :meth:`test_git_lifecycle_memoization.GitLifecycleMemoizationTests.test_verify_issue_ready_for_close_memoizes_parent_child_and_catches_defects()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_parent_child_issue_linking_bundled_subtasks_and_parent_closure()`
# @used-by :meth:`test_repo_tag_close_gate.RepoTagCloseGateTests.test_verify_close_rejects_untagged_invalid_and_unpushed_tags_and_accepts_pushed_valid()`
# @used-by :mod:`agent_tools.github_issue`
# @used-by :mod:`agent_tools.issues.service`
def verify_repo_issue_ready_for_close(code_repo: Path, repo: str, number: int, *, project_root: str | Path | None=None, git_cache=None) -> dict:
	return GitRepoGate(code_repo, strict=True).verify_issue_ready_for_close(repo, number, project_root=project_root, git_cache=git_cache)
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def verify_staged_blob_sizes(root: Path, staged_paths: list[str] | None=None) -> None:
	GitRepoGate(root).verify_staged_blob_sizes(staged_paths, extracted_max=EXTRACTED_MAX_BYTES, github_max=GITHUB_MAX_BLOB_BYTES)
