# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.text.starts_ends import df_starts_with
from Df.Harness.Issue.IssueFirstEvaluator import IssueFirstEvaluator
from Df.Harness.Issue.IssueFirstPreToolEvaluator import IssueFirstPreToolEvaluator
from Df.Harness.lib.issue import dfh_is_df_issue_command_text, dfh_is_excluded_meta_rel
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_first_last_starts_with_and_is_windows_delegation_to_df()`
def _is_excluded_meta_rel(rel_posix: str) -> bool:
	return dfh_is_excluded_meta_rel(rel_posix, starts_with_fn=df_starts_with)
# @used-by :func:`Df.Harness.lib.trace_effects._record_file_tool_effects()`
# @used-by :func:`Df.Harness.lib.trace_effects._record_patch_effects()`
# @used-by :func:`Df.Harness.lib.trace_effects._record_shell_issue_first()`
def build_code_write_issue_first_event(step: int, raw_path: str | Path, *, cwd: Path | None=None, content: str | None=None, sub_step: int | None=None, cmd_outputs=None) -> dict | None:
	return IssueFirstPreToolEvaluator.build_code_write_event(step, raw_path, cwd=cwd, content=content, sub_step=sub_step, cmd_outputs=cmd_outputs)
# @used-by :func:`Df.Harness.lib.completion_child_trace._handle_child_output_item()`
# @used-by :func:`Df.Harness.lib.trace_effects._record_shell_issue_first()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_output_row()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_subagent_output()`
def build_issue_action_events(step: int, cmd: str, outputs: list[str] | tuple[str, ...] | str, *, sub_step: int | None=None) -> list[dict]:
	return IssueFirstPreToolEvaluator.build_issue_action_events(step, cmd, outputs, sub_step=sub_step)
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_issue_first_status()`
# @used-by :meth:`test_comment_exemption_and_denied_writes.CommentExemptionAndDeniedWritesTests.test_issue_first_skips_denied_writes_and_reads_background_task_issue_actions()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_chronological_state_machine_enforces_parent_issue_before_tests_and_code()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_user_input_seeding_accepts_referenced_open_evidence_and_rejects_closed_or_unreferenced()`
def evaluate_issue_first_events(events: list[dict] | tuple[dict, ...] | None, *, requests: list | tuple | None=None, project_root: Path | None=None) -> dict:
	return IssueFirstEvaluator(events, requests=requests, project_root=project_root).evaluate()
# @used-by :meth:`Df.Harness.Gate.IssueFirstPreToolGate.IssueFirstPreToolGate.check()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_child_subagent_blocked_when_parent_issue_closed_or_missing_evidence()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_child_subagent_inherits_verified_open_parent_from_turn_state_and_summary_db()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_evaluate_pre_tool_use_issue_first_blocks_spoofing_and_enforces_live_order()`
def evaluate_pre_tool_use_issue_first(name: str, args: dict, payload: dict) -> str | None:
	return IssueFirstPreToolEvaluator(name, args, payload).evaluate()
# @used-by :meth:`test_comment_exemption_and_denied_writes.CommentExemptionAndDeniedWritesTests.test_issue_first_skips_denied_writes_and_reads_background_task_issue_actions()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_in_process_cache_shares_single_disk_read_across_pre_tool_gates()`
def extract_antigravity_issue_first_events(transcript_path: Path, *, cwd: Path | None=None) -> tuple[list[dict], list[dict]]:
	return IssueFirstPreToolEvaluator.extract_antigravity_events(transcript_path, cwd=cwd)
# @used-by :func:`Df.Harness.lib.completion_child_trace._handle_child_call_item()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_subagent_call()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_tool_call_row()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_extract_issue_actions_recognizes_fetch_and_anti_spoofing_command_check()`
# @used-by :meth:`test_issue_preflight_and_batch.IssuePreflightAndBatchTests.test_batch_create_verifies_readback_and_action_extraction()`
def is_df_github_issue_command(cmd: str) -> bool:
	return dfh_is_df_issue_command_text(cmd)
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_resolve_issue_first_target_distinguishes_github_backed_local_and_metadata_paths()`
def resolve_issue_first_target(path: str | Path, *, content: str | None=None) -> dict | None:
	return IssueFirstPreToolEvaluator.resolve_target(path, content=content)
