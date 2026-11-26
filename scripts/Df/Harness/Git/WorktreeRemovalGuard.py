# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Git.WorktreeLockFinder import WorktreeLockFinder
import os
import stat
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreeRemovalGuard:
	# @used-by :func:`agent_tools.worktree_guard.remove_worktree_fail_closed()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCleaner.WorktreeCleaner.cleanup()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	def __init__(self, main_repo: Path, wt_path: Path, *, force: bool, git_exec_fn, lock_finder_fn=None) -> None:
		self.__main_repo = main_repo
		self.__wt_path = wt_path
		self.__force = force
		self.__git_exec = git_exec_fn
		self.__lock_finder = lock_finder_fn
	# @used-by :meth:`WorktreeRemovalGuard.remove()`
	def __find_holders(self) -> list[dict[str, Any]]:
		return self.__lock_finder(self.__wt_path) if None is not self.__lock_finder else WorktreeLockFinder(self.__wt_path).find()
	# @used-by :meth:`WorktreeRemovalGuard.remove()`
	@staticmethod
	def __format_error(git_err: str, holders: list[dict[str, Any]], rem_errors: list[str]) -> str:
		parts: list[str] = []
		if git_err:
			parts.append(git_err)
		if holders:
			desc = ', '.join((f"{h['name']}(PID {h['pid']})" for h in holders[:4]))
			parts.append(f'locking processes: {desc}')
		if rem_errors:
			parts.append('; '.join(rem_errors[:3]))
		return ' | '.join(parts) if parts else 'Worktree directory remained present after cleanup'
	# @used-by :meth:`WorktreeRemovalGuard.remove()`
	def __remove_tree_strict(self) -> list[str]:
		errors: list[str] = []
		for dirpath, dirnames, filenames in os.walk(self.__wt_path, topdown=False):
			base = Path(dirpath)
			for name in filenames:
				self.__unlink_strict(base / name, False, errors)
			for name in dirnames:
				self.__unlink_strict(base / name, True, errors)
		if self.__wt_path.exists():
			self.__unlink_strict(self.__wt_path, True, errors)
		return errors
	# @used-by :meth:`WorktreeRemovalGuard.__remove_tree_strict()`
	@staticmethod
	def __unlink_strict(target: Path, is_dir: bool, errors: list[str]) -> None:
		try:
			target.rmdir() if is_dir else target.unlink()
		except PermissionError:
			try:
				os.chmod(target, stat.S_IWRITE)
				target.rmdir() if is_dir else target.unlink()
			except OSError as exc:
				errors.append(f'{target.as_posix()}: {exc}')
		except OSError as exc:
			errors.append(f'{target.as_posix()}: {exc}')
	# @used-by :func:`agent_tools.worktree_guard.remove_worktree_fail_closed()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCleaner.WorktreeCleaner.cleanup()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	def remove(self) -> dict[str, Any]:
		git_err, rem_errors = ('', [])
		if self.__wt_path.exists():
			if (self.__wt_path / '.git').exists():
				args = ['worktree', 'remove', '--force', str(self.__wt_path)] if self.__force else ['worktree', 'remove', str(self.__wt_path)]
				proc = self.__git_exec(self.__main_repo, *args)
				if 0 != proc.returncode:
					git_err = (proc.stderr or proc.stdout or f'git worktree remove exited {proc.returncode}').strip()
			elif not self.__find_holders():
				rem_errors = self.__remove_tree_strict()
		ok = (not self.__wt_path.exists()) and (not git_err) and (not rem_errors)
		holders = [] if ok else self.__find_holders()
		err = '' if ok else self.__format_error(git_err, holders, rem_errors)
		return {'ok': ok, 'error': err, 'removal_errors': rem_errors, 'locking_processes': holders}
