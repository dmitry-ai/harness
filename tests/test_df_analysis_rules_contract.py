# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = WT_ROOT / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools import links, native_profiles
import check_markdown_slop
# 2026-11-24
# "Create /df-analysis skill and codify mandatory analytical rules":
# https://github.com/dmitry-ai/harness/issues/182
class DfAnalysisRulesAndSkillContractTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_cli_help_exposes_problem_metadata_and_analysis_check(self) -> None:
		harness_cli = str(SCRIPT_DIR / 'harness.py')
		p_root = subprocess.run([sys.executable, harness_cli, '--help'], capture_output=True, text=True, encoding='utf-8', check=True)
		self.assertIn('problem-metadata', p_root.stdout)
		self.assertIn('analysis-check', p_root.stdout)
		p_meta = subprocess.run([sys.executable, harness_cli, 'problem-metadata', '--help'], capture_output=True, text=True, encoding='utf-8', check=True)
		self.assertIn('--issue', p_meta.stdout)
		self.assertIn('--no-issue', p_meta.stdout)
		self.assertIn('--source-project', p_meta.stdout)
		p_chk = subprocess.run([sys.executable, harness_cli, 'analysis-check', '--help'], capture_output=True, text=True, encoding='utf-8', check=True)
		self.assertIn('--response-file', p_chk.stdout)
		self.assertIn('--mode', p_chk.stdout)
	# @used-by :mod:`unittest`
	def test_df_analysis_skill_discovered_by_native_profiles_and_lints_cleanly(self) -> None:
		skills = native_profiles._skills(WT_ROOT)
		self.assertIn('df-analysis', skills)
		skill_path, meta = skills['df-analysis']
		self.assertEqual('df-analysis', meta['name'])
		self.assertIn('/df-analysis', meta['description'])
		self.assertEqual([], links.validate_file(skill_path, local_anchors=True, readable_links=True))
		skill_text = skill_path.read_text(encoding='utf-8')
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(skill_text))
		for token in ('no single unambiguous solution', 'problem-metadata', 'analysis-check', '# 0', '# 1', '# 2', '# 3', '# 4', 'Issue', 'verbatim', 'Harness'):
			self.assertIn(token, skill_text, f'Missing token {token!r} in skills/df-analysis/SKILL.md')
	# @used-by :mod:`unittest`
	def test_rules_adapters_and_docs_codify_df_analysis_and_pass_lint(self) -> None:
		stmt_rule = WT_ROOT / 'rules/04-statement-structure.md'
		link_rule = WT_ROOT / 'rules/02-link-standards.md'
		ag_doc = WT_ROOT / 'platforms/antigravity.md'
		cx_doc = WT_ROOT / 'platforms/codex.md'
		turn_doc = WT_ROOT / 'references/turn-completion.md'
		readme_doc = WT_ROOT / 'scripts/README-agent-tools.md'
		for doc in (stmt_rule, link_rule, ag_doc, cx_doc, turn_doc, readme_doc):
			link_errs = links.validate_file(doc, local_anchors=True, readable_links=True)
			self.assertEqual([], link_errs, f'Link errors in {doc.name}: {link_errs}')
			slop_errs = check_markdown_slop.markdown_slop_issues(doc.read_text(encoding='utf-8'))
			self.assertEqual([], slop_errs, f'DOC-4 slop errors in {doc.name}: {slop_errs}')
		stmt_bytes = stmt_rule.read_bytes()
		self.assertLess(len(stmt_bytes), 12000, 'rules/04-statement-structure.md must stay compact')
		stmt_text = stmt_bytes.decode('utf-8')
		for token in ('no single unambiguous solution', '## DOC-5', 'df-analysis', 'problem-metadata', 'Issue', 'Markdown tables'):
			self.assertIn(token, stmt_text, f'Missing term {token!r} in rules/04-statement-structure.md')
		link_text = link_rule.read_text(encoding='utf-8')
		self.assertIn('anchor_exception', link_text)
		self.assertIn('omitting an `#anchor`', link_text)
		self.assertIn('/df-analysis', ag_doc.read_text(encoding='utf-8'))
		self.assertIn('/df-analysis', cx_doc.read_text(encoding='utf-8'))
		self.assertIn('$df-analysis', cx_doc.read_text(encoding='utf-8'))
		turn_text = turn_doc.read_text(encoding='utf-8')
		for token in ('df-analysis', 'Markdown table', 'anchor'):
			self.assertIn(token, turn_text, f'Missing term {token!r} in references/turn-completion.md')
		readme_text = readme_doc.read_text(encoding='utf-8')
		for token in ('problem-metadata', 'analysis-check', 'df-analysis'):
			self.assertIn(token, readme_text, f'Missing term {token!r} in scripts/README-agent-tools.md')
if '__main__' == __name__:
	unittest.main()
