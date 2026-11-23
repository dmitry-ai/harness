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
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.failfast_gate import evaluate_pre_tool_use_test_failfast
from agent_tools.gates import run_pre_tool_gates
from agent_tools.gates.batch_synthesis import check as check_batch_analysis_generator
from agent_tools.gates.browser_mcp import _turn_has_background_mcp_new_page, check as check_browser_mcp_gate
from agent_tools.gates.bulk_source_read import MAX_UNPERSISTED_SOURCE_READS, check as check_bulk_source_read_streak
from agent_tools.gates.cdp_bypass import _is_inside_harness_code, _is_inside_sanctioned_code, check as check_cdp_bypass_gate
from agent_tools.gates.code_size import check as check_code_size_gate
from agent_tools.gates.external_write import EXTERNAL_WRITE_INTENT_RE, _upwork_project_root_for_command, check as check_external_write_gate
from agent_tools.gates.git_write import check as check_git_write_gate
from agent_tools.gates.issue_first import check as check_issue_first_gate
from agent_tools.gates.journal_write import check as check_journal_write_gate
from agent_tools.gates.rules_budget import check as check_rules_budget
from agent_tools.gates.schedule_gate import check as check_schedule_gate
from agent_tools.gates.server_hygiene import check as check_server_hygiene
from agent_tools.gates.tdd import check as check_tdd_gate
from agent_tools.hook_runtime import run_json_hook
def _apply_failfast(name: str, args: dict, decision: dict) -> dict:
	r = decision
	if 'allow' == decision.get('decision'):
		ff_err, ff_overwrite = evaluate_pre_tool_use_test_failfast(name, args)
		if ff_err:
			r = {'decision': 'deny', 'reason': f'REJECTED (EXEC-2-TEST-FAILFAST-GATE): {ff_err}'}
		elif ff_overwrite:
			r = {'decision': 'allow', 'overwrite': ff_overwrite, 'reason': 'EXEC-2-TEST-FAILFAST-GATE: Normalized test command fail-fast and WaitMsBeforeAsync.'}
	return r
def _evaluate_payload(payload: dict) -> dict:
	tool_call = payload.get('toolCall', {})
	name, args = (tool_call.get('name', ''), tool_call.get('args', {}))
	return _apply_failfast(name, args, run_pre_tool_gates(name, args, payload))
def main():
	run_json_hook(_evaluate_payload)
if '__main__' == __name__:
	main()
