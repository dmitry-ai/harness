# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
from agent_tools.storage import replace_bytes
import os
import subprocess
GIT_IGNORE_END = '# <<< harness:ephemeral-ignore:end <<<'
GIT_IGNORE_START = '# >>> harness:ephemeral-ignore:start >>>'
HARNESS_GLOBAL_IGNORE_PATTERNS = ('\ua616/data/worktrees/', '\ua616/data/scratch/', '\ua616/data/browser-locks/', '\ua616/data/repo-leases/', '**/*.lock')
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class GlobalIgnoreSyncer:
	# @used-by :func:`agent_tools.git_ignore.sync_global_git_ignore()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def __init__(self, *, check: bool=False, ignore_path: Path | str | None=None, env: dict[str, str] | None=None, patterns: tuple[str, ...]=HARNESS_GLOBAL_IGNORE_PATTERNS) -> None:
		self.__check = check
		self.__ignore_path = ignore_path
		self.__env = env
		self.__patterns = patterns
	# @used-by :meth:`GlobalIgnoreSyncer.__resolve_path()`
	def __configured_excludes_file(self) -> Path | None:
		proc = subprocess.run(['git', 'config', '--global', '--path', '--get', 'core.excludesFile'], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', env=self.__env, check=False, creationflags=_NO_WINDOW)
		raw = (proc.stdout or '').strip() if 0 == proc.returncode else ''
		return HostPathNormalizer(raw).normalize().resolve() if raw else None
	# @used-by :meth:`GlobalIgnoreSyncer.__plan()`
	def __merge_block(self, existing: str) -> str:
		nl = '\r\n' if '\r\n' in existing else '\n'
		block = nl.join((GIT_IGNORE_START, *self.__patterns, GIT_IGNORE_END))
		has_start, has_end = (GIT_IGNORE_START in existing, GIT_IGNORE_END in existing)
		if (not has_start) and (not has_end):
			sep = '' if (not existing) or existing.endswith(('\n', '\r')) else nl
			r = f'{existing}{sep}{block}{nl}'
		elif 1 != existing.count(GIT_IGNORE_START) or 1 != existing.count(GIT_IGNORE_END) or existing.index(GIT_IGNORE_START) > existing.index(GIT_IGNORE_END):
			raise ValueError('Malformed Harness global Git ignore block; user file preserved')
		else:
			r = existing[:existing.index(GIT_IGNORE_START)] + block + existing[existing.index(GIT_IGNORE_END) + len(GIT_IGNORE_END):]
		return r
	# @used-by :meth:`GlobalIgnoreSyncer.sync()`
	def __plan(self, target: Path) -> tuple[str | None, str | None, str | None]:
		if target.exists() and (not target.is_file()):
			r: tuple[str | None, str | None, str | None] = (None, None, 'Global Git ignore target is not a regular file; preserved')
		else:
			try:
				existing = target.read_text(encoding='utf-8') if target.exists() else ''
				r = (existing, self.__merge_block(existing), None)
			except (OSError, UnicodeDecodeError, ValueError) as exc:
				r = (None, None, str(exc))
		return r
	# @used-by :meth:`GlobalIgnoreSyncer.sync()`
	def __resolve_path(self) -> Path:
		if None is not self.__ignore_path:
			r = HostPathNormalizer(str(self.__ignore_path)).normalize().resolve()
		else:
			configured = self.__configured_excludes_file()
			if None is not configured:
				r = configured
			else:
				eff_env = os.environ if None is self.__env else self.__env
				xdg = (eff_env.get('XDG_CONFIG_HOME') or '').strip()
				home = (eff_env.get('HOME') or '').strip()
				r = (HostPathNormalizer(xdg).normalize() / 'git/ignore').resolve() if xdg else ((HostPathNormalizer(home).normalize() / '.config/git/ignore').resolve() if home else (Path.home() / '.config/git/ignore').resolve())
		return r
	# @used-by :meth:`GlobalIgnoreSyncer.sync()`
	@staticmethod
	def __write_verified(target: Path, desired: str) -> str | None:
		payload = desired.encode('utf-8')
		try:
			replace_bytes(target, payload)
			err = None if target.read_bytes() == payload else 'Global Git ignore read-back verification failed'
		except OSError as exc:
			err = str(exc)
		return err
	# @used-by :func:`agent_tools.git_ignore.sync_global_git_ignore()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def sync(self) -> dict:
		target = self.__resolve_path()
		existing, desired, plan_err = self.__plan(target)
		pats = list(self.__patterns)
		if None is not plan_err:
			r = {'valid': False, 'path': target.as_posix(), 'changed': False, 'patterns': pats, 'issues': [{'file': str(target), 'message': plan_err}]}
		elif target.exists() and existing == desired:
			r = {'valid': True, 'path': target.as_posix(), 'changed': False, 'patterns': pats, 'issues': []}
		elif self.__check:
			r = {'valid': False, 'path': target.as_posix(), 'changed': False, 'patterns': pats, 'issues': [{'file': str(target), 'message': 'Global Git ignore file is missing or stale Harness ephemeral block; run harness.py install-global'}]}
		else:
			write_err = self.__write_verified(target, desired or '')
			issues = [] if None is write_err else [{'file': str(target), 'message': write_err}]
			r = {'valid': None is write_err, 'path': target.as_posix(), 'changed': None is write_err, 'patterns': pats, 'issues': issues}
		return r
