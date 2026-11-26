# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from agent_tools.git_gate import _NO_WINDOW, run_git_read
from agent_tools.repo_tags import pick_preferred_tag
from agent_tools.worktree_flow import git_config_file
import configparser
import os
import subprocess
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class RepoTagGate:
	# @used-by :func:`agent_tools.repo_tag_gate.verify_closing_commit_tag()`
	# @used-by :meth:`RepoTagGate.finalize_close_check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	def __init__(self, repo: Path, commit_sha: str, issue_url: str, *, git_cache=None) -> None:
		self.__repo = Path(repo).resolve()
		self.__commit_sha = commit_sha
		self.__issue_url = issue_url
		self.__git_cache = git_cache
	# @used-by :meth:`RepoTagGate.verify()`
	@staticmethod
	def __cached_local_tag_map(repo: Path, git_cache) -> dict[str, list[str]]:
		resolved = Path(repo).resolve()
		store = getattr(git_cache, '_local_tag_map_cache', None) if None is not git_cache else None
		if None is store and None is not git_cache:
			store = {}
			setattr(git_cache, '_local_tag_map_cache', store)
		cached = store.get(resolved) if None is not store else None
		if None is cached:
			cached = RepoTagGate.__read_local_tag_map(resolved)
			if None is not store:
				store[resolved] = cached
		return cached
	# @used-by :meth:`RepoTagGate.verify()`
	@staticmethod
	def __cached_remote_tags(repo: Path, remote_target: str, git_cache) -> set[str]:
		key = (Path(repo).resolve(), remote_target)
		store = getattr(git_cache, '_remote_tags_cache', None) if None is not git_cache else None
		if None is store and None is not git_cache:
			store = {}
			setattr(git_cache, '_remote_tags_cache', store)
		cached = store.get(key) if None is not store else None
		if None is cached:
			cached = RepoTagGate.__read_remote_tags(Path(repo).resolve(), remote_target)
			if None is not store:
				store[key] = cached
		return cached
	# @used-by :meth:`RepoTagGate.verify()`
	@staticmethod
	def __has_upstream(repo: Path, git_cache) -> bool:
		if None is not git_cache:
			r = bool(git_cache.upstream_unpushed(repo)[0])
		else:
			r = 0 == run_git_read(repo, ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'], check=False).returncode
		return r
	# @used-by :meth:`RepoTagGate.__read_remote_tags()`
	@staticmethod
	def __parse_ls_remote_tags(raw: str) -> set[str]:
		tags: set[str] = set()
		for line in (raw or '').splitlines():
			parts = line.strip().split('\t', 1)
			if 2 == len(parts) and parts[1].startswith('refs/tags/'):
				name = parts[1][len('refs/tags/'):]
				if not name.endswith('^{}'):
					tags.add(name)
		return tags
	# @used-by :meth:`RepoTagGate.__cached_local_tag_map()`
	@staticmethod
	def __read_local_tag_map(repo: Path) -> dict[str, list[str]]:
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
	# @used-by :meth:`RepoTagGate.__cached_remote_tags()`
	@staticmethod
	def __read_remote_tags(repo: Path, remote_target: str) -> set[str]:
		local_cand = Path(remote_target)
		if local_cand.is_dir():
			proc = run_git_read(local_cand, ['for-each-ref', '--format=%(refname:short)', 'refs/tags'], check=False)
			r = {ln.strip() for ln in proc.stdout.decode('utf-8', errors='replace').splitlines() if ln.strip()} if 0 == proc.returncode else set()
		else:
			env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'}
			try:
				proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), 'ls-remote', '--tags', 'origin'], stdin=subprocess.DEVNULL, capture_output=True, env=env, check=False, timeout=20, creationflags=_NO_WINDOW)
				r = RepoTagGate.__parse_ls_remote_tags(proc.stdout.decode('utf-8', errors='replace')) if 0 == proc.returncode else set()
			except subprocess.TimeoutExpired:
				r = set()
		return r
	# @used-by :meth:`RepoTagGate.verify()`
	@staticmethod
	def __resolve_origin_push_target(repo: Path) -> str:
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
	# @used-by :func:`agent_tools.repo_tag_gate.finalize_commit_close_check()`
	@staticmethod
	def finalize_close_check(repo: Path, commit_sha: str, issue_url: str, git_cache) -> dict:
		pushed = git_cache.verify_commit_pushed(repo, commit_sha, issue_url)
		tag = RepoTagGate(repo, commit_sha, issue_url, git_cache=git_cache).verify()
		return {'verified': True, 'repo': str(repo), 'issue_url': issue_url, 'commit_sha': commit_sha, 'pushed': pushed, 'tag': tag}
	# @used-by :func:`agent_tools.repo_tag_gate.verify_closing_commit_tag()`
	# @used-by :meth:`RepoTagGate.finalize_close_check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	def verify(self) -> str:
		tag_map = RepoTagGate.__cached_local_tag_map(self.__repo, self.__git_cache)
		tag = pick_preferred_tag(tag_map.get(self.__commit_sha, ()))
		if None is tag:
			raise ValueError(f'EXEC-5 violation: closing commit {self.__commit_sha[:12]} referencing {self.__issue_url} in {self.__repo} has no valid Git tag (run harness.py repo-tag "{self.__repo.as_posix()}" --commit {self.__commit_sha[:12]} --push before df_github_issue.py close)')
		remote_target = RepoTagGate.__resolve_origin_push_target(self.__repo)
		if remote_target and RepoTagGate.__has_upstream(self.__repo, self.__git_cache):
			remote_tags = RepoTagGate.__cached_remote_tags(self.__repo, remote_target, self.__git_cache)
			if tag not in remote_tags:
				raise ValueError(f'EXEC-5 violation: Git tag {tag} on closing commit {self.__commit_sha[:12]} referencing {self.__issue_url} in {self.__repo} is not pushed to origin (run harness.py repo-tag "{self.__repo.as_posix()}" --commit {self.__commit_sha[:12]} --push before df_github_issue.py close)')
		return tag
