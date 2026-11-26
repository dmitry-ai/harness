# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
from agent_tools.storage import replace_bytes
import os
import subprocess
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreeExcludeManager:
	# @used-by :func:`Df.Harness.lib.worktree.dfh_prepare_worktrees_base_dir()`
	# @used-by :func:`agent_tools.git_ignore.ensure_worktree_dir_ignored()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def __init__(self, base_dir: Path | str) -> None:
		self.__target = HostPathNormalizer(str(base_dir)).normalize().resolve()
	# @used-by :meth:`WorktreeExcludeManager.ensure()`
	@staticmethod
	def __append_pattern(exclude_file: Path, pattern: str) -> bool:
		existing = exclude_file.read_text(encoding='utf-8') if exclude_file.is_file() else ''
		if pattern in existing.splitlines():
			r = False
		else:
			nl = '\r\n' if '\r\n' in existing else '\n'
			sep = '' if (not existing) or existing.endswith(('\n', '\r')) else nl
			replace_bytes(exclude_file, f'{existing}{sep}{pattern}{nl}'.encode('utf-8'))
			r = True
		return r
	# @used-by :meth:`WorktreeExcludeManager.ensure()`
	def __detect_enclosing(self) -> tuple[Path, Path, str] | None:
		proc = self.__git_read(self.__target, 'rev-parse', '--show-toplevel', '--git-common-dir')
		lines = [ln.strip() for ln in (proc.stdout or '').splitlines() if ln.strip()] if 0 == proc.returncode else []
		if 2 > len(lines):
			r = None
		else:
			toplevel = HostPathNormalizer(lines[0]).normalize().resolve()
			raw_common = HostPathNormalizer(lines[1]).normalize()
			common = raw_common.resolve() if raw_common.is_absolute() else (self.__target / raw_common).resolve()
			try:
				rel = self.__target.relative_to(toplevel).as_posix()
			except ValueError:
				rel = ''
			r = (toplevel, common, rel) if rel and '.' != rel else None
		return r
	# @used-by :meth:`WorktreeExcludeManager.__detect_enclosing()`
	# @used-by :meth:`WorktreeExcludeManager.__tracked_entries()`
	# @used-by :meth:`WorktreeExcludeManager.ensure()`
	@staticmethod
	def __git_read(cwd: Path, *args: str) -> subprocess.CompletedProcess:
		return subprocess.run(['git', '--no-optional-locks', '-C', str(cwd), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}, check=False, creationflags=_NO_WINDOW)
	# @used-by :meth:`WorktreeExcludeManager.ensure()`
	def __tracked_entries(self, toplevel: Path, rel: str) -> tuple[list[dict], list[str], list[str]]:
		proc = self.__git_read(toplevel, '-c', 'core.quotePath=false', 'ls-files', '--stage', '--', rel)
		entries, gitlinks, warnings = ([], [], [])
		if 0 == proc.returncode:
			for line in (proc.stdout or '').splitlines():
				meta, sep, path = line.partition('\t')
				parts = meta.split()
				if sep and 2 <= len(parts) and path:
					mode, sha = (parts[0], parts[1])
					entries.append({'mode': mode, 'sha': sha, 'path': path})
					if '160000' == mode:
						gitlinks.append(path)
					warnings.append(f'Enclosing repo {toplevel.as_posix()} already tracks {path} (mode {mode}); untrack via: git -C "{toplevel.as_posix()}" rm --cached "{path}"')
		return (entries, gitlinks, warnings)
	# @used-by :func:`Df.Harness.lib.worktree.dfh_prepare_worktrees_base_dir()`
	# @used-by :func:`agent_tools.git_ignore.ensure_worktree_dir_ignored()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def ensure(self) -> dict:
		self.__target.mkdir(parents=True, exist_ok=True)
		enclosing = self.__detect_enclosing()
		if None is enclosing:
			r = {'enclosing_repo': None, 'already_ignored': False, 'excluded': False, 'exclude_file': None, 'pattern': None, 'tracked_entries': [], 'tracked_gitlinks': [], 'warnings': []}
		else:
			toplevel, common_dir, rel = enclosing
			pattern = f'/{rel}/'
			exclude_file = common_dir / 'info/exclude'
			already = 0 == self.__git_read(toplevel, 'check-ignore', '-q', '--no-index', '--', f'{rel}/probe').returncode
			excluded = False if already else self.__append_pattern(exclude_file, pattern)
			entries, gitlinks, warnings = self.__tracked_entries(toplevel, rel)
			r = {'enclosing_repo': toplevel.as_posix(), 'already_ignored': already, 'excluded': excluded, 'exclude_file': exclude_file.as_posix(), 'pattern': pattern, 'tracked_entries': entries, 'tracked_gitlinks': gitlinks, 'warnings': warnings}
		return r
