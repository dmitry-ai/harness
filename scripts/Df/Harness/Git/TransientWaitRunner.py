# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
from Df.Harness.Git.LandingLease import LandingLease
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.Git.RepoWaiter import DEFAULT_WAIT_POLL_SECONDS, RepoWaiter
from Df.Harness.Git.RetryableError import RetryableError
from Df.Harness.Git.WorktreePathResolver import WorktreePathResolver
from agent_tools.path_registry import project_paths
import sqlite3
import time
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class TransientWaitRunner:
	# @used-by :func:`agent_tools.repo_wait.is_transient_contention_error()`
	# @used-by :func:`agent_tools.repo_wait.run_with_transient_wait()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def __init__(self, root: Path | None, fn: Callable[[], dict[str, Any]] | None=None, *, wait_timeout: float=0.0, poll_interval: float=DEFAULT_WAIT_POLL_SECONDS, wait_repos: list[Path] | tuple[Path, ...] | None=None, conversation: str | None=None, platform: str | None=None, backend: Path | str | None=None) -> None:
		self.__root = root
		self.__fn = fn
		self.__wait_timeout = max(0.0, float(wait_timeout))
		self.__poll = float(poll_interval)
		self.__wait_repos = wait_repos
		self.__conversation = conversation
		self.__platform = platform
		self.__backend = backend
	# @used-by :meth:`TransientWaitRunner.__resolve_target_repos()`
	def __active_turn_paths(self, root_p: Path) -> list[str]:
		from agent_tools.hook_runtime import iter_turn_state_files
		cid_low = str(self.__conversation or '').strip().lower()
		plat_low = str(self.__platform or '').strip().lower()
		be_str = str(self.__backend or '').strip()
		best: tuple[tuple[int, str, int], dict] | None = None
		try:
			turns_dir = project_paths(root_p, exact_root=True).turns_dir
		except (OSError, ValueError):
			turns_dir = None
		if None is not turns_dir and turns_dir.is_dir():
			for tfile, st in iter_turn_state_files(turns_dir):
				if self.__turn_matches(st, cid_low, plat_low, be_str):
					key = self.__state_priority(st, tfile.stat().st_mtime_ns)
					if None is best or key > best[0]:
						best = (key, st)
		return self.__extract_state_paths(best[1]) if None is not best else []
	# @used-by :meth:`TransientWaitRunner.run()`
	def __execute_retries(self, deadline: float) -> tuple[dict[str, Any], int, float, float]:
		attempts, retry_wait_s, exec_s = (0, 0.0, 0.0)
		while True:
			attempts += 1
			t0 = time.monotonic()
			try:
				res = self.__fn()
				exec_s += time.monotonic() - t0
				break
			except Exception as exc:
				exec_s += time.monotonic() - t0
				if not self.__is_transient(exc):
					raise
				retry_wait_s += self.__sleep_or_raise(exc, deadline)
		return (res, attempts, retry_wait_s, exec_s)
	# @used-by :meth:`TransientWaitRunner.__active_turn_paths()`
	@staticmethod
	def __extract_state_paths(st: dict) -> list[str]:
		paths = [str(p) for p in (st.get('touched_files') or ()) if p]
		lc = st.get('code_lifecycle_check')
		if isinstance(lc, dict) and isinstance(lc.get('touched_repos'), dict):
			paths.extend((str(k) for k in lc['touched_repos'] if k))
		return paths
	# @used-by :meth:`TransientWaitRunner.__is_transient()`
	def __has_active_lease(self) -> bool:
		return None is not self.__root and any((not LandingLease(cr).status()['free'] for cr in self.__workspace_code_repos(self.__root)))
	# @used-by :meth:`TransientWaitRunner.__execute_retries()`
	# @used-by :meth:`TransientWaitRunner.run()`
	def __is_transient(self, exc: BaseException) -> bool:
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
			r = self.__has_active_lease()
		else:
			r = False
		return r
	# @used-by :meth:`TransientWaitRunner.__resolve_target_repos()`
	@staticmethod
	def __map_path_to_repo(root_p: Path, raw_path: str, ws_set: set[Path]) -> Path | None:
		cand = Path(raw_path.strip())
		resolved = cand.resolve() if cand.is_absolute() else (root_p / cand).resolve()
		if resolved in ws_set:
			r: Path | None = resolved
		else:
			hit = WorktreePathResolver(resolved, lambda anc: (anc / '.git').exists()).resolve()
			repo_hit = hit[0] if None is not hit else (resolved if (resolved / '.git').exists() else None)
			main_r = RepoGate(repo_hit).main_repo().resolve() if None is not repo_hit else None
			r = main_r if main_r in ws_set else None
		return r
	# @used-by :meth:`TransientWaitRunner.run()`
	def __resolve_target_repos(self) -> list[Path]:
		if None is not self.__wait_repos:
			r: list[Path] = []
			for repo in self.__wait_repos:
				res = Path(repo).resolve()
				if (res / '.git').exists() and res not in r:
					r.append(res)
		elif None is self.__root:
			r = []
		elif not str(self.__conversation or '').strip():
			r = self.__workspace_code_repos(self.__root)
		else:
			ws_repos = self.__workspace_code_repos(self.__root)
			ws_set, root_p, r = (set(ws_repos), Path(self.__root).resolve(), [])
			for raw_p in self.__active_turn_paths(root_p):
				repo = self.__map_path_to_repo(root_p, raw_p, ws_set)
				if None is not repo and repo not in r:
					r.append(repo)
		return r
	# @used-by :meth:`TransientWaitRunner.__execute_retries()`
	def __sleep_or_raise(self, exc: BaseException, deadline: float) -> float:
		rem = deadline - time.monotonic()
		if 0.0 >= rem:
			raise RetryableError(str(exc)) from exc
		t0 = time.monotonic()
		time.sleep(min(max(0.01, self.__poll), rem))
		return time.monotonic() - t0
	# @used-by :meth:`TransientWaitRunner.__active_turn_paths()`
	@staticmethod
	def __state_priority(st: dict, mtime_ns: int) -> tuple[int, str, int]:
		status = str(st.get('status') or '')
		rank = 3 if 'open' == status else (2 if 'prepared' == status else (1 if 'conflict' == status else 0))
		return (rank, str(st.get('updated_at') or ''), mtime_ns)
	# @used-by :meth:`TransientWaitRunner.__active_turn_paths()`
	@staticmethod
	def __turn_matches(st: dict, cid_low: str, plat_low: str, be_str: str) -> bool:
		st_cid = str(st.get('conversation_id') or '').strip().lower()
		st_plat = str(st.get('platform') or '').strip().lower()
		st_be = str(st.get('native_backend') or '').strip()
		return bool(st_cid and cid_low == st_cid and ((not plat_low) or (not st_plat) or plat_low == st_plat) and ((not be_str) or (not st_be) or be_str == st_be))
	# @used-by :meth:`TransientWaitRunner.run()`
	def __wait_active_leases(self, repos: list[Path], deadline: float) -> float:
		waited = 0.0
		for cr in repos:
			if LandingLease(cr).status()['free']:
				continue
			rem = deadline - time.monotonic()
			if 0.0 >= rem:
				raise RetryableError(f'Timed out waiting for active landing lease on {cr.as_posix()}')
			t0 = time.monotonic()
			res = RepoWaiter(cr, lease_free=True, timeout=rem, poll_interval=self.__poll).wait()
			waited += time.monotonic() - t0
			if not res['ready']:
				raise RetryableError(f'Timed out waiting for active landing lease on {cr.as_posix()}')
		return waited
	# @used-by :meth:`TransientWaitRunner.__has_active_lease()`
	# @used-by :meth:`TransientWaitRunner.__resolve_target_repos()`
	@staticmethod
	def __workspace_code_repos(root: Path) -> list[Path]:
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
	# @used-by :func:`agent_tools.repo_wait.is_transient_contention_error()`
	# @used-by :func:`agent_tools.repo_wait.run_with_transient_wait()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def run(self, *, probe_exc: BaseException | None=None) -> Any:
		if None is not probe_exc:
			r: Any = self.__is_transient(probe_exc)
		else:
			started = time.monotonic()
			deadline = started + self.__wait_timeout
			target_repos = self.__resolve_target_repos() if 0.0 < self.__wait_timeout else []
			lease_wait_s = self.__wait_active_leases(target_repos, deadline) if target_repos else 0.0
			res, attempts, retry_wait_s, exec_s = self.__execute_retries(deadline)
			res.update(retryable=False, lease_wait_seconds=round(lease_wait_s, 3), retry_wait_seconds=round(retry_wait_s, 3), execution_seconds=round(exec_s, 3), total_seconds=round(time.monotonic() - started, 3))
			if 1 < attempts or 0.0 < self.__wait_timeout:
				res['waited_seconds'] = round(lease_wait_s + retry_wait_s, 3)
			r = res
		return r
