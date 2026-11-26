# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.Git.WorktreeRemovalGuard import WorktreeRemovalGuard
from Df.Harness.lib.worktree import dfh_git_exec
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreeCleaner:
	# @used-by :func:`agent_tools.worktree_flow.worktree_cleanup()`
	# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__cleanup_worktree()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	def __init__(self, repo: Path | str, target: Path | str, *, force: bool=False, git_exec_fn=None, lock_finder_fn=None) -> None:
		self.__repo = Path(repo).resolve()
		self.__target = Path(target).resolve()
		self.__force = force
		self.__git_exec = git_exec_fn if None is not git_exec_fn else dfh_git_exec
		self.__lock_finder = lock_finder_fn
	# @used-by :meth:`WorktreeCleaner.cleanup()`
	@staticmethod
	def __current_branch(repo: Path) -> str:
		proc = RepoGate(repo).run_read(['rev-parse', '--abbrev-ref', 'HEAD'], check=False)
		return proc.stdout.decode('utf-8', errors='replace').strip() if 0 == proc.returncode else ''
	# @used-by :func:`agent_tools.worktree_flow.worktree_cleanup()`
	# @used-by :func:`git_fixture_cache._cleanup_templates()`
	# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__cleanup_worktree()`
	# @used-by :meth:`agent_tools.text_browser.ManagedHeadlessShell.close()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	def cleanup(self) -> dict:
		main_repo = RepoGate(self.__repo).main_repo()
		branch = self.__current_branch(self.__target) if (self.__target / '.git').exists() else ''
		outcome = WorktreeRemovalGuard(main_repo, self.__target, force=self.__force, git_exec_fn=self.__git_exec, lock_finder_fn=self.__lock_finder).remove()
		self.__git_exec(main_repo, 'worktree', 'prune')
		branch_deleted = False
		if outcome['ok'] and branch and branch.startswith('task/'):
			branch_deleted = 0 == self.__git_exec(main_repo, 'branch', '-D' if self.__force else '-d', branch).returncode
		return {'valid': outcome['ok'], 'main_repo': main_repo.as_posix(), 'worktree': self.__target.as_posix(), 'branch': branch, 'branch_deleted': branch_deleted, 'error': outcome['error'], 'removal_errors': outcome['removal_errors'], 'locking_processes': outcome['locking_processes']}
