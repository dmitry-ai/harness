"""Offline native-shaped fixtures for explicitly initialized text workspaces."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from agent_tools.platforms import antigravity, codex
from agent_tools.platforms.request_binding import native_project_id, scoped_inputs, text_project_id


class TextNativeBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'text-workspace'
        self.root.mkdir()
        self.marker = self.root / 'ꘖ/data/text-project.json'
        self.marker.parent.mkdir(parents=True)
        self.identity = {'schema_version': 1, 'kind': 'client_text_workspace',
                         'project_root': str(self.root.resolve()), 'id': text_project_id(self.root)}
        self.write_marker(self.identity)
        self.parent, self.child = str(uuid.uuid4()), str(uuid.uuid4())

    def write_marker(self, value):
        self.marker.write_text(json.dumps(value), encoding='utf-8')

    def test_internal_identity_is_explicit_and_validated_without_creating_upwork_state(self):
        self.assertEqual(native_project_id(self.root), self.identity['id'])
        self.assertTrue(native_project_id(self.root).startswith('text-'))
        self.assertFalse((self.root / 'ꘖ/project.json').exists())
        for bad in ({'schema_version': True}, {'schema_version': 2}, {'kind': 'upwork'},
                    {'project_root': str(self.base)}, {'project_root': '.'}, {'id': 'text-forged'}):
            self.write_marker({**self.identity, **bad})
            with self.assertRaises(ValueError):
                native_project_id(self.root)
        self.marker.unlink()
        with self.assertRaises(ValueError):
            native_project_id(self.root)

    def test_existing_real_job_identity_wins_and_invalid_job_file_cannot_fall_back(self):
        project = self.root / 'ꘖ/project.json'
        original = b'{"job_id":"~02123456","custom":"keep"}\n'
        project.write_bytes(original)
        self.assertEqual(native_project_id(self.root), '~02123456')
        self.assertEqual(project.read_bytes(), original)
        project.write_text('{"job_id":"text-forged"}', encoding='utf-8')
        with self.assertRaises(ValueError):
            native_project_id(self.root)

    def test_internal_id_mention_never_substitutes_for_actual_cwd_or_explicit_root(self):
        identifier = self.identity['id']
        selected, active, _ = scoped_inputs(self.root, identifier, [(1, 'Reference ' + identifier)])
        self.assertEqual(selected, [])
        self.assertFalse(active)
        request = f'Write an article.\nProject root: `{self.root}`'
        selected, active, _ = scoped_inputs(self.root, identifier, [(1, request)])
        self.assertEqual(selected[0][1], request)
        self.assertTrue(active)
        selected, active, _ = scoped_inputs(self.root, identifier, [(1, 'Write'),
            (2, '/upwork-init https://upwork.com/jobs/~0299999'), (3, 'Continue')],
            [(0, str(self.root), 'native-cwd'), (4, str(self.root), 'native-cwd')])
        self.assertEqual([item[1] for item in selected], ['Write'])
        self.assertFalse(active)

    def codex_fixture(self, cwd=None, request='  Exact article request.  '):
        home = self.base / 'codex-home'
        (home / 'sessions').mkdir(parents=True, exist_ok=True)
        package = self.root / 'ꘖ/KB/Evidence/Reviews/package.json'
        package.parent.mkdir(parents=True, exist_ok=True)
        package.write_text('{"fixture":"immutable review package"}', encoding='utf-8')
        assignment = 'Review ' + package.relative_to(self.root).as_posix()
        context = {'type': 'turn_context', 'payload': {'model': 'fixture-model', 'effort': 'high',
                                                      'cwd': str(cwd or self.root)}}
        parent = [{'type': 'session_meta', 'payload': {'id': self.parent, 'cwd': str(cwd or self.root), 'source': 'vscode'}},
                  context, {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                    'content': [{'type': 'input_text', 'text': request}],
                    'internal_chat_message_metadata_passthrough': {'content_item_kinds': ['user.text']}}},
                  {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'collaboration.spawn_agent',
                    'call_id': 'spawn', 'arguments': json.dumps({'task_name': 'reviewer', 'message': assignment})}}]
        receipt = {'upwork_review_input': 1, 'verified': True, 'reviewer_id': self.child,
            'parent_id': self.parent, 'project_root': str(self.root.resolve()),
            'package': package.relative_to(self.root).as_posix(), 'package_sha256': hashlib.sha256(package.read_bytes()).hexdigest()}
        child = [{'type': 'session_meta', 'payload': {'id': self.child, 'cwd': str(self.root),
            'source': {'subagent': {'thread_spawn': {'parent_thread_id': self.parent, 'agent_path': '/root/reviewer'}}}}},
            deepcopy(context), {'type': 'response_item', 'payload': {'type': 'custom_tool_call',
                'name': 'exec', 'call_id': 'package-input', 'input': 'review-input --package ' + receipt['package']}},
            {'type': 'response_item', 'payload': {'type': 'custom_tool_call_output',
                'call_id': 'package-input', 'output': json.dumps(receipt)}},
            {'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': 'Review result fixture'}}]
        connection = sqlite3.connect(home / 'state_5.sqlite')
        connection.execute('CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY, rollout_path TEXT, agent_path TEXT)')
        for ident, rows, path in ((self.parent, parent, None), (self.child, child, '/root/reviewer')):
            log = home / 'sessions' / f'{ident}.jsonl'
            log.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
            connection.execute('INSERT OR REPLACE INTO threads VALUES(?,?,?)', (ident, str(log), path))
        connection.commit()
        connection.close()
        return home

    def antigravity_fixture(self):
        backend = self.base / 'antigravity'
        (backend / 'conversations').mkdir(parents=True)
        connection = sqlite3.connect(backend / 'conversation_summaries.db')
        connection.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,agent_name TEXT,workspace_uris TEXT)')
        for ident, parent, agent in ((self.parent, '', ''), (self.child, self.parent, 'self')):
            connection.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?)',
                               (ident, parent, agent, json.dumps([self.root.as_uri()])))
            database = sqlite3.connect(backend / 'conversations' / f'{ident}.db')
            database.execute('CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, metadata BLOB)')
            database.execute('INSERT INTO steps VALUES(1,15,3,NULL)')
            database.commit()
            database.close()
        connection.commit()
        connection.close()
        prompt = 'Review fixture-package.json'
        parent = [{'step_index': 0, 'type': 'USER_INPUT', 'content': '  Exact article request.  '},
            {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'invoke_subagent',
             'args': {'Subagents': [{'TypeName': 'self', 'Model': 'inherit', 'Prompt': prompt}]}}]}]
        child = [{'step_index': 0, 'type': 'SYSTEM_MESSAGE', 'content': prompt},
                 {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': 'Review result fixture'}]
        for ident, rows in ((self.parent, parent), (self.child, child)):
            log = backend / 'brain' / ident / '.system_generated/logs/transcript_full.jsonl'
            log.parent.mkdir(parents=True)
            log.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
        return backend

    def test_codex_requests_preserve_exact_text_without_analysis_project(self):
        home = self.codex_fixture()
        requests = codex.native_requests(self.root, self.parent, backend=home)
        self.assertEqual([request['text'] for request in requests], ['  Exact article request.  '])
        self.assertEqual(requests[0]['project_binding']['kind'], 'codex-session-cwd')
        self.codex_fixture(cwd=self.base)
        with self.assertRaises(ValueError):
            codex.native_requests(self.root, self.parent, backend=home)
        exact = f'Write an article.\nКорень проекта: `{self.root}`'
        self.codex_fixture(cwd=self.base, request=exact)
        self.assertEqual(codex.native_requests(self.root, self.parent, backend=home)[0]['text'], exact)

    def test_antigravity_scope_uses_workspace_or_explicit_root_for_text(self):
        backend = self.antigravity_fixture()
        selected, active, _ = antigravity._request_scope(self.root, self.parent, backend,
                                                       inputs=[(0, 'Exact article request')])
        self.assertEqual(selected[0][1], 'Exact article request')
        self.assertTrue(active)
        connection = sqlite3.connect(backend / 'conversation_summaries.db')
        connection.execute('UPDATE conversation_summaries SET workspace_uris=? WHERE conversation_id=?',
                           (json.dumps([self.base.as_uri()]), self.parent))
        connection.commit()
        connection.close()
        selected, active, _ = antigravity._request_scope(self.root, self.parent, backend,
                                                       inputs=[(0, 'Exact article request')])
        self.assertEqual(selected, [])
        exact = f'Write an article.\nProject root: `{self.root}`'
        selected, active, _ = antigravity._request_scope(self.root, self.parent, backend, inputs=[(0, exact)])
        self.assertEqual(selected[0][1], exact)
        self.assertTrue(active)

    def test_codex_native_review_for_text_has_no_fabricated_upwork_job(self):
        home = self.codex_fixture()
        proof = codex.native_review_proof(self.root, self.parent, self.child, backend=home, write=False)
        self.assertEqual(proof['status'], 'completed')
        self.assertEqual(proof['project_id'], self.identity['id'])
        self.assertEqual(proof['project_kind'], 'client_text_workspace')
        self.assertIsNone(proof['job_id'])
        self.assertFalse((self.root / 'ꘖ/project.json').exists())
        self.codex_fixture(cwd=self.base)
        with self.assertRaises(ValueError):
            codex.native_review_proof(self.root, self.parent, self.child, backend=home, write=False)

    def test_antigravity_native_review_for_text_uses_actual_workspace_binding(self):
        backend = self.antigravity_fixture()
        proof = antigravity.native_review_proof(self.root, self.parent, self.child, backend=backend, write=False)
        self.assertEqual(proof['status'], 'completed')
        self.assertEqual(proof['project_id'], self.identity['id'])
        self.assertEqual(proof['project_kind'], 'client_text_workspace')
        self.assertIsNone(proof['job_id'])
        self.assertFalse((self.root / 'ꘖ/project.json').exists())
        connection = sqlite3.connect(backend / 'conversation_summaries.db')
        connection.execute('UPDATE conversation_summaries SET workspace_uris=? WHERE conversation_id=?',
                           (json.dumps([self.base.as_uri()]), self.parent))
        connection.commit()
        connection.close()
        with self.assertRaises(ValueError):
            antigravity.native_review_proof(self.root, self.parent, self.child, backend=backend, write=False)


if __name__ == '__main__':
    unittest.main()
