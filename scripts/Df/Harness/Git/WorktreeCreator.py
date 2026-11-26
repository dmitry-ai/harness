# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.lib.worktree import dfh_git_exec, dfh_prepare_worktrees_base_dir
import re
_SAFE_TASK_RE = re.compile(r'[^A-Za-z0-9_.-]+')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreeCreator:
	# @used-by :func:`agent_tools.worktree_flow.worktree_begin()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def __init__(self, repo: Path | str, task_id: str, *, base_ref: str='main', worktrees_dir: Path | str | None=None, git_exec_fn=None) -> None:
		self.__repo = Path(repo).resolve()
		self.__task_id = task_id
		self.__base_ref = base_ref
		self.__worktrees_dir = worktrees_dir
		self.__git_exec = git_exec_fn if None is not git_exec_fn else dfh_git_exec
	# @used-by :meth:`WorktreeCreator.begin()`
	@staticmethod
	def __current_branch(repo: Path) -> str:
		proc = RepoGate(repo).run_read(['rev-parse', '--abbrev-ref', 'HEAD'], check=False)
		return proc.stdout.decode('utf-8', errors='replace').strip() if 0 == proc.returncode else ''
	# @used-by :meth:`WorktreeCreator.begin()`
	def __safe_task_id(self) -> str:
		clean = _SAFE_TASK_RE.sub('-', str(self.__task_id or '').strip()).strip('-.')
		if not clean:
			raise ValueError('A non-empty task identifier is required')
		return clean[:48]
	# @used-by :func:`agent_tools.worktree_flow.worktree_begin()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def begin(self) -> dict:
		main_repo = RepoGate(self.__repo).main_repo()
		safe_id = self.__safe_task_id()
		branch = f'task/{safe_id}'
		base_dir, ignore_info = dfh_prepare_worktrees_base_dir(main_repo, worktrees_dir=self.__worktrees_dir)
		wt_path = (base_dir / safe_id).resolve()
		if not (wt_path / '.git').exists():
			proc = self.__git_exec(main_repo, 'worktree', 'add', '-b', branch, str(wt_path), self.__base_ref)
			if 0 != proc.returncode:
				raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f'git worktree add failed for {wt_path}')
		head = RepoGate(wt_path).git('rev-parse', 'HEAD').decode('utf-8', errors='replace').strip()
		return {'valid': True, 'main_repo': main_repo.as_posix(), 'worktree': wt_path.as_posix(), 'branch': self.__current_branch(wt_path) or branch, 'base_ref': self.__base_ref, 'head': head, 'enclosing_ignore': ignore_info}
