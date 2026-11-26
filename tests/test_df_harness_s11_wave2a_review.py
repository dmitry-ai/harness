# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
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
# @used-by :meth:`DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
# @used-by :meth:`DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
def _sample_requirement(req_id: str='EXP-1', method: str='http', prop: str='markup') -> dict:
	return {
		'id': req_id,
		'claim': 'Product markup includes Offer price.',
		'property': prop,
		'method': method,
		'scope': {'objects': ['https://example.com/p1']},
		'conditions': {'session': {'mode': 'unknown'}},
		'expected': 'Offer appears in HTML.',
		'falsification': 'Offer is absent.',
		'discriminating_test': 'Check response text.',
		'completion_criterion': 'HTTP observation inspected.',
		'alternatives': ['Client-side JS renders Offer.'],
		'assertions': [{'id': 'A-1', 'artifact_id': 'page_html', 'locator': {'type': 'text', 'value': 'Offer'}, 'operator': 'contains', 'expected': 'Offer', 'disconfirming': {'operator': 'equals', 'expected': ''}}],
	}
# @used-by :meth:`DfHarnessS11Wave2aReviewTests.test_review_merkle_and_predicates()`
# @used-by :meth:`DfHarnessS11Wave2aReviewTests.test_review_package_and_recording_classes()`
# @used-by :meth:`DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
def _sample_package(root: Path, *, risk: str='significant', review_mode: str='falsifier') -> tuple[str, str, dict]:
	cand_dir = root / '\ua616/KB/Evidence/Reviews/Candidates'
	cand_dir.mkdir(parents=True, exist_ok=True)
	resp_b = b'Verified finding 42.'
	resp_sha = hashlib.sha256(resp_b).hexdigest()
	(cand_dir / f'{resp_sha}.txt').write_bytes(resp_b)
	pkg = {
		'schema_version': 2,
		'project_root': str(root),
		'job_id': '~01rev',
		'parent_id': 'parent-1',
		'risk': risk,
		'review_mode': review_mode,
		'risk_basis': 'Significant analysis.',
		'risk_reasons': ['C-1'],
		'request_scope': 'Initial analysis.',
		'task_flags': ['material_analysis'],
		'requests': [{'id': '1', 'text': 'Check site'}],
		'response': {'file': f'\ua616/KB/Evidence/Reviews/Candidates/{resp_sha}.txt', 'sha256': resp_sha, 'bytes': len(resp_b)},
		'kb_inputs': {},
		'evidence_inputs': {'Evidence/a.json': 'a' * 64},
		'scope': ['identity', 'concerns', 'misconceptions', 'causes', 'methods', 'kb_consistency', 'response'],
		'claims': [{'claim_id': 'C-1', 'claim_sha256': 'b' * 64, 'response_excerpt': 'Verified finding 42.', 'novelty': 'new', 'materiality': 'significant', 'category': 'descriptive', 'properties': ['content'], 'knowledge_type': 'observation', 'verification_status': 'verified', 'essence': 'Verified finding 42.'}],
	}
	from agent_tools.research import json_data
	sub_payload = json_data({k: pkg[k] for k in ('project_root', 'job_id', 'requests', 'response', 'kb_inputs', 'evidence_inputs')})
	pkg['subject_sha256'] = hashlib.sha256(sub_payload).hexdigest()
	pkg_b = json_data(pkg)
	pkg_sha = hashlib.sha256(pkg_b).hexdigest()
	pkg_rel = f'\ua616/KB/Evidence/Reviews/{pkg_sha}-inputs.json'
	(root / pkg_rel).write_bytes(pkg_b)
	return (pkg_rel, pkg_sha, pkg)
# @used-by :mod:`unittest`
class DfHarnessS11Wave2aReviewTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_experiment_plan_and_run_classes(self) -> None:
		from Df.Harness.Experiment.PlanLoader import PlanLoader
		from Df.Harness.Experiment.PlanPreparer import PlanPreparer
		from Df.Harness.Experiment.PlanStore import PlanStore
		from Df.Harness.Experiment.PreregistrationAuditor import PreregistrationAuditor
		from Df.Harness.Experiment.RunLoader import RunLoader
		from Df.Harness.Experiment.RunRecorder import RunRecorder
		from Df.Harness.Experiment.RunValidator import RunValidator
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			req = _sample_requirement()
			prepared = PlanPreparer(root, req).prepare_plan()
			loaded = PlanLoader(root, prepared['plan']).load_plan()
			self.assertEqual('EXP-1', loaded['requirement']['id'])
			amended = PlanStore(root).prepare({**req, 'expected': 'Offer USD'}, amendment_of=prepared['plan'], amendment_reason='Clarified unit')
			self.assertEqual(2, amended['revision'])
			obs_dir = root / '\ua616/KB/Evidence/HTTP/o1'
			obs_dir.mkdir(parents=True, exist_ok=True)
			(obs_dir / 'response.bin').write_bytes(b'<html>Offer USD</html>')
			obs_meta = {'schema_version': 1, 'kind': 'http', 'method': 'GET', 'url': 'https://example.com/p1', 'status': 200, 'headers': {'content-type': 'text/html'}, 'observed_at': '2099-01-01T00:00:00+00:00', 'body_bytes': len(b'<html>Offer USD</html>'), 'body_sha256': hashlib.sha256(b'<html>Offer USD</html>').hexdigest()}
			(obs_dir / 'observation.json').write_text(json.dumps(obs_meta), encoding='utf-8')
			spec = {'plan': amended['plan'], 'plan_sha256': amended['plan_sha256'], 'status': 'verified', 'actual_result': 'Offer USD found.', 'actual_steps': ['Fetched HTML'], 'conditions': {'session': {'mode': 'unknown'}}, 'artifacts': [{'id': 'page_html', 'observation': 'Evidence/HTTP/o1/observation.json'}]}
			rec = RunRecorder(root, spec).record_run()
			self.assertEqual('verified', rec['status'])
			run = RunLoader(root, rec['experiment']).load_run()
			self.assertEqual('verified', run['status'])
			self.assertEqual([], PreregistrationAuditor(root, run).issues())
			self.assertEqual([], PlanStore(root).preregistration_issues(run))
			rv = RunValidator(root, run, {})
			self.assertIn('markup', rv.capabilities())
			self.assertEqual([], rv.run_issues())
			self.assertEqual('verified', RunValidator.load(root, rec['experiment'])['status'])
	# @used-by :mod:`unittest`
	def test_experiment_trace_inspector_classes(self) -> None:
		from Df.Harness.Experiment.BrowserIdentityExtractor import BrowserIdentityExtractor
		from Df.Harness.Experiment.CallChainParser import CallChainParser
		from Df.Harness.Experiment.NativeGeoExtractor import NativeGeoExtractor
		from Df.Harness.Experiment.TraceContextAuditor import TraceContextAuditor
		from Df.Harness.Experiment.TraceInspector import TraceInspector
		calls = CallChainParser("await page.getByRole('button', {name: 'USD'}).click();").parse_calls()
		self.assertEqual([('page', 'click')], calls)
		ev_read = {'id': 'e1', 'name': 'browser_get_state', 'successful': True, 'arguments': {'browser_id': 'b1', 'tab_id': 't1'}, 'result': {'browser_id': 'b1', 'tab_id': 't1', 'url': 'https://ipapi.co/json'}}
		self.assertEqual({'browser_id': 'b1', 'tab_id': 't1'}, BrowserIdentityExtractor(ev_read).extract_identity())
		self.assertTrue(NativeGeoExtractor.is_geo_url('https://ipapi.co/json'))
		self.assertEqual('DE', NativeGeoExtractor.extract_verified_country({'country_code': 'DE', 'ip': '1.2.3.4'}))
		ev_geo = {'id': 'e2', 'name': 'browser_navigate', 'successful': True, 'arguments': {'url': 'https://ipapi.co/json', 'browser_id': 'b1', 'tab_id': 't1'}, 'result': json.dumps({'country_code': 'DE', 'ip': '1.2.3.4', 'browser_id': 'b1', 'tab_id': 't1'})}
		self.assertEqual('DE', NativeGeoExtractor(ev_geo).extract_country())
		self.assertEqual({'click'}, TraceInspector.event_actions({'name': 'click_browser_element', 'successful': True, 'arguments': {}}))
		self.assertEqual([('page', 'click')], TraceInspector.unconditional_calls("await page.locator(['a', {k: 1}]).click();"))
		self.assertEqual('ns__click', TraceInspector.native_tool_name({'namespace': 'ns', 'name': 'click'}))
		self.assertTrue(TraceInspector.is_geo_url('https://ipapi.co/json'))
		self.assertEqual('DE', TraceInspector.extract_verified_country({'country_code': 'DE', 'ip': '1.2.3.4'}))
		self.assertEqual('DE', TraceInspector.native_geolocation(ev_geo))
		run_ctx = {'requirement': {'method': 'browser_scenario'}, 'actual_steps': [{'native_event_id': 'e1'}], 'conditions': {}}
		self.assertEqual([], TraceContextAuditor(run_ctx, {'e1': ev_read}, lambda _: []).issues())
		self.assertEqual([], TraceInspector.context_issues(run_ctx, {'e1': ev_read}, lambda _: []))
	# @used-by :mod:`unittest`
	def test_experiment_validators_and_evaluators(self) -> None:
		from Df.Harness.Experiment.ArtifactIngestor import ArtifactIngestor
		from Df.Harness.Experiment.ArtifactVerifier import ArtifactVerifier
		from Df.Harness.Experiment.AssertionEvaluator import AssertionEvaluator
		from Df.Harness.Experiment.BrowserStepAuditor import BrowserStepAuditor
		from Df.Harness.Experiment.CapabilityResolver import CapabilityResolver
		from Df.Harness.Experiment.ConditionAuditor import ConditionAuditor
		from Df.Harness.Experiment.RequirementValidator import RequirementValidator
		from Df.Harness.Experiment.ResultValidator import ResultValidator
		from Df.Harness.Experiment.RunAuditor import RunAuditor
		req = _sample_requirement()
		self.assertEqual([], RequirementValidator([req]).issues())
		self.assertTrue(RequirementValidator([{'id': ''}]).issues())
		run = {'schema_version': 1, 'kind': 'experiment', 'status': 'verified', 'requirement': req, 'actual_result': 'ok', 'actual_steps': [], 'conditions': {'session': {'mode': 'unknown'}}, 'artifacts': [{'id': 'page_html', 'sha256': 'a' * 64, 'observation_kind': 'http', 'source_observation': 'Evidence/HTTP/o1/observation.json', 'observation_capabilities': ['content', 'markup']}]}
		ev_out = AssertionEvaluator(run, {'page_html': b'Offer present'}, {}).evaluate()
		self.assertEqual('verified', ev_out['status'])
		self.assertIn('markup', CapabilityResolver(run).capabilities())
		self.assertEqual([], ConditionAuditor(run, {}, lambda _: []).issues())
		self.assertTrue(BrowserStepAuditor({**run, 'requirement': {**req, 'method': 'browser_scenario'}}, {}, {}, lambda _: []).issues())
		self.assertEqual([], RunAuditor(run, {'page_html': run['artifacts'][0]}, {}, lambda _: []).issues())
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			f = root / 'raw.txt'
			f.write_text('hello', encoding='utf-8')
			saved, contents = ArtifactIngestor(root, {}, [{'id': 'a1', 'path': 'raw.txt'}], None).ingest()
			self.assertEqual(b'hello', contents['a1'])
			self.assertTrue(ResultValidator(root, req, {'requirement_id': 'EXP-1', 'status': 'verified', 'experiment': 'Evidence/missing.json', 'experiment_sha256': '0' * 64}).issues())
			ArtifactVerifier(root, {'artifacts': [], 'native_trace': None}, {}, {}).verify(root / '\ua616/KB/Evidence/Experiments/x/experiment.json')
	# @used-by :mod:`unittest`
	def test_review_alignment_and_classifier_classes(self) -> None:
		from Df.Harness.Review.AlignmentValidator import AlignmentValidator
		from Df.Harness.Review.ClaimTargetBuilder import ClaimTargetBuilder
		from Df.Harness.Review.Classifier import Classifier
		from Df.Harness.Review.ContractBinder import ContractBinder
		from Df.Harness.Review.EnvelopeValidator import EnvelopeValidator
		from Df.Harness.Review.ReviewModeResolver import ReviewModeResolver
		self.assertEqual([], AlignmentValidator('C-1', {'target_claim': 'X', 'tested_claim': 'X', 'relationship': 'direct', 'rationale': 'Match', 'counterexample': 'None'}, 'X').issues())
		self.assertTrue(AlignmentValidator('C-1', {'target_claim': 'Y'}, 'X').issues())
		self.assertEqual({'C-1': 'X'}, ClaimTargetBuilder([{'claim_id': 'C-1', 'essence': 'X'}]).build())
		bound = ContractBinder({'falsifier_required_top_level_fields': ['result']}, 'pkg.json', 'a' * 64, 'falsifier').bind()
		self.assertEqual(['result'], bound['required_top_level_fields'])
		env_errs = EnvelopeValidator({'schema_version': 2, 'result': 'approved', 'scope': ['identity'], 'package': 'p', 'package_sha256': 'a'}, {'kind': 'client_text', 'scope': ['identity'], 'package_sha256': 'a'}, review_schema=2, scopes=('identity',), require_envelope=True).issues()
		self.assertEqual([], env_errs)
		self.assertTrue(Classifier.has_significant_flags([{'materiality': 'significant'}], []))
		class _FakeEval:
			# @used-by :meth:`DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
			def latest_for_subject(self, _p):
				return {}
			# @used-by :meth:`DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
			def significant_findings(self, _s):
				return False
		self.assertEqual('falsifier', ReviewModeResolver({}, {'risk': 'significant', 'subject_sha256': 's'}, _FakeEval()).resolve())
	# @used-by :mod:`unittest`
	def test_review_merkle_and_predicates(self) -> None:
		from Df.Harness.Review.BlindPredicateBuilder import BlindPredicateBuilder
		from Df.Harness.Review.ClaimEvidenceCollector import ClaimEvidenceCollector
		from Df.Harness.Review.ClaimMerkleHasher import ClaimMerkleHasher
		from Df.Harness.Review.MerkleCacheUpdater import MerkleCacheUpdater
		from Df.Harness.Review.MerkleDeltaCalculator import MerkleDeltaCalculator
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			(root / '\ua616/data').mkdir(parents=True, exist_ok=True)
			_, _, pkg = _sample_package(root)
			val = {'schema_version': 3, 'facts': [{'id': 'C-1', 'essence': 'Verified finding 42 (80%).', 'knowledge_type': 'observation', 'verification_status': 'verified', 'derived_from': [], 'evidence': [{'source': 'Evidence/a.json', 'source_sha256': 'a' * 64}]}], 'identity': [], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': []}
			idx = {'C-1': val['facts'][0]}
			self.assertEqual([('Evidence/a.json', 'a' * 64)], ClaimEvidenceCollector('C-1', idx, {'Evidence/a.json': 'a' * 64}).pairs())
			m_hash = ClaimMerkleHasher(pkg['claims'][0], idx, {'Evidence/a.json': 'a' * 64}).compute_hash()
			self.assertEqual(64, len(m_hash))
			delta1 = MerkleDeltaCalculator(root, pkg['claims'], val, {'Evidence/a.json': 'a' * 64}).compute()
			self.assertEqual(['C-1'], delta1['unverified_claim_ids'])
			MerkleCacheUpdater(root, pkg, val).update()
			delta2 = MerkleDeltaCalculator(root, pkg['claims'], val, {'Evidence/a.json': 'a' * 64}).compute()
			self.assertEqual(['C-1'], delta2['cached_claim_ids'])
			preds = BlindPredicateBuilder(pkg['claims'], val).build()
			self.assertEqual('C-1', preds[0]['claim_id'])
	# @used-by :mod:`unittest`
	def test_review_quorum_and_authorizer_classes(self) -> None:
		from Df.Harness.Review.AddressedReviewResolver import AddressedReviewResolver
		from Df.Harness.Review.ApprovalChecker import ApprovalChecker
		from Df.Harness.Review.ApprovedDigestCollector import ApprovedDigestCollector
		from Df.Harness.Review.AuthorizedGroupSelector import AuthorizedGroupSelector
		from Df.Harness.Review.FindingsClosureChecker import FindingsClosureChecker
		from Df.Harness.Review.QuorumChecker import QuorumChecker
		from Df.Harness.Review.QuorumEvaluator import QuorumEvaluator
		from Df.Harness.Review.ReportParser import ReportParser
		from Df.Harness.Review.SignificantFindingScanner import SignificantFindingScanner
		from Df.Harness.Review.UnhandledVerdictChecker import UnhandledVerdictChecker
		self.assertEqual({'ok': True}, ReportParser('```json\n{"ok": true}\n```').parse())
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			pkg_rel, pkg_sha, pkg = _sample_package(root)
			rep_rel = '\ua616/KB/Evidence/Reviews/r1.json'
			(root / rep_rel).write_text(json.dumps({'findings': []}), encoding='utf-8')
			entry = {'schema_version': 2, 'id': 'rev-1', 'reviewer_id': 'aa-1', 'result': 'approved', 'independent': True, 'review_mode': 'falsifier', 'package': pkg_rel, 'package_sha256': pkg_sha, 'subject_sha256': pkg['subject_sha256'], 'report': rep_rel, 'proof': {}, 'dispositions': []}
			state = {'reviews': [entry], 'stages': {}}
			ev = QuorumEvaluator(root, state)
			self.assertTrue(FindingsClosureChecker(root, ev, entry).closed())
			self.assertFalse(SignificantFindingScanner(root, state, ev, pkg['subject_sha256']).has_significant())
			self.assertFalse(UnhandledVerdictChecker(state, ev, pkg).has_unhandled())
			self.assertTrue(QuorumChecker(ev, pkg, {'aa-1': entry}, [entry]).satisfied())
			self.assertIsNotNone(AuthorizedGroupSelector(ev, {pkg_rel: (pkg, [entry])}).select())
			self.assertEqual([], AddressedReviewResolver(root, {}, pkg, True, []).resolve_addressed()[0])
			self.assertIsInstance(ApprovedDigestCollector(root, state, ev).digests(), set)
			self.assertFalse(ApprovalChecker(root, state, ev, {}).check())
	# @used-by :mod:`unittest`
	def test_review_report_validator_classes(self) -> None:
		from Df.Harness.Review.ClaimReviewValidator import ClaimReviewValidator
		from Df.Harness.Review.FalsifierValidator import FalsifierValidator
		from Df.Harness.Review.FindingValidator import FindingValidator
		from Df.Harness.Review.ReportValidator import ReportValidator
		scopes = ['identity', 'concerns', 'misconceptions', 'causes', 'methods', 'kb_consistency', 'response']
		pkg = {'schema_version': 2, 'risk': 'significant', 'scope': scopes, 'package_sha256': 'a' * 64, 'claims': [{'claim_id': 'C-1', 'essence': 'Site uses HTTPS.', 'response_excerpt': 'Site uses HTTPS.'}]}
		falsifier_rep = {'schema_version': 2, 'review_mode': 'falsifier', 'package': 'p.json', 'package_sha256': 'a' * 64, 'result': 'approved', 'scope': scopes, 'disproved_claims': [], 'findings': []}
		self.assertTrue(ReportValidator.is_falsifier_report(falsifier_rep))
		self.assertEqual([], ReportValidator(pkg, require_envelope=True).validate(falsifier_rep))
		std_rep = {'schema_version': 2, 'package': 'p.json', 'package_sha256': 'a' * 64, 'result': 'approved', 'scope': scopes, 'findings': [], 'claim_reviews': [{'claim_id': 'C-1', 'observed': 'HTTPS 200', 'inferred': 'None', 'method': 'HTTP', 'alternatives': 'None', 'limits': 'Single URL', 'falsification': 'HTTP error', 'raw_vs_criteria': 'Exact match', 'outcome': 'supported', 'test_alignment': {'target_claim': 'Site uses HTTPS.', 'tested_claim': 'Site uses HTTPS.', 'relationship': 'direct', 'rationale': 'Direct check', 'counterexample': 'Redirect to HTTP'}}]}
		self.assertEqual([], ReportValidator(pkg, candidate='Site uses HTTPS.', require_envelope=True).validate(std_rep))
		errs: list[str] = []
		FalsifierValidator(pkg, {'C-1'}, None).check({'result': 'needs_changes', 'disproved_claims': [], 'findings': []}, errs)
		FindingValidator(pkg, {'C-1'}).check({'result': 'approved', 'findings': [{'id': ''}]}, errs)
		ClaimReviewValidator(pkg, {'C-1'}, {'C-1': pkg['claims'][0]}, {'C-1': 'Site uses HTTPS.'}, None).check({'claim_reviews': []}, errs)
		self.assertGreaterEqual(len(errs), 3)
	# @used-by :mod:`unittest`
	def test_review_package_and_recording_classes(self) -> None:
		from Df.Harness.Review.DispositionRecorder import DispositionRecorder
		from Df.Harness.Review.InputReceiptBuilder import InputReceiptBuilder
		from Df.Harness.Review.NativeProofVerifier import NativeProofVerifier
		from Df.Harness.Review.PackageEnvelopeReader import PackageEnvelopeReader
		from Df.Harness.Review.PackagePreparer import PackagePreparer
		from Df.Harness.Review.PackageReader import PackageReader
		from Df.Harness.Review.ReportAuthenticator import ReportAuthenticator
		from Df.Harness.Review.ReviewAuthorizer import ReviewAuthorizer
		from Df.Harness.Review.VerdictPreparer import VerdictPreparer
		from Df.Harness.Review.VerdictRecorder import VerdictRecorder
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			pkg_rel, _, pkg = _sample_package(root)
			root_p, _, data, cand_b = PackageEnvelopeReader(root, pkg_rel).read_envelope()
			self.assertEqual(root, root_p)
			self.assertEqual(b'Verified finding 42.', cand_b)
			self.assertEqual('~01rev', data['job_id'])
			for cls_obj in (DispositionRecorder, InputReceiptBuilder, NativeProofVerifier, PackagePreparer, PackageReader, ReportAuthenticator, ReviewAuthorizer, VerdictPreparer, VerdictRecorder):
				self.assertTrue(callable(cls_obj))
if '__main__' == __name__:
	unittest.main()
