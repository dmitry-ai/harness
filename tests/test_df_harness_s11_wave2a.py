# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from decimal import Decimal
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
# @used-by :func:`_seed_v3_project()`
def _intake_claim(cid: str, eid: str, quote: str, ptr: str, ref: str, sha: str) -> dict:
	return {
		'id': cid,
		'essence': quote,
		'assessment_basis': 'Verbatim saved intake quote.',
		'knowledge_type': 'client_report',
		'verification_status': 'verified',
		'scope': {'description': 'Saved intake file.', 'sample': [ref], 'limitations': ['Intake only.']},
		'properties': ['content'],
		'missing_checks': [],
		'derived_from': [],
		'materiality': 'routine',
		'novelty': 'new',
		'category': 'descriptive',
		'impact': {'severity': 'unknown', 'basis': 'Not measured.', 'evidence_claim_ids': []},
		'probability_percent': 100,
		'addresses': [],
		'evidence': [{'id': eid, 'kind': 'intake', 'source': ref, 'manifest': ref, 'source_sha256': sha, 'quote': quote, 'locator': {'type': 'json_pointer', 'value': ptr}}],
		'for': [{'argument': 'Exact quote.', 'evidence_id': eid}],
		'against': [],
		'counterevidence': {'status': 'not_found', 'reviewed_sources': [ref], 'limitations': 'Intake only.'},
	}
# @used-by :meth:`DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
# @used-by :meth:`DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
# @used-by :meth:`DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
# @used-by :meth:`DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
def _seed_http_obs(root: Path, url: str='https://example.com/doc') -> tuple[Path, dict]:
	obs_dir = root / '\ua616/KB/Evidence/HTTP/obs1'
	obs_dir.mkdir(parents=True, exist_ok=True)
	body = '<html><head><title>Doc Title</title></head><body><h1 id="sec1">Heading</h1><p>Verified phrase 42.</p><h2>NoAnchor</h2><p>Plain section text.</p></body></html>'.encode('utf-8')
	(obs_dir / 'response.bin').write_bytes(body)
	meta = {'schema_version': 1, 'url': url, 'final_url': url, 'status': 200, 'kind': 'http', 'content_type': 'text/html; charset=utf-8', 'charset': 'utf-8', 'body_sha256': hashlib.sha256(body).hexdigest(), 'body_bytes': len(body), 'observation': 'Evidence/HTTP/obs1/observation.json'}
	obs_json = obs_dir / 'observation.json'
	obs_json.write_text(json.dumps(meta), encoding='utf-8')
	(root / '\ua616/data').mkdir(parents=True, exist_ok=True)
	(root / '\ua616/data/http-index.json').write_text(json.dumps({'k1': {'observation': meta['observation']}}), encoding='utf-8')
	return (obs_json, meta)
# @used-by :meth:`DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
# @used-by :meth:`DfHarnessS11Wave2aTests.test_claim_graph_and_validators()`
# @used-by :meth:`DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
# @used-by :meth:`DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
# @used-by :meth:`DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
def _seed_v3_project(root: Path, title: str='Store Feed Fix', concern: str='Feed lags 100 USD') -> tuple[str, str, dict, dict]:
	raw = json.dumps({'job_id': '~01wave2a', 'title': title, 'concern': concern, 'price_a': {'amount': '100', 'currency': 'USD'}, 'price_b': {'amount': '120', 'currency': 'USD'}}).encode('utf-8')
	sha = hashlib.sha256(raw).hexdigest()
	intake = root / f'\ua616/KB/Evidence/{sha}.json'
	intake.parent.mkdir(parents=True, exist_ok=True)
	intake.write_bytes(raw)
	(root / '\ua616/project.json').write_text(json.dumps({'initialized': True, 'job_id': '~01wave2a', 'snapshot': f'\ua616/KB/Evidence/{sha}.json', 'request_date': '2026-11-26'}), encoding='utf-8')
	(root / '.md').write_text('# Project\n\nManual notes.\n', encoding='utf-8')
	ref = f'Evidence/{sha}.json'
	c_id = _intake_claim('F-TITLE', 'E-TITLE', title, '/title', ref, sha)
	c_con = _intake_claim('F-CONCERN', 'E-CONCERN', concern, '/concern', ref, sha)
	return (ref, sha, c_id, c_con)
# @used-by :mod:`unittest`
class DfHarnessS11Wave2aTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_analysis_merger_and_lifecycle_classes(self) -> None:
		from Df.Harness.Analysis.CandidateMerger import CandidateMerger
		from Df.Harness.Analysis.Merger import Merger
		from Df.Harness.Analysis.OwnedPublisher import OwnedPublisher
		from Df.Harness.Analysis.Publisher import Publisher
		from Df.Harness.Analysis.Renderer import Renderer
		from Df.Harness.Analysis.Saver import Saver
		from Df.Harness.Analysis.Validator import Validator
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			_, _, c_id, c_con = _seed_v3_project(root)
			merged_c = CandidateMerger({'facts': [], 'identity': [c_id]}, {'identity': [], 'concerns': [c_con], 'remove_claim_ids': ['F-TITLE'], 'notes': {'causes': 'None'}}).merge()
			self.assertEqual([], merged_c['identity'])
			self.assertEqual(['F-CONCERN'], [x['id'] for x in merged_c['concerns']])
			draft = Merger(root, {'identity': [c_id], 'websites': [{'role': 'client', 'url': None, 'basis_id': 'F-TITLE'}]}, partial=True).save()
			self.assertTrue(draft['partial'])
			notes = {'misconceptions': 'None.', 'causes': 'Pending.', 'methods': 'Pending.'}
			final = Merger(root, {'concerns': [c_con], 'notes': notes, 'red_flags': []}, partial=False).save()
			self.assertTrue(final['draft_cleared'])
			val = json.loads((root / '\ua616/KB/Analysis.json').read_text(encoding='utf-8'))
			self.assertEqual([], Validator(val).issues())
			self.assertIn('# 1. Client Identification', Renderer(val).render())
			self.assertEqual('published', Publisher(root / '\ua616/KB/Analysis.json').publish()['status'])
			self.assertEqual('published', OwnedPublisher(root / '\ua616/KB/Note.md', '# Note\n').publish()['status'])
			self.assertEqual(final['sha256'], Saver(root, val, expected_sha256=final['sha256']).save()['sha256'])
	# @used-by :mod:`unittest`
	def test_claim_arithmetic_and_grounding_classes(self) -> None:
		from Df.Harness.Analysis.Claim.CalculationContract import CalculationContract
		from Df.Harness.Analysis.Claim.ComparisonContract import ComparisonContract
		from Df.Harness.Analysis.Claim.InlineCalcVerifier import InlineCalcVerifier
		from Df.Harness.Analysis.Claim.QuantityMatcher import QuantityMatcher
		from Df.Harness.Analysis.Claim.SafeArithmetic import SafeArithmetic
		from Df.Harness.Analysis.Claim.SourceNumericTokenizer import SourceNumericTokenizer
		from Df.Harness.Analysis.Claim.StandaloneNumberExtractor import StandaloneNumberExtractor
		val_dec, toks = SafeArithmetic('100 + 20 * 2').evaluate()
		self.assertEqual(Decimal('140'), val_dec)
		self.assertEqual({'100', '20', '2'}, toks)
		ver_nums, calc_errs = InlineCalcVerifier('100 + 20 = 120', {'100', '20'}).extract()
		self.assertIn('120', ver_nums)
		self.assertEqual([], calc_errs)
		self.assertIn('1000', SourceNumericTokenizer('1,000 USD').tokenize())
		self.assertEqual({'42'}, StandaloneNumberExtractor('Found 42 items.').extract())
		self.assertTrue(QuantityMatcher({'quote': '100 USD', 'locator': {'type': 'text', 'value': '100 USD'}}, '100', 'USD', 'Price 100 USD').matches())
		self.assertTrue(CalculationContract({'operation': 'bad'}, '/calc', {'id': 'F-1'}).issues())
		self.assertTrue(ComparisonContract({'relation': 'bad'}, '/comp', {'id': 'F-1'}, []).issues())
	# @used-by :mod:`unittest`
	def test_claim_graph_and_validators(self) -> None:
		from Df.Harness.Analysis.Claim.CalculationValidator import CalculationValidator
		from Df.Harness.Analysis.Claim.ClosureCollector import ClosureCollector
		from Df.Harness.Analysis.Claim.ComparisonValidator import ComparisonValidator
		from Df.Harness.Analysis.Claim.CounterevidenceAuditor import CounterevidenceAuditor
		from Df.Harness.Analysis.Claim.ManifestPrimaryVerifier import ManifestPrimaryVerifier
		from Df.Harness.Analysis.Claim.NumericGrounding import NumericGrounding
		from Df.Harness.Analysis.Claim.PrimaryCapabilities import PrimaryCapabilities
		from Df.Harness.Analysis.Claim.ScopeCoverageAuditor import ScopeCoverageAuditor
		from Df.Harness.Analysis.Claim.StructureAuditor import StructureAuditor
		from Df.Harness.Analysis.ClaimGraph import ClaimGraph
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			_, _, c_id, c_con = _seed_v3_project(root)
			val = {'schema_version': 3, 'facts': [c_id], 'identity': [c_con], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': [], 'notes': {k: 'None.' for k in ('concerns', 'misconceptions', 'causes', 'methods')}}
			cg = ClaimGraph(val, root=root)
			self.assertEqual([], cg.structural_issues())
			self.assertEqual([], cg.evidence_issues(skip_structural=True))
			self.assertEqual(['F-TITLE'], ClosureCollector(['F-TITLE'], cg.index).collect())
			self.assertIn('100', NumericGrounding(c_con, cg.index).grounded_numbers())
			self.assertEqual({'client_report', 'content'}, ManifestPrimaryVerifier(root, c_id['evidence'][0]).verify())
			caps, _ = PrimaryCapabilities(root, c_id['evidence'][0]).resolve()
			self.assertIn('content', caps)
			with self.assertRaises(ValueError):
				CalculationValidator({'id': 'C-1', 'calculation': {'operation': 'bad'}}, cg.index, {}).check()
			with self.assertRaises(ValueError):
				ComparisonValidator({'id': 'C-1', 'comparison': {'relation': 'bad'}}, cg.index, {}).check()
			out_issues: list = []
			StructureAuditor(val, cg.locations, out_issues).check()
			CounterevidenceAuditor(out_issues, {}).check('/causes/0', 'causes', {'id': 'H-1', 'knowledge_type': 'hypothesis', 'verification_status': 'unverified', 'probability_percent': 80, 'against': [], 'alternative_explanations': ['Alt']})
			ScopeCoverageAuditor(out_issues).check('/facts/0', {'id': 'F-1', 'essence': 'demo post', 'scope': {'sample': ['https://ex.test/p1']}}, {'https://ex.test/sitemap.xml'})
			self.assertGreaterEqual(len(out_issues), 2)
	# @used-by :mod:`unittest`
	def test_diagnostics_and_label_classes(self) -> None:
		from Df.Harness.Project.Diagnostics import Diagnostics
		from Df.Harness.Project.DomainNormalizer import DomainNormalizer
		from Df.Harness.Project.InitLabelResolver import InitLabelResolver
		from Df.Harness.Project.IssueValidator import IssueValidator
		from Df.Harness.Project.LabelError import LabelError
		from Df.Harness.Project.LabelStateUpdater import LabelStateUpdater
		from Df.Harness.Project.LabelValidator import LabelValidator
		from Df.Harness.Project.ValidationError import ValidationError
		prob = Diagnostics().problem('claim.required', '/f', 'missing', hint=None)
		self.assertIn('hint', prob)
		with self.assertRaises(ValidationError):
			IssueValidator([prob]).require_valid()
		self.assertTrue(LabelValidator.is_valid_domain('example.com'))
		self.assertEqual('example.com', DomainNormalizer('https://www.example.com/path').normalize())
		self.assertTrue(LabelValidator.is_kebab('my-kebab-slug'))
		self.assertEqual('example.com', LabelValidator('example.com').validate(kind='domain'))
		self.assertEqual(('example.com', 'domain', None), InitLabelResolver(domain='example.com').resolve())
		with self.assertRaises(LabelError):
			LabelValidator('my-kebab-slug').validate(kind='topic')
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve() / '1 - example.com'
			root.mkdir()
			st: dict = {}
			LabelStateUpdater(st, root, root / '\ua616/KB/Evidence/snap.json', '2026-11-26', 'domain').update()
			self.assertEqual('domain', st['label_kind'])
	# @used-by :mod:`unittest`
	def test_drift_red_flags_and_card_sync_classes(self) -> None:
		from Df.Harness.Analysis.RedFlagRenderer import RedFlagRenderer
		from Df.Harness.Analysis.RedFlagSyncer import RedFlagSyncer
		from Df.Harness.Analysis.RedFlagValidator import RedFlagValidator
		from Df.Harness.Project.CardSyncAuditor import CardSyncAuditor
		from Df.Harness.Project.CardSyncer import CardSyncer
		from Df.Harness.Project.DriftAuditor import DriftAuditor
		from Df.Harness.Project.FinalizeDriftGuard import FinalizeDriftGuard
		from Df.Harness.Project.LinkAudit import LinkAudit
		from Df.Harness.Project.StageValidityGuard import StageValidityGuard
		from agent_tools.path_registry import project_paths
		self.assertEqual([], LinkAudit(SCRIPTS).audit())
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve() / '1 - provisional'
			root.mkdir()
			_, _, c_id, _ = _seed_v3_project(root)
			c_id['essence'] = 'Target site is https://shop.example.org'
			rf = [{'id': 'RF-CLIENT-INTERMEDIARY', 'status': 'suspected', 'summary': 'Agency post.', 'basis_ids': ['F-TITLE']}]
			val = {'schema_version': 3, 'facts': [], 'identity': [c_id], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': [], 'notes': {k: 'None.' for k in ('concerns', 'misconceptions', 'causes', 'methods')}, 'websites': [{'role': 'target', 'url': 'https://shop.example.org', 'basis_id': 'F-TITLE'}], 'red_flags': rf}
			self.assertEqual([], RedFlagValidator(val, {'F-TITLE': 'identity'}).issues())
			self.assertIn('Red Flags', RedFlagRenderer(val).render())
			self.assertEqual('published', RedFlagSyncer(root, val).sync()['status'])
			self.assertEqual('published', CardSyncer(root, root / '.md', 'demo', '## Demo\nBody\n').sync()['status'])
			self.assertEqual(['project.domain_drift'], [i['code'] for i in DriftAuditor(root, val).audit()])
			self.assertTrue(CardSyncAuditor(project_paths(root, exact_root=True), val).audit())
			(root / '\ua616/KB/Analysis.json').write_text(json.dumps(val), encoding='utf-8')
			with self.assertRaises(ValueError):
				FinalizeDriftGuard(root).require()
			with self.assertRaises(ValueError):
				StageValidityGuard(root, lambda _: {'valid': False, 'issues': [{'message': 'broken'}]}, 'Stage failed').require()
	# @used-by :mod:`unittest`
	def test_evidence_and_observation_classes(self) -> None:
		from Df.Harness.Analysis.CardValidationLoader import CardValidationLoader
		from Df.Harness.Analysis.EvidenceAuditor import EvidenceAuditor
		from Df.Harness.Analysis.HtmlQuoteVerifier import HtmlQuoteVerifier
		from Df.Harness.Analysis.JsonPointer import JsonPointer
		from Df.Harness.Analysis.LocalSourceResolver import LocalSourceResolver
		from Df.Harness.Analysis.ObservationBundleLoader import ObservationBundleLoader
		from Df.Harness.Analysis.ObservationContentLoader import ObservationContentLoader
		from Df.Harness.Analysis.ObservationHtmlResolver import ObservationHtmlResolver
		from Df.Harness.Analysis.ObservationProber import ObservationProber
		from Df.Harness.Analysis.ObservationResolver import ObservationResolver
		from Df.Harness.Analysis.SavedQuoteVerifier import SavedQuoteVerifier
		from Df.Harness.Analysis.SavedSourceLoader import SavedSourceLoader
		self.assertEqual('/a~1b/c~0d', JsonPointer.render_pointer('a/b', 'c~d'))
		self.assertEqual('ok', JsonPointer({'a/b': {'c~d': 'ok'}}, '/a~1b/c~0d').resolve())
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			obs_json, meta = _seed_http_obs(root)
			obs_ref, loaded = ObservationResolver(root, 'https://example.com/doc').resolve()
			self.assertEqual(meta['observation'], obs_ref)
			self.assertEqual(obs_json, LocalSourceResolver(root, obs_ref).resolve())
			self.assertIn('sec1', ObservationHtmlResolver(obs_json.parent, None, loaded, need_sections=True).resolve()['anchors'])
			self.assertEqual('html', ObservationContentLoader(root, obs_ref, loaded, fragment='sec1').load()['kind'])
			self.assertEqual('http-ok', ObservationProber(root, loaded, 'https://example.com/doc', 'sec1').probe())
			self.assertTrue(ObservationBundleLoader(obs_json, loaded, max_bytes=1024 * 1024).load()['valid'])
			saved = SavedSourceLoader(root, 'https://example.com/doc#sec1').load()
			self.assertIn('Verified phrase 42', HtmlQuoteVerifier(saved, 'Verified phrase 42').verify())
			self.assertEqual('html', SavedQuoteVerifier(root, 'https://example.com/doc#sec1', 'Verified phrase 42').verify()['kind'])
			self.assertEqual([], EvidenceAuditor(root, {'schema_version': 2, 'identity': [], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': []}).issues())
			(root / 'a.json').write_text('{}', encoding='utf-8')
			self.assertEqual(({}, [], []), CardValidationLoader(root, root / 'a.json', None, analysis_issues_fn=lambda _: [], evidence_issues_fn=lambda _r, _v: []).load())
	# @used-by :mod:`unittest`
	def test_registration_classes(self) -> None:
		from Df.Harness.Project.RegistrationAttemptStarter import RegistrationAttemptStarter
		from Df.Harness.Project.RegistrationConflict import RegistrationConflict
		from Df.Harness.Project.RegistrationExpectation import RegistrationExpectation
		from Df.Harness.Project.RegistrationStore import RegistrationStore
		from Df.Harness.Project.RegistrationValidator import RegistrationValidator
		from Df.Harness.Project.Registry import Registry
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve() / '1 - example.com'
			root.mkdir()
			(root / '\ua616').mkdir()
			(root / '\ua616/project.json').write_text(json.dumps({'request_date': '2026-11-26'}), encoding='utf-8')
			_, _, _, exp = RegistrationExpectation(root, 'example.com', '2026-11-26').build()
			self.assertEqual('attempting', RegistrationAttemptStarter(root, 'antigravity', exp).begin()['status'])
			valid_res = RegistrationValidator(root, 'example.com', '2026-11-26', 'antigravity', {**exp, 'project_id': 'p1', 'folder_id': 'f1'}).validate()
			self.assertTrue(valid_res['complete'])
			self.assertEqual('registered', RegistrationStore(root, 'antigravity', valid_res).save()['status'])
			with self.assertRaises(RegistrationConflict):
				RegistrationValidator(root, 'example.com', '2026-11-26', 'antigravity', {'project_name': 'wrong'}).validate()
			fake_cfg = {'platforms': {'antigravity': {'enabled': True}}, 'registration': {'targets': ['antigravity']}}
			reg_out = Registry(root, 'example.com', '2026-11-26', settings_fn=lambda: fake_cfg).register(platform='antigravity', targets=['antigravity'], registrars={'antigravity': lambda r, l, d: {**exp, 'project_id': 'p1', 'folder_id': 'f1'}})
			self.assertTrue(reg_out['complete'])
	# @used-by :mod:`unittest`
	def test_schema_help_classes(self) -> None:
		from Df.Harness.Analysis.AssertionValidator import AssertionValidator
		from Df.Harness.Analysis.ClaimHintResolver import ClaimHintResolver
		from Df.Harness.Analysis.IssueHintAnnotator import IssueHintAnnotator
		from Df.Harness.Analysis.SchemaHelp import SchemaHelp
		from Df.Harness.Analysis.SchemaHelpFormatter import SchemaHelpFormatter
		payload = SchemaHelp('analysis').payload()
		self.assertEqual(3, payload['schema_version'])
		self.assertIn('Schema Help: analysis', SchemaHelpFormatter(payload).render_text())
		self.assertIn('schema-help analysis', ClaimHintResolver('claim.required').resolve() or '')
		self.assertTrue(IssueHintAnnotator('review', ['err']).annotate()[0].endswith(')'))
		self.assertTrue(IssueHintAnnotator('experiment', ['err']).annotate()[0].endswith(')'))
		self.assertTrue(AssertionValidator('R-1', {'assertions': [{'id': ''}]}, ('equals',)).issues())
	# @used-by :mod:`unittest`
	def test_z_claim_calc_and_comparison_paths(self) -> None:
		from Df.Harness.Analysis.Claim.CalculationContract import CalculationContract
		from Df.Harness.Analysis.Claim.CalculationValidator import CalculationValidator
		from Df.Harness.Analysis.Claim.ComparisonContract import ComparisonContract
		from Df.Harness.Analysis.Claim.ComparisonValidator import ComparisonValidator
		from Df.Harness.Analysis.Claim.CounterevidenceAuditor import CounterevidenceAuditor
		from Df.Harness.Analysis.Claim.QuantityMatcher import QuantityMatcher
		from Df.Harness.Analysis.Claim.SafeArithmetic import SafeArithmetic
		from Df.Harness.Analysis.Claim.StructureAuditor import StructureAuditor
		from Df.Harness.Analysis.ClaimGraph import ClaimGraph
		val_div, _ = SafeArithmetic('round(100 / 3, 2)').evaluate()
		self.assertEqual(Decimal('33.33'), val_div)
		self.assertTrue(QuantityMatcher({'quote': '100', 'locator': {'type': 'json_pointer', 'value': '/price_a/amount'}}, '100', 'USD', json.dumps({'amount': '100', 'currency': 'USD'})).matches())
		ev_a = {'id': 'E-A', 'source': 'Evidence/s.json', 'source_sha256': 'a' * 64, 'quote': '100 USD', 'locator': {'type': 'text', 'value': '100 USD'}}
		ev_b = {'id': 'E-B', 'source': 'Evidence/s.json', 'source_sha256': 'b' * 64, 'quote': '120 USD', 'locator': {'type': 'text', 'value': '120 USD'}}
		c_a, c_b = ({'id': 'F-A', 'evidence': [ev_a]}, {'id': 'F-B', 'evidence': [ev_b]})
		refs = {'E-A': (c_a, ev_a, {'quantity_context': '100 USD'}), 'E-B': (c_b, ev_b, {'quantity_context': '120 USD'})}
		calc = {'operation': 'percent_change', 'formula': '(new - old) / old * 100', 'rounding': 'ROUND_HALF_UP', 'operands': {'old': {'claim_id': 'F-A', 'evidence_id': 'E-A', 'value': '100', 'unit': 'USD'}, 'new': {'claim_id': 'F-B', 'evidence_id': 'E-B', 'value': '120', 'unit': 'USD'}}, 'result': '20.00', 'result_unit': 'percent', 'rounding_places': 2}
		c_calc = {'id': 'C-1', 'derived_from': [{'claim_id': 'F-A'}, {'claim_id': 'F-B'}], 'calculation': calc}
		self.assertEqual([], CalculationContract(calc, '/calc', c_calc).issues())
		CalculationValidator(c_calc, {'F-A': c_a, 'F-B': c_b}, refs).check()
		comp = {'relation': 'differs', 'operand_a_evidence_id': 'E-A', 'operand_b_evidence_id': 'E-B'}
		c_comp = {'id': 'C-2', 'derived_from': [{'claim_id': 'F-A'}, {'claim_id': 'F-B'}], 'evidence': [], 'comparison': comp}
		self.assertEqual([], ComparisonContract(comp, '/comp', c_comp, []).issues())
		ComparisonValidator(c_comp, {'F-A': c_a, 'F-B': c_b}, refs).check()
		issues: list = []
		StructureAuditor({'facts': [{'id': 'F-1'}, {'id': 'F-1'}]}, [('/facts/0', 'facts', {'id': 'F-1'}), ('/facts/1', 'facts', {'id': 'F-1'})], issues).check()
		CounterevidenceAuditor(issues, {'Evidence/s.json': {'kind': 'intake'}}).check('/causes/0', 'causes', {'id': 'H-1', 'knowledge_type': 'hypothesis', 'verification_status': 'unverified', 'probability_percent': 80, 'for': [{'evidence_id': 'E-A'}], 'against': [{'evidence_id': 'E-A'}]})
		CounterevidenceAuditor(issues, {'Evidence/s.json': {'kind': 'intake'}}).check('/causes/1', 'causes', {'id': 'H-2', 'knowledge_type': 'hypothesis', 'verification_status': 'unverified', 'probability_percent': 80, 'for': [], 'against': [], 'counterevidence': {'status': 'not_found', 'reviewed_sources': ['Evidence/s.json'], 'limitations': 'Intake.'}})
		self.assertTrue(issues)
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			_, meta = _seed_http_obs(root)
			ev_dns = {'id': 'E-H', 'kind': 'http', 'source': 'https://example.com/doc', 'manifest': meta['observation'], 'source_sha256': meta['body_sha256'], 'quote': 'Verified phrase 42.', 'locator': {'type': 'text', 'value': 'Verified phrase 42.'}}
			cg = ClaimGraph({'schema_version': 3, 'facts': [{'id': 'F-DNS', 'essence': 'DNS ok', 'knowledge_type': 'observation', 'verification_status': 'verified', 'properties': ['dns'], 'evidence': [ev_dns], 'scope': {'description': 'S', 'sample': ['https://example.com/doc'], 'limitations': []}, 'derived_from': [], 'missing_checks': [], 'materiality': 'routine', 'novelty': 'new', 'category': 'descriptive', 'impact': {'severity': 'unknown', 'basis': 'B', 'evidence_claim_ids': []}}], 'identity': [], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': []}, root=root)
			self.assertTrue(cg.evidence_issues(skip_structural=True))
	# @used-by :mod:`unittest`
	def test_z_evidence_manifest_and_loader_paths(self) -> None:
		from Df.Harness.Analysis.Claim.ManifestPrimaryVerifier import ManifestPrimaryVerifier
		from Df.Harness.Analysis.Claim.PrimaryCapabilities import PrimaryCapabilities
		from Df.Harness.Analysis.HtmlQuoteVerifier import HtmlQuoteVerifier
		from Df.Harness.Analysis.JsonPointer import JsonPointer
		from Df.Harness.Analysis.ObservationBundleLoader import ObservationBundleLoader
		from Df.Harness.Analysis.ObservationHtmlResolver import ObservationHtmlResolver
		from Df.Harness.Analysis.SavedSourceLoader import SavedSourceLoader
		from agent_tools.research import extractor_version
		self.assertEqual('/a~1b', JsonPointer.render_pointer('a/b'))
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			ref, sha, _, _ = _seed_v3_project(root)
			cap = (root.parent / '01wave2a-20261126').resolve()
			rcpt_dir = root / '\ua616/KB/Evidence/Intake'
			rcpt_dir.mkdir(parents=True, exist_ok=True)
			raw_b = (root / '\ua616/KB' / ref).read_bytes()
			snap_obj = {'file': f'\ua616/KB/{ref}', 'sha256': sha, 'transform': 'Drop transport saved_attachments/cookies; add verified project asset_evidence.'}
			rcpt = {'version': 1, 'capture_id': cap.name, 'job_id': '~01wave2a', 'status': 'drained', 'original_directory_provenance': str(cap), 'original_paths_are_provenance_only': True, 'snapshot': snap_obj, 'entries': [{'original_relative_provenance': 'source.json', 'sha256': sha, 'bytes': len(raw_b), 'durable_file': f'\ua616/KB/{ref}', 'transform': 'identity'}]}
			(rcpt_dir / f'{cap.name}.json').write_text(json.dumps(rcpt), encoding='utf-8')
			self.assertEqual({'client_report', 'content'}, ManifestPrimaryVerifier(root, {'kind': 'intake', 'source': ref, 'manifest': f'Evidence/Intake/{cap.name}.json', 'source_sha256': sha}).verify())
			(root / '\ua616/KB/Evidence/x.json').write_text('{}', encoding='utf-8')
			with self.assertRaises(ValueError):
				PrimaryCapabilities(root, {'kind': 'experiment', 'experiment': 'Evidence/x.json', 'source': 'Evidence/x.json', 'manifest': 'Evidence/x.json', 'source_sha256': '0' * 64, 'quote': 'x'}).resolve()
			obs_json, meta = _seed_http_obs(root)
			(obs_json.parent / 'extracted-1.json').write_text(json.dumps({'extractor_version': extractor_version(), 'word_count': 5, 'title': '', 'headings': [{'level': 1, 'text': 'Doc H1'}], 'anchors': ['user-content-sec1'], 'text': 'Verified phrase 42.'}), encoding='utf-8')
			self.assertTrue(ObservationBundleLoader(obs_json, meta, max_bytes=1024 * 1024).load()['valid'])
			self.assertIn('sec1', ObservationHtmlResolver(obs_json.parent, None, meta, need_sections=True).resolve()['anchors'])
			md_dir = root / '\ua616/KB/Evidence/HTTP/obs_md'
			md_dir.mkdir(parents=True, exist_ok=True)
			(md_dir / 'response.bin').write_bytes(b'# MD Title\nBody text.\n')
			md_meta = {'url': 'https://example.com/a.md', 'status': 200, 'kind': 'http', 'content_type': 'text/markdown', 'charset': 'utf-8'}
			self.assertTrue(ObservationBundleLoader(md_dir / 'observation.json', md_meta, max_bytes=1024 * 1024).load()['valid'])
			(root / '\ua616/KB/Doc.md').write_text('# Sec1\nBody line.\n', encoding='utf-8')
			(root / '\ua616/KB/Note.txt').write_text('Plain note.\n', encoding='utf-8')
			self.assertEqual('text', SavedSourceLoader(root, 'Doc.md#sec1').load()['kind'])
			self.assertEqual('text', SavedSourceLoader(root, 'Note.txt').load()['kind'])
			saved_nf = SavedSourceLoader(root, 'https://example.com/doc').load()
			self.assertIn('Plain section text', HtmlQuoteVerifier(saved_nf, 'Plain section text.', documentation=True, exception={'section': 'NoAnchor'}).verify())
			self.assertIn('Verified phrase 42', HtmlQuoteVerifier(saved_nf, 'Verified phrase 42.').verify())
	# @used-by :mod:`unittest`
	def test_z_project_sync_and_schema_paths(self) -> None:
		from Df.Harness.Analysis.RedFlagSyncer import RedFlagSyncer
		from Df.Harness.Analysis.SchemaHelp import SchemaHelp
		from Df.Harness.Analysis.SchemaHelpFormatter import SchemaHelpFormatter
		from Df.Harness.Analysis.Validator import Validator
		from Df.Harness.Project.CardSyncer import CardSyncer
		from Df.Harness.Project.RegistrationConflict import RegistrationConflict
		from Df.Harness.Project.RegistrationExpectation import RegistrationExpectation
		from Df.Harness.Project.RegistrationStore import RegistrationStore
		from Df.Harness.Project.RegistrationValidator import RegistrationValidator
		self.assertEqual('experiment', SchemaHelp('experiment').payload()['topic'])
		self.assertEqual('review', SchemaHelp('review').payload()['topic'])
		self.assertIn('Schema Help: analysis', SchemaHelpFormatter(SchemaHelp('analysis').payload()).render_text())
		v2 = {'schema_version': 2, 'sources': {'S1': 'https://example.com#sec1'}, 'identity': [{'id': 'H-1', 'essence': 'E', 'assessment_basis': 'B', 'probability_percent': 50, 'for': [{'argument': 'A', 'quote': 'Q', 'source_id': 'S1'}], 'against': [{'argument': 'B', 'quote': 'R', 'source': 'https://example.com#sec2'}]}], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': []}
		self.assertIsInstance(Validator(v2).issues(), list)
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve() / '1 - example.com'
			root.mkdir()
			_, _, c_id, _ = _seed_v3_project(root)
			rf = [{'id': 'RF-CLIENT-INTERMEDIARY', 'status': 'suspected', 'summary': 'Agency post.', 'basis_ids': ['F-TITLE']}]
			val = {'schema_version': 3, 'facts': [], 'identity': [c_id], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': [], 'notes': {k: 'None.' for k in ('concerns', 'misconceptions', 'causes', 'methods')}, 'websites': [{'role': 'client', 'url': None, 'basis_id': 'F-TITLE'}], 'red_flags': rf}
			self.assertEqual('published', RedFlagSyncer(root, val).sync()['status'])
			self.assertEqual('unchanged', RedFlagSyncer(root, val).sync()['status'])
			card = root / '.md'
			self.assertEqual('published', CardSyncer(root, card, 'demo', '## Demo\nV1\n').sync()['status'])
			self.assertEqual('published', CardSyncer(root, card, 'demo', '## Demo\nV2\n').sync()['status'])
			card.write_text(card.read_text(encoding='utf-8').replace('V2', 'ManualEdit'), encoding='utf-8')
			self.assertEqual('conflict', CardSyncer(root, card, 'demo', '## Demo\nV3\n').sync()['status'])
			_, _, _, exp = RegistrationExpectation(root, 'example.com', '2026-11-26').build()
			with self.assertRaises(RegistrationConflict):
				RegistrationValidator(root, 'example.com', '2026-11-26', 'antigravity', {**exp, 'project_name': 'wrong', 'project_id': 'p1', 'folder_id': 'f1'}).validate()
			RegistrationStore(root, 'antigravity', {**exp, 'project_id': 'p1', 'folder_id': 'f1'}).save()
			failed = RegistrationStore(root, 'antigravity', {'complete': False, 'status': 'failed'}).save()
			self.assertIn('last_success', failed)
	# @used-by :mod:`unittest`
	def test_z_remaining_edge_paths(self) -> None:
		from Df.Harness.Analysis.Claim.ComparisonContract import ComparisonContract
		from Df.Harness.Analysis.Claim.CounterevidenceAuditor import CounterevidenceAuditor
		from Df.Harness.Analysis.ClaimGraph import ClaimGraph
		from Df.Harness.Analysis.ObservationHtmlResolver import ObservationHtmlResolver
		from Df.Harness.Analysis.SavedSourceLoader import SavedSourceLoader
		from Df.Harness.Project.RegistrationConflict import RegistrationConflict
		from agent_tools.research import extractor_version
		self.assertTrue(ComparisonContract({'relation': 'differs', 'operand_a_evidence_id': 'E-1', 'operand_b_evidence_id': 'E-2'}, '/comp', {'id': 'C-1', 'derived_from': []}, [{'id': 'E-1'}]).issues())
		h1 = {'id': 'H-1', 'knowledge_type': 'hypothesis', 'verification_status': 'unverified', 'probability_percent': 80, 'for': [{'evidence_id': 'E-A'}], 'against': [{'evidence_id': 'E-A'}]}
		issues: list = []
		CounterevidenceAuditor(issues, {'H-1': ('/causes/0', 'causes', h1)}).check('/causes/0', 'causes', h1)
		self.assertTrue(issues)
		err = RegistrationConflict('conflict', expected={'a': 1}, actual={'a': 2}, issues=['mismatch'])
		self.assertEqual(['mismatch'], err.issues)
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			obs_json, meta = _seed_http_obs(root)
			(obs_json.parent / 'extracted-html.json').write_text(json.dumps({'body_sha256': meta['body_sha256'], 'extractor_version': extractor_version(), 'anchors': ['sec1'], 'browser_check_required': False, 'text': 'Verified', 'anchor_content': {}, 'sections': [{'content': 'Verified'}]}), encoding='utf-8')
			self.assertIn('sec1', ObservationHtmlResolver(obs_json.parent, None, meta, need_sections=True).resolve()['anchors'])
			(root / '\ua616/KB/Sample.rtf').write_text('{\\rtf1 Hello world.}', encoding='utf-8')
			self.assertIn('Hello world', SavedSourceLoader(root, 'Sample.rtf').load()['text'])
			cg = ClaimGraph({'schema_version': 3, 'facts': [{'id': 'F-DNS', 'essence': 'DNS NXDOMAIN error', 'assessment_basis': 'Check', 'knowledge_type': 'hypothesis', 'verification_status': 'unverified', 'properties': ['dns'], 'evidence': [], 'scope': {'description': 'S', 'sample': [], 'limitations': []}, 'derived_from': [], 'missing_checks': [], 'materiality': 'routine', 'novelty': 'new', 'category': 'descriptive', 'impact': {'severity': 'unknown', 'basis': 'B', 'evidence_claim_ids': []}}], 'identity': [], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': []}, root=root)
			self.assertTrue(cg.evidence_issues(skip_structural=True))
if '__main__' == __name__:
	unittest.main()