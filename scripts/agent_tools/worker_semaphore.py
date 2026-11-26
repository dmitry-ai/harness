# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add host test-worker semaphore and worksteal pytest mode":
# https://github.com/dmitry-ai/harness/issues/354
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Any
import json
import os
import time
import uuid
from .landing_lease import _pid_is_alive
from .path_registry import project_paths
from .runtime import PRIMARY
from .storage import locked, replace_bytes
# @used-by :func:`_try_reserve_once()`
def _read_live_slots(path: Path, now: float) -> int:
	r = 0
	try:
		raw = json.loads(path.read_text(encoding='utf-8'))
		if isinstance(raw, dict):
			exp = float(raw.get('expires_at') or 0.0)
			slots = int(raw.get('slots') or 0)
			pid = raw.get('pid')
			if now < exp and 0 < slots and (not isinstance(pid, int) or _pid_is_alive(pid)):
				r = slots
	except (OSError, TypeError, ValueError):
		r = 0
	if 0 == r:
		try:
			path.unlink(missing_ok=True)
		except OSError:
			pass
	return r
# @used-by :func:`acquire_worker_slots()`
def _resolve_slots_dir(slots_dir: Path | str | None) -> Path:
	return default_slots_dir() if None is slots_dir else Path(slots_dir).resolve()
# @used-by :func:`acquire_worker_slots()`
def _try_reserve_once(sdir: Path, owner: str, req: int, cap: int, ttl_s: float) -> dict[str, Any] | None:
	r: dict[str, Any] | None = None
	with locked(sdir / '.slots.lock'):
		now = time.time()
		used = sum((_read_live_slots(p, now) for p in sorted(sdir.glob('*.json'))))
		free = max(0, cap - used)
		if 0 < free:
			granted = min(req, free)
			slot_file = sdir / f'{owner}.json'
			payload = {'acquired_at': now, 'expires_at': now + ttl_s, 'owner': owner, 'pid': os.getpid(), 'slots': granted}
			replace_bytes(slot_file, (json.dumps(payload, ensure_ascii=False, indent='\t', sort_keys=True) + '\n').encode('utf-8'))
			r = {'granted': granted, 'max_slots': cap, 'owner': owner, 'requested': req, 'reserved': True, 'slot_file': slot_file.as_posix()}
	return r
# @used-by :func:`worker_slot_budget()`
# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_worker_semaphore_bounds_total_slots_and_reclaims_dead_and_expired()`
def acquire_worker_slots(requested: int, *, max_slots: int | None=None, slots_dir: Path | str | None=None, ttl_s: float=600.0, wait_timeout: float=2.0, poll_interval: float=0.1) -> dict[str, Any]:
	req = max(1, int(requested))
	cap = max(1, int(max_slots)) if None is not max_slots else default_max_slots()
	sdir = _resolve_slots_dir(slots_dir)
	owner = f'w-{os.getpid()}-{uuid.uuid4().hex[:8]}'
	eff_ttl = max(1.0, float(ttl_s))
	deadline = time.monotonic() + max(0.0, float(wait_timeout))
	lease = _try_reserve_once(sdir, owner, req, cap, eff_ttl)
	while None is lease and time.monotonic() < deadline:
		time.sleep(min(max(0.01, float(poll_interval)), max(0.01, deadline - time.monotonic())))
		lease = _try_reserve_once(sdir, owner, req, cap, eff_ttl)
	if None is lease:
		lease = {'granted': 1, 'max_slots': cap, 'owner': owner, 'requested': req, 'reserved': False, 'slot_file': None}
	return lease
# @used-by :func:`acquire_worker_slots()`
def default_max_slots() -> int:
	raw = str(os.environ.get('HARNESS_MAX_TEST_WORKERS') or '').strip()
	if raw.isdigit() and 0 < int(raw):
		r = int(raw)
	else:
		r = min(8, max(2, (os.cpu_count() or 4) // 2))
	return r
# @used-by :func:`_resolve_slots_dir()`
# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_worker_semaphore_bounds_total_slots_and_reclaims_dead_and_expired()`
def default_slots_dir() -> Path:
	return project_paths(PRIMARY).data_dir / 'test-worker-slots'
# @used-by :func:`worker_slot_budget()`
# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_worker_semaphore_bounds_total_slots_and_reclaims_dead_and_expired()`
def release_worker_slots(lease: dict[str, Any] | None) -> bool:
	r = False
	raw_file = lease.get('slot_file') if isinstance(lease, dict) else None
	if raw_file:
		try:
			Path(str(raw_file)).unlink(missing_ok=True)
			r = True
		except OSError:
			r = False
	return r
# @used-by :func:`agent_tools.parallel_runner.run_parallel_tests()`
# @used-by :func:`agent_tools.suite_runner.run_test_suite()`
def worker_slot_budget(requested: int, *, max_slots: int | None=None, slots_dir: Path | str | None=None, ttl_s: float=600.0, wait_timeout: float=2.0, poll_interval: float=0.1):
	# @used-by :func:`worker_slot_budget()`
	@contextmanager
	def _ctx():
		lease = acquire_worker_slots(requested, max_slots=max_slots, slots_dir=slots_dir, ttl_s=ttl_s, wait_timeout=wait_timeout, poll_interval=poll_interval)
		try:
			yield lease
		finally:
			release_worker_slots(lease)
	return _ctx()
