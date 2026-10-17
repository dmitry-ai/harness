"""Publication outcomes, bounded diagnostics, and disposable input safety."""

from copy import deepcopy
import io
import json
from types import SimpleNamespace
from unittest.mock import patch

from test_analysis_workflow import ProjectCase
from test_onboarding import claim, source
from test_evidence_contract import v3_analysis
from agent_tools import operations, workflow, research
from agent_tools.analysis import analysis_issues, publish_analysis
from agent_tools.knowledge import sync_website_card


class PublicationLifecycleTests(ProjectCase):
    def valid_analysis(self):
        value = v3_analysis(self.project, super().valid_analysis())
        self.put_project('ꘖ/KB/Analysis.json', json.dumps(value, ensure_ascii=False))
        return value

    def test_creation_publishes_supplied_site_and_reinit_keeps_the_card(self):
        from agent_tools.upwork_project import initialize_upwork_project
        hypothesis = {**claim('H-SITE-1'), 'website_url': 'https://example.org/'}
        data = source()
        kwargs = dict(domain_or_topic='Known', extracted_data=data, daily_root=self.root / 'new-daily', register_native=False)
        result = initialize_upwork_project(data['job_id'], site_hypothesis=hypothesis, **kwargs)
        from pathlib import Path
        card = Path(result['project_dir']) / '.md'
        self.assertIn('https://example.org/', card.read_text(encoding='utf-8'))
        self.assertIn('KB/Project.md#13-сайт', card.read_text(encoding='utf-8'))
        from agent_tools.links import validate_file
        self.assertEqual(validate_file(card, local_anchors=True), [])
        previous = card.read_bytes()
        initialize_upwork_project(data['job_id'], **kwargs)
        self.assertEqual(card.read_bytes(), previous)

    def test_explicit_website_is_published_and_reused_without_overwriting_card_or_metadata(self):
        value = self.valid_analysis()
        value['identity'] = [claim('H-SITE-1')]
        ident = value['identity'][0]['id']
        value['websites'] = [{'url': 'https://example.org/', 'role': 'target', 'basis_id': ident}]
        value = v3_analysis(self.project, value)
        source = self.project / 'ꘖ/KB/Analysis.json'
        source.write_text(json.dumps(value), encoding='utf-8')
        card = self.project / '.md'
        original = card.read_bytes()
        old_state = json.loads((self.project / 'ꘖ/project.json').read_text())
        result = publish_analysis(source)
        self.assertNotEqual(result['status'], 'conflict', result)
        current = card.read_bytes()
        self.assertIn(b'https://example.org/', current)
        self.assertIn(original.splitlines()[-1], current)
        self.assertIn('ꘖ/KB/Analysis.json#/identity/0', current.decode())
        for key, expected in old_state.items():
            self.assertEqual(json.loads((self.project / 'ꘖ/project.json').read_text())[key], expected)
        del value['websites']
        self.assertEqual(sync_website_card(self.project, value)['status'], 'unchanged')
        value['identity'][0]['essence'] += ' New contradictory evidence.'
        self.assertEqual(sync_website_card(self.project, value)['status'], 'conflict')
        self.assertEqual(card.read_bytes(), current)

    def test_website_requires_valid_url_and_identity_basis(self):
        value = self.valid_analysis()
        value['identity'] = [claim('H-SITE-1')]
        for site in ({'url': 'file:///x', 'role': 'target', 'basis_id': value['identity'][0]['id']},
                     {'url': 'https://example.org/', 'role': 'client', 'basis_id': 'MISSING'}):
            candidate = deepcopy(value)
            candidate['websites'] = [site]
            self.assertTrue(analysis_issues(candidate))
        for malformed in ({'websites': [{'url': 123, 'role': 'target', 'basis_id': 'H-SITE-1'}]},
                          {'identity': None, 'websites': [{'url': None, 'role': 'target', 'basis_id': []}]}):
            self.assertTrue(analysis_issues({**value, **malformed}))

    def test_new_analysis_cannot_finish_with_an_unpublished_website_card(self):
        value = self.valid_analysis()
        value['identity'] = [claim('H-SITE-1')]
        value = v3_analysis(self.project, value)
        path = self.project / 'ꘖ/KB/Analysis.json'
        path.write_text(json.dumps(value), encoding='utf-8')
        self.assertIn('project.website', {x['code'] for x in workflow.check_project(self.project)['issues']})
        value['websites'] = [{'url': None, 'role': 'target', 'basis_id': 'H-SITE-1'}]
        path.write_text(json.dumps(value), encoding='utf-8')
        publish_analysis(path)
        self.assertNotIn('project.website', {x['code'] for x in workflow.check_project(self.project)['issues']})

    def test_stdin_analysis_and_owned_scratch_inputs_leave_no_permanent_candidate(self):
        value = self.valid_analysis()
        source = self.project / 'ꘖ/KB/Analysis.json'
        source.unlink()
        args = SimpleNamespace(command='save-analysis', project=self.project, candidate='-', expected_sha256=None, consume_input=False)
        stdin = io.TextIOWrapper(io.BytesIO(json.dumps(value).encode()), encoding='utf-8')
        with patch('sys.stdin', stdin):
            result = operations.execute(args)
        self.assertTrue(source.is_file())
        self.assertFalse((self.project / '-').exists())
        scratch = self.put_project('ꘖ/data/scratch/candidate.json', json.dumps(value))
        args.candidate, args.consume_input, args.expected_sha256 = scratch.relative_to(self.project).as_posix(), True, result['sha256']
        operations.execute(args)
        self.assertFalse(scratch.exists())

    def test_website_and_red_flags_have_stable_order_and_preserve_manual_edits(self):
        value = self.valid_analysis()
        value['identity'] = [claim('H-SITE-1')]
        value['websites'] = [{'url': None, 'role': 'target', 'basis_id': 'H-SITE-1'}]
        value['red_flags'] = [{'id': 'RF-WEBSITE-UNIDENTIFIED', 'status': 'unresolved', 'summary': 'No established site.', 'basis_ids': ['H-SITE-1']}]
        value = v3_analysis(self.project, value)
        path = self.project / 'ꘖ/KB/Analysis.json'
        path.write_text(json.dumps(value), encoding='utf-8')
        publish_analysis(path)
        card = self.project / '.md'
        original = card.read_bytes()
        publish_analysis(path)
        self.assertEqual(card.read_bytes(), original)
        self.assertLess(original.index(b'websites:start'), original.index(b'red-flags:start'))
        self.assertLess(original.index(b'# Red Flags'), original.index(b'red-flags:start'))
        self.assertTrue(original.rstrip().endswith(b'<!-- upwork-init:red-flags:end -->'))
        card.write_bytes(original.replace(b'No established site.', b'USER ASSESSMENT'))
        changed = card.read_bytes()
        self.assertEqual(publish_analysis(path)['status'], 'conflict')
        self.assertEqual(card.read_bytes(), changed)

    def test_invalid_consumption_scope_fails_before_analysis_changes(self):
        value = self.valid_analysis()
        source = self.project / 'ꘖ/KB/Analysis.json'
        original = source.read_bytes()
        candidate = self.put_project('ꘖ/data/manual-candidate.json', json.dumps(value))
        args = SimpleNamespace(command='save-analysis', project=self.project, candidate=str(candidate), expected_sha256=None, consume_input=True)
        with self.assertRaisesRegex(ValueError, 'scratch'):
            operations.execute(args)
        self.assertEqual(source.read_bytes(), original)
        self.assertTrue(candidate.exists())

    def test_failed_or_changed_input_is_retained(self):
        path = self.put_project('ꘖ/data/scratch/plan.json', '{}')
        args = SimpleNamespace(project=self.project, consume_input=True)
        operations._consumed(args, path, b'{}', {'complete': False})
        self.assertTrue(path.exists())
        path.write_bytes(b'USER CHANGE')
        operations._consumed(args, path, b'{}', {'complete': True})
        self.assertEqual(path.read_bytes(), b'USER CHANGE')

    def test_collect_receipt_preserves_plan_after_input_is_consumed(self):
        path = self.put_project('ꘖ/data/scratch/plan.json', '{"requests": []}')
        args = SimpleNamespace(command='collect', project=self.project, plan=path, output='ꘖ/KB/Evidence/report.json', consume_input=True)
        with patch.object(research, 'collect_plan', return_value={'results': [], 'complete': True}):
            operations.execute(args)
        self.assertFalse(path.exists())
        receipts = json.loads((self.project / 'ꘖ/data/rendered.json').read_text())
        source = receipts[str(self.project / args.output)]['source']
        self.assertEqual(source['plan'], {'requests': []})
        self.assertEqual(source['kind'], 'collection-plan')

    def test_progress_is_replaced_without_archiving_derived_navigation(self):
        state = workflow.load(self.project)
        workflow.publish_progress(self.project, state)
        state['questions']['Q'] = {'id': 'Q', 'question': 'Q?', 'status': 'pending', 'done_when': 'Done'}
        workflow.publish_progress(self.project, state)
        self.assertFalse((self.project / 'ꘖ/data/render-history').exists())

    def test_collector_retains_totals_and_only_32_recent_diagnostics(self):
        path = self.project / 'ꘖ/data/research-metrics.json'
        path.write_text(json.dumps([{'cached': True}, {'cached': False, 'error': 'old failure'}]))
        for number in range(40):
            research.observed_use(self.project, {'url': f'https://example.org/{number}', 'cached': False, 'kind': 'http', 'status': 200})
        value = json.loads(path.read_text())
        self.assertEqual(len(value['recent']), 32)
        self.assertEqual(value['totals'], {'uses': 42, 'cache_hits': 1, 'fresh_attempts': 41, 'failed_attempts': 1, 'http_unavailable': 0})
