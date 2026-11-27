# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from agent_tools.landing_lease import _pid_is_alive
from agent_tools.path_registry import project_paths
from agent_tools.runtime import PRIMARY
from agent_tools.storage import locked, replace_bytes
import json
import os
import time
import uuid
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class WorkerSemaphore:
	# @used-by :func:`agent_tools.worker_semaphore.acquire_worker_slots()`
	# @used-by :meth:`WorkerSemaphore.slot_budget()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_process_tree_watchdog_semaphore_and_pytest_modes()`
	def __init__(self, requested: int, *, max_slots: int | None=None, slots_dir: Path | str | None=None, ttl_s: float=600.0, wait_timeout: float=2.0, poll_interval: float=0.1) -> None:
		self.__requested = requested
		self.__max_slots = max_slots
		self.__slots_dir = slots_dir
		self.__ttl_s = ttl_s
		self.__wait_timeout = wait_timeout
		self.__poll_interval = poll_interval
	# @used-by :func:`agent_tools.worker_semaphore.acquire_worker_slots()`
	# @used-by :meth:`WorkerSemaphore.slot_budget()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_process_tree_watchdog_semaphore_and_pytest_modes()`
	def acquire(self) -> dict[str, Any]:
		req = max(1, int(self.__requested))
		cap = max(1, int(self.__max_slots)) if None is not self.__max_slots else WorkerSemaphore.default_max_slots()
		sdir = WorkerSemaphore.__resolve_slots_dir(self.__slots_dir)
		owner = f'w-{os.getpid()}-{uuid.uuid4().hex[:8]}'
		eff_ttl = max(1.0, float(self.__ttl_s))
		deadline = time.monotonic() + max(0.0, float(self.__wait_timeout))
		lease = WorkerSemaphore.__try_reserve_once(sdir, owner, req, cap, eff_ttl)
		while None is lease and time.monotonic() < deadline:
			time.sleep(min(max(0.01, float(self.__poll_interval)), max(0.01, deadline - time.monotonic())))
			lease = WorkerSemaphore.__try_reserve_once(sdir, owner, req, cap, eff_ttl)
		return lease if None is not lease else {'granted': 1, 'max_slots': cap, 'owner': owner, 'requested': req, 'reserved': False, 'slot_file': None}
	# @used-by :meth:`WorkerSemaphore.__try_reserve_once()`
	@staticmethod
	def __read_live_slots(path: Path, now: float) -> int:
		r = 0
		try:
			raw = json.loads(path.read_text(encoding='utf-8'))
			if isinstance(raw, dict):
				exp, slots, pid = (float(raw.get('expires_at') or 0.0), int(raw.get('slots') or 0), raw.get('pid'))
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
	# @used-by :meth:`WorkerSemaphore.acquire()`
	@staticmethod
	def __resolve_slots_dir(slots_dir: Path | str | None) -> Path:
		return WorkerSemaphore.default_slots_dir() if None is slots_dir else Path(slots_dir).resolve()
	# @used-by :meth:`WorkerSemaphore.acquire()`
	@staticmethod
	def __try_reserve_once(sdir: Path, owner: str, req: int, cap: int, ttl_s: float) -> dict[str, Any] | None:
		r: dict[str, Any] | None = None
		with locked(sdir / '.slots.lock'):
			now = time.time()
			used = sum((WorkerSemaphore.__read_live_slots(p, now) for p in sorted(sdir.glob('*.json'))))
			free = max(0, cap - used)
			if 0 < free:
				granted = min(req, free)
				slot_file = sdir / f'{owner}.json'
				payload = {'acquired_at': now, 'expires_at': now + ttl_s, 'owner': owner, 'pid': os.getpid(), 'slots': granted}
				replace_bytes(slot_file, (json.dumps(payload, ensure_ascii=False, indent='\t', sort_keys=True) + '\n').encode('utf-8'))
				r = {'granted': granted, 'max_slots': cap, 'owner': owner, 'requested': req, 'reserved': True, 'slot_file': slot_file.as_posix()}
		return r
	# @used-by :func:`agent_tools.worker_semaphore.default_max_slots()`
	# @used-by :meth:`WorkerSemaphore.acquire()`
	@staticmethod
	def default_max_slots() -> int:
		raw = str(os.environ.get('HARNESS_MAX_TEST_WORKERS') or '').strip()
		return int(raw) if raw.isdigit() and 0 < int(raw) else min(8, max(2, (os.cpu_count() or 4) // 2))
	# @used-by :func:`agent_tools.worker_semaphore.default_slots_dir()`
	# @used-by :meth:`WorkerSemaphore.__resolve_slots_dir()`
	@staticmethod
	def default_slots_dir() -> Path:
		return project_paths(PRIMARY).data_dir / 'test-worker-slots'
	# @used-by :func:`agent_tools.worker_semaphore.release_worker_slots()`
	# @used-by :meth:`WorkerSemaphore.slot_budget()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_process_tree_watchdog_semaphore_and_pytest_modes()`
	@staticmethod
	def release(lease: dict[str, Any] | None) -> bool:
		r = False
		raw_file = lease.get('slot_file') if isinstance(lease, dict) else None
		if raw_file:
			try:
				Path(str(raw_file)).unlink(missing_ok=True)
				r = True
			except OSError:
				r = False
		return r
	# @used-by :func:`agent_tools.worker_semaphore.worker_slot_budget()`
	# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.run()`
	# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.run()`
	@staticmethod
	def slot_budget(requested: int, *, max_slots: int | None=None, slots_dir: Path | str | None=None, ttl_s: float=600.0, wait_timeout: float=2.0, poll_interval: float=0.1, acquire_fn=None):
		# @used-by :meth:`WorkerSemaphore.slot_budget()`
		@contextmanager
		def _ctx():
			req = max(1, int(requested))
			nested = None is slots_dir and '1' == os.environ.get('HARNESS_TEST_IN_WORKER')
			acq = acquire_fn if None is not acquire_fn else (lambda r_val, **kw: WorkerSemaphore(r_val, **kw).acquire())
			lease = {'granted': req, 'max_slots': req, 'owner': 'nested-worker', 'requested': req, 'reserved': False, 'slot_file': None} if nested else acq(req, max_slots=max_slots, slots_dir=slots_dir, ttl_s=ttl_s, wait_timeout=wait_timeout, poll_interval=poll_interval)
			try:
				yield lease
			finally:
				WorkerSemaphore.release(lease)
		return _ctx()
