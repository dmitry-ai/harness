# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate token/stage summarize, native_review_proof, read-only SQLite, file:// helpers, and ProjectCleanupScanner across trace_common.py, antigravity.py, codex.py, metrics.py, and cleanup.py":
# https://github.com/dmitry-ai/harness/issues/75
# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import uuid
from unittest.mock import patch
from test_analysis_workflow import ProjectCase
from agent_tools import runtime, workflow as flow
from agent_tools.analysis import SECTIONS
from agent_tools.platforms import codex, antigravity
class CodexContinuationTests(ProjectCase):
	def setUp(self):
		super().setUp()
		self.home = self.root / 'codex'
		self.home.mkdir()
		self.parent, self.child = (str(uuid.uuid4()), str(uuid.uuid4()))
		flow.resume(self.project, 'native fixture', '  Continue analysis.\nAfter outage.  ')
		self.package = self.review_package(self.parent)
		self.parent_rows = [self.meta(self.parent, self.project), self.context(self.project), self.message('  Continue analysis.\nAfter outage.  '), {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'collaboration.spawn_agent', 'call_id': 'spawn', 'arguments': json.dumps({'task_name': 'audit', 'message': 'Review ' + self.package['package']})}}]
		with patch.dict(os.environ, {'CODEX_THREAD_ID': self.child}):
			receipt = flow.review_input(self.project, self.package['package'])
		self.child_rows = [self.meta(self.child, self.project, parent=self.parent), self.context(self.project), {'type': 'response_item', 'payload': {'type': 'custom_tool_call', 'name': 'exec', 'call_id': 'read-package', 'input': 'review-input --package ' + self.package['package']}}, {'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'read-package', 'output': json.dumps(receipt)}}, {'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': 'Reviewed'}}]
		self.write(self.parent, self.parent_rows)
		self.write(self.child, self.child_rows)
	def meta(self, ident, cwd, parent=None):
		return {'type': 'session_meta', 'payload': {'id': ident, 'cwd': str(cwd), 'source': {'subagent': {'thread_spawn': {'parent_thread_id': parent, 'agent_path': '/root/audit'}}} if parent else 'vscode'}}
	def context(self, cwd, turn='turn-a'):
		return {'type': 'turn_context', 'payload': {'model': 'fixture-model', 'effort': 'max', 'cwd': str(cwd), 'turn_id': turn}}
	def message(self, text, kinds=('user.text',), turn='turn-a'):
		payload = {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': text}]}
		if None is not kinds:
			payload['internal_chat_message_metadata_passthrough'] = {'content_item_kinds': list(kinds), 'turn_id': turn}
		r = {'type': 'response_item', 'payload': payload}
		return r
	def write(self, ident, rows):
		path = self.home / 'sessions' / (ident + '.jsonl')
		path.parent.mkdir(exist_ok=True)
		path.write_text('\n'.join((json.dumps(item, ensure_ascii=False) for item in rows)) + '\n', encoding='utf-8')
		conn = sqlite3.connect(self.home / 'state_5.sqlite')
		conn.execute('CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY,rollout_path TEXT,agent_path TEXT)')
		conn.execute('INSERT OR REPLACE INTO threads VALUES(?,?,?)', (ident, str(path), '/root/audit' if ident == self.child else None))
		conn.commit()
		conn.close()
	@contextmanager
	def selected(self):
		config = runtime.platform_settings('codex')
		config['homes'] = {'C2': str(self.home)}
		with patch.object(codex, 'platform_settings', return_value=config), runtime.using('codex', 'C2'):
			yield
	def report(self):
		return self.review_report(self.package, self_review=True)
	def test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds(self):
		requests = codex.native_requests(self.project, self.parent, backend=self.home)
		self.assertEqual([item['text'] for item in requests], ['  Continue analysis.\nAfter outage.  '])
		self.assertEqual(requests[0]['project_binding']['kind'], 'codex-session-cwd')
		with self.selected():
			flow.adopt_requests(self.project, self.parent)
			self.package = self.review_package(self.parent)
			self.put_project('ꘖ/KB/Evidence/Reviews/self.json', json.dumps(self.report()))
			flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/self.json', parent_id=self.parent, reviewer_id=self.parent)
			proof = codex.native_review_proof(self.project, self.parent, self.child, backend=self.home, write=False)
		self.assertEqual(proof['status'], 'completed')
		self.assertFalse(flow.load(self.project)['reviews'][0]['independent'])
	def test_same_words_in_another_native_root_do_not_establish_ownership(self):
		rows = [self.meta(self.parent, self.root), self.context(self.root), self.message('  Continue analysis.\nAfter outage.  ')]
		self.write(self.parent, rows)
		with self.assertRaises(ValueError):
			codex.native_requests(self.project, self.parent, backend=self.home)
		with self.assertRaises(ValueError):
			codex.require_current_binding(self.project, self.parent, backend=self.home)
	def test_changed_cwd_before_and_after_user_input_does_not_import_foreign_turn(self):
		rows = [self.meta(self.parent, self.project), self.context(self.project), self.message('Own first'), self.message('Foreign before its native context', turn='turn-b'), self.context(self.root, 'turn-b'), self.message('Foreign after context', turn='turn-b'), self.context(self.project, 'turn-c'), self.message('Own again', turn='turn-c')]
		self.write(self.parent, rows)
		requests = codex.native_requests(self.project, self.parent, backend=self.home)
		self.assertEqual([item['text'] for item in requests], ['Own first', 'Own again'])
	def test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews(self):
		rows = [*self.parent_rows[:-1], self.message('/upwork-init https://www.upwork.com/jobs/~0299999'), self.context(self.project), self.message('Continue analysis.'), self.parent_rows[-1]]
		self.write(self.parent, rows)
		self.assertEqual(len(codex.native_requests(self.project, self.parent, backend=self.home)), 1)
		with self.assertRaises(ValueError):
			codex.native_review_proof(self.project, self.parent, self.child, backend=self.home, write=False)
		self.put_project('ꘖ/KB/Evidence/Reviews/self.json', json.dumps(self.report()))
		with self.selected(), self.assertRaises(ValueError):
			flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/self.json', parent_id=self.parent, reviewer_id=self.parent)
	def test_injected_rules_and_environment_are_excluded_but_user_text_is_unchanged(self):
		rules = '# AGENTS.md instructions for ' + str(self.project) + '\n<INSTRUCTIONS>text</INSTRUCTIONS>'
		literal_environment = '<environment_context>quoted by user</environment_context>'
		rows = [self.meta(self.parent, self.project), self.context(self.project), self.message(rules, ('agents_md.instructions',)), self.message('<environment_context>injected</environment_context>', ('environments.environment_context',)), self.message(rules), self.message(literal_environment), self.message(rules, kinds=None)]
		self.write(self.parent, rows)
		requests = codex.native_requests(self.project, self.parent, backend=self.home)
		self.assertEqual([item['text'] for item in requests], [rules, literal_environment])
	def test_missing_native_root_keeps_legacy_job_id_but_foreign_root_does_not(self):
		rows = [self.meta(self.parent, self.root), self.message('Reference ' + flow.load(self.project)['job_id'])]
		self.write(self.parent, rows)
		with self.assertRaises(ValueError):
			codex.native_requests(self.project, self.parent, backend=self.home)
		del rows[0]['payload']['cwd']
		self.write(self.parent, rows)
		self.assertEqual(len(codex.native_requests(self.project, self.parent, backend=self.home)), 1)
		rows += [self.message('/upwork-init https://www.upwork.com/jobs/~0299999'), self.message('Reference again ' + flow.load(self.project)['job_id']), self.message('Continue analysis.')]
		self.write(self.parent, rows)
		self.assertEqual(len(codex.native_requests(self.project, self.parent, backend=self.home)), 1)
		with self.assertRaises(ValueError):
			codex.require_current_binding(self.project, self.parent, backend=self.home)
def wire(field, payload):
	def encode(value):
		encoded = bytearray()
		while value >= 128:
			encoded.append(value & 127 | 128)
			value >>= 7
		encoded.append(value)
		r = bytes(encoded)
		return r
	return encode(field << 3 | 2) + encode(len(payload)) + payload
class AntigravityContinuationTests(ProjectCase):
	def setUp(self):
		super().setUp()
		self.home = self.root / 'ag-home'
		self.backend = self.home / '.gemini/antigravity'
		(self.backend / 'conversations').mkdir(parents=True)
		self.parent, self.child = (str(uuid.uuid4()), str(uuid.uuid4()))
		self.package = self.review_package(self.parent)
		conn = sqlite3.connect(self.backend / 'conversation_summaries.db')
		conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,agent_name TEXT,workspace_uris TEXT)')
		conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?)', (self.parent, '', '', json.dumps([self.project.as_uri()])))
		conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?)', (self.child, self.parent, 'self', json.dumps([self.project.as_uri()])))
		conn.commit()
		conn.close()
		self.inputs(['  Continue analysis.\nAfter outage.  '])
	def workspace(self, paths):
		conn = sqlite3.connect(self.backend / 'conversation_summaries.db')
		conn.execute('UPDATE conversation_summaries SET workspace_uris=? WHERE conversation_id=?', (json.dumps([path.as_uri() for path in paths]), self.parent))
		conn.commit()
		conn.close()
	def inputs(self, texts):
		conn = sqlite3.connect(self.backend / 'conversations' / (self.parent + '.db'))
		conn.execute('CREATE TABLE IF NOT EXISTS steps(idx INTEGER,step_type INTEGER,status INTEGER,step_format INTEGER,step_payload BLOB,metadata BLOB)')
		conn.execute('DELETE FROM steps')
		for i, text in enumerate(texts):
			conn.execute('INSERT INTO steps VALUES(?,14,3,0,?,NULL)', (i, wire(19, wire(2, text.encode()))))
		conn.commit()
		conn.close()
		prompt = 'Review ' + self.package['package']
		parent = [{'step_index': i, 'type': 'USER_INPUT', 'content': text} for i, text in enumerate(texts)]
		parent.append({'step_index': len(texts), 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'self', 'Model': 'inherit', 'Prompt': prompt}]}}]})
		child = [{'step_index': 0, 'type': 'SYSTEM_MESSAGE', 'content': prompt}, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': 'Reviewed'}]
		for cid, rows in [(self.parent, parent), (self.child, child)]:
			log = self.backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
			log.parent.mkdir(parents=True, exist_ok=True)
			log.write_text('\n'.join((json.dumps(row, ensure_ascii=False) for row in rows)) + '\n', encoding='utf-8')
		conn = sqlite3.connect(self.backend / 'conversations' / (self.child + '.db'))
		conn.execute('CREATE TABLE IF NOT EXISTS steps(idx INTEGER,step_type INTEGER,status INTEGER)')
		conn.execute('DELETE FROM steps')
		conn.execute('INSERT INTO steps VALUES(1,15,3)')
		conn.commit()
		conn.close()
	def test_exact_native_workspace_allows_plain_continuation_and_independent_review(self):
		requests = antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.assertEqual(requests[0]['text'], '  Continue analysis.\nAfter outage.  ')
		self.assertEqual(requests[0]['project_binding']['kind'], 'antigravity-workspace-uris')
		proof = antigravity.native_review_proof(self.project, self.parent, self.child, backend=self.backend, write=False)
		self.assertEqual(proof['status'], 'completed')
	def test_foreign_or_multiple_native_workspaces_cannot_claim_identical_request(self):
		for paths in ([self.root], [self.project, self.root]):
			self.workspace(paths)
			with self.assertRaises(ValueError):
				antigravity.native_requests(self.project, self.parent, backend=self.backend)
	def test_explicit_exact_root_binds_generic_workspace_without_rewriting_user_text(self):
		self.workspace([self.root])
		request = f'Continue analysis.\nProject root: `{self.project}`'
		self.inputs([request])
		saved = antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.assertEqual(saved[0]['text'], request)
		self.assertEqual(saved[0]['project_binding']['kind'], 'explicit-project-root')
		self.assertEqual(antigravity.native_review_proof(self.project, self.parent, self.child, backend=self.backend, write=False)['status'], 'completed')
	def test_wrong_explicit_root_or_foreign_job_does_not_claim_parent_or_self_review(self):
		for request in (f'Continue analysis.\nProject root: `{self.root}`', '/upwork-init https://www.upwork.com/jobs/~0299999'):
			self.inputs(['Own request', request, 'Continue analysis.'])
			self.assertEqual(len(antigravity.native_requests(self.project, self.parent, backend=self.backend)), 1)
			with self.assertRaises(ValueError):
				antigravity.native_review_proof(self.project, self.parent, self.child, backend=self.backend, write=False)
			with self.assertRaises(ValueError):
				antigravity.require_current_binding(self.project, self.parent, backend=self.backend)
	def test_explicit_root_supports_self_review_and_empty_metadata_keeps_legacy_job_id(self):
		self.workspace([])
		self.inputs([f'Continue analysis.\nProject root: `{self.project}`'])
		report = self.review_report(self.package, self_review=True)
		self.put_project('ꘖ/KB/Evidence/Reviews/self.json', json.dumps(report))
		with patch.object(Path, 'home', return_value=self.home), runtime.using('antigravity'):
			flow.record_review(self.project, 'ꘖ/KB/Evidence/Reviews/self.json', parent_id=self.parent, reviewer_id=self.parent)
		self.inputs(['Exact native job ' + flow.load(self.project)['job_id']])
		self.assertEqual(len(antigravity.native_requests(self.project, self.parent, backend=self.backend)), 1)
	def test_legacy_job_mention_after_foreign_init_cannot_reactivate_old_project(self):
		self.workspace([])
		job_id = flow.load(self.project)['job_id']
		texts = ['Exact native job ' + job_id, '/upwork-init https://www.upwork.com/jobs/~0299999', 'Reference to the former job ' + job_id, 'Continue analysis.']
		self.inputs(texts)
		self.assertEqual([item['text'] for item in antigravity.native_requests(self.project, self.parent, backend=self.backend)], [texts[0]])
		with self.assertRaises(ValueError):
			antigravity.require_current_binding(self.project, self.parent, backend=self.backend)
	# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
	# "Canonicalize relocated Codex, Antigravity, and Harness project roots and support v2Migrated gitFolder project resources":
	# https://github.com/dmitry-ai/harness/issues/29
	def test_git_folder_project_id_fallback_and_relocated_root_canonicalization(self):
		from agent_tools.platforms.request_binding import _same_root
		self.assertTrue(_same_root('C:/work/research/provision/code/Software/OpenAI/Codex', 'C:/work/research/provision/code/AI/products/OpenAI/ChatGPT/Desktop/Addons'))
		self.assertTrue(_same_root('C:/work/research/provision/code/Software/Google/AI/Antigravity', 'C:/work/research/provision/code/AI/products/Google/Antigravity/Addons'))
		self.assertTrue(_same_root('C:/work/upwork/code/AI', 'C:/work/research/provision/code/AI/harness'))
		self.assertTrue(_same_root('C:/work/research/provision/code/AI/primary', 'C:/work/research/provision/code/AI/harness'))
		pid = 'cd16380f-c085-4876-a083-62bf924eda55'
		projects_dir = self.backend.parent / 'config/projects'
		projects_dir.mkdir(parents=True, exist_ok=True)
		(projects_dir / f'{pid}.json').write_text(json.dumps({'id': pid, 'name': 'Test', 'projectResources': {'resources': [{'gitFolder': {'folderUri': self.project.as_uri()}}]}}), encoding='utf-8')
		conn = sqlite3.connect(self.backend / 'conversation_summaries.db')
		try:
			conn.execute('ALTER TABLE conversation_summaries ADD COLUMN project_id TEXT')
			conn.execute('UPDATE conversation_summaries SET workspace_uris=?, project_id=? WHERE conversation_id=?', ('[]', pid, self.parent))
			conn.commit()
		finally:
			conn.close()
		requests = antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.assertEqual(requests[0]['project_binding']['kind'], 'antigravity-project-id')
		self.assertEqual(Path(requests[0]['project_binding']['root']).resolve(), self.project.resolve())
	def test_status_five_compacted_step_recovers_nested_protobuf_and_transcript_fallback(self):
		db_file = self.backend / 'conversations' / (self.parent + '.db')
		conn = sqlite3.connect(db_file)
		try:
			conn.execute('DELETE FROM steps')
			conn.execute('INSERT INTO steps VALUES(0,14,5,0,?,NULL)', (wire(19, wire(3, wire(1, b'First compacted request'))),))
			conn.execute('INSERT INTO steps VALUES(2,14,5,0,?,NULL)', (b'',))
			conn.commit()
		finally:
			conn.close()
		log = self.backend / 'brain' / self.parent / '.system_generated/logs/transcript_full.jsonl'
		log.write_text('\n'.join((json.dumps(row, ensure_ascii=False) for row in [{'step_index': 0, 'type': 'USER_INPUT', 'content': '<USER_REQUEST>\nFirst compacted request\n</USER_REQUEST>'}, {'step_index': 2, 'type': 'USER_INPUT', 'content': '<USER_REQUEST>\nSecond compacted request\n</USER_REQUEST>\n<ADDITIONAL_METADATA>\nmeta\n</ADDITIONAL_METADATA>'}])) + '\n', encoding='utf-8')
		requests = antigravity.native_requests(self.project, self.parent, backend=self.backend)
		self.assertEqual([item['text'] for item in requests], ['First compacted request', 'Second compacted request'])
		conn = sqlite3.connect(db_file)
		try:
			conn.execute('INSERT INTO steps VALUES(4,14,3,0,?,NULL)', (b'',))
			conn.commit()
		finally:
			conn.close()
		with self.assertRaises(ValueError):
			antigravity.native_requests(self.project, self.parent, backend=self.backend)
