# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import links, native_profiles, upwork_project
import check_markdown_slop
_FENCE_RE = re.compile(r'```[\s\S]*?```')
_HTML_COMMENT_RE = re.compile(r'<!--[\s\S]*?-->')
# 2026-11-25
# "Refactor shared rules into compact three-layer M-2 architecture":
# https://github.com/dmitry-ai/harness/issues/242
class RulesArchitectureM2Tests(unittest.TestCase):
	def test_always_on_budget_and_three_layer_partition(self) -> None:
		doc = upwork_project.doctor(primary=WT_ROOT)
		self.assertEqual(['00-scope.md', '01-file-boundaries.md', '02-link-standards.md', '03-language-lexicon.md', '04-statement-structure.md', '05-verification-audit.md', '08-execution-and-tools.md'], doc['always_on_rules'])
		self.assertEqual(['06-knowledge-base.md', '07-review-and-delegation.md', '11-code-formatting.md'], doc['model_decision_rules'])
		self.assertFalse((WT_ROOT / 'rules/09-initial-analysis.md').exists())
		self.assertFalse((WT_ROOT / 'rules/10-client-text.md').exists())
		self.assertLessEqual(doc['always_on_rule_bytes'], 20000)
		for name in doc['always_on_rules']:
			self.assertLessEqual(doc['per_file_bytes'][name], 4500, f'always_on rule {name} exceeds 4,500 bytes')
		for name in doc['model_decision_rules']:
			self.assertLessEqual(doc['per_file_bytes'][name], 6000, f'model_decision rule {name} exceeds 6,000 bytes')
	def test_codex_adapter_and_bootstrap_match_three_layer_rules(self) -> None:
		codex_doc = (WT_ROOT / 'platforms/codex.md').read_text(encoding='utf-8')
		self.assertIn('answer-<turn_key>.md', codex_doc)
		self.assertNotIn('scratch/answer.md', codex_doc)
		bootstrap = WT_ROOT / 'platforms/codex/AGENTS.md'
		expected = native_profiles.shared_native_outputs(WT_ROOT)[bootstrap]
		self.assertEqual(expected, bootstrap.read_text(encoding='utf-8'))
		self.assertIn('On-demand shared rules (trigger: model_decision', expected)
		self.assertNotIn('09-initial-analysis.md', expected)
		self.assertNotIn('10-client-text.md', expected)
	def test_rules_have_zero_html_comments_valid_links_and_legacy_reference(self) -> None:
		legacy_ref = WT_ROOT / 'references/legacy-v1-compatibility.md'
		self.assertTrue(legacy_ref.is_file(), 'Missing references/legacy-v1-compatibility.md')
		self.assertEqual([], links.validate_file(legacy_ref, local_anchors=True, readable_links=True))
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(legacy_ref.read_text(encoding='utf-8')))
		self.assertIn('legacy-v1-compatibility.md', (WT_ROOT / 'rules/00-scope.md').read_text(encoding='utf-8'))
		for path in sorted((WT_ROOT / 'rules').glob('*.md')):
			text = path.read_text(encoding='utf-8')
			self.assertEqual([], links.validate_file(path, local_anchors=True, readable_links=True), f'Link errors in {path.name}')
			self.assertEqual([], check_markdown_slop.markdown_slop_issues(text), f'DOC-4 errors in {path.name}')
			stripped = _FENCE_RE.sub('', text)
			self.assertIsNone(_HTML_COMMENT_RE.search(stripped), f'HTML comment found in {path.name}')
	def test_skills_retain_migrated_init_pub_and_shadow_replay_clauses(self) -> None:
		upwork_skill = (WT_ROOT / 'skills/upwork-init/SKILL.md').read_text(encoding='utf-8')
		for token in ('shadow-replay', 'sitemap.xml', 'draft.prev.md', 'RF-CLIENT-INTERMEDIARY', 'RF-WEBSITE-UNIDENTIFIED'):
			self.assertIn(token, upwork_skill, f'Missing {token!r} in skills/upwork-init/SKILL.md')
		article_skill = (WT_ROOT / 'skills/df-article/SKILL.md').read_text(encoding='utf-8')
		proposal_skill = (WT_ROOT / 'skills/df-proposal/SKILL.md').read_text(encoding='utf-8')
		for skill_text in (article_skill, proposal_skill):
			self.assertIn('response --against', skill_text)
			self.assertIn('begin', skill_text)
if '__main__' == __name__:
	unittest.main()