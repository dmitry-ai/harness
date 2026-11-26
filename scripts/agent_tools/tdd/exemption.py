# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from ..shell_audit import _GITHUB_ISSUE_URL_RE, is_code_file, parse_issue_url
from .comment_diff import is_comment_only_diff, is_git_file_comment_only
# 2026-11-25
# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
# https://github.com/dmitry-ai/harness/issues/239
from .mechanical import is_git_file_mechanical_exempt, is_mechanical_diff_exempt
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
# 2026-11-25
# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
# https://github.com/dmitry-ai/harness/issues/239
# @used-by :func:`agent_tools.tdd.enforcement._eval_pre_code_write()`
# @used-by :func:`agent_tools.tdd.enforcement._eval_pre_test_write()`
# @used-by :func:`agent_tools.tdd.enforcement._verify_staged_test_file()`
# @used-by :func:`agent_tools.tdd.enforcement.verify_staged_tdd_diff()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_diff_exempt(path: str | Path, old_text: str | None, new_text: str | None, *, repo_root: Path | None=None, message: str | None=None, project_root: Path | None=None) -> bool:
	return is_comment_only_diff(path, old_text, new_text) or is_mechanical_diff_exempt(old_text, new_text, repo_root=repo_root, message=message, project_root=project_root)
# 2026-11-25
# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
# https://github.com/dmitry-ai/harness/issues/239
# @used-by :func:`is_write_event_exempt()`
# @used-by :func:`verify_staged_issue_urls()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_touched_code_file()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_git_path_exempt(repo_root: Path, rel_posix: str, *, disk_text: str | None=None, use_index: bool=False, message: str | None=None, project_root: Path | None=None) -> bool:
	return is_git_file_comment_only(repo_root, rel_posix, disk_text=disk_text, use_index=use_index) or is_git_file_mechanical_exempt(repo_root, rel_posix, disk_text=disk_text, use_index=use_index, message=message, project_root=project_root)
# 2026-11-26 "Resolve deleted worktree paths in TDD comment-only exemption": https://github.com/dmitry-ai/harness/issues/278
# @used-by :func:`agent_tools.tdd.evaluator._is_exempt_cached()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_memoizes_exemption_and_allows_exempt_only_edits()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_write_event_exempt(raw_path: str | Path, scope_str: str, *, project_root: Path | None=None) -> bool:
	r = False
	if raw_path and scope_str:
		fpath, scope = (Path(str(raw_path)), Path(scope_str))
		rel = _resolve_scope_rel_path(fpath, scope)
		if rel and (scope / '.git').exists():
			r = is_git_path_exempt(scope, rel, project_root=project_root)
	return r
# 2026-11-26 "Scope issue-URL lifecycle gates to target repository": https://github.com/dmitry-ai/harness/issues/321
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_touched_code_file()`
def filter_repo_turn_issue_urls(comment_urls: set[str], turn_issues: dict, repo_slug: str | None) -> list[str]:
	return sorted((u for u in comment_urls if u in turn_issues and _is_same_repo_url(u, repo_slug)))
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_workflow()`
# @used-by :meth:`test_cross_repo_issue_urls.CrossRepoIssueUrlsTests.test_staged_issue_urls_ignore_foreign_repo_urls_and_check_dotpy()`
def verify_staged_issue_urls(gate, relative: list[str], stripped_msg: str | None, *, project_root: Path | None=None) -> set[str]:
	from ..issue_lifecycle import origin_repo_slug
	repo_slug = origin_repo_slug(gate.root)
	all_new: set[str] = set()
	for name in relative:
		path = gate.root / name
		# 2026-11-26 "Scope issue-URL lifecycle gates to target repository": https://github.com/dmitry-ai/harness/issues/321
		if path.is_file() and is_code_file(name):
			content = path.read_text(encoding='utf-8', errors='replace')
			if content.strip() and (not is_git_path_exempt(gate.root, name, disk_text=content, message=stripped_msg, project_root=project_root)):
				_verify_single_file_issue_urls(gate, name, content, stripped_msg, all_new, repo_slug)
	if 1 < len(all_new):
		raise ValueError(f'Staged files mix changes from multiple GitHub Issues: {sorted(all_new)}')
	return all_new
# 2026-11-26 "Scope issue-URL lifecycle gates to target repository": https://github.com/dmitry-ai/harness/issues/321
# @used-by :func:`_same_repo_urls()`
# @used-by :func:`filter_repo_turn_issue_urls()`
def _is_same_repo_url(url: str, repo_slug: str | None) -> bool:
	parsed = parse_issue_url(url)
	return (not repo_slug) or (None is not parsed and parsed[0].lower() == repo_slug.lower())
# 2026-11-26 "Resolve deleted worktree paths in TDD comment-only exemption": https://github.com/dmitry-ai/harness/issues/278
# @used-by :func:`is_write_event_exempt()`
def _resolve_scope_rel_path(fpath: Path, scope: Path) -> str:
	parts = fpath.parts
	r = ''
	for idx in range(len(parts) - 3):
		if ('\ua616', 'data', 'worktrees') == parts[idx:idx + 3] and idx + 4 < len(parts):
			r = Path(*parts[idx + 4:]).as_posix()
			break
	if not r:
		try:
			r = fpath.resolve().relative_to(scope.resolve()).as_posix()
		except (OSError, ValueError):
			r = ''
	return r
# 2026-11-26 "Scope issue-URL lifecycle gates to target repository": https://github.com/dmitry-ai/harness/issues/321
# @used-by :func:`_verify_single_file_issue_urls()`
def _check_file_issue_urls(name: str, content: str, stripped_msg: str | None, repo_slug: str | None) -> None:
	raw_urls = set(_GITHUB_ISSUE_URL_RE.findall(content))
	if not raw_urls:
		raise ValueError(f'Issue-tracked code file lacks a GitHub Issue URL reference: {name}')
	file_urls = _same_repo_urls(raw_urls, repo_slug)
	if not file_urls:
		raise ValueError(f'EXEC-5 ISSUE-FIRST-GATE: Referenced issue {sorted(raw_urls)[0]} does not match repository {repo_slug}')
	if None is not stripped_msg and stripped_msg not in file_urls:
		raise ValueError(f'Issue-tracked code file {name} does not reference the commit GitHub Issue URL {stripped_msg}')
# 2026-11-26 "Scope issue-URL lifecycle gates to target repository": https://github.com/dmitry-ai/harness/issues/321
# @used-by :func:`_check_file_issue_urls()`
# @used-by :func:`_verify_single_file_issue_urls()`
def _same_repo_urls(urls: set[str], repo_slug: str | None) -> set[str]:
	return {u for u in urls if _is_same_repo_url(u, repo_slug)}
# @used-by :func:`verify_staged_issue_urls()`
def _verify_single_file_issue_urls(gate, name: str, content: str, stripped_msg: str | None, all_new: set[str], repo_slug: str | None=None) -> None:
	# 2026-11-26 "Scope issue-URL lifecycle gates to target repository": https://github.com/dmitry-ai/harness/issues/321
	_check_file_issue_urls(name, content, stripped_msg, repo_slug)
	added_urls, head_urls = gate._extract_added_diff_urls(name)
	new_diff_urls = _same_repo_urls(added_urls - head_urls, repo_slug)
	if 1 < len(new_diff_urls):
		raise ValueError(f'Staged diff in {name} introduces multiple distinct GitHub Issue URLs: {sorted(new_diff_urls)}')
	if None is not stripped_msg and new_diff_urls and (new_diff_urls != {stripped_msg}):
		raise ValueError(f'Staged diff in {name} introduces GitHub Issue URL(s) {sorted(new_diff_urls)} not matching commit message {stripped_msg}')
	all_new.update(new_diff_urls)
