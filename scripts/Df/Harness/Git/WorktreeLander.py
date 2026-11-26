# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.DirtyMainChecker import DirtyMainChecker
from Df.Harness.Git.LandingLease import LandingLease
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.Git.WorktreeMerger import WorktreeMerger
from Df.Harness.Git.WorktreeRebaseVerifier import WorktreeRebaseVerifier
from Df.Harness.lib.worktree import dfh_attach_land_telemetry, dfh_fail_land
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreeLander:
	# @used-by :func:`agent_tools.worktree_land_flow.execute_optimistic_worktree_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def __init__(self, main_repo: Path, wt_path: Path, branch: str, cfg: dict, *, max_optimistic_retries: int=2) -> None:
		self.__main_repo = main_repo
		self.__wt_path = wt_path
		self.__branch = branch
		self.__cfg = cfg
		self.__retries = max(0, int(max_optimistic_retries))
	# @used-by :meth:`WorktreeLander.__fifo_fallback()`
	# @used-by :meth:`WorktreeLander.__phase2_commit()`
	# @used-by :meth:`WorktreeLander.__run_optimistic_loop()`
	# @used-by :meth:`WorktreeLander.land()`
	@staticmethod
	def __annotate(res: dict, *, land_mode: str, optimistic_retries: int, total_test_runs: int) -> dict:
		res['land_mode'] = land_mode
		res['optimistic_retries'] = optimistic_retries
		res['test_runs'] = total_test_runs
		return res
	# @used-by :meth:`WorktreeLander.__phase2_commit()`
	# @used-by :meth:`WorktreeLander.__run_optimistic_loop()`
	def __branch_sha(self) -> str:
		return RepoGate(self.__main_repo).git('rev-parse', self.__cfg['target_branch']).decode('utf-8', errors='replace').strip()
	# @used-by :meth:`WorktreeLander.__run_optimistic_loop()`
	def __fifo_fallback(self, *, prior_test_runs: int, plan: dict | None=None) -> dict:
		cfg = self.__cfg
		lease_mgr = LandingLease(self.__main_repo, owner=cfg['owner'], leases_dir=cfg['leases_dir'])
		lease = lease_mgr.acquire(wait=True, timeout=cfg['wait_timeout'])
		if not lease['acquired']:
			r = self.__annotate(dfh_fail_land(self.__main_repo, self.__wt_path, self.__branch, 'lease_timeout', 'Timed out waiting for FIFO landing lease', test_runs=prior_test_runs, plan=plan), land_mode='fifo_fallback', optimistic_retries=self.__retries, total_test_runs=prior_test_runs)
		else:
			try:
				raw = self.__land_under_lease(check_dirty_worktree=False)
			finally:
				LandingLease(self.__main_repo, owner=lease['owner'], leases_dir=cfg['leases_dir']).release()
			if 'dirty_main' == raw.get('stage') and None is not plan:
				dfh_attach_land_telemetry(raw, plan)
			r = self.__annotate(raw, land_mode='fifo_fallback', optimistic_retries=self.__retries, total_test_runs=prior_test_runs + int(raw.get('test_runs') or 0))
		return r
	# @used-by :meth:`WorktreeLander.__fifo_fallback()`
	def __land_under_lease(self, *, check_dirty_worktree: bool=True) -> dict:
		cfg = self.__cfg
		if check_dirty_worktree and RepoGate(self.__wt_path).git('status', '--porcelain').strip():
			r = dfh_fail_land(self.__main_repo, self.__wt_path, self.__branch, 'dirty_worktree', 'Worktree has uncommitted changes')
		elif DirtyMainChecker(self.__main_repo, self.__branch).find_blocking():
			r = dfh_fail_land(self.__main_repo, self.__wt_path, self.__branch, 'dirty_main', 'Main checkout has uncommitted changes')
		else:
			err, test_runs, test_res, plan = WorktreeRebaseVerifier(self.__main_repo, self.__wt_path, self.__branch, cfg['target_branch'], run_tests=cfg['run_tests'], workers=cfg['workers'], no_tests_reason=cfg['no_tests_reason'], git_exec_fn=cfg.get('git_exec_fn'), polyglot_test_fn=cfg.get('polyglot_test_fn')).verify()
			eff_health = bool(plan['should_run_post_health']) if None is not plan else cfg['run_tests']
			r = err if None is not err else WorktreeMerger(self.__main_repo, self.__wt_path, self.__branch, cfg['target_branch'], run_tests=eff_health, push=cfg['push'], remove=cfg['remove'], test_runs=test_runs, test_res=test_res, post_merge_fn=cfg['post_merge_fn'], promote_snapshot=cfg['promote_snapshot'], snapshot_store=cfg['snapshot_store'], tag=cfg['tag'], plan=plan, git_exec_fn=cfg.get('git_exec_fn'), cleanup_fn=cfg.get('cleanup_fn'), health_fn=cfg.get('health_fn')).merge()
		return r
	# @used-by :meth:`WorktreeLander.__run_optimistic_loop()`
	def __phase2_commit(self, *, tested_sha: str, attempt: int, total_test_runs: int, test_res: dict | None, plan: dict | None=None) -> tuple[bool, dict | None]:
		cfg = self.__cfg
		lease = LandingLease(self.__main_repo, owner=cfg['owner'], leases_dir=cfg['leases_dir']).acquire(wait=True, timeout=cfg['wait_timeout'])
		if not lease['acquired']:
			r: tuple[bool, dict | None] = (False, self.__annotate(dfh_fail_land(self.__main_repo, self.__wt_path, self.__branch, 'lease_timeout', 'Timed out waiting for FIFO landing lease', test_runs=total_test_runs, test_result=test_res, plan=plan), land_mode='optimistic', optimistic_retries=attempt, total_test_runs=total_test_runs))
		else:
			try:
				if DirtyMainChecker(self.__main_repo, self.__branch).find_blocking():
					r = (False, self.__annotate(dfh_fail_land(self.__main_repo, self.__wt_path, self.__branch, 'dirty_main', 'Main checkout has uncommitted changes', test_runs=total_test_runs, test_result=test_res, plan=plan), land_mode='optimistic', optimistic_retries=attempt, total_test_runs=total_test_runs))
				elif self.__branch_sha() != tested_sha:
					r = (True, None)
				else:
					eff_health = bool(plan['should_run_post_health']) if None is not plan else cfg['run_tests']
					merged = WorktreeMerger(self.__main_repo, self.__wt_path, self.__branch, cfg['target_branch'], run_tests=eff_health, push=cfg['push'], remove=cfg['remove'], test_runs=total_test_runs, test_res=test_res, post_merge_fn=cfg['post_merge_fn'], promote_snapshot=cfg['promote_snapshot'], snapshot_store=cfg['snapshot_store'], tag=cfg['tag'], plan=plan, git_exec_fn=cfg.get('git_exec_fn'), cleanup_fn=cfg.get('cleanup_fn'), health_fn=cfg.get('health_fn')).merge()
					r = (False, self.__annotate(merged, land_mode='optimistic', optimistic_retries=attempt, total_test_runs=total_test_runs))
			finally:
				LandingLease(self.__main_repo, owner=lease['owner'], leases_dir=cfg['leases_dir']).release()
		return r
	# @used-by :meth:`WorktreeLander.land()`
	def __run_optimistic_loop(self) -> dict:
		total_runs, r, last_plan = (0, None, None)
		cfg = self.__cfg
		for attempt in range(self.__retries):
			tested_sha = self.__branch_sha()
			err, runs, test_res, plan = WorktreeRebaseVerifier(self.__main_repo, self.__wt_path, self.__branch, cfg['target_branch'], run_tests=cfg['run_tests'], workers=cfg['workers'], no_tests_reason=cfg['no_tests_reason'], git_exec_fn=cfg.get('git_exec_fn'), polyglot_test_fn=cfg.get('polyglot_test_fn')).verify()
			last_plan = plan
			total_runs += runs
			if None is not err:
				r = self.__annotate(err, land_mode='optimistic', optimistic_retries=attempt, total_test_runs=total_runs)
				break
			collided, outcome = self.__phase2_commit(tested_sha=tested_sha, attempt=attempt, total_test_runs=total_runs, test_res=test_res, plan=plan)
			if not collided:
				r = outcome
				break
		return r if None is not r else self.__fifo_fallback(prior_test_runs=total_runs, plan=last_plan)
	# @used-by :func:`agent_tools.worktree_land_flow.execute_optimistic_worktree_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def land(self) -> dict:
		if RepoGate(self.__wt_path).git('status', '--porcelain').strip():
			r = self.__annotate(dfh_fail_land(self.__main_repo, self.__wt_path, self.__branch, 'dirty_worktree', 'Worktree has uncommitted changes'), land_mode='optimistic', optimistic_retries=0, total_test_runs=0)
		else:
			r = self.__run_optimistic_loop()
		return r
