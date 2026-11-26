# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.CommandInspector import CommandInspector
_HARNESS_WATCHDOG_PREFIX_RE = CommandInspector.HARNESS_WATCHDOG_PREFIX_RE
_RIGGED_FAILURE_RE = CommandInspector.RIGGED_FAILURE_RE
_SHELL_DELETE_RE = CommandInspector.SHELL_DELETE_RE
_SHELL_TEST_FILE_TOKEN_RE = CommandInspector.SHELL_TEST_FILE_TOKEN_RE
_SHELL_WRITE_CMD_PATTERNS = CommandInspector.SHELL_WRITE_CMD_PATTERNS
# @used-by :mod:`agent_tools.tdd.commands`
def _extract_cmd_paths(seg: str) -> list[str]:
	return CommandInspector.extract_cmd_paths(seg)
# @used-by :mod:`agent_tools.tdd.commands`
def _mask_quoted(seg: str) -> str:
	return CommandInspector.mask_quoted(seg)
# @used-by :mod:`agent_tools.tdd.commands`
def _single_test_file_in_args(seg: str) -> bool:
	return CommandInspector.single_test_file_in_args(seg)
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_clean_null_and_unique_fast_delegation_to_df()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_classify_run_tests_full_and_filtered()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_classify_test_command_recognizes_harness_run_tests_full_and_filtered()`
# @used-by :meth:`test_pytest_xdist_runner.PytestXdistRunnerTests.test_classify_pytest_xdist_full_suite_and_filtered()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_commands_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_chronological_tdd_state_machine_and_commit_reset()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_test_command_detection_full_suite_vs_single_and_rigged_rejection()`
# @used-by :meth:`test_watchdog_and_timeout_gate.WatchdogAndTimeoutGateTests.test_non_test_command_mentioning_pytest_in_quoted_arg_is_ignored()`
# @used-by :meth:`test_watchdog_and_timeout_gate.WatchdogAndTimeoutGateTests.test_tdd_classify_unwraps_test_watchdog_prefix_for_scope_and_full_suite()`
# @used-by :mod:`agent_tools.tdd.commands`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def classify_test_command(cmd: str, *, scope_root: Path | None=None) -> dict:
	return CommandInspector(cmd, scope_root=scope_root).classify_test_command()
# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_shell_write_targets_detects_test_production_and_doc_writes()`
# @used-by :meth:`test_shell_herestring_write_targets_m4.ShellHerestringWriteTargetsM4Tests.test_ignores_arrows_and_html_inside_powershell_herestring()`
# @used-by :meth:`test_shell_herestring_write_targets_m4.ShellHerestringWriteTargetsM4Tests.test_ignores_double_quoted_herestring_and_bash_heredoc_bodies()`
# @used-by :meth:`test_shell_herestring_write_targets_m4.ShellHerestringWriteTargetsM4Tests.test_preserves_real_shell_redirects_and_embedded_code_writes()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_commands_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_shell_code_write_targets_and_ratchet_issue_evidence()`
# @used-by :mod:`agent_tools.tdd.commands`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def shell_code_write_targets(cmd: str, *, cwd: Path | None=None) -> list[Path]:
	return CommandInspector.shell_code_write_targets(cmd, cwd=cwd)
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_commands_module_behavior_and_parity()`
# @used-by :mod:`agent_tools.tdd.commands`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def shell_test_delete_targets(cmd: str, *, cwd: Path | None=None) -> list[Path]:
	return CommandInspector.shell_test_delete_targets(cmd, cwd=cwd)
# @used-by :func:`agent_tools.issue_first_bg._handle_run_command_call()`
# @used-by :func:`agent_tools.issue_first_gate.evaluate_pre_tool_use_issue_first()`
# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_shell_write_targets_detects_test_production_and_doc_writes()`
# @used-by :meth:`test_shell_herestring_write_targets_m4.ShellHerestringWriteTargetsM4Tests.test_ignores_arrows_and_html_inside_powershell_herestring()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_commands_module_behavior_and_parity()`
# @used-by :mod:`agent_tools.tdd.commands`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def shell_write_targets(cmd: str, *, cwd: Path | None=None, classifications: tuple[str, ...] | None=None) -> list[Path]:
	return CommandInspector.shell_write_targets(cmd, cwd=cwd, classifications=classifications)
# @used-by :mod:`agent_tools.tdd.commands`
def unwrap_watchdog_prefix(seg: str) -> str:
	return CommandInspector.unwrap_watchdog_prefix(seg)
__all__ = ['_HARNESS_WATCHDOG_PREFIX_RE', '_RIGGED_FAILURE_RE', '_SHELL_DELETE_RE', '_SHELL_TEST_FILE_TOKEN_RE', '_SHELL_WRITE_CMD_PATTERNS', '_extract_cmd_paths', '_mask_quoted', '_single_test_file_in_args', 'classify_test_command', 'shell_code_write_targets', 'shell_test_delete_targets', 'shell_write_targets', 'unwrap_watchdog_prefix']
