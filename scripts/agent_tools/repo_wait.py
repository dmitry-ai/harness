# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
from typing import override
import sqlite3
import time
from .git_gate import GitRepoGate
from .issues.git_read_cache import _parse_porcelain_z
from .landing_lease import lease_status
from .path_registry import project_paths
DEFAULT_WAIT_POLL_SECONDS = 1.0
DEFAULT_WAIT_TIMEOUT_SECONDS = 180.0
class RetryableOperationError(RuntimeError):
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :func:`_sleep_or_raise_transient()`
	# @used-by :func:`_wait_active_repo_leases()`
	# @see :meth:`RuntimeError.__init__()`
	@override
	def __init__(self, message: str) -> None:
		super().__init__(message)
		self.retryable = True
# 2026-11-26 "Split worktree-land into optimistic pre-lease verification and targeted wait": https://github.com/dmitry-ai/harness/issues/350
# @used-by :func:`_resolve_targeted_wait_repos()`
def _active_turn_touched_paths(root: Path, conversation: str, *, platform: str | None, backend: Path | str | None) -> list[str]:
	from .hook_runtime import iter_turn_state_files
	cid_low = str(conversation or '').strip().lower()
	plat_low = str(platform or '').strip().lower()
	backend_str = str(backend or '').strip()
	best: tuple[tuple[int, str, int], dict] | None = None
	try:
		turns_dir = project_paths(Path(root).resolve(), exact_root=True).turns_dir
	except (OSError, ValueError):
		turns_dir = None
	if None is not turns_dir and turns_dir.is_dir():
		for tfile, st in iter_turn_state_files(turns_dir):
			if _turn_matches_session(st, cid_low, plat_low, backend_str):
				key = _state_priority(st, tfile.stat().st_mtime_ns)
				if None is best or key > best[0]:
					best = (key, st)
	return _extract_state_paths(best[1]) if None is not best else []
# @used-by :func:`_probe_repo_state()`
def _dirty_files(repo: Path) -> list[str]:
	proc = GitRepoGate(repo).run_read(['status', '--porcelain', '-z'], check=False)
	raw = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else ''
	return _parse_porcelain_z(raw)
# 2026-11-26 "Split worktree-land into optimistic pre-lease verification and targeted wait": https://github.com/dmitry-ai/harness/issues/350
# @used-by :func:`_active_turn_touched_paths()`
def _extract_state_paths(st: dict) -> list[str]:
	paths = [str(p) for p in (st.get('touched_files') or ()) if p]
	lc = st.get('code_lifecycle_check')
	if isinstance(lc, dict) and isinstance(lc.get('touched_repos'), dict):
		paths.extend((str(k) for k in lc['touched_repos'] if k))
	return paths
# @used-by :func:`is_transient_contention_error()`
def _has_active_workspace_lease(root: Path | None) -> bool:
	r = False
	if None is not root:
		for cr in _workspace_code_repos(root):
			if not lease_status(cr)['free']:
				r = True
				break
	return r
# 2026-11-26 "Split worktree-land into optimistic pre-lease verification and targeted wait": https://github.com/dmitry-ai/harness/issues/350
# @used-by :func:`_resolve_targeted_wait_repos()`
def _map_touched_path_to_repo(root_p: Path, raw_path: str, ws_set: set[Path]) -> Path | None:
	from .worktree_flow import resolve_touched_repo_file
	cand = Path(raw_path.strip())
	resolved = cand.resolve() if cand.is_absolute() else (root_p / cand).resolve()
	if resolved in ws_set:
		r: Path | None = resolved
	else:
		hit = resolve_touched_repo_file(resolved, lambda anc: (anc / '.git').exists())
		repo_hit = hit[0] if None is not hit else None
		if None is repo_hit and (resolved / '.git').exists():
			repo_hit = resolved
		main_r = GitRepoGate(repo_hit).main_repo().resolve() if None is not repo_hit else None
		r = main_r if main_r in ws_set else None
	return r
# 2026-11-26 "Split worktree-land into optimistic pre-lease verification and targeted wait": https://github.com/dmitry-ai/harness/issues/350
# @used-by :func:`_resolve_targeted_wait_repos()`
def _normalize_repo_list(repos: list[Path] | tuple[Path, ...]) -> list[Path]:
	out: list[Path] = []
	for repo in repos:
		resolved = Path(repo).resolve()
		if (resolved / '.git').exists() and resolved not in out:
			out.append(resolved)
	return out
# @used-by :func:`wait_for_repo()`
def _probe_repo_state(main_repo: Path, *, require_clean: bool, require_lease_free: bool, leases_dir: Path | None) -> dict[str, Any]:
	st = lease_status(main_repo, leases_dir=leases_dir)
	dirty = _dirty_files(main_repo) if require_clean else []
	is_clean, is_free = (not dirty, bool(st.get('free')))
	ready = (is_clean or (not require_clean)) and (is_free or (not require_lease_free))
	return {'ready': ready, 'clean': is_clean, 'lease_free': is_free, 'dirty_files': dirty, 'holder': st.get('holder'), 'queue_length': len(st.get('queue') or [])}
# 2026-11-26 "Split worktree-land into optimistic pre-lease verification and targeted wait": https://github.com/dmitry-ai/harness/issues/350
# @used-by :func:`run_with_transient_wait()`
def _resolve_targeted_wait_repos(root: Path, *, wait_repos: list[Path] | tuple[Path, ...] | None=None, conversation: str | None=None, platform: str | None=None, backend: Path | str | None=None) -> list[Path]:
	if None is not wait_repos:
		r = _normalize_repo_list(wait_repos)
	elif not str(conversation or '').strip():
		r = _workspace_code_repos(root)
	else:
		ws_repos = _workspace_code_repos(root)
		ws_set = set(ws_repos)
		root_p = Path(root).resolve()
		matched: list[Path] = []
		for raw_p in _active_turn_touched_paths(root_p, str(conversation), platform=platform, backend=backend):
			repo = _map_touched_path_to_repo(root_p, raw_p, ws_set)
			if None is not repo and repo not in matched:
				matched.append(repo)
		r = matched
	return r
# 2026-11-26 "Split worktree-land into optimistic pre-lease verification and targeted wait": https://github.com/dmitry-ai/harness/issues/350
# @used-by :func:`_active_turn_touched_paths()`
def _state_priority(st: dict, mtime_ns: int) -> tuple[int, str, int]:
	status = str(st.get('status') or '')
	rank = 3 if 'open' == status else (2 if 'prepared' == status else (1 if 'conflict' == status else 0))
	return (rank, str(st.get('updated_at') or ''), mtime_ns)
# 2026-11-26 "Split worktree-land into optimistic pre-lease verification and targeted wait": https://github.com/dmitry-ai/harness/issues/350
# @used-by :func:`_active_turn_touched_paths()`
def _turn_matches_session(st: dict, cid_low: str, plat_low: str, backend_str: str) -> bool:
	st_cid = str(st.get('conversation_id') or '').strip().lower()
	st_plat = str(st.get('platform') or '').strip().lower()
	st_be = str(st.get('native_backend') or '').strip()
	ok_plat = (not plat_low) or (not st_plat) or plat_low == st_plat
	ok_be = (not backend_str) or (not st_be) or backend_str == st_be
	return bool(st_cid and cid_low == st_cid and ok_plat and ok_be)
# 2026-11-26 "Fix shadow-replay CLI matching and observability timing diagnostics": https://github.com/dmitry-ai/harness/issues/342
# @used-by :func:`run_with_transient_wait()`
def _execute_with_retries(root: Path, fn: Callable[[], dict[str, Any]], deadline: float, poll_interval: float) -> tuple[dict[str, Any], int, float, float]:
	attempts = 0
	retry_wait_s = 0.0
	exec_s = 0.0
	while True:
		attempts += 1
		t0 = time.monotonic()
		try:
			res = fn()
			exec_s += time.monotonic() - t0
			break
		except Exception as exc:
			exec_s += time.monotonic() - t0
			if not is_transient_contention_error(exc, root):
				raise
			retry_wait_s += _sleep_or_raise_transient(exc, deadline, poll_interval)
	return (res, attempts, retry_wait_s, exec_s)
# 2026-11-26 "Fix shadow-replay CLI matching and observability timing diagnostics": https://github.com/dmitry-ai/harness/issues/342
# @used-by :func:`_execute_with_retries()`
def _sleep_or_raise_transient(exc: BaseException, deadline: float, poll_interval: float) -> float:
	rem = deadline - time.monotonic()
	if 0.0 >= rem:
		raise RetryableOperationError(str(exc)) from exc
	t0 = time.monotonic()
	time.sleep(min(max(0.01, float(poll_interval)), rem))
	return time.monotonic() - t0
# 2026-11-26 "Fix shadow-replay CLI matching and observability timing diagnostics": https://github.com/dmitry-ai/harness/issues/342
# 2026-11-26 "Split worktree-land into optimistic pre-lease verification and targeted wait": https://github.com/dmitry-ai/harness/issues/350
# @used-by :func:`run_with_transient_wait()`
def _wait_active_repo_leases(repos: list[Path], deadline: float, poll_interval: float) -> float:
	waited = 0.0
	for cr in repos:
		if lease_status(cr)['free']:
			continue
		rem = deadline - time.monotonic()
		if 0.0 >= rem:
			raise RetryableOperationError(f'Timed out waiting for active landing lease on {cr.as_posix()}')
		t0 = time.monotonic()
		res = wait_for_repo(cr, lease_free=True, timeout=rem, poll_interval=poll_interval)
		waited += time.monotonic() - t0
		if not res['ready']:
			raise RetryableOperationError(f'Timed out waiting for active landing lease on {cr.as_posix()}')
	return waited
# @used-by :func:`_has_active_workspace_lease()`
# @used-by :func:`_resolve_targeted_wait_repos()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_bypasses_foreign_lease_on_readonly_and_noncode_turns()`
def _workspace_code_repos(root: Path) -> list[Path]:
	repos: list[Path] = []
	try:
		cands = list(project_paths(Path(root).resolve(), exact_root=True).code_repos)
	except (OSError, ValueError):
		cands = []
	for cand in cands:
		resolved = Path(cand).resolve()
		if (resolved / '.git').exists() and resolved not in repos:
			repos.append(resolved)
	return repos
# @used-by :func:`_execute_with_retries()`
# @used-by :func:`agent_tools.cli_common.operation_error_payload()`
def is_transient_contention_error(exc: BaseException, root: Path | None=None) -> bool:
	msg = str(exc).lower()
	if bool(getattr(exc, 'retryable', False)):
		r = True
	elif isinstance(exc, TimeoutError) and 'lock busy' in msg:
		r = True
	elif isinstance(exc, sqlite3.OperationalError) and ('locked' in msg or 'busy' in msg):
		r = True
	elif isinstance(exc, PermissionError):
		r = True
	elif isinstance(exc, ValueError) and ('uncommitted file' in msg or 'not committed' in msg):
		r = _has_active_workspace_lease(root)
	else:
		r = False
	return r
# 2026-11-26 "Fix shadow-replay CLI matching and observability timing diagnostics": https://github.com/dmitry-ai/harness/issues/342
# 2026-11-26 "Split worktree-land into optimistic pre-lease verification and targeted wait": https://github.com/dmitry-ai/harness/issues/350
# @used-by :func:`agent_tools.completion.prepare()`
# @used-by :meth:`test_observability_diagnostics.ObservabilityDiagnosticsTests.test_run_with_transient_wait_separates_lease_retry_and_execution_seconds()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_blocks_when_turn_touches_leased_repo_or_worktree()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_bypasses_foreign_lease_on_readonly_and_noncode_turns()`
def run_with_transient_wait(root: Path, fn: Callable[[], dict[str, Any]], *, wait_timeout: float=0.0, poll_interval: float=DEFAULT_WAIT_POLL_SECONDS, wait_repos: list[Path] | tuple[Path, ...] | None=None, conversation: str | None=None, platform: str | None=None, backend: Path | str | None=None) -> dict[str, Any]:
	started = time.monotonic()
	budget = max(0.0, float(wait_timeout))
	deadline = started + budget
	target_repos = _resolve_targeted_wait_repos(root, wait_repos=wait_repos, conversation=conversation, platform=platform, backend=backend) if 0.0 < budget else []
	lease_wait_s = _wait_active_repo_leases(target_repos, deadline, poll_interval) if target_repos else 0.0
	res, attempts, retry_wait_s, exec_s = _execute_with_retries(root, fn, deadline, poll_interval)
	total_s = time.monotonic() - started
	res['retryable'] = False
	res['lease_wait_seconds'] = round(lease_wait_s, 3)
	res['retry_wait_seconds'] = round(retry_wait_s, 3)
	res['execution_seconds'] = round(exec_s, 3)
	res['total_seconds'] = round(total_s, 3)
	if 1 < attempts or 0.0 < budget:
		res['waited_seconds'] = round(lease_wait_s + retry_wait_s, 3)
	return res
# 2026-11-24
# "Add deterministic reactive wait primitive for transient repository and journal contention":
# https://github.com/dmitry-ai/harness/issues/199
# @used-by :func:`_wait_active_repo_leases()`
# @used-by :func:`agent_tools.cli_registry._exec_wait_repo()`
# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_wait_repo_reacts_to_lease_release_dead_pid_and_clean_tree()`
def wait_for_repo(repo: Path | str, *, clean: bool=False, lease_free: bool=False, timeout: float=DEFAULT_WAIT_TIMEOUT_SECONDS, poll_interval: float=DEFAULT_WAIT_POLL_SECONDS, leases_dir: Path | None=None) -> dict[str, Any]:
	resolved = Path(repo).resolve()
	main_repo = GitRepoGate(resolved).main_repo() if (resolved / '.git').exists() else resolved
	req_clean, req_lease = (bool(clean or (not lease_free)), bool(lease_free or (not clean)))
	started = time.monotonic()
	deadline = started + max(0.0, float(timeout))
	probe = _probe_repo_state(main_repo, require_clean=req_clean, require_lease_free=req_lease, leases_dir=leases_dir)
	while not probe['ready']:
		rem = deadline - time.monotonic()
		if 0.0 >= rem:
			break
		time.sleep(min(max(0.01, float(poll_interval)), rem))
		probe = _probe_repo_state(main_repo, require_clean=req_clean, require_lease_free=req_lease, leases_dir=leases_dir)
	ready = bool(probe['ready'])
	return {'valid': ready, 'ready': ready, 'timed_out': not ready, 'retryable': not ready, 'elapsed_seconds': round(time.monotonic() - started, 3), 'repo': main_repo.as_posix(), 'clean_required': req_clean, 'lease_free_required': req_lease, 'clean': probe['clean'], 'lease_free': probe['lease_free'], 'dirty_files': probe['dirty_files'], 'holder': probe['holder'], 'holder_alive': None is not probe['holder'], 'queue_length': probe['queue_length']}