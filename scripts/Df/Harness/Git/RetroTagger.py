# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from Df.Harness.Git.DateTagAllocator import DateTagAllocator
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.Git.TagSelector import TagSelector
from Df.Harness.lib.worktree import dfh_has_origin_remote
import re
import subprocess
_ISSUE_URL_RE = re.compile(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\d+)\b')
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class RetroTagger:
	# @used-by :func:`agent_tools.repo_tags.plan_retro_tags()`
	# @used-by :func:`agent_tools.repo_tags.retro_tag_repo()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def __init__(self, repo: Path | str, *, apply: bool=False, push: bool=False, include_task_groups: bool=False, extra_commits: list[str] | tuple[str, ...]=(), remote: str='origin') -> None:
		self.__repo = Path(repo).resolve()
		self.__apply = apply
		self.__push = push
		self.__include_groups = include_task_groups
		self.__extra_commits = extra_commits
		self.__remote = remote
	# @used-by :meth:`RetroTagger.__plan()`
	@staticmethod
	def __build_entry(by_sha: dict[str, list[str]], row: tuple[str, str, str], reason: str, known: set[str], tz: ZoneInfo) -> dict:
		sha, ci_iso, subj = row
		day = datetime.fromisoformat(ci_iso.strip().replace('Z', '+00:00')).astimezone(tz).strftime('%Y-%m-%d')
		existing = TagSelector(by_sha.get(sha, ())).pick()
		if None is not existing:
			r = {'sha': sha, 'day': day, 'tag': existing, 'already_tagged': True, 'reason': reason, 'subject': subj}
		else:
			tag = DateTagAllocator(known, day).allocate()
			known.add(tag)
			r = {'sha': sha, 'day': day, 'tag': tag, 'already_tagged': False, 'reason': reason, 'subject': subj}
		return r
	# @used-by :meth:`RetroTagger.__plan()`
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
	# @used-by :meth:`RetroTagger.run()`
	def __git_write(self, args: list[str], *, timeout: int=60) -> subprocess.CompletedProcess:
		return subprocess.run(['git', '-C', str(self.__repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False, timeout=timeout, creationflags=_NO_WINDOW)
	# @used-by :meth:`RetroTagger.run()`
	def __plan(self) -> list[dict]:
		proc = RepoGate(self.__repo).run_read(['log', '--first-parent', '--reverse', '--format=%H%x1f%cI%x1f%s'], check=False)
		if 0 != proc.returncode:
			err = proc.stderr.decode('utf-8', errors='replace').strip()
			raise RuntimeError(f'Unable to read git log for {self.__repo}: {err}')
		commits = [tuple(ln.split('\x1f', 2)) for ln in proc.stdout.decode('utf-8', errors='replace').splitlines() if 2 == ln.count('\x1f')]
		extra_shas = {self.__resolve_sha(c) for c in self.__extra_commits if c and str(c).strip()}
		reasons = self.__qualifying_indices(commits, extra_shas)
		all_tags, by_sha = self.__read_tag_refs()
		tz, known = (self.__configured_tz(), set(all_tags))
		return [self.__build_entry(by_sha, commits[idx], reasons[idx], known, tz) for idx in sorted(reasons)]
	# @used-by :meth:`RetroTagger.__plan()`
	def __qualifying_indices(self, commits: list[tuple[str, str, str]], extra_shas: set[str]) -> dict[int, str]:
		reasons: dict[int, str] = {}
		last_issue: dict[str, int] = {}
		for idx, (sha, _, subj) in enumerate(commits):
			m = _ISSUE_URL_RE.search(subj)
			if None is not m:
				last_issue[f'{m.group(1).lower()}#{m.group(2)}'] = idx
			if sha in extra_shas:
				reasons[idx] = 'referenced'
		for key, idx in last_issue.items():
			reasons.setdefault(idx, f'issue:{key}')
		if self.__include_groups:
			n = len(commits)
			for idx, (_, _, subj) in enumerate(commits):
				clean = subj.strip()
				if clean and '\u2800' != clean and (not _ISSUE_URL_RE.search(clean)) and (idx + 1 == n or commits[idx + 1][2].strip() != clean):
					reasons.setdefault(idx, 'task_group')
		return reasons
	# @used-by :meth:`RetroTagger.__plan()`
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
	# @used-by :meth:`RetroTagger.__plan()`
	def __resolve_sha(self, commit: str) -> str:
		proc = RepoGate(self.__repo).run_read(['rev-parse', f'{commit}^{{commit}}'], check=False)
		if 0 != proc.returncode:
			err = proc.stderr.decode('utf-8', errors='replace').strip()
			raise ValueError(f'Unknown commit "{commit}" in {self.__repo}: {err}')
		return proc.stdout.decode('utf-8', errors='replace').strip()
	# @used-by :func:`agent_tools.repo_tags.plan_retro_tags()`
	# @used-by :func:`agent_tools.repo_tags.retro_tag_repo()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def run(self) -> dict:
		plan = self.__plan()
		created = 0
		if self.__apply:
			for item in plan:
				if not item['already_tagged']:
					tag_name, sha = (item['tag'], item['sha'])
					proc = self.__git_write(['tag', tag_name, sha])
					if 0 != proc.returncode:
						raise RuntimeError(f'git tag {tag_name} {sha[:12]} failed: {proc.stderr.strip() or proc.stdout.strip()}')
					created += 1
		pushed = False
		if self.__apply and self.__push and dfh_has_origin_remote(self.__repo, remote=self.__remote):
			p_proc = self.__git_write(['push', self.__remote, '--tags'], timeout=120)
			if 0 != p_proc.returncode:
				raise RuntimeError(f'git push {self.__remote} --tags failed: {p_proc.stderr.strip() or p_proc.stdout.strip()}')
			pushed = True
		return {'valid': True, 'repo': self.__repo.as_posix(), 'apply': bool(self.__apply), 'planned_count': len(plan), 'created_count': created, 'already_tagged_count': sum((1 for x in plan if x['already_tagged'])), 'pushed': pushed, 'planned': plan}
