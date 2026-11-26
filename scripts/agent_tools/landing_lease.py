# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.LandingLease import DEFAULT_POLL_SECONDS, DEFAULT_TTL_SECONDS, LandingLease
from Df.Harness.lib.process import dfh_pid_is_alive
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :meth:`Df.Harness.TestRunner.WorkerSemaphore.WorkerSemaphore.__read_live_slots()`
def _pid_is_alive(pid: int) -> bool:
	return dfh_pid_is_alive(pid)
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_land_acquire()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_acquire_and_release_lifecycle()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_fifo_ordering_prevents_starvation()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_stale_dead_pid_and_expired_ttl_evicted()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_wait_timeout_cleans_up_queue_entry()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_dirty_worktree_fails_fast_without_acquiring_lease()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_blocks_when_turn_touches_leased_repo_or_worktree()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_bypasses_foreign_lease_on_readonly_and_noncode_turns()`
# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_wait_repo_reacts_to_lease_release_dead_pid_and_clean_tree()`
def acquire_lease(repo: Path | str, owner: str | None=None, *, wait: bool=False, timeout: float=600.0, ttl: float=DEFAULT_TTL_SECONDS, poll_interval: float=DEFAULT_POLL_SECONDS, pid: int | None=None, leases_dir: Path | None=None) -> dict:
	return LandingLease(repo, owner, leases_dir=leases_dir).acquire(wait=wait, timeout=timeout, ttl=ttl, poll_interval=poll_interval, pid=pid)
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_land_status()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_acquire_and_release_lifecycle()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_wait_timeout_cleans_up_queue_entry()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_concurrent_main_advance_retries_optimistically_and_lands()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_optimistic_phase1_runs_tests_without_holding_fifo_lease()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_repeated_main_collisions_fall_back_to_fifo_lease()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_worktree_land_aborts_when_tests_fail()`
def lease_status(repo: Path | str, *, leases_dir: Path | None=None) -> dict:
	return LandingLease(repo, leases_dir=leases_dir).status()
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_land_release()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_acquire_and_release_lifecycle()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_fifo_ordering_prevents_starvation()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_stale_dead_pid_and_expired_ttl_evicted()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_wait_timeout_cleans_up_queue_entry()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_dirty_worktree_fails_fast_without_acquiring_lease()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_blocks_when_turn_touches_leased_repo_or_worktree()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_bypasses_foreign_lease_on_readonly_and_noncode_turns()`
# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_wait_repo_reacts_to_lease_release_dead_pid_and_clean_tree()`
def release_lease(repo: Path | str, owner: str | None=None, *, force: bool=False, leases_dir: Path | None=None) -> dict:
	return LandingLease(repo, owner, leases_dir=leases_dir).release(force=force)
