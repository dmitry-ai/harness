# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Codify mandatory TDD workflow and ratchet contract in Harness documentation":
# https://github.com/dmitry-ai/harness/issues/139
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = HARNESS_ROOT / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))

from agent_tools import links, upwork_project
import check_markdown_slop


class TddRulesAndDocumentationContractTests(unittest.TestCase):
	def test_rules_and_docs_codify_tdd_contract_and_pass_lint_checks(self) -> None:
		rule_doc = HARNESS_ROOT / 'rules/08-execution-and-tools.md'
		turn_doc = HARNESS_ROOT / 'references/turn-completion.md'
		readme_doc = HARNESS_ROOT / 'scripts/README-agent-tools.md'

		for doc in (rule_doc, turn_doc, readme_doc):
			link_errs = links.validate_file(doc, local_anchors=True, readable_links=True)
			self.assertEqual(link_errs, [], f'Link errors in {doc.name}: {link_errs}')
			text = doc.read_text(encoding='utf-8')
			slop_errs = check_markdown_slop.markdown_slop_issues(text)
			self.assertEqual(slop_errs, [], f'DOC-4 slop errors in {doc.name}: {slop_errs}')

		# Canonical rule budget and mandatory TDD contract terms
		rule_bytes = rule_doc.read_bytes()
		self.assertLess(len(rule_bytes), 20000, 'rules/08-execution-and-tools.md must remain comfortably under system prompt budget')
		rule_text = rule_bytes.decode('utf-8')
		for token in ('RATCHET-OK', 'ratchet-ok', 'tdd-check', 'Red', 'full test suite'):
			self.assertIn(token, rule_text, f'Missing mandatory TDD term {token!r} in rules/08-execution-and-tools.md')

		# Turn completion contract documents tdd_check and CLI commands
		turn_text = turn_doc.read_text(encoding='utf-8')
		for token in ('tdd_check', 'ratchet-ok', 'tdd-check', 'RATCHET-OK'):
			self.assertIn(token, turn_text, f'Missing TDD contract term {token!r} in references/turn-completion.md')

		# README-agent-tools documents CLI commands and PreToolUse / pre-commit gates
		readme_text = readme_doc.read_text(encoding='utf-8')
		for token in ('ratchet-ok', 'tdd-check', 'RATCHET-OK', 'PreToolUse', 'pre-commit'):
			self.assertIn(token, readme_text, f'Missing TDD documentation term {token!r} in scripts/README-agent-tools.md')

	def test_cli_help_and_doctor_expose_tdd_commands(self) -> None:
		p_root = subprocess.run(
			[sys.executable, str(SCRIPT_DIR / 'harness.py'), '--help'],
			capture_output=True, text=True, encoding='utf-8', check=True,
		)
		self.assertIn('ratchet-ok', p_root.stdout)
		self.assertIn('tdd-check', p_root.stdout)

		p_ratchet = subprocess.run(
			[sys.executable, str(SCRIPT_DIR / 'harness.py'), 'ratchet-ok', '--help'],
			capture_output=True, text=True, encoding='utf-8', check=True,
		)
		self.assertIn('--file', p_ratchet.stdout)
		self.assertIn('--reason', p_ratchet.stdout)

		p_tdd = subprocess.run(
			[sys.executable, str(SCRIPT_DIR / 'harness.py'), 'tdd-check', '--help'],
			capture_output=True, text=True, encoding='utf-8', check=True,
		)
		self.assertIn('--conversation', p_tdd.stdout)

		doc_report = upwork_project.doctor()
		self.assertIn('tool_version', doc_report)
		self.assertIn('per_file_bytes', doc_report)
		self.assertIn('08-execution-and-tools.md', doc_report['per_file_bytes'])


if '__main__' == __name__:
	unittest.main()
