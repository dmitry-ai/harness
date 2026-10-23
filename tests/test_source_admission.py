"""Primary-byte fixtures and a real HTTP server reproduce the three link defects."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


class LinkPresentationTests(unittest.TestCase):
    def findings(self, text, profile='formatted'):
        findings = []
        check_link_style(scan(text), findings, profile)
        return {f.rule for f in findings}

    def test_original_numeric_anchor_is_not_a_quantitative_claim(self):
        for fragment in ('15.3', 'p-15.3(k)'):
            text = f'[**ecfr.gov**/current/title-47/part-15#{fragment}](<https://www.ecfr.gov/current/title-47/part-15#{fragment}>)'
            self.assertEqual(standalone_numbers(text), set())
            self.assertEqual(self.findings(text), set())

    def test_numeric_prose_in_a_link_label_still_needs_grounding(self):
        self.assertEqual(standalone_numbers('[The limit is 15.3 volts.](https://example.org/)'), {'15.3'})
        self.assertEqual(standalone_numbers('The limit is **15.3** volts.'), {'15.3'})

    def test_reference_links_and_balanced_parentheses_keep_the_same_behavior(self):
        text = '[**ecfr.gov**/part-15#p-15.3(k)][law]\n\n[law]: <https://ecfr.gov/part-15#p-15.3(k)>'
        self.assertEqual(standalone_numbers(text), set())
        self.assertNotIn('LINK-LABEL', self.findings(text))

    def test_missing_changed_fragment_path_query_or_host_is_rejected(self):
        target = 'https://ecfr.gov/part-15?edition=current#p-15.3(k)'
        for label in ['ecfr.gov/part-15?edition=current', 'ecfr.gov/part-15?edition=current#wrong',
                      'ecfr.gov/part-16?edition=current#p-15.3(k)', 'ecfr.gov/part-15#p-15.3(k)',
                      'other.gov/part-15?edition=current#p-15.3(k)']:
            self.assertIn('LINK-LABEL', self.findings(f'[{label}](<{target}>)'), label)

    def test_named_links_are_allowed_in_other_profiles_and_literals_are_preserved(self):
        text = '[The source](https://example.org/#p)'
        self.assertNotIn('LINK-LABEL', self.findings(text, 'markdown'))
        self.assertNotIn('LINK-LABEL', self.findings('`' + text + '`\n«' + text + '»\n> ' + text))


class SourceAdmissionTests(TextWorkspaceCase):
    def setUp(self):
        super().setUp()
        self.url = 'https://example.org/rule#p'
        self.candidate = '1. Read ' + self.url + '.\n'
        self.target, self.op = self.start(self.candidate, changes='links')

    def spec(self, *, url=None, body=None, status=200, final=None, kind='http'):
        url = url or self.url
        body = body or b'<h2 id="p">Rule</h2><p>Exact legal text.</p>'
        observation = collect(self.project, url, max_age=0, observation_kind=kind,
            fetcher=lambda *args: Response(final or args[0], status, 'text/html', body))
        return {'url': url, 'currency': 'current', 'currency_basis': 'This exact captured page at the observed time.',
            'evidence': {'source': url, 'observation': observation['observation'],
                'source_sha256': observation['body_sha256'], 'quote': 'Exact legal text.',
                'documentation': True, 'locator': {'type': 'anchor', 'value': 'p'}}}

    def saved(self, spec=None, candidate=None):
        return text_sources.save_source_check(self.project, candidate or self.candidate, spec or self.spec())

    def checked(self, records):
        return text_workflow.check(self.project, self.op['id'], self.candidate, {'source_checks': records})

    def cli(self, *args):
        script = Path(__file__).resolve().parents[1] / 'scripts/df_text.py'
        return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, timeout=30)

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

    def test_missing_source_checks_cannot_become_a_valid_mechanical_check(self):
        result = self.checked([])
        self.assertFalse(result['valid'])
        self.assertIn('text.source_missing', codes(result))

    def test_unicode_address_and_encoded_markdown_destination_share_one_identity(self):
        self.url = 'https://example.org/документ#раздел'
        self.candidate = 'Read [документ](<' + self.url + '>).'
        spec = self.spec(body='<h2 id="раздел">Rule</h2><p>Exact legal text.</p>'.encode('utf-8'))
        spec['evidence']['locator']['value'] = 'раздел'
        saved = self.saved(spec)
        self.assertTrue(saved['valid'], saved['issues'])
        self.assertEqual(text_sources.source_urls(self.candidate), [self.url])
        self.assertFalse(text_sources.validate_source_checks(self.project, self.candidate, [saved['source_check']])['issues'])

    def test_exact_primary_quote_receipt_is_reused_without_network_and_apply_keeps_it(self):
        saved = self.saved()
        self.assertTrue(saved['valid'], saved)
        with patch('agent_tools.research.fetch', side_effect=AssertionError('No new network during check/apply')):
            checked = self.checked([saved['source_check']])
            self.assertTrue(checked['valid'], checked['issues'])
            applied = text_workflow.apply(self.project, checked['check'])
            self.assertEqual(applied['source_checks'], [saved['source_check']])
            self.assertTrue(text_workflow.gate(self.project)['valid'])
        self.assertTrue(any(path.endswith('response.bin') for path in checked['inputs']))

    def test_http_500_wrong_anchor_and_wrong_quote_are_preserved_as_failed_receipts(self):
        for spec in [self.spec(status=500), self.spec(body=b'<h2 id="other">Rule</h2><p>Exact legal text.</p>'),
                     self.spec(body=b'<h2 id="p">Rule</h2><p>Different legal text.</p>')]:
            failed = self.saved(spec)
            self.assertFalse(failed['valid'])
            self.assertFalse(self.checked([failed['source_check']])['valid'])

    def test_a_200_redirect_to_a_challenge_is_not_the_intended_resource(self):
        failed = self.saved(self.spec(final='https://unblock.example.org/'))
        self.assertFalse(failed['valid'])
        self.assertIn('Final URL', ' '.join(failed['issues']))

    def test_explicit_canonical_redirect_still_requires_the_anchor_and_quote(self):
        spec = self.spec(final='https://example.org/canonical')
        spec['expected_final_url'] = 'https://example.org/canonical'
        self.assertTrue(self.saved(spec)['valid'])
        bad = deepcopy(spec); bad['evidence']['quote'] = 'Not in the primary document.'
        self.assertFalse(self.saved(bad)['valid'])

    def test_a_redirect_capture_cannot_substitute_for_requesting_a_different_citation(self):
        spec = self.spec(final='https://example.org/canonical')
        self.url = 'https://example.org/canonical#p'
        self.candidate = 'Read ' + self.url
        spec['url'] = self.url
        spec['evidence']['source'] = self.url
        failed = self.saved(spec)
        self.assertFalse(failed['valid'])
        self.assertIn('Requested URL', ' '.join(failed['issues']))

    def test_plain_authored_verified_objects_and_changed_candidates_are_rejected(self):
        saved = self.saved()
        self.assertFalse(self.checked([{'url': self.url, 'valid': True}])['valid'])
        with self.assertRaisesRegex(ValueError, 'another candidate'):
            text_sources.read_source_check(self.project, self.candidate + 'Changed.', saved['source_check'])

    def test_primary_byte_or_metadata_change_invalidates_a_previously_valid_check(self):
        saved = self.saved()
        checked = self.checked([saved['source_check']])
        meta = self.project / 'ꘖ/KB' / saved['spec']['evidence']['observation']
        meta.with_name('response.bin').write_bytes(b'Changed original source')
        with self.assertRaisesRegex(ValueError, 'stale or failed'):
            text_workflow.refresh_check(self.project, checked['check'])

    def test_a_later_failed_probe_cannot_be_overridden_by_minting_an_older_success(self):
        spec = self.spec(); saved = self.saved(spec)
        self.assertTrue(self.checked([saved['source_check']])['valid'])
        probe = text_sources.probe_links(self.project, self.candidate,
            fetcher=lambda *args: Response(args[0], 500, 'text/html', b'Internal server error'))
        self.assertTrue(probe['findings'])
        self.assertFalse(self.checked([saved['source_check']])['valid'])
        self.assertFalse(self.saved(spec)['valid'])
        refreshed = self.saved(self.spec())
        self.assertTrue(self.checked([refreshed['source_check']])['valid'])

    def test_changing_candidate_does_not_erase_a_later_failure_of_the_same_url(self):
        spec = self.spec(); self.saved(spec)
        text_sources.probe_links(self.project, self.candidate,
            fetcher=lambda *args: Response(args[0], 500, 'text/html', b'Internal server error'))
        self.assertFalse(self.saved(spec, self.candidate + '\n')['valid'])

    def test_later_failure_invalidates_apply_and_an_already_applied_gate(self):
        checked = self.checked([self.saved()['source_check']])
        text_sources.probe_links(self.project, self.candidate,
            fetcher=lambda *args: Response(args[0], 500, 'text/html', b'Internal server error'))
        with self.assertRaisesRegex(ValueError, 'stale or failed'):
            text_workflow.apply(self.project, checked['check'])
        refreshed = self.checked([self.saved()['source_check']])
        text_workflow.apply(self.project, refreshed['check'])
        text_sources.probe_links(self.project, self.candidate,
            fetcher=lambda *args: Response(args[0], 500, 'text/html', b'Internal server error'))
        with self.assertRaisesRegex(ValueError, 'newer conflicting'):
            text_workflow.gate(self.project)

    def test_snapshot_replacement_does_not_verify_the_old_broken_citation(self):
        different = self.spec(url='https://example.org/other#p')
        self.assertFalse(self.saved(different)['valid'])

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

    def test_documentation_anchor_cannot_exist_only_in_the_receipt(self):
        self.url = 'https://example.org/rule'
        self.candidate = 'Read ' + self.url
        failed = self.saved(self.spec())
        self.assertFalse(failed['valid'])
        self.assertIn('cited URL itself', ' '.join(failed['issues']))

    def test_old_current_sources_expire_but_explicit_historical_editions_are_distinct(self):
        spec = self.spec()
        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.now(timezone.utc) + timedelta(days=2)
        with patch('agent_tools.text_sources.datetime', Later):
            self.assertFalse(self.saved(spec)['valid'])
            spec.update(currency='historical', edition='2024 edition', currency_basis='An explicitly historical comparison only.')
            self.assertTrue(self.saved(spec)['valid'])

    def test_dom_fallback_needs_the_exact_captured_identity(self):
        spec = self.spec(kind='dom')
        self.assertFalse(self.saved(spec)['valid'])

    def test_valid_dom_capture_identity_can_resolve_the_http_channel_failure(self):
        from agent_tools.storage import create_bytes
        text_sources.probe_links(self.project, self.candidate,
            fetcher=lambda *args: Response(args[0], 403, 'text/html', b'Forbidden'))
        identity = {'schema_version': 1, 'session_id': 'fixture-session', 'target_id': 'fixture-tab',
                    'browser_websocket': 'ws://127.0.0.1/fixture', 'profile': {'name': 'fixture'},
                    'account': None, 'observed_at': datetime.now(timezone.utc).isoformat()}
        raw = json_data(identity)
        path = self.project / 'ꘖ/KB/Evidence/CDPSessions' / (digest(raw) + '.json')
        path.parent.mkdir(parents=True)
        create_bytes(path, raw)
        reference = path.relative_to(self.project / 'ꘖ/KB').as_posix()
        observation = collect(self.project, self.url, max_age=0, observation_kind='dom',
            scope=f'CDP-session:fixture-session:tab:fixture-tab:identity:{reference}',
            context={'session_id': 'fixture-session'},
            fetcher=lambda *args: Response(args[0], 0, 'text/html', b'<h2 id="p">Rule</h2><p>Exact legal text.</p>'))
        spec = {'url': self.url, 'currency': 'current', 'currency_basis': 'Explicit read-only DOM test fixture.',
                'cdp_identity': reference, 'evidence': {'source': self.url,
                'observation': observation['observation'], 'source_sha256': observation['body_sha256'],
                'documentation': True, 'quote': 'Exact legal text.', 'locator': {'type': 'anchor', 'value': 'p'}}}
        result = self.saved(spec)
        self.assertTrue(result['valid'], result['issues'])
        self.assertTrue(self.checked([result['source_check']])['valid'])

    def test_reviewer_approval_needs_a_receipt_bound_assessment_for_each_url(self):
        saved = self.saved()
        package = {'source_checks': [saved['source_check']]}
        data = {'result': 'approved'}
        with self.assertRaisesRegex(ValueError, 'every external source'):
            text_review._source_reviews(self.project, data, package, self.candidate)
        data['source_reviews'] = [{'url': self.url, 'receipt': saved['source_check'],
            'assessment': 'The exact quote and anchor establish this narrow statement in this edition.', 'outcome': 'supported'}]
        self.assertTrue(text_review._source_reviews(self.project, data, package, self.candidate))
        data['source_reviews'][0]['outcome'] = 'unsupported'
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            text_review._source_reviews(self.project, data, package, self.candidate)

    def test_reviewer_can_collect_its_own_equal_bytes_without_invalidating_the_author(self):
        author = self.saved()
        independent = self.saved(self.spec())
        package = {'source_checks': [author['source_check']]}
        report = {'result': 'approved', 'source_reviews': [{'url': self.url,
            'receipt': independent['source_check'], 'assessment': 'Independent bytes, same exact quote and section.',
            'outcome': 'supported'}]}
        self.assertTrue(text_review._source_reviews(self.project, report, package, self.candidate))
        self.assertTrue(self.checked([author['source_check']])['valid'])

    def test_full_native_review_fixture_requires_and_preserves_source_assessments(self):
        # Reuse the existing end-to-end native-review fixture, never a live verdict.
        from test_text_integration import TextReviewTests
        import uuid
        fixture = TextReviewTests()
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        fixture.candidate = '1. The captured page contains Alternative: https://example.org/source.\n'
        registry = json.loads((fixture.project / 'ꘖ/KB/TextClaims.json').read_text(encoding='utf-8'))
        ref = deepcopy(registry['facts'][0]['evidence'][0]); ref['documentation'] = False
        source = text_sources.save_source_check(fixture.project, fixture.candidate,
            {'url': ref['source'], 'currency': 'current', 'currency_basis': 'Current synthetic page capture.', 'evidence': ref})
        self.assertTrue(source['valid'], source)
        manifest = fixture.manifest(fixture.candidate)
        manifest['source_checks'] = [source['source_check']]
        fixture.checked = text_workflow.check(fixture.project, fixture.op['id'], fixture.candidate, manifest)
        self.assertTrue(fixture.checked['valid'], fixture.checked['issues'])
        package = fixture.package()
        with self.assertRaisesRegex(ValueError, 'every external source'):
            fixture.record_fixture(package)
        report = fixture.report(package)
        report['source_reviews'] = [{'url': ref['source'], 'receipt': source['source_check'],
            'assessment': 'Literal saved page content; this is not a causal or execution claim.', 'outcome': 'supported'}]
        reviewer = str(uuid.uuid4()); final = json.dumps(report, ensure_ascii=False)
        native = {'surface': 'codex-ui', 'status': 'completed', 'parent_id': fixture.parent, 'reviewer_id': reviewer,
                  'final_response': final, 'final_response_sha256': digest(final.encode())}
        native_path = fixture.project_file('ꘖ/KB/Evidence/Reviews/' + reviewer + '.json', json.dumps(native))
        with patch('agent_tools.metrics.verify_native_proof', return_value=native):
            entry = text_review.record(fixture.project, final.encode(), parent_id=fixture.parent, reviewer_id=reviewer,
                native_evidence=native_path.relative_to(fixture.project).as_posix())
            applied = text_workflow.apply(fixture.project, fixture.checked['check'])
        self.assertEqual(applied['status'], 'applied')
        self.assertTrue(any(path.endswith('response.bin') for path in entry['proof']))

    def test_real_http_failure_and_redirect_are_saved_once_per_base_url(self):
        hits = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                if self.path == '/redirect':
                    self.send_response(302); self.send_header('Location', '/challenge'); self.end_headers()
                else:
                    self.send_response(500 if self.path == '/bad' else 200)
                    self.send_header('Content-Type', 'text/html'); self.end_headers()
                    self.wfile.write(b'<h2 id="p">Rule</h2><p>Exact legal text.</p>')
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            result = text_sources.probe_links(self.project, f'[a]({base}/good#p) [b]({base}/good#absent) [c]({base}/bad) [d]({base}/redirect#p)')
            self.assertEqual(hits.count('/good'), 1)
            self.assertIn('unavailable', {r['status'] for r in result['results']})
            self.assertIn('redirect-unverified', {r['status'] for r in result['results']})
            self.assertIn('anchor-unverified', {r['status'] for r in result['results']})
            self.assertTrue(all((self.project / r['probe']).is_file() for r in result['results']))
            candidate = self.project_file('network-candidate.md', f'1. Read {base}/bad.\n')
            missing = self.cli('lint', candidate, '--kind', 'proposal', '--network', '--json')
            self.assertEqual(missing.returncode, 2)
            failed = self.cli('lint', candidate, '--kind', 'proposal', '--network', '--project', self.project, '--json')
            self.assertEqual(failed.returncode, 1, failed.stderr.decode('utf-8'))
            self.assertIn(b'SOURCE-UNVERIFIED', failed.stdout)
            probes = [json.loads(path.read_text(encoding='utf-8')) for path in
                      (self.project / 'ꘖ/data/texts/sources').glob('*-probe.json')]
            self.assertTrue(any(p['candidate_sha256'] == digest(candidate.read_bytes()) and p['http_status'] == 500 for p in probes))
        finally:
            server.shutdown(); thread.join(); server.server_close()


if __name__ == '__main__':
    unittest.main()
