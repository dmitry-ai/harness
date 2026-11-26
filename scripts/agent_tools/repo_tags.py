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
DATE_TAG_RE = re.compile(r'^(?P<date>\d{4}-\d{2}-\d{2})(?:--(?P<num>[2-9]\d*|1\d+))?$')
SEMVER_TAG_RE = re.compile(r'^v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$')
_ISSUE_URL_RE = re.compile(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\d+)\b')
_LINE_FRAG_RE = re.compile(r'^L(\d+)(?:-L?(\d+))?$')
def _build_retro_entry(repo: Path, commit_row: tuple[str, str, str], reason: str, known: set[str], tz: ZoneInfo) -> dict:
	sha, ci_iso, subj = commit_row
	day = _parse_iso_day(ci_iso, tz)
	existing = pick_preferred_tag(tags_at_commit(repo, sha))
	if None is not existing:
		r = {'sha': sha, 'day': day, 'tag': existing, 'already_tagged': True, 'reason': reason, 'subject': subj}
	else:
		tag = next_date_tag(known, day)
		known.add(tag)
		r = {'sha': sha, 'day': day, 'tag': tag, 'already_tagged': False, 'reason': reason, 'subject': subj}
	return r
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
def _find_git_root(path: Path) -> Path | None:
	start = path if path.is_dir() else path.parent
	r = None
	for anc in (start, *start.parents):
		if (anc / '.git').exists():
			r = anc.resolve()
			break
	return r
def _git_write(repo: Path, args: list[str], *, timeout: int=60) -> subprocess.CompletedProcess:
	return subprocess.run(['git', '-C', str(Path(repo).resolve()), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False, timeout=timeout, creationflags=_NO_WINDOW)
def _mark_task_group_ends(commits: list[tuple[str, str, str]], reasons: dict[int, str]) -> None:
	n = len(commits)
	for idx, (_, _, subj) in enumerate(commits):
		clean = subj.strip()
		if clean and '\u2800' != clean and (not _ISSUE_URL_RE.search(clean)):
			if idx + 1 == n or commits[idx + 1][2].strip() != clean:
				reasons.setdefault(idx, 'task_group')
def _parse_iso_day(iso_text: str, tz: ZoneInfo) -> str:
	return datetime.fromisoformat(iso_text.strip().replace('Z', '+00:00')).astimezone(tz).strftime('%Y-%m-%d')
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
def _resolve_commit_sha(repo: Path, commit: str) -> str:
	proc = run_git_read(repo, ['rev-parse', f'{commit}^{{commit}}'], check=False)
	if 0 != proc.returncode:
		err = proc.stderr.decode('utf-8', errors='replace').strip()
		raise ValueError(f'Unknown commit "{commit}" in {repo}: {err}')
	return proc.stdout.decode('utf-8', errors='replace').strip()
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
def commit_date_day(repo: Path, commit: str='HEAD') -> str:
	proc = run_git_read(repo, ['show', '-s', '--format=%cI', commit], check=False)
	if 0 != proc.returncode or (not proc.stdout.strip()):
		raise ValueError(f'Unable to read committer date for {commit} in {repo}')
	return _parse_iso_day(proc.stdout.decode('utf-8', errors='replace'), _configured_timezone())
def ensure_commit_tag(repo: Path | str, *, commit: str='HEAD', date_override: str | None=None, push: bool=False, remote: str='origin') -> dict:
	repo_p = Path(repo).resolve()
	sha = _resolve_commit_sha(repo_p, commit)
	existing = pick_preferred_tag(tags_at_commit(repo_p, sha))
	if None is not existing:
		tag, created = (existing, False)
	else:
		day = date_override.strip() if date_override else commit_date_day(repo_p, sha)
		tag = next_date_tag(list_repo_tags(repo_p), day)
		proc = _git_write(repo_p, ['tag', tag, sha])
		if 0 != proc.returncode:
			raise RuntimeError(f'git tag {tag} {sha[:12]} failed: {proc.stderr.strip() or proc.stdout.strip()}')
		created = True
	pushed = push_tag(repo_p, tag, remote=remote) if push and has_origin_remote(repo_p, remote=remote) else False
	return {'valid': True, 'repo': repo_p.as_posix(), 'commit': sha, 'tag': tag, 'created': created, 'pushed': pushed}
def has_origin_remote(repo: Path, *, remote: str='origin') -> bool:
	return 0 == run_git_read(repo, ['remote', 'get-url', remote], check=False).returncode
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
def is_valid_repo_tag(tag: str) -> bool:
	clean = (tag or '').strip()
	return is_valid_date_tag(clean) or bool(SEMVER_TAG_RE.fullmatch(clean))
def list_repo_tags(repo: Path) -> list[str]:
	proc = run_git_read(repo, ['tag', '-l'], check=False)
	return [ln.strip() for ln in proc.stdout.decode('utf-8', errors='replace').splitlines() if ln.strip()] if 0 == proc.returncode else []
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
def pick_preferred_tag(tags: Iterable[str]) -> str | None:
	cleaned = [t.strip() for t in tags if t and t.strip()]
	date_tags = sorted((t for t in cleaned if is_valid_date_tag(t)))
	if date_tags:
		r: str | None = date_tags[0]
	else:
		sem_tags = sorted((t for t in cleaned if is_valid_repo_tag(t)))
		r = sem_tags[0] if sem_tags else None
	return r
def plan_retro_tags(repo: Path, *, include_task_groups: bool=False, extra_commits: list[str] | tuple[str, ...]=()) -> list[dict]:
	proc = run_git_read(repo, ['log', '--first-parent', '--reverse', '--format=%H%x1f%cI%x1f%s'], check=False)
	if 0 != proc.returncode:
		err = proc.stderr.decode('utf-8', errors='replace').strip()
		raise RuntimeError(f'Unable to read git log for {repo}: {err}')
	commits = [tuple(ln.split('\x1f', 2)) for ln in proc.stdout.decode('utf-8', errors='replace').splitlines() if 2 == ln.count('\x1f')]
	extra_shas = {_resolve_commit_sha(repo, c) for c in extra_commits if c and str(c).strip()}
	reasons = _qualifying_commit_indices(commits, include_task_groups, extra_shas)
	tz, known = (_configured_timezone(), set(list_repo_tags(repo)))
	return [_build_retro_entry(repo, commits[idx], reasons[idx], known, tz) for idx in sorted(reasons)]
def push_tag(repo: Path, tag: str, *, remote: str='origin') -> bool:
	proc = _git_write(repo, ['push', remote, f'refs/tags/{tag}'])
	if 0 != proc.returncode:
		raise RuntimeError(f'git push {remote} refs/tags/{tag} failed: {proc.stderr.strip() or proc.stdout.strip()}')
	return True
def remote_has_tag(repo: Path, tag: str, *, remote: str='origin') -> bool:
	proc = run_git_read(repo, ['ls-remote', '--tags', remote, f'refs/tags/{tag}'], check=False)
	return 0 == proc.returncode and bool(proc.stdout.strip())
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
def tags_at_commit(repo: Path, commit: str='HEAD') -> list[str]:
	proc = run_git_read(repo, ['tag', '--points-at', commit], check=False)
	return [ln.strip() for ln in proc.stdout.decode('utf-8', errors='replace').splitlines() if ln.strip()] if 0 == proc.returncode else []
def validate_tree_path_and_fragment(repo: Path, ref: str, rel_path: str, fragment: str='') -> tuple[str, int]:
	proc = run_git_read(repo, ['-c', 'core.quotepath=false', 'cat-file', '-t', f'{ref}:{rel_path}'], check=False)
	if 0 != proc.returncode:
		raise ValueError(f'Path "{rel_path}" does not exist at tag "{ref}" in {repo}')
	obj_type = proc.stdout.decode('utf-8', errors='replace').strip()
	if 'tree' == obj_type and fragment:
		raise ValueError(f'Directory link cannot carry fragment #{fragment}: {rel_path}')
	total = _validate_blob_fragment(repo, ref, rel_path, fragment) if 'blob' == obj_type else 0
	return (obj_type, total)
