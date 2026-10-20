"""Continuation, exact journals, isolated examples and saved observation boundaries."""

from contextlib import redirect_stdout, closing
from copy import deepcopy
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sqlite3
import unittest
import uuid

from test_analysis_workflow import ProjectCase
from agent_tools import journal, storage, workflow as flow
from agent_tools.analysis import analysis_issues, save_analysis
from agent_tools.context import generate
from agent_tools.evidence import evidence_issues
from agent_tools.metrics import native_requests, project_metrics
from agent_tools.research import collect, collect_plan, capture_dom, select_dom_tab, extract_bytes, Response
from agent_tools import upwork_project as up


def varint(value):
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128); value >>= 7
    result.append(value)
    return bytes(result)


def message(field, payload):
    return varint(field * 8 + 2) + varint(len(payload)) + payload


class ResumeExportTests(ProjectCase):
    def request_database(self, texts, format_id=0):
        cid = str(uuid.uuid4())
        home = self.root / 'native-home'
        backend = home / '.gemini/antigravity'
        directory = backend / 'conversations'
        directory.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(directory / (cid + '.db'))) as conn:
            conn.execute('CREATE TABLE steps (idx INTEGER,step_type INTEGER,status INTEGER,step_format INTEGER,step_payload BLOB)')
            conn.executemany('INSERT INTO steps VALUES (?,14,3,?,?)',
                [(i, format_id, message(19, message(2, text.encode()))) for i, text in enumerate(texts)])
            conn.commit()
        return home, backend, cid

    def test_native_requests_preserve_exact_bytes_and_current_job_scope(self):
        texts = ['Other task', '/upwork-init https://www.upwork.com/jobs/' + up.normalize_job_id('~021234567890'),
                 'Продолжай анализ.\nПричина: Windows\n', '/upwork-init https://www.upwork.com/jobs/~029999999999', 'Continue unrelated job']
        home, backend, cid = self.request_database(texts)
        result = native_requests(self.project, cid, backend=backend)
        self.assertEqual([x['text'] for x in result], texts[1:3])
        self.assertEqual([x['native_step'] for x in result], [1, 2])
        self.assertEqual(result[1]['id'], cid + '-2')

    def test_unknown_native_format_does_not_reconstruct_request(self):
        home, backend, cid = self.request_database(['/upwork-init https://www.upwork.com/jobs/~021234567890'], format_id=7)
        with self.assertRaises(ValueError): native_requests(self.project, cid, backend=backend)

    def test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate(self):
        texts = ['/upwork-init https://www.upwork.com/jobs/~021234567890', 'Продолжай анализ.\n']
        home, backend, cid = self.request_database(texts)
        answer = 'Полный настоящий ответ. Client task.\n```text\nточно\n```\n'
        flow.resume(self.project, 'quota')
        with patch.object(Path, 'home', return_value=home):
            flow.adopt_requests(self.project, cid)
            package = self.review_package(cid, response=answer)
            report = self.review_report(package, self_review=True)
            path = self.put_project('ꘖ/KB/Evidence/Reviews/self.json', json.dumps(report))
            flow.record_review(self.project, path.relative_to(self.project).as_posix(), parent_id=cid, reviewer_id=cid)
            result = flow.record_current_answer(self.project, answer)
            self.assertFalse(result['delivery_verified'])
            flow.adopt_requests(self.project, cid)
            self.assertTrue(all(x.get('response_prepared') for x in flow.load(self.project)['requests']))
        directory = self.project / 'ꙮ/1 - Анализ'
        self.assertEqual(journal.get_existing_step_ids(directory), {1, 2})
        for index, text in enumerate(texts, 1):
            self.assertEqual((directory / 'req' / f'{index}.md').read_bytes(), text.encode())
            self.assertEqual((directory / 'res' / f'{index}.md').read_bytes(), answer.encode())
        target, content, sources = generate(self.project, self.project / '.agents/context.json')
        self.assertLess(content.index(texts[1]), content.index(answer))
        self.assertIn('one final answer shared', content)

    def test_group_crash_reserves_all_numbers_and_preserves_previous_context(self):
        directory = self.project / 'ꙮ/1 - Анализ'
        target = self.project / 'ꙮ/0/Context.md'
        previous = target.read_bytes()
        real = journal.create_bytes
        def fail_on_second_request(path, data):
            if Path(path) == directory / 'req/2.md':
                raise OSError('simulated power failure')
            return real(path, data)
        with patch.object(journal, 'create_bytes', side_effect=fail_on_second_request), self.assertRaises(OSError):
            journal.record_answer(directory, ['First exact request', 'Second exact request'], 'One final answer', 'turn-1')
        self.assertEqual(journal.get_existing_step_ids(directory), {1, 2})
        with self.assertRaises(ValueError): generate(self.project, self.project / '.agents/context.json')
        self.assertEqual(target.read_bytes(), previous)
        self.assertEqual(journal.record_step(directory, 'Unrelated later request', 'Later answer'), 3)
        self.assertEqual(journal.record_answer(directory, ['First exact request', 'Second exact request'], 'One final answer', 'turn-1'), [1, 2])
        self.assertEqual(journal.record_answer(directory, ['First exact request', 'Second exact request'], 'One final answer', 'turn-1'), [1, 2])
        self.assertEqual(len(journal.answer_groups(directory)), 1)
        with self.assertRaises(ValueError): journal.record_answer(directory, ['First exact request', 'Second exact request'], 'Changed answer', 'turn-1')

    def test_atomic_create_does_not_leave_a_partial_final_file(self):
        target = self.project / 'ꘖ/data/new-state.json'
        with patch.object(storage.os, 'fsync', side_effect=OSError('power failure')), self.assertRaises(OSError):
            storage.create_bytes(target, b'{"complete":true}')
        self.assertFalse(target.exists())
        storage.create_bytes(target, b'complete')
        with self.assertRaises(FileExistsError): storage.create_bytes(target, b'replacement')
        self.assertEqual(target.read_bytes(), b'complete')

    def test_analysis_commit_requires_current_hash_and_preserves_history(self):
        value = self.valid_review_analysis()
        target = self.project / 'ꘖ/KB/Analysis.json'
        original = target.read_bytes(); digest = hashlib.sha256(original).hexdigest()
        value['identity'][0]['essence'] = 'Corrected wording of the attributed title'
        candidate = self.put_project('ꘖ/data/candidate.json', json.dumps(value))
        with self.assertRaises(ValueError): save_analysis(self.project, candidate)
        result = save_analysis(self.project, candidate, digest)
        self.assertEqual((self.project / 'ꘖ/data/analysis-history' / (digest + '.json')).read_bytes(), original)
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), result['sha256'])
        target.write_bytes(b'{"manual_change":true}')
        with self.assertRaises(ValueError): save_analysis(self.project, candidate, result['sha256'])
        self.assertEqual(target.read_bytes(), b'{"manual_change":true}')

    def test_public_example_passes_structure_evidence_and_project_checks(self):
        directory = up.PRIMARY_AGENTS_DIR / 'skills/upwork-init/references'
        source = self.put_project('ꘖ/KB/Evidence/example-source.json', (directory / 'example-source.json').read_bytes())
        self.put_project('ꘖ/KB/Evidence/Examples/response.bin', (directory / 'example-source.json').read_bytes())
        self.put_project('ꘖ/KB/Evidence/Examples/observation.json', (directory / 'example-observation.json').read_bytes())
        value = json.loads((directory / 'analysis.example.json').read_text(encoding='utf-8'))
        self.put_project('ꘖ/KB/Analysis.json', json.dumps(value, ensure_ascii=False))
        self.assertEqual(analysis_issues(value), [])
        self.assertEqual(evidence_issues(self.project, value), [])
        from agent_tools.analysis import publish_analysis
        publish_analysis(self.project / 'ꘖ/KB/Analysis.json')
        self.assertTrue(flow.check_project(self.project)['valid'])

    def test_failed_extraction_keeps_saved_observation_and_reuses_it(self):
        calls = []
        def fetcher(*args):
            calls.append(args); return Response(args[0], 200, 'text/html', b'<h1>Not product JSON</h1>')
        plan = {'requests': [{'url': 'https://example.invalid/', 'profile': 'shopify'}]}
        result = collect_plan(self.project, plan, fetcher=fetcher)
        self.assertTrue(result['complete'])
        self.assertFalse(result['content_available_for_all'])
        self.assertIn('extraction_error', result['results'][0])
        self.assertTrue((self.project / 'ꘖ/KB' / result['results'][0]['observation']).exists())
        plan['requests'][0]['profile'] = 'html'
        retry = collect_plan(self.project, plan, fetcher=fetcher)
        self.assertTrue(retry['content_available_for_all'])
        self.assertEqual(len(calls), 1)
        observed = project_metrics(self.project)['collector']
        self.assertEqual((observed['fresh_attempts'], observed['cache_hits']), (1, 1))

    def test_collection_cli_signals_unavailable_content_with_saved_diagnostics(self):
        plan = self.put_project('ꘖ/data/plan.json', '{"requests":[{"url":"https://example.invalid/absent"}]}')
        from agent_tools import research
        for attempt in range(2):
            stream = StringIO()
            with patch.object(research, 'fetch', return_value=Response('https://example.invalid/absent', 404, 'text/plain', b'Not found')) as fetched, redirect_stdout(stream):
                code = up.main(['collect', str(self.project), '--plan', str(plan)])
            result = json.loads(stream.getvalue())
            self.assertEqual(code, 2)
            self.assertTrue(result['complete'])
            self.assertEqual(result['results'][0]['status'], 404)
            self.assertTrue((self.project / 'ꘖ/KB' / result['results'][0]['observation']).is_file())
            self.assertEqual(fetched.call_count, 1 if attempt == 0 else 0)

    def test_exact_dom_tab_is_read_without_inventing_http_status(self):
        tabs = [{'id': 'a', 'type': 'page', 'url': 'https://example.invalid/a'}]
        self.assertEqual(select_dom_tab(tabs, 'https://example.invalid/a#part', 'a'), tabs[0])
        with self.assertRaises(ValueError): select_dom_tab(tabs, 'https://example.invalid/b', 'a')
        from test_text_browser import dom_fixture
        guard, _ = dom_fixture(self.project, 'https://example.invalid/a', 'a', '<h1 id="a">Saved DOM</h1>')
        result = capture_dom(self.project, 'https://example.invalid/a', 'a', session_id='offline-dom', guard=guard)
        self.assertIsNone(result['status'])
        self.assertFalse(result['http_status_verified'])
        self.assertEqual(result['kind'], 'dom')

    def test_remote_json_pointer_checks_only_the_target_field(self):
        value = self.valid_analysis()
        collect(self.project, 'https://example.invalid/product.json', fetcher=lambda *args: Response(args[0], 200, 'application/json', b'{"a":"The concern","b":"Alternative"}'))
        value['concerns'][0]['for'][0]['source'] = 'https://example.invalid/product.json#/b'
        self.assertTrue(evidence_issues(self.project, value))
        value['concerns'][0]['for'][0]['source'] = 'https://example.invalid/product.json#/a'
        self.assertEqual(evidence_issues(self.project, value), [])

    def test_overview_and_nested_kb_module_change_invalidates_review_receipt(self):
        self.put_project('ꘖ/KB/.md', '# Overview\n')
        self.put_project('ꘖ/KB/Modules/pricing.md', '# Pricing\n')
        paths = flow.kb_paths(self.project)
        self.assertIn('ꘖ/KB/.md', paths)
        self.assertIn('ꘖ/KB/Modules/pricing.md', paths)
        receipt = {'kb_inputs': flow.hashes(self.project, paths)}
        self.assertTrue(flow.receipt_current(self.project, receipt))
        self.put_project('ꘖ/KB/.md', '# Updated overview\n')
        self.assertFalse(flow.receipt_current(self.project, receipt))

    def test_malformed_evidence_fields_return_diagnostics_without_crashing(self):
        value = self.valid_analysis()
        arg = value['causes'][0]['for'][0]
        arg['source_id'] = ['invalid']; arg.pop('source')
        arg['anchor_exception'] = 'invalid'
        self.assertTrue(analysis_issues(value))
        evidence_issues(self.project, value)
        self.put_project('ꘖ/data/invalid.json', json.dumps(value))
        stream = StringIO()
        with redirect_stdout(stream):
            code = up.main(['validate-analysis', str(self.project / 'ꘖ/data/invalid.json'), '--format', 'json', '--evidence'])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(stream.getvalue())['valid'])

    def test_routine_self_review_is_explicit_and_never_counts_as_independent(self):
        self.valid_analysis()
        home, backend, cid = self.request_database(['/upwork-init https://www.upwork.com/jobs/~021234567890'])
        flow.resume(self.project, 'quota')
        package = self.review_package(cid)
        report = self.review_report(package, self_review=True)
        self.put_project('ꘖ/KB/Evidence/Reviews/self.json', json.dumps(report))
        with patch.object(Path, 'home', return_value=home):
            flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/self.json', parent_id=cid, reviewer_id=cid)
        review = flow.load(self.project)['reviews'][0]
        self.assertFalse(review['independent'])
        self.assertEqual(review['risk'], 'routine')
        report.pop('review_kind')
        self.put_project('ꘖ/KB/Evidence/Reviews/self.json', json.dumps(report))
        with patch.object(Path, 'home', return_value=home), self.assertRaises(ValueError):
            flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/self.json', parent_id=cid, reviewer_id=cid)

    def test_tracking_extraction_handles_quoted_keys_and_declares_unparsed_js(self):
        value = extract_bytes(b'<script>{"webPixelsConfigList":[{"id":1}]};wpmLoader=window.cfg</script>', 'text/html', 'tracking')
        self.assertEqual(value['embedded_json']['webPixelsConfigList'], [[{'id': 1}]])
        self.assertEqual(value['embedded_json_unparsed'][0]['key'], 'wpmLoader')
        self.assertFalse(value['execution_checked'])

    def test_new_question_invalidates_completed_research_and_dependent_analysis(self):
        self.valid_review_analysis()
        flow.resume(self.project, 'quota')
        self.put_project('ꘖ/KB/Evidence/init.json', '{}')
        self.put_project('ꘖ/KB/Evidence/research.json', '{}')
        flow.complete_stage(self.project, 'identity_init', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/init.json'])
        flow.complete_stage(self.project, 'research', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/research.json'])
        flow.complete_stage(self.project, 'analysis', ['ꘖ/project.json'], ['ꘖ/KB/Analysis.json'])
        flow.add_question(self.project, 'Q-NEW', 'New material question', 'Could change the cause', 'Evidence or explicit gap', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/new.json'], requirements=[self.experiment_requirement()])
        flow.claim_question(self.project, 'Q-NEW', 'worker')
        statuses = flow.status(self.project)['stages']
        self.assertEqual(statuses['research'], 'stale')
        self.assertEqual(statuses['analysis'], 'stale')
        with self.assertRaises(ValueError):
            flow.complete_stage(self.project, 'review', ['ꘖ/KB/Analysis.json'], ['ꘖ/KB/Evidence/init.json'])

    def test_review_package_pins_primary_evidence_and_unquoted_new_contradiction(self):
        self.valid_analysis()
        parent = str(uuid.uuid4())
        package = self.review_package(parent)
        self.assertIn('ꘖ/KB/Evidence/client.json', package['evidence_inputs'])
        current = {'kb_inputs': package['kb_inputs'], 'evidence_inputs': package['evidence_inputs']}
        self.assertTrue(flow.receipt_current(self.project, current))
        self.put_project('ꘖ/KB/Evidence/client.json', '{"concern":"The concern","alternative":"Alternative","new":"Contradictory evidence"}')
        self.assertTrue(flow.check_project(self.project)['valid'])
        self.assertFalse(flow.receipt_current(self.project, current))
        updated = self.review_package(parent)
        self.assertNotEqual(package['package'], updated['package'])
        self.assertEqual(package['kb_inputs'], updated['kb_inputs'])


if __name__ == '__main__':
    unittest.main()
