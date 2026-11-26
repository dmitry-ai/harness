# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
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


# 2026-11-23
# "Codify mandatory TDD workflow and ratchet contract in Harness documentation":
# https://github.com/dmitry-ai/harness/issues/139
class TddRulesAndDocumentationContractTests(unittest.TestCase):
	# @used-by :mod:`unittest`
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
		# 2026-11-25
		# "Refactor shared rules into compact three-layer M-2 architecture":
		# https://github.com/dmitry-ai/harness/issues/242
		self.assertLess(len(rule_bytes), 6000, 'rules/08-execution-and-tools.md must remain comfortably under system prompt budget')
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

	# @used-by :mod:`unittest`
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

	# 2026-11-23
	# "Codify fail-fast defaults and prohibit schedule timers over run_command in rules and docs":
	# https://github.com/dmitry-ai/harness/issues/164
	# @used-by :mod:`unittest`
	def test_failfast_defaults_and_schedule_prohibition_contract(self) -> None:
		rule_text = (HARNESS_ROOT / 'rules/08-execution-and-tools.md').read_text(encoding='utf-8')
		self.assertNotIn('or a `schedule` timer with `DurationSeconds`', rule_text)
		# 2026-11-25
		# "Refactor shared rules into compact three-layer M-2 architecture":
		# https://github.com/dmitry-ai/harness/issues/242
		for token in ('run-tests', 'WaitMsBeforeAsync', 'fail-fast', 'DurationSeconds'):
			self.assertIn(token, rule_text, f'Missing fail-fast / schedule rule term {token!r} in rules/08-execution-and-tools.md')
		readme_text = (HARNESS_ROOT / 'scripts/README-agent-tools.md').read_text(encoding='utf-8')
		for gate_tok in ('EXEC-4-SCHEDULE-GATE', 'EXEC-2-TEST-FAILFAST-GATE'):
			self.assertIn(gate_tok, readme_text)
		self.assertIn('# Regression Suite', readme_text)
		reg_section = readme_text.split('# Regression Suite', 1)[1].split('\n# ', 1)[0]
		self.assertIn('harness.py run-tests', reg_section)
		self.assertIn('-f', reg_section)
		self.assertIn('WaitMsBeforeAsync', reg_section)
		p_rt = subprocess.run([sys.executable, str(SCRIPT_DIR / 'harness.py'), 'run-tests', '--help'], capture_output=True, text=True, encoding='utf-8', check=True)
		for opt in ('--workers', '--module-timeout', '--no-failfast', '--module', '--format'):
			self.assertIn(opt, p_rt.stdout)


if '__main__' == __name__:
	unittest.main()
