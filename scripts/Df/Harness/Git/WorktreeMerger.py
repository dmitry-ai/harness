# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.CommitTagger import CommitTagger
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.Git.RepoHealthChecker import RepoHealthChecker
from Df.Harness.Git.WorktreeCleaner import WorktreeCleaner
from Df.Harness.lib.worktree import dfh_attach_land_telemetry, dfh_fail_land, dfh_git_exec
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreeMerger:
	# @used-by :func:`agent_tools.worktree_flow._merge_and_finalize()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__land_under_lease()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__phase2_commit()`
	def __init__(self, main_repo: Path, wt_path: Path, branch: str, target_branch: str, *, run_tests: bool=True, push: bool, remove: bool, test_runs: int, test_res: dict | None, post_merge_fn, promote_snapshot: bool | None=None, snapshot_store: Path | None=None, tag: bool=False, plan: dict | None=None, git_exec_fn=None, cleanup_fn=None, health_fn=None) -> None:
		self.__main_repo, self.__wt_path = (main_repo, wt_path)
		self.__branch, self.__target_branch = (branch, target_branch)
		self.__run_tests, self.__push, self.__remove = (run_tests, push, remove)
		self.__test_runs, self.__test_res = (test_runs, test_res)
		self.__post_merge_fn = post_merge_fn
		self.__promote_snapshot, self.__snapshot_store = (promote_snapshot, snapshot_store)
		self.__tag, self.__plan = (tag, plan)
		self.__git_exec = git_exec_fn if None is not git_exec_fn else dfh_git_exec
		self.__cleanup = cleanup_fn
		self.__health = health_fn
	# @used-by :meth:`WorktreeMerger.__push_and_finish()`
	def __cleanup_worktree(self) -> dict | None:
		if not self.__remove:
			r = None
		elif None is not self.__cleanup:
			r = self.__cleanup(self.__main_repo, self.__wt_path, force=True)
		else:
			r = WorktreeCleaner(self.__main_repo, self.__wt_path, force=True, git_exec_fn=self.__git_exec).cleanup()
		return r
	# @used-by :meth:`WorktreeMerger.__post_merge_checks()`
	def __maybe_promote_snapshot(self, base_ref: str | None) -> dict | None:
		from agent_tools.runtime_snapshot import is_harness_code_repo, promote_runtime_snapshot
		should = self.__promote_snapshot if None is not self.__promote_snapshot else is_harness_code_repo(self.__main_repo)
		return promote_runtime_snapshot(self.__main_repo, store_dir=self.__snapshot_store, base_ref=base_ref) if should else None
	# @used-by :meth:`WorktreeMerger.merge()`
	def __post_merge_checks(self, base_ref: str | None) -> tuple[dict | None, str | None, str | None]:
		snap = self.__maybe_promote_snapshot(base_ref)
		if None is not snap and (not snap.get('valid')):
			r = (snap, 'snapshot_promote', str(snap.get('error') or 'Runtime snapshot promotion failed'))
		elif self.__run_tests:
			health = self.__health(self.__main_repo) if None is not self.__health else RepoHealthChecker(self.__main_repo).check()
			r = (snap, None, None) if health.get('ok') else (snap, 'post_land_health', str(health.get('error') or 'Post-land repository health check failed'))
		else:
			r = (snap, None, None)
		return r
	# @used-by :meth:`WorktreeMerger.merge()`
	def __push_and_finish(self, snap: dict | None) -> dict:
		p_err = ''
		if self.__push:
			p_proc = self.__git_exec(self.__main_repo, 'push')
			p_err = '' if 0 == p_proc.returncode else (p_proc.stderr.strip() or p_proc.stdout.strip())
		if p_err:
			r = dfh_fail_land(self.__main_repo, self.__wt_path, self.__branch, 'push', p_err, test_runs=self.__test_runs, test_result=self.__test_res, plan=self.__plan)
		else:
			head = RepoGate(self.__main_repo).git('rev-parse', 'HEAD').decode('utf-8', errors='replace').strip()
			tag_name = CommitTagger(self.__main_repo, commit=head, push=self.__push).ensure()['tag'] if self.__tag else None
			cleanup = self.__cleanup_worktree()
			removed = bool(cleanup['valid']) if None is not cleanup else False
			ok_land = None is cleanup or removed
			r = dfh_attach_land_telemetry({'valid': ok_land, 'landed': True, 'main_repo': self.__main_repo.as_posix(), 'worktree': self.__wt_path.as_posix(), 'branch': self.__branch, 'target_branch': self.__target_branch, 'head': head, 'tag': tag_name, 'test_runs': self.__test_runs, 'test_result': self.__test_res, 'pushed': self.__push, 'removed': removed, 'runtime_snapshot': snap}, self.__plan)
			if (not ok_land) and None is not cleanup:
				r.update(stage='worktree_cleanup', error=str(cleanup.get('error') or 'Worktree cleanup failed'), cleanup=cleanup)
		return r
	# @used-by :func:`agent_tools.worktree_flow._merge_and_finalize()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__land_under_lease()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__phase2_commit()`
	def merge(self) -> dict:
		prev_head = RepoGate(self.__main_repo).git('rev-parse', 'HEAD').decode('utf-8', errors='replace').strip()
		ff = self.__git_exec(self.__main_repo, 'merge', '--ff-only', self.__branch)
		if 0 != ff.returncode:
			r = dfh_fail_land(self.__main_repo, self.__wt_path, self.__branch, 'ff_merge', ff.stderr.strip() or ff.stdout.strip(), test_runs=self.__test_runs, test_result=self.__test_res, plan=self.__plan)
		else:
			if self.__post_merge_fn:
				self.__post_merge_fn(self.__main_repo)
			snap, err_stage, err_msg = self.__post_merge_checks(prev_head)
			if None is not err_stage:
				r = dfh_fail_land(self.__main_repo, self.__wt_path, self.__branch, err_stage, err_msg or 'Post-merge verification failed', test_runs=self.__test_runs, test_result=self.__test_res, plan=self.__plan)
			else:
				r = self.__push_and_finish(snap)
		return r
