# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pushed Git tags on issue-closing commits in lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/263
from __future__ import annotations
from pathlib import Path
import configparser
import os
import subprocess
from .git_gate import _NO_WINDOW, run_git_read
from .repo_tags import pick_preferred_tag
from .worktree_flow import git_config_file
def _cached_local_tag_map(repo: Path, git_cache) -> dict[str, list[str]]:
	resolved = Path(repo).resolve()
	store = getattr(git_cache, '_local_tag_map_cache', None) if None is not git_cache else None
	if None is store and None is not git_cache:
		store = {}
		setattr(git_cache, '_local_tag_map_cache', store)
	cached = store.get(resolved) if None is not store else None
	if None is cached:
		cached = _read_local_tag_map(resolved)
		if None is not store:
			store[resolved] = cached
	return cached
def _cached_remote_tags(repo: Path, remote_target: str, git_cache) -> set[str]:
	key = (Path(repo).resolve(), remote_target)
	store = getattr(git_cache, '_remote_tags_cache', None) if None is not git_cache else None
	if None is store and None is not git_cache:
		store = {}
		setattr(git_cache, '_remote_tags_cache', store)
	cached = store.get(key) if None is not store else None
	if None is cached:
		cached = _read_remote_tags(Path(repo).resolve(), remote_target)
		if None is not store:
			store[key] = cached
	return cached
def _has_upstream(repo: Path, git_cache) -> bool:
	if None is not git_cache:
		r = bool(git_cache.upstream_unpushed(repo)[0])
	else:
		r = 0 == run_git_read(repo, ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'], check=False).returncode
	return r
def _parse_ls_remote_tags(raw: str) -> set[str]:
	tags: set[str] = set()
	for line in (raw or '').splitlines():
		parts = line.strip().split('\t', 1)
		if 2 == len(parts) and parts[1].startswith('refs/tags/'):
			name = parts[1][len('refs/tags/'):]
			if not name.endswith('^{}'):
				tags.add(name)
	return tags
def _read_local_tag_map(repo: Path) -> dict[str, list[str]]:
	proc = run_git_read(repo, ['for-each-ref', '--format=%(objectname)%09%(*objectname)%09%(refname:short)', 'refs/tags'], check=False)
	by_sha: dict[str, list[str]] = {}
	if 0 == proc.returncode:
		for line in proc.stdout.decode('utf-8', errors='replace').splitlines():
			parts = line.split('\t')
			if 3 == len(parts) and parts[2].strip():
				target_sha = parts[1].strip() or parts[0].strip()
				if target_sha:
					by_sha.setdefault(target_sha, []).append(parts[2].strip())
	return by_sha
def _read_remote_tags(repo: Path, remote_target: str) -> set[str]:
	local_cand = Path(remote_target)
	if local_cand.is_dir():
		proc = run_git_read(local_cand, ['for-each-ref', '--format=%(refname:short)', 'refs/tags'], check=False)
		r = {ln.strip() for ln in proc.stdout.decode('utf-8', errors='replace').splitlines() if ln.strip()} if 0 == proc.returncode else set()
	else:
		env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'}
		try:
			proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), 'ls-remote', '--tags', 'origin'], stdin=subprocess.DEVNULL, capture_output=True, env=env, check=False, timeout=20, creationflags=_NO_WINDOW)
			r = _parse_ls_remote_tags(proc.stdout.decode('utf-8', errors='replace')) if 0 == proc.returncode else set()
		except subprocess.TimeoutExpired:
			r = set()
	return r
def _resolve_origin_push_target(repo: Path) -> str:
	cfg_file = git_config_file(repo)
	r = ''
	if cfg_file.is_file():
		parser = configparser.RawConfigParser(strict=False)
		try:
			parser.read_string(cfg_file.read_text(encoding='utf-8', errors='replace'))
			sec = 'remote "origin"'
			if parser.has_section(sec):
				r = (parser.get(sec, 'pushurl', fallback='') or parser.get(sec, 'url', fallback='')).strip()
		except (OSError, configparser.Error):
			r = ''
	return r
def finalize_commit_close_check(repo: Path, commit_sha: str, issue_url: str, git_cache) -> dict:
	pushed = git_cache.verify_commit_pushed(repo, commit_sha, issue_url)
	tag = verify_closing_commit_tag(repo, commit_sha, issue_url, git_cache=git_cache)
	return {'verified': True, 'repo': str(repo), 'issue_url': issue_url, 'commit_sha': commit_sha, 'pushed': pushed, 'tag': tag}
def verify_closing_commit_tag(repo: Path, commit_sha: str, issue_url: str, *, git_cache=None) -> str:
	resolved = Path(repo).resolve()
	tag_map = _cached_local_tag_map(resolved, git_cache)
	tag = pick_preferred_tag(tag_map.get(commit_sha, ()))
	if None is tag:
		raise ValueError(f'EXEC-5 violation: closing commit {commit_sha[:12]} referencing {issue_url} in {resolved} has no valid Git tag (run harness.py repo-tag "{resolved.as_posix()}" --commit {commit_sha[:12]} --push before df_github_issue.py close)')
	remote_target = _resolve_origin_push_target(resolved)
	if remote_target and _has_upstream(resolved, git_cache):
		remote_tags = _cached_remote_tags(resolved, remote_target, git_cache)
		if tag not in remote_tags:
			raise ValueError(f'EXEC-5 violation: Git tag {tag} on closing commit {commit_sha[:12]} referencing {issue_url} in {resolved} is not pushed to origin (run harness.py repo-tag "{resolved.as_posix()}" --commit {commit_sha[:12]} --push before df_github_issue.py close)')
	return tag
