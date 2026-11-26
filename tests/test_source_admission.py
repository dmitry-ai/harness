# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import override
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread
from unittest.mock import patch
import unittest
from test_text_workflow import TextWorkspaceCase, codes
from agent_tools import text_sources, text_workflow, text_review
from agent_tools.claims import standalone_numbers
from agent_tools.article import check_link_style
from agent_tools.text_core import scan
from agent_tools.research import collect, Response, json_data
from agent_tools.text_claims import digest
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
class LinkPresentationTests(unittest.TestCase):
	# @used-by :meth:`LinkPresentationTests.test_missing_changed_fragment_path_query_or_host_is_rejected()`
	# @used-by :meth:`LinkPresentationTests.test_named_links_are_allowed_in_other_profiles_and_literals_are_preserved()`
	# @used-by :meth:`LinkPresentationTests.test_original_numeric_anchor_is_not_a_quantitative_claim()`
	# @used-by :meth:`LinkPresentationTests.test_reference_links_and_balanced_parentheses_keep_the_same_behavior()`
	def findings(self, text, profile='formatted'):
		findings = []
		check_link_style(scan(text), findings, profile)
		r = {f.rule for f in findings}
		return r
	# @used-by :mod:`unittest`
	def test_original_numeric_anchor_is_not_a_quantitative_claim(self):
		for fragment in ('15.3', 'p-15.3(k)'):
			text = f'[**ecfr.gov**/current/title-47/part-15#{fragment}](<https://www.ecfr.gov/current/title-47/part-15#{fragment}>)'
			self.assertEqual(standalone_numbers(text), set())
			self.assertEqual(self.findings(text), set())
	# @used-by :mod:`unittest`
	def test_numeric_prose_in_a_link_label_still_needs_grounding(self):
		self.assertEqual(standalone_numbers('[The limit is 15.3 volts.](https://example.org/)'), {'15.3'})
		self.assertEqual(standalone_numbers('The limit is **15.3** volts.'), {'15.3'})
	# @used-by :mod:`unittest`
	def test_reference_links_and_balanced_parentheses_keep_the_same_behavior(self):
		text = '[**ecfr.gov**/part-15#p-15.3(k)][law]\n\n[law]: <https://ecfr.gov/part-15#p-15.3(k)>'
		self.assertEqual(standalone_numbers(text), set())
		self.assertNotIn('LINK-LABEL', self.findings(text))
	# @used-by :mod:`unittest`
	def test_missing_changed_fragment_path_query_or_host_is_rejected(self):
		target = 'https://ecfr.gov/part-15?edition=current#p-15.3(k)'
		for label in ['ecfr.gov/part-15?edition=current', 'ecfr.gov/part-15?edition=current#wrong', 'ecfr.gov/part-16?edition=current#p-15.3(k)', 'ecfr.gov/part-15#p-15.3(k)', 'other.gov/part-15?edition=current#p-15.3(k)']:
			self.assertIn('LINK-LABEL', self.findings(f'[{label}](<{target}>)'), label)
	# @used-by :mod:`unittest`
	def test_named_links_are_allowed_in_other_profiles_and_literals_are_preserved(self):
		text = '[The source](https://example.org/#p)'
		self.assertNotIn('LINK-LABEL', self.findings(text, 'markdown'))
		self.assertNotIn('LINK-LABEL', self.findings('`' + text + '`\n«' + text + '»\n> ' + text))
class SourceAdmissionTests(TextWorkspaceCase):
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :mod:`unittest`
	# @see :meth:`test_text_workflow.TextWorkspaceCase.setUp()`
	@override
	def setUp(self):
		super().setUp()
		self.url = 'https://example.org/rule#p'
		self.candidate = '1. Read ' + self.url + '.\n'
		self.target, self.op = self.start(self.candidate, changes='links')
	# @used-by :func:`agent_tools.cli_domains._op_prepare_experiment()`
	# @used-by :func:`agent_tools.cli_domains._op_prepare_review()`
	# @used-by :func:`agent_tools.cli_domains._op_question_add()`
	# @used-by :func:`agent_tools.cli_domains._op_record_experiment()`
	# @used-by :func:`agent_tools.text_cli.main()`
	# @used-by :meth:`SourceAdmissionTests.saved()`
	# @used-by :meth:`SourceAdmissionTests.test_a_200_redirect_to_a_challenge_is_not_the_intended_resource()`
	# @used-by :meth:`SourceAdmissionTests.test_a_later_failed_probe_cannot_be_overridden_by_minting_an_older_success()`
	# @used-by :meth:`SourceAdmissionTests.test_a_redirect_capture_cannot_substitute_for_requesting_a_different_citation()`
	# @used-by :meth:`SourceAdmissionTests.test_a_source_without_anchor_requires_an_actual_no_anchor_section()`
	# @used-by :meth:`SourceAdmissionTests.test_changing_candidate_does_not_erase_a_later_failure_of_the_same_url()`
	# @used-by :meth:`SourceAdmissionTests.test_documentation_anchor_cannot_exist_only_in_the_receipt()`
	# @used-by :meth:`SourceAdmissionTests.test_dom_fallback_needs_the_exact_captured_identity()`
	# @used-by :meth:`SourceAdmissionTests.test_explicit_canonical_redirect_still_requires_the_anchor_and_quote()`
	# @used-by :meth:`SourceAdmissionTests.test_http_500_wrong_anchor_and_wrong_quote_are_preserved_as_failed_receipts()`
	# @used-by :meth:`SourceAdmissionTests.test_m1_heading_band_wrapper_child_sentinel_and_github_user_content_anchors()`
	# @used-by :meth:`SourceAdmissionTests.test_m3_passive_cloudflare_jsd_script_is_admitted_while_real_interstitial_is_blocked()`
	# @used-by :meth:`SourceAdmissionTests.test_old_current_sources_expire_but_explicit_historical_editions_are_distinct()`
	# @used-by :meth:`SourceAdmissionTests.test_reviewer_can_collect_its_own_equal_bytes_without_invalidating_the_author()`
	# @used-by :meth:`SourceAdmissionTests.test_snapshot_replacement_does_not_verify_the_old_broken_citation()`
	# @used-by :meth:`SourceAdmissionTests.test_source_check_cli_preserves_success_and_failed_receipts_with_exit_codes()`
	# @used-by :meth:`SourceAdmissionTests.test_unicode_address_and_encoded_markdown_destination_share_one_identity()`
	def spec(self, *, url=None, body=None, status=200, final=None, kind='http'):
		url = url or self.url
		body = body or b'<h2 id="p">Rule</h2><p>Exact legal text.</p>'
		observation = collect(self.project, url, max_age=0, observation_kind=kind, fetcher=lambda *args: Response(final or args[0], status, 'text/html', body))
		r = {'url': url, 'currency': 'current', 'currency_basis': 'This exact captured page at the observed time.', 'evidence': {'source': url, 'observation': observation['observation'], 'source_sha256': observation['body_sha256'], 'quote': 'Exact legal text.', 'documentation': True, 'locator': {'type': 'anchor', 'value': 'p'}}}
		return r
	# @used-by :meth:`SourceAdmissionTests.test_a_200_redirect_to_a_challenge_is_not_the_intended_resource()`
	# @used-by :meth:`SourceAdmissionTests.test_a_later_failed_probe_cannot_be_overridden_by_minting_an_older_success()`
	# @used-by :meth:`SourceAdmissionTests.test_a_redirect_capture_cannot_substitute_for_requesting_a_different_citation()`
	# @used-by :meth:`SourceAdmissionTests.test_a_source_without_anchor_requires_an_actual_no_anchor_section()`
	# @used-by :meth:`SourceAdmissionTests.test_changing_candidate_does_not_erase_a_later_failure_of_the_same_url()`
	# @used-by :meth:`SourceAdmissionTests.test_documentation_anchor_cannot_exist_only_in_the_receipt()`
	# @used-by :meth:`SourceAdmissionTests.test_dom_fallback_needs_the_exact_captured_identity()`
	# @used-by :meth:`SourceAdmissionTests.test_exact_primary_quote_receipt_is_reused_without_network_and_apply_keeps_it()`
	# @used-by :meth:`SourceAdmissionTests.test_explicit_canonical_redirect_still_requires_the_anchor_and_quote()`
	# @used-by :meth:`SourceAdmissionTests.test_http_500_wrong_anchor_and_wrong_quote_are_preserved_as_failed_receipts()`
	# @used-by :meth:`SourceAdmissionTests.test_later_failure_invalidates_apply_and_an_already_applied_gate()`
	# @used-by :meth:`SourceAdmissionTests.test_m1_heading_band_wrapper_child_sentinel_and_github_user_content_anchors()`
	# @used-by :meth:`SourceAdmissionTests.test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids()`
	# @used-by :meth:`SourceAdmissionTests.test_m3_passive_cloudflare_jsd_script_is_admitted_while_real_interstitial_is_blocked()`
	# @used-by :meth:`SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
	# @used-by :meth:`SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
	# @used-by :meth:`SourceAdmissionTests.test_old_current_sources_expire_but_explicit_historical_editions_are_distinct()`
	# @used-by :meth:`SourceAdmissionTests.test_plain_authored_verified_objects_and_changed_candidates_are_rejected()`
	# @used-by :meth:`SourceAdmissionTests.test_primary_byte_or_metadata_change_invalidates_a_previously_valid_check()`
	# @used-by :meth:`SourceAdmissionTests.test_reviewer_approval_needs_a_receipt_bound_assessment_for_each_url()`
	# @used-by :meth:`SourceAdmissionTests.test_reviewer_can_collect_its_own_equal_bytes_without_invalidating_the_author()`
	# @used-by :meth:`SourceAdmissionTests.test_snapshot_replacement_does_not_verify_the_old_broken_citation()`
	# @used-by :meth:`SourceAdmissionTests.test_unicode_address_and_encoded_markdown_destination_share_one_identity()`
	# @used-by :meth:`SourceAdmissionTests.test_valid_dom_capture_identity_can_resolve_the_http_channel_failure()`
	def saved(self, spec=None, candidate=None):
		return text_sources.save_source_check(self.project, candidate or self.candidate, spec or self.spec())
	# @used-by :meth:`SourceAdmissionTests.test_a_later_failed_probe_cannot_be_overridden_by_minting_an_older_success()`
	# @used-by :meth:`SourceAdmissionTests.test_exact_primary_quote_receipt_is_reused_without_network_and_apply_keeps_it()`
	# @used-by :meth:`SourceAdmissionTests.test_http_500_wrong_anchor_and_wrong_quote_are_preserved_as_failed_receipts()`
	# @used-by :meth:`SourceAdmissionTests.test_later_failure_invalidates_apply_and_an_already_applied_gate()`
	# @used-by :meth:`SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
	# @used-by :meth:`SourceAdmissionTests.test_missing_source_checks_cannot_become_a_valid_mechanical_check()`
	# @used-by :meth:`SourceAdmissionTests.test_plain_authored_verified_objects_and_changed_candidates_are_rejected()`
	# @used-by :meth:`SourceAdmissionTests.test_primary_byte_or_metadata_change_invalidates_a_previously_valid_check()`
	# @used-by :meth:`SourceAdmissionTests.test_reviewer_can_collect_its_own_equal_bytes_without_invalidating_the_author()`
	# @used-by :meth:`SourceAdmissionTests.test_valid_dom_capture_identity_can_resolve_the_http_channel_failure()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.check_and_review()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_explicit_reconciled_baseline_preserves_history_without_granting_publication()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_failed_semantic_admission_is_not_granted_by_a_later_valid_apply()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_historical_successor_lineage_preserves_history_when_later_reviewer_trace_is_unverified()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_later_legitimate_applied_revision_does_not_invalidate_old_answer()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_proof_evidence_review_document_and_journal_changes_remain_conflicts()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_replaying_an_older_applied_target_is_not_a_later_legitimate_revision()`
	def checked(self, records):
		return text_workflow.check(self.project, self.op['id'], self.candidate, {'source_checks': records})
	# @used-by :meth:`SourceAdmissionTests.test_real_http_failure_and_redirect_are_saved_once_per_base_url()`
	# @used-by :meth:`SourceAdmissionTests.test_source_check_cli_preserves_success_and_failed_receipts_with_exit_codes()`
	# @see :meth:`test_agent_tools.TemporaryCase.cli()`
	@override
	def cli(self, *args):
		script = Path(__file__).resolve().parents[1] / 'scripts/df_text.py'
		r = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, timeout=30)
		return r
	# @used-by :mod:`unittest`
	def test_source_check_cli_preserves_success_and_failed_receipts_with_exit_codes(self):
		spec = self.spec()
		file = self.project_file('source.json', json.dumps(spec))
		valid = self.cli('source-check', self.project, '--candidate', self.target, '--spec', file)
		self.assertEqual(valid.returncode, 0, valid.stderr.decode('utf-8'))
		self.assertTrue(json.loads(valid.stdout)['valid'])
		spec['evidence']['quote'] = 'Absent from this captured page.'
		file.write_text(json.dumps(spec), encoding='utf-8')
		failed = self.cli('source-check', self.project, '--candidate', self.target, '--spec', file)
		self.assertEqual(failed.returncode, 1, failed.stderr.decode('utf-8'))
		result = json.loads(failed.stdout)
		self.assertFalse(result['valid'])
		self.assertTrue((self.project / result['source_check']).is_file())
	# @used-by :mod:`unittest`
	def test_missing_source_checks_cannot_become_a_valid_mechanical_check(self):
		result = self.checked([])
		self.assertFalse(result['valid'])
		self.assertIn('text.source_missing', codes(result))
	# @used-by :mod:`unittest`
	def test_unicode_address_and_encoded_markdown_destination_share_one_identity(self):
		self.url = 'https://example.org/\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442#\u0440\u0430\u0437\u0434\u0435\u043b'
		self.candidate = 'Read [\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442](<' + self.url + '>).'
		spec = self.spec(body='<h2 id="\u0440\u0430\u0437\u0434\u0435\u043b">Rule</h2><p>Exact legal text.</p>'.encode('utf-8'))
		spec['evidence']['locator']['value'] = '\u0440\u0430\u0437\u0434\u0435\u043b'
		saved = self.saved(spec)
		self.assertTrue(saved['valid'], saved['issues'])
		self.assertEqual(text_sources.source_urls(self.candidate), [self.url])
		self.assertFalse(text_sources.validate_source_checks(self.project, self.candidate, [saved['source_check']])['issues'])
	# @used-by :mod:`unittest`
	def test_exact_primary_quote_receipt_is_reused_without_network_and_apply_keeps_it(self):
		saved = self.saved()
		self.assertTrue(saved['valid'], saved)
		with patch('agent_tools.research.fetch', side_effect=AssertionError('No new network during check/apply')):
			checked = self.checked([saved['source_check']])
			self.assertTrue(checked['valid'], checked['issues'])
			applied = text_workflow.apply(self.project, checked['check'])
			self.assertEqual(applied['source_checks'], [saved['source_check']])
			self.assertTrue(text_workflow.gate(self.project)['valid'])
		self.assertTrue(any((path.endswith('response.bin') for path in checked['inputs'])))
	# @used-by :mod:`unittest`
	def test_http_500_wrong_anchor_and_wrong_quote_are_preserved_as_failed_receipts(self):
		for spec in [self.spec(status=500), self.spec(body=b'<h2 id="other">Rule</h2><p>Exact legal text.</p>'), self.spec(body=b'<h2 id="p">Rule</h2><p>Different legal text.</p>')]:
			failed = self.saved(spec)
			self.assertFalse(failed['valid'])
			self.assertFalse(self.checked([failed['source_check']])['valid'])
	# @used-by :mod:`unittest`
	def test_a_200_redirect_to_a_challenge_is_not_the_intended_resource(self):
		failed = self.saved(self.spec(final='https://unblock.example.org/'))
		self.assertFalse(failed['valid'])
		self.assertIn('Final URL', ' '.join(failed['issues']))
	# @used-by :mod:`unittest`
	def test_explicit_canonical_redirect_still_requires_the_anchor_and_quote(self):
		spec = self.spec(final='https://example.org/canonical')
		spec['expected_final_url'] = 'https://example.org/canonical'
		self.assertTrue(self.saved(spec)['valid'])
		bad = deepcopy(spec)
		bad['evidence']['quote'] = 'Not in the primary document.'
		self.assertFalse(self.saved(bad)['valid'])
	# @used-by :mod:`unittest`
	def test_a_redirect_capture_cannot_substitute_for_requesting_a_different_citation(self):
		spec = self.spec(final='https://example.org/canonical')
		self.url = 'https://example.org/canonical#p'
		self.candidate = 'Read ' + self.url
		spec['url'] = self.url
		spec['evidence']['source'] = self.url
		failed = self.saved(spec)
		self.assertFalse(failed['valid'])
		self.assertIn('Requested URL', ' '.join(failed['issues']))
	# @used-by :mod:`unittest`
	def test_plain_authored_verified_objects_and_changed_candidates_are_rejected(self):
		saved = self.saved()
		self.assertFalse(self.checked([{'url': self.url, 'valid': True}])['valid'])
		with self.assertRaisesRegex(ValueError, 'another candidate'):
			text_sources.read_source_check(self.project, self.candidate + 'Changed.', saved['source_check'])
	# @used-by :mod:`unittest`
	def test_primary_byte_or_metadata_change_invalidates_a_previously_valid_check(self):
		saved = self.saved()
		checked = self.checked([saved['source_check']])
		meta = self.project / 'ꘖ/KB' / saved['spec']['evidence']['observation']
		meta.with_name('response.bin').write_bytes(b'Changed original source')
		with self.assertRaisesRegex(ValueError, 'stale or failed'):
			text_workflow.refresh_check(self.project, checked['check'])
	# @used-by :mod:`unittest`
	def test_a_later_failed_probe_cannot_be_overridden_by_minting_an_older_success(self):
		spec = self.spec()
		saved = self.saved(spec)
		self.assertTrue(self.checked([saved['source_check']])['valid'])
		probe = text_sources.probe_links(self.project, self.candidate, fetcher=lambda *args: Response(args[0], 500, 'text/html', b'Internal server error'))
		self.assertTrue(probe['findings'])
		self.assertFalse(self.checked([saved['source_check']])['valid'])
		self.assertFalse(self.saved(spec)['valid'])
		refreshed = self.saved(self.spec())
		self.assertTrue(self.checked([refreshed['source_check']])['valid'])
	# @used-by :mod:`unittest`
	def test_changing_candidate_does_not_erase_a_later_failure_of_the_same_url(self):
		spec = self.spec()
		self.saved(spec)
		text_sources.probe_links(self.project, self.candidate, fetcher=lambda *args: Response(args[0], 500, 'text/html', b'Internal server error'))
		self.assertFalse(self.saved(spec, self.candidate + '\n')['valid'])
	# @used-by :mod:`unittest`
	def test_later_failure_invalidates_apply_and_an_already_applied_gate(self):
		checked = self.checked([self.saved()['source_check']])
		text_sources.probe_links(self.project, self.candidate, fetcher=lambda *args: Response(args[0], 500, 'text/html', b'Internal server error'))
		with self.assertRaisesRegex(ValueError, 'stale or failed'):
			text_workflow.apply(self.project, checked['check'])
		refreshed = self.checked([self.saved()['source_check']])
		text_workflow.apply(self.project, refreshed['check'])
		text_sources.probe_links(self.project, self.candidate, fetcher=lambda *args: Response(args[0], 500, 'text/html', b'Internal server error'))
		with self.assertRaisesRegex(ValueError, 'newer conflicting'):
			text_workflow.gate(self.project)
	# @used-by :mod:`unittest`
	def test_snapshot_replacement_does_not_verify_the_old_broken_citation(self):
		different = self.spec(url='https://example.org/other#p')
		self.assertFalse(self.saved(different)['valid'])
	# @used-by :mod:`unittest`
	def test_a_source_without_anchor_requires_an_actual_no_anchor_section(self):
		self.url = 'https://example.org/rule'
		self.candidate = '1. Read [rule](' + self.url + ').\n'
		spec = self.spec(body=b'<h2>Rule</h2><p>Exact legal text.</p>')
		ref = spec['evidence']
		ref['locator'] = {'type': 'text', 'value': 'Exact legal text.'}
		ref['anchor_exception'] = {'section': 'Rule', 'observation': ref['observation']}
		self.assertTrue(self.saved(spec)['valid'])
		bad = self.spec()
		bad['evidence']['locator'] = {'type': 'text', 'value': 'Exact legal text.'}
		bad['evidence']['anchor_exception'] = {'section': 'Rule', 'observation': bad['evidence']['observation']}
		self.assertFalse(self.saved(bad)['valid'])
	# @used-by :mod:`unittest`
	def test_documentation_anchor_cannot_exist_only_in_the_receipt(self):
		self.url = 'https://example.org/rule'
		self.candidate = 'Read ' + self.url
		failed = self.saved(self.spec())
		self.assertFalse(failed['valid'])
		self.assertIn('cited URL itself', ' '.join(failed['issues']))
	# @used-by :mod:`unittest`
	def test_old_current_sources_expire_but_explicit_historical_editions_are_distinct(self):
		spec = self.spec()
		class Later(datetime):
			# @used-by :meth:`SourceAdmissionTests.test_old_current_sources_expire_but_explicit_historical_editions_are_distinct()`
			@classmethod
			def now(cls, tz=None):
				return datetime.now(timezone.utc) + timedelta(days=2)
		with patch('agent_tools.text_sources.datetime', Later):
			self.assertFalse(self.saved(spec)['valid'])
			spec.update(currency='historical', edition='2024 edition', currency_basis='An explicitly historical comparison only.')
			self.assertTrue(self.saved(spec)['valid'])
	# @used-by :mod:`unittest`
	def test_dom_fallback_needs_the_exact_captured_identity(self):
		spec = self.spec(kind='dom')
		self.assertFalse(self.saved(spec)['valid'])
	# @used-by :mod:`unittest`
	def test_valid_dom_capture_identity_can_resolve_the_http_channel_failure(self):
		from agent_tools.storage import create_bytes
		text_sources.probe_links(self.project, self.candidate, fetcher=lambda *args: Response(args[0], 403, 'text/html', b'Forbidden'))
		identity = {'schema_version': 1, 'session_id': 'fixture-session', 'target_id': 'fixture-tab', 'browser_websocket': 'ws://127.0.0.1/fixture', 'profile': {'name': 'fixture', 'status': 'verified'}, 'account': None, 'observed_at': datetime.now(timezone.utc).isoformat()}
		raw = json_data(identity)
		path = self.project / 'ꘖ/KB/Evidence/CDPSessions' / (digest(raw) + '.json')
		path.parent.mkdir(parents=True)
		create_bytes(path, raw)
		reference = path.relative_to(self.project / 'ꘖ/KB').as_posix()
		observation = collect(self.project, self.url, max_age=0, observation_kind='dom', scope=f'CDP-session:fixture-session:tab:fixture-tab:identity:{reference}', context={'session_id': 'fixture-session'}, fetcher=lambda *args: Response(args[0], 0, 'text/html', b'<h2 id="p">Rule</h2><p>Exact legal text.</p>'))
		spec = {'url': self.url, 'currency': 'current', 'currency_basis': 'Explicit read-only DOM test fixture.', 'cdp_identity': reference, 'evidence': {'source': self.url, 'observation': observation['observation'], 'source_sha256': observation['body_sha256'], 'documentation': True, 'quote': 'Exact legal text.', 'locator': {'type': 'anchor', 'value': 'p'}}}
		result = self.saved(spec)
		self.assertTrue(result['valid'], result['issues'])
		self.assertTrue(self.checked([result['source_check']])['valid'])
		# 2026-11-16
		# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
		# https://github.com/dmitry-ai/harness/issues/81
		unver_id = {**identity, 'profile': {'name': 'fixture'}}
		unver_raw = json_data(unver_id)
		unver_path = self.project / 'ꘖ/KB/Evidence/CDPSessions' / (digest(unver_raw) + '.json')
		create_bytes(unver_path, unver_raw)
		unver_ref = unver_path.relative_to(self.project / 'ꘖ/KB').as_posix()
		unver_obs = collect(self.project, self.url, max_age=0, observation_kind='dom', scope=f'CDP-session:fixture-session:tab:fixture-tab:identity:{unver_ref}', context={'session_id': 'fixture-session'}, fetcher=lambda *args: Response(args[0], 0, 'text/html', b'<h2 id="p">Rule</h2><p>Exact legal text.</p>'))
		unver_spec = {**spec, 'cdp_identity': unver_ref, 'evidence': {**spec['evidence'], 'observation': unver_obs['observation'], 'source_sha256': unver_obs['body_sha256']}}
		self.assertFalse(self.saved(unver_spec)['valid'])
	# @used-by :mod:`unittest`
	def test_reviewer_approval_needs_a_receipt_bound_assessment_for_each_url(self):
		saved = self.saved()
		package = {'source_checks': [saved['source_check']]}
		data = {'result': 'approved'}
		with self.assertRaisesRegex(ValueError, 'every external source'):
			text_review._source_reviews(self.project, data, package, self.candidate)
		data['source_reviews'] = [{'url': self.url, 'receipt': saved['source_check'], 'assessment': 'The exact quote and anchor establish this narrow statement in this edition.', 'outcome': 'supported'}]
		self.assertTrue(text_review._source_reviews(self.project, data, package, self.candidate))
		data['source_reviews'][0]['outcome'] = 'unsupported'
		with self.assertRaisesRegex(ValueError, 'unsupported'):
			text_review._source_reviews(self.project, data, package, self.candidate)
	# @used-by :mod:`unittest`
	def test_reviewer_can_collect_its_own_equal_bytes_without_invalidating_the_author(self):
		author = self.saved()
		independent = self.saved(self.spec())
		package = {'source_checks': [author['source_check']]}
		report = {'result': 'approved', 'source_reviews': [{'url': self.url, 'receipt': independent['source_check'], 'assessment': 'Independent bytes, same exact quote and section.', 'outcome': 'supported'}]}
		self.assertTrue(text_review._source_reviews(self.project, report, package, self.candidate))
		self.assertTrue(self.checked([author['source_check']])['valid'])
	# @used-by :mod:`unittest`
	def test_full_native_review_fixture_requires_and_preserves_source_assessments(self):
		from test_text_integration import TextReviewTests
		import uuid
		fixture = TextReviewTests()
		fixture.setUp()
		self.addCleanup(fixture.doCleanups)
		fixture.candidate = '1. The captured page contains Alternative: https://example.org/source.\n'
		registry = json.loads((fixture.project / 'ꘖ/KB/TextClaims.json').read_text(encoding='utf-8'))
		ref = deepcopy(registry['facts'][0]['evidence'][0])
		ref['documentation'] = False
		source = text_sources.save_source_check(fixture.project, fixture.candidate, {'url': ref['source'], 'currency': 'current', 'currency_basis': 'Current synthetic page capture.', 'evidence': ref})
		self.assertTrue(source['valid'], source)
		manifest = fixture.manifest(fixture.candidate)
		manifest['source_checks'] = [source['source_check']]
		fixture.checked = text_workflow.check(fixture.project, fixture.op['id'], fixture.candidate, manifest)
		self.assertTrue(fixture.checked['valid'], fixture.checked['issues'])
		package = fixture.package()
		with self.assertRaisesRegex(ValueError, 'every external source'):
			fixture.record_fixture(package)
		report = fixture.report(package)
		report['source_reviews'] = [{'url': ref['source'], 'receipt': source['source_check'], 'assessment': 'Literal saved page content; this is not a causal or execution claim.', 'outcome': 'supported'}]
		reviewer = str(uuid.uuid4())
		final = json.dumps(report, ensure_ascii=False)
		native = {'surface': 'codex-ui', 'status': 'completed', 'parent_id': fixture.parent, 'reviewer_id': reviewer, 'final_response': final, 'final_response_sha256': digest(final.encode())}
		native_path = fixture.project_file('ꘖ/KB/Evidence/Reviews/' + reviewer + '.json', json.dumps(native))
		with patch('agent_tools.metrics.verify_native_proof', return_value=native):
			entry = text_review.record(fixture.project, final.encode(), parent_id=fixture.parent, reviewer_id=reviewer, native_evidence=native_path.relative_to(fixture.project).as_posix())
			applied = text_workflow.apply(fixture.project, fixture.checked['check'])
		self.assertEqual(applied['status'], 'applied')
		self.assertTrue(any((path.endswith('response.bin') for path in entry['proof'])))
	# @used-by :mod:`unittest`
	def test_real_http_failure_and_redirect_are_saved_once_per_base_url(self):
		hits = []
		class Handler(BaseHTTPRequestHandler):
			# @used-by :meth:`SourceAdmissionTests.test_real_http_failure_and_redirect_are_saved_once_per_base_url()`
			def do_GET(self):
				hits.append(self.path)
				if '/redirect' == self.path:
					self.send_response(302)
					self.send_header('Location', '/challenge')
					self.end_headers()
				else:
					self.send_response(500 if '/bad' == self.path else 200)
					self.send_header('Content-Type', 'text/html')
					self.end_headers()
					self.wfile.write(b'<h2 id="p">Rule</h2><p>Exact legal text.</p>')
			# @used-by :meth:`SourceAdmissionTests.test_real_http_failure_and_redirect_are_saved_once_per_base_url()`
			def log_message(self, *args):
				pass
		server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
		thread = Thread(target=server.serve_forever, daemon=True)
		thread.start()
		try:
			base = f'http://127.0.0.1:{server.server_port}'
			result = text_sources.probe_links(self.project, f'[a]({base}/good#p) [b]({base}/good#absent) [c]({base}/bad) [d]({base}/redirect#p)')
			self.assertEqual(hits.count('/good'), 1)
			self.assertIn('unavailable', {r['status'] for r in result['results']})
			self.assertIn('redirect-unverified', {r['status'] for r in result['results']})
			self.assertIn('anchor-unverified', {r['status'] for r in result['results']})
			self.assertTrue(all(((self.project / r['probe']).is_file() for r in result['results'])))
			candidate = self.project_file('network-candidate.md', f'1. Read {base}/bad.\n')
			missing = self.cli('lint', candidate, '--kind', 'proposal', '--network', '--json')
			self.assertEqual(missing.returncode, 2)
			failed = self.cli('lint', candidate, '--kind', 'proposal', '--network', '--project', self.project, '--json')
			self.assertEqual(failed.returncode, 1, failed.stderr.decode('utf-8'))
			self.assertIn(b'SOURCE-UNVERIFIED', failed.stdout)
			probes = [json.loads(path.read_text(encoding='utf-8')) for path in (self.project / 'ꘖ/data/texts/sources').glob('*-probe.json')]
			self.assertTrue(any((p['candidate_sha256'] == digest(candidate.read_bytes()) and 500 == p['http_status'] for p in probes)))
		finally:
			server.shutdown()
			thread.join()
			server.server_close()
	# 2026-11-16
	# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
	# https://github.com/dmitry-ai/harness/issues/81
	# @used-by :mod:`unittest`
	def test_m1_heading_band_wrapper_child_sentinel_and_github_user_content_anchors(self):
		html_body = (
			'<div id="testEvents"><h2>Test Events Tool</h2></div>'
			'<p>Use the Test Events tool to verify server events with test_event_code.</p>'
			'<div class="markdown-heading"><h2 class="heading-element">Empty Header</h2><a id="user-content-empty-header" class="anchor" href="#empty-header">#</a></div>'
			'<div class="markdown-heading"><h2 class="heading-element">Server Events</h2><a id="user-content-server-events" class="anchor" href="#server-events">#</a></div>'
			'<p>Send Conversions API events directly from your backend.</p>'
			'<h2><a id="child-id"></a>Child Heading</h2><p>Child section quote.</p>'
			'<a name="legacy-id"></a><h2>Legacy Heading</h2><p>Legacy section quote.</p>'
			'<h2>Post Heading</h2><a id="post-id"></a><p>Post section quote.</p>'
		).encode('utf-8')
		for frag, quote in (
			('testEvents', 'Use the Test Events tool to verify server events with test_event_code.'),
			('server-events', 'Send Conversions API events directly from your backend.'),
			('user-content-server-events', 'Send Conversions API events directly from your backend.'),
			('child-id', 'Child section quote.'),
			('legacy-id', 'Legacy section quote.'),
			('post-id', 'Post section quote.'),
		):
			url = f'https://example.org/docs#{frag}'
			cand = f'1. Read {url}.\n'
			spec = self.spec(url=url, body=html_body)
			spec['evidence']['quote'] = quote
			spec['evidence']['locator'] = {'type': 'anchor', 'value': frag}
			res = self.saved(spec, cand)
			self.assertTrue(res['valid'], (frag, res['issues']))
		wrong_url = 'https://example.org/docs#testEvents'
		wrong_cand = f'1. Read {wrong_url}.\n'
		wrong_spec = self.spec(url=wrong_url, body=html_body)
		wrong_spec['evidence']['quote'] = 'Send Conversions API events directly from your backend.'
		wrong_spec['evidence']['locator'] = {'type': 'anchor', 'value': 'testEvents'}
		self.assertFalse(self.saved(wrong_spec, wrong_cand)['valid'])
		no_frag_url = 'https://example.org/docs'
		no_frag_cand = f'1. Read [docs]({no_frag_url}).\n'
		exc_spec = self.spec(url=no_frag_url, body=html_body)
		exc_spec['evidence']['quote'] = 'Use the Test Events tool to verify server events with test_event_code.'
		exc_spec['evidence']['locator'] = {'type': 'text', 'value': exc_spec['evidence']['quote']}
		exc_spec['evidence']['anchor_exception'] = {'section': 'Test Events Tool', 'observation': exc_spec['evidence']['observation']}
		exc_res = self.saved(exc_spec, no_frag_cand)
		self.assertFalse(exc_res['valid'])
		self.assertIn('available anchor', ' '.join(exc_res['issues']))
		root_wrapped_html = b'<html id="facebook"><body id="mount_0_0"><main id="doc-root"><h1>Overview</h1><p>Intro text.</p><h2>Unanchored Section</h2><p>Truly unanchored section text.</p><section id="wrapped-sec"><h2>Wrapped Section</h2><p>Wrapped section text.</p></section></main></body></html>'
		unanchored_spec = self.spec(url=no_frag_url, body=root_wrapped_html)
		unanchored_spec['evidence']['quote'] = 'Truly unanchored section text.'
		unanchored_spec['evidence']['locator'] = {'type': 'text', 'value': 'Truly unanchored section text.'}
		unanchored_spec['evidence']['anchor_exception'] = {'section': 'Unanchored Section', 'observation': unanchored_spec['evidence']['observation']}
		self.assertTrue(self.saved(unanchored_spec, no_frag_cand)['valid'])
		wrapped_exc = self.spec(url=no_frag_url, body=root_wrapped_html)
		wrapped_exc['evidence']['quote'] = 'Wrapped section text.'
		wrapped_exc['evidence']['locator'] = {'type': 'text', 'value': 'Wrapped section text.'}
		wrapped_exc['evidence']['anchor_exception'] = {'section': 'Wrapped Section', 'observation': wrapped_exc['evidence']['observation']}
		self.assertFalse(self.saved(wrapped_exc, no_frag_cand)['valid'])
		edge_html = (
			'<head><style id="jss">body{}</style></head><body>'
			'<div id="fb-root"></div>'
			'<header id="hero"><h1>Title</h1><p>Subtitle</p></header>'
			'<h2>Pricing</h2><p>Secret pricing text.</p>'
			'<section id="sec-a"><h2>Section A</h2><p>Inside section A.</p><article id="c1"><p>Narrow comment.</p></article></section><p>Outside section A.</p>'
			'<h2>Section 1</h2><p>Prose <a id="p1-end"></a></p><div id="mount"></div>'
			'<div class="markdown-heading"><h2>Empty</h2><a id="post-empty">#</a></div>'
			'<h2>Section 2</h2><p>Sec 2 quote.</p>'
			'<div id="foo"><p>Sidebar</p></div><div class="markdown-heading"><h2>Foo</h2><a id="user-content-foo">#</a></div><p>Main foo body.</p>'
			'</body>'
		).encode('utf-8')
		for bad_frag, bad_q in (('hero', 'Secret pricing text.'), ('sec-a', 'Outside section A.'), ('c1', 'Inside section A.'), ('p1-end', 'Sec 2 quote.'), ('post-empty', 'Sec 2 quote.'), ('foo', 'Main foo body.')):
			b_url = f'https://example.org/edge#{bad_frag}'
			b_spec = self.spec(url=b_url, body=edge_html)
			b_spec['evidence'].update(quote=bad_q, locator={'type': 'anchor', 'value': bad_frag})
			self.assertFalse(self.saved(b_spec, f'1. {b_url}\n')['valid'], bad_frag)
		for ok_frag, ok_q in (('sec-a', 'Inside section A.'), ('c1', 'Narrow comment.'), ('user-content-foo', 'Main foo body.')):
			g_url = f'https://example.org/edge#{ok_frag}'
			g_spec = self.spec(url=g_url, body=edge_html)
			g_spec['evidence'].update(quote=ok_q, locator={'type': 'anchor', 'value': ok_frag})
			self.assertTrue(self.saved(g_spec, f'1. {g_url}\n')['valid'], ok_frag)
		edge_base = 'https://example.org/edge'
		edge_cand = f'1. Read [edge]({edge_base}).\n'
		outside_exc = self.spec(url=edge_base, body=edge_html)
		outside_exc['evidence'].update(quote='Outside section A.', locator={'type': 'text', 'value': 'Outside section A.'}, anchor_exception={'section': 'Section A', 'observation': outside_exc['evidence']['observation']})
		self.assertTrue(self.saved(outside_exc, edge_cand)['valid'])
		inside_exc = self.spec(url=edge_base, body=edge_html)
		inside_exc['evidence'].update(quote='Inside section A.', locator={'type': 'text', 'value': 'Inside section A.'}, anchor_exception={'section': 'Section A', 'observation': inside_exc['evidence']['observation']})
		self.assertFalse(self.saved(inside_exc, edge_cand)['valid'])
		head_mount_html = b'<html><head><style id="jss">body{}</style><script id="boot"></script></head><body><div id="fb-root"></div><h1>Overview</h1><p>Unanchored overview text.</p></body></html>'
		hm_spec = self.spec(url=edge_base, body=head_mount_html)
		hm_spec['evidence'].update(quote='Unanchored overview text.', locator={'type': 'text', 'value': 'Unanchored overview text.'}, anchor_exception={'section': 'Overview', 'observation': hm_spec['evidence']['observation']})
		self.assertTrue(self.saved(hm_spec, edge_cand)['valid'])
	# 2026-11-16
	# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
	# https://github.com/dmitry-ai/harness/issues/81
	# @used-by :mod:`unittest`
	def test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids(self):
		from agent_tools.links import Page, check_network
		seen_headers = {}
		md_body = (
			'---\ntitle: Consent Mode Guide\n---\n'
			'# Consent Mode Guide\n'
			'---\n'
			'## Server Events &#123;#test-events&#125;\n'
			'Verify payloads using &#96;test_event_code&#96; in Events Manager.\n'
			'```html\n<div id="fenced-fake">Fake</div>\n```\n'
			'---\n'
			'## Intro {#setup}\n'
			'Explicit setup section quote.\n'
			'## Setup\n'
			'Auto-deduplicated setup-1 section quote.\n'
			'## Implementation {#implementation}\n'
			'Configure default consent states before tags fire.\n'
		).encode('utf-8')
		# @used-by :meth:`SourceAdmissionTests.test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids()`
		def md_fetcher(req_url, headers, timeout):
			seen_headers.update(headers)
			return Response(req_url, 200, 'text/markdown', md_body)
		for frag, quote in (
			('test-events', 'Verify payloads using `test_event_code` in Events Manager.'),
			('server-events', 'Verify payloads using `test_event_code` in Events Manager.'),
			('setup', 'Explicit setup section quote.'),
			('setup-1', 'Auto-deduplicated setup-1 section quote.'),
			('implementation', 'Configure default consent states before tags fire.'),
		):
			url = f'https://example.org/consent#{frag}'
			cand = f'1. See {url}.\n'
			obs = collect(self.project, url, max_age=0, fetcher=md_fetcher)
			self.assertIn('text/markdown', seen_headers.get('Accept', ''))
			spec = {'url': url, 'currency': 'current', 'currency_basis': 'Current Markdown documentation.', 'evidence': {'source': url, 'observation': obs['observation'], 'source_sha256': obs['body_sha256'], 'quote': quote, 'documentation': True, 'locator': {'type': 'anchor', 'value': frag}}}
			res = self.saved(spec, cand)
			self.assertTrue(res['valid'], (frag, res['issues']))
		wrong_sec_spec = {'url': 'https://example.org/consent#setup', 'currency': 'current', 'currency_basis': 'Wrong section.', 'evidence': {'source': 'https://example.org/consent#setup', 'observation': obs['observation'], 'source_sha256': obs['body_sha256'], 'quote': 'Auto-deduplicated setup-1 section quote.', 'documentation': True, 'locator': {'type': 'anchor', 'value': 'setup'}}}
		self.assertFalse(self.saved(wrong_sec_spec, '1. See https://example.org/consent#setup.\n')['valid'])
		fenced_spec = {'url': 'https://example.org/consent#fenced-fake', 'currency': 'current', 'currency_basis': 'Code block fake id.', 'evidence': {'source': 'https://example.org/consent#fenced-fake', 'observation': obs['observation'], 'source_sha256': obs['body_sha256'], 'quote': 'Fake', 'documentation': True, 'locator': {'type': 'anchor', 'value': 'fenced-fake'}}}
		self.assertFalse(self.saved(fenced_spec, '1. See https://example.org/consent#fenced-fake.\n')['valid'])
		dom_seen = {}
		# @used-by :meth:`SourceAdmissionTests.test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids()`
		def dom_hdr_fetcher(req_url, headers, timeout):
			dom_seen.update(headers)
			return Response(req_url, 0, 'text/html', b'<h1>DOM</h1>')
		collect(self.project, 'https://example.org/dom-hdr', max_age=0, observation_kind='dom', fetcher=dom_hdr_fetcher)
		self.assertNotIn('Accept', dom_seen)
		net_res = check_network(['https://example.org/consent#test-events', 'https://example.org/consent#fenced-fake'], anchors=True, fetcher=lambda u, t: Page(u, 200, 'text/markdown', md_body.decode('utf-8')))
		self.assertEqual({r['url']: r['status'] for r in net_res}, {'https://example.org/consent#test-events': 'found-in-source', 'https://example.org/consent#fenced-fake': 'not-found-in-source'})
		probe = text_sources.probe_links(self.project, '[ok](https://example.org/consent#test-events) [bad](https://example.org/consent#missing)', fetcher=md_fetcher)
		statuses = {item['url']: item['status'] for item in probe['results']}
		self.assertEqual(statuses['https://example.org/consent#test-events'], 'http-ok')
		self.assertEqual(statuses['https://example.org/consent#missing'], 'anchor-unverified')
	# 2026-11-16
	# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
	# https://github.com/dmitry-ai/harness/issues/81
	# @used-by :mod:`unittest`
	def test_m3_passive_cloudflare_jsd_script_is_admitted_while_real_interstitial_is_blocked(self):
		from agent_tools.research import classify_html_challenge
		passive_cf_html = (
			'<!DOCTYPE html><html><head><title>Daniel M. - GTM & Meta CAPI Specialist</title></head><body>'
			'<noscript>Enable JavaScript and cookies to continue</noscript>'
			'<main id="history"><h1>Work History</h1><p>Completed server-side GTM and Meta Conversions API setup with 5.0 rating.</p></main>'
			'<script src="/cdn-cgi/challenge-platform/h/b/scripts/jsd/991413702c0a/main.js"></script>'
			'<script>window.__CF$cv$params={r:"99a1b2c3",t:"MTc2"};</script>'
			'</body></html>'
		).encode('utf-8')
		prof_url = 'https://example.org/freelancers/~01abcdef#history'
		prof_cand = f'1. Profile: {prof_url}.\n'
		prof_spec = self.spec(url=prof_url, body=passive_cf_html)
		prof_spec['evidence'].update(documentation=False, quote='Completed server-side GTM and Meta Conversions API setup with 5.0 rating.', locator={'type': 'anchor', 'value': 'history'})
		prof_res = self.saved(prof_spec, prof_cand)
		self.assertTrue(prof_res['valid'], prof_res['issues'])
		doc_about_cf = (
			'<!DOCTYPE html><html><head><title>Troubleshooting Anti-Bot Challenges</title></head><body>'
			'<h1 id="guide">Handling Cloudflare Interstitials</h1>'
			'<p>When an origin returns an interstitial page containing <code>window._cf_chl_opt</code>, <code>challenge-platform</code>, or <code>Verify you are human</code>, capture the rendered DOM via headless browser.</p>'
			'</body></html>'
		).encode('utf-8')
		doc_url = 'https://example.org/cf-guide#guide'
		doc_cand = f'1. Guide: {doc_url}.\n'
		doc_spec = self.spec(url=doc_url, body=doc_about_cf)
		doc_spec['evidence'].update(documentation=True, quote='capture the rendered DOM via headless browser.', locator={'type': 'anchor', 'value': 'guide'})
		self.assertTrue(self.saved(doc_spec, doc_cand)['valid'])
		real_challenge = (
			'<!DOCTYPE html><html><head><title>Just a moment...</title></head><body>'
			'<div id="history"><div id="challenge-running">Checking your browser before accessing example.org.</div></div>'
			'<script>window._cf_chl_opt={cvId:"3"};</script>'
			'</body></html>'
		).encode('utf-8')
		chal_spec = self.spec(url=prof_url, body=real_challenge)
		chal_spec['evidence'].update(documentation=False, quote='Checking your browser', locator={'type': 'anchor', 'value': 'history'})
		chal_res = self.saved(chal_spec, prof_cand)
		self.assertFalse(chal_res['valid'])
		self.assertIn('Challenge page', ' '.join(chal_res['issues']))
		self.assertTrue(classify_html_challenge('<html><body><div id="app"></div><noscript>Enable JavaScript to run this app.</noscript></body></html>'))
		self.assertFalse(classify_html_challenge('<html><body><pre>{"event_name":"Purchase","value":120}</pre></body></html>'))
		self.assertTrue(classify_html_challenge('<html><head><title>Un instant...</title></head><body><p>V\u00e9rification de la s\u00e9curit\u00e9 de votre connexion avant d\'acc\u00e9der au site.</p><script>window._cf_chl_opt={cvId:"3"};</script></body></html>', status=None))
	# 2026-11-16
	# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
	# https://github.com/dmitry-ai/harness/issues/81
	# @used-by :mod:`unittest`
	def test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance(self):
		from agent_tools.research import collect_browser, load_observation
		from agent_tools.text_browser import save_cdp_identity
		pub_url = 'https://example.org/public-dom#sec'
		pub_cand = f'1. Public DOM: {pub_url}.\n'
		collect(self.project, pub_url, scope='public', observation_kind='dom', fetcher=lambda *a: Response(a[0], 0, 'text/html', b'<h2 id="sec">Section</h2><p>Legacy cached without cdp_identity.</p>'))
		# @used-by :meth:`SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
		def fake_headless_fetcher(proj_root, target, **kwargs):
			id_ref, id_sha = save_cdp_identity(proj_root, {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(), 'endpoint': 'http://127.0.0.1:54321', 'browser': 'HeadlessChrome/139.0', 'browser_websocket': 'ws://127.0.0.1:54321/devtools/browser/1', 'target_id': 'HEADLESS-TAB-1', 'target_mode': 'ephemeral_headless_context', 'closed_after_capture': True, 'profile': {'status': 'verified', 'mode': 'ephemeral_headless_shell'}})
			return {'url': target, 'html': '<h2 id="sec">Section</h2><p>Rendered headless quote.</p>', 'title': 'Public DOM', 'target_id': 'HEADLESS-TAB-1', 'target_mode': 'ephemeral_headless_context', 'closed_after_capture': True, 'cdp_identity': id_ref, 'cdp_identity_sha256': id_sha, 'endpoint': 'http://127.0.0.1:54321'}
		dom_obs = collect_browser(self.project, pub_url, cdp_fetcher=fake_headless_fetcher)
		self.assertFalse(dom_obs['cached'])
		cached_obs = collect_browser(self.project, pub_url, cdp_fetcher=fake_headless_fetcher)
		self.assertTrue(cached_obs['cached'])
		self.assertEqual(cached_obs.get('cdp_identity'), dom_obs['cdp_identity'])
		self.assertEqual(load_observation(self.project, dom_obs['observation']).get('cdp_identity'), dom_obs['cdp_identity'])
		pub_spec = {'url': pub_url, 'currency': 'current', 'currency_basis': 'Current isolated headless DOM capture.', 'cdp_identity': dom_obs['cdp_identity'], 'evidence': {'source': pub_url, 'observation': dom_obs['observation'], 'source_sha256': load_observation(self.project, dom_obs['observation'])['body_sha256'], 'documentation': True, 'quote': 'Rendered headless quote.', 'locator': {'type': 'anchor', 'value': 'sec'}}}
		pub_res = self.saved(pub_spec, pub_cand)
		self.assertTrue(pub_res['valid'], pub_res['issues'])
		self.assertTrue(text_sources.source_integrity(self.project, pub_cand, pub_res['source_check'])['source_check'])
		self.assertTrue(text_review._source_reviews(self.project, {'result': 'approved', 'source_reviews': [{'url': pub_url, 'receipt': pub_res['source_check'], 'assessment': 'Verified isolated DOM receipt.', 'outcome': 'supported'}]}, {'source_checks': [pub_res['source_check']]}, pub_cand))
		auth_url = 'https://example.org/auth-dom#sec'
		auth_cand = f'1. Auth DOM: {auth_url}.\n'
		# @used-by :meth:`SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
		def fake_auth_fetcher(proj_root, target, **kwargs):
			id_ref, id_sha = save_cdp_identity(proj_root, {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(), 'session_id': 'chrome-default', 'endpoint': 'http://127.0.0.1:9222', 'browser': 'Chrome/142.0', 'browser_websocket': 'ws://127.0.0.1:9222/devtools/browser/2', 'target_id': 'AUTH-TAB-2', 'target_mode': 'm2a_extension_background_tab', 'closed_after_capture': True, 'profile': {'status': 'verified', 'name': 'Default'}})
			return {'url': target, 'html': '<h2 id="sec">Auth</h2><p>Authenticated profile quote.</p>', 'title': 'Auth DOM', 'target_id': 'AUTH-TAB-2', 'target_mode': 'm2a_extension_background_tab', 'closed_after_capture': True, 'cdp_identity': id_ref, 'cdp_identity_sha256': id_sha, 'endpoint': 'http://127.0.0.1:9222'}
		auth_obs = collect_browser(self.project, auth_url, session_id='chrome-default', cdp_fetcher=fake_auth_fetcher)
		auth_spec = {'url': auth_url, 'currency': 'current', 'currency_basis': 'Current authenticated Default profile DOM capture.', 'cdp_identity': auth_obs['cdp_identity'], 'evidence': {'source': auth_url, 'observation': auth_obs['observation'], 'source_sha256': load_observation(self.project, auth_obs['observation'])['body_sha256'], 'documentation': True, 'quote': 'Authenticated profile quote.', 'locator': {'type': 'anchor', 'value': 'sec'}}}
		auth_res = self.saved(auth_spec, auth_cand)
		self.assertTrue(auth_res['valid'], auth_res['issues'])
		wrong_id_spec = deepcopy(auth_spec)
		wrong_id_spec['cdp_identity'] = dom_obs['cdp_identity']
		self.assertFalse(self.saved(wrong_id_spec, auth_cand)['valid'])
		unverified_ref, _ = save_cdp_identity(self.project, {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(), 'endpoint': 'http://127.0.0.1:54321', 'browser_websocket': 'ws://127.0.0.1:54321/devtools/browser/1', 'target_id': 'HEADLESS-TAB-1', 'target_mode': 'ephemeral_headless_context', 'profile': {'status': 'unverified'}})
		bad_prof_spec = deepcopy(pub_spec)
		bad_prof_spec['cdp_identity'] = unverified_ref
		self.assertFalse(self.saved(bad_prof_spec, pub_cand)['valid'])
	# 2026-11-16
	# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
	# https://github.com/dmitry-ai/harness/issues/81
	# @used-by :mod:`unittest`
	def test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation(self):
		job_id = '~021989674775509080169'
		snapshot_obj = {'job_id': job_id, 'captured_at': '2026-11-10T09:00:00+00:00', 'description': 'Need GTM Server-Side and Meta CAPI audit.', 'client': {'recent_history': [{'freelancer_feedback_text': 'Clear communication throughout the GTM audit.'}]}}
		snap_bytes = json_data(snapshot_obj)
		snap_sha = digest(snap_bytes)
		snap_path = self.project / f'ꘖ/KB/Evidence/{snap_sha}.json'
		snap_path.parent.mkdir(parents=True, exist_ok=True)
		snap_path.write_bytes(snap_bytes)
		(self.project / 'ꘖ/project.json').write_text(json.dumps({'initialized': True, 'job_id': job_id, 'snapshot': f'ꘖ/KB/Evidence/{snap_sha}.json'}), encoding='utf-8')
		for job_url in (f'https://www.upwork.com/jobs/{job_id}', f'https://upwork.com/jobs/Meta-CAPI-Audit_{job_id}'):
			self.candidate = f'1. Read {job_url}.\n'
			text_sources.probe_links(self.project, self.candidate, fetcher=lambda *args: Response(args[0], 403, 'text/html', b'<title>Just a moment...</title>'))
			spec = {'url': job_url, 'currency': 'current', 'currency_basis': 'Immutable project intake job snapshot.', 'evidence': {'kind': 'intake', 'source': job_url, 'manifest': f'Evidence/{snap_sha}.json', 'source_sha256': snap_sha, 'documentation': False, 'quote': 'Clear communication throughout the GTM audit.', 'locator': {'type': 'json_pointer', 'value': '/client/recent_history/0/freelancer_feedback_text'}}}
			saved = self.saved(spec, self.candidate)
			self.assertTrue(saved['valid'], saved['issues'])
			self.assertEqual(saved['method'], 'INTAKE_SNAPSHOT')
			checked = self.checked([saved['source_check']])
			self.assertTrue(checked['valid'], checked['issues'])
			self.assertIn(f'ꘖ/KB/Evidence/{snap_sha}.json', checked['inputs'])
			self.assertNotIn('ꘖ/project.json', checked['inputs'])
		freelancer_url = 'https://www.upwork.com/freelancers/~0123456789abcdef'
		f_cand = f'1. Freelancer: {freelancer_url}.\n'
		bad_freelancer = {'url': freelancer_url, 'currency': 'current', 'currency_basis': 'Wrong entity kind.', 'evidence': {'kind': 'intake', 'source': freelancer_url, 'manifest': f'Evidence/{snap_sha}.json', 'source_sha256': snap_sha, 'documentation': False, 'quote': 'Clear communication throughout the GTM audit.', 'locator': {'type': 'json_pointer', 'value': '/client/recent_history/0/freelancer_feedback_text'}}}
		self.assertFalse(self.saved(bad_freelancer, f_cand)['valid'])
		other_job_url = 'https://www.upwork.com/jobs/~029999999999999999999'
		o_cand = f'1. Other job: {other_job_url}.\n'
		bad_other_job = deepcopy(bad_freelancer)
		bad_other_job['url'] = other_job_url
		bad_other_job['evidence']['source'] = other_job_url
		self.assertFalse(self.saved(bad_other_job, o_cand)['valid'])
		class Later(datetime):
			# @used-by :meth:`SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
			@classmethod
			def now(cls, tz=None):
				return datetime.now(timezone.utc) + timedelta(days=5)
		canon_url = f'https://www.upwork.com/jobs/{job_id}'
		canon_cand = f'1. Read {canon_url}.\n'
		canon_spec = {'url': canon_url, 'currency': 'current', 'currency_basis': 'Immutable project intake job snapshot.', 'evidence': {'kind': 'intake', 'source': canon_url, 'manifest': f'Evidence/{snap_sha}.json', 'source_sha256': snap_sha, 'documentation': False, 'quote': 'Clear communication throughout the GTM audit.', 'locator': {'type': 'json_pointer', 'value': '/client/recent_history/0/freelancer_feedback_text'}}}
		with patch('agent_tools.text_sources.datetime', Later):
			aged_res = self.saved(canon_spec, canon_cand)
			self.assertTrue(aged_res['valid'], aged_res['issues'])
			self.assertTrue(text_sources.source_integrity(self.project, canon_cand, aged_res['source_check'])['source_check'])
			self.assertTrue(text_review._source_reviews(self.project, {'result': 'approved', 'source_reviews': [{'url': canon_url, 'receipt': aged_res['source_check'], 'assessment': 'Immutable intake snapshot.', 'outcome': 'supported'}]}, {'source_checks': [aged_res['source_check']]}, canon_cand))
		for rejected_url in (f'{canon_url}#frag', f'{canon_url}?foo=1', f'https://www.upwork.com/jobs/../freelancers/{job_id}'):
			rej_cand = f'1. Bad URL: {rejected_url}.\n'
			rej_spec = deepcopy(canon_spec)
			rej_spec['url'] = rejected_url
			rej_spec['evidence']['source'] = rejected_url
			self.assertFalse(self.saved(rej_spec, rej_cand)['valid'], rejected_url)
		from test_intake import IntakeTests
		intake_fx = IntakeTests()
		intake_fx.setUp()
		self.addCleanup(intake_fx.doCleanups)
		intake_fx.initialize()
		intake_fx.capture_file('request.txt', b'User request\n')
		self.assertEqual(intake_fx.commit()['status'], 'drained')
		receipt_file = intake_fx.manifest()
		receipt_doc = json.loads(receipt_file.read_text(encoding='utf-8'))
		src_entry = next((e for e in receipt_doc['entries'] if 'source.json' == e['original_relative_provenance']))
		req_entry = next((e for e in receipt_doc['entries'] if 'request.txt' == e['original_relative_provenance']))
		fx_url = f"https://www.upwork.com/jobs/{intake_fx.source['job_id']}"
		fx_cand = f'1. Intake job: {fx_url}.\n'
		fx_target = intake_fx.project / 'result/proposal.md'
		fx_target.parent.mkdir(parents=True, exist_ok=True)
		fx_target.write_bytes(fx_cand.encode('utf-8'))
		fx_op = text_workflow.begin(intake_fx.project, {'kind': 'proposal', 'mode': 'edit', 'changes': 'links', 'target': 'result/proposal.md', 'goal': 'Check intake link.', 'requests': ['Check intake link.']})
		fx_manifest = receipt_file.relative_to(intake_fx.project / 'ꘖ/KB').as_posix()
		fx_spec = {'url': fx_url, 'currency': 'current', 'currency_basis': 'Registered Intake receipt source.json.', 'evidence': {'kind': 'intake', 'source': fx_url, 'manifest': fx_manifest, 'source_sha256': src_entry['sha256'], 'documentation': False, 'quote': 'Exact source\n', 'locator': {'type': 'json_pointer', 'value': '/description'}}}
		fx_saved = text_sources.save_source_check(intake_fx.project, fx_cand, fx_spec)
		self.assertTrue(fx_saved['valid'], fx_saved['issues'])
		self.assertTrue(text_workflow.check(intake_fx.project, fx_op['id'], fx_cand, {'source_checks': [fx_saved['source_check']]})['valid'])
		bad_req_txt = {'url': fx_url, 'currency': 'current', 'currency_basis': 'Request note is not job snapshot.', 'evidence': {'kind': 'intake', 'source': (intake_fx.project / req_entry['durable_file']).relative_to(intake_fx.project / 'ꘖ/KB').as_posix(), 'manifest': fx_manifest, 'source_sha256': req_entry['sha256'], 'documentation': False, 'quote': 'User request', 'locator': {'type': 'text', 'value': 'User request'}}}
		self.assertFalse(text_sources.save_source_check(intake_fx.project, fx_cand, bad_req_txt)['valid'])
if '__main__' == __name__:
	unittest.main()
