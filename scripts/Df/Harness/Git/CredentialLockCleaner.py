# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.state import df_is_windows
from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
import os
import subprocess
import time
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CredentialLockCleaner:
	# @used-by :func:`agent_tools.git_gate.cleanup_stale_credential_locks()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def __init__(self, max_age_seconds: float=10.0, *, candidates: list[Path] | tuple[Path, ...] | None=None, check_running: bool=True) -> None:
		self.__max_age = max_age_seconds
		self.__candidates = candidates
		self.__check_running = check_running
	# @used-by :meth:`CredentialLockCleaner.clean()`
	def __collect_candidates(self) -> list[Path]:
		if None is not self.__candidates:
			r = [HostPathNormalizer(p).normalize() for p in self.__candidates]
		else:
			from agent_tools.path_registry import tool_list
			roots = [Path(h) for h in tool_list('git_credential_lock_homes')]
			try:
				roots.insert(0, Path.home())
			except RuntimeError:
				pass
			if os.environ.get('HOME'):
				roots.append(HostPathNormalizer(os.environ['HOME']).normalize())
			r = self.__expand_lock_paths(roots, tuple(tool_list('git_credential_lock_relpaths')))
		return r
	# @used-by :meth:`CredentialLockCleaner.__collect_candidates()`
	@staticmethod
	def __expand_lock_paths(roots: list[Path], lock_rels: tuple[str, ...]) -> list[Path]:
		seen: set[str] = set()
		out: list[Path] = []
		for base in roots:
			for rel in lock_rels:
				cand = base / rel
				key = str(cand).replace('\\', '/').lower()
				if key not in seen:
					seen.add(key)
					out.append(cand)
		return out
	# @used-by :meth:`CredentialLockCleaner.clean()`
	def __expired_locks(self, existing: list[Path]) -> list[Path]:
		now = time.time()
		expired: list[Path] = []
		for lp in existing:
			try:
				if self.__max_age <= now - lp.stat().st_mtime:
					expired.append(lp)
			except OSError:
				continue
		return expired
	# @used-by :meth:`CredentialLockCleaner.clean()`
	def __is_store_running(self) -> bool:
		r = False
		if self.__check_running and df_is_windows():
			proc = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq git-credential-store.exe', '/NH'], stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False, creationflags=_NO_WINDOW)
			r = 'git-credential-store' in (proc.stdout or '').lower()
		return r
	# @used-by :func:`agent_tools.git_gate.cleanup_stale_credential_locks()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def clean(self) -> list[str]:
		existing = [lp for lp in self.__collect_candidates() if lp.is_file()]
		r: list[str] = []
		if existing:
			expired = self.__expired_locks(existing)
			if expired and (not self.__is_store_running()):
				for lp in expired:
					try:
						lp.unlink(missing_ok=True)
						r.append(str(lp))
					except OSError:
						continue
		return r
