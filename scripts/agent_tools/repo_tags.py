# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo
from Df.Harness.Git.BlobUrlBuilder import BlobUrlBuilder
from Df.Harness.Git.CommitTagger import CommitTagger
from Df.Harness.Git.DateTagAllocator import DATE_TAG_RE, SEMVER_TAG_RE, DateTagAllocator
from Df.Harness.Git.RetroTagger import RetroTagger
from Df.Harness.Git.TagSelector import TagSelector
from Df.Harness.lib.worktree import dfh_has_origin_remote
from .git_gate import _NO_WINDOW, run_git_read
import subprocess
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :func:`run_repo_tag_cli()`
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_github_blob_url_builder_validates_file_and_lines()`
def build_github_blob_url(file_path: Path | str, *, commit: str='HEAD', lines: str | None=None, anchor: str | None=None, push: bool=False, date_override: str | None=None) -> str:
	return BlobUrlBuilder(file_path, commit=commit, lines=lines, anchor=anchor, push=push, date_override=date_override).build()
# @used-by unused
def commit_date_day(repo: Path, commit: str='HEAD') -> str:
	proc = run_git_read(repo, ['show', '-s', '--format=%cI', commit], check=False)
	if 0 != proc.returncode or (not proc.stdout.strip()):
		raise ValueError(f'Unable to read committer date for {commit} in {repo}')
	tz_name = 'Europe/Istanbul'
	try:
		from .runtime import settings
		tz_name = str((settings() or {}).get('timezone') or '').strip() or tz_name
	except Exception:
		pass
	return datetime.fromisoformat(proc.stdout.decode('utf-8', errors='replace').strip().replace('Z', '+00:00')).astimezone(ZoneInfo(tz_name)).strftime('%Y-%m-%d')
# @used-by :func:`run_repo_tag_cli()`
# @used-by :func:`test_clarification_stop_consent._build_fixture()`
# @used-by :func:`test_dirty_diff_issue_scope._init_repo()`
# @used-by :func:`test_git_lifecycle_memoization._init_multi_issue_repo()`
# @used-by :func:`test_incomplete_scope_regression_matrix._build_step_281_fixture()`
# @used-by :func:`test_issue_close_acceptance._commit_and_tag()`
# @used-by :func:`test_issue_first_completion._init_github_project()`
# @used-by :func:`test_issue_preflight_and_batch._commit_and_tag()`
# @used-by :func:`test_open_child_deferral_gate._init_repo()`
# @used-by :func:`test_repo_link_gate._init_tagged_repo()`
# @used-by :func:`test_tdd_completion._build_template_project()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_close_requires_committed_issue_url_in_local_code_repo()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_parent_child_issue_linking_bundled_subtasks_and_parent_closure()`
# @used-by :meth:`test_repo_tag_close_gate.RepoTagCloseGateTests.test_verify_closing_commit_tag_reads_origin_from_config_without_git_config_spawn()`
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_ensure_commit_tag_creates_reuses_and_pushes_lightweight_tag()`
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_ensure_commit_tag_uses_bounded_git_subprocesses()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_similar_projects_parity_gate_stop_hook_pre_invocation_and_exemption()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_code_and_issue_lifecycle_gate_blocks_uncommitted_unpushed_and_open_issue_in_prepare()`
# @used-by :meth:`test_turn_completion.IssueLifecycleTests.test_mixed_multi_commit_closed_issues_and_open_backlog_issue()`
# @used-by :meth:`test_turn_completion.IssueLifecycleTests.test_multi_subtask_parent_and_child_commits_enforced_in_lifecycle()`
# @used-by :meth:`test_turn_completion.IssueLifecycleTests.test_post_audit_turn_isolation_diagnostic_parent_and_unclosed_parent_checks()`
def ensure_commit_tag(repo: Path | str, *, commit: str='HEAD', date_override: str | None=None, push: bool=False, remote: str='origin') -> dict:
	return CommitTagger(repo, commit=commit, date_override=date_override, push=push, remote=remote).ensure()
# @used-by unused
def has_origin_remote(repo: Path, *, remote: str='origin') -> bool:
	return dfh_has_origin_remote(repo, remote=remote)
# @used-by :func:`is_valid_repo_tag()`
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_date_tag_and_repo_tag_validation()`
def is_valid_date_tag(tag: str) -> bool:
	m = DATE_TAG_RE.fullmatch((tag or '').strip())
	if None is m:
		r = False
	else:
		try:
			date.fromisoformat(m.group('date'))
			r = True
		except ValueError:
			r = False
	return r
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.resolve_blob()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.validate_github_url()`
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_date_tag_and_repo_tag_validation()`
def is_valid_repo_tag(tag: str) -> bool:
	clean = (tag or '').strip()
	return is_valid_date_tag(clean) or bool(SEMVER_TAG_RE.fullmatch(clean))
# @used-by unused
def list_repo_tags(repo: Path) -> list[str]:
	proc = run_git_read(repo, ['tag', '-l'], check=False)
	return [ln.strip() for ln in proc.stdout.decode('utf-8', errors='replace').splitlines() if ln.strip()] if 0 == proc.returncode else []
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_next_date_tag_daily_counter_and_reset()`
def next_date_tag(existing_tags: Iterable[str], day: str) -> str:
	return DateTagAllocator(existing_tags, day).allocate()
# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.verify()`
def pick_preferred_tag(tags: Iterable[str]) -> str | None:
	return TagSelector(tags).pick()
# @used-by unused
def plan_retro_tags(repo: Path, *, include_task_groups: bool=False, extra_commits: list[str] | tuple[str, ...]=()) -> list[dict]:
	return RetroTagger(repo, apply=False, include_task_groups=include_task_groups, extra_commits=extra_commits).run()['planned']
# @used-by unused
def push_tag(repo: Path, tag: str, *, remote: str='origin') -> bool:
	proc = subprocess.run(['git', '-C', str(Path(repo).resolve()), 'push', remote, f'refs/tags/{tag}'], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False, timeout=60, creationflags=_NO_WINDOW)
	if 0 != proc.returncode:
		raise RuntimeError(f'git push {remote} refs/tags/{tag} failed: {proc.stderr.strip() or proc.stdout.strip()}')
	return True
# @used-by unused
def remote_has_tag(repo: Path, tag: str, *, remote: str='origin') -> bool:
	proc = run_git_read(repo, ['ls-remote', '--tags', remote, f'refs/tags/{tag}'], check=False)
	return 0 == proc.returncode and bool(proc.stdout.strip())
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_repo_tag_retro()`
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_retro_tag_repo_tags_closing_commits_chronologically()`
def retro_tag_repo(repo: Path | str, *, apply: bool=False, push: bool=False, include_task_groups: bool=False, extra_commits: list[str] | tuple[str, ...]=(), remote: str='origin') -> dict:
	return RetroTagger(repo, apply=apply, push=push, include_task_groups=include_task_groups, extra_commits=extra_commits, remote=remote).run()
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_repo_tag()`
def run_repo_tag_cli(args) -> dict:
	repo_p = Path(args.repo).resolve()
	res = ensure_commit_tag(repo_p, commit=args.commit, date_override=args.date, push=bool(args.push))
	if args.file:
		file_p = Path(args.file)
		full_p = file_p if file_p.is_absolute() else (repo_p / file_p)
		res['github_url'] = build_github_blob_url(full_p, commit=args.commit, lines=args.lines, anchor=args.anchor, push=False, date_override=args.date)
	return res
# @used-by unused
def tags_at_commit(repo: Path, commit: str='HEAD') -> list[str]:
	proc = run_git_read(repo, ['tag', '--points-at', commit], check=False)
	return [ln.strip() for ln in proc.stdout.decode('utf-8', errors='replace').splitlines() if ln.strip()] if 0 == proc.returncode else []
# @used-by unused
def validate_tree_path_and_fragment(repo: Path, ref: str, rel_path: str, fragment: str='') -> tuple[str, int]:
	b = BlobUrlBuilder(Path(repo) / rel_path, commit=ref, lines=fragment)
	return b._BlobUrlBuilder__validate_tree_path(Path(repo).resolve(), ref, rel_path)
