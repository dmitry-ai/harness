# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Core.lib.array.first import df_first
from Df.Harness.Tdd.OutcomeParser import OutcomeParser
_BG_HEADER_SPLIT_RE = OutcomeParser.BG_HEADER_SPLIT_RE
_BG_TASK_FINISHED_RE = OutcomeParser.BG_TASK_FINISHED_RE
_BG_TASK_ID_RE = OutcomeParser.BG_TASK_ID_RE
_BG_TASK_LOG_RE = OutcomeParser.BG_TASK_LOG_RE
_EXIT_CODE_RE = OutcomeParser.EXIT_CODE_RE
_INVOCATION_ERROR_RE = OutcomeParser.INVOCATION_ERROR_RE
_OUTPUT_BODY_SPLIT_RE = OutcomeParser.OUTPUT_BODY_SPLIT_RE
_ZERO_TESTS_RE = OutcomeParser.ZERO_TESTS_RE
# @used-by :mod:`agent_tools.tdd.outcomes`
def _infer_exit_code_from_log_text(text: str) -> int | None:
	return OutcomeParser.infer_exit_code_from_log_text(text)
# @used-by :func:`agent_tools.issue_first_bg._bg_fin_outputs()`
# @used-by :func:`agent_tools.issue_first_bg._register_bg_issue_tasks()`
# @used-by :mod:`agent_tools.tdd.outcomes`
def _uri_to_local_path(uri: str) -> Path | None:
	return OutcomeParser.uri_to_local_path(uri)
# @used-by :func:`agent_tools.issue_first_bg._register_bg_issue_tasks()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__update_bg_tasks()`
# @used-by :mod:`agent_tools.tdd.outcomes`
def extract_bg_task_ids(text: str) -> list[str]:
	return OutcomeParser.extract_bg_task_ids(text)
# @used-by :func:`Df.Harness.lib.completion_child_trace.dfh_scan_child_trace_turn()`
# @used-by :func:`Df.Harness.lib.hook_verif_ops._inspect_shadow_call()`
# @used-by :func:`Df.Harness.lib.hook_verif_ops.dfh_classify_shadow_output()`
# @used-by :func:`agent_tools.cli_command_grounding._is_passing_output()`
# @used-by :func:`agent_tools.cli_command_grounding._record_call_outcome()`
# @used-by :func:`agent_tools.doc5_context._inspect_call_failure()`
# @used-by :func:`agent_tools.doc5_context._is_failed_cli_output()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__handle_system_message()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__visit_subagent_row()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_output_row()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_subagent_output()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_first_last_starts_with_and_is_windows_delegation_to_df()`
# @used-by :meth:`test_pytest_xdist_runner.PytestXdistRunnerTests.test_parse_command_outcome_handles_pytest_xdist_pass_fail_and_exit_code_5()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_outcomes_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_chronological_tdd_state_machine_and_commit_reset()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_hardening_header_exit_code_indirect_source_read_and_index_blob()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_parse_command_outcome_sync_codex_and_background_task_log()`
# @used-by :mod:`agent_tools.tdd.outcomes`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def parse_command_outcome(outputs: list[str] | tuple[str, ...] | str, *, task_log_paths: list[Path] | None=None) -> dict:
	return OutcomeParser(outputs, task_log_paths=task_log_paths, first_fn=df_first).parse()
__all__ = ['_BG_HEADER_SPLIT_RE', '_BG_TASK_FINISHED_RE', '_BG_TASK_ID_RE', '_BG_TASK_LOG_RE', '_EXIT_CODE_RE', '_INVOCATION_ERROR_RE', '_OUTPUT_BODY_SPLIT_RE', '_ZERO_TESTS_RE', '_infer_exit_code_from_log_text', '_uri_to_local_path', 'extract_bg_task_ids', 'parse_command_outcome']
