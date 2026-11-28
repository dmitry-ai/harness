# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.text.trim import df_trim_text_left
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Git.WorktreeCleaner import WorktreeCleaner
from Df.Harness.Git.WorktreeCreator import WorktreeCreator
from Df.Harness.Git.WorktreeMerger import WorktreeMerger
from Df.Harness.Git.WorktreePathResolver import WorktreePathResolver
from Df.Harness.Git.WorktreeRebaseVerifier import WorktreeRebaseVerifier
from Df.Harness.Git.WorktreeStatusInspector import WorktreeStatusInspector
from Df.Harness.lib.worktree import dfh_attach_land_telemetry, dfh_fail_land, dfh_git_config_file, dfh_git_exec
from . import polyglot_land, worktree_guard
from .git_gate import GitRepoGate
from .git_ignore import ensure_worktree_dir_ignored
from .path_registry import project_paths
import subprocess
LAND_STAGE_POLICIES: dict[str, str] = {
	'diff_coverage': 'executable_only',
	'ff_merge': 'always',
	'polyglot_tests': 'executable_only',
	'post_land_health': 'executable_only',
	'push': 'always',
	'python_integrity': 'always',
	'rebase': 'always',
	'snapshot_canary': 'executable_only',
	'snapshot_promote': 'always',
	'tag': 'always',
	'tests': 'executable_only',
	'worktree_cleanup': 'always',
	'xref_integrity': 'always',
}
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_normalize_and_trim_delegation_to_df()`
def _apply_porcelain_line(cur: dict, line: str) -> None:
	if line.startswith('worktree '):
		cur['path'] = Path(line[9:].strip()).resolve().as_posix()
	elif line.startswith('HEAD '):
		cur['head'] = line[5:].strip()
	elif line.startswith('branch '):
		cur['branch'] = str(df_trim_text_left(line[7:].strip(), 'refs/heads/'))
	elif 'detached' == line:
		cur['detached'] = True
# @used-by unused
def _attach_land_telemetry(result: dict, plan: dict | None) -> dict:
	return dfh_attach_land_telemetry(result, plan)
# @used-by :func:`worktree_land()`
def _current_branch(repo: Path) -> str:
	proc = GitRepoGate(repo).run_read(['rev-parse', '--abbrev-ref', 'HEAD'], check=False)
	return proc.stdout.decode('utf-8', errors='replace').strip() if 0 == proc.returncode else ''
# @used-by unused
def _fail_land(main_repo: Path, wt_path: Path, branch: str, stage: str, error: str, *, test_runs: int=0, test_result: dict | None=None, plan: dict | None=None) -> dict:
	return dfh_fail_land(main_repo, wt_path, branch, stage, error, test_runs=test_runs, test_result=test_result, plan=plan)
# @used-by :func:`_merge_and_finalize()`
# @used-by :func:`_rebase_and_test()`
# @used-by :func:`worktree_begin()`
# @used-by :func:`worktree_cleanup()`
# @used-by :func:`worktree_land()`
def _git_exec(repo: Path, *args: str) -> subprocess.CompletedProcess:
	return dfh_git_exec(repo, *args)
# @used-by unused
def _merge_and_finalize(main_repo: Path, wt_path: Path, branch: str, target_branch: str, *, run_tests: bool=True, push: bool, remove: bool, test_runs: int, test_res: dict | None, post_merge_fn, promote_snapshot: bool | None=None, snapshot_store: Path | None=None, tag: bool=False, plan: dict | None=None) -> dict:
	return WorktreeMerger(main_repo, wt_path, branch, target_branch, run_tests=run_tests, push=push, remove=remove, test_runs=test_runs, test_res=test_res, post_merge_fn=post_merge_fn, promote_snapshot=promote_snapshot, snapshot_store=snapshot_store, tag=tag, plan=plan, git_exec_fn=_git_exec, cleanup_fn=worktree_cleanup, health_fn=polyglot_land.run_repo_health_check).merge()
# @used-by unused
def _rebase_and_test(main_repo: Path, wt_path: Path, branch: str, target_branch: str, *, run_tests: bool, workers: int | None, no_tests_reason: str | None=None) -> tuple[dict | None, int, dict | None, dict | None]:
	return WorktreeRebaseVerifier(main_repo, wt_path, branch, target_branch, run_tests=run_tests, workers=workers, no_tests_reason=no_tests_reason, git_exec_fn=_git_exec, polyglot_test_fn=polyglot_land.run_polyglot_land_tests).verify()
# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.__resolve_origin_push_target()`
def git_config_file(code_repo: Path) -> Path:
	return dfh_git_config_file(code_repo)
# @used-by :func:`prioritized_worktree_candidates()`
# @used-by :func:`worktree_land()`
# @used-by :meth:`Df.Harness.Gate.WorktreeIsolationGate.WorktreeIsolationGate.check()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_origin_repo_slug_and_linked_worktree_detection()`
def is_linked_worktree(path: Path | str) -> bool:
	return (Path(path).resolve() / '.git').is_file()
# @used-by unused
def prioritized_worktree_candidates(repo_root: str | Path | None=None, cwd: Path | None=None) -> list[Path]:
	cands: list[Path] = []
	if None is not repo_root and str(repo_root).strip():
		cands.append(Path(repo_root).resolve())
	eff_cwd = Path(cwd).resolve() if None is not cwd else Path.cwd().resolve()
	for anc in (eff_cwd, *eff_cwd.parents):
		if is_linked_worktree(anc):
			cands.append(anc)
			break
	return cands
# @used-by :meth:`Df.Harness.Tdd.DiffCoverage.DiffCoverage.__touched_git_repos()`
def resolve_touched_repo_file(path: Path, is_tracked_fn) -> tuple[Path, str] | None:
	return WorktreePathResolver(path, is_tracked_fn).resolve()
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_worktree_begin()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_antigravity_ps_deleted_worktree_commit_rebase_and_land_green()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_child_subagent_blocked_when_parent_issue_closed_or_missing_evidence()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_child_subagent_inherits_verified_open_parent_from_turn_state_and_summary_db()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_parallel_deleted_worktrees_isolate_tdd_scopes_and_accept_main_full_green()`
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_worktree_land_blocks_uncovered_new_function_and_passes_when_covered()`
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_worktree_land_handles_cross_cutting_commit_and_diff_coverage_timeout()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_polyglot_land_skips_tests_and_health_for_comment_only_js()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_worktree_land_blocks_no_tests_on_executable_and_allows_audited_reason()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_worktree_land_skips_tests_for_non_executable_and_runs_for_executable()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_worktree_land_passes_prev_head_base_ref_and_skips_canary_for_non_exec()`
# @used-by :meth:`test_diff_executability_telemetry.DiffExecutabilityTelemetryTests.test_worktree_land_attaches_telemetry_on_failed_landings()`
# @used-by :meth:`test_diff_executability_telemetry.DiffExecutabilityTelemetryTests.test_worktree_land_emits_telemetry_for_non_executable_executable_and_override()`
# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_worktree_land_enforces_answer_gate_corpus_before_merge()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_worktree_land_emits_mixed_commit_warning_and_clean_commit_has_none()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_concurrent_main_advance_retries_optimistically_and_lands()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_dirty_worktree_fails_fast_without_acquiring_lease()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_optimistic_phase1_runs_tests_without_holding_fifo_lease()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_repeated_main_collisions_fall_back_to_fifo_lease()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_blocks_when_turn_touches_leased_repo_or_worktree()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_polyglot_node_repo_runs_in_workspace_sandbox_and_lands()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_post_land_health_passes_ready_skips_unavailable_and_blocks_error()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_worktree_land_allows_whitelisted_live_runtime_data_on_main_only()`
# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_pre_commit_and_worktree_land_enforce_integrity_and_ratchet()`
# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_worktree_land_python_integrity_handles_cross_cutting_multi_file_commit()`
# @used-by :meth:`test_repo_tag_close_gate.RepoTagCloseGateTests.test_worktree_land_with_tag_tags_and_pushes_landed_commit()`
# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_worktree_land_promotes_runtime_snapshot_after_merge()`
# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_worktree_cleanup_fails_closed_with_lock_holders_on_locked_dir()`
# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_worktree_land_fails_closed_when_cleanup_is_locked()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_origin_repo_slug_and_linked_worktree_detection()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_resolve_code_anchor_maps_linked_worktree_to_canonical_main_repo()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_resolve_code_scope_keeps_active_worktree_for_new_files_and_falls_back_after_cleanup()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_two_parallel_worktrees_commit_and_land_with_single_test_run()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_worktree_land_aborts_when_tests_fail()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_worktree_scoped_issue_first_ignores_dirty_main_checkout()`
# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_begin_adds_info_exclude_without_touching_gitignore_and_blocks_160000()`
# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_begin_detects_previously_tracked_160000_gitlinks()`
# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_harness_main_blocks_write_and_edit_while_linked_worktree_allows()`
# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_non_harness_repo_allows_single_turn_and_blocks_concurrent_open_turns()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_cli_worktree_land_default_removes_and_keep_preserves()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_worktree_land_removes_worktree_and_branch_by_default()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_worktree_status_flags_missing_worktree_as_stale()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_worktree_status_flags_stale_behind_and_preserves_active_worktrees()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_worktree_land_blocks_stale_xref_and_passes_when_synced()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_worktree_land_xref_handles_cross_cutting_multi_file_commit()`
def worktree_begin(repo: Path | str, task_id: str, *, base_ref: str='main', worktrees_dir: Path | str | None=None) -> dict:
	return WorktreeCreator(repo, task_id, base_ref=base_ref, worktrees_dir=worktrees_dir, git_exec_fn=_git_exec).begin()
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_worktree_cleanup()`
# @used-by :func:`_merge_and_finalize()`
# @used-by :func:`worktree_land()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_antigravity_ps_deleted_worktree_commit_rebase_and_land_green()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_child_subagent_blocked_when_parent_issue_closed_or_missing_evidence()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_child_subagent_inherits_verified_open_parent_from_turn_state_and_summary_db()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_parallel_deleted_worktrees_isolate_tdd_scopes_and_accept_main_full_green()`
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_worktree_land_handles_cross_cutting_commit_and_diff_coverage_timeout()`
# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_worktree_land_enforces_answer_gate_corpus_before_merge()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_dirty_worktree_fails_fast_without_acquiring_lease()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_blocks_when_turn_touches_leased_repo_or_worktree()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_post_land_health_passes_ready_skips_unavailable_and_blocks_error()`
# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_worktree_cleanup_fails_closed_with_lock_holders_on_locked_dir()`
# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_worktree_land_fails_closed_when_cleanup_is_locked()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_origin_repo_slug_and_linked_worktree_detection()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_resolve_code_anchor_maps_linked_worktree_to_canonical_main_repo()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_resolve_code_scope_keeps_active_worktree_for_new_files_and_falls_back_after_cleanup()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_worktree_land_aborts_when_tests_fail()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_worktree_scoped_issue_first_ignores_dirty_main_checkout()`
# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_begin_adds_info_exclude_without_touching_gitignore_and_blocks_160000()`
# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_begin_detects_previously_tracked_160000_gitlinks()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_cli_worktree_land_default_removes_and_keep_preserves()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_worktree_land_removes_worktree_and_branch_by_default()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_worktree_status_flags_missing_worktree_as_stale()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_worktree_status_flags_stale_behind_and_preserves_active_worktrees()`
def worktree_cleanup(repo: Path | str, target: Path | str, *, force: bool=False) -> dict:
	return WorktreeCleaner(repo, target, force=force, git_exec_fn=_git_exec, lock_finder_fn=worktree_guard.find_worktree_lock_holders).cleanup()
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_worktree_land()`
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_worktree_land_blocks_uncovered_new_function_and_passes_when_covered()`
# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_worktree_land_handles_cross_cutting_commit_and_diff_coverage_timeout()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_polyglot_land_skips_tests_and_health_for_comment_only_js()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_worktree_land_blocks_no_tests_on_executable_and_allows_audited_reason()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_worktree_land_skips_tests_for_non_executable_and_runs_for_executable()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_worktree_land_passes_prev_head_base_ref_and_skips_canary_for_non_exec()`
# @used-by :meth:`test_diff_executability_telemetry.DiffExecutabilityTelemetryTests.test_worktree_land_attaches_telemetry_on_failed_landings()`
# @used-by :meth:`test_diff_executability_telemetry.DiffExecutabilityTelemetryTests.test_worktree_land_emits_telemetry_for_non_executable_executable_and_override()`
# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_worktree_land_enforces_answer_gate_corpus_before_merge()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_worktree_land_emits_mixed_commit_warning_and_clean_commit_has_none()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_concurrent_main_advance_retries_optimistically_and_lands()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_dirty_worktree_fails_fast_without_acquiring_lease()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_optimistic_phase1_runs_tests_without_holding_fifo_lease()`
# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_repeated_main_collisions_fall_back_to_fifo_lease()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_polyglot_node_repo_runs_in_workspace_sandbox_and_lands()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_post_land_health_passes_ready_skips_unavailable_and_blocks_error()`
# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_worktree_land_allows_whitelisted_live_runtime_data_on_main_only()`
# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_pre_commit_and_worktree_land_enforce_integrity_and_ratchet()`
# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_worktree_land_python_integrity_handles_cross_cutting_multi_file_commit()`
# @used-by :meth:`test_repo_tag_close_gate.RepoTagCloseGateTests.test_worktree_land_with_tag_tags_and_pushes_landed_commit()`
# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_worktree_land_promotes_runtime_snapshot_after_merge()`
# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_worktree_land_fails_closed_when_cleanup_is_locked()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_two_parallel_worktrees_commit_and_land_with_single_test_run()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_worktree_land_aborts_when_tests_fail()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_worktree_land_removes_worktree_and_branch_by_default()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_worktree_land_blocks_stale_xref_and_passes_when_synced()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_worktree_land_xref_handles_cross_cutting_multi_file_commit()`
def worktree_land(worktree: Path | str, *, target_branch: str='main', run_tests: bool=True, push: bool=False, remove: bool=True, owner: str | None=None, wait_timeout: float=600.0, leases_dir: Path | None=None, workers: int | None=None, post_merge_fn=None, promote_snapshot: bool | None=None, snapshot_store: Path | None=None, tag: bool=False, max_optimistic_retries: int=2, no_tests_reason: str | None=None) -> dict:
	from .worktree_land_flow import execute_optimistic_worktree_land
	wt_path = Path(worktree).resolve()
	if not is_linked_worktree(wt_path):
		raise ValueError(f'Not a linked git worktree: {wt_path}')
	main_repo = GitRepoGate(wt_path).main_repo()
	branch = _current_branch(wt_path)
	if None is leases_dir:
		ensure_worktree_dir_ignored(project_paths(main_repo).data_dir / 'repo-leases')
	return execute_optimistic_worktree_land(main_repo, wt_path, branch, target_branch=target_branch, run_tests=run_tests, push=push, remove=remove, owner=owner, wait_timeout=wait_timeout, leases_dir=leases_dir, workers=workers, post_merge_fn=post_merge_fn, promote_snapshot=promote_snapshot, snapshot_store=snapshot_store, tag=tag, max_optimistic_retries=max_optimistic_retries, no_tests_reason=no_tests_reason, git_exec_fn=_git_exec, cleanup_fn=worktree_cleanup, health_fn=polyglot_land.run_repo_health_check, polyglot_test_fn=polyglot_land.run_polyglot_land_tests)
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_worktree_status()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_worktree_status_flags_missing_worktree_as_stale()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_worktree_status_flags_stale_behind_and_preserves_active_worktrees()`
def worktree_status(repo: Path | str) -> dict:
	return WorktreeStatusInspector(repo).inspect()
