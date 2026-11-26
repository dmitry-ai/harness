# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Codify daily Git tagging and tagged GitHub links in rules and documentation":
# https://github.com/dmitry-ai/harness/issues/265
from __future__ import annotations
from pathlib import Path
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import links, rules_audit
import check_markdown_slop
class RepoTagsDocsTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_rules_and_docs_codify_daily_tagging_and_link6_within_budgets(self) -> None:
		audit = rules_audit.audit_rules(WT_ROOT)
		self.assertTrue(audit['valid'], audit['issues'])
		link_rule = (WT_ROOT / 'rules/02-link-standards.md').read_text(encoding='utf-8')
		for tok in ('## LINK-6', 'file:///', 'YYYY-MM-DD', 'YYYY-MM-DD--', 'repo-tag'):
			self.assertIn(tok, link_rule, f'Missing {tok!r} in rules/02-link-standards.md')
		exec_rule = (WT_ROOT / 'rules/08-execution-and-tools.md').read_text(encoding='utf-8')
		for tok in ('repo-tag', 'YYYY-MM-DD'):
			self.assertIn(tok, exec_rule, f'Missing {tok!r} in rules/08-execution-and-tools.md')
		turn_doc = (WT_ROOT / 'references/turn-completion.md').read_text(encoding='utf-8')
		for tok in ('LINK-6', 'repo-tag', 'tagged GitHub'):
			self.assertIn(tok, turn_doc, f'Missing {tok!r} in references/turn-completion.md')
		gh_skill = (WT_ROOT / 'skills/df-github-issue/SKILL.md').read_text(encoding='utf-8')
		for tok in ('repo-tag', 'YYYY-MM-DD'):
			self.assertIn(tok, gh_skill, f'Missing {tok!r} in skills/df-github-issue/SKILL.md')
		readme_doc = (WT_ROOT / 'scripts/README-agent-tools.md').read_text(encoding='utf-8')
		for tok in ('repo-tag', 'repo-tag-retro', '--tag'):
			self.assertIn(tok, readme_doc, f'Missing {tok!r} in scripts/README-agent-tools.md')
		for rel in ('rules/02-link-standards.md', 'rules/08-execution-and-tools.md', 'references/turn-completion.md', 'skills/df-github-issue/SKILL.md', 'scripts/README-agent-tools.md'):
			doc_p = WT_ROOT / rel
			self.assertEqual([], links.validate_file(doc_p, local_anchors=True, readable_links=True), rel)
			self.assertEqual([], check_markdown_slop.markdown_slop_issues(doc_p.read_text(encoding='utf-8')), rel)
if '__main__' == __name__:
	unittest.main()
