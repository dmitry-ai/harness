"""Cross-platform behavior: unchanged source data, native provenance and generated config."""

from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sqlite3
import tomllib
import unittest
from unittest.mock import patch
import uuid

from test_analysis_workflow import ProjectCase
from test_agent_tools import TemporaryCase
from test_onboarding import source
from agent_tools import configuration, runtime, metrics, workflow as flow, upwork_project as up
from agent_tools.platforms import codex
from agent_tools.analysis import publish_owned, render_analysis, SECTIONS


class ProjectionTests(TemporaryCase):
    def setUp(self):
        super().setUp()
        self.primary = self.root / 'canonical'
        for relative in ('rules', 'platforms', 'skills/upwork-init', 'agents'):
            (self.primary / relative).mkdir(parents=True, exist_ok=True)
        for path in runtime.PRIMARY.joinpath('rules').glob('*.md'):
            shutil.copyfile(path, self.primary / 'rules' / path.name)
        for relative in ('runtime.json', 'platforms/codex.md', 'skills/upwork-init/SKILL.md', 'agents/worker.md'):
            shutil.copyfile(runtime.PRIMARY / relative, self.primary / relative)
        self.output = self.root / 'workspace'

    def test_generation_is_idempotent_detects_source_changes_and_preserves_manual_edits(self):
        first = configuration.build_native(self.output, primary=self.primary)
        self.assertTrue(first['valid'])
        self.assertEqual(configuration.build_native(self.output, primary=self.primary)['written'], [])
        self.assertTrue(configuration.build_native(self.output, primary=self.primary, check=True)['valid'])
        rule = self.primary / 'rules/00-scope.md'
        rule.write_text(rule.read_text(encoding='utf-8') + '\nSpecific changed policy.\n', encoding='utf-8')
        self.assertFalse(configuration.build_native(self.output, primary=self.primary, check=True)['valid'])
        self.assertTrue(configuration.build_native(self.output, primary=self.primary)['valid'])
        generated = self.output / 'CODEX.md'
        generated.write_text('USER CHANGE', encoding='utf-8')
        result = configuration.build_native(self.output, primary=self.primary)
        self.assertFalse(result['valid'])
        self.assertEqual(generated.read_text(), 'USER CHANGE')

    def test_check_does_not_create_an_uninstalled_workspace(self):
        self.assertFalse(configuration.build_native(self.output, primary=self.primary, check=True)['valid'])
        self.assertFalse(self.output.exists())

    def test_first_install_preserves_an_unowned_antigravity_worker(self):
        worker = self.primary / 'agents/af-worker.md'
        worker.write_text('CUSTOM WORKER', encoding='utf-8')
        result = configuration.build_native(self.output, primary=self.primary)
        self.assertFalse(result['valid'])
        self.assertEqual(worker.read_text(), 'CUSTOM WORKER')

    def test_native_toml_preserves_settings_and_resolves_models_from_one_config(self):
        config = deepcopy(runtime.settings())
        config['platforms']['codex']['roles']['AA'].update(model='test-next-model', effort='high')
        with patch.object(runtime, 'settings', return_value=config), patch.object(configuration, 'settings', return_value=config):
            result = configuration.build_native(self.output, primary=self.primary)
        self.assertTrue(result['valid'])
        native_config = tomllib.loads((self.output / '.codex/config.toml').read_text())
        self.assertNotIn('model', native_config)
        self.assertNotIn('model_reasoning_effort', native_config)
        for name in ('upwork-aa', 'upwork-af'):
            value = tomllib.loads((self.output / f'.codex/agents/{name}.toml').read_text(encoding='utf-8'))
            self.assertNotIn('model', value)
            self.assertNotIn('model_reasoning_effort', value)
        with patch.object(runtime, 'settings', return_value=config):
            self.assertEqual(runtime.role_settings('codex', 'AF')['selection'], 'parent')
            self.assertNotIn('model', runtime.role_settings('codex', 'AF'))
        original = 'model = "user-selected"\n[projects."C:/elsewhere"]\ntrust_level = "trusted"\n'
        result = tomllib.loads(configuration._root_options(original))
        self.assertEqual(result['model'], 'user-selected')
        self.assertEqual(result['projects']['C:/elsewhere']['trust_level'], 'trusted')
        self.assertIn('CODEX.md', result['project_doc_fallback_filenames'])
        self.assertGreaterEqual(result['project_doc_max_bytes'], 65536)


class CodexEvidenceTests(ProjectCase):
    def setUp(self):
        super().setUp()
        self.home = self.root / 'codex-profile'
        self.home.mkdir()
        self.parent, self.child = str(uuid.uuid4()), str(uuid.uuid4())
        self.model = 'observed-parent-model'
        self.assignment = 'gAAAAA-native-encrypted-assignment'
        self.package = flow.prepare_review(self.project, self.parent)
        self.parent_rows = [self.meta(self.parent), self.context(),
            self.message('user', '  $upwork-init https://www.upwork.com/jobs/' + source()['job_id'] + '\nТочный текст.  '),
            {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'collaboration.spawn_agent',
             'call_id': 'spawn-reviewer', 'arguments': json.dumps({'task_name': 'reviewer',
              'message': self.assignment})}}]
        self.child_rows = [self.meta(self.child, self.parent), self.context(),
            {'type': 'response_item', 'payload': {'type': 'agent_message', 'author': '/root', 'recipient': '/root/reviewer',
             'content': [{'type': 'input_text', 'text': 'Message Type: NEW_TASK\nPayload:\n'},
                         {'type': 'encrypted_content', 'encrypted_content': self.assignment}]}},
            self.message('assistant', 'Reviewed.'),
            {'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': 'Reviewed.'}}]
        self.set_review_input(self.package)
        self.write_trace(self.parent, self.parent_rows)
        self.write_trace(self.child, self.child_rows)

    def meta(self, ident, parent=None):
        return {'type': 'session_meta', 'payload': {'id': ident, 'source':
            {'subagent': {'thread_spawn': {'parent_thread_id': parent, 'agent_path': '/root/reviewer'}}} if parent else 'vscode'}}

    def context(self):
        return {'type': 'turn_context', 'payload': {'model': self.model, 'effort': 'max'}}

    def message(self, role, text):
        return {'type': 'response_item', 'payload': {'type': 'message', 'role': role,
            'content': [{'type': 'input_text' if role == 'user' else 'output_text', 'text': text}]}}

    def set_review_input(self, package):
        with patch.dict('os.environ', {'CODEX_THREAD_ID': self.child}):
            receipt = flow.review_input(self.project, package['package'])
        self.child_rows = [item for item in self.child_rows if item.get('payload', {}).get('call_id') != 'review-input-call']
        self.child_rows[3:3] = [
            {'type': 'response_item', 'payload': {'type': 'custom_tool_call', 'call_id': 'review-input-call', 'name': 'exec',
             'input': f'python upwork_project.py review-input "{self.project}" --package "{package["package"]}" --platform codex'}},
            {'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'review-input-call',
             'output': [{'type': 'input_text', 'text': json.dumps(receipt)}]}}]

    def write_trace(self, ident, rows):
        path = self.home / 'sessions/2026/10/15' / (ident + '.jsonl')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in rows) + '\n', encoding='utf-8')
        connection = sqlite3.connect(self.home / 'state_5.sqlite')
        connection.execute('CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY, rollout_path TEXT, agent_path TEXT)')
        connection.execute('INSERT OR REPLACE INTO threads VALUES(?,?,?)', (ident, str(path), '/root/reviewer' if ident == self.child else None))
        connection.commit(); connection.close()
        return path

    @contextmanager
    def selected(self):
        config = runtime.platform_settings('codex')
        config['homes'] = {'C2': str(self.home)}
        with patch.object(codex, 'platform_settings', return_value=config), runtime.using('codex', 'C2'):
            yield

    def test_exact_user_text_job_scope_and_cross_platform_request_merge(self):
        other = str(uuid.uuid4())
        rows = [*self.parent_rows, self.message('user', 'Продолжай анализ.\n\nПосле сбоя.'),
                self.message('user', '/upwork-init https://www.upwork.com/jobs/~0299999'),
                self.message('user', 'Текст другого проекта.')]
        self.write_trace(self.parent, rows)
        requests = codex.native_requests(self.project, self.parent, backend=self.home)
        self.assertEqual(len(requests), 2)
        self.assertTrue(requests[0]['text'].startswith('  $upwork-init'))
        self.assertTrue(requests[0]['text'].endswith('  '))
        flow.resume(self.project, 'cross-system')
        flow.update(self.project, {'action': 'fixture'}, lambda state: state['requests'].append(
            {'id': 'antigravity-existing', 'text': 'Прежний точный запрос', 'native_conversation_id': other,
             'response_prepared': {'turn': 'old', 'steps': [1], 'sha256': 'kept'}}))
        with self.selected():
            flow.adopt_requests(self.project, self.parent)
            flow.adopt_requests(self.project, self.parent)
        saved = flow.load(self.project)['requests']
        self.assertEqual(len(saved), 3)
        self.assertEqual(saved[0]['response_prepared']['sha256'], 'kept')

    def test_review_provenance_checks_parent_completion_model_and_assignment(self):
        with self.selected():
            proof = metrics.native_review_proof(self.project, self.parent, self.child)
            self.assertEqual(proof['assignment_source'], 'matching-native-spawn-and-child-ciphertext')
            metrics.verify_native_proof(self.project, proof, package=Path(self.package['package']).name)
            with self.assertRaises(ValueError):
                metrics.verify_native_proof(self.project, proof, package='unassigned-package.json')
            proof['final_response_sha256'] = 'authored-assertion'
            with self.assertRaises(ValueError):
                metrics.verify_native_proof(self.project, proof)
        self.child_rows[-1]['payload']['type'] = 'turn_aborted'
        self.write_trace(self.child, self.child_rows)
        with self.assertRaises(ValueError):
            codex.native_review_proof(self.project, self.parent, self.child, backend=self.home)
        self.child_rows[-1]['payload']['type'] = 'task_complete'
        self.child_rows[1]['payload']['model'] = 'different-model'
        self.write_trace(self.child, self.child_rows)
        with self.assertRaises(ValueError):
            codex.native_review_proof(self.project, self.parent, self.child, backend=self.home)

    def test_parent_can_select_another_model_and_effort_with_native_proof(self):
        self.parent_rows[-1]['payload']['arguments'] = json.dumps({'task_name': 'reviewer', 'message': self.assignment,
            'model': 'context-selected-model', 'reasoning_effort': 'high', 'fork_turns': 'none'})
        self.write_trace(self.parent, self.parent_rows)
        self.child_rows[1]['payload'].update(model='context-selected-model', effort='high')
        self.write_trace(self.child, self.child_rows)
        with self.selected():
            proof = metrics.native_review_proof(self.project, self.parent, self.child)
            self.assertEqual(proof['model_selection']['selection'], 'explicit-parent-spawn')
            metrics.verify_native_proof(self.project, proof)

    def test_codex_token_metrics_use_response_usage_and_do_not_count_summaries(self):
        row = {'type': 'token_usage_record', 'payload': {'thread_id': self.child, 'turn_id': 'turn', 'response_id': 'response',
               'usage': {'input_tokens': 100, 'cached_input_tokens': 60, 'output_tokens': 7}}}
        path = self.write_trace(self.parent, [*self.parent_rows, self.meta(str(uuid.uuid4())), row, row,
            {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': {'input_tokens': 999}}}}])
        result = metrics.summarize([path], {self.child: [{'stage': 'review', 'first_step': 0, 'last_step': 1000}]})
        self.assertEqual(result['generations'], 1)
        self.assertEqual(result['duplicate_records_ignored'], 1)
        self.assertEqual(result['tokens']['input_tokens']['complete_total'], 100)
        self.assertEqual(result['tokens']['cache_read_tokens']['complete_total'], 60)
        self.assertEqual(result['phases']['review']['generations'], 1)

    def test_encrypted_assignment_or_missing_native_package_execution_cannot_prove_a_review(self):
        self.child_rows[2]['payload']['content'][1]['encrypted_content'] = 'different-assignment'
        self.write_trace(self.child, self.child_rows)
        with self.assertRaisesRegex(ValueError, 'Encrypted native spawn'):
            codex.native_review_proof(self.project, self.parent, self.child, backend=self.home)
        self.child_rows[2]['payload']['content'][1]['encrypted_content'] = self.assignment
        self.child_rows = [item for item in self.child_rows if item.get('payload', {}).get('type') != 'custom_tool_call_output']
        self.write_trace(self.child, self.child_rows)
        with self.assertRaisesRegex(ValueError, 'review-input execution'):
            codex.native_review_proof(self.project, self.parent, self.child, backend=self.home)

    def test_self_review_uses_codex_parent_evidence_without_requiring_antigravity(self):
        report = {'result': 'approved', 'scope': ['identity', 'concerns', 'misconceptions', 'causes', 'methods', 'kb_consistency'],
                  'findings': [], 'review_kind': 'self_review', 'package': self.package['package']}
        self.put_project('ꘖ/KB/Evidence/Reviews/self.json', json.dumps(report))
        with self.selected():
            flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/self.json', parent_id=self.parent, reviewer_id=self.parent)
        self.assertFalse(flow.load(self.project)['reviews'][0]['independent'])

    def test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply(self):
        value = self.valid_analysis()
        publish_owned(self.project / 'ꘖ/KB/Analysis.md', render_analysis(value))
        self.put_project('ꘖ/KB/Evidence/init.json', '{}')
        self.put_project('ꘖ/KB/Evidence/research.json', '{}')
        with self.selected():
            flow.resume(self.project, 'continue in Codex')
            flow.adopt_requests(self.project, self.parent)
            flow.complete_stage(self.project, 'identity_init', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/init.json'])
            flow.complete_stage(self.project, 'research', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/research.json'])
            flow.complete_stage(self.project, 'analysis', ['ꘖ/project.json'], ['ꘖ/KB/Analysis.json', 'ꘖ/KB/Analysis.md'])
            package = flow.prepare_review(self.project, self.parent)
            self.set_review_input(package)
            self.write_trace(self.child, self.child_rows)
            native = metrics.native_review_proof(self.project, self.parent, self.child)
            report = {'result': 'approved', 'scope': [*SECTIONS, 'kb_consistency'], 'findings': [],
                      'native_evidence': native['proof'], 'package': package['package']}
            self.put_project('ꘖ/KB/Evidence/Reviews/report.json', json.dumps(report))
            flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/report.json', parent_id=self.parent, reviewer_id=self.child)
            flow.complete_stage(self.project, 'review', ['ꘖ/KB/Analysis.json'], ['ꘖ/KB/Evidence/Reviews/report.json'])
            flow.complete_stage(self.project, 'kb_review', flow.kb_paths(self.project), ['ꘖ/KB/Analysis.md'], note='Checked current KB')
            answer = 'Точный окончательный ответ.\n\nБез реконструкции.'
            flow.record_current_answer(self.project, answer)
            flow.complete_stage(self.project, 'finalize', flow.kb_paths(self.project), ['ꙮ/1 - Анализ/res/1.md'])
            self.assertTrue(all(value == 'complete' for value in flow.status(self.project)['stages'].values()))
            flow.resume(self.project, 'another request', 'Новый точный запрос')
            self.assertEqual(flow.status(self.project)['next_stage'], 'finalize')
            self.put_project('ꘖ/data/registrations.json', json.dumps({'codex': {'complete': False,
                'profiles': {'C2': {'ready': False}}, 'status': 'pending'}}))
            self.assertEqual(flow.status(self.project)['next_stage'], 'identity_init')
            with self.assertRaisesRegex(ValueError, 'registration'):
                flow.complete_stage(self.project, 'identity_init', ['ꘖ/project.json'], ['ꘖ/KB/Evidence/init.json'])
        expected = self.parent_rows[2]['payload']['content'][0]['text']
        self.assertEqual((self.project / 'ꙮ/1 - Анализ/req/1.md').read_bytes().decode(), expected)
        context = (self.project / 'ꙮ/0/Context.md').read_text(encoding='utf-8')
        self.assertIn(expected, context)
        self.assertIn(answer, context)

    def test_second_platform_keeps_original_date_root_manual_kb_and_saved_snapshot(self):
        manual = self.project / 'KB/Project.md'
        manual.write_bytes(manual.read_bytes() + b'\nUSER TEXT\n')
        before = manual.read_bytes()
        state_before = json.loads((self.project / 'ꘖ/project.json').read_text(encoding='utf-8'))
        result = up.initialize_upwork_project(source()['job_id'], 'Different label', '2026-10-16',
            daily_root=self.root / 'daily', extracted_data=source(), register_native=False, platform='codex')
        self.assertEqual(Path(result['project_dir']), self.project)
        self.assertEqual(manual.read_bytes(), before)
        state = json.loads((self.project / 'ꘖ/project.json').read_text(encoding='utf-8'))
        self.assertEqual(state['request_date'], state_before['request_date'])
        self.assertEqual(state['snapshot'], state_before['snapshot'])
        self.assertIn('`Topic`', (self.project / 'CODEX.md').read_text(encoding='utf-8'))
