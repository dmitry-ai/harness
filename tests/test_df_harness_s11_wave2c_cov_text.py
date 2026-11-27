# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from Df.Harness.Research.Page import Page
from Df.Harness.Text.Article.Linter import Linter as ArticleLinter
from Df.Harness.Text.Article.NumberedParser import NumberedParser
from Df.Harness.Text.Article.SourceExporter import SourceExporter as ArticleSourceExporter
from Df.Harness.Text.CliRunner import CliRunner
from Df.Harness.Text.DiagnosticsScanner import DiagnosticsScanner
from Df.Harness.Text.KeyedProseRewriter import KeyedProseRewriter
from Df.Harness.Text.ResponseChecker import ResponseChecker
from Df.Harness.Text.WorkspaceScopeChecker import WorkspaceScopeChecker
from Df.Harness.lib.text_core import dfh_excerpt, dfh_scan
from Df.Harness.lib.text_sources import dfh_check_claim_sources, dfh_check_source_links
from Df.Harness.lib.text_workflow import dfh_record_text_answer
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DfHarnessS11Wave2CCovTextTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_article_linter_structure_source_exporter_and_sections(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			art = "# I. First Part\n## 1. Parent Group (2)\n<a name='I.1'></a>\n### 1.1. Child One (1)\n<a name='I.1.1'></a>\n1. Item referencing **[§§1.1–1.3](#I.1.1)**.\n### 1.2. Child Two and Three, With Extra Long Title Case Heading Words Here (1)\n<a name='I.1.2'></a>\nSee §1.1 and §§1.1–1.2.\n# II. Second Part\n## 1. Action\n<a name='II.1'></a>\nUses **[§I.1.1](#I.1.1)**.\n"
			findings = ArticleLinter(art, path=root / 'article.md').lint()
			rules = {f.rule for f in findings}
			self.assertIn('REF-DANGLING', rules)
			self.assertIn('HEADING-ENUM', rules)
			sections = NumberedParser(dfh_scan(art)).parse()
			self.assertGreaterEqual(sections[0].span_dict()['subtree_end'], sections[0].end)
			exported = ArticleSourceExporter(art).export()
			self.assertIn('§@I.1.1', exported)
			self.assertEqual('long tex…', dfh_excerpt('long text here', re.search('long', 'long text here'), 4))
			rew = KeyedProseRewriter('See [ok](#@k1) and [bad](#@k2).', 1, {'k1': '1'}, [], [], format_ref=lambda _m, s, _e: s, anchors={'k1': '1'}).rewrite()
			self.assertIn('(#1)', rew)
			sc = WorkspaceScopeChecker({'mode': 'edit', 'changes': 'content', 'kind': 'article', 'allow_sections': ['I.1.1-I.1.2', 'I.1.1']}, art, art).check()
			self.assertEqual([], sc)
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_cli_runner_source_render_and_text_helpers(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			art = root / 'art.md'
			art.write_bytes("# I. Part\n## 1.\n<a name='I.1'></a>\nClaim text.\n# II. Part\n## 1.\n<a name='II.1'></a>\nUses **[§I.1](#I.1)**.\n".encode('utf-8'))
			buf = io.StringIO()
			with patch('sys.stdout', buf):
				rc = CliRunner(['source', '--kind', 'article', str(art)]).run()
			self.assertEqual(0, rc)
			keyed = root / 'keyed.md'
			keyed.write_bytes(buf.getvalue().encode('utf-8'))
			out_file = root / 'rendered.md'
			with patch('sys.stdout', io.StringIO()):
				self.assertEqual(0, CliRunner(['render', '--kind', 'article', '--diff', str(keyed)]).run())
				self.assertEqual(0, CliRunner(['render', '--kind', 'article', '--output', str(out_file), str(keyed)]).run())
			self.assertTrue(out_file.is_file())
			reg = root / 'ꘖ/KB/TextClaims.json'
			reg.parent.mkdir(parents=True)
			reg.write_text(json.dumps({'schema_version': 3, 'claims': {}}), encoding='utf-8')
			self.assertTrue(dfh_check_claim_sources(root, [])['valid'])
			link_errs = dfh_check_source_links('See [doc](https://example.com/a#sec).', fetcher=lambda u, _t=15: Page(u, 200, 'text/html', '<h2 id="sec">Sec</h2>'))
			self.assertEqual([], link_errs)
			with patch('agent_tools.journal.record_answer', return_value=[1]):
				rec = dfh_record_text_answer(root, root / 'ꙮ', ['req'], 'resp', 't1')
			self.assertEqual([1], rec['journal_steps'])
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_diagnostics_scanner_and_response_checker(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			(root / 'AGENTS.md').write_text('# Agents\n', encoding='utf-8')
			(root / 'extra.md').write_text('# Extra\n', encoding='utf-8')
			sk = root / '.agents/skills/demo'
			sk.mkdir(parents=True)
			(sk / 'SKILL.md').write_text('---\nname: demo\n---\nSee [extra](<extra.md>)\n', encoding='utf-8')
			(root / '.agents/r1.md').write_text('# Rule\n', encoding='utf-8')
			(root / '.agents/rules.json').write_text(json.dumps({'entries': [{'path': 'r1.md', 'when': 'always'}]}), encoding='utf-8')
			(root / '.codex').mkdir()
			(root / '.codex/config.toml').write_text('developer_instructions = "See [doc](<extra.md>)"\nproject_doc_fallback_filenames = ["AGENTS.md", "../bad.md"]\n', encoding='utf-8')
			diag = DiagnosticsScanner(root, platform='codex', config={'workspace_root': str(root), 'platforms': {'codex': {'instances': {}}}}).run()
			self.assertTrue(any(('UNSUPPORTED-DOC-SELECTOR' == c['code'] for c in diag['conflicts'])))
			res_dir = root / 'ꙮ/≺'
			res_dir.mkdir(parents=True)
			body = 'I removed `legacy_token` from the target file completely.\n'
			(res_dir / '1.md').write_text(body, encoding='utf-8')
			r2 = res_dir / '2.md'
			r2.write_text(body, encoding='utf-8')
			target = root / 'target.md'
			target.write_text('Still contains legacy_token here.\n', encoding='utf-8')
			rc_findings = ResponseChecker(r2, against=[target]).check()
			rules = {f.rule for f in rc_findings}
			self.assertIn('RESP-CLAIM', rules)
			self.assertIn('RESP-DUP', rules)
if '__main__' == __name__:
	unittest.main()
