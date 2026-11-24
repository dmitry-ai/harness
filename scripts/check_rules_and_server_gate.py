# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce single falsifier review default and block duplicate send_message reports":
# https://github.com/dmitry-ai/harness/issues/226
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/79
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce AST function and file SLOC ratchet gate in PreToolUse and Git pre-commit":
# https://github.com/dmitry-ai/harness/issues/161
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce PreToolUse fail-fast normalization and block redundant schedule timers over run_command":
# https://github.com/dmitry-ai/harness/issues/162
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce live PreToolUse Issue-First gate before TDD in check_rules_and_server_gate.py":
# https://github.com/dmitry-ai/harness/issues/145
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce live TDD PreToolUse gate in check_rules_and_server_gate.py":
# https://github.com/dmitry-ai/harness/issues/136
# 2026-11-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce similar_projects parity gate, hooks, and documented CLI contract across turn completion and issue lifecycle":
# https://github.com/dmitry-ai/harness/issues/123
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
# https://github.com/dmitry-ai/harness/issues/109
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
# https://github.com/dmitry-ai/harness/issues/101
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Integrate declarative Antigravity addons health and sanctioning into Harness":
# https://github.com/dmitry-ai/harness/issues/92
# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix post-audit edge cases in parent-child issue validation and turn-scoped lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/87
# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/84
# 2026-11-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
import importlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.hook_runtime import run_json_hook
_LAZY_EXPORTS = {
	'EXTERNAL_WRITE_INTENT_RE': ('agent_tools.gates.external_write', 'EXTERNAL_WRITE_INTENT_RE'),
	'MAX_UNPERSISTED_SOURCE_READS': ('agent_tools.gates.bulk_source_read', 'MAX_UNPERSISTED_SOURCE_READS'),
	'_is_inside_harness_code': ('agent_tools.gates.cdp_bypass', '_is_inside_harness_code'),
	'_is_inside_sanctioned_code': ('agent_tools.gates.cdp_bypass', '_is_inside_sanctioned_code'),
	'_turn_has_background_mcp_new_page': ('agent_tools.gates.browser_mcp', '_turn_has_background_mcp_new_page'),
	'_upwork_project_root_for_command': ('agent_tools.gates.external_write', '_upwork_project_root_for_command'),
	'check_batch_analysis_generator': ('agent_tools.gates.batch_synthesis', 'check'),
	'check_browser_mcp_gate': ('agent_tools.gates.browser_mcp', 'check'),
	'check_bulk_source_read_streak': ('agent_tools.gates.bulk_source_read', 'check'),
	'check_cdp_bypass_gate': ('agent_tools.gates.cdp_bypass', 'check'),
	'check_code_size_gate': ('agent_tools.gates.code_size', 'check'),
	'check_external_write_gate': ('agent_tools.gates.external_write', 'check'),
	'check_git_write_gate': ('agent_tools.gates.git_write', 'check'),
	'check_issue_first_gate': ('agent_tools.gates.issue_first', 'check'),
	'check_journal_write_gate': ('agent_tools.gates.journal_write', 'check'),
	'check_rules_budget': ('agent_tools.gates.rules_budget', 'check'),
	'check_schedule_gate': ('agent_tools.gates.schedule_gate', 'check'),
	'check_send_message_gate': ('agent_tools.gates.send_message_gate', 'check'),
	'check_server_hygiene': ('agent_tools.gates.server_hygiene', 'check'),
	'check_subprocess_hygiene_gate': ('agent_tools.gates.subprocess_hygiene', 'check'),
	'check_tdd_gate': ('agent_tools.gates.tdd', 'check'),
	'check_worktree_isolation_gate': ('agent_tools.gates.worktree_isolation', 'check'),
	'evaluate_pre_tool_use_test_failfast': ('agent_tools.failfast_gate', 'evaluate_pre_tool_use_test_failfast'),
	'run_pre_tool_gates': ('agent_tools.gates', 'run_pre_tool_gates'),
}
def __getattr__(name: str):
	target = _LAZY_EXPORTS.get(name)
	if None is target:
		raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
	return getattr(importlib.import_module(target[0]), target[1])
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
def _evaluate_payload(payload: dict) -> dict:
	from agent_tools.gates import run_pre_tool_gates
	tool_call = payload.get('toolCall', {})
	name, args = (tool_call.get('name', ''), tool_call.get('args', {}))
	return _apply_failfast(name, args, run_pre_tool_gates(name, args, payload))
def main():
	run_json_hook(_evaluate_payload)
if '__main__' == __name__:
	main()
