# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace monolithic CLI router with declarative registry and modular docs":
# https://github.com/dmitry-ai/harness/issues/168
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = HARNESS_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import links
import check_markdown_slop
class CliRegistryTests(unittest.TestCase):
	def test_cli_docs_renders_registered_commands_and_runs_via_cli(self):
		from agent_tools.cli_registry import render_cli_index
		from agent_tools.upwork_project import main as cli_main
		md = render_cli_index()
		for cmd in ('cli-docs', 'land-acquire', 'run-tests', 'worktree-begin', 'worktree-land'):
			self.assertIn(f'`{cmd}`', md)
		self.assertEqual(cli_main(['cli-docs']), 0)
	def test_dynamic_command_registration_roundtrip(self):
		from agent_tools.cli_registry import _REGISTRY, execute_registered, register_command
		seen: list[str] = []
		register_command('demo-plugin-cmd', 'Demo plugin command', (('--tag', {'default': 'ok'}),), lambda ns: {'valid': True, 'tag': seen.append(ns.tag) or ns.tag})
		try:
			hit, res, rc = execute_registered(argparse.Namespace(command='demo-plugin-cmd', tag='alpha'))
			self.assertTrue(hit)
			self.assertEqual(res['tag'], 'alpha')
			self.assertIsNone(rc)
			self.assertEqual(seen, ['alpha'])
		finally:
			_REGISTRY.pop('demo-plugin-cmd', None)
	def test_modular_docs_and_per_feature_test_rule_valid(self):
		readme = HARNESS_ROOT / 'scripts/README-agent-tools.md'
		doc_wt = HARNESS_ROOT / 'scripts/docs/worktrees-and-testing.md'
		doc_reg = HARNESS_ROOT / 'scripts/docs/plugin-registries.md'
		rule_doc = HARNESS_ROOT / 'rules/11-code-formatting.md'
		for doc in (readme, doc_wt, doc_reg, rule_doc):
			self.assertTrue(doc.is_file(), f'Missing doc: {doc}')
			self.assertEqual(links.validate_file(doc, local_anchors=True, readable_links=True), [])
			self.assertEqual(check_markdown_slop.markdown_slop_issues(doc.read_text(encoding='utf-8')), [])
		r_text = readme.read_text(encoding='utf-8')
		self.assertIn('docs/worktrees-and-testing.md', r_text)
		self.assertIn('docs/plugin-registries.md', r_text)
		self.assertIn('run-tests', r_text)
		self.assertIn('test_<feature>.py', rule_doc.read_text(encoding='utf-8'))
	def test_operation_handlers_cover_all_non_completion_commands(self):
		from agent_tools.cli_domains import OPERATION_HANDLERS
		from agent_tools.completion import COMMANDS as COMP_CMDS
		from agent_tools.operations import COMMANDS as OP_CMDS, execute
		expected = {c for c in OP_CMDS if c not in COMP_CMDS}
		self.assertEqual(set(OPERATION_HANDLERS), expected)
		with self.assertRaises(ValueError):
			execute(argparse.Namespace(command='nonexistent-command-xyz'))
if '__main__' == __name__:
	unittest.main()
