# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :mod:`unittest`
class DfHarnessS11Wave2CTextDocsTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_article_subsystem_roundtrip_and_audit(self) -> None:
		from Df.Harness.Text.AddressedSection import AddressedSection
		from Df.Harness.Text.Article.GraphAuditor import GraphAuditor
		from Df.Harness.Text.Article.KeyedParser import KeyedParser
		from Df.Harness.Text.Article.LinkStyleAuditor import LinkStyleAuditor
		from Df.Harness.Text.Article.NumberedParser import NumberedParser
		from Df.Harness.Text.Article.Renderer import Renderer as ArticleRenderer
		from Df.Harness.Text.Article.Section import Section
		from Df.Harness.Text.Article.SourceExporter import SourceExporter as ArticleExporter
		from Df.Harness.Text.Article.StructureAuditor import StructureAuditor
		from Df.Harness.lib.text_core import dfh_scan
		from agent_tools import article, text_sections
		self.assertIs(AddressedSection, text_sections.AddressedSection)
		self.assertIs(Section, article.Section)
		doc = "# I. Analysis\n## 1\n<a name='I.1'></a>\nhttps://example.org/doc\n# II. Recommendations\n## 1\n<a name='II.1'></a>\nAct on **[§I.1](#I.1)**.\n"
		lines = dfh_scan(doc)
		secs = NumberedParser(lines).parse()
		self.assertEqual(['I.1', 'II.1'], [s.key for s in secs])
		s_findings, g_findings, l_findings = ([], [], [])
		StructureAuditor(lines, secs, s_findings).audit()
		GraphAuditor(lines, secs, g_findings).audit()
		LinkStyleAuditor(lines, l_findings, 'formatted').audit()
		self.assertEqual([], [f for f in s_findings + g_findings if 'error' == f.severity])
		self.assertIn('LINK-BARE', {f.rule for f in l_findings})
		keyed_src = ArticleExporter(doc).export()
		keyed_secs, _ = KeyedParser(dfh_scan(keyed_src), []).parse()
		self.assertEqual(['I.1', 'II.1'], [s.name for s in keyed_secs])
		rendered, _, r_findings = ArticleRenderer(keyed_src).render()
		self.assertEqual([], r_findings)
		self.assertEqual(doc, rendered)
	# @used-by :mod:`unittest`
	def test_diagnostics_scanner_and_response_checker(self) -> None:
		from Df.Harness.Text.DiagnosticsScanner import DiagnosticsScanner
		from Df.Harness.Text.ResponseChecker import ResponseChecker
		from agent_tools import text_diagnostics
		self.assertIs(DiagnosticsScanner, text_diagnostics.SourceDiagnosticsScanner)
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			prim = base / 'primary'
			(prim / 'rules').mkdir(parents=True)
			(prim / 'skills/demo').mkdir(parents=True)
			(prim / 'platforms').mkdir(parents=True)
			(prim / 'runtime.json').write_text(json.dumps({'workspace_root': str(base), 'platforms': {'antigravity': {'enabled': True}}}), encoding='utf-8')
			(prim / 'rules/00-scope.md').write_text('---\ntrigger: always_on\n---\n# Scope\n', encoding='utf-8')
			(prim / 'skills/demo/SKILL.md').write_text('---\nname: demo\n---\n# Demo\n', encoding='utf-8')
			(prim / 'platforms/antigravity.md').write_text('# AG\n', encoding='utf-8')
			(base / '\ua616/data').mkdir(parents=True)
			proj_dir = base / 'proj'
			(proj_dir / '\ua616/data').mkdir(parents=True)
			cand = proj_dir / 'resp.md'
			cand.write_text('Done.\n', encoding='utf-8')
			self.assertEqual([], ResponseChecker(cand, lexicon=[]).check())
			scanner = DiagnosticsScanner(proj_dir, config=json.loads((prim / 'runtime.json').read_text(encoding='utf-8')), primary=prim)
			self.assertTrue(scanner.run()['valid'])
			self.assertTrue(all((hasattr(scanner, k) for k in ('_record_issue', '_add_source', '_inspect_native_toml', '_check_rule_and_skill_divergence'))))
	# @used-by :mod:`unittest`
	def test_proposal_subsystem_roundtrip_and_fields(self) -> None:
		from Df.Harness.Text.Proposal.Block import Block
		from Df.Harness.Text.Proposal.FieldLinter import FieldLinter
		from Df.Harness.Text.Proposal.Linter import Linter as ProposalLinter
		from Df.Harness.Text.Proposal.Parser import Parser as ProposalParser
		from Df.Harness.Text.Proposal.Renderer import Renderer as ProposalRenderer
		from Df.Harness.Text.Proposal.SourceExporter import SourceExporter as ProposalExporter
		from agent_tools import proposal
		self.assertIs(Block, proposal.ProposalBlock)
		prop = '1. Fact about storefront.\n2. Action based on §1.\n'
		blocks = ProposalParser(prop).parse()
		self.assertEqual(['1', '2'], [b.key for b in blocks])
		self.assertEqual([], ProposalLinter(prop, lexicon=[], bans=[]).lint())
		p_src = ProposalExporter(prop).export()
		p_ren, _, p_find = ProposalRenderer(p_src).render()
		self.assertEqual([], p_find)
		self.assertEqual(prop, p_ren)
		self.assertEqual([], FieldLinter({'cover': 'hello'}, {'cover': 10}).lint())
		self.assertIn('PROPOSAL-FIELD-LIMIT', {f.rule for f in FieldLinter({'cover': 'hello'}, {'cover': 3}).lint()})
	# @used-by :mod:`unittest`
	def test_text_core_linters_replayer_and_sections(self) -> None:
		from Df.Harness.Text.CodeBlockLinter import CodeBlockLinter
		from Df.Harness.Text.CommandReplayer import CommandReplayer
		from Df.Harness.Text.Finding import Finding
		from Df.Harness.Text.KeyedProseRewriter import KeyedProseRewriter
		from Df.Harness.Text.Line import Line
		from Df.Harness.Text.MechanicalProjector import MechanicalProjector
		from Df.Harness.Text.ProseLinter import ProseLinter
		from Df.Harness.lib.text_core import dfh_changed_command_lines, dfh_clean, dfh_detect_language, dfh_scan, dfh_sentences
		from Df.Harness.lib.text_sections import dfh_content_blocks
		from agent_tools import text_core
		self.assertIs(Finding, text_core.Finding)
		self.assertIs(Line, text_core.Line)
		self.assertIn('[error] R1', Finding('error', 'R1', 2, 'bad').format('a.md'))
		lines = dfh_scan('```bash\nprintf ok\n```\n> ok\n')
		self.assertEqual(['fence', 'code', 'fence', 'quote'], [l.kind for l in lines])
		self.assertEqual('en', dfh_detect_language('Storefront latency increased.'))
		self.assertEqual(2, len(dfh_sentences('First sentence. Second sentence.')))
		self.assertEqual('Hello CODE world.', dfh_clean('Hello `x` world.'))
		self.assertEqual([1], dfh_changed_command_lines('```bash\nprintf ok\n```\n> ok\n'))
		code_findings, prose_findings = ([], [])
		CodeBlockLinter(dfh_scan('```bash\ncurl https://example.org/assets/app-Abc12345.js\n```'), code_findings).check()
		self.assertIn('CODE-VOLATILE', {f.rule for f in code_findings})
		ProseLinter(dfh_scan('**Label**: bad leadin.\n'), 'article', 'en', prose_findings, [], []).check()
		self.assertIn('BOLD-LEADIN', {f.rule for f in prose_findings})
		rep = CommandReplayer('```bash\nprintf ok\n```\n> ok\n').replay()
		self.assertEqual('match', rep[0]['status'])
		proj = MechanicalProjector('1. See §1.\n', 'proposal', 'renumber').project()
		self.assertIn('REF:0', proj)
		rw_findings, ext_changes = ([], [])
		rewritten = KeyedProseRewriter('See §@a.', 1, {'a': '1'}, rw_findings, ext_changes, format_ref=lambda _m, s, _e: f'§{s}').rewrite()
		self.assertEqual('See §a.', rewritten)
		self.assertEqual(['1', '2'], [b['section'] for b in dfh_content_blocks('One.\n\nTwo.', 'letter')])
if '__main__' == __name__:
	unittest.main()
