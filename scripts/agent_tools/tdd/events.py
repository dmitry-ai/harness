# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.EventsExtractor import EventsExtractor
# @used-by :meth:`test_multiturn_handoff_stop_guard_and_schedule_m1.MultiturnHandoffStopGuardAndScheduleM1Tests.test_schedule_timers_and_stdout_prose_do_not_merge_completed_turn1_into_turn2()`
# @used-by :mod:`agent_tools.tdd.events`
def _antigravity_segment_is_interrupted(seg_rows: list[dict]) -> bool:
	return EventsExtractor.antigravity_segment_is_interrupted(seg_rows)
# @used-by :mod:`agent_tools.tdd.events`
def _is_git_commit_command(cmd: str, *, cwd: Path | None=None) -> tuple[bool, Path | None]:
	return EventsExtractor.is_git_commit_command(cmd, cwd=cwd)
# @used-by :meth:`Df.Harness.Issue.IssueFirstBgScanner.IssueFirstBgScanner.__dispatch_single_call()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_events_module_behavior_and_parity()`
# @used-by :mod:`agent_tools.tdd.events`
def _normalize_args_dict(raw_args) -> dict:
	return EventsExtractor.normalize_args_dict(raw_args)
# @used-by :mod:`agent_tools.tdd.events`
def _unwrap_arg_value(val):
	return EventsExtractor.unwrap_arg_value(val)
# @used-by :func:`Df.Harness.lib.trace_effects._record_shell_tdd()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_parallel_deleted_worktrees_isolate_tdd_scopes_and_accept_main_full_green()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_evaluator_exempts_comment_only_test_edits_in_idle_and_post_green()`
# @used-by :meth:`test_diff_executability_telemetry.DiffExecutabilityTelemetryTests.test_evaluate_tdd_events_records_exempt_edits_without_state_transition()`
# @used-by :meth:`test_failfast_and_schedule_gate.FailFastAndScheduleGateTests.test_tdd_gate_records_non_failfast_full_suite_warning_without_breaking_verified()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_classify_test_command_recognizes_harness_run_tests_full_and_filtered()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_linked_worktree_scope_accepts_full_suite_green_on_main_repo()`
# @used-by :meth:`test_pytest_xdist_runner.PytestXdistRunnerTests.test_tdd_state_machine_rejects_exit_5_red_and_accepts_xdist_full_green()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_evaluator_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_lazy_exemption_and_full_green_edge_cases()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_memoizes_exemption_and_allows_exempt_only_edits()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_combined_git_commit_and_full_test_command_updates_full_green()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_subagent_events_sharing_parent_step_preserve_sub_step_order()`
# @used-by :mod:`agent_tools.tdd.events`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def build_command_tdd_event(step: int, cmd: str, outputs: list[str] | tuple[str, ...] | str, *, cwd: Path | None=None, scope_hint: Path | None=None, sub_step: int | None=None, subagent_id: str | None=None) -> dict:
	return EventsExtractor.build_command_event(step, cmd, outputs, cwd=cwd, scope_hint=scope_hint, sub_step=sub_step, subagent_id=subagent_id)
# @used-by :func:`Df.Harness.lib.trace_effects._record_patch_effects()`
# @used-by :func:`test_diff_executability_contract._verify_tdd_gate_delegation()`
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
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_auditor_and_evaluator_accept_committed_mechanical_diff_and_reject_drift()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_combined_git_commit_and_full_test_command_updates_full_green()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_subagent_events_sharing_parent_step_preserve_sub_step_order()`
# @used-by :meth:`test_worktree_comment_exemption.WorktreeCommentExemptionTests.test_deleted_sibling_and_nested_worktree_comment_only_commits_are_exempt()`
# @used-by :meth:`test_worktree_comment_exemption.WorktreeCommentExemptionTests.test_deleted_worktree_non_comment_code_commit_remains_blocked()`
# @used-by :mod:`agent_tools.tdd.events`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def build_file_write_tdd_event(step: int, raw_path: str | Path, *, cwd: Path | None=None, content: str | None=None, sub_step: int | None=None, subagent_id: str | None=None) -> dict:
	return EventsExtractor.build_file_write_event(step, raw_path, cwd=cwd, content=content, sub_step=sub_step, subagent_id=subagent_id)
# @used-by :func:`agent_tools.tdd.enforcement.evaluate_pre_tool_use_tdd()`
# @used-by :meth:`test_background_wait_and_tdd_inheritance.BackgroundWaitAndTddInheritanceTests.test_completed_prior_turn_does_not_bleed_tdd_events_into_unrelated_followup()`
# @used-by :meth:`test_background_wait_and_tdd_inheritance.BackgroundWaitAndTddInheritanceTests.test_unfinished_background_run_command_and_russian_stub_merge_and_preserve_tdd_full_gate()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_in_process_cache_shares_single_disk_read_across_pre_tool_gates()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_events_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_extract_antigravity_tdd_events_handles_compact_and_full_transcripts()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_denied_write_tool_call_is_excluded_from_tdd_events()`
# @used-by :mod:`agent_tools.tdd.events`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def extract_antigravity_tdd_events(transcript_path: Path, *, cwd: Path | None=None) -> list[dict]:
	return EventsExtractor(transcript_path, cwd=cwd).extract()
# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.build_code_write_event()`
# @used-by :mod:`agent_tools.tdd.events`
def is_denied_write_output(outputs) -> bool:
	return EventsExtractor.is_denied_write_output(outputs)
# @used-by :func:`Df.Harness.lib.trace_effects._record_file_tool_effects()`
# @used-by :func:`Df.Harness.lib.trace_effects._record_shell_tdd()`
# @used-by :mod:`agent_tools.tdd.events`
def record_tdd_tool_write_event(acc: dict, step: int, raw_path: str | Path, *, cwd: Path | None=None, content: str | None=None, cmd_outputs=None, sub_step: int | None=None, subagent_id: str | None=None) -> dict | None:
	return EventsExtractor.record_tool_write_event(acc, step, raw_path, cwd=cwd, content=content, cmd_outputs=cmd_outputs, sub_step=sub_step, subagent_id=subagent_id)
__all__ = ['_antigravity_segment_is_interrupted', '_is_git_commit_command', '_normalize_args_dict', '_unwrap_arg_value', 'build_command_tdd_event', 'build_file_write_tdd_event', 'extract_antigravity_tdd_events', 'is_denied_write_output', 'record_tdd_tool_write_event']
