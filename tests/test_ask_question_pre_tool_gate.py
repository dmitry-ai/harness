# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce PreToolUse governance gate for ask_question calls":
# https://github.com/dmitry-ai/harness/issues/374
from __future__ import annotations
from pathlib import Path
import json
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import links, rules_audit, upwork_project
from agent_tools.gates import _BUILTIN_TOOLS_MANIFEST, discover_pre_tool_gates, run_pre_tool_gates
import check_markdown_slop
import check_rules_and_server_gate
Q1_ARCH = {
	'question': '\u041a\u0430\u043a \u043e\u0440\u0433\u0430\u043d\u0438\u0437\u043e\u0432\u0430\u0442\u044c Python namespaces \u0438 \u0438\u043c\u0435\u043d\u0430 \u0444\u0430\u0439\u043b\u043e\u0432 \u043a\u043b\u0430\u0441\u0441\u043e\u0432 (\u00a75 \u0438 \u00a711.6)?',
	'options': ['(Recommended) PascalCase \u0444\u0430\u0439\u043b\u044b = \u0438\u043c\u0435\u043d\u0430 \u043a\u043b\u0430\u0441\u0441\u043e\u0432', 'snake_case \u0444\u0430\u0439\u043b\u044b + PEP 562 __getattr__'],
}
Q2_ARCH = {
	'question': '\u041a\u0430\u043a\u043e\u0439 \u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c \u043f\u0440\u0438\u0432\u0430\u0442\u043d\u043e\u0441\u0442\u0438 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c \u0434\u043b\u044f \u043f\u0440\u0438\u0432\u0430\u0442\u043d\u044b\u0445 \u043c\u0435\u0442\u043e\u0434\u043e\u0432 (\u00a711.4)?',
	'options': ['(Recommended) \u0414\u0432\u043e\u0439\u043d\u043e\u0435 \u043f\u043e\u0434\u0447\u0435\u0440\u043a\u0438\u0432\u0430\u043d\u0438\u0435 __method', '\u041e\u0434\u0438\u043d\u0430\u0440\u043d\u043e\u0435 \u043f\u043e\u0434\u0447\u0435\u0440\u043a\u0438\u0432\u0430\u043d\u0438\u0435 _method'],
}
Q3_ARCH = {
	'question': '\u0413\u0434\u0435 \u0440\u0430\u0437\u043c\u0435\u0441\u0442\u0438\u0442\u044c \u043f\u0430\u043f\u043a\u0443 Df \u0432 \u0440\u0435\u043f\u043e\u0437\u0438\u0442\u043e\u0440\u0438\u0438 Harness?',
	'options': ['(Recommended) \u041f\u043e\u043c\u0435\u0441\u0442\u0438\u0442\u044c \u0432 scripts/Df/', '\u041f\u043e\u043c\u0435\u0441\u0442\u0438\u0442\u044c \u0432 \u043a\u043e\u0440\u0435\u043d\u044c Df/'],
}
Q4_STEP100 = {
	'question': '\u041e\u0431\u044a\u0435\u043c \u00a7\u00a72\u201311 \u043e\u0445\u0432\u0430\u0442\u044b\u0432\u0430\u0435\u0442 ~300+ \u0444\u0443\u043d\u043a\u0446\u0438\u0439. \u041a\u0430\u043a\u043e\u0439 \u043f\u043e\u0440\u044f\u0434\u043e\u043a \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u0438\u044f \u043f\u0440\u0435\u0434\u043f\u043e\u0447\u0442\u0438\u0442\u0435\u043b\u0435\u043d?',
	'options': [
		'(Recommended) \u0412\u044b\u043f\u043e\u043b\u043d\u044f\u0442\u044c \u043f\u043e\u044d\u0442\u0430\u043f\u043d\u043e \u0447\u0435\u0440\u0435\u0437 parent + child issues \u0432 \u0438\u0437\u043e\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u043e\u043c worktree: \u043d\u0430\u0447\u0430\u0442\u044c \u0441\u0440\u0430\u0437\u0443 \u0441 \u043f\u043e\u043b\u043d\u043e\u0433\u043e \u043f\u043e\u0440\u0442\u0430 \u00a7\u00a72\u20137 (+ \u00a79 \u043f\u0440\u0438 \u043d\u0430\u0445\u043e\u0434\u043a\u0430\u0445), \u0444\u0438\u043a\u0441\u0438\u0440\u0443\u044f \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u0432 continuation.md \u0434\u043b\u044f \u043f\u0435\u0440\u0435\u0445\u043e\u0434\u0430 \u043a \u00a7\u00a78\u201311 \u0431\u0435\u0437 \u043f\u043e\u0442\u0435\u0440\u0438 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u0430',
		'\u0412\u044b\u043f\u043e\u043b\u043d\u044f\u0442\u044c \u043d\u0435\u043f\u0440\u0435\u0440\u044b\u0432\u043d\u043e \u043e\u0442 \u00a72 \u0434\u043e \u00a711 \u0432 \u0440\u0430\u043c\u043a\u0430\u0445 \u0442\u0435\u043a\u0443\u0449\u0435\u0433\u043e \u043f\u0440\u043e\u0445\u043e\u0434\u0430',
	],
}
# 2026-11-26
# "Enforce PreToolUse governance gate for ask_question calls":
# https://github.com/dmitry-ai/harness/issues/374
class AskQuestionPreToolGateTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_hooks_manifest_and_canonical_hooks_include_ask_question(self) -> None:
		hooks = json.loads((WT_ROOT / 'platforms/antigravity/hooks.json').read_text(encoding='utf-8'))
		matcher = hooks['rules-and-server-gate']['PreToolUse'][0]['matcher']
		self.assertIn('|ask_question', matcher)
		canon = upwork_project.canonical_global_hooks(WT_ROOT)
		self.assertEqual(canon['rules-and-server-gate']['PreToolUse'][0]['matcher'], matcher)
		names = [g['name'] for g in discover_pre_tool_gates(tool_name='ask_question')]
		self.assertEqual(['SCOPE-2-ASK-QUESTION-GATE'], names)
		self.assertEqual(frozenset({'ask_question'}), _BUILTIN_TOOLS_MANIFEST.get('ask_question_gate'))
		self.assertTrue(callable(check_rules_and_server_gate.check_ask_question_gate))
	# @used-by :mod:`unittest`
	def test_pre_tool_gate_blocks_q4_undisclosed_deferral_and_allows_q1_to_q3(self) -> None:
		ok_arch = run_pre_tool_gates('ask_question', {'questions': [Q1_ARCH, Q2_ARCH, Q3_ARCH]}, {})
		self.assertEqual('allow', ok_arch['decision'], ok_arch)
		bad_q4 = run_pre_tool_gates('ask_question', {'questions': [Q1_ARCH, Q2_ARCH, Q3_ARCH, Q4_STEP100]}, {})
		self.assertEqual('deny', bad_q4['decision'], bad_q4)
		self.assertIn('SCOPE-2-ASK-QUESTION-GATE', bad_q4.get('reason', ''))
		bad_en = run_pre_tool_gates('ask_question', {'questions': [{'question': 'How should we execute?', 'options': ['(Recommended) Run Phase 1 now and defer Phase 2 into continuation.md for the next turn', 'Run all phases now']}]}, {})
		self.assertEqual('deny', bad_en['decision'], bad_en)
		ok_explicit = run_pre_tool_gates('ask_question', {'questions': [{'question': 'Execution scope choice:', 'options': ['(Recommended) Complete all requested sections in this turn', 'Stop the turn after Phase 1 and return control before Phase 2']}]}, {})
		self.assertEqual('allow', ok_explicit['decision'], ok_explicit)
		ok_warned = run_pre_tool_gates('ask_question', {'questions': [{'question': 'Execution scope choice:', 'options': ['(Recommended) Stop the turn after Phase 1 and return control without completing Phase 2 (saved in continuation.md)', 'Complete all sections now']}]}, {})
		self.assertEqual('allow', ok_warned['decision'], ok_warned)
	# @used-by :mod:`unittest`
	def test_pre_tool_gate_blocks_stop_gate_bypass_and_docs_codify_rule(self) -> None:
		step669 = {'questions': [{'question': 'Confirm when Harness fixes are applied:', 'options': ['Continue finalization', 'Cancel']}]}
		bad_669 = run_pre_tool_gates('ask_question', step669, {})
		self.assertEqual('deny', bad_669['decision'], bad_669)
		self.assertIn('--blocked-report', bad_669.get('reason', ''))
		bad_ru = run_pre_tool_gates('ask_question', {'questions': [{'question': '\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u0435, \u043a\u043e\u0433\u0434\u0430 \u0438\u0441\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f Harness \u0431\u0443\u0434\u0443\u0442 \u043f\u0440\u0438\u043c\u0435\u043d\u0435\u043d\u044b:', 'options': ['\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c', '\u041e\u0442\u043c\u0435\u043d\u0430']}]}, {})
		self.assertEqual('deny', bad_ru['decision'], bad_ru)
		scope_doc = WT_ROOT / 'rules/00-scope.md'
		scope_text = scope_doc.read_text(encoding='utf-8')
		self.assertIn('ask_question', scope_text)
		self.assertEqual([], links.validate_file(scope_doc, local_anchors=True, readable_links=True))
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(scope_text))
		self.assertTrue(rules_audit.audit_rules(WT_ROOT)['valid'])
if '__main__' == __name__:
	unittest.main()
