# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Runtime.SnapshotPromoter import SnapshotPromoter
from Df.Harness.lib.runtime_launcher_templates import GIT_HOOK_LAUNCHER_HEADER, HOOK_RUNNER_HEADER, dfh_git_hook_shell_wrapper as git_hook_shell_wrapper
from Df.Harness.lib.runtime_snapshot_ops import ARCHIVE_TARGETS as _ARCHIVE_TARGETS, DEFAULT_KEEP_RELEASES, GIT_HOOK_NAMES, NO_WINDOW as _NO_WINDOW, REQUIRED_ENTRYPOINTS, VALIDATION_PROBE as _VALIDATION_PROBE, dfh_check_runtime_snapshot as check_runtime_snapshot, dfh_deploy_git_hooks as _deploy_git_hooks, dfh_effective_git_hooks_dir as effective_git_hooks_dir, dfh_ensure_repo_git_hooks as ensure_repo_git_hooks, dfh_export_git_archive as _export_git_archive, dfh_finalize_native_install, dfh_git_read as _git_read, dfh_has_git_head as _has_git_head, dfh_is_harness_code_repo as is_harness_code_repo, dfh_read_pointer as _read_pointer, dfh_rotate_releases as _rotate_releases, dfh_runtime_store_dir as runtime_store_dir, dfh_safe_extract_tar as _safe_extract_tar, dfh_set_local_hooks_path as _set_local_hooks_path, dfh_validate_staged_release
from .runtime_launchers import git_hook_launcher_source, harness_hook_runner_source
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_validate_staged_release()`
# @used-by :func:`promote_runtime_snapshot()`
def _canary_via_facade(staging: Path) -> tuple[bool, str]:
	from .snapshot_canary import run_pre_tool_use_canary
	return run_pre_tool_use_canary(staging)
# @used-by unused
def _validate_staged_release(staging: Path, canonical_primary: Path, entrypoints: tuple[str, ...], *, run_canary: bool=True) -> tuple[bool, str]:
	return dfh_validate_staged_release(staging, canonical_primary, entrypoints, run_canary=run_canary, canary_fn=_canary_via_facade)
# @used-by :func:`agent_tools.git_ignore.finalize_install_result()`
# @used-by :mod:`agent_tools.runtime_snapshot`
def finalize_native_install(result: dict, primary: Path, *, check: bool) -> dict:
	return dfh_finalize_native_install(result, primary, check=check, promote_fn=promote_runtime_snapshot)
# @used-by :func:`finalize_native_install()`
# @used-by :func:`test_hook_runner_watchdog._seed_two_releases()`
# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__maybe_promote_snapshot()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_runtime_snapshot_canary_skips_non_executable_and_runs_for_code_or_config()`
# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_snapshot_promotion_and_auditor_reject_undefined_global()`
# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_broken_head_rejected_by_validation_preserving_current()`
# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_ensure_hooks_uses_deployed_immutable_git_hooks_dir()`
# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_lkg_fallback_runs_previous_release_when_current_crashes()`
# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_promote_exports_snapshot_surviving_live_tree_corruption_and_preserving_anchor()`
# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_release_rotation_keeps_latest_five_and_retains_lkg()`
# @used-by :meth:`test_snapshot_canary_and_hook_crash_audit.SnapshotCanaryAndHookCrashAuditTests.test_promote_rejects_chatty_pre_tool_use_snapshot_and_keeps_current()`
# @used-by :meth:`test_snapshot_canary_and_hook_crash_audit.SnapshotCanaryAndHookCrashAuditTests.test_promote_rejects_slow_pre_tool_use_snapshot_and_keeps_current()`
# @used-by :meth:`test_snapshot_latency_and_delegation_policy.SnapshotLatencyAndDelegationPolicyTests.test_fallback_spike_blocks_promotion_only_when_strict_and_ignores_historical_lines()`
# @used-by :meth:`test_snapshot_latency_and_delegation_policy.SnapshotLatencyAndDelegationPolicyTests.test_promote_rejects_large_transcript_slow_snapshot_and_accepts_fast_snapshot()`
# @used-by :mod:`agent_tools.runtime_snapshot`
def promote_runtime_snapshot(primary: str | Path, *, store_dir: str | Path | None=None, keep: int=DEFAULT_KEEP_RELEASES, entrypoints: tuple[str, ...]=REQUIRED_ENTRYPOINTS, configure_repo_hooks: bool=True, fail_on_fallback_spike: bool=False, base_ref: str | None=None) -> dict:
	return SnapshotPromoter(primary, store_dir=store_dir, keep=keep, entrypoints=entrypoints, configure_repo_hooks=configure_repo_hooks, fail_on_fallback_spike=fail_on_fallback_spike, base_ref=base_ref, canary_fn=_canary_via_facade).run()
__all__ = ['DEFAULT_KEEP_RELEASES', 'GIT_HOOK_LAUNCHER_HEADER', 'GIT_HOOK_NAMES', 'HOOK_RUNNER_HEADER', 'REQUIRED_ENTRYPOINTS', 'check_runtime_snapshot', 'effective_git_hooks_dir', 'ensure_repo_git_hooks', 'finalize_native_install', 'git_hook_launcher_source', 'git_hook_shell_wrapper', 'harness_hook_runner_source', 'is_harness_code_repo', 'promote_runtime_snapshot', 'runtime_store_dir']
