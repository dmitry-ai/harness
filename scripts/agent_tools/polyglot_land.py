# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Git.DirtyMainChecker import DirtyMainChecker
from Df.Harness.Git.PolyglotTestRunner import PolyglotTestRunner
from Df.Harness.Git.RepoHealthChecker import RepoHealthChecker
from Df.Harness.Git.VerificationSpecResolver import VerificationSpecResolver
import subprocess
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :mod:`agent_tools.polyglot_land`
def dirty_blocking_main_files(main_repo: Path, branch: str) -> list[str]:
	return DirtyMainChecker(main_repo, branch).find_blocking()
# @used-by :mod:`agent_tools.polyglot_land`
def resolve_repo_verification_spec(main_repo: Path, wt_path: Path | None=None, *, slug: str | None=None) -> dict[str, Any] | None:
	return VerificationSpecResolver(main_repo, wt_path, slug=slug).resolve()
# @used-by :func:`agent_tools.worktree_flow._rebase_and_test()`
# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_host_state_mutation_fails_closed_while_heartbeat_timestamp_is_ignored()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly()`
# @used-by :mod:`agent_tools.polyglot_land`
def run_polyglot_land_tests(main_repo: Path, wt_path: Path, *, spec: dict[str, Any] | None=None, base_ref: str | None=None) -> tuple[bool, dict[str, Any] | None]:
	return PolyglotTestRunner(main_repo, wt_path, spec=spec, base_ref=base_ref, run_fn=subprocess.run).run()
# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_check_close_companion_health()`
# @used-by :func:`agent_tools.worktree_flow._merge_and_finalize()`
# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_post_land_health_passes_ready_skips_unavailable_and_blocks_error()`
# @used-by :mod:`agent_tools.polyglot_land`
def run_repo_health_check(code_repo: Path, *, slug: str | None=None, spec: dict[str, Any] | None=None, force: bool=False) -> dict[str, Any]:
	return RepoHealthChecker(code_repo, slug=slug, spec=spec, force=force, run_fn=subprocess.run).check()
__all__ = ['dirty_blocking_main_files', 'resolve_repo_verification_spec', 'run_polyglot_land_tests', 'run_repo_health_check']
