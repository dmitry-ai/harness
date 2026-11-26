# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Git.WorktreeLander import WorktreeLander
# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
def execute_optimistic_worktree_land(main_repo: Path, wt_path: Path, branch: str, *, target_branch: str='main', run_tests: bool=True, push: bool=False, remove: bool=True, owner: str | None=None, wait_timeout: float=600.0, leases_dir: Path | None=None, workers: int | None=None, post_merge_fn=None, promote_snapshot: bool | None=None, snapshot_store: Path | None=None, tag: bool=False, max_optimistic_retries: int=2, no_tests_reason: str | None=None, git_exec_fn=None, cleanup_fn=None, health_fn=None, polyglot_test_fn=None) -> dict:
	cfg = {'cleanup_fn': cleanup_fn, 'git_exec_fn': git_exec_fn, 'health_fn': health_fn, 'leases_dir': leases_dir, 'no_tests_reason': no_tests_reason, 'owner': owner, 'polyglot_test_fn': polyglot_test_fn, 'post_merge_fn': post_merge_fn, 'promote_snapshot': promote_snapshot, 'push': push, 'remove': remove, 'run_tests': run_tests, 'snapshot_store': snapshot_store, 'tag': tag, 'target_branch': target_branch, 'wait_timeout': wait_timeout, 'workers': workers}
	return WorktreeLander(main_repo, wt_path, branch, cfg, max_optimistic_retries=max_optimistic_retries).land()
