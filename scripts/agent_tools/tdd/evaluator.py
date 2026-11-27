# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.Evaluator import Evaluator
from .exemption import is_write_event_exempt
# @used-by :mod:`agent_tools.tdd.evaluator`
def _command_matches_scope(event: dict, scope_str: str, written_test_files: set[str]) -> bool:
	return Evaluator.command_matches_scope(event, scope_str, written_test_files)
# @used-by :mod:`agent_tools.tdd.evaluator`
def _git_main_repo_root(repo: Path) -> Path:
	return Evaluator.git_main_repo_root(repo)
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_tdd_status()`
# @used-by :func:`test_diff_executability_contract._verify_tdd_gate_delegation()`
# @used-by :meth:`test_background_wait_and_tdd_inheritance.BackgroundWaitAndTddInheritanceTests.test_completed_prior_turn_does_not_bleed_tdd_events_into_unrelated_followup()`
# @used-by :meth:`test_background_wait_and_tdd_inheritance.BackgroundWaitAndTddInheritanceTests.test_unfinished_background_run_command_and_russian_stub_merge_and_preserve_tdd_full_gate()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_parallel_deleted_worktrees_isolate_tdd_scopes_and_accept_main_full_green()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_evaluator_exempts_comment_only_test_edits_in_idle_and_post_green()`
# @used-by :meth:`test_diff_executability_telemetry.DiffExecutabilityTelemetryTests.test_evaluate_tdd_events_records_exempt_edits_without_state_transition()`
# @used-by :meth:`test_failfast_and_schedule_gate.FailFastAndScheduleGateTests.test_tdd_gate_records_non_failfast_full_suite_warning_without_breaking_verified()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_classify_test_command_recognizes_harness_run_tests_full_and_filtered()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_linked_worktree_scope_accepts_full_suite_green_on_main_repo()`
# @used-by :meth:`test_pytest_xdist_runner.PytestXdistRunnerTests.test_tdd_state_machine_rejects_exit_5_red_and_accepts_xdist_full_green()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_evaluator_skips_tdd_red_and_full_gates_for_comment_only_write()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_evaluator_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_lazy_exemption_and_full_green_edge_cases()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_memoizes_exemption_and_allows_exempt_only_edits()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_chronological_tdd_state_machine_and_commit_reset()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_extract_antigravity_tdd_events_handles_compact_and_full_transcripts()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_auditor_and_evaluator_accept_committed_mechanical_diff_and_reject_drift()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_combined_git_commit_and_full_test_command_updates_full_green()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_subagent_events_sharing_parent_step_preserve_sub_step_order()`
# @used-by :meth:`test_worktree_comment_exemption.WorktreeCommentExemptionTests.test_deleted_sibling_and_nested_worktree_comment_only_commits_are_exempt()`
# @used-by :meth:`test_worktree_comment_exemption.WorktreeCommentExemptionTests.test_deleted_worktree_non_comment_code_commit_remains_blocked()`
# @used-by :mod:`agent_tools.tdd.evaluator`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def evaluate_tdd_events(events: list[dict], *, require_final_full_green: bool=True, project_root: Path | None=None) -> dict:
	return Evaluator(events, require_final_full_green=require_final_full_green, project_root=project_root, is_exempt_fn=is_write_event_exempt).evaluate()
__all__ = ['_command_matches_scope', '_git_main_repo_root', 'evaluate_tdd_events']
