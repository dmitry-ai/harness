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

from agent_tools import links
import check_markdown_slop


# 2026-11-23
# "Codify mandatory pre-TDD Issue-First workflow in Harness rules and documentation":
# https://github.com/dmitry-ai/harness/issues/147
class IssueFirstRulesAndDocsContractTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_rules_skill_and_docs_codify_issue_first_before_tdd_and_pass_lint(self) -> None:
		rule_doc = HARNESS_ROOT / 'rules/08-execution-and-tools.md'
		skill_doc = HARNESS_ROOT / 'skills/df-github-issue/SKILL.md'
		turn_doc = HARNESS_ROOT / 'references/turn-completion.md'
		readme_doc = HARNESS_ROOT / 'scripts/README-agent-tools.md'

		for doc in (rule_doc, skill_doc, turn_doc, readme_doc):
			link_errs = links.validate_file(doc, local_anchors=True, readable_links=True)
			self.assertEqual(link_errs, [], f'Link errors in {doc.name}: {link_errs}')
			text = doc.read_text(encoding='utf-8')
			slop_errs = check_markdown_slop.markdown_slop_issues(text)
			self.assertEqual(slop_errs, [], f'DOC-4 slop errors in {doc.name}: {slop_errs}')

		rule_bytes = rule_doc.read_bytes()
		# 2026-11-25
		# "Refactor shared rules into compact three-layer M-2 architecture":
		# https://github.com/dmitry-ai/harness/issues/242
		self.assertLess(len(rule_bytes), 6000, 'rules/08-execution-and-tools.md must remain comfortably under system prompt budget')
		rule_text = rule_bytes.decode('utf-8')
		for token in ('Issue-First', 'issue-first-check', 'df-github-issue', 'fetch'):
			self.assertIn(token, rule_text, f'Missing Issue-First term {token!r} in rules/08-execution-and-tools.md')

		skill_text = skill_doc.read_text(encoding='utf-8')
		for token in ('Issue-First', 'fetch', 'pre_flight_issue_first', 'before writing any tests or code'):
			self.assertIn(token, skill_text, f'Missing Issue-First term {token!r} in skills/df-github-issue/SKILL.md')

		turn_text = turn_doc.read_text(encoding='utf-8')
		for token in ('issue_first_check', 'issue-first-check', 'EXEC-5-ISSUE-FIRST-GATE'):
			self.assertIn(token, turn_text, f'Missing Issue-First term {token!r} in references/turn-completion.md')

		readme_text = readme_doc.read_text(encoding='utf-8')
		for token in ('issue-first-check', 'fetch', 'EXEC-5-ISSUE-FIRST-GATE'):
			self.assertIn(token, readme_text, f'Missing Issue-First term {token!r} in scripts/README-agent-tools.md')

	# @used-by :mod:`unittest`
	def test_cli_help_exposes_issue_first_check_and_github_fetch(self) -> None:
		p_root = subprocess.run(
			[sys.executable, str(SCRIPT_DIR / 'harness.py'), '--help'],
			capture_output=True, text=True, encoding='utf-8', check=True,
		)
		self.assertIn('issue-first-check', p_root.stdout)

		p_ifc = subprocess.run(
			[sys.executable, str(SCRIPT_DIR / 'harness.py'), 'issue-first-check', '--help'],
			capture_output=True, text=True, encoding='utf-8', check=True,
		)
		self.assertIn('--conversation', p_ifc.stdout)

		p_gh = subprocess.run(
			[sys.executable, str(SCRIPT_DIR / 'df_github_issue.py'), 'fetch', '--help'],
			capture_output=True, text=True, encoding='utf-8', check=True,
		)
		self.assertIn('--repo', p_gh.stdout)
		self.assertIn('--issue', p_gh.stdout)


if '__main__' == __name__:
	unittest.main()
