# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from copy import deepcopy
from contextlib import redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib
import json
import uuid
from test_analysis_workflow import ProjectCase
from agent_tools import workflow as flow, review
from agent_tools.research import json_data
class ReviewContractTests(ProjectCase):
	def setUp(self):
		super().setUp()
		self.value = self.valid_review_analysis()
		self.parent = str(uuid.uuid4())
		flow.resume(self.project, 'review contract fixture', 'Show the saved client title.')
		self.answer = 'Client task\n'
		self.manifest = [{'claim_id': 'F-TITLE', 'response_excerpt': 'Client task'}]
	def package(self, *, risk='routine', novelty='new'):
		manifest = [{**self.manifest[0], 'novelty': novelty}]
		r = self.review_package(self.parent, self.answer, risk, manifest)
		return r
	def self_record(self, package, *, result='approved', findings=None):
		report = self.review_report(package, self_review=True, result=result, findings=findings)
		with patch('agent_tools.platforms.adapter'):
			flow.record_review(self.project, json_data(report), parent_id=self.parent, reviewer_id=self.parent)
		r = report
		return r
	def native_record(self, package, reviewer=None, *, report=None, actual=None):
		reviewer = reviewer or str(uuid.uuid4())
		report = report or self.review_report(package)
		final = json.dumps(actual if None is not actual else report, ensure_ascii=False)
		native = {'surface': 'codex-ui', 'status': 'completed', 'parent_id': self.parent, 'reviewer_id': reviewer, 'final_response': final, 'final_response_sha256': hashlib.sha256(final.encode()).hexdigest()}
		path = self.put_project(f'ꘖ/KB/Evidence/Reviews/{reviewer}-{hashlib.sha256(final.encode()).hexdigest()[:16]}-native.json', json.dumps(native))
		with patch('agent_tools.metrics.verify_native_proof', return_value=native):
			flow.record_review(self.project, json_data(report), parent_id=self.parent, reviewer_id=reviewer, native_evidence=path.relative_to(self.project).as_posix())
		r = native
		return r
	def authorize(self, response=None):
		def verified(root, native, package=None):
			return native
		with patch('agent_tools.metrics.verify_native_proof', side_effect=verified):
			return review.authorize(self.project, flow.load(self.project), response=response or self.answer)
	def test_routine_fact_approves_and_exact_answer_is_recorded(self):
		package = self.package()
		self.self_record(package)
		result = flow.record_current_answer(self.project, self.answer)
		self.assertFalse(result['delivery_verified'])
		self.assertEqual((self.project / 'ꙮ/1 - Analysis/res/1.md').read_bytes(), self.answer.encode())
		self.assertEqual(flow.load(self.project)['requests'][-1]['response_prepared']['review_approval']['package'], package['package'])
	def test_answer_change_and_new_request_need_new_review_even_without_kb_change(self):
		package = self.package()
		self.self_record(package)
		before = flow.hashes(self.project, flow.kb_paths(self.project))
		with self.assertRaisesRegex(ValueError, 'answer-bound'):
			flow.record_current_answer(self.project, self.answer + 'New architecture recommendation.')
		flow.resume(self.project, 'new task', 'Now explain the cause.')
		self.assertEqual(before, flow.hashes(self.project, flow.kb_paths(self.project)))
		with self.assertRaisesRegex(ValueError, 'current requests'):
			self.authorize()
	def test_missing_risk_basis_or_manifest_is_rejected(self):
		with self.assertRaisesRegex(ValueError, 'Explicit'):
			flow.prepare_review(self.project, self.parent, None, self.answer)
		spec = {'risk': 'routine', 'basis': '', 'request_scope': 'Current task', 'claim_ids': [], 'claims': []}
		with self.assertRaisesRegex(ValueError, 'basis'):
			flow.prepare_review(self.project, self.parent, spec, self.answer)
	def test_causal_property_forces_significant_even_when_labeled_descriptive_routine(self):
		claim = self.value['identity'][0]
		claim.update(verification_status='limited', missing_checks=['Perform a discriminating experiment.'], properties=['content', 'causality'])
		self.put_project('ꘖ/KB/Analysis.json', json.dumps(self.value))
		with self.assertRaisesRegex(ValueError, 'routine risk downgrade'):
			self.package()
		package = self.package(risk='significant')
		self.assertEqual(package['minimum_risk'], 'significant')
		with self.assertRaisesRegex(ValueError, 'two independent'):
			self.self_record(package)
		self.native_record(package)
		with self.assertRaisesRegex(ValueError, 'two independent'):
			self.authorize()
		self.native_record(package)
		self.assertEqual(self.authorize()['risk'], 'significant')
	def test_restatement_is_routine_only_after_two_approved_exact_versions_and_no_new_evidence(self):
		claim = self.value['identity'][0]
		claim.update(category='pricing')
		self.put_project('ꘖ/KB/Analysis.json', json.dumps(self.value))
		with self.assertRaisesRegex(ValueError, 'routine risk downgrade'):
			self.package(novelty='restatement')
		first = self.package(risk='significant')
		self.native_record(first)
		with self.assertRaisesRegex(ValueError, 'routine risk downgrade'):
			self.package(novelty='restatement')
		self.native_record(first)
		restated = self.package(novelty='restatement')
		self.assertTrue(restated['claims'][0]['previously_approved_restatement'])
		self.put_project('ꘖ/KB/Evidence/new-observation.txt', 'New conflicting evidence')
		with self.assertRaisesRegex(ValueError, 'routine risk downgrade'):
			self.package(novelty='restatement')
	def test_parent_cannot_replace_authored_needs_changes_with_an_approved_json(self):
		package = self.package()
		approved = self.review_report(package)
		rejected = deepcopy(approved)
		rejected['result'] = 'needs_changes'
		rejected['claim_reviews'][0]['outcome'] = 'unsupported'
		with self.assertRaisesRegex(ValueError, 'actual native reviewer verdict'):
			self.native_record(package, report=approved, actual=rejected)
		self.assertEqual(flow.load(self.project)['reviews'], [])
	def test_needs_changes_and_open_findings_persist_and_parent_disposition_cannot_approve(self):
		package = self.package()
		finding = {'id': 'A-1', 'claim_ids': ['F-TITLE'], 'severity': 'minor', 'description': 'The proposed interpretation is unsupported.', 'status': 'open'}
		report = self.self_record(package, result='needs_changes', findings=[finding])
		entry = flow.load(self.project)['reviews'][0]
		original = (self.project / entry['report']).read_bytes()
		evidence = self.put_project('ꘖ/KB/Evidence/Reviews/disposition-evidence.txt', 'Parent investigated the issue.')
		with patch('agent_tools.platforms.adapter'):
			flow.record_review_disposition(self.project, entry['id'], 'A-1', 'resolved', 'Tracked the resolution separately.', [evidence.relative_to(self.project).as_posix()], self.parent)
		self.assertEqual((self.project / entry['report']).read_bytes(), original)
		self.assertEqual(json.loads(original)['result'], 'needs_changes')
		with self.assertRaisesRegex(ValueError, 'needs changes'):
			self.authorize()
		self.self_record(package)
		self.assertEqual(len(flow.load(self.project)['reviews']), 2)
		self.assertEqual((self.project / entry['report']).read_bytes(), original)
		self.authorize()
	def test_per_claim_audit_is_required_and_qualified_gap_can_pass(self):
		package = self.package()
		report = self.review_report(package, self_review=True)
		report['claim_reviews'] = []
		with patch('agent_tools.platforms.adapter'), self.assertRaisesRegex(ValueError, 'Every response claim'):
			flow.record_review(self.project, json_data(report), parent_id=self.parent, reviewer_id=self.parent)
		self.answer = 'Client task. Independent confirmation is unavailable.'
		package = self.package()
		report = self.review_report(package, self_review=True)
		report['claim_reviews'][0].update(outcome='qualified', response_qualification='Independent confirmation is unavailable.')
		with patch('agent_tools.platforms.adapter'):
			flow.record_review(self.project, json_data(report), parent_id=self.parent, reviewer_id=self.parent)
		self.authorize()
	def test_legacy_review_and_analysis_cannot_authorize_new_answer(self):
		self.valid_analysis()
		state = flow.load(self.project)
		state['reviews'] = [{'reviewer_id': self.parent, 'risk': 'routine', 'result': 'approved'}]
		with self.assertRaisesRegex(ValueError, 'schema 3'):
			review.authorize(self.project, state, response=self.answer)
		self.assertIn('stages', flow.status(self.project))
	def test_original_report_proof_is_immutable_when_input_filename_is_reused(self):
		package = self.package()
		report = self.review_report(package, self_review=True)
		path = self.put_project('ꘖ/KB/Evidence/Reviews/self-review.json', json.dumps(report))
		with patch('agent_tools.platforms.adapter'):
			flow.record_review(self.project, path.relative_to(self.project).as_posix(), parent_id=self.parent, reviewer_id=self.parent)
		entry = flow.load(self.project)['reviews'][0]
		original = (self.project / entry['report']).read_bytes()
		path.write_text('{"result":"needs_changes"}')
		self.assertEqual((self.project / entry['report']).read_bytes(), original)
		self.authorize()
	def test_finalize_rejects_changed_journal_answer_after_approved_stage_receipts(self):
		self.put_project('ꘖ/KB/Evidence/init.json', '{}')
		self.put_project('ꘖ/KB/Evidence/research.json', '{}')
		flow.complete_stage(self.project, 'identity_init', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/init.json'])
		flow.complete_stage(self.project, 'research', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/research.json'])
		flow.complete_stage(self.project, 'analysis', ['ꘖ/project.json'], ['ꘖ/KB/Analysis.json'])
		package = self.package()
		self.self_record(package)
		flow.complete_stage(self.project, 'review', ['ꘖ/KB/Analysis.json'], [package['package']])
		flow.complete_stage(self.project, 'kb_review', flow.kb_paths(self.project), ['ꘖ/KB/Analysis.json'], note='Checked consistency.')
		flow.record_current_answer(self.project, self.answer)
		reply = self.project / 'ꙮ/1 - Analysis/res/1.md'
		reply.write_bytes((self.answer + 'Unreviewed addition.').encode())
		with self.assertRaises(ValueError):
			flow.complete_stage(self.project, 'finalize', flow.kb_paths(self.project), ['ꙮ/1 - Analysis/res/1.md'])
	def test_handwritten_routine_package_cannot_bypass_computed_risk(self):
		self.value['identity'][0]['category'] = 'pricing'
		self.put_project('ꘖ/KB/Analysis.json', json.dumps(self.value))
		original = self.package(risk='significant')
		forged = {k: v for k, v in original.items() if k not in ('package', 'package_sha256')}
		forged.update(risk='routine', minimum_risk='routine', task_flags=[], minimum_task_flags=[], risk_reasons=[])
		payload = json_data(forged)
		path = self.put_project(f'ꘖ/KB/Evidence/Reviews/{review.digest(payload)}-inputs.json', payload)
		with self.assertRaisesRegex(ValueError, 'routine risk downgrade'):
			review.read_package(self.project, path.relative_to(self.project).as_posix())
	def test_relabeling_same_answer_cannot_hide_an_independent_rejection(self):
		first = self.package()
		rejected = self.review_report(first, result='needs_changes')
		rejected['claim_reviews'][0]['outcome'] = 'unsupported'
		self.native_record(first, report=rejected)
		prior = flow.load(self.project)['reviews'][-1]
		changed_spec = {'risk': 'routine', 'task_flags': [], 'basis': 'A different package label.', 'request_scope': 'Another wording of the same scope.', 'claim_ids': ['F-TITLE'], 'claims': self.manifest}
		second = flow.prepare_review(self.project, self.parent, changed_spec, self.answer)
		self.assertNotEqual(first['package'], second['package'])
		self.assertEqual(first['subject_sha256'], second['subject_sha256'])
		self.native_record(second)
		with self.assertRaisesRegex(ValueError, 'answer-bound'):
			self.authorize()
		approved = self.review_report(second)
		approved['addresses_reviews'] = [{'review_id': prior['id'], 'basis': 'The literal title is present in the registered snapshot.', 'evidence': ['ꘖ/KB/Analysis.json']}]
		self.native_record(second, report=approved)
		self.authorize()
		self.assertEqual(json.loads((self.project / prior['report']).read_bytes())['result'], 'needs_changes')
	def test_significant_self_finding_requires_two_independent_authored_followups(self):
		first = self.package()
		finding = {'id': 'A-MATERIAL', 'claim_ids': ['F-TITLE'], 'severity': 'significant', 'description': 'The interpretation needs an independent material review.', 'status': 'open'}
		self.self_record(first, result='needs_changes', findings=[finding])
		prior = flow.load(self.project)['reviews'][-1]
		with self.assertRaisesRegex(ValueError, 'significant package'):
			self.package()
		significant = self.package(risk='significant')
		approved = self.review_report(significant)
		approved['addresses_reviews'] = [{'review_id': prior['id'], 'basis': 'Checked raw title against the exact response and resolved the concern.', 'evidence': ['ꘖ/KB/Analysis.json']}]
		self.native_record(significant, report=approved)
		with self.assertRaisesRegex(ValueError, 'two independent'):
			self.authorize()
		self.native_record(significant, report=approved)
		self.authorize()
	def test_task_flags_cannot_omit_typed_work_or_silently_default(self):
		spec = {'risk': 'routine', 'basis': 'Literal title only.', 'request_scope': 'Current request.', 'claim_ids': [], 'claims': []}
		with self.assertRaisesRegex(ValueError, 'task_flags'):
			flow.prepare_review(self.project, self.parent, spec, self.answer)
		self.value['identity'][0]['category'] = 'architecture'
		self.put_project('ꘖ/KB/Analysis.json', json.dumps(self.value))
		spec.update(risk='significant', task_flags=[], claim_ids=['F-TITLE'], claims=self.manifest)
		with self.assertRaisesRegex(ValueError, 'Task flags omit'):
			flow.prepare_review(self.project, self.parent, spec, self.answer)
	def test_audit_must_explain_falsifiability_and_compare_raw_criteria(self):
		package = self.package()
		report = self.review_report(package, self_review=True)
		report['claim_reviews'][0].pop('falsification')
		report['claim_reviews'][0].pop('raw_vs_criteria')
		with patch('agent_tools.platforms.adapter'), self.assertRaisesRegex(ValueError, 'falsification'):
			flow.record_review(self.project, json_data(report), parent_id=self.parent, reviewer_id=self.parent)
	def cli(self, arguments, payload=None):
		from agent_tools.upwork_project import main
		stream = StringIO()
		with patch('sys.stdin', SimpleNamespace(buffer=BytesIO(payload or b''))), redirect_stdout(stream):
			code = main(arguments)
		result = json.loads(stream.getvalue())
		self.assertEqual(code, 0, result)
		r = result
		return r
	def test_cli_exact_candidate_and_report_support_stdin_without_implicit_risk(self):
		spec = {'risk': 'routine', 'task_flags': [], 'basis': 'Literal title only.', 'request_scope': 'Current request.', 'claim_ids': ['F-TITLE'], 'claims': self.manifest}
		source = self.put_project('ꘖ/data/review-spec.json', json.dumps(spec))
		exact = b'Client task\r\n'
		package = self.cli(['prepare-review', str(self.project), '--parent', self.parent, '--spec', str(source), '--response-file', '-'], exact)
		self.assertEqual((self.project / package['response']['file']).read_bytes(), exact)
		report = self.review_report(package, self_review=True)
		with patch('agent_tools.platforms.adapter'):
			self.cli(['record-review', str(self.project), '--parent', self.parent, '--reviewer', self.parent, '--report', '-'], json_data(report))
		self.cli(['record-answer', str(self.project), '--response-file', '-'], exact)
		self.assertEqual((self.project / 'ꙮ/1 - Analysis/res/1.md').read_bytes(), exact)
	def test_cli_preregistered_unavailable_experiment_finishes_question_with_explicit_gap(self):
		requirement = self.experiment_requirement()
		question = {'id': 'Q-CONTENT', 'question': 'Inspect source content.', 'impact': 'Limits attribution.', 'done_when': 'Saved response or explicit gap.', 'inputs': ['ꘖ/project.json'], 'outputs': ['ꘖ/KB/Evidence/question-report.json'], 'requirements': [requirement]}
		self.cli(['question-add', str(self.project), '--spec', '-'], json_data(question))
		self.cli(['question-claim', str(self.project), 'Q-CONTENT', '--owner', 'native-worker'])
		plan = self.cli(['prepare-experiment', str(self.project), '--spec', '-'], json_data(requirement))
		specification = {'plan': plan['plan'], 'plan_sha256': plan['plan_sha256'], 'status': 'unavailable', 'conditions': {}, 'actual_steps': [], 'artifacts': [], 'actual_result': 'The source was unavailable.', 'limitation': 'The source is unavailable; no content conclusion can be verified.'}
		result = self.cli(['record-experiment', str(self.project), '--spec', '-'], json_data(specification))
		self.put_project(question['outputs'][0], json.dumps(result))
		self.cli(['question-finish', str(self.project), 'Q-CONTENT', '--owner', 'native-worker', '--output', question['outputs'][0], '--gap', specification['limitation'], '--results', '-'], json_data([result]))
		saved = flow.load(self.project)
		self.assertEqual(saved['questions']['Q-CONTENT']['status'], 'gap')
		self.assertTrue(flow.questions_current(self.project, saved))
	def test_official_distributor_is_not_established_by_contains_lunos_proxy(self):
		claim = self.value['identity'][0]
		claim.update(essence='The site is an official distributor of Lunos.', knowledge_type='hypothesis', verification_status='limited', missing_checks=['Confirm distributor status with the manufacturer.'])
		self.put_project('ꘖ/KB/Analysis.json', json.dumps(self.value))
		self.answer = 'The site mentions Lunos; official distributor status is unverified.'
		self.manifest = [{'claim_id': 'F-TITLE', 'response_excerpt': self.answer}]
		package = self.package()
		report = self.review_report(package, self_review=True)
		report['claim_reviews'][0]['test_alignment'] = {'target_claim': claim['essence'], 'tested_claim': 'The document contains the word Lunos.', 'relationship': 'proxy', 'rationale': 'A brand mention does not distinguish official distributors from unrelated mentions.', 'counterexample': 'An unaffiliated reseller or an article can mention Lunos without official distributor status.'}
		with patch('agent_tools.platforms.adapter'), self.assertRaisesRegex(ValueError, 'proxy test cannot support'):
			flow.record_review(self.project, json_data(report), parent_id=self.parent, reviewer_id=self.parent)
		report['claim_reviews'][0].update(outcome='qualified', response_qualification='official distributor status is unverified.')
		with patch('agent_tools.platforms.adapter'):
			flow.record_review(self.project, json_data(report), parent_id=self.parent, reviewer_id=self.parent)
		self.authorize()
	def test_audit_target_must_equal_the_analysis_claim_and_irrelevant_test_is_unsupported(self):
		package = self.package()
		report = self.review_report(package, self_review=True)
		alignment = report['claim_reviews'][0]['test_alignment']
		alignment['target_claim'] = 'A different easier statement.'
		self.assertTrue(any(('test_alignment' in issue for issue in review.report_issues(report, package))))
		alignment.update(target_claim=package['claims'][0]['essence'], relationship='irrelevant')
		self.assertTrue(any(('irrelevant test' in issue for issue in review.report_issues(report, package))))
	def test_new_parent_cannot_self_approve_unchanged_answer_rejected_by_native_reviewer(self):
		first = self.package()
		rejected = self.review_report(first, result='needs_changes')
		rejected['claim_reviews'][0]['outcome'] = 'unsupported'
		self.native_record(first, report=rejected)
		with self.assertRaisesRegex(ValueError, 'answer-bound'):
			self.authorize()
		old_parent = self.parent
		self.parent = str(uuid.uuid4())
		second = self.package()
		self.assertNotEqual(first['package'], second['package'])
		self.assertNotEqual(old_parent, second['parent_id'])
		self.assertEqual(first['subject_sha256'], second['subject_sha256'])
		for field in ('response', 'requests', 'kb_inputs', 'evidence_inputs'):
			self.assertEqual(first[field], second[field])
		self.self_record(second)
		with self.assertRaisesRegex(ValueError, 'answer-bound'):
			self.authorize()
	def test_empty_manifest_cannot_omit_the_entire_pricing_analysis(self):
		self.value['identity'][0]['category'] = 'pricing'
		self.put_project('ꘖ/KB/Analysis.json', json.dumps(self.value))
		with self.assertRaisesRegex(ValueError, 'nonempty claim_ids'):
			self.review_package(self.parent, self.answer, 'routine', claims=[])
	def test_handwritten_empty_manifest_package_cannot_pass_record_review(self):
		original = self.package()
		forged = {k: v for k, v in original.items() if k not in ('package', 'package_sha256')}
		forged.update(claims=[], task_flags=[], minimum_task_flags=[], risk_reasons=[])
		payload = json_data(forged)
		path = self.put_project(f'ꘖ/KB/Evidence/Reviews/{review.digest(payload)}-inputs.json', payload)
		package = {'package': path.relative_to(self.project).as_posix(), 'package_sha256': review.digest(payload), **forged}
		report = self.review_report(package, self_review=True)
		self.assertEqual(report['claim_reviews'], [])
		with patch('agent_tools.platforms.adapter'), self.assertRaisesRegex(ValueError, 'nonempty claim_ids'):
			flow.record_review(self.project, json_data(report), parent_id=self.parent, reviewer_id=self.parent)
	def test_review_package_rejects_ungrounded_numbers_in_response_excerpt_and_reviewer_report(self):
		self.answer = 'Client task with 13 items.\n'
		self.manifest = [{'claim_id': 'F-TITLE', 'response_excerpt': 'Client task with 13 items.'}]
		with self.assertRaisesRegex(ValueError, 'numeric figures not grounded'):
			self.package()
		from agent_tools.research import collect, Response
		obs = collect(self.project, 'https://example.org/count', fetcher=lambda *a: Response(a[0], 200, 'text/plain', b'Client task with 13 items.'))
		claim = self.value['identity'][0]
		claim.update(knowledge_type='observation', essence='Client task with 13 items.', scope={'description': 'Captured count page.', 'sample': [obs['url']], 'limitations': []}, evidence=[{'id': 'E-COUNT', 'kind': 'observation', 'source': obs['url'], 'observation': obs['observation'], 'source_sha256': obs['body_sha256'], 'quote': 'Client task with 13 items.', 'locator': {'type': 'text', 'value': 'Client task with 13 items.'}}], for_args=[{'argument': 'The page states 13 items.', 'evidence_id': 'E-COUNT'}])
		claim['for'] = claim.pop('for_args')
		self.put_project('ꘖ/KB/Analysis.json', json.dumps(self.value))
		package = self.package()
		report = self.review_report(package, self_review=True)
		report['claim_reviews'][0]['observed'] = 'Exact registered title inspected without counts.'
		report['claim_reviews'][0]['test_alignment']['tested_claim'] = 'The registered intake contains the title.'
		self.assertTrue(any(('numeric figure' in issue for issue in review.report_issues(report, package))))
		report['claim_reviews'][0]['observed'] = 'Exact registered title inspected: 13 items.'
		self.assertEqual(review.report_issues(report, package), [])
	def test_review_input_returns_neutral_report_contract_with_all_options(self):
		package = self.package()
		receipt = review.input_receipt(self.project, package['package'])
		self.assertIn('report_contract', receipt)
		self.assertEqual(receipt['report_contract']['result_options'], ['approved', 'needs_changes'])
		self.assertEqual(receipt['report_contract']['claim_review_required']['outcome_options'], ['supported', 'qualified', 'unsupported'])
		self.assertEqual(receipt['report_contract']['claim_review_required']['test_alignment_required']['relationship_options'], ['direct', 'proxy', 'irrelevant'])
	def test_e8_causes_misconceptions_and_methods_cannot_be_downgraded_or_omitted_in_routine_review(self):
		from agent_tools.claims import claim_digest
		fact = self.value['identity'][0]
		concern = deepcopy(fact)
		concern.update(id='C-1', essence='Concern item', knowledge_type='hypothesis', verification_status='limited', probability_percent=70, evidence=[], derived_from=[{'claim_id': 'F-TITLE', 'sha256': claim_digest(fact)}], for_args=[{'argument': 'Stated in intake.', 'claim_id': 'F-TITLE'}], missing_checks=['Check admin panel.'])
		concern['for'] = concern.pop('for_args')
		cause = deepcopy(fact)
		cause.update(id='H-CAUSE-1', essence='Root cause explanation', knowledge_type='hypothesis', verification_status='limited', category='descriptive', materiality='routine', properties=['content'], probability_percent=70, addresses=['C-1'], evidence=[], derived_from=[{'claim_id': 'F-TITLE', 'sha256': claim_digest(fact)}], for_args=[{'argument': 'Stated in intake.', 'claim_id': 'F-TITLE'}], missing_checks=['Check admin panel.'], alternative_explanations=['Another cause is possible.'], discriminating_check='Compare admin logs.')
		cause['for'] = cause.pop('for_args')
		self.value['concerns'] = [concern]
		self.value['causes'] = [cause]
		self.put_project('ꘖ/KB/Analysis.json', json.dumps(self.value))
		with self.assertRaisesRegex(ValueError, 'unreviewed causes/misconceptions/methods claims'):
			self.package(risk='routine')
		self.answer = 'Client task\nRoot cause explanation\n'
		self.manifest = [{'claim_id': 'F-TITLE', 'response_excerpt': 'Client task'}, {'claim_id': 'H-CAUSE-1', 'response_excerpt': 'Root cause explanation'}]
		with self.assertRaisesRegex(ValueError, 'routine risk downgrade'):
			self.review_package(self.parent, self.answer, 'routine', self.manifest)
	def test_e9_e10_e11_prepare_review_rejects_empty_red_flags_finalize_notes_and_doc4_multi_sentence_lines(self):
		self.value['red_flags'] = []
		self.put_project('ꘖ/KB/Analysis.json', json.dumps(self.value))
		with self.assertRaisesRegex(ValueError, 'Red Flags heading'):
			self.review_package(self.parent, '# Red Flags\nNone\nClient task\n', 'routine', self.manifest)
		with self.assertRaisesRegex(ValueError, 'internal service notes'):
			self.review_package(self.parent, 'Client task\n## 4. Project Artifacts\ngenerated during finalize\n', 'routine', self.manifest)
		bad_doc4 = 'Client task\n- **Essence:** First sentence of the claim. Second sentence on the same line.\n'
		with self.assertRaisesRegex(ValueError, 'DOC-4 violation'):
			self.review_package(self.parent, bad_doc4, 'routine', self.manifest)
	def test_e12_check_project_flags_unsynced_client_identity_in_kb_project_md(self):
		claim = self.value['identity'][0]
		claim['essence'] = 'The client and website owner is Jean Pierre.'
		claim['verification_status'] = 'verified'
		self.put_project('ꘖ/KB/Analysis.json', json.dumps(self.value))
		self.put_project('KB/Project.md', '# 1. Client\n## 1.1 Name\nunknown\n')
		self.put_project('ꘖ/KB/Project.md', '# 1. Client\n## 1.1 Name\nunknown\n')
		res = flow.check_project(self.project)
		codes = {issue['code'] for issue in res['issues']}
		self.assertIn('kb.identity_mismatch', codes)
	def test_merkle_cached_single_reviewer_quorum_recognizes_approved_digests_and_storage_receipts(self):
		from agent_tools.storage import read_addressed_json, write_immutable_bytes
		claim = self.value['identity'][0]
		claim.update(category='pricing')
		self.put_project('ꘖ/KB/Analysis.json', json.dumps(self.value))
		seed = self.package(risk='significant')
		review.update_verified_claims_cache(self.project, seed, self.value)
		cached_pkg = self.review_package(self.parent, 'Client task\nConfirmed.\n', 'significant', [{'claim_id': 'F-TITLE', 'response_excerpt': 'Client task', 'novelty': 'new'}])
		self.assertEqual(['F-TITLE'], cached_pkg['merkle_delta']['cached_claim_ids'])
		self.assertEqual([], cached_pkg['merkle_delta']['unverified_claim_ids'])
		self.native_record(cached_pkg)
		approved = self.authorize(response='Client task\nConfirmed.\n')
		self.assertEqual(1, len(approved['review_ids']))
		restated = self.review_package(self.parent, 'Client task\nRestated.\n', 'routine', [{'claim_id': 'F-TITLE', 'response_excerpt': 'Client task', 'novelty': 'restatement'}])
		self.assertTrue(restated['claims'][0]['previously_approved_restatement'])
		payload = json_data({'ok': 1})
		sha = review.digest(payload)
		target = write_immutable_bytes(self.project / 'ꘖ/data/receipts' / (sha + '-check.json'), payload, diff_error='immutable mismatch')
		self.assertEqual(target, write_immutable_bytes(target, payload, diff_error='immutable mismatch'))
		with self.assertRaisesRegex(ValueError, 'immutable mismatch'):
			write_immutable_bytes(target, json_data({'ok': 2}), diff_error='immutable mismatch')
		self.assertEqual({'ok': 1}, read_addressed_json(target, suffix='-check.json', error_msg='bad receipt')[1])
		bad_name = self.put_project('ꘖ/data/receipts/0000-check.json', payload.decode('utf-8'))
		with self.assertRaisesRegex(ValueError, 'bad receipt'):
			read_addressed_json(bad_name, suffix='-check.json', error_msg='bad receipt')
