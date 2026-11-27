# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add host test-worker semaphore and worksteal pytest mode":
# https://github.com/dmitry-ai/harness/issues/354
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.TestRunner.WorkerSemaphore import WorkerSemaphore
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :func:`worker_slot_budget()`
# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_worker_semaphore_bounds_total_slots_and_reclaims_dead_and_expired()`
def acquire_worker_slots(requested: int, *, max_slots: int | None=None, slots_dir: Path | str | None=None, ttl_s: float=600.0, wait_timeout: float=2.0, poll_interval: float=0.1) -> dict[str, Any]:
	return WorkerSemaphore(requested, max_slots=max_slots, slots_dir=slots_dir, ttl_s=ttl_s, wait_timeout=wait_timeout, poll_interval=poll_interval).acquire()
# @used-by unused
def default_max_slots() -> int:
	return WorkerSemaphore.default_max_slots()
# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_worker_semaphore_bounds_total_slots_and_reclaims_dead_and_expired()`
def default_slots_dir() -> Path:
	return WorkerSemaphore.default_slots_dir()
# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_worker_semaphore_bounds_total_slots_and_reclaims_dead_and_expired()`
def release_worker_slots(lease: dict[str, Any] | None) -> bool:
	return WorkerSemaphore.release(lease)
# @used-by :func:`agent_tools.parallel_runner.run_parallel_tests()`
# @used-by :func:`agent_tools.suite_runner.run_test_suite()`
# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_nested_worker_slot_budget_skips_self_throttling_against_parent_lease()`
def worker_slot_budget(requested: int, *, max_slots: int | None=None, slots_dir: Path | str | None=None, ttl_s: float=600.0, wait_timeout: float=2.0, poll_interval: float=0.1):
	return WorkerSemaphore.slot_budget(requested, max_slots=max_slots, slots_dir=slots_dir, ttl_s=ttl_s, wait_timeout=wait_timeout, poll_interval=poll_interval, acquire_fn=acquire_worker_slots)
