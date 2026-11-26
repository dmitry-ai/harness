# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Git.RepoWaiter import DEFAULT_WAIT_POLL_SECONDS, DEFAULT_WAIT_TIMEOUT_SECONDS, RepoWaiter
from Df.Harness.Git.RetryableError import RetryableError as RetryableOperationError
from Df.Harness.Git.TransientWaitRunner import TransientWaitRunner
from .path_registry import project_paths
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
# @used-by :func:`Df.Harness.lib.cli_input.dfh_operation_error_payload()`
def is_transient_contention_error(exc: BaseException, root: Path | None=None) -> bool:
	return bool(TransientWaitRunner(root).run(probe_exc=exc))
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare()`
# @used-by :meth:`test_observability_diagnostics.ObservabilityDiagnosticsTests.test_run_with_transient_wait_separates_lease_retry_and_execution_seconds()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_blocks_when_turn_touches_leased_repo_or_worktree()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_bypasses_foreign_lease_on_readonly_and_noncode_turns()`
def run_with_transient_wait(root: Path, fn: Callable[[], dict[str, Any]], *, wait_timeout: float=0.0, poll_interval: float=DEFAULT_WAIT_POLL_SECONDS, wait_repos: list[Path] | tuple[Path, ...] | None=None, conversation: str | None=None, platform: str | None=None, backend: Path | str | None=None) -> dict[str, Any]:
	return TransientWaitRunner(root, fn, wait_timeout=wait_timeout, poll_interval=poll_interval, wait_repos=wait_repos, conversation=conversation, platform=platform, backend=backend).run()
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_wait_repo()`
# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_wait_repo_reacts_to_lease_release_dead_pid_and_clean_tree()`
def wait_for_repo(repo: Path | str, *, clean: bool=False, lease_free: bool=False, timeout: float=DEFAULT_WAIT_TIMEOUT_SECONDS, poll_interval: float=DEFAULT_WAIT_POLL_SECONDS, leases_dir: Path | None=None) -> dict[str, Any]:
	return RepoWaiter(repo, clean=clean, lease_free=lease_free, timeout=timeout, poll_interval=poll_interval, leases_dir=leases_dir).wait()
