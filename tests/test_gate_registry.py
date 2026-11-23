# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = HARNESS_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
class GateRegistryTests(unittest.TestCase):
	def test_answer_gates_collect_issues_and_checks_map(self):
		from agent_tools.gates import run_answer_gates
		ctx = {
			'role': 'primary',
			'doc4_errs': ['DOC-4 err'],
			'link_errs': [],
			'prob_errs': [],
			'source_errs': [],
			'lang_errs': [],
			'exec5_chk': {'verified': True, 'violations': []},
			'http_chk': {'verified': True, 'violations': []},
			'comp_chk': {'verified': True},
			'evicted_cited': [],
			'del_chk': {'verified': True},
			'issue_first_chk': {'verified': False, 'violations': ['No parent issue']},
			'lifecycle_chk': {'verified': True, 'violations': []},
			'tdd_chk': {'verified': True, 'violations': []},
			'wf_errs': [],
		}
		issues, checks = run_answer_gates(ctx)
		self.assertFalse(checks['doc4'])
		self.assertFalse(checks['issue_first'])
		self.assertTrue(checks['tdd'])
		gate_ids = [item['gate_id'] for item in issues]
		self.assertIn('doc4', gate_ids)
		self.assertIn('issue_first', gate_ids)
	def test_backward_compatible_exports_on_rules_gate_script(self):
		import check_rules_and_server_gate as mod
		for sym in ('check_rules_budget', 'check_server_hygiene', 'check_git_write_gate', 'check_external_write_gate', 'check_journal_write_gate', 'check_batch_analysis_generator', 'check_bulk_source_read_streak', 'check_cdp_bypass_gate', 'check_browser_mcp_gate', 'check_schedule_gate', 'check_issue_first_gate', 'check_tdd_gate', 'check_code_size_gate', 'MAX_UNPERSISTED_SOURCE_READS', 'EXTERNAL_WRITE_INTENT_RE'):
			self.assertTrue(hasattr(mod, sym), f'Missing export {sym}')
	def test_builtin_pre_tool_gates_discovered_in_strict_priority_order(self):
		from agent_tools.gates import discover_pre_tool_gates
		gates = discover_pre_tool_gates()
		names = [g['name'] for g in gates]
		priorities = [g['priority'] for g in gates]
		self.assertEqual(priorities, sorted(priorities))
		self.assertIn('EXEC-4-SCHEDULE-GATE', names)
		self.assertIn('EXEC-5-ISSUE-FIRST-GATE', names)
		self.assertIn('EXEC-2-TDD-GATE', names)
		self.assertIn('CODE-SIZE-RATCHET-GATE', names)
		self.assertLess(names.index('M-5-BROWSER-MCP-GATE'), names.index('EXEC-4-SCHEDULE-GATE'))
		self.assertLess(names.index('EXEC-4-SCHEDULE-GATE'), names.index('EXEC-5-ISSUE-FIRST-GATE'))
		self.assertLess(names.index('EXEC-5-ISSUE-FIRST-GATE'), names.index('EXEC-2-TDD-GATE'))
		self.assertLess(names.index('EXEC-2-TDD-GATE'), names.index('CODE-SIZE-RATCHET-GATE'))
	def test_dynamic_plugin_discovery_runs_without_touching_dispatcher(self):
		from agent_tools.gates import run_pre_tool_gates
		with tempfile.TemporaryDirectory() as td:
			plug_dir = Path(td)
			(plug_dir / 'custom_high.py').write_text("NAME = 'CUSTOM-HIGH-GATE'\nPRIORITY = 5\ndef check(name, args, payload):\n\treturn 'blocked by custom plugin' if 'ping' == name else None\n", encoding='utf-8')
			decision = run_pre_tool_gates('ping', {}, {}, extra_dirs=[plug_dir])
			self.assertEqual(decision['decision'], 'deny')
			self.assertIn('CUSTOM-HIGH-GATE', decision['reason'])
			self.assertIn('blocked by custom plugin', decision['reason'])
			ok = run_pre_tool_gates('other', {}, {}, extra_dirs=[plug_dir])
			self.assertEqual(ok['decision'], 'allow')
	def test_stop_gates_evaluate_in_priority_order(self):
		from agent_tools.gates import run_stop_gates
		bad_if = {'status': 'prepared', 'prepared': {'response_sha256': 'x'}, 'readiness_check': {'verified': True}, 'issue_first_check': {'verified': False, 'violations': ['missing parent']}, 'tdd_check': {'verified': False, 'violations': ['no red']}}
		res = run_stop_gates(bad_if)
		self.assertIsNotNone(res)
		self.assertEqual(res['decision'], 'continue')
		self.assertIn('ISSUE-FIRST', res['reason'])
		ok_state = {'status': 'prepared', 'prepared': {'response_sha256': 'x'}, 'readiness_check': {'verified': True}, 'issue_first_check': {'verified': True}, 'code_lifecycle_check': {'verified': True}, 'tdd_check': {'verified': True}}
		self.assertIsNone(run_stop_gates(ok_state))
if '__main__' == __name__:
	unittest.main()
