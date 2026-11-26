# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement daily-counter Git tag engine and repo-tag CLI commands":
# https://github.com/dmitry-ai/harness/issues/262
from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo
import re
import subprocess
from .git_gate import _NO_WINDOW, run_git_read
from .issues.repo_locator import origin_repo_slug
from .worktree_flow import git_config_file
DATE_TAG_RE = re.compile(r'^(?P<date>\d{4}-\d{2}-\d{2})(?:--(?P<num>[2-9]\d*|1\d+))?$')
SEMVER_TAG_RE = re.compile(r'^v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$')
_ISSUE_URL_RE = re.compile(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\d+)\b')
_LINE_FRAG_RE = re.compile(r'^L(\d+)(?:-L?(\d+))?$')
# @used-by :func:`plan_retro_tags()`
def _build_retro_entry(by_sha: dict[str, list[str]], commit_row: tuple[str, str, str], reason: str, known: set[str], tz: ZoneInfo) -> dict:
	sha, ci_iso, subj = commit_row
	day = _parse_iso_day(ci_iso, tz)
	existing = pick_preferred_tag(by_sha.get(sha, ()))
	if None is not existing:
		r = {'sha': sha, 'day': day, 'tag': existing, 'already_tagged': True, 'reason': reason, 'subject': subj}
	else:
		tag = next_date_tag(known, day)
		known.add(tag)
		r = {'sha': sha, 'day': day, 'tag': tag, 'already_tagged': False, 'reason': reason, 'subject': subj}
	return r
# @used-by :func:`ensure_commit_tag()`
def _commit_sha_and_day(repo: Path, commit: str) -> tuple[str, str]:
	proc = run_git_read(repo, ['show', '-s', '--format=%H%x1f%cI', f'{commit}^{{commit}}'], check=False)
	raw = proc.stdout.decode('utf-8', errors='replace').strip() if 0 == proc.returncode else ''
	if 0 != proc.returncode or '\x1f' not in raw:
		err = proc.stderr.decode('utf-8', errors='replace').strip()
		raise ValueError(f'Unknown commit "{commit}" in {repo}: {err}')
	sha, ci_iso = raw.split('\x1f', 1)
	return (sha.strip(), _parse_iso_day(ci_iso, _configured_timezone()))
# @used-by :func:`_commit_sha_and_day()`
# @used-by :func:`commit_date_day()`
# @used-by :func:`plan_retro_tags()`
def _configured_timezone() -> ZoneInfo:
	tz_name = 'Europe/Istanbul'
	try:
		from .runtime import settings
		val = str((settings() or {}).get('timezone') or '').strip()
		if val:
			tz_name = val
	except Exception:
		pass
	return ZoneInfo(tz_name)
# @used-by :func:`build_github_blob_url()`
def _find_git_root(path: Path) -> Path | None:
	start = path if path.is_dir() else path.parent
	r = None
	for anc in (start, *start.parents):
		if (anc / '.git').exists():
			r = anc.resolve()
			break
	return r
# @used-by :func:`ensure_commit_tag()`
# @used-by :func:`push_tag()`
# @used-by :func:`retro_tag_repo()`
def _git_write(repo: Path, args: list[str], *, timeout: int=60) -> subprocess.CompletedProcess:
	return subprocess.run(['git', '-C', str(Path(repo).resolve()), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False, timeout=timeout, creationflags=_NO_WINDOW)
# @used-by :func:`_qualifying_commit_indices()`
def _mark_task_group_ends(commits: list[tuple[str, str, str]], reasons: dict[int, str]) -> None:
	n = len(commits)
	for idx, (_, _, subj) in enumerate(commits):
		clean = subj.strip()
		if clean and '\u2800' != clean and (not _ISSUE_URL_RE.search(clean)):
			if idx + 1 == n or commits[idx + 1][2].strip() != clean:
				reasons.setdefault(idx, 'task_group')
# @used-by :func:`_build_retro_entry()`
# @used-by :func:`_commit_sha_and_day()`
# @used-by :func:`commit_date_day()`
def _parse_iso_day(iso_text: str, tz: ZoneInfo) -> str:
	return datetime.fromisoformat(iso_text.strip().replace('Z', '+00:00')).astimezone(tz).strftime('%Y-%m-%d')
# @used-by :func:`plan_retro_tags()`
def _qualifying_commit_indices(commits: list[tuple[str, str, str]], include_task_groups: bool, extra_shas: set[str]) -> dict[int, str]:
	reasons: dict[int, str] = {}
	last_issue: dict[str, int] = {}
	for idx, (sha, _, subj) in enumerate(commits):
		m = _ISSUE_URL_RE.search(subj)
		if m:
			last_issue[f'{m.group(1).lower()}#{m.group(2)}'] = idx
		if sha in extra_shas:
			reasons[idx] = 'referenced'
	for key, idx in last_issue.items():
		reasons.setdefault(idx, f'issue:{key}')
	if include_task_groups:
		_mark_task_group_ends(commits, reasons)
	return reasons
# @used-by :func:`ensure_commit_tag()`
# @used-by :func:`plan_retro_tags()`
def _read_tag_refs(repo: Path) -> tuple[list[str], dict[str, list[str]]]:
	proc = run_git_read(repo, ['for-each-ref', '--format=%(objectname)%09%(*objectname)%09%(refname:short)', 'refs/tags'], check=False)
	all_tags, by_sha = ([], {})
	if 0 == proc.returncode:
		for line in proc.stdout.decode('utf-8', errors='replace').splitlines():
			parts = line.split('\t')
			if 3 == len(parts) and parts[2].strip():
				name = parts[2].strip()
				all_tags.append(name)
				target = parts[1].strip() or parts[0].strip()
				if target:
					by_sha.setdefault(target, []).append(name)
	return (all_tags, by_sha)
# @used-by :func:`plan_retro_tags()`
def _resolve_commit_sha(repo: Path, commit: str) -> str:
	proc = run_git_read(repo, ['rev-parse', f'{commit}^{{commit}}'], check=False)
	if 0 != proc.returncode:
		err = proc.stderr.decode('utf-8', errors='replace').strip()
		raise ValueError(f'Unknown commit "{commit}" in {repo}: {err}')
	return proc.stdout.decode('utf-8', errors='replace').strip()
# @used-by :func:`validate_tree_path_and_fragment()`
def _validate_blob_fragment(repo: Path, ref: str, rel_path: str, fragment: str) -> int:
	proc = run_git_read(repo, ['-c', 'core.quotepath=false', 'show', f'{ref}:{rel_path}'], check=False)
	if 0 != proc.returncode:
		raise ValueError(f'Path "{rel_path}" is missing at tag "{ref}" in {repo}')
	text = proc.stdout.decode('utf-8', errors='replace')
	total = max(1, len(text.splitlines()))
	m_ln = _LINE_FRAG_RE.fullmatch(fragment) if fragment else None
	if None is not m_ln:
		start = int(m_ln.group(1))
		end = int(m_ln.group(2) or start)
		if 1 > start or start > end or end > total:
			raise ValueError(f'Line anchor #{fragment} out of bounds (1..{total}) for {rel_path} at {ref}')
	return total
# @used-by :func:`run_repo_tag_cli()`
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_github_blob_url_builder_validates_file_and_lines()`
def build_github_blob_url(file_path: Path | str, *, commit: str='HEAD', lines: str | None=None, anchor: str | None=None, push: bool=False, date_override: str | None=None) -> str:
	target = Path(file_path).resolve()
	repo_root = _find_git_root(target)
	if None is repo_root:
		raise ValueError(f'Path is not inside a Git repository: {target}')
	slug = origin_repo_slug(repo_root)
	if not slug:
		raise ValueError(f'Repository has no GitHub remote slug: {repo_root}')
	rel_path = target.relative_to(repo_root).as_posix()
	if not rel_path or '.' == rel_path:
		raise ValueError(f'Target must be a file or subdirectory inside {repo_root}')
	tag = ensure_commit_tag(repo_root, commit=commit, date_override=date_override, push=push)['tag']
	frag = (lines or anchor or '').strip().lstrip('#')
	obj_type, _ = validate_tree_path_and_fragment(repo_root, tag, rel_path, frag)
	kind = 'tree' if 'tree' == obj_type else 'blob'
	return f'https://github.com/{slug}/{kind}/{tag}/{rel_path}' + (f'#{frag}' if frag else '')
# @used-by unused
def commit_date_day(repo: Path, commit: str='HEAD') -> str:
	proc = run_git_read(repo, ['show', '-s', '--format=%cI', commit], check=False)
	if 0 != proc.returncode or (not proc.stdout.strip()):
		raise ValueError(f'Unable to read committer date for {commit} in {repo}')
	return _parse_iso_day(proc.stdout.decode('utf-8', errors='replace'), _configured_timezone())
# @used-by :func:`agent_tools.worktree_flow._apply_land_tag()`
# @used-by :func:`build_github_blob_url()`
# @used-by :func:`run_repo_tag_cli()`
# @used-by :func:`test_clarification_stop_consent._build_fixture()`
# @used-by :func:`test_dirty_diff_issue_scope._init_repo()`
# @used-by :func:`test_git_lifecycle_memoization._init_multi_issue_repo()`
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
	repo_p = Path(repo).resolve()
	sha, auto_day = _commit_sha_and_day(repo_p, commit)
	all_tags, by_sha = _read_tag_refs(repo_p)
	existing = pick_preferred_tag(by_sha.get(sha, ()))
	if None is not existing:
		tag, created = (existing, False)
	else:
		day = date_override.strip() if date_override else auto_day
		tag = next_date_tag(all_tags, day)
		proc = _git_write(repo_p, ['tag', tag, sha])
		if 0 != proc.returncode:
			raise RuntimeError(f'git tag {tag} {sha[:12]} failed: {proc.stderr.strip() or proc.stdout.strip()}')
		created = True
	pushed = push_tag(repo_p, tag, remote=remote) if push and has_origin_remote(repo_p, remote=remote) else False
	return {'valid': True, 'repo': repo_p.as_posix(), 'commit': sha, 'tag': tag, 'created': created, 'pushed': pushed}
# @used-by :func:`ensure_commit_tag()`
# @used-by :func:`retro_tag_repo()`
def has_origin_remote(repo: Path, *, remote: str='origin') -> bool:
	cfg = git_config_file(repo)
	if cfg.is_file():
		r = f'[remote "{remote}"]' in cfg.read_text(encoding='utf-8', errors='replace')
	else:
		r = 0 == run_git_read(repo, ['remote', 'get-url', remote], check=False).returncode
	return r
# @used-by :func:`is_valid_repo_tag()`
# @used-by :func:`pick_preferred_tag()`
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
# @used-by :func:`agent_tools.repo_link_gate._validate_github_url()`
# @used-by :func:`agent_tools.repo_link_gate.resolve_local_github_blob()`
# @used-by :func:`pick_preferred_tag()`
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_date_tag_and_repo_tag_validation()`
def is_valid_repo_tag(tag: str) -> bool:
	clean = (tag or '').strip()
	return is_valid_date_tag(clean) or bool(SEMVER_TAG_RE.fullmatch(clean))
# @used-by unused
def list_repo_tags(repo: Path) -> list[str]:
	proc = run_git_read(repo, ['tag', '-l'], check=False)
	return [ln.strip() for ln in proc.stdout.decode('utf-8', errors='replace').splitlines() if ln.strip()] if 0 == proc.returncode else []
# @used-by :func:`_build_retro_entry()`
# @used-by :func:`ensure_commit_tag()`
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_next_date_tag_daily_counter_and_reset()`
def next_date_tag(existing_tags: Iterable[str], day: str) -> str:
	clean_day = date.fromisoformat((day or '').strip()).isoformat()
	max_num = 0
	for raw in existing_tags:
		m = DATE_TAG_RE.fullmatch((raw or '').strip())
		if None is not m and clean_day == m.group('date'):
			num = 1 if None is m.group('num') else int(m.group('num'))
			if num > max_num:
				max_num = num
	return clean_day if 0 == max_num else f'{clean_day}--{max_num + 1}'
# @used-by :func:`_build_retro_entry()`
# @used-by :func:`agent_tools.repo_tag_gate.verify_closing_commit_tag()`
# @used-by :func:`ensure_commit_tag()`
def pick_preferred_tag(tags: Iterable[str]) -> str | None:
	cleaned = [t.strip() for t in tags if t and t.strip()]
	date_tags = sorted((t for t in cleaned if is_valid_date_tag(t)))
	if date_tags:
		r: str | None = date_tags[0]
	else:
		sem_tags = sorted((t for t in cleaned if is_valid_repo_tag(t)))
		r = sem_tags[0] if sem_tags else None
	return r
# @used-by :func:`retro_tag_repo()`
def plan_retro_tags(repo: Path, *, include_task_groups: bool=False, extra_commits: list[str] | tuple[str, ...]=()) -> list[dict]:
	proc = run_git_read(repo, ['log', '--first-parent', '--reverse', '--format=%H%x1f%cI%x1f%s'], check=False)
	if 0 != proc.returncode:
		err = proc.stderr.decode('utf-8', errors='replace').strip()
		raise RuntimeError(f'Unable to read git log for {repo}: {err}')
	commits = [tuple(ln.split('\x1f', 2)) for ln in proc.stdout.decode('utf-8', errors='replace').splitlines() if 2 == ln.count('\x1f')]
	extra_shas = {_resolve_commit_sha(repo, c) for c in extra_commits if c and str(c).strip()}
	reasons = _qualifying_commit_indices(commits, include_task_groups, extra_shas)
	all_tags, by_sha = _read_tag_refs(repo)
	tz, known = (_configured_timezone(), set(all_tags))
	return [_build_retro_entry(by_sha, commits[idx], reasons[idx], known, tz) for idx in sorted(reasons)]
# @used-by :func:`ensure_commit_tag()`
def push_tag(repo: Path, tag: str, *, remote: str='origin') -> bool:
	proc = _git_write(repo, ['push', remote, f'refs/tags/{tag}'])
	if 0 != proc.returncode:
		raise RuntimeError(f'git push {remote} refs/tags/{tag} failed: {proc.stderr.strip() or proc.stdout.strip()}')
	return True
# @used-by unused
def remote_has_tag(repo: Path, tag: str, *, remote: str='origin') -> bool:
	proc = run_git_read(repo, ['ls-remote', '--tags', remote, f'refs/tags/{tag}'], check=False)
	return 0 == proc.returncode and bool(proc.stdout.strip())
# @used-by :func:`agent_tools.cli_registry._exec_repo_tag_retro()`
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_retro_tag_repo_tags_closing_commits_chronologically()`
def retro_tag_repo(repo: Path | str, *, apply: bool=False, push: bool=False, include_task_groups: bool=False, extra_commits: list[str] | tuple[str, ...]=(), remote: str='origin') -> dict:
	repo_p = Path(repo).resolve()
	plan = plan_retro_tags(repo_p, include_task_groups=include_task_groups, extra_commits=extra_commits)
	created = 0
	if apply:
		for item in plan:
			if not item['already_tagged']:
				tag_name, sha = (item['tag'], item['sha'])
				proc = _git_write(repo_p, ['tag', tag_name, sha])
				if 0 != proc.returncode:
					raise RuntimeError(f'git tag {tag_name} {sha[:12]} failed: {proc.stderr.strip() or proc.stdout.strip()}')
				created += 1
	pushed = False
	if apply and push and has_origin_remote(repo_p, remote=remote):
		p_proc = _git_write(repo_p, ['push', remote, '--tags'], timeout=120)
		if 0 != p_proc.returncode:
			raise RuntimeError(f'git push {remote} --tags failed: {p_proc.stderr.strip() or p_proc.stdout.strip()}')
		pushed = True
	return {'valid': True, 'repo': repo_p.as_posix(), 'apply': bool(apply), 'planned_count': len(plan), 'created_count': created, 'already_tagged_count': sum((1 for x in plan if x['already_tagged'])), 'pushed': pushed, 'planned': plan}
# @used-by :func:`agent_tools.cli_registry._exec_repo_tag()`
def run_repo_tag_cli(args) -> dict:
	repo_p = Path(args.repo).resolve()
	if args.file:
		file_p = Path(args.file)
		full_p = file_p if file_p.is_absolute() else (repo_p / file_p)
		res = ensure_commit_tag(repo_p, commit=args.commit, date_override=args.date, push=bool(args.push))
		res['github_url'] = build_github_blob_url(full_p, commit=args.commit, lines=args.lines, anchor=args.anchor, push=False, date_override=args.date)
	else:
		res = ensure_commit_tag(repo_p, commit=args.commit, date_override=args.date, push=bool(args.push))
	return res
# @used-by unused
def tags_at_commit(repo: Path, commit: str='HEAD') -> list[str]:
	proc = run_git_read(repo, ['tag', '--points-at', commit], check=False)
	return [ln.strip() for ln in proc.stdout.decode('utf-8', errors='replace').splitlines() if ln.strip()] if 0 == proc.returncode else []
# @used-by :func:`build_github_blob_url()`
def validate_tree_path_and_fragment(repo: Path, ref: str, rel_path: str, fragment: str='') -> tuple[str, int]:
	proc = run_git_read(repo, ['-c', 'core.quotepath=false', 'cat-file', '-t', f'{ref}:{rel_path}'], check=False)
	if 0 != proc.returncode:
		raise ValueError(f'Path "{rel_path}" does not exist at tag "{ref}" in {repo}')
	obj_type = proc.stdout.decode('utf-8', errors='replace').strip()
	if 'tree' == obj_type and fragment:
		raise ValueError(f'Directory link cannot carry fragment #{fragment}: {rel_path}')
	total = _validate_blob_fragment(repo, ref, rel_path, fragment) if 'blob' == obj_type else 0
	return (obj_type, total)
