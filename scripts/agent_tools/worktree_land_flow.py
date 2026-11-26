# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Split worktree-land into optimistic pre-lease verification and targeted wait":
# https://github.com/dmitry-ai/harness/issues/350
from __future__ import annotations
from pathlib import Path
from .git_gate import GitRepoGate
from .landing_lease import acquire_lease, release_lease
from .polyglot_land import dirty_blocking_main_files
# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
from .worktree_flow import _attach_land_telemetry, _fail_land, _land_under_lease, _merge_and_finalize, _rebase_and_test
# @used-by :func:`_fifo_fallback_land()`
# @used-by :func:`_phase2_commit_under_lease()`
# @used-by :func:`_run_optimistic_loop()`
# @used-by :func:`execute_optimistic_worktree_land()`
def _annotate_land_result(res: dict, *, land_mode: str, optimistic_retries: int, total_test_runs: int) -> dict:
	res['land_mode'] = land_mode
	res['optimistic_retries'] = optimistic_retries
	res['test_runs'] = total_test_runs
	return res
# @used-by :func:`_phase2_commit_under_lease()`
# @used-by :func:`_run_optimistic_loop()`
def _branch_sha(main_repo: Path, target_branch: str) -> str:
	return GitRepoGate(main_repo).git('rev-parse', target_branch).decode('utf-8', errors='replace').strip()
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
# @used-by :func:`_run_optimistic_loop()`
def _fifo_fallback_land(main_repo: Path, wt_path: Path, branch: str, cfg: dict, *, prior_test_runs: int, retries: int, plan: dict | None=None) -> dict:
	lease = acquire_lease(main_repo, owner=cfg['owner'], wait=True, timeout=cfg['wait_timeout'], leases_dir=cfg['leases_dir'])
	if not lease['acquired']:
		r = _annotate_land_result(_fail_land(main_repo, wt_path, branch, 'lease_timeout', 'Timed out waiting for FIFO landing lease', test_runs=prior_test_runs, plan=plan), land_mode='fifo_fallback', optimistic_retries=retries, total_test_runs=prior_test_runs)
	else:
		try:
			raw = _land_under_lease(main_repo, wt_path, branch, target_branch=cfg['target_branch'], run_tests=cfg['run_tests'], push=cfg['push'], remove=cfg['remove'], workers=cfg['workers'], post_merge_fn=cfg['post_merge_fn'], promote_snapshot=cfg['promote_snapshot'], snapshot_store=cfg['snapshot_store'], tag=cfg['tag'], check_dirty_worktree=False, no_tests_reason=cfg['no_tests_reason'])
		finally:
			release_lease(main_repo, owner=lease['owner'], leases_dir=cfg['leases_dir'])
		if 'dirty_main' == raw.get('stage') and None is not plan:
			_attach_land_telemetry(raw, plan)
		r = _annotate_land_result(raw, land_mode='fifo_fallback', optimistic_retries=retries, total_test_runs=prior_test_runs + int(raw.get('test_runs') or 0))
	return r
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
# @used-by :func:`_run_optimistic_loop()`
def _phase2_commit_under_lease(main_repo: Path, wt_path: Path, branch: str, cfg: dict, *, tested_sha: str, attempt: int, total_test_runs: int, test_res: dict | None, plan: dict | None=None) -> tuple[bool, dict | None]:
	lease = acquire_lease(main_repo, owner=cfg['owner'], wait=True, timeout=cfg['wait_timeout'], leases_dir=cfg['leases_dir'])
	if not lease['acquired']:
		r: tuple[bool, dict | None] = (False, _annotate_land_result(_fail_land(main_repo, wt_path, branch, 'lease_timeout', 'Timed out waiting for FIFO landing lease', test_runs=total_test_runs, test_result=test_res, plan=plan), land_mode='optimistic', optimistic_retries=attempt, total_test_runs=total_test_runs))
	else:
		try:
			if dirty_blocking_main_files(main_repo, branch):
				r = (False, _annotate_land_result(_fail_land(main_repo, wt_path, branch, 'dirty_main', 'Main checkout has uncommitted changes', test_runs=total_test_runs, test_result=test_res, plan=plan), land_mode='optimistic', optimistic_retries=attempt, total_test_runs=total_test_runs))
			elif _branch_sha(main_repo, cfg['target_branch']) != tested_sha:
				r = (True, None)
			else:
				eff_health = bool(plan['should_run_post_health']) if None is not plan else cfg['run_tests']
				merged = _merge_and_finalize(main_repo, wt_path, branch, cfg['target_branch'], run_tests=eff_health, push=cfg['push'], remove=cfg['remove'], test_runs=total_test_runs, test_res=test_res, post_merge_fn=cfg['post_merge_fn'], promote_snapshot=cfg['promote_snapshot'], snapshot_store=cfg['snapshot_store'], tag=cfg['tag'], plan=plan)
				r = (False, _annotate_land_result(merged, land_mode='optimistic', optimistic_retries=attempt, total_test_runs=total_test_runs))
		finally:
			release_lease(main_repo, owner=lease['owner'], leases_dir=cfg['leases_dir'])
	return r
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
# @used-by :func:`execute_optimistic_worktree_land()`
def _run_optimistic_loop(main_repo: Path, wt_path: Path, branch: str, cfg: dict, retries: int) -> dict:
	total_runs, r, last_plan = (0, None, None)
	for attempt in range(retries):
		tested_sha = _branch_sha(main_repo, cfg['target_branch'])
		err, runs, test_res, plan = _rebase_and_test(main_repo, wt_path, branch, cfg['target_branch'], run_tests=cfg['run_tests'], workers=cfg['workers'], no_tests_reason=cfg['no_tests_reason'])
		last_plan = plan
		total_runs += runs
		if None is not err:
			r = _annotate_land_result(err, land_mode='optimistic', optimistic_retries=attempt, total_test_runs=total_runs)
			break
		collided, outcome = _phase2_commit_under_lease(main_repo, wt_path, branch, cfg, tested_sha=tested_sha, attempt=attempt, total_test_runs=total_runs, test_res=test_res, plan=plan)
		if not collided:
			r = outcome
			break
	return r if None is not r else _fifo_fallback_land(main_repo, wt_path, branch, cfg, prior_test_runs=total_runs, retries=retries, plan=last_plan)
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
def execute_optimistic_worktree_land(main_repo: Path, wt_path: Path, branch: str, *, target_branch: str='main', run_tests: bool=True, push: bool=False, remove: bool=True, owner: str | None=None, wait_timeout: float=600.0, leases_dir: Path | None=None, workers: int | None=None, post_merge_fn=None, promote_snapshot: bool | None=None, snapshot_store: Path | None=None, tag: bool=False, max_optimistic_retries: int=2, no_tests_reason: str | None=None) -> dict:
	if GitRepoGate(wt_path).git('status', '--porcelain').strip():
		r = _annotate_land_result(_fail_land(main_repo, wt_path, branch, 'dirty_worktree', 'Worktree has uncommitted changes'), land_mode='optimistic', optimistic_retries=0, total_test_runs=0)
	else:
		cfg = {'leases_dir': leases_dir, 'no_tests_reason': no_tests_reason, 'owner': owner, 'post_merge_fn': post_merge_fn, 'promote_snapshot': promote_snapshot, 'push': push, 'remove': remove, 'run_tests': run_tests, 'snapshot_store': snapshot_store, 'tag': tag, 'target_branch': target_branch, 'wait_timeout': wait_timeout, 'workers': workers}
		r = _run_optimistic_loop(main_repo, wt_path, branch, cfg, max(0, int(max_optimistic_retries)))
	return r