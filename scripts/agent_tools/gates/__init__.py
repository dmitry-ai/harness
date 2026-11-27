# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.PreToolRegistry import PreToolRegistry
from .answer_checks import run_answer_gates
from .stop_checks import run_stop_gates
_BUILTIN_TOOLS_MANIFEST = PreToolRegistry.BUILTIN_TOOLS_MANIFEST
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_arch_audit_gate_priority_manifest_and_lazy_export()`
# @used-by :meth:`test_ask_question_pre_tool_gate.AskQuestionPreToolGateTests.test_hooks_manifest_and_canonical_hooks_include_ask_question()`
# @used-by :meth:`test_gate_registry.GateRegistryTests.test_builtin_pre_tool_gates_discovered_in_strict_priority_order()`
# @used-by :meth:`test_hook_lazy_imports.HookLazyImportsTests.test_discover_pre_tool_gates_tool_filtering_and_manifest_parity()`
# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_harness_main_blocks_write_and_edit_while_linked_worktree_allows()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax()`
# @used-by :mod:`agent_tools.gates`
def discover_pre_tool_gates(*, tool_name: str | None=None, extra_dirs: list[Path] | tuple[Path, ...] | None=None) -> list[dict]:
	return PreToolRegistry.discover(tool_name=tool_name, extra_dirs=extra_dirs, pkg_name=__name__, pkg_dir=Path(__file__).resolve().parent)
# @used-by :meth:`Df.Harness.Hook.RulesServerGate.RulesServerGate.run()`
# @used-by :meth:`test_ask_question_pre_tool_gate.AskQuestionPreToolGateTests.test_pre_tool_gate_blocks_q4_undisclosed_deferral_and_allows_q1_to_q3()`
# @used-by :meth:`test_ask_question_pre_tool_gate.AskQuestionPreToolGateTests.test_pre_tool_gate_blocks_stop_gate_bypass_and_docs_codify_rule()`
# @used-by :meth:`test_code_style_gate.CodeStyleGateTests.test_pre_tool_use_gate_and_pre_commit_enforce_code_style()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.test_send_message_gate_blocks_duplicate_json_verdicts_and_allows_prompts()`
# @used-by :meth:`test_gate_registry.GateRegistryTests.test_dynamic_plugin_discovery_runs_without_touching_dispatcher()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_in_process_cache_shares_single_disk_read_across_pre_tool_gates()`
# @used-by :meth:`test_issue_comment_gate.IssueCommentGateTests.test_pre_tool_use_and_pre_commit_enforce_issue_comment_gate()`
# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_pre_tool_use_blocks_raw_git_worktree_remove()`
# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_pre_tool_use_blocks_silent_shell_deletion_of_managed_worktrees()`
# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_harness_main_blocks_write_and_edit_while_linked_worktree_allows()`
# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_non_harness_repo_allows_single_turn_and_blocks_concurrent_open_turns()`
# @used-by :meth:`test_xref_gate.XrefGateTests._assert_pre_tool_allows_valid_and_legacy_ratchet()`
# @used-by :meth:`test_xref_gate.XrefGateTests._assert_pre_tool_denies_bad_samples()`
# @used-by :mod:`agent_tools.gates`
def run_pre_tool_gates(name: str, args: dict, payload: dict, *, extra_dirs: list[Path] | tuple[Path, ...] | None=None) -> dict:
	return PreToolRegistry(pkg_name=__name__, pkg_dir=Path(__file__).resolve().parent).run(name, args, payload, extra_dirs=extra_dirs)
__all__ = ['_BUILTIN_TOOLS_MANIFEST', 'discover_pre_tool_gates', 'run_answer_gates', 'run_pre_tool_gates', 'run_stop_gates']
