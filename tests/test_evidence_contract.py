# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import unittest
from test_agent_tools import TemporaryCase
from agent_tools.analysis import analysis_issues, render_analysis, save_analysis, publish_analysis, SECTIONS
from agent_tools.claims import all_claims, claim_index, claim_digest, contract_issues
from agent_tools.evidence import evidence_issues
from agent_tools.research import collect, Response
def claim_metadata(ident, *, knowledge_type='observation', status='verified'):
	return {'id': ident, 'essence': 'The captured page contains the stated text.', 'assessment_basis': 'Exact saved bytes at this URL; no statement about UI execution.', 'knowledge_type': knowledge_type, 'verification_status': status, 'scope': {'description': 'One captured public page at the recorded time.', 'sample': ['https://example.org/source'], 'limitations': ['One sample; no admin access.']}, 'properties': ['content'], 'materiality': 'routine', 'novelty': 'new', 'category': 'descriptive', 'derived_from': [], 'evidence': [], 'missing_checks': [] if 'verified' == status else ['Run the discriminating browser/admin check.'], 'impact': {'severity': 'unknown', 'basis': 'No business impact measured.', 'evidence_claim_ids': []}}
def v3_analysis(project, legacy=None):
	observation = collect(project, 'https://example.org/source', fetcher=lambda *args: Response(args[0], 200, 'text/plain', b'The concern\nAlternative\nOld price EUR53.95\nNew price EUR63.95\n'))
	fact = claim_metadata('F-PRIMARY-1')
	fact['evidence'] = [{'id': 'E-PRIMARY-1', 'kind': 'observation', 'source': observation['url'], 'observation': observation['observation'], 'source_sha256': observation['body_sha256'], 'quote': 'The concern\nAlternative', 'locator': {'type': 'lines', 'value': '1-2'}}]
	value = deepcopy(legacy) if None is not legacy else {key: [] for key in SECTIONS}
	value['schema_version'] = 3
	value['facts'] = [fact]
	value.setdefault('notes', {})
	for section in SECTIONS:
		if not value.get(section):
			value['notes'].setdefault(section, 'Not established from available evidence.')
		for claim in value.get(section, []):
			original = dict(claim)
			claim.update(claim_metadata(original['id'], knowledge_type='recommendation' if 'methods' == section else 'hypothesis', status='limited'))
			for key in ('essence', 'assessment_basis', 'probability_percent', 'score_percent', 'criterion', 'addresses'):
				if key in original:
					claim[key] = original[key]
			claim['derived_from'] = [{'claim_id': fact['id'], 'sha256': claim_digest(fact)}]
			for side in ('for', 'against'):
				claim[side] = [{'argument': argument['argument'], 'claim_id': fact['id']} for argument in original.get(side, [])]
			if not claim['against']:
				claim['counterevidence'] = {'status': 'unavailable', 'reviewed_sources': [observation['observation']], 'limitations': 'Synthetic fixture; no additional public counterevidence.'}
			if 'causes' == section:
				claim.update(category='causal', alternative_explanations=['A different configuration can produce the same output.'], discriminating_check='Inspect authorized settings and reproduce under controlled conditions.')
			if 'methods' == section:
				claim.update(applicability=['Confirm the cause in the authorized admin first.'], validation='Repeat the same scenario after the change; compare output and regressions.')
	r = value
	return r
class EvidenceContractTests(TemporaryCase):
	def setUp(self):
		super().setUp()
		self.project = self.root / 'project'
		self.project.mkdir()
	def codes(self, issues):
		return {issue['code'] for issue in issues}
	def test_primary_http_fact_accepts_and_renders_with_scope(self):
		value = v3_analysis(self.project)
		self.assertEqual(analysis_issues(value), [])
		self.assertEqual(evidence_issues(self.project, value), [])
		rendered = render_analysis(value)
		self.assertIn('verified', rendered)
		self.assertIn('One captured public page', rendered)
		self.assertIn('E-PRIMARY-1', rendered)
	def test_legacy_is_readable_but_cannot_be_newly_saved_or_published(self):
		from test_onboarding import analysis
		value = analysis()
		self.assertEqual(analysis_issues(value), [])
		self.assertIn('H-CONCERN-1', render_analysis(value))
		with self.assertRaisesRegex(ValueError, 'schema_version 3'):
			save_analysis(self.project, value)
		target = self.project / 'ꘖ/KB/Analysis.json'
		target.parent.mkdir(parents=True)
		target.write_text(json.dumps(value), encoding='utf-8')
		with self.assertRaisesRegex(ValueError, 'schema_version 3'):
			publish_analysis(target)
	def test_v3_save_checks_real_evidence_and_does_not_overwrite_invalid_candidate(self):
		value = v3_analysis(self.project)
		result = save_analysis(self.project, value)
		self.assertTrue(result['evidence_checked'])
		target = Path(result['target'])
		original = target.read_bytes()
		bad = deepcopy(value)
		bad['facts'][0]['evidence'][0]['quote'] = 'invented'
		with self.assertRaisesRegex(ValueError, 'primary.unconfirmed'):
			save_analysis(self.project, bad, result['sha256'])
		self.assertEqual(target.read_bytes(), original)
		self.assertEqual(publish_analysis(target)['status'], 'published')
	def test_own_prya_kb_note_in_evidence_is_not_a_primary_observation(self):
		value = v3_analysis(self.project)
		note = self.project / 'ꘖ/KB/Evidence/Website.md'
		note.write_text('The concern\nAlternative', encoding='utf-8')
		ref = value['facts'][0]['evidence'][0]
		ref.update(source='Evidence/Website.md', kind='intake', manifest='Evidence/Website.md', source_sha256=hashlib.sha256(note.read_bytes()).hexdigest())
		self.assertIn('primary.unconfirmed', self.codes(evidence_issues(self.project, value)))
	def test_http_does_not_establish_click_currency_ip_or_admin(self):
		for property_name in ('dom', 'interaction', 'currency_transition', 'ip_country', 'admin_configuration', 'serp', 'causality', 'business_impact'):
			with self.subTest(property=property_name):
				value = v3_analysis(self.project)
				value['facts'][0]['properties'] = [property_name]
				self.assertIn('claim.method_insufficient', self.codes(evidence_issues(self.project, value)))
	def test_limited_hypothesis_keeps_missing_browser_check_and_can_be_published(self):
		from test_onboarding import analysis
		value = v3_analysis(self.project, analysis())
		cause = value['causes'][0]
		cause['properties'] = ['admin_configuration', 'causality']
		self.assertEqual(analysis_issues(value), [])
		self.assertEqual(evidence_issues(self.project, value), [])
		target = Path(save_analysis(self.project, value)['target'])
		self.assertEqual(publish_analysis(target)['status'], 'published')
		self.assertIn('Missing check', target.with_suffix('.md').read_text(encoding='utf-8'))
	def test_unavailable_result_is_valid_with_explicit_gap(self):
		value = v3_analysis(self.project)
		claim = value['facts'][0]
		claim.update(verification_status='unavailable', evidence=[], missing_checks=['Obtain the authorized Admin export.'], properties=['admin_configuration'])
		self.assertEqual(analysis_issues(value), [])
		self.assertEqual(evidence_issues(self.project, value), [])
		claim['missing_checks'] = []
		self.assertIn('claim.missing_checks', self.codes(analysis_issues(value)))
	def test_causal_alternatives_and_recommendation_conditions_are_required(self):
		from test_onboarding import analysis
		value = v3_analysis(self.project, analysis())
		value['causes'][0].pop('alternative_explanations')
		value['methods'][0].pop('validation')
		self.assertTrue({'claim.causal', 'claim.recommendation'} <= self.codes(analysis_issues(value)))
	def test_critical_severity_needs_impact_evidence(self):
		value = v3_analysis(self.project)
		value['facts'][0]['impact'].update(severity='critical', basis='Serious defect')
		self.assertIn('claim.impact_evidence', self.codes(analysis_issues(value)))
	def test_dependency_change_and_cycle_are_reported(self):
		from test_onboarding import analysis
		value = v3_analysis(self.project, analysis())
		value['facts'][0]['essence'] = 'Changed premise'
		self.assertIn('claim.stale_dependency', self.codes(analysis_issues(value)))
		value['facts'][0]['derived_from'] = [{'claim_id': value['causes'][0]['id'], 'sha256': claim_digest(value['causes'][0])}]
		self.assertIn('claim.cycle', self.codes(analysis_issues(value)))
	def test_claim_index_includes_facts_and_all_five_stages(self):
		from test_onboarding import analysis
		value = v3_analysis(self.project, analysis())
		self.assertEqual(len(all_claims(value)), 4)
		self.assertIn('F-PRIMARY-1', claim_index(value))
	def test_explicit_text_locator_does_not_cover_another_part_of_page(self):
		value = v3_analysis(self.project)
		ref = value['facts'][0]['evidence'][0]
		ref.update(quote='Alternative', locator={'type': 'text', 'value': 'The concern'})
		self.assertIn('primary.unconfirmed', self.codes(evidence_issues(self.project, value)))
	def price_analysis(self):
		value = v3_analysis(self.project)
		observation = value['facts'][0]['evidence'][0]
		old, new = (claim_metadata('F-OLD'), claim_metadata('F-NEW'))
		for claim, refid, quote in ((old, 'E-OLD', 'Old price EUR53.95'), (new, 'E-NEW', 'New price EUR63.95')):
			ref = deepcopy(observation)
			ref.update(id=refid, quote=quote, locator={'type': 'text', 'value': quote})
			claim['evidence'] = [ref]
		calc = claim_metadata('F-DELTA', knowledge_type='calculation')
		calc['properties'] = ['calculation']
		calc['derived_from'] = [{'claim_id': c['id'], 'sha256': claim_digest(c)} for c in (old, new)]
		calc['calculation'] = {'operation': 'percent_change', 'formula': '(new - old) / old * 100', 'operands': {'old': {'value': '53.95', 'unit': 'EUR', 'claim_id': old['id'], 'evidence_id': 'E-OLD'}, 'new': {'value': '63.95', 'unit': 'EUR', 'claim_id': new['id'], 'evidence_id': 'E-NEW'}}, 'rounding': 'ROUND_HALF_UP', 'rounding_places': 4, 'result': '18.5357', 'result_unit': 'percent'}
		value['facts'] = [old, new, calc]
		r = value
		return r
	def test_6395_relative_to_5395_is_185357_percent_not_20(self):
		value = self.price_analysis()
		self.assertEqual(analysis_issues(value), [])
		self.assertEqual(evidence_issues(self.project, value), [])
		value['facts'][2]['calculation']['result'] = '20'
		issues = evidence_issues(self.project, value)
		self.assertIn('calculation.unconfirmed', self.codes(issues))
		self.assertIn('18.5357', str(issues))
	def test_calculation_operand_must_match_its_own_primary_quote(self):
		value = self.price_analysis()
		value['facts'][2]['calculation']['operands']['old']['value'] = '50'
		self.assertIn('calculation.unconfirmed', self.codes(evidence_issues(self.project, value)))
		value = self.price_analysis()
		value['facts'][2]['calculation']['operands']['old']['evidence_id'] = 'E-NEW'
		self.assertIn('calculation.unconfirmed', self.codes(evidence_issues(self.project, value)))
	def test_calculation_requires_sourced_common_units_and_explicit_percent_result(self):
		value = self.price_analysis()
		calculation = value['facts'][2]['calculation']
		calculation['operands']['old'].pop('unit')
		self.assertIn('calculation.contract', self.codes(analysis_issues(value)))
		calculation['operands']['old']['unit'] = 'EUR'
		calculation.pop('result_unit')
		self.assertIn('calculation.contract', self.codes(analysis_issues(value)))
		calculation['result_unit'] = 'percent'
		calculation['operands']['new']['unit'] = 'GBP'
		self.assertIn('calculation.contract', self.codes(analysis_issues(value)))
		self.assertIn('calculation.contract', self.codes(evidence_issues(self.project, value)))
		calculation['operands']['old']['unit'] = 'GBP'
		self.assertEqual(analysis_issues(value), [])
		self.assertIn('calculation.unconfirmed', self.codes(evidence_issues(self.project, value)))
	def test_missing_or_revised_primary_hash_is_rejected(self):
		value = v3_analysis(self.project)
		value['facts'][0]['evidence'][0]['source_sha256'] = '0' * 64
		self.assertIn('primary.unconfirmed', self.codes(evidence_issues(self.project, value)))
	def test_registered_intake_and_attachment_are_primary_but_quote_must_match_locator(self):
		value = v3_analysis(self.project)
		raw_attachment = b'Client attached requirement'
		att_hash = hashlib.sha256(raw_attachment).hexdigest()
		attachment = self.project / f'ꘖ/KB/Evidence/Attachments/{att_hash}/client.txt'
		attachment.parent.mkdir(parents=True)
		attachment.write_bytes(raw_attachment)
		snapshot = {'job_id': '~02123', 'description': 'Client says the concern exists.', 'buyer': {'name': 'The unrelated field'}, 'asset_evidence': [{'file': f'Evidence/Attachments/{att_hash}/client.txt', 'sha256': att_hash}]}
		raw = json.dumps(snapshot).encode('utf-8')
		sha = hashlib.sha256(raw).hexdigest()
		file = self.project / f'ꘖ/KB/Evidence/{sha}.json'
		file.write_bytes(raw)
		state = self.project / 'ꘖ/project.json'
		state.write_text(json.dumps({'initialized': True, 'job_id': '~02123', 'snapshot': file.relative_to(self.project).as_posix()}), encoding='utf-8')
		fact = value['facts'][0]
		fact['knowledge_type'] = 'client_report'
		fact['evidence'] = [{'id': 'E-INTAKE', 'kind': 'intake', 'source': f'Evidence/{sha}.json', 'manifest': f'Evidence/{sha}.json', 'source_sha256': sha, 'quote': 'Client says the concern exists.', 'locator': {'type': 'json_pointer', 'value': '/description'}}]
		self.assertEqual(evidence_issues(self.project, value), [])
		fact['evidence'][0]['locator']['value'] = '/buyer/name'
		self.assertIn('primary.unconfirmed', self.codes(evidence_issues(self.project, value)))
		fact['evidence'] = [{'id': 'E-ATTACHMENT', 'kind': 'attachment', 'source': snapshot['asset_evidence'][0]['file'], 'manifest': f'Evidence/{sha}.json', 'source_sha256': att_hash, 'quote': raw_attachment.decode(), 'locator': {'type': 'text', 'value': raw_attachment.decode()}}]
		self.assertEqual(evidence_issues(self.project, value), [])
		fact['properties'] = ['admin_configuration']
		self.assertIn('claim.method_insufficient', self.codes(evidence_issues(self.project, value)))
	def test_referenced_primary_cannot_be_replaced_with_an_own_kb_quote(self):
		from test_onboarding import analysis
		value = v3_analysis(self.project, analysis())
		value['concerns'][0]['for'][0].update(source='Website.md#claim', quote='Agent says verified')
		self.assertIn('argument.competing_reference', self.codes(analysis_issues(value)))
	def test_experiment_primary_uses_recorder_artifact_and_actual_method(self):
		from agent_tools.experiments import prepare_experiment, record_experiment, load_experiment
		requirement = {'id': 'REQ-CONTENT', 'claim': 'This HTTP capture contains the concern.', 'property': 'content', 'method': 'http', 'alternatives': ['The response is a challenge page.'], 'conditions': {}, 'scope': {'objects': ['https://example.org/source']}, 'expected': 'Contains the concern', 'falsification': 'The exact phrase is absent.', 'discriminating_test': 'Compare an exact primary quote against the response.', 'completion_criterion': 'Exact saved source quote matches.', 'assertions': [{'id': 'ASSERT-CONTENT', 'artifact_id': 'A-CONTENT', 'locator': {'type': 'text', 'value': ''}, 'operator': 'contains', 'expected': 'The concern', 'disconfirming': {'operator': 'contains', 'expected': 'Concern absent'}}]}
		plan = prepare_experiment(self.project, requirement)
		value = v3_analysis(self.project)
		original = value['facts'][0]['evidence'][0]
		receipt = record_experiment(self.project, {'status': 'verified', 'plan': plan['plan'], 'plan_sha256': plan['plan_sha256'], 'conditions': {}, 'actual_steps': [], 'actual_result': 'The concern is present in the saved text.', 'artifacts': [{'id': 'A-CONTENT', 'observation': original['observation']}]})
		run = load_experiment(self.project, receipt['experiment'])
		artifact = run['artifacts'][0]
		value['facts'][0]['evidence'] = [{'id': 'E-EXPERIMENT', 'kind': 'experiment', 'experiment': receipt['experiment'], 'artifact_id': artifact['id'], 'source': artifact['path'], 'source_sha256': artifact['sha256'], 'quote': 'The concern', 'locator': {'type': 'text', 'value': 'The concern'}}]
		self.assertEqual(analysis_issues(value), [])
		self.assertEqual(evidence_issues(self.project, value), [])
		value['facts'][0]['properties'] = ['interaction']
		self.assertIn('claim.method_insufficient', self.codes(evidence_issues(self.project, value)))
		value['facts'][0]['evidence'][0]['artifact_id'] = 'nonexistent'
		self.assertIn('primary.unconfirmed', self.codes(evidence_issues(self.project, value)))
	def test_malformed_typed_metadata_returns_diagnostics(self):
		for key in ('knowledge_type', 'verification_status', 'materiality', 'novelty', 'category'):
			with self.subTest(field=key):
				value = v3_analysis(self.project)
				value['facts'][0][key] = []
				self.assertTrue(contract_issues(value))
	def test_agent_site_hypothesis_in_intake_manifest_is_not_primary(self):
		value = v3_analysis(self.project)
		raw = b'{"essence":"Configured exactly +20 percent"}'
		sha = hashlib.sha256(raw).hexdigest()
		target = self.project / f'ꘖ/KB/Evidence/Intake/objects/{sha}.json'
		target.parent.mkdir(parents=True)
		target.write_bytes(raw)
		manifest = self.project / 'ꘖ/KB/Evidence/Intake/capture.json'
		manifest.write_text(json.dumps({'version': 1, 'status': 'drained', 'job_id': '~02123', 'entries': [{'durable_file': target.relative_to(self.project).as_posix(), 'sha256': sha, 'original_relative_provenance': 'site.json', 'transform': 'identity'}]}), encoding='utf-8')
		(self.project / 'ꘖ/project.json').write_text('{"job_id":"~02123"}', encoding='utf-8')
		value['facts'][0]['evidence'] = [{'id': 'E-SELF', 'kind': 'intake', 'source': target.relative_to(self.project / 'ꘖ/KB').as_posix(), 'manifest': manifest.relative_to(self.project / 'ꘖ/KB').as_posix(), 'source_sha256': sha, 'quote': 'Configured exactly +20 percent', 'locator': {'type': 'json_pointer', 'value': '/essence'}}]
		self.assertIn('primary.unconfirmed', self.codes(evidence_issues(self.project, value)))
	def test_arbitrary_intake_receipt_cannot_promote_own_note_or_attachment(self):
		value = v3_analysis(self.project)
		raw = b'{"job_id":"~02123","description":"Original client statement"}'
		sha = hashlib.sha256(raw).hexdigest()
		snapshot = self.project / f'ꘖ/KB/Evidence/{sha}.json'
		snapshot.write_bytes(raw)
		(self.project / 'ꘖ/project.json').write_text(json.dumps({'initialized': True, 'job_id': '~02123', 'snapshot': snapshot.relative_to(self.project).as_posix()}), encoding='utf-8')
		note = self.project / 'ꘖ/KB/Website.md'
		note.write_text('Own agent note.', encoding='utf-8')
		note_sha = hashlib.sha256(note.read_bytes()).hexdigest()
		manifest = self.project / 'ꘖ/KB/Evidence/Intake/arbitrary.json'
		manifest.parent.mkdir(parents=True)
		for kind, name in (('intake', 'source.json'), ('attachment', 'attachments/client.txt')):
			with self.subTest(kind=kind):
				manifest.write_text(json.dumps({'version': 1, 'status': 'drained', 'job_id': '~02123', 'entries': [{'durable_file': note.relative_to(self.project).as_posix(), 'sha256': note_sha, 'original_relative_provenance': name, 'transform': 'identity'}]}), encoding='utf-8')
				value['facts'][0]['evidence'] = [{'id': 'E-OWN', 'kind': kind, 'source': 'Website.md', 'manifest': 'Evidence/Intake/arbitrary.json', 'source_sha256': note_sha, 'quote': 'Own agent note.', 'locator': {'type': 'text', 'value': 'Own agent note.'}}]
				self.assertEqual(analysis_issues(value), [])
				self.assertIn('primary.unconfirmed', self.codes(evidence_issues(self.project, value)))
				with self.assertRaisesRegex(ValueError, 'primary.unconfirmed'):
					save_analysis(self.project, value)
				self.assertFalse((self.project / 'ꘖ/KB/Analysis.json').exists())
	def test_full_real_intake_receipt_binds_source_to_snapshot_and_rejects_relabelled_note(self):
		from test_intake import IntakeTests
		fixture = IntakeTests()
		fixture.setUp()
		self.addCleanup(fixture.doCleanups)
		fixture.initialize()
		self.assertEqual(fixture.commit()['status'], 'drained')
		receipt_file = fixture.manifest()
		receipt = json.loads(receipt_file.read_text(encoding='utf-8'))
		original = next((e for e in receipt['entries'] if 'source.json' == e['original_relative_provenance']))
		value = v3_analysis(fixture.project)
		source = fixture.project / original['durable_file']
		value['facts'][0]['evidence'] = [{'id': 'E-INTAKE', 'kind': 'intake', 'source': source.relative_to(fixture.project / 'ꘖ/KB').as_posix(), 'manifest': receipt_file.relative_to(fixture.project / 'ꘖ/KB').as_posix(), 'source_sha256': original['sha256'], 'quote': 'Exact source\n', 'locator': {'type': 'json_pointer', 'value': '/description'}}]
		self.assertEqual(evidence_issues(fixture.project, value), [])
		payload = json.dumps({'job_id': fixture.source['job_id'], 'description': 'Own agent conclusion', 'saved_attachments': []}).encode('utf-8')
		sha = hashlib.sha256(payload).hexdigest()
		note = fixture.project / f'ꘖ/KB/Evidence/Intake/objects/{sha}.json'
		note.write_bytes(payload)
		original.update(durable_file=note.relative_to(fixture.project).as_posix(), sha256=sha, bytes=len(payload))
		receipt_file.write_text(json.dumps(receipt), encoding='utf-8')
		ref = value['facts'][0]['evidence'][0]
		ref.update(source=note.relative_to(fixture.project / 'ꘖ/KB').as_posix(), source_sha256=sha, quote='Own agent conclusion')
		self.assertIn('primary.unconfirmed', self.codes(evidence_issues(fixture.project, value)))
	def test_malformed_properties_and_dependency_keep_field_diagnostics_in_cli(self):
		for field, bad, expected in (('properties', 1, 'claim.properties'), ('derived_from', [{'claim_id': [], 'sha256': '0' * 64}], 'claim.dependency')):
			with self.subTest(field=field):
				value = v3_analysis(self.project)
				value['facts'][0][field] = bad
				self.assertIn(expected, self.codes(evidence_issues(self.project, value)))
				path = self.project / 'ꘖ/KB/Analysis.json'
				path.write_text(json.dumps(value), encoding='utf-8')
				result = self.cli('upwork_project', 'validate-analysis', path, '--format', 'json', '--evidence')
				self.assertEqual(result.returncode, 1, result.stderr)
				issues = json.loads(result.stdout)['issues']
				self.assertIn(expected, self.codes(issues))
				self.assertNotIn('operation.input', self.codes(issues))
				self.assertTrue(any(('F-PRIMARY-1' == i.get('claim_id') and i['field'].startswith('/facts/0/') for i in issues)))
	def test_currency_cannot_be_borrowed_from_another_quantity(self):
		value = self.price_analysis()
		response = Response('https://example.org/prices', 200, 'text/plain', b'Old price GBP53.95; EUR1.00 conversion reference.\nNew price GBP63.95; EUR1.00 conversion reference.')
		observation = collect(self.project, response.url, fetcher=lambda *args: response)
		for claim, label, number in ((value['facts'][0], 'Old', '53.95'), (value['facts'][1], 'New', '63.95')):
			quote = f'{label} price GBP{number}; EUR1.00 conversion reference.'
			claim['evidence'][0].update(source=response.url, observation=observation['observation'], source_sha256=observation['body_sha256'], quote=quote, locator={'type': 'text', 'value': quote})
		value['facts'][2]['derived_from'] = [{'claim_id': c['id'], 'sha256': claim_digest(c)} for c in value['facts'][:2]]
		self.assertEqual(analysis_issues(value), [])
		self.assertIn('calculation.unconfirmed', self.codes(evidence_issues(self.project, value)))
		for operand in value['facts'][2]['calculation']['operands'].values():
			operand['unit'] = 'GBP'
		self.assertEqual(evidence_issues(self.project, value), [])
	def test_json_amount_currency_pair_is_an_exact_quantity_locator(self):
		value = self.price_analysis()
		payload = json.dumps({'old': {'amount': '53.95', 'currency': 'EUR'}, 'new': {'amount': '63.95', 'currency': 'EUR'}}).encode('utf-8')
		response = Response('https://example.org/prices.json', 200, 'application/json', payload)
		observation = collect(self.project, response.url, fetcher=lambda *args: response)
		for claim, label, number in ((value['facts'][0], 'old', '53.95'), (value['facts'][1], 'new', '63.95')):
			quote = json.dumps({'amount': number, 'currency': 'EUR'}, indent=2)
			claim['evidence'][0].update(source=response.url, observation=observation['observation'], source_sha256=observation['body_sha256'], quote=quote, locator={'type': 'json_pointer', 'value': '/' + label})
		value['facts'][2]['derived_from'] = [{'claim_id': c['id'], 'sha256': claim_digest(c)} for c in value['facts'][:2]]
		self.assertEqual(analysis_issues(value), [])
		self.assertEqual(evidence_issues(self.project, value), [])
	def signed_price_analysis(self, quote, declared_old, *, excerpt=None):
		value = self.price_analysis()
		new_quote = 'New price 63.95 EUR'
		response = Response('https://example.org/signed-prices', 200, 'text/plain', (quote + '\n' + new_quote).encode('utf-8'))
		observation = collect(self.project, response.url, refresh_reason='Distinct signed quantity case', fetcher=lambda *args: response)
		for claim, source_quote in ((value['facts'][0], excerpt or quote), (value['facts'][1], new_quote)):
			claim['evidence'][0].update(source=response.url, observation=observation['observation'], source_sha256=observation['body_sha256'], quote=source_quote, locator={'type': 'text', 'value': source_quote})
		calculation = value['facts'][2]['calculation']
		calculation['operands']['old']['value'] = declared_old
		calculation['result'] = '-218.5357' if declared_old.startswith('-') else '18.5357'
		value['facts'][2]['derived_from'] = [{'claim_id': c['id'], 'sha256': claim_digest(c)} for c in value['facts'][:2]]
		r = value
		return r
	def test_signed_quantity_cannot_be_replaced_with_its_positive_substring(self):
		cases = [('-53.95 EUR', '53.95'), ('−53.95 EUR', '53.95'), ('- 53.95 EUR', '53.95'), ('EUR-53.95', '53.95'), ('-EUR53.95', '53.95'), ('-€53.95', '53.95'), ('- EUR53.95', '53.95'), ('EUR −53.95', '53.95'), ('+53.95 EUR', '-53.95'), ('EUR+53.95', '-53.95'), ('(EUR53.95)', '53.95'), ('(53.95) EUR', '53.95'), ('EUR153.95', '53.95'), ('1 053.95 EUR', '53.95'), ('－53.95 EUR', '53.95'), ('-\u200b53.95 EUR', '53.95')]
		for quote, declared in cases:
			with self.subTest(quote=quote, declared=declared):
				value = self.signed_price_analysis('Old price ' + quote, declared)
				self.assertEqual(analysis_issues(value), [])
				self.assertIn('calculation.unconfirmed', self.codes(evidence_issues(self.project, value)))
				with self.assertRaisesRegex(ValueError, 'calculation.unconfirmed'):
					save_analysis(self.project, value)
		for quote, excerpt in (('-53.95 EUR', '53.95 EUR'), ('−53.95 EUR', '53.95 EUR'), ('-€53.95', '€53.95'), ('- EUR53.95', 'EUR53.95')):
			with self.subTest(trimmed_sign=quote):
				value = self.signed_price_analysis('Old price ' + quote, '53.95', excerpt=excerpt)
				self.assertIn('calculation.unconfirmed', self.codes(evidence_issues(self.project, value)))
	def test_supported_signed_quantities_preserve_decimal_value_and_units(self):
		for quote in ('EUR53.95', '53.95 EUR', '€53.95', '+53.95 EUR', 'EUR+53.95'):
			with self.subTest(positive=quote):
				value = self.signed_price_analysis('Old price ' + quote, '53.95')
				self.assertEqual(evidence_issues(self.project, value), [])
		for quote in ('-53.95 EUR', '−53.95 EUR', '- 53.95 EUR', 'EUR-53.95', '-EUR53.95', '-€53.95', '- EUR53.95', 'EUR −53.95'):
			with self.subTest(negative=quote):
				value = self.signed_price_analysis('Old price ' + quote, '-53.95')
				self.assertEqual(evidence_issues(self.project, value), [])
				self.assertEqual(value['facts'][2]['calculation']['result'], '-218.5357')
	def test_html_markup_cannot_hide_a_sign_between_spans(self):
		value = self.price_analysis()
		response = Response('https://example.org/html-prices', 200, 'text/html', b'<html><p>Old price <span class="sign">-</span><span class="value">53.95 EUR</span></p><p>New price <span class="value">63.95 EUR</span></p></html>')
		observation = collect(self.project, response.url, fetcher=lambda *args: response)
		for claim, number in ((value['facts'][0], '53.95'), (value['facts'][1], '63.95')):
			quote = f'<span class="value">{number} EUR</span>'
			claim['evidence'][0].update(source=response.url, observation=observation['observation'], source_sha256=observation['body_sha256'], quote=quote, locator={'type': 'text', 'value': quote})
		def refresh_dependencies():
			value['facts'][2]['derived_from'] = [{'claim_id': c['id'], 'sha256': claim_digest(c)} for c in value['facts'][:2]]
		refresh_dependencies()
		self.assertEqual(analysis_issues(value), [])
		issues = evidence_issues(self.project, value)
		self.assertIn('calculation.unconfirmed', self.codes(issues))
		self.assertIn('Raw markup excerpts', str(issues))
		with self.assertRaisesRegex(ValueError, 'Raw markup excerpts'):
			save_analysis(self.project, value)
		for claim, quote in ((value['facts'][0], '53.95 EUR'), (value['facts'][1], '63.95 EUR')):
			claim['evidence'][0].update(quote=quote, locator={'type': 'text', 'value': quote})
		refresh_dependencies()
		self.assertIn('calculation.unconfirmed', self.codes(evidence_issues(self.project, value)))
		quote = '-53.95 EUR'
		value['facts'][0]['evidence'][0].update(quote=quote, locator={'type': 'text', 'value': quote})
		value['facts'][2]['calculation']['operands']['old']['value'] = '-53.95'
		value['facts'][2]['calculation']['result'] = '-218.5357'
		refresh_dependencies()
		self.assertEqual(analysis_issues(value), [])
		self.assertEqual(evidence_issues(self.project, value), [])
		self.assertTrue(save_analysis(self.project, value)['evidence_checked'])
	def test_v3_documentation_requires_verified_anchor_or_genuine_no_anchor_section(self):
		value = v3_analysis(self.project)
		response = Response('https://docs.example.org/feature', 200, 'text/html', b'<html><h2 id="policy">Policy</h2><p>Official source says this feature exists.</p></html>')
		observation = collect(self.project, response.url, fetcher=lambda *args: response)
		fact = value['facts'][0]
		fact['properties'] = ['platform_capability']
		fact['scope']['sample'] = [response.url]
		fact['evidence'] = [{'id': 'E-DOC', 'kind': 'observation', 'documentation': True, 'source': response.url, 'observation': observation['observation'], 'source_sha256': observation['body_sha256'], 'quote': 'Official source says this feature exists.', 'locator': {'type': 'text', 'value': 'Official source says this feature exists.'}}]
		self.assertIn('documentation.locator', self.codes(analysis_issues(value)))
		with self.assertRaisesRegex(ValueError, 'documentation.locator'):
			save_analysis(self.project, value)
		ref = fact['evidence'][0]
		ref['anchor_exception'] = {'section': 'Policy', 'observation': observation['observation']}
		self.assertIn('primary.unconfirmed', self.codes(evidence_issues(self.project, value)))
		ref.pop('anchor_exception')
		ref.update(source=response.url + '#policy', locator={'type': 'anchor', 'value': 'policy'})
		self.assertEqual(analysis_issues(value), [])
		self.assertEqual(evidence_issues(self.project, value), [])
		no_anchor = Response(response.url, 200, 'text/html', b'<html><h2>Policy</h2><p>Official source says this feature exists.</p><h2>Other</h2>Unrelated text.</html>')
		observation = collect(self.project, response.url, refresh_reason='Separate no-anchor documentation sample', fetcher=lambda *args: no_anchor)
		ref.update(source=response.url, observation=observation['observation'], source_sha256=observation['body_sha256'], locator={'type': 'text', 'value': ref['quote']}, anchor_exception={'section': 'Policy', 'observation': observation['observation']})
		self.assertEqual(analysis_issues(value), [])
		self.assertEqual(evidence_issues(self.project, value), [])
		self.assertIn('Documentation section: Policy', render_analysis(value))
		ref['anchor_exception']['section'] = 'Other'
		self.assertIn('primary.unconfirmed', self.codes(evidence_issues(self.project, value)))
	def test_verified_observation_rejects_ungrounded_numbers_in_essence(self):
		value = v3_analysis(self.project)
		fact = value['facts'][0]
		fact['essence'] = 'The captured page contains 13 items created on 2026-10-08.'
		issues = analysis_issues(value)
		self.assertIn('claim.ungrounded_number', self.codes(issues))
		fact['evidence'][0]['quote'] = 'The concern\nAlternative\n13 items created on 2026-10-08'
		self.assertNotIn('claim.ungrounded_number', self.codes(analysis_issues(value)))
	def test_misconception_hypothesis_requires_alternatives_and_discriminating_check(self):
		value = v3_analysis(self.project)
		fact = value['facts'][0]
		misconception = claim_metadata('H-MISC-1', knowledge_type='hypothesis', status='limited')
		misconception.update(essence='The client assumes the missing items were indexed previously.', derived_from=[{'claim_id': fact['id'], 'sha256': claim_digest(fact)}], for_args=[{'argument': 'Stated in description.', 'claim_id': fact['id']}], against=[], counterevidence={'status': 'not_found', 'reviewed_sources': [fact['evidence'][0]['observation']], 'limitations': 'Public only.'}, probability_percent=70)
		misconception['for'] = misconception.pop('for_args')
		value['misconceptions'] = [misconception]
		self.assertIn('claim.causal', self.codes(analysis_issues(value)))
		misconception['alternative_explanations'] = ['Items were created recently and never indexed.']
		misconception['discriminating_check'] = 'Compare item creation timestamps against index snapshots.'
		self.assertNotIn('claim.causal', self.codes(analysis_issues(value)))
	def test_unverified_hypothesis_with_empty_against_caps_probability_at_75(self):
		from test_onboarding import analysis
		value = v3_analysis(self.project, analysis())
		cause = value['causes'][0]
		cause['against'] = []
		cause['counterevidence'] = {'status': 'not_found', 'reviewed_sources': [value['facts'][0]['evidence'][0]['observation']], 'limitations': 'Public source only.'}
		cause['probability_percent'] = 85
		self.assertIn('claim.counterevidence', self.codes(analysis_issues(value)))
		cause['probability_percent'] = 75
		self.assertNotIn('claim.counterevidence', self.codes(analysis_issues(value)))
	def test_e1_and_e2_sitemap_alone_and_unobserved_sample_urls_are_rejected(self):
		value = v3_analysis(self.project)
		sitemap_xml = b'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.org/blog/post-one</loc></url></urlset>'
		obs = collect(self.project, 'https://example.org/sitemap.xml', fetcher=lambda *a: Response(a[0], 200, 'application/xml', sitemap_xml))
		fact = value['facts'][0]
		fact['essence'] = 'The blog post is a demo post with thin content.'
		fact['scope']['sample'] = ['https://example.org/sitemap.xml', 'https://example.org/blog/post-one']
		fact['evidence'] = [{'id': 'E-SITEMAP', 'kind': 'observation', 'source': obs['url'], 'observation': obs['observation'], 'source_sha256': obs['body_sha256'], 'quote': 'https://example.org/blog/post-one', 'locator': {'type': 'text', 'value': 'https://example.org/blog/post-one'}}]
		codes = self.codes(evidence_issues(self.project, value))
		self.assertIn('claim.sitemap_insufficient', codes)
		self.assertIn('claim.unobserved_sample', codes)
	def test_e3_network_error_classification_and_unverified_dns_claim_rejection(self):
		import socket
		from agent_tools.research import classify_network_error
		self.assertEqual(classify_network_error(socket.gaierror(11001, 'getaddrinfo failed')), ('dns_error', False))
		self.assertEqual(classify_network_error(TimeoutError('timed out')), ('tcp_timeout', None))
		def timeout_fetcher(*args):
			raise TimeoutError('timed out')
		obs = collect(self.project, 'https://timeout.example.org/', fetcher=timeout_fetcher)
		self.assertEqual(obs['error_kind'], 'tcp_timeout')
		self.assertIsNone(obs['dns_resolved'])
		value = v3_analysis(self.project)
		fact = value['facts'][0]
		fact['essence'] = 'Domain timeout.example.org has no DNS record (NXDOMAIN) and is unregistered.'
		fact['scope']['sample'] = ['https://timeout.example.org/']
		raw_obs = json.loads((self.project / 'ꘖ/KB' / obs['observation']).read_text(encoding='utf-8'))
		fact['evidence'][0]['observation'] = obs['observation']
		self.assertIn('claim.unverified_dns', self.codes(evidence_issues(self.project, value)))
		self.assertEqual(raw_obs['error_kind'], 'tcp_timeout')
	def test_e4_site_wide_schema_absence_requires_multi_page_or_product_template_sample(self):
		value = v3_analysis(self.project)
		fact = value['facts'][0]
		fact['essence'] = 'Product and BlogPosting Schema.org markup are absent across the entire site.'
		fact['scope']['sample'] = ['https://example.org/source']
		self.assertIn('claim.scope_extrapolation', self.codes(evidence_issues(self.project, value)))
		obs2 = collect(self.project, 'https://example.org/shop/product-one', fetcher=lambda *a: Response(a[0], 200, 'text/html', b'<html><h1>Product One</h1></html>'))
		fact['scope']['sample'] = ['https://example.org/source', obs2['url']]
		fact['evidence'].append({'id': 'E-PROD-ONE', 'kind': 'observation', 'source': obs2['url'], 'observation': obs2['observation'], 'source_sha256': obs2['body_sha256'], 'quote': 'Product One', 'locator': {'type': 'text', 'value': 'Product One'}})
		self.assertNotIn('claim.scope_extrapolation', self.codes(evidence_issues(self.project, value)))
	def test_e5_and_e6_html_sitemap_and_site_summary_diagnostics(self):
		from agent_tools.research import compute_site_summary, extract_observation
		html_bytes = b'<html><head><title>' + b'Very Long Page Title ' * 4 + b'</title><script type="application/ld+json">{"@type":"WebSite","name":"S P I R I T  S E A","description":"","image":"http://example.org/logo.jpg"}</script></head><body><h1>First H1</h1><h1>Second H1</h1><img src="/a.jpg" alt=""><iframe src="https://www.youtube.com/embed/xyz"></iframe></body></html>'
		r1 = collect(self.project, 'https://example.org/page-a', fetcher=lambda *a: Response(a[0], 200, 'text/html', html_bytes))
		r1.update(extract_observation(self.project, r1['observation']))
		r2 = collect(self.project, 'https://example.org/page-b', fetcher=lambda *a: Response(a[0], 200, 'text/html', html_bytes))
		r2.update(extract_observation(self.project, r2['observation']))
		sitemap_bytes = b'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.org/blog-post-title-one</loc><lastmod>2020-05-05</lastmod></url><url><loc>https://example.org/home</loc><lastmod>2020-05-05</lastmod></url></urlset>'
		r3 = collect(self.project, 'https://example.org/sitemap.xml', fetcher=lambda *a: Response(a[0], 200, 'application/xml', sitemap_bytes))
		r3.update(extract_observation(self.project, r3['observation']))
		ext = json.loads((self.project / 'ꘖ/KB' / r1['extraction']).read_text(encoding='utf-8'))
		self.assertTrue(ext['seo_diagnostics']['multiple_h1'])
		self.assertTrue(ext['seo_diagnostics']['overlong_title'])
		self.assertTrue(ext['seo_diagnostics']['spaced_brand_name'])
		self.assertTrue(ext['seo_diagnostics']['empty_json_ld_description'])
		self.assertTrue(ext['seo_diagnostics']['insecure_or_relative_json_ld_image'])
		self.assertEqual(ext['image_alt_summary']['empty_alt'], 1)
		self.assertEqual(ext['embeds'], [{'tag': 'iframe', 'src': 'https://www.youtube.com/embed/xyz'}])
		ext_sitemap = json.loads((self.project / 'ꘖ/KB' / r3['extraction']).read_text(encoding='utf-8'))
		self.assertIn('https://example.org/blog-post-title-one', ext_sitemap['sitemap']['sitemap_issues']['template_slug_urls'])
		self.assertTrue(ext_sitemap['sitemap']['sitemap_issues']['root_url_missing'])
		summary = compute_site_summary(self.project, [r1, r2, r3])
		self.assertEqual(len(summary['duplicate_titles']), 1)
		self.assertEqual(summary['multiple_h1_urls'], ['https://example.org/page-a', 'https://example.org/page-b'])
	def test_e7_contradictory_evidence_reuse_in_against_and_intake_only_counterevidence_cap(self):
		from test_onboarding import analysis
		value = v3_analysis(self.project, analysis())
		cause = value['causes'][0]
		ref = deepcopy(value['facts'][0]['evidence'][0])
		ref['id'] = 'E-CAUSE-OWN'
		cause['evidence'] = [ref]
		cause['for'] = [{'argument': 'Supports the cause.', 'evidence_id': 'E-CAUSE-OWN'}]
		cause['against'] = [{'argument': 'Same evidence reused in against.', 'evidence_id': 'E-CAUSE-OWN'}]
		self.assertIn('argument.contradictory_reuse', self.codes(analysis_issues(value)))
	def test_e8_relational_comparison_and_modification_require_two_distinct_operands_with_verified_hashes(self):
		from test_onboarding import analysis
		value = v3_analysis(self.project, analysis())
		mod_fact = deepcopy(value['facts'][0])
		mod_fact['id'] = 'F-MOD-1'
		mod_fact['evidence'][0]['id'] = 'E-MOD-A'
		mod_fact['properties'] = ['content', 'modification']
		value['facts'].append(mod_fact)
		self.assertIn('claim.relational_arity', self.codes(analysis_issues(value)))
		mod_fact['comparison'] = {'relation': 'modified_from', 'operand_a_evidence_id': 'E-MOD-A', 'operand_b_evidence_id': 'E-MOD-A'}
		self.assertIn('claim.relational_arity', self.codes(analysis_issues(value)))
		obs_same = collect(self.project, 'https://example.org/baseline-same', fetcher=lambda *a: Response(a[0], 200, 'text/plain', b'The concern\nAlternative\nOld price EUR53.95\nNew price EUR63.95\n'))
		mod_fact['evidence'].append({'id': 'E-BASELINE-SAME', 'kind': 'observation', 'source': obs_same['url'], 'observation': obs_same['observation'], 'source_sha256': obs_same['body_sha256'], 'quote': 'The concern\nAlternative', 'locator': {'type': 'lines', 'value': '1-2'}})
		mod_fact['comparison'] = {'relation': 'modified_from', 'operand_a_evidence_id': 'E-MOD-A', 'operand_b_evidence_id': 'E-BASELINE-SAME'}
		self.assertIn('comparison.unconfirmed', self.codes(evidence_issues(self.project, value)))
		obs_diff = collect(self.project, 'https://example.org/baseline-clean', fetcher=lambda *a: Response(a[0], 200, 'text/plain', b'Clean upstream distribution file\n'))
		mod_fact['evidence'][-1] = {'id': 'E-BASELINE-CLEAN', 'kind': 'observation', 'source': obs_diff['url'], 'observation': obs_diff['observation'], 'source_sha256': obs_diff['body_sha256'], 'quote': 'Clean upstream distribution file', 'locator': {'type': 'text', 'value': 'Clean upstream distribution file'}}
		mod_fact['comparison'] = {'relation': 'modified_from', 'operand_a_evidence_id': 'E-MOD-A', 'operand_b_evidence_id': 'E-BASELINE-CLEAN'}
		self.assertNotIn('claim.relational_arity', self.codes(evidence_issues(self.project, value)))
		self.assertNotIn('comparison.unconfirmed', self.codes(evidence_issues(self.project, value)))
if '__main__' == __name__:
	unittest.main()
