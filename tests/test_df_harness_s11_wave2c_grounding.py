# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import json
import re
import sys
import tempfile
import unittest
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPTS_DIR))
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DfHarnessS11Wave2CGroundingTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_active_corpus_builder_and_block_line_auditor(self) -> None:
		from Df.Harness.Grounding.ActiveCorpusBuilder import ActiveCorpusBuilder
		from Df.Harness.Grounding.BlockLineAuditor import BlockLineAuditor
		from Df.Harness.Grounding.LocalSourceAuditor import LocalSourceAuditor
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			src = root / 'source.md'
			src.write_text('## 1 — Alice (2026)\norder_id/998877\nmem_total: 4096\nQuote: hello verified world here\n', encoding='utf-8')
			aud = LocalSourceAuditor(root, 'Per [src](source.md): `order_id/998877` and 4096.', observed_texts={'https://example.com/p': ['extra 7777 text']})
			infos, raw, norm, nums, label = ActiveCorpusBuilder(aud, [src], ['https://example.com/p#frag'], [src]).build()
			self.assertEqual(1, len(infos))
			self.assertIn('7777', nums)
			self.assertEqual('source.md', label)
			self.assertEqual([], aud.run())
			bad_aud = LocalSourceAuditor(root, 'Per [src](source.md): `"unseen literal text"` \u00abunseen verbatim phrase\u00bb `order_id/123456` /sales/order/view/order_id/123456 and 8888 MB.\n\n> \u00abunseen quoted block text\u00bb\n')
			bad_errs = bad_aud.run()
			self.assertTrue(any(('123456' in e for e in bad_errs)))
			self.assertTrue(any(('8888' in e for e in bad_errs)))
			self.assertIn('message #9 (available: [1])', BlockLineAuditor.line_grounded_numbers_check('Message #9 says 4096', {'4096'}, {1}, set(), True))
			self.assertEqual([], BlockLineAuditor.line_grounded_numbers_check('Ran 10 tests in 0.2s', set(), set(), set(), False))
	# @used-by :mod:`unittest`
	def test_cli_command_and_doc5_requirement_auditors(self) -> None:
		from Df.Harness.Grounding.CliCommandAuditor import CliCommandAuditor
		from Df.Harness.Grounding.Doc5ContextDetector import Doc5ContextDetector
		from Df.Harness.Grounding.Doc5RequirementChecker import Doc5RequirementChecker
		self.assertTrue(CliCommandAuditor.is_passing_output('{"ok": true}\nCommand exited with code 0'))
		self.assertFalse(CliCommandAuditor.is_passing_output('{"ok": false}\nCommand exited with code 0'))
		self.assertTrue(Doc5RequirementChecker.is_failed_cli_output('{"ok": false}'))
		self.assertTrue(Doc5RequirementChecker.is_failed_cli_output('Traceback (most recent call last)'))
		turn_fail = {'turn_id': 't1', 'start_step': 0, 'final_step': 5, 'issue_actions': [{'action': 'create', 'repo': 'o/r', 'parent_number': None, 'step': 3}]}
		with tempfile.TemporaryDirectory() as td:
			f_fail = Path(td) / 'fail.jsonl'
			f_fail.write_text('\n'.join((json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'arguments': {'CommandLine': 'python scripts/harness.py rename-project --domain example.com'}}]}), json.dumps({'step_index': 2, 'type': 'GENERIC', 'content': '{"ok": false}\nCommand exited with code 1'}))) + '\n', encoding='utf-8')
			f_ok = Path(td) / 'ok.jsonl'
			f_ok.write_text('\n'.join((json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'arguments': {'CommandLine': 'python scripts/harness.py shadow-replay --exec-rename-domain example.com'}}]}), json.dumps({'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 0'}))) + '\n', encoding='utf-8')
			native = {'source_file': str(f_fail)}
			native_ok = {'source_file': str(f_ok)}
			self.assertTrue(Doc5RequirementChecker({'root': None, 'turn': turn_fail, 'native': native}).is_required())
			self.assertTrue(Doc5RequirementChecker({'bug_report_signal': True}).is_required())
			resp = 'Run `python scripts/harness.py rename-project --domain example.com` now.'
			self.assertTrue(CliCommandAuditor(resp, turn=turn_fail, native=native).audit())
			self.assertEqual([], CliCommandAuditor(resp, turn=turn_fail, native=native_ok).audit())
		mode = Doc5ContextDetector('plain', [], [], 'auto', turn_context={'bug_report_signal': True}, prob_head_re=re.compile('problem'), req_cmd_fn=lambda _: False, explicit_fn=lambda _: ([], [])).detect()
		self.assertEqual('problem', mode)
	# @used-by :mod:`unittest`
	def test_df_analysis_problem_tracks_scatter_banner_and_statements(self) -> None:
		from Df.Harness.Grounding.DfAnalysisValidator import DfAnalysisValidator
		from Df.Harness.Grounding.ProblemTrackAuditor import ProblemTrackAuditor
		from Df.Harness.Grounding.ScatterBannerAuditor import ScatterBannerAuditor
		from Df.Harness.Grounding.StatementDirValidator import StatementDirValidator
		from Df.Harness.lib.grounding import SCATTER_BANNER
		from Df.Harness.lib.grounding_md import dfh_external_anchor_issues, dfh_markdown_table_issues
		self.assertTrue(dfh_markdown_table_issues('| A | B |\n|---|---|\n| 1 | 2 |\n'))
		self.assertTrue(dfh_external_anchor_issues('Docs', 'https://docs.example.com/guide', 'https://docs.example.com/guide', {'https://docs.example.com/guide': {'intro'}}, 'no exception'))
		self.assertTrue(ScatterBannerAuditor.proposes_external_scattering('### M-1\nMove caches to /tmp/cache\n'))
		self.assertTrue(ScatterBannerAuditor.has_leading_banner(f'### M-1\n{SCATTER_BANNER}\nMove caches to /tmp/cache\n'))
		self.assertTrue(ScatterBannerAuditor('### M-1\nStore state in /tmp/state\n', mode='general').audit())
		bad_prob = '# 0 Metadata\n```json\n{"Project": "P"}\n```\n# 1 Problem\nshort\n'
		errs = DfAnalysisValidator(bad_prob, mode='problem').validate()
		self.assertTrue(any(('Issue' in e for e in errs)))
		self.assertTrue(any(('at least 4' in e for e in errs)))
		self.assertTrue(ProblemTrackAuditor([]).audit())
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			self.assertTrue(StatementDirValidator(base / 'missing').validate())
			self.assertTrue(StatementDirValidator(base).validate())
			(base / '1').mkdir()
			(base / '1' / '.md').write_text('ok', encoding='utf-8')
			(base / '1' / 'Test.md').write_text('ok', encoding='utf-8')
			self.assertEqual([], StatementDirValidator(base).validate())
	# @used-by :mod:`unittest`
	def test_domain_fact_extractor_and_contradiction_checker(self) -> None:
		from Df.Harness.Grounding.DomainFactExtractor import DomainFactExtractor
		from Df.Harness.Grounding.FactContradictionChecker import FactContradictionChecker
		with tempfile.TemporaryDirectory() as td:
			p = Path(td) / 'facts.json'
			p.write_text(json.dumps({'tier': 'M', 'mem_total': 4096, 'swap_total': 0, 'vcpu': None, 'cpus': 4}), encoding='utf-8')
			tuples = DomainFactExtractor(p, root=Path(td)).extract()
			self.assertTrue(any(('Plan M' == t['entity'] for t in tuples)))
			md_p = Path(td) / 'source.md'
			md_p.write_text('## 1 — John Doe (2026)\nPlan M mem_total=4096\nload average: 1.5\n', encoding='utf-8')
			is_t, msgs, _ = DomainFactExtractor.extract_ticket_metadata(md_p, md_p.read_text(encoding='utf-8'))
			self.assertTrue(is_t and 1 in msgs)
			md_tuples = DomainFactExtractor(md_p, root=Path(td)).extract()
			infos = [{'path': md_p, 'tier': 'tier_0', 'raw': 'mem_total=4096', 'fact_tuples': tuples + md_tuples}]
			self.assertTrue(FactContradictionChecker('Plan M has 8 vcpu', infos).check())
			self.assertTrue(FactContradictionChecker('Server has 16 GB RAM burst 16 GB', infos).check())
			self.assertTrue(FactContradictionChecker('Server is swapping heavily', infos).check())
			self.assertTrue(FactContradictionChecker('load average overload saturating CPU', infos).check())
			self.assertTrue(DomainFactExtractor.order_url_issues('/sales/order/view/order_id/55555', set(), '', 'src'))
			self.assertTrue(DomainFactExtractor.ticket_author_issues('\u0418\u0432\u0430\u043d \u0418\u0432\u0430\u043d\u043e\u0432 (`Ghost Person`)', 'john doe', 'src'))
	# @used-by :mod:`unittest`
	def test_locale_verifier_probability_and_scope_deferral(self) -> None:
		from Df.Harness.Grounding.LocaleVerifier import LocaleVerifier
		from Df.Harness.Grounding.ProbabilityClaimChecker import ProbabilityClaimChecker
		from Df.Harness.Grounding.ScopeDeferralEvaluator import ScopeDeferralEvaluator
		self.assertEqual('und', LocaleVerifier.detect_prose_locale('12345')['locale_family'])
		self.assertEqual('en', LocaleVerifier.detect_prose_locale('The system checks every file and verifies results')['locale_family'])
		self.assertTrue(LocaleVerifier('\u042d\u0442\u043e \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u0442\u0435\u043a\u0441\u0442 \u0434\u043b\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u043b\u043e\u043a\u0430\u043b\u0438', target_locale='en-US').verify())
		self.assertTrue(LocaleVerifier('English text in a Russian container request', target_locale='und', container_text='\u041f\u0440\u043e\u0432\u0435\u0440\u044c \u044d\u0442\u0443 \u0437\u0430\u0434\u0430\u0447\u0443 \u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430').verify())
		self.assertEqual([], LocaleVerifier('English reply', target_locale='und', container_text='\u041d\u0430\u043f\u0438\u0448\u0438 in english', allow_explicit_english_request=True).verify())
		self.assertEqual('Clean title', LocaleVerifier.extract_authored_prose('Clean `code` title https://x.test', is_title=True))
		self.assertTrue(ProbabilityClaimChecker('Because of lack of evidence we assign 50/50 equal probability.').check())
		self.assertEqual([], ProbabilityClaimChecker('Lack of evidence does not prove 50/50 equal probability.').check())
		lc = {'deferred_children': [{'children': ['https://github.com/o/r/issues/2']}]}
		res_fail = ScopeDeferralEvaluator({}, {}, lc, 'Done without explanation.').evaluate()
		self.assertFalse(res_fail['verified'])
		turn_ok = {'clarifications': [{'ask_step': 1, 'answer_step': 2, 'answers': [{'id': 'A1', 'text': 'Please stop the turn after issue 1'}]}]}
		res_ok = ScopeDeferralEvaluator(turn_ok, {}, lc, 'Deferred issue 2 because user confirmed A1.').evaluate()
		self.assertTrue(res_ok['verified'])
		failed: list[tuple[str, str]] = []
		runner = SimpleNamespace(turn={}, value={}, response='Done.', blocked_report=False, _fail_gate=lambda g, m: failed.append((g, m)))
		ScopeDeferralEvaluator.check_runner(runner, lc)
		self.assertTrue(failed)
	# @used-by :mod:`unittest`
	def test_response_auditor_ingestor_and_tier0_index(self) -> None:
		from Df.Harness.Grounding.EvidenceBundleIngestor import EvidenceBundleIngestor
		from Df.Harness.Grounding.ResponseAuditor import ResponseAuditor
		from Df.Harness.Grounding.Tier0Index import Tier0Index
		from Df.Harness.lib.grounding import dfh_read_only_grounding
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			ev_dir = root / '\ua616' / 'KB' / 'Evidence'
			ev_dir.mkdir(parents=True)
			(ev_dir / 'topic.json').write_text(json.dumps({'url': 'https://forum.example.com/t/hello/42', 'title': 'Verified Forum Topic Title', 'body': 'exact observed body text for verification', 'topics': [{'id': 43, 'title': 'Second Topic', 'slug': 'second'}]}), encoding='utf-8')
			(ev_dir / 'source.md').write_text('Plan M mem_total: 4096\n', encoding='utf-8')
			idx = Tier0Index.for_root(root)
			with dfh_read_only_grounding():
				found = idx.discover_entities('Plan M mem_total')
			self.assertTrue(found)
			ledger = idx.sync_ledger()
			self.assertGreaterEqual(ledger['tuple_count'], 1)
			self.assertEqual(root.resolve(), Tier0Index.infer_source_root(ev_dir / 'source.md'))
			self.assertEqual('tier_0', Tier0Index.hydrate_standalone(ev_dir / 'source.md')['tier'])
			resp = 'See [Verified Forum Topic Title](https://forum.example.com/t/hello/42) for details.'
			aud = ResponseAuditor(root, resp, [])
			aud._extract_markdown_refs()
			self.assertEqual(1, len(aud.authored_links))
			EvidenceBundleIngestor(aud).ingest()
			self.assertIn('https://forum.example.com/t/hello/42', aud.observed_urls)
			self.assertEqual([], ResponseAuditor(root, resp, []).validate())
			with self.assertRaises(AttributeError):
				_ = aud.nonexistent_attr
if '__main__' == __name__:
	unittest.main()