# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.lib.process import dfh_pid_is_alive
from agent_tools.path_registry import project_paths
from agent_tools.storage import locked, replace_bytes
import hashlib
import json
import os
import time
DEFAULT_POLL_SECONDS = 2.0
DEFAULT_TTL_SECONDS = 600.0
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class LandingLease:
	# @used-by :func:`agent_tools.landing_lease.acquire_lease()`
	# @used-by :func:`agent_tools.landing_lease.lease_status()`
	# @used-by :func:`agent_tools.landing_lease.release_lease()`
	# @used-by :meth:`Df.Harness.Git.RepoWaiter.RepoWaiter.__probe()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__has_active_lease()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__wait_active_leases()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__fifo_fallback()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__phase2_commit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def __init__(self, repo: Path | str, owner: str | None=None, *, leases_dir: Path | None=None) -> None:
		resolved = Path(repo).resolve()
		self.__main_repo = RepoGate(resolved).main_repo() if (resolved / '.git').exists() else resolved
		base = Path(leases_dir).resolve() if None is not leases_dir else (project_paths(self.__main_repo).data_dir / 'repo-leases')
		repo_hash = hashlib.sha256(self.__main_repo.as_posix().lower().encode('utf-8')).hexdigest()[:16]
		self.__path = base / f'{repo_hash}.json'
		conv = os.environ.get('ANTIGRAVITY_CONVERSATION_ID') or os.environ.get('CODEX_THREAD_ID') or ''
		default_owner = f'{conv[:12]}-{os.getpid()}' if conv else f'pid-{os.getpid()}'
		self.__owner = str(owner).strip() if owner and str(owner).strip() else default_owner
	# @used-by :meth:`LandingLease.__try_once()`
	def __enqueue(self, queue: list[dict], now: float, pid: int, ttl: float) -> int:
		idx = next((i for i, q in enumerate(queue) if self.__owner == q.get('owner')), None)
		if None is idx:
			queue.append({'owner': self.__owner, 'pid': pid, 'enqueued_at': now, 'heartbeat_at': now, 'ttl': ttl})
			idx = len(queue) - 1
		else:
			queue[idx].update(pid=pid, heartbeat_at=now, ttl=ttl)
		return idx + 1
	# @used-by :meth:`LandingLease.__prune()`
	@staticmethod
	def __is_alive(entry: dict | None, now: float) -> bool:
		r = False
		if isinstance(entry, dict) and entry.get('owner'):
			hb = float(entry.get('heartbeat_at') or entry.get('acquired_at') or entry.get('enqueued_at') or 0.0)
			ttl = max(0.01, float(entry.get('ttl') or DEFAULT_TTL_SECONDS))
			pid = entry.get('pid')
			if now - hb <= ttl:
				r = True if not isinstance(pid, int) else dfh_pid_is_alive(pid)
		return r
	# @used-by :meth:`LandingLease.__try_once()`
	# @used-by :meth:`LandingLease.__unqueue()`
	# @used-by :meth:`LandingLease.release()`
	# @used-by :meth:`LandingLease.status()`
	def __load(self) -> dict:
		repo_str = self.__main_repo.as_posix()
		r = {'version': 1, 'repo': repo_str, 'holder': None, 'queue': []}
		if self.__path.is_file():
			try:
				raw = json.loads(self.__path.read_text(encoding='utf-8'))
				if isinstance(raw, dict):
					r = {'version': 1, 'repo': str(raw.get('repo') or repo_str), 'holder': raw.get('holder'), 'queue': list(raw.get('queue') or [])}
			except (OSError, ValueError):
				pass
		return r
	# @used-by :meth:`LandingLease.__try_once()`
	# @used-by :meth:`LandingLease.release()`
	# @used-by :meth:`LandingLease.status()`
	def __prune(self, state: dict, now: float) -> None:
		if not self.__is_alive(state.get('holder'), now):
			state['holder'] = None
		state['queue'] = [item for item in (state.get('queue') or []) if self.__is_alive(item, now)]
	# @used-by :meth:`LandingLease.__try_once()`
	# @used-by :meth:`LandingLease.__unqueue()`
	# @used-by :meth:`LandingLease.release()`
	def __save(self, state: dict) -> None:
		self.__path.parent.mkdir(parents=True, exist_ok=True)
		replace_bytes(self.__path, (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
	# @used-by :meth:`LandingLease.acquire()`
	def __try_once(self, now: float, pid: int, ttl: float) -> tuple[bool, int, dict]:
		with locked(self.__path.with_suffix('.lock')):
			state = self.__load()
			self.__prune(state, now)
			holder, queue = (state['holder'], state['queue'])
			if isinstance(holder, dict) and self.__owner == holder.get('owner'):
				holder.update(pid=pid, heartbeat_at=now, ttl=ttl)
				acquired, pos = (True, 0)
			elif None is holder and ((not queue) or self.__owner == queue[0].get('owner')):
				state['queue'] = [q for q in queue if self.__owner != q.get('owner')]
				state['holder'] = {'owner': self.__owner, 'pid': pid, 'acquired_at': now, 'heartbeat_at': now, 'ttl': ttl}
				acquired, pos = (True, 0)
			else:
				acquired, pos = (False, self.__enqueue(queue, now, pid, ttl))
			self.__save(state)
		return (acquired, pos, state)
	# @used-by :meth:`LandingLease.acquire()`
	def __unqueue(self) -> None:
		with locked(self.__path.with_suffix('.lock')):
			state = self.__load()
			state['queue'] = [q for q in state['queue'] if self.__owner != q.get('owner')]
			self.__save(state)
	# @used-by :func:`agent_tools.landing_lease.acquire_lease()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__fifo_fallback()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__phase2_commit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def acquire(self, *, wait: bool=False, timeout: float=600.0, ttl: float=DEFAULT_TTL_SECONDS, poll_interval: float=DEFAULT_POLL_SECONDS, pid: int | None=None) -> dict:
		eff_pid = os.getpid() if None is pid else int(pid)
		eff_ttl = float(ttl)
		deadline = time.monotonic() + max(0.0, float(timeout))
		timed_out = False
		acquired, pos, state = self.__try_once(time.time(), eff_pid, eff_ttl)
		while wait and (not acquired):
			rem = deadline - time.monotonic()
			if 0 >= rem:
				timed_out = True
				self.__unqueue()
				break
			time.sleep(min(max(0.01, float(poll_interval)), rem))
			acquired, pos, state = self.__try_once(time.time(), eff_pid, eff_ttl)
		return {'valid': acquired, 'acquired': acquired, 'timed_out': timed_out, 'owner': self.__owner, 'repo': self.__main_repo.as_posix(), 'lease_file': self.__path.as_posix(), 'position': pos, 'holder': state.get('holder'), 'queue_length': len(state.get('queue') or [])}
	# @used-by :func:`agent_tools.landing_lease.release_lease()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__fifo_fallback()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__phase2_commit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	def release(self, *, force: bool=False) -> dict:
		with locked(self.__path.with_suffix('.lock')):
			state = self.__load()
			self.__prune(state, time.time())
			holder = state.get('holder')
			released = isinstance(holder, dict) and (force or self.__owner == holder.get('owner'))
			if released:
				state['holder'] = None
			before_q = len(state['queue'])
			state['queue'] = [q for q in state['queue'] if self.__owner != q.get('owner')]
			removed = len(state['queue']) < before_q
			self.__save(state)
		return {'valid': True, 'released': released, 'removed_from_queue': removed, 'owner': self.__owner, 'repo': self.__main_repo.as_posix(), 'holder': state.get('holder'), 'queue_length': len(state.get('queue') or [])}
	# @used-by :func:`agent_tools.landing_lease.lease_status()`
	# @used-by :meth:`Df.Harness.Git.RepoWaiter.RepoWaiter.__probe()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__has_active_lease()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__wait_active_leases()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	def status(self) -> dict:
		state = self.__load()
		self.__prune(state, time.time())
		return {'valid': True, 'repo': self.__main_repo.as_posix(), 'lease_file': self.__path.as_posix(), 'free': None is state.get('holder'), 'holder': state.get('holder'), 'queue': state.get('queue') or []}
