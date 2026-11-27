# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from Df.Harness.Grounding.DfAnalysisValidator import DfAnalysisValidator
from Df.Harness.Grounding.LocaleVerifier import LocaleVerifier
from Df.Harness.Grounding.ProblemTrackAuditor import ProblemTrackAuditor
from Df.Harness.Grounding.ResponseAuditor import ResponseAuditor
from Df.Harness.Grounding.ScopeDeferralEvaluator import ScopeDeferralEvaluator
from Df.Harness.Grounding.Tier0Index import Tier0Index
from Df.Harness.lib.grounding_md import dfh_parse_section_items
from agent_tools import source_grounding as sg
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DfHarnessS11Wave2CCovGroundingTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_df_analysis_validator_general_and_section_lists(self) -> None:
		resp = '## H-1\nCause [doc](https://example.com) arguments for: x; arguments against: y; 60%\n## H-2\nOther [doc](https://example.com) arguments for: a; arguments against: b; 40%\n## M-1\nFix arguments for: x; arguments against: y; 80%\n## M-2\nAlt arguments for: a; arguments against: b; 20%\n'
		self.assertEqual([], DfAnalysisValidator.analysis_gate_issues(resp, requests=['/df-analysis']))
		parsed = dfh_parse_section_items('- H-1 alpha\n  extra\n- H-2 beta\n')
		self.assertEqual(2, len(parsed))
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_evidence_bundle_ingestor_and_response_auditor(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			ev = root / 'ꘖ/KB/Evidence/obs1'
			ev.mkdir(parents=True)
			(ev / 'raw.html').write_text('<html><head><title>Doc Title</title></head><body><h2 id="sec-a">Section A</h2><p>Observed verbatim sentence for testing grounding.</p></body></html>', encoding='utf-8')
			(ev / 'observation.json').write_text(json.dumps({'url': 'https://docs.example.com/guide', 'final_url': 'https://docs.example.com/guide', 'status': 200, 'raw_file': 'raw.html', 'content_type': 'text/html'}), encoding='utf-8')
			(root / 'ꘖ/KB/Project.md').write_text('Ref https://docs.example.com/guide\n', encoding='utf-8')
			(root / 'notes.md').write_text('# Heading\nBody text without ungrounded numbers.\n', encoding='utf-8')
			resp = 'See [Doc Title](https://docs.example.com/guide#sec-a).\n\n> «Observed verbatim sentence for testing grounding.»\n'
			errs = ResponseAuditor(root, resp, requests=[{'text': 'Check https://docs.example.com/guide'}], touched_files=['notes.md']).validate()
			self.assertEqual([], errs)
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_locale_problem_track_scope_deferral_tier0_and_facade(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			loc_errs = LocaleVerifier('English text with enough words to evaluate properly.', target_locale='und', container_text='Текст на русском языке для проверки локали.', default_locale='ru-RU').verify()
			self.assertTrue(bool(loc_errs))
			blocks = [
				{'header': 'Primary', 'sections': {0: ('', ''), 1: ('Problem', 'failure trace')}},
				{'header': 'Culprit', 'sections': {0: ('', ''), 1: ('Culprit attribution', 'who broke it')}},
				{'header': 'Test Escape', 'sections': {0: ('', ''), 1: ('Test escape', 'why tests missed it')}},
				{'header': 'Journal', 'sections': {0: ('', ''), 1: ('Journal integrity', 'bypassed the journal')}},
			]
			self.assertEqual([], ProblemTrackAuditor(blocks).audit())
			sd = ScopeDeferralEvaluator({'clarifications': [{'ask_step': 1, 'answers': [{'id': 'A1', 'text': 'continue later'}]}]}, None, {'deferred_children': [{'children': ['https://github.com/o/r/issues/2']}]}, 'Deferred without consent').evaluate()
			self.assertFalse(sd['verified'])
			idx = Tier0Index.for_root(root)
			idx.seed_entries({})
			self.assertEqual({}, idx.entries)
			src = root / 'source.md'
			src.write_text('Ticket #12345 message #1\n', encoding='utf-8')
			self.assertIn('tickets', sg.extract_domain_entities('Ticket #999'))
			self.assertIsInstance(sg.extract_fact_tuples(src, root=root), list)
			self.assertIsInstance(sg.extract_ticket_metadata(src, 'Ticket #12345'), tuple)
			self.assertEqual([], sg.fact_tuple_contradictions('Plain text', []))
			self.assertEqual([], sg.order_url_issues('Plain text', set(), '', 'src'))
			self.assertEqual([], sg.ticket_author_issues('Plain text', '', 'src'))
			self.assertEqual([], sg.ticket_message_issues('Plain text', set(), set()))
if '__main__' == __name__:
	unittest.main()
