# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Migrate general code formatting rules with Bash and ES6 guides":
# https://github.com/dmitry-ai/harness/issues/154
from __future__ import annotations
from pathlib import Path
import sys
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = HARNESS_ROOT / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools import links, native_profiles, upwork_project
import check_markdown_slop
CODE_FORMATTING_DIR = HARNESS_ROOT / 'references/code-formatting'
RULE_DOC = HARNESS_ROOT / 'rules/11-code-formatting.md'
class CodeFormattingRulesContractTests(unittest.TestCase):
	def _assert_clean_doc(self, doc: Path) -> str:
		self.assertTrue(doc.is_file(), f'Missing formatting document: {doc}')
		self.assertFalse(doc.name.startswith('P.'), f'Prohibited P. filename prefix: {doc}')
		link_errs = links.validate_file(doc, local_anchors=True, readable_links=True)
		self.assertEqual([], link_errs, f'Link errors in {doc.name}: {link_errs}')
		text = doc.read_text(encoding='utf-8')
		slop_errs = check_markdown_slop.markdown_slop_issues(text)
		self.assertEqual([], slop_errs, f'DOC-4 slop errors in {doc.name}: {slop_errs}')
		return text
	def test_bash_and_javascript_guides_cover_migrated_rules_without_p_prefix(self) -> None:
		self.assertTrue(CODE_FORMATTING_DIR.is_dir(), f'Missing hierarchy directory: {CODE_FORMATTING_DIR}')
		p_prefixed = [p for p in CODE_FORMATTING_DIR.rglob('*.md') if p.name.startswith('P.')]
		self.assertEqual([], p_prefixed, f'Found prohibited P.-prefixed files: {p_prefixed}')
		bash_doc = CODE_FORMATTING_DIR / 'programming/bash.md'
		bash_text = self._assert_clean_doc(bash_doc)
		for token in ('11-code-formatting.md#code-1', '--extract', 'alphabetical', 'o=(', '"${o[@]}"', 'o1', 'o2', 'not part of'):
			self.assertIn(token, bash_text, f'Missing Bash formatting requirement {token!r}')
		js_doc = CODE_FORMATTING_DIR / 'programming/javascript.md'
		js_text = self._assert_clean_doc(js_doc)
		for token in ('11-code-formatting.md#code-1', 'ES6', 'const', '=>', 'template literal', '===', 'else', 'not part of'):
			self.assertIn(token, js_text, f'Missing JavaScript formatting requirement {token!r}')
	def test_general_rule_passes_doctor_native_bootstrap_and_lint(self) -> None:
		rule_text = self._assert_clean_doc(RULE_DOC)
		self.assertLess(len(RULE_DOC.read_bytes()), 20000, 'rules/11-code-formatting.md must stay under per-file budget')
		for token in ('trigger: always_on', '## CODE-1', '## CODE-2', '## CODE-3', 'EXEC-5', 'DOC-4', 'FILE-1', 'tab', 'blank lines', 'single return point', '`r`', 'constant on the left', 'shorter', 'single quotes', 'alphabetical', 'programming/bash.md', 'programming/javascript.md'):
			self.assertIn(token, rule_text, f'Missing general rule token {token!r} in {RULE_DOC.name}')
		doc_report = upwork_project.doctor(primary=HARNESS_ROOT)
		self.assertIn('11-code-formatting.md', doc_report['per_file_bytes'])
		codex_bootstrap = HARNESS_ROOT / 'platforms/codex/AGENTS.md'
		expected = native_profiles.shared_native_outputs(HARNESS_ROOT)[codex_bootstrap]
		self.assertEqual(expected, codex_bootstrap.read_text(encoding='utf-8'))
		self.assertIn('rules/11-code-formatting.md', expected)
if '__main__' == __name__:
	unittest.main()
