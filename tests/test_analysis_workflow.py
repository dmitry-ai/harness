"""Behavioral regression: real files, native-shaped traces, GETs and interruptions."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch
import hashlib
import json
import sqlite3
import unittest
import uuid

from test_agent_tools import TemporaryCase
from test_onboarding import source, analysis
from agent_tools import upwork_project as up
from agent_tools.analysis import analysis_issues, publish_owned, render_analysis, SECTIONS
from agent_tools.evidence import evidence_issues, pointer, resolve_pointer
from agent_tools.research import collect, collect_plan, extract_file, extract_observation, extract_bytes, Response, load_observation, json_data
from agent_tools import workflow as flow
from agent_tools.metrics import summarize, native_review_proof
from agent_tools.context import generate
from agent_tools.journal import record_step


class ProjectCase(TemporaryCase):
    def setUp(self):
        super().setUp()
        self.project = Path(up.initialize_upwork_project(source()['job_id'], domain_or_topic='Topic',
            extracted_data=source(), date_str='2026-10-15', daily_root=self.root / 'daily',
            register_antigravity=False)['project_dir'])

    def put_project(self, relative, data):
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
        return path

    def valid_analysis(self):
        value = analysis()
        self.put_project('ꘖ/KB/Evidence/client.json', '{"concern":"The concern","alternative":"Alternative"}')
        for section in SECTIONS:
            for claim in value[section]:
                for side, fragment in [('for', 'concern'), ('against', 'alternative')]:
                    for arg in claim[side]:
                        arg['source'] = f'Evidence/client.json#/{fragment}'
        self.put_project('ꘖ/KB/Analysis.json', json.dumps(value, ensure_ascii=False))
        return value


class AnalysisContractTests(ProjectCase):
    def test_many_independent_errors_are_reported_with_fields_and_ids(self):
        value = self.valid_analysis()
        value['causes'][0]['probability_percent'] = None
        value['causes'][0]['addresses'] = ['MISSING']
        value['methods'][0].pop('criterion')
        value['concerns'][0]['for'][0]['quote'] = ''
        issues = analysis_issues(value)
        self.assertTrue({'claim.score', 'claim.reference', 'claim.required', 'argument.required'}.issubset({x['code'] for x in issues}))
        self.assertTrue(all('field' in x and 'claim_id' in x for x in issues))

    def test_no_counterevidence_needs_documented_review_and_real_sources(self):
        value = self.valid_analysis(); claim = value['causes'][0]
        claim['against'] = []
        self.assertTrue(analysis_issues(value))
        claim['counterevidence'] = {'status': 'not_found', 'reviewed_sources': ['Evidence/client.json'], 'limitations': 'Public source only; admin logs are unavailable.'}
        self.assertEqual(analysis_issues(value), [])
        self.assertEqual(evidence_issues(self.project, value), [])
        claim['counterevidence']['reviewed_sources'] = ['Evidence/invented.json']
        self.assertTrue(evidence_issues(self.project, value))

    def test_source_registry_and_escaped_pointers_resolve(self):
        data = {'~job/a': ['точная цитата']}
        ref = pointer('~job/a', 0)
        self.assertEqual(resolve_pointer(data, ref), 'точная цитата')
        for invalid in ('/~2', '/~0job~1a/-1', '/~0job~1a/00'):
            with self.assertRaises((ValueError, KeyError)):
                resolve_pointer(data, invalid)
        value = self.valid_analysis()
        value['sources'] = {'SOURCE-1': 'Evidence/client.json#/concern'}
        arg = value['concerns'][0]['for'][0]; arg.pop('source'); arg['source_id'] = 'SOURCE-1'
        self.assertEqual(analysis_issues(value), [])
        self.assertEqual(evidence_issues(self.project, value), [])
        self.assertIn('Evidence/client.json#/concern', render_analysis(value))

    def test_quote_from_another_json_field_is_rejected(self):
        value = self.valid_analysis()
        value['concerns'][0]['for'][0]['source'] = 'Evidence/client.json#/alternative'
        self.assertTrue(evidence_issues(self.project, value))

    def test_local_markdown_quote_must_belong_to_the_linked_section(self):
        self.put_project('ꘖ/KB/Evidence/article.md', '# First\nThe concern\n\n# Second\nAlternative\n')
        value = self.valid_analysis()
        value['concerns'][0]['for'][0]['source'] = 'Evidence/article.md#second'
        self.assertTrue(evidence_issues(self.project, value))

    def test_no_anchor_exception_uses_an_observed_specific_section(self):
        response = Response('https://docs.example/article', 200, 'text/html',
            b'<h1>Article</h1><h2>Eligibility</h2><p>The concern</p><h2>Other</h2><p>Alternative</p>')
        observation = collect(self.project, response.url, fetcher=lambda *args: response)
        value = self.valid_analysis(); arg = value['concerns'][0]['for'][0]
        arg.update(source=response.url, documentation=True,
            anchor_exception={'section': 'Eligibility', 'observation': observation['observation']})
        self.assertEqual(analysis_issues(value), [])
        self.assertEqual(evidence_issues(self.project, value), [])
        arg['anchor_exception']['section'] = 'Other'
        self.assertTrue(evidence_issues(self.project, value))
        arg['anchor_exception']['observation'] = 'Evidence/missing/observation.json'
        self.assertTrue(evidence_issues(self.project, value))

    def test_existing_heading_or_ancestor_anchor_is_required(self):
        for html in (b'<h2 id="eligibility">Eligibility</h2><p>The concern</p>',
                     b'<section id="part"><h2>Eligibility</h2><p>The concern</p></section>'):
            response = Response('https://docs.example/article', 200, 'text/html', html)
            observation = collect(self.project, response.url, refresh_reason='separate sample', fetcher=lambda *args: response)
            value = self.valid_analysis(); arg = value['concerns'][0]['for'][0]
            arg.update(source=response.url, documentation=True,
                anchor_exception={'section': 'Eligibility', 'observation': observation['observation']})
            self.assertTrue(evidence_issues(self.project, value))
            arg.pop('anchor_exception'); arg['source'] += '#eligibility' if b'id="eligibility"' in html else '#part'
            self.assertEqual(evidence_issues(self.project, value), [])

    def test_anchored_quote_from_another_section_is_rejected(self):
        response = Response('https://docs.example/article', 200, 'text/html', b'<h2 id="a">A</h2>The concern<h2 id="b">B</h2>Alternative')
        collect(self.project, response.url, fetcher=lambda *args: response)
        value = self.valid_analysis(); value['concerns'][0]['for'][0].update(source=response.url + '#b', documentation=True)
        self.assertTrue(evidence_issues(self.project, value))

    def test_content_addressed_primary_evidence_tampering_is_detected(self):
        value = self.valid_analysis()
        raw = b'{"concern":"The concern"}'
        digest = hashlib.sha256(raw).hexdigest()
        file = self.put_project(f'ꘖ/KB/Evidence/{digest}.json', raw)
        value['concerns'][0]['for'][0]['source'] = f'Evidence/{digest}.json#/concern'
        self.assertEqual(evidence_issues(self.project, value), [])
        file.write_bytes(b'{"concern":"edited"}')
        self.assertTrue(evidence_issues(self.project, value))


class PublicationTests(ProjectCase):
    def test_repeat_render_updates_owned_file_and_archives_previous_bytes(self):
        target = self.project / 'ꘖ/KB/Analysis.md'
        self.assertEqual(publish_owned(target, 'first')['status'], 'published')
        self.assertEqual(publish_owned(target, 'first')['status'], 'unchanged')
        self.assertEqual(publish_owned(target, 'second')['status'], 'published')
        self.assertEqual(target.read_text(), 'second')
        self.assertIn(b'first', [p.read_bytes() for p in (self.project / 'ꘖ/data/render-history').rglob('*.md')])

    def test_untracked_or_manually_edited_file_is_preserved_with_candidate(self):
        target = self.put_project('ꘖ/KB/Analysis.md', 'manual')
        result = publish_owned(target, 'generated')
        self.assertEqual(result['status'], 'conflict')
        self.assertEqual(target.read_text(), 'manual')
        self.assertEqual(Path(result['candidate']).read_text(), 'generated')
        publish_owned(target, 'manual')  # Adopt only an identical output.
        target.write_text('new manual edit')
        self.assertEqual(publish_owned(target, 'generated')['status'], 'conflict')
        self.assertEqual(target.read_text(), 'new manual edit')

    def test_interrupted_state_write_preserves_published_output_for_recovery(self):
        target = self.project / 'ꘖ/KB/Analysis.md'
        from agent_tools import analysis as module
        real = module.replace_bytes
        def interrupted(path, data):
            if Path(path).name == 'rendered.json':
                raise OSError('power failure')
            return real(path, data)
        with patch.object(module, 'replace_bytes', side_effect=interrupted), self.assertRaises(OSError):
            publish_owned(target, 'first')
        self.assertEqual(target.read_text(), 'first')
        self.assertEqual(publish_owned(target, 'first')['status'], 'unchanged')


class ResearchTests(ProjectCase):
    def test_concurrent_and_repeated_fetches_reuse_one_saved_response(self):
        calls = []
        def fetcher(*args):
            calls.append(args)
            return Response(args[0], 200, 'text/html', b'<head><title>Title</title></head><body><h1>Title</h1><p>Exact text</p></body>')
        with ThreadPoolExecutor(max_workers=4) as pool:
            observations = list(pool.map(lambda _: collect(self.project, 'https://example.org/', fetcher=fetcher), range(4)))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len({x['observation'] for x in observations}), 1)
        extracted = extract_observation(self.project, observations[0]['observation'])
        data = json.loads((self.project / 'ꘖ/KB' / extracted['extraction']).read_text())
        self.assertEqual(data['title'], 'Title')
        self.assertIn('Exact text', data['text'])

    def test_conditions_scope_and_explicit_refresh_make_separate_measurements(self):
        calls = []
        def fetcher(*args):
            calls.append(args)
            return Response(args[0], 200, 'text/plain', b'body')
        first = collect(self.project, 'https://example.org/', headers={'Authorization': 'FAKE-TEST-SECRET'}, scope='account-a', fetcher=fetcher)
        same = collect(self.project, 'https://example.org/', headers={'Authorization': 'FAKE-TEST-SECRET'}, scope='account-a', fetcher=fetcher)
        changed = collect(self.project, 'https://example.org/', headers={'Accept-Language': 'ru'}, fetcher=fetcher)
        refreshed = collect(self.project, 'https://example.org/', headers={'Authorization': 'FAKE-TEST-SECRET'}, scope='account-a', refresh_reason='new time measurement', fetcher=fetcher)
        self.assertEqual(len(calls), 3)
        self.assertEqual(first['observation'], same['observation'])
        self.assertNotEqual(first['observation'], refreshed['observation'])
        self.assertNotEqual(first['request_key'], changed['request_key'])
        self.assertNotIn('FAKE-TEST-SECRET', json.dumps(first))

    def test_changed_cached_body_is_not_silently_used(self):
        observation = collect(self.project, 'https://example.org/', fetcher=lambda *a: Response(a[0], 200, 'text/plain', b'original'))
        folder = (self.project / 'ꘖ/KB' / observation['observation']).parent
        (folder / 'response.bin').write_bytes(b'altered')
        with self.assertRaises(ValueError):
            load_observation(self.project, observation['observation'])

    def test_http_error_observation_is_completed_and_preserved(self):
        result = collect_plan(self.project, {'requests': [{'url': 'https://example.org/absent'}]},
            fetcher=lambda *a: Response(a[0], 404, 'text/html', b'Not found'))
        self.assertTrue(result['complete'])
        self.assertFalse(result['content_available_for_all'])
        self.assertEqual(result['results'][0]['status'], 404)
        self.assertTrue((self.project / 'ꘖ/KB' / result['results'][0]['observation']).is_file())

    def test_tracking_and_shopify_extraction_preserve_provenance_limits(self):
        data = extract_bytes(b'<script>webPixelsConfigList=[{"id":123}];</script><div>GTM-ABC</div>', 'text/html', 'tracking')
        self.assertFalse(data['execution_checked'])
        self.assertEqual(data['embedded_json']['webPixelsConfigList'][0], [{'id': 123}])
        product = extract_bytes(b'{"product":{"id":1,"variants":[{"price":"25.97"}]}}', 'application/json', 'shopify')
        self.assertEqual(product['data']['product']['variants'][0]['price'], '25.97')
        self.assertIn('not Merchant Center', product['scope'])

    def test_real_get_and_cross_origin_redirect_strip_authentication(self):
        received = []
        class Destination(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append(self.headers.get('Authorization'))
                self.send_response(200); self.send_header('Content-Type', 'text/html'); self.end_headers(); self.wfile.write(b'<h1>Actual response</h1>')
            def log_message(self, *args): pass
        destination = ThreadingHTTPServer(('127.0.0.1', 0), Destination)
        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302); self.send_header('Location', f'http://127.0.0.1:{destination.server_port}/'); self.end_headers()
            def log_message(self, *args): pass
        redirect = ThreadingHTTPServer(('127.0.0.1', 0), Redirect)
        threads = [Thread(target=server.serve_forever, daemon=True) for server in (destination, redirect)]
        for thread in threads: thread.start()
        try:
            result = collect(self.project, f'http://127.0.0.1:{redirect.server_port}/', headers={'Authorization': 'FAKE'}, scope='test')
            self.assertEqual(result['status'], 200)
            self.assertEqual(received, [None])
            self.assertEqual(len(result['redirects']), 1)
        finally:
            for server in (destination, redirect): server.shutdown(); server.server_close()
            for thread in threads: thread.join()


class ContinuationTests(ProjectCase):
    def test_resume_uses_existing_capture_and_agent_kb_without_reading_context(self):
        original = {p: p.read_bytes() for p in (self.project / 'ꘖ/KB').glob('*.md')}
        capture = self.project / json.loads((self.project / 'ꘖ/project.json').read_text())['snapshot']
        request = 'Продолжай анализ. Анализ оборвался из-за сбоя электропитания.\n'
        context = self.project / 'ꙮ/0/Context.md'
        context.write_text('EXTERNAL_ONLY_INFORMATION')
        result = flow.resume(self.project, 'power failure', request)
        self.assertEqual(result['stages']['capture'], 'complete')
        self.assertEqual(result['next_stage'], 'identity_init')
        self.assertTrue(capture.is_file())
        self.assertEqual({p: p.read_bytes() for p in original}, original)
        self.assertNotIn('EXTERNAL_ONLY_INFORMATION', (self.project / 'ꘖ/KB/Progress.md').read_text())
        self.assertEqual(flow.load(self.project)['requests'][-1]['text'], request)

    def test_file_presence_does_not_complete_analysis_or_review(self):
        self.valid_analysis()
        flow.resume(self.project, 'quota')
        self.assertNotEqual(flow.status(self.project)['stages']['analysis'], 'complete')
        self.assertNotEqual(flow.status(self.project)['stages']['review'], 'complete')

    def test_changed_completed_stage_output_invalidates_dependencies(self):
        flow.resume(self.project, 'quota')
        path = self.put_project('ꘖ/KB/Evidence/init-check.json', '{}')
        flow.complete_stage(self.project, 'identity_init', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/init-check.json'])
        self.assertEqual(flow.status(self.project)['stages']['identity_init'], 'complete')
        path.write_text('{"changed":true}')
        self.assertEqual(flow.status(self.project)['stages']['identity_init'], 'stale')

    def test_question_has_one_owner_and_explicit_handoff(self):
        flow.resume(self.project, 'quota')
        flow.add_question(self.project, 'Q-SITE', 'Check canonical URL', 'Affects identity', 'Saved exact canonical', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/site.json'])
        flow.claim_question(self.project, 'Q-SITE', 'worker-a')
        with self.assertRaises(ValueError): flow.claim_question(self.project, 'Q-SITE', 'worker-b')
        flow.handoff(self.project, 'Q-SITE', 'worker-a', 'worker-b', 'Native status shows worker-a stopped')
        self.put_project('ꘖ/KB/Evidence/site.json', '{"canonical":"https://example.org"}')
        flow.finish_question(self.project, 'Q-SITE', 'worker-b', ['ꘖ/KB/Evidence/site.json'])
        with self.assertRaises(ValueError): flow.claim_question(self.project, 'Q-SITE', 'worker-a')

    def test_search_cycle_returns_gap_or_requires_a_new_method(self):
        flow.resume(self.project, 'quota')
        flow.add_question(self.project, 'Q-DOC', 'Find diagnostics source', 'Needed for cause', 'Exact source or gap', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/doc.json'])
        flow.claim_question(self.project, 'Q-DOC', 'worker')
        for n in range(3): flow.record_search(self.project, 'Q-DOC', 'worker', f'variant {n}')
        with self.assertRaises(ValueError): flow.record_search(self.project, 'Q-DOC', 'worker', 'fourth variant')
        flow.record_search(self.project, 'Q-DOC', 'worker', 'official navigation', method_change='Use documentation navigation instead of reformulating search')


class NativeReviewTests(ProjectCase):
    def native_fixture(self, package, child=None, agent='self', final_type=15):
        home = self.root / 'home'; backend = home / '.gemini/antigravity'
        backend.mkdir(parents=True, exist_ok=True)
        parent = package['parent_id']; child = child or str(uuid.uuid4())
        conn = sqlite3.connect(backend / 'conversation_summaries.db')
        conn.execute('CREATE TABLE IF NOT EXISTS conversation_summaries (conversation_id TEXT,parent_conversation_id TEXT,agent_name TEXT)')
        conn.execute('INSERT INTO conversation_summaries VALUES (?,?,?)', (child, parent, agent)); conn.commit(); conn.close()
        prompt = 'Review package: ' + Path(package['package']).name
        for cid, items in [(parent, [{'step_index': 0, 'type': 'USER_INPUT', 'content': '/upwork-init https://upwork.com/jobs/' + source()['job_id']},
                                    {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'self', 'Model': 'inherit', 'Prompt': prompt}]}}]}]),
                           (child, [{'step_index': 0, 'type': 'SYSTEM_MESSAGE', 'content': 'Review package: ' + Path(package['package']).name},
                                    {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': 'Independent report delivered.'}])]:
            file = backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text('\n'.join(json.dumps(x) for x in items) + '\n', encoding='utf-8')
        (backend / 'conversations').mkdir(exist_ok=True)
        if not (backend / 'conversations' / (parent + '.db')).exists():
            parent_conn = sqlite3.connect(backend / 'conversations' / (parent + '.db'))
            parent_conn.execute('CREATE TABLE steps (idx INTEGER,step_type INTEGER,status INTEGER)')
            parent_conn.execute('INSERT INTO steps VALUES (1,15,3)'); parent_conn.commit(); parent_conn.close()
        conn = sqlite3.connect(backend / 'conversations' / (child + '.db'))
        conn.execute('CREATE TABLE steps (idx INTEGER,step_type INTEGER,status INTEGER)')
        conn.execute('INSERT INTO steps VALUES (1,?,3)', (final_type,)); conn.commit(); conn.close()
        return home, backend, parent, child

    def test_af_or_terminal_quota_error_is_not_an_independent_completed_aa_review(self):
        package = flow.prepare_review(self.project, str(uuid.uuid4()))
        for agent, final in [('af-worker', 15), ('self', 17)]:
            home, backend, parent, child = self.native_fixture(package, agent=agent, final_type=final)
            with self.assertRaises(ValueError): native_review_proof(self.project, parent, child, backend=backend)

    def test_flash_request_or_observed_model_mismatch_is_rejected(self):
        package = flow.prepare_review(self.project, str(uuid.uuid4()))
        home, backend, parent, child = self.native_fixture(package)
        parent_log = backend / 'brain' / parent / '.system_generated/logs/transcript_full.jsonl'
        original = parent_log.read_text(encoding='utf-8')
        parent_log.write_text(original.replace('"Model": "inherit"', '"Model": "flash"'), encoding='utf-8')
        with self.assertRaises(ValueError): native_review_proof(self.project, parent, child, backend=backend)
        parent_log.write_text(original, encoding='utf-8')
        for cid, ident in [(parent, 100), (child, 101)]:
            conn = sqlite3.connect(backend / 'conversations' / (cid + '.db'))
            try:
                conn.execute('ALTER TABLE steps ADD COLUMN metadata BLOB')
                conn.execute('UPDATE steps SET metadata=?', (bytes([88, ident]),))
                conn.commit()
            finally: conn.close()
        with self.assertRaises(ValueError): native_review_proof(self.project, parent, child, backend=backend)

    def test_significant_risk_cannot_finish_with_one_independent_aa(self):
        self.valid_analysis()
        flow.resume(self.project, 'quota')
        self.put_project('ꘖ/KB/Evidence/init.json', '{}')
        self.put_project('ꘖ/KB/Evidence/research.json', '{}')
        flow.complete_stage(self.project, 'identity_init', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/init.json'])
        flow.complete_stage(self.project, 'research', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/research.json'])
        flow.complete_stage(self.project, 'analysis', ['ꘖ/project.json'], ['ꘖ/KB/Analysis.json'])
        package = flow.prepare_review(self.project, str(uuid.uuid4()), 'significant')
        home, backend, parent, child = self.native_fixture(package)
        with patch.object(Path, 'home', return_value=home):
            native = native_review_proof(self.project, parent, child)
            report = {'result': 'approved', 'scope': [*SECTIONS, 'kb_consistency'], 'findings': [], 'native_evidence': native['proof'], 'package': package['package']}
            self.put_project('ꘖ/KB/Evidence/Reviews/significant.json', json.dumps(report))
            flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/significant.json', parent_id=parent, reviewer_id=child)
            with self.assertRaises(ValueError):
                flow.complete_stage(self.project, 'review', ['ꘖ/KB/Analysis.json'], ['ꘖ/KB/Evidence/Reviews/significant.json'])

    def test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context(self):
        value = self.valid_analysis()
        publish_owned(self.project / 'ꘖ/KB/Analysis.md', render_analysis(value))
        flow.resume(self.project, 'quota', 'Продолжай анализ.')
        self.put_project('ꘖ/KB/Evidence/init-check.json', '{}')
        self.put_project('ꘖ/KB/Evidence/research-report.json', '{}')
        flow.complete_stage(self.project, 'identity_init', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/init-check.json'])
        flow.complete_stage(self.project, 'research', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/research-report.json'])
        flow.complete_stage(self.project, 'analysis', ['ꘖ/KB/Evidence/client.json'], ['ꘖ/KB/Analysis.json', 'ꘖ/KB/Analysis.md'])
        with self.assertRaises(ValueError): flow.complete_stage(self.project, 'review', ['ꘖ/KB/Analysis.json'], ['ꘖ/KB/Analysis.md'])
        package = flow.prepare_review(self.project, str(uuid.uuid4()))
        home, backend, parent, child = self.native_fixture(package)
        with patch.object(Path, 'home', return_value=home):
            native = native_review_proof(self.project, parent, child)
            report = {'result': 'approved', 'scope': [*SECTIONS, 'kb_consistency'], 'findings': [], 'native_evidence': native['proof'], 'package': package['package']}
            self.put_project('ꘖ/KB/Evidence/Reviews/report.json', json.dumps(report))
            flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/report.json', parent_id=parent, reviewer_id=child)
            flow.complete_stage(self.project, 'review', ['ꘖ/KB/Analysis.json'], ['ꘖ/KB/Evidence/Reviews/report.json'])
            flow.complete_stage(self.project, 'kb_review', flow.kb_paths(self.project), ['ꘖ/KB/Analysis.md'], note='Reviewed contradictions and missing evidence in the present KB')
            journal = self.project / 'ꙮ/1 - Анализ'
            record_step(journal, 'Продолжай анализ.', 'Final response exactly as saved')
            flow.complete_stage(self.project, 'finalize', flow.kb_paths(self.project), ['ꙮ/1 - Анализ/res/1.md'])
            self.assertTrue(all(x == 'complete' for x in flow.status(self.project)['stages'].values()))
            context = (self.project / 'ꙮ/0/Context.md').read_text(encoding='utf-8')
            self.assertIn('Final response exactly as saved', context)
            self.assertIn((self.project / 'ꘖ/KB/Progress.md').read_text(encoding='utf-8'), context)
            self.put_project('ꘖ/KB/Website.md', '# Сайт\nNew evidence changes this module\n')
            with self.assertRaises(ValueError): flow.complete_stage(self.project, 'review', ['ꘖ/KB/Analysis.json'], ['ꘖ/KB/Evidence/Reviews/report.json'])


class MetricsTests(TemporaryCase):
    def test_unknown_tokens_stay_unknown_and_duplicate_exports_are_not_summed(self):
        path = self.put('c-id/.system_generated/logs/transcript_full.jsonl', json.dumps({'type': 'PLANNER_RESPONSE', 'step_index': 1, 'input_tokens': 10, 'output_tokens': 4}) + '\n')
        result = summarize([path, path])
        self.assertEqual(result['tokens']['input_tokens']['complete_total'], 10)
        self.assertIsNone(result['tokens']['cache_read_tokens']['complete_total'])
        self.assertEqual(result['duplicate_records_ignored'], 1)
        self.assertEqual(result['generations'], 1)


if __name__ == '__main__':
    unittest.main()
