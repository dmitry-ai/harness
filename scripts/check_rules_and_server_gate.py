# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import importlib
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
sys.path.insert(0, str(Path(__file__).resolve().parent))
from Df.Harness.Hook.JsonRunner import JsonRunner
from Df.Harness.Hook.RulesServerGate import RulesServerGate
_LAZY_EXPORTS = {
	'EXTERNAL_WRITE_INTENT_RE': ('agent_tools.gates.external_write', 'EXTERNAL_WRITE_INTENT_RE'),
	'MAX_UNPERSISTED_SOURCE_READS': ('agent_tools.gates.bulk_source_read', 'MAX_UNPERSISTED_SOURCE_READS'),
	'_is_inside_harness_code': ('agent_tools.gates.cdp_bypass', '_is_inside_harness_code'),
	'_is_inside_sanctioned_code': ('agent_tools.gates.cdp_bypass', '_is_inside_sanctioned_code'),
	'_turn_has_background_mcp_new_page': ('agent_tools.gates.browser_mcp', '_turn_has_background_mcp_new_page'),
	'_upwork_project_root_for_command': ('agent_tools.gates.external_write', '_upwork_project_root_for_command'),
	'check_arch_audit_gate': ('agent_tools.gates.arch_audit', 'check'),
	'check_ask_question_gate': ('agent_tools.gates.ask_question_gate', 'check'),
	'check_batch_analysis_generator': ('agent_tools.gates.batch_synthesis', 'check'),
	'check_browser_mcp_gate': ('agent_tools.gates.browser_mcp', 'check'),
	'check_bulk_source_read_streak': ('agent_tools.gates.bulk_source_read', 'check'),
	'check_cdp_bypass_gate': ('agent_tools.gates.cdp_bypass', 'check'),
	'check_code_size_gate': ('agent_tools.gates.code_size', 'check'),
	'check_code_style_gate': ('agent_tools.gates.code_style', 'check'),
	'check_external_write_gate': ('agent_tools.gates.external_write', 'check'),
	'check_git_write_gate': ('agent_tools.gates.git_write', 'check'),
	'check_issue_comment_gate': ('agent_tools.gates.issue_comment', 'check'),
	'check_issue_first_gate': ('agent_tools.gates.issue_first', 'check'),
	'check_journal_write_gate': ('agent_tools.gates.journal_write', 'check'),
	'check_rules_budget': ('agent_tools.gates.rules_budget', 'check'),
	'check_schedule_gate': ('agent_tools.gates.schedule_gate', 'check'),
	'check_send_message_gate': ('agent_tools.gates.send_message_gate', 'check'),
	'check_server_hygiene': ('agent_tools.gates.server_hygiene', 'check'),
	'check_subprocess_hygiene_gate': ('agent_tools.gates.subprocess_hygiene', 'check'),
	'check_tdd_gate': ('agent_tools.gates.tdd', 'check'),
	'check_worktree_isolation_gate': ('agent_tools.gates.worktree_isolation', 'check'),
	'check_xref_gate': ('agent_tools.gates.xref', 'check'),
	'evaluate_pre_tool_use_test_failfast': ('agent_tools.failfast_gate', 'evaluate_pre_tool_use_test_failfast'),
	'run_pre_tool_gates': ('agent_tools.gates', 'run_pre_tool_gates'),
}
# @used-by :mod:`check_rules_and_server_gate`
def __getattr__(name: str):
	target = _LAZY_EXPORTS.get(name)
	if None is target:
		raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
	return getattr(importlib.import_module(target[0]), target[1])
# @used-by :func:`main()`
# @used-by :meth:`test_service_finalization_exempt_and_sync_all_open.ServiceFinalizationAndSyncAllOpenTests.test_service_finalization_passes_under_blocked_tdd_and_shell_bypass_is_denied()`
# @used-by :meth:`test_tdd_pre_tool_use_perf.TddPreToolUsePerfTests.test_code_and_test_writes_stay_o1_subprocesses_across_25_committed_files()`
# @used-by :meth:`test_tdd_pre_tool_use_perf.TddPreToolUsePerfTests.test_non_code_write_and_non_writing_command_spawn_zero_subprocesses()`
def _evaluate_payload(payload: dict) -> dict:
	return RulesServerGate(payload).run()
# @used-by :func:`test_issue_first_pre_tool_use._run_hook()`
# @used-by :func:`test_tdd_pre_tool_use._run_hook()`
# @used-by :mod:`check_rules_and_server_gate`
def main():
	JsonRunner(_evaluate_payload).run()
if '__main__' == __name__:
	main()