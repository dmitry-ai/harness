# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
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
# 2026-11-23
# "Migrate general code formatting rules with Bash and ES6 guides":
# https://github.com/dmitry-ai/harness/issues/154
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
		# 2026-11-25
		# "Refactor shared rules into compact three-layer M-2 architecture":
		# https://github.com/dmitry-ai/harness/issues/242
		self.assertLess(len(RULE_DOC.read_bytes()), 6000, 'rules/11-code-formatting.md must stay under per-file budget')
		for token in ('trigger: model_decision', '## CODE-1', '## CODE-2', '## CODE-3', 'EXEC-5', 'DOC-4', 'FILE-1', 'tab', 'blank lines', 'single return point', '`r`', 'constant on the left', 'shorter', 'single quotes', 'alphabetical', 'programming/bash.md', 'programming/javascript.md'):
			self.assertIn(token, rule_text, f'Missing general rule token {token!r} in {RULE_DOC.name}')
		doc_report = upwork_project.doctor(primary=HARNESS_ROOT)
		self.assertIn('11-code-formatting.md', doc_report['per_file_bytes'])
		codex_bootstrap = HARNESS_ROOT / 'platforms/codex/AGENTS.md'
		expected = native_profiles.shared_native_outputs(HARNESS_ROOT)[codex_bootstrap]
		self.assertEqual(expected, codex_bootstrap.read_text(encoding='utf-8'))
		self.assertIn('rules/11-code-formatting.md', expected)
	# 2026-11-26
	# "Codify contextual issue-comment placement standard in Harness rules":
	# https://github.com/dmitry-ai/harness/issues/272
	def test_issue_comments_guide_and_rules_codify_contextual_placement(self) -> None:
		rule_text = self._assert_clean_doc(RULE_DOC)
		self.assertIn('issue-comments.md', rule_text)
		guide_text = self._assert_clean_doc(CODE_FORMATTING_DIR / 'issue-comments.md')
		for token in ('11-code-formatting.md#code-3', 'mage2pro/core', 'modified block', 'function', 'Dmitrii Fediuk https://github.com/dmitrii-fediuk', 'once per file', 'oldest-first', 'creation date'):
			self.assertIn(token, guide_text, f'Missing issue-comment rule token {token!r}')
		exec_rule = self._assert_clean_doc(HARNESS_ROOT / 'rules/08-execution-and-tools.md')
		self.assertIn('issue-comments.md', exec_rule)
		gh_skill = self._assert_clean_doc(HARNESS_ROOT / 'skills/df-github-issue/SKILL.md')
		self.assertIn('issue-comments.md', gh_skill)
	# 2026-11-23
	# "Add PHP and markup formatting standards derived from mage2pro/core":
	# https://github.com/dmitry-ai/harness/issues/155
	def test_mage2pro_derived_php_markup_and_other_guides(self) -> None:
		rule_text = self._assert_clean_doc(RULE_DOC)
		for rel in ('programming/php.md', 'markup/xml.md', 'markup/html.md', 'other/json.md', 'other/less.md'):
			self.assertIn(rel, rule_text, f'rules/11-code-formatting.md missing link to {rel}')
		php_text = self._assert_clean_doc(CODE_FORMATTING_DIR / 'programming/php.md')
		for token in ('11-code-formatting.md#code-1', '<?php', '?>', 'public', 'final class', ':string', 'function(', 'use(', 'leading comma', '$r', '_P', '`#`', 'not part of'):
			self.assertIn(token, php_text, f'Missing PHP formatting requirement {token!r}')
		xml_text = self._assert_clean_doc(CODE_FORMATTING_DIR / 'markup/xml.md')
		for token in ('11-code-formatting.md#code-1', "<?xml version='1.0'?>", 'single quotes', 'alphabetical', 'own line', '/>', 'column 0', 'not part of'):
			self.assertIn(token, xml_text, f'Missing XML formatting requirement {token!r}')
		html_text = self._assert_clean_doc(CODE_FORMATTING_DIR / 'markup/html.md')
		for token in ('11-code-formatting.md#code-1', 'single quotes', 'tab', 'not part of'):
			self.assertIn(token, html_text, f'Missing HTML formatting requirement {token!r}')
		json_text = self._assert_clean_doc(CODE_FORMATTING_DIR / 'other/json.md')
		for token in ('11-code-formatting.md#code-1', 'double quotes', 'tab', 'leading comma', 'not part of'):
			self.assertIn(token, json_text, f'Missing JSON formatting requirement {token!r}')
		less_text = self._assert_clean_doc(CODE_FORMATTING_DIR / 'other/less.md')
		for token in ('11-code-formatting.md#code-1', 'tab', 'single-line', 'leading comma', 'not part of'):
			self.assertIn(token, less_text, f'Missing LESS formatting requirement {token!r}')
	# 2026-11-23
	# "Add Python and INI formatting standards derived from reference pipelines":
	# https://github.com/dmitry-ai/harness/issues/156
	def test_python_and_ini_guides_cover_pipeline_standards(self) -> None:
		rule_text = self._assert_clean_doc(RULE_DOC)
		for rel in ('programming/python.md', 'other/ini.md'):
			self.assertIn(rel, rule_text, f'rules/11-code-formatting.md missing link to {rel}')
		py_text = self._assert_clean_doc(CODE_FORMATTING_DIR / 'programming/python.md')
		for token in ('11-code-formatting.md#code-1', 'from ... import ...', 'import ...', 'None is', "'__main__' == __name__", 'leading comma', 'alphabetical', "encoding='utf-8'", "indent='\\t'", 'lambda', 'ⵗ', 'ᛡ', 'not part of'):
			self.assertIn(token, py_text, f'Missing Python formatting requirement {token!r}')
		ini_text = self._assert_clean_doc(CODE_FORMATTING_DIR / 'other/ini.md')
		for token in ('11-code-formatting.md#code-1', 'key = value', 'alphabetical', '`#`', 'not part of'):
			self.assertIn(token, ini_text, f'Missing INI formatting requirement {token!r}')
		all_guides = sorted(CODE_FORMATTING_DIR.rglob('*.md'))
		self.assertGreaterEqual(len(all_guides), 10)
		for guide in all_guides:
			rel = guide.relative_to(CODE_FORMATTING_DIR).as_posix()
			self.assertIn(rel, rule_text, f'Orphaned formatting guide not indexed in {RULE_DOC.name}: {rel}')
			self._assert_clean_doc(guide)
	# 2026-11-26
	# "Codify navigable cross-reference standards and override SLOC exemption":
	# https://github.com/dmitry-ai/harness/issues/286
	def test_xref_standards_codified_for_python_javascript_and_java(self) -> None:
		rule_text = self._assert_clean_doc(RULE_DOC)
		self.assertLess(len(RULE_DOC.read_bytes()), 6000)
		for token in ('programming/java.md', '@used-by', '@uses', '@see', '@override', 'xref-sync', 'xref-check'):
			self.assertIn(token, rule_text, f'Missing cross-reference token {token!r} in {RULE_DOC.name}')
		py_text = self._assert_clean_doc(CODE_FORMATTING_DIR / 'programming/python.md')
		for token in ('@used-by', '@uses', '@see', '@override', ':func:', ':meth:', 'typing', 'self.', 'xref-sync'):
			self.assertIn(token, py_text, f'Missing Python xref token {token!r}')
		js_text = self._assert_clean_doc(CODE_FORMATTING_DIR / 'programming/javascript.md')
		for token in ('@used-by', '@uses', '@see', '@override', '{@link', 'import(', 'TypeScript', 'override'):
			self.assertIn(token, js_text, f'Missing JS/TS xref token {token!r}')
		java_text = self._assert_clean_doc(CODE_FORMATTING_DIR / 'programming/java.md')
		for token in ('11-code-formatting.md#code-1', '- @used-by', '- @uses', '@see', '@Override', '{@link', '-Xdoclint:all', 'not part of'):
			self.assertIn(token, java_text, f'Missing Java xref token {token!r}')
if '__main__' == __name__:
	unittest.main()
