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
# "Document JSON metadata header contract in rules and references":
# https://github.com/dmitry-ai/harness/issues/152
class MetadataRulesAndDocsContractTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_rules_skill_and_docs_codify_json_metadata_headers_and_pass_lint(self) -> None:
		file_rule = HARNESS_ROOT / 'rules/01-file-boundaries.md'
		exec_rule = HARNESS_ROOT / 'rules/08-execution-and-tools.md'
		turn_doc = HARNESS_ROOT / 'references/turn-completion.md'
		skill_doc = HARNESS_ROOT / 'skills/df-github-issue/SKILL.md'
		readme_doc = HARNESS_ROOT / 'scripts/README-agent-tools.md'

		for doc in (file_rule, exec_rule, turn_doc, skill_doc, readme_doc):
			link_errs = links.validate_file(doc, local_anchors=True, readable_links=True)
			self.assertEqual(link_errs, [], f'Link errors in {doc.name}: {link_errs}')
			text = doc.read_text(encoding='utf-8')
			slop_errs = check_markdown_slop.markdown_slop_issues(text)
			self.assertEqual(slop_errs, [], f'DOC-4 slop errors in {doc.name}: {slop_errs}')

		exec_bytes = exec_rule.read_bytes()
		# 2026-11-25
		# "Refactor shared rules into compact three-layer M-2 architecture":
		# https://github.com/dmitry-ai/harness/issues/242
		self.assertLess(len(exec_bytes), 6000, 'rules/08-execution-and-tools.md must remain under system prompt budget')

		file_text = file_rule.read_text(encoding='utf-8')
		for token in ('JSON metadata', 'body_sha256', 'chat'):
			self.assertIn(token, file_text, f'Missing metadata term {token!r} in rules/01-file-boundaries.md')

		exec_text = exec_bytes.decode('utf-8')
		# 2026-11-25
		# "Refactor shared rules into compact three-layer M-2 architecture":
		# https://github.com/dmitry-ai/harness/issues/242
		for token in ('df-github-issue', 'Issue-First'):
			self.assertIn(token, exec_text, f'Missing metadata pointer {token!r} in rules/08-execution-and-tools.md')

		turn_text = turn_doc.read_text(encoding='utf-8')
		for token in ('JSON metadata', 'body_sha256', 'Time', 'Agent', 'Trace'):
			self.assertIn(token, turn_text, f'Missing metadata term {token!r} in references/turn-completion.md')

		skill_text = skill_doc.read_text(encoding='utf-8')
		for token in ('JSON metadata', '--no-metadata', 'Time', 'Issue', 'Agent', 'Trace'):
			self.assertIn(token, skill_text, f'Missing metadata term {token!r} in skills/df-github-issue/SKILL.md')

		readme_text = readme_doc.read_text(encoding='utf-8')
		for token in ('JSON metadata', '--no-metadata', 'body_sha256'):
			self.assertIn(token, readme_text, f'Missing metadata term {token!r} in scripts/README-agent-tools.md')

	# @used-by :mod:`unittest`
	def test_cli_help_exposes_github_issue_no_metadata_flag(self) -> None:
		p_gh = subprocess.run(
			[sys.executable, str(SCRIPT_DIR / 'df_github_issue.py'), 'create', '--help'],
			capture_output=True, text=True, encoding='utf-8', check=True,
		)
		self.assertIn('--no-metadata', p_gh.stdout)
		self.assertIn('--project-root', p_gh.stdout)


if '__main__' == __name__:
	unittest.main()
