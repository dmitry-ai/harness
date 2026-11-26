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
# @used-by :func:`_probe_repo_state()`
def _dirty_files(repo: Path) -> list[str]:
	proc = GitRepoGate(repo).run_read(['status', '--porcelain', '-z'], check=False)
	raw = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else ''
	return _parse_porcelain_z(raw)
# @used-by :func:`is_transient_contention_error()`
def _has_active_workspace_lease(root: Path | None) -> bool:
	r = False
	if None is not root:
		for cr in _workspace_code_repos(root):
			if not lease_status(cr)['free']:
				r = True
				break
	return r
# @used-by :func:`wait_for_repo()`
def _probe_repo_state(main_repo: Path, *, require_clean: bool, require_lease_free: bool, leases_dir: Path | None) -> dict[str, Any]:
	st = lease_status(main_repo, leases_dir=leases_dir)
	dirty = _dirty_files(main_repo) if require_clean else []
	is_clean, is_free = (not dirty, bool(st.get('free')))
	ready = (is_clean or (not require_clean)) and (is_free or (not require_lease_free))
	return {'ready': ready, 'clean': is_clean, 'lease_free': is_free, 'dirty_files': dirty, 'holder': st.get('holder'), 'queue_length': len(st.get('queue') or [])}
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
# @used-by :func:`run_with_transient_wait()`
def _wait_active_repo_leases(root: Path, deadline: float, poll_interval: float) -> float:
	waited = 0.0
	for cr in _workspace_code_repos(root):
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
# @used-by :func:`_wait_active_repo_leases()`
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
# @used-by :func:`agent_tools.completion.prepare()`
# @used-by :meth:`test_observability_diagnostics.ObservabilityDiagnosticsTests.test_run_with_transient_wait_separates_lease_retry_and_execution_seconds()`
def run_with_transient_wait(root: Path, fn: Callable[[], dict[str, Any]], *, wait_timeout: float=0.0, poll_interval: float=DEFAULT_WAIT_POLL_SECONDS) -> dict[str, Any]:
	started = time.monotonic()
	budget = max(0.0, float(wait_timeout))
	deadline = started + budget
	lease_wait_s = _wait_active_repo_leases(root, deadline, poll_interval) if 0.0 < budget else 0.0
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