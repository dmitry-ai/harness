# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Git.LandingLease import LandingLease
from Df.Harness.Git.RepoGate import RepoGate
from agent_tools.issues.git_read_cache import _parse_porcelain_z
import time
DEFAULT_WAIT_POLL_SECONDS = 1.0
DEFAULT_WAIT_TIMEOUT_SECONDS = 180.0
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class RepoWaiter:
	# @used-by :func:`agent_tools.repo_wait.wait_for_repo()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__wait_active_leases()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def __init__(self, repo: Path | str, *, clean: bool=False, lease_free: bool=False, timeout: float=DEFAULT_WAIT_TIMEOUT_SECONDS, poll_interval: float=DEFAULT_WAIT_POLL_SECONDS, leases_dir: Path | None=None) -> None:
		resolved = Path(repo).resolve()
		self.__main_repo = RepoGate(resolved).main_repo() if (resolved / '.git').exists() else resolved
		self.__req_clean = bool(clean or (not lease_free))
		self.__req_lease = bool(lease_free or (not clean))
		self.__timeout = max(0.0, float(timeout))
		self.__poll = float(poll_interval)
		self.__leases_dir = leases_dir
	# @used-by :meth:`RepoWaiter.__probe()`
	def __dirty_files(self) -> list[str]:
		proc = RepoGate(self.__main_repo).run_read(['status', '--porcelain', '-z'], check=False)
		raw = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else ''
		return _parse_porcelain_z(raw)
	# @used-by :meth:`RepoWaiter.wait()`
	def __probe(self) -> dict[str, Any]:
		st = LandingLease(self.__main_repo, leases_dir=self.__leases_dir).status()
		dirty = self.__dirty_files() if self.__req_clean else []
		is_clean, is_free = (not dirty, bool(st.get('free')))
		ready = (is_clean or (not self.__req_clean)) and (is_free or (not self.__req_lease))
		return {'ready': ready, 'clean': is_clean, 'lease_free': is_free, 'dirty_files': dirty, 'holder': st.get('holder'), 'queue_length': len(st.get('queue') or [])}
	# @used-by :func:`agent_tools.repo_wait.wait_for_repo()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__wait_active_leases()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	def wait(self) -> dict[str, Any]:
		started = time.monotonic()
		deadline = started + self.__timeout
		probe = self.__probe()
		while not probe['ready']:
			rem = deadline - time.monotonic()
			if 0.0 >= rem:
				break
			time.sleep(min(max(0.01, self.__poll), rem))
			probe = self.__probe()
		ready = bool(probe['ready'])
		return {'valid': ready, 'ready': ready, 'timed_out': not ready, 'retryable': not ready, 'elapsed_seconds': round(time.monotonic() - started, 3), 'repo': self.__main_repo.as_posix(), 'clean_required': self.__req_clean, 'lease_free_required': self.__req_lease, 'clean': probe['clean'], 'lease_free': probe['lease_free'], 'dirty_files': probe['dirty_files'], 'holder': probe['holder'], 'holder_alive': None is not probe['holder'], 'queue_length': probe['queue_length']}
