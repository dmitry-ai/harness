# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
import importlib
from pathlib import Path
import sys
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
sys.path.insert(0, str(Path(__file__).resolve().parent))
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
from agent_tools.hook_runtime import run_json_hook
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
_LAZY_EXPORTS = {
	# 2026-11-02
	# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
	# https://github.com/dmitry-ai/harness/issues/37
	'EXTERNAL_WRITE_INTENT_RE': ('agent_tools.gates.external_write', 'EXTERNAL_WRITE_INTENT_RE'),
	# 2026-11-01
	# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
	# https://github.com/dmitry-ai/harness/issues/34
	'MAX_UNPERSISTED_SOURCE_READS': ('agent_tools.gates.bulk_source_read', 'MAX_UNPERSISTED_SOURCE_READS'),
	# 2026-11-16
	# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
	# https://github.com/dmitry-ai/harness/issues/80
	'_is_inside_harness_code': ('agent_tools.gates.cdp_bypass', '_is_inside_harness_code'),
	# 2026-11-19
	# "Integrate declarative Antigravity addons health and sanctioning into Harness":
	# https://github.com/dmitry-ai/harness/issues/92
	'_is_inside_sanctioned_code': ('agent_tools.gates.cdp_bypass', '_is_inside_sanctioned_code'),
	'_turn_has_background_mcp_new_page': ('agent_tools.gates.browser_mcp', '_turn_has_background_mcp_new_page'),
	'_upwork_project_root_for_command': ('agent_tools.gates.external_write', '_upwork_project_root_for_command'),
	'check_batch_analysis_generator': ('agent_tools.gates.batch_synthesis', 'check'),
	'check_browser_mcp_gate': ('agent_tools.gates.browser_mcp', 'check'),
	'check_bulk_source_read_streak': ('agent_tools.gates.bulk_source_read', 'check'),
	'check_cdp_bypass_gate': ('agent_tools.gates.cdp_bypass', 'check'),
	# 2026-11-23
	# "Enforce AST function and file SLOC ratchet gate in PreToolUse and Git pre-commit":
	# https://github.com/dmitry-ai/harness/issues/161
	'check_code_size_gate': ('agent_tools.gates.code_size', 'check'),
	# 2026-11-25
	# "Add CODE-1 Python style ratchet linter gate in PreToolUse and pre-commit":
	# https://github.com/dmitry-ai/harness/issues/243
	'check_code_style_gate': ('agent_tools.gates.code_style', 'check'),
	'check_external_write_gate': ('agent_tools.gates.external_write', 'check'),
	'check_git_write_gate': ('agent_tools.gates.git_write', 'check'),
	# 2026-11-26
	# "Add PreToolUse and pre-commit gate for issue-comment placement":
	# https://github.com/dmitry-ai/harness/issues/273
	'check_issue_comment_gate': ('agent_tools.gates.issue_comment', 'check'),
	# 2026-11-23
	# "Enforce live PreToolUse Issue-First gate before TDD in check_rules_and_server_gate.py":
	# https://github.com/dmitry-ai/harness/issues/145
	'check_issue_first_gate': ('agent_tools.gates.issue_first', 'check'),
	# 2026-11-02
	# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
	# https://github.com/dmitry-ai/harness/issues/36
	'check_journal_write_gate': ('agent_tools.gates.journal_write', 'check'),
	# 2026-10-26
	# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
	# https://github.com/dmitry-ai/harness/issues/17
	'check_rules_budget': ('agent_tools.gates.rules_budget', 'check'),
	# 2026-11-23
	# "Enforce PreToolUse fail-fast normalization and block redundant schedule timers over run_command":
	# https://github.com/dmitry-ai/harness/issues/162
	'check_schedule_gate': ('agent_tools.gates.schedule_gate', 'check'),
	# 2026-11-24
	# "Enforce single falsifier review default and block duplicate send_message reports":
	# https://github.com/dmitry-ai/harness/issues/226
	'check_send_message_gate': ('agent_tools.gates.send_message_gate', 'check'),
	'check_server_hygiene': ('agent_tools.gates.server_hygiene', 'check'),
	'check_subprocess_hygiene_gate': ('agent_tools.gates.subprocess_hygiene', 'check'),
	# 2026-11-23
	# "Enforce live TDD PreToolUse gate in check_rules_and_server_gate.py":
	# https://github.com/dmitry-ai/harness/issues/136
	'check_tdd_gate': ('agent_tools.gates.tdd', 'check'),
	'check_worktree_isolation_gate': ('agent_tools.gates.worktree_isolation', 'check'),
	'evaluate_pre_tool_use_test_failfast': ('agent_tools.failfast_gate', 'evaluate_pre_tool_use_test_failfast'),
	'run_pre_tool_gates': ('agent_tools.gates', 'run_pre_tool_gates'),
}
# @used-by :mod:`check_rules_and_server_gate`
def __getattr__(name: str):
	target = _LAZY_EXPORTS.get(name)
	if None is target:
		raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
	return getattr(importlib.import_module(target[0]), target[1])
# 2026-11-23
# "Enforce PreToolUse fail-fast normalization and block redundant schedule timers over run_command":
# https://github.com/dmitry-ai/harness/issues/162
# @used-by :func:`_evaluate_payload()`
def _apply_failfast(name: str, args: dict, decision: dict) -> dict:
	r = decision
	if 'run_command' == name and 'allow' == decision.get('decision'):
		from agent_tools.failfast_gate import evaluate_pre_tool_use_test_failfast
		ff_err, ff_overwrite = evaluate_pre_tool_use_test_failfast(name, args)
		if ff_err:
			r = {'decision': 'deny', 'reason': f'REJECTED (EXEC-2-TEST-FAILFAST-GATE): {ff_err}'}
		elif ff_overwrite:
			r = {'decision': 'allow', 'overwrite': ff_overwrite, 'reason': 'EXEC-2-TEST-FAILFAST-GATE: Normalized test command fail-fast and WaitMsBeforeAsync.'}
	return r
# 2026-11-24
# "Unify PreToolUse/Stop JSON hook harnesses, turns/*.json iterators, DOC-4 sentence scanning, and GitHub Evidence resolvers":
# https://github.com/dmitry-ai/harness/issues/79
# @used-by :func:`main()`
# @used-by :meth:`test_service_finalization_exempt_and_sync_all_open.ServiceFinalizationAndSyncAllOpenTests.test_service_finalization_passes_under_blocked_tdd_and_shell_bypass_is_denied()`
# @used-by :meth:`test_tdd_pre_tool_use_perf.TddPreToolUsePerfTests.test_code_and_test_writes_stay_o1_subprocesses_across_25_committed_files()`
# @used-by :meth:`test_tdd_pre_tool_use_perf.TddPreToolUsePerfTests.test_non_code_write_and_non_writing_command_spawn_zero_subprocesses()`
def _evaluate_payload(payload: dict) -> dict:
	from agent_tools.gates import run_pre_tool_gates
	tool_call = payload.get('toolCall', {})
	name, args = (tool_call.get('name', ''), tool_call.get('args', {}))
	return _apply_failfast(name, args, run_pre_tool_gates(name, args, payload))
# @used-by :func:`test_issue_first_pre_tool_use._run_hook()`
# @used-by :func:`test_tdd_pre_tool_use._run_hook()`
# @used-by :mod:`check_rules_and_server_gate`
def main():
	run_json_hook(_evaluate_payload)
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
if '__main__' == __name__:
	main()
