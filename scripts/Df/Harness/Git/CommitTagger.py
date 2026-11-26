# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from Df.Harness.Git.DateTagAllocator import DateTagAllocator
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.Git.TagSelector import TagSelector
from Df.Harness.lib.worktree import dfh_has_origin_remote
import subprocess
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CommitTagger:
	# @used-by :func:`agent_tools.repo_tags.ensure_commit_tag()`
	# @used-by :meth:`Df.Harness.Git.BlobUrlBuilder.BlobUrlBuilder.build()`
	# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__push_and_finish()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def __init__(self, repo: Path | str, *, commit: str='HEAD', date_override: str | None=None, push: bool=False, remote: str='origin') -> None:
		self.__repo = Path(repo).resolve()
		self.__commit = commit
		self.__date_override = date_override
		self.__push = push
		self.__remote = remote
	# @used-by :meth:`CommitTagger.ensure()`
	def __commit_sha_and_day(self) -> tuple[str, str]:
		proc = RepoGate(self.__repo).run_read(['show', '-s', '--format=%H%x1f%cI', f'{self.__commit}^{{commit}}'], check=False)
		raw = proc.stdout.decode('utf-8', errors='replace').strip() if 0 == proc.returncode else ''
		if 0 != proc.returncode or '\x1f' not in raw:
			err = proc.stderr.decode('utf-8', errors='replace').strip()
			raise ValueError(f'Unknown commit "{self.__commit}" in {self.__repo}: {err}')
		sha, ci_iso = raw.split('\x1f', 1)
		day = datetime.fromisoformat(ci_iso.strip().replace('Z', '+00:00')).astimezone(self.__configured_tz()).strftime('%Y-%m-%d')
		return (sha.strip(), day)
	# @used-by :meth:`CommitTagger.__commit_sha_and_day()`
	@staticmethod
	def __configured_tz() -> ZoneInfo:
		tz_name = 'Europe/Istanbul'
		try:
			from agent_tools.runtime import settings
			val = str((settings() or {}).get('timezone') or '').strip()
			if val:
				tz_name = val
		except Exception:
			pass
		return ZoneInfo(tz_name)
	# @used-by :meth:`CommitTagger.__push_tag()`
	# @used-by :meth:`CommitTagger.ensure()`
	def __git_write(self, args: list[str], *, timeout: int=60) -> subprocess.CompletedProcess:
		return subprocess.run(['git', '-C', str(self.__repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False, timeout=timeout, creationflags=_NO_WINDOW)
	# @used-by :meth:`CommitTagger.ensure()`
	def __push_tag(self, tag: str) -> bool:
		proc = self.__git_write(['push', self.__remote, f'refs/tags/{tag}'])
		if 0 != proc.returncode:
			raise RuntimeError(f'git push {self.__remote} refs/tags/{tag} failed: {proc.stderr.strip() or proc.stdout.strip()}')
		return True
	# @used-by :meth:`CommitTagger.ensure()`
	def __read_tag_refs(self) -> tuple[list[str], dict[str, list[str]]]:
		proc = RepoGate(self.__repo).run_read(['for-each-ref', '--format=%(objectname)%09%(*objectname)%09%(refname:short)', 'refs/tags'], check=False)
		all_tags, by_sha = ([], {})
		if 0 == proc.returncode:
			for line in proc.stdout.decode('utf-8', errors='replace').splitlines():
				parts = line.split('\t')
				if 3 == len(parts) and parts[2].strip():
					name, target = (parts[2].strip(), parts[1].strip() or parts[0].strip())
					all_tags.append(name)
					if target:
						by_sha.setdefault(target, []).append(name)
		return (all_tags, by_sha)
	# @used-by :func:`agent_tools.repo_tags.ensure_commit_tag()`
	# @used-by :meth:`Df.Harness.Git.BlobUrlBuilder.BlobUrlBuilder.build()`
	# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__push_and_finish()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def ensure(self) -> dict:
		sha, auto_day = self.__commit_sha_and_day()
		all_tags, by_sha = self.__read_tag_refs()
		existing = TagSelector(by_sha.get(sha, ())).pick()
		if None is not existing:
			tag, created = (existing, False)
		else:
			day = self.__date_override.strip() if self.__date_override else auto_day
			tag = DateTagAllocator(all_tags, day).allocate()
			proc = self.__git_write(['tag', tag, sha])
			if 0 != proc.returncode:
				raise RuntimeError(f'git tag {tag} {sha[:12]} failed: {proc.stderr.strip() or proc.stdout.strip()}')
			created = True
		pushed = self.__push_tag(tag) if self.__push and dfh_has_origin_remote(self.__repo, remote=self.__remote) else False
		return {'valid': True, 'repo': self.__repo.as_posix(), 'commit': sha, 'tag': tag, 'created': created, 'pushed': pushed}
