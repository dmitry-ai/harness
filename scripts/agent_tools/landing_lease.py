# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add deterministic FIFO repository landing lease with reactive wait":
# https://github.com/dmitry-ai/harness/issues/163
from __future__ import annotations
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import time
from .git_gate import GitRepoGate
from .path_registry import project_paths
from .storage import locked, replace_bytes
DEFAULT_POLL_SECONDS = 2.0
DEFAULT_TTL_SECONDS = 600.0
_DEFAULT_STATE = {'version': 1, 'repo': '', 'holder': None, 'queue': []}
def _default_owner() -> str:
	conv = os.environ.get('ANTIGRAVITY_CONVERSATION_ID') or os.environ.get('CODEX_THREAD_ID') or ''
	return f'{conv[:12]}-{os.getpid()}' if conv else f'pid-{os.getpid()}'
def _enqueue_owner(queue: list[dict], owner: str, *, pid: int, ttl: float, now: float) -> int:
	idx = next((i for i, q in enumerate(queue) if owner == q.get('owner')), None)
	if None is idx:
		queue.append({'owner': owner, 'pid': pid, 'enqueued_at': now, 'heartbeat_at': now, 'ttl': ttl})
		idx = len(queue) - 1
	else:
		queue[idx].update(pid=pid, heartbeat_at=now, ttl=ttl)
	return idx + 1
def _is_entry_alive(entry: dict | None, now: float) -> bool:
	r = False
	if isinstance(entry, dict) and entry.get('owner'):
		hb = float(entry.get('heartbeat_at') or entry.get('acquired_at') or entry.get('enqueued_at') or 0.0)
		ttl = max(0.01, float(entry.get('ttl') or DEFAULT_TTL_SECONDS))
		pid = entry.get('pid')
		if now - hb <= ttl:
			r = True if not isinstance(pid, int) else _pid_is_alive(pid)
	return r
def _lease_file_for(repo: Path | str, leases_dir: Path | None=None) -> tuple[Path, Path]:
	resolved = Path(repo).resolve()
	main_repo = GitRepoGate(resolved).main_repo() if (resolved / '.git').exists() else resolved
	base = Path(leases_dir).resolve() if None is not leases_dir else (project_paths(main_repo).data_dir / 'repo-leases')
	repo_hash = hashlib.sha256(main_repo.as_posix().lower().encode('utf-8')).hexdigest()[:16]
	return (main_repo, base / f'{repo_hash}.json')
def _load_state(path: Path, repo_str: str) -> dict:
	r = {**_DEFAULT_STATE, 'repo': repo_str, 'queue': []}
	if path.is_file():
		try:
			raw = json.loads(path.read_text(encoding='utf-8'))
			if isinstance(raw, dict):
				r = {'version': 1, 'repo': str(raw.get('repo') or repo_str), 'holder': raw.get('holder'), 'queue': list(raw.get('queue') or [])}
		except (OSError, ValueError):
			pass
	return r
def _pid_alive_nt(pid: int) -> bool:
	kernel32 = ctypes.windll.kernel32
	handle = kernel32.OpenProcess(0x1000, False, pid)
	if not handle:
		r = 5 == kernel32.GetLastError()
	else:
		code = wintypes.DWORD()
		ok = bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code)))
		kernel32.CloseHandle(handle)
		r = ok and 259 == code.value
	return r
def _pid_is_alive(pid: int) -> bool:
	if 0 >= int(pid):
		r = False
	elif 'nt' == os.name:
		r = _pid_alive_nt(int(pid))
	else:
		try:
			os.kill(int(pid), 0)
			r = True
		except PermissionError:
			r = True
		except OSError:
			r = False
	return r
def _prune_state(state: dict, now: float) -> None:
	if not _is_entry_alive(state.get('holder'), now):
		state['holder'] = None
	state['queue'] = [item for item in (state.get('queue') or []) if _is_entry_alive(item, now)]
def _save_state(path: Path, state: dict) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	replace_bytes(path, (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
def _try_acquire_once(path: Path, repo_str: str, owner: str, *, pid: int, ttl: float, now: float) -> tuple[bool, int, dict]:
	with locked(path.with_suffix('.lock')):
		state = _load_state(path, repo_str)
		_prune_state(state, now)
		holder, queue = (state['holder'], state['queue'])
		if isinstance(holder, dict) and owner == holder.get('owner'):
			holder.update(pid=pid, heartbeat_at=now, ttl=ttl)
			acquired, pos = (True, 0)
		elif None is holder and ((not queue) or owner == queue[0].get('owner')):
			state['queue'] = [q for q in queue if owner != q.get('owner')]
			state['holder'] = {'owner': owner, 'pid': pid, 'acquired_at': now, 'heartbeat_at': now, 'ttl': ttl}
			acquired, pos = (True, 0)
		else:
			acquired, pos = (False, _enqueue_owner(queue, owner, pid=pid, ttl=ttl, now=now))
		_save_state(path, state)
	return (acquired, pos, state)
def _unqueue_owner(path: Path, repo_str: str, owner: str) -> None:
	with locked(path.with_suffix('.lock')):
		state = _load_state(path, repo_str)
		state['queue'] = [q for q in state['queue'] if owner != q.get('owner')]
		_save_state(path, state)
def acquire_lease(repo: Path | str, owner: str | None=None, *, wait: bool=False, timeout: float=600.0, ttl: float=DEFAULT_TTL_SECONDS, poll_interval: float=DEFAULT_POLL_SECONDS, pid: int | None=None, leases_dir: Path | None=None) -> dict:
	main_repo, path = _lease_file_for(repo, leases_dir=leases_dir)
	eff_owner = str(owner).strip() if owner and str(owner).strip() else _default_owner()
	eff_pid = os.getpid() if None is pid else int(pid)
	deadline = time.monotonic() + max(0.0, float(timeout))
	timed_out = False
	acquired, pos, state = _try_acquire_once(path, main_repo.as_posix(), eff_owner, pid=eff_pid, ttl=float(ttl), now=time.time())
	while wait and (not acquired):
		rem = deadline - time.monotonic()
		if 0 >= rem:
			timed_out = True
			_unqueue_owner(path, main_repo.as_posix(), eff_owner)
			break
		time.sleep(min(max(0.01, float(poll_interval)), rem))
		acquired, pos, state = _try_acquire_once(path, main_repo.as_posix(), eff_owner, pid=eff_pid, ttl=float(ttl), now=time.time())
	return {'valid': acquired, 'acquired': acquired, 'timed_out': timed_out, 'owner': eff_owner, 'repo': main_repo.as_posix(), 'lease_file': path.as_posix(), 'position': pos, 'holder': state.get('holder'), 'queue_length': len(state.get('queue') or [])}
def lease_status(repo: Path | str, *, leases_dir: Path | None=None) -> dict:
	main_repo, path = _lease_file_for(repo, leases_dir=leases_dir)
	state = _load_state(path, main_repo.as_posix())
	_prune_state(state, time.time())
	return {'valid': True, 'repo': main_repo.as_posix(), 'lease_file': path.as_posix(), 'free': None is state.get('holder'), 'holder': state.get('holder'), 'queue': state.get('queue') or []}
def release_lease(repo: Path | str, owner: str | None=None, *, force: bool=False, leases_dir: Path | None=None) -> dict:
	main_repo, path = _lease_file_for(repo, leases_dir=leases_dir)
	eff_owner = str(owner).strip() if owner and str(owner).strip() else _default_owner()
	with locked(path.with_suffix('.lock')):
		state = _load_state(path, main_repo.as_posix())
		_prune_state(state, time.time())
		holder = state.get('holder')
		released = False
		if isinstance(holder, dict) and (force or eff_owner == holder.get('owner')):
			state['holder'] = None
			released = True
		before_q = len(state['queue'])
		state['queue'] = [q for q in state['queue'] if eff_owner != q.get('owner')]
		removed_from_queue = len(state['queue']) < before_q
		_save_state(path, state)
	return {'valid': True, 'released': released, 'removed_from_queue': removed_from_queue, 'owner': eff_owner, 'repo': main_repo.as_posix(), 'holder': state.get('holder'), 'queue_length': len(state.get('queue') or [])}
