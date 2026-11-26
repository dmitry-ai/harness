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
SKILL_NAME = 'df--harness--improvement--performance'
# 2026-11-24
# "Add /df--harness--improvement--performance skill and update platform adapters":
# https://github.com/dmitry-ai/harness/issues/193
class PerfImprovementSkillContractTests(unittest.TestCase):
	def test_adapters_and_readme_document_skill_and_perf_cli_and_pass_lint(self) -> None:
		ag_doc = WT_ROOT / 'platforms/antigravity.md'
		cx_doc = WT_ROOT / 'platforms/codex.md'
		readme_doc = WT_ROOT / 'scripts/README-agent-tools.md'
		for doc in (ag_doc, cx_doc, readme_doc):
			self.assertEqual([], links.validate_file(doc, local_anchors=True, readable_links=True), f'Link issues in {doc.name}')
			self.assertEqual([], check_markdown_slop.markdown_slop_issues(doc.read_text(encoding='utf-8')), f'DOC-4 issues in {doc.name}')
		self.assertIn(f'/{SKILL_NAME}', ag_doc.read_text(encoding='utf-8'))
		cx_text = cx_doc.read_text(encoding='utf-8')
		self.assertIn(f'/{SKILL_NAME}', cx_text)
		self.assertIn(f'${SKILL_NAME}', cx_text)
		readme_text = readme_doc.read_text(encoding='utf-8')
		for token in (f'/{SKILL_NAME}', 'perf-timesheet', 'perf-profile-tests'):
			self.assertIn(token, readme_text, f'Missing {token!r} in README-agent-tools.md')
	def test_cli_help_exposes_perf_timesheet_and_perf_profile_tests(self) -> None:
		harness_cli = str(SCRIPT_DIR / 'harness.py')
		p_root = subprocess.run([sys.executable, harness_cli, '--help'], capture_output=True, text=True, encoding='utf-8', check=True)
		self.assertIn('perf-timesheet', p_root.stdout)
		self.assertIn('perf-profile-tests', p_root.stdout)
		p_ts = subprocess.run([sys.executable, harness_cli, 'perf-timesheet', '--help'], capture_output=True, text=True, encoding='utf-8', check=True)
		self.assertIn('--journal-step', p_ts.stdout)
		p_pr = subprocess.run([sys.executable, harness_cli, 'perf-profile-tests', '--help'], capture_output=True, text=True, encoding='utf-8', check=True)
		self.assertIn('--cprofile', p_pr.stdout)
	def test_perf_improvement_skill_discovered_and_references_pass_lint(self) -> None:
		skills = native_profiles._skills(WT_ROOT)
		self.assertIn(SKILL_NAME, skills)
		skill_path, meta = skills[SKILL_NAME]
		self.assertEqual(SKILL_NAME, meta['name'])
		self.assertIn(f'/{SKILL_NAME}', meta['description'])
		ref_dir = skill_path.parent / 'references'
		meth_path = ref_dir / 'methodology.md'
		tmpl_path = ref_dir / 'report-template.md'
		for doc in (skill_path, meth_path, tmpl_path):
			self.assertTrue(doc.is_file(), f'Missing {doc}')
			self.assertEqual([], links.validate_file(doc, local_anchors=True, readable_links=True), f'Link issues in {doc.name}')
			self.assertEqual([], check_markdown_slop.markdown_slop_issues(doc.read_text(encoding='utf-8')), f'DOC-4 issues in {doc.name}')
		skill_text = skill_path.read_text(encoding='utf-8')
		for token in ('perf-timesheet', 'perf-profile-tests', 'Track A', 'Track B', 'methodology.md', 'report-template.md', 'SCOPE-2', 'EXEC-5', 'EXEC-2', 'problem-metadata', 'analysis-check'):
			self.assertIn(token, skill_text, f'Missing {token!r} in SKILL.md')
		meth_text = meth_path.read_text(encoding='utf-8')
		for token in ('microbenchmark', 'cache_read_tokens', 'CHECKPOINT', 'Popen', 'cProfile', 'anchor_exception', 'CODE-4'):
			self.assertIn(token, meth_text, f'Missing {token!r} in methodology.md')
		tmpl_text = tmpl_path.read_text(encoding='utf-8')
		for token in ('# 0', '# 1', '# 2', '# 3', '# 4', 'Issue', 'Markdown tables'):
			self.assertIn(token, tmpl_text, f'Missing {token!r} in report-template.md')
if '__main__' == __name__:
	unittest.main()
