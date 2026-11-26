# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import override
import json
from pathlib import Path
import sqlite3
import sys
import unittest
import uuid
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (str(SCRIPTS), str(TESTS)):
	if p not in sys.path:
		sys.path.insert(0, p)
from agent_tools import workflow as flow
from agent_tools.platforms import antigravity
from agent_tools.platforms.request_binding import _extract_leading_upwork_init_ids, scoped_inputs
from test_analysis_workflow import ProjectCase
from test_continuation_binding import wire
# @used-by :meth:`NativeReviewBindingM4Tests.test_native_review_proof_binds_launcher_chat_with_user_request_and_uses_native_meta()`
def _chip_payload(prefix_text: str, cmd_name: str, suffix_text: str, flat_text: str) -> bytes:
	parts = [wire(2, flat_text.encode('utf-8'))]
	if prefix_text:
		parts.append(wire(3, wire(1, prefix_text.encode('utf-8'))))
	parts.append(wire(3, wire(2, wire(27, wire(1, wire(1, cmd_name.encode('utf-8')))))))
	if suffix_text:
		parts.append(wire(3, wire(1, suffix_text.encode('utf-8'))))
	return wire(19, b''.join(parts))
# 2026-11-24
# "Use canonical native inputs and strip USER_REQUEST in native_review_proof":
# https://github.com/dmitry-ai/harness/issues/210
class NativeReviewBindingM4Tests(ProjectCase):
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :mod:`unittest`
	# @see :meth:`test_analysis_workflow.ProjectCase.setUp()`
	@override
	def setUp(self) -> None:
		super().setUp()
		self.home = self.root / 'ag-home'
		self.backend = self.home / '.gemini/antigravity'
		(self.backend / 'conversations').mkdir(parents=True)
		self.launcher = self.root / 'launcher_init'
		self.launcher.mkdir(parents=True)
		self.parent = str(uuid.uuid4())
		self.child = str(uuid.uuid4())
		self.package = self.review_package(self.parent)
		self.job_id = flow.load(self.project)['job_id']
		conn = sqlite3.connect(self.backend / 'conversation_summaries.db')
		try:
			conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,agent_name TEXT,workspace_uris TEXT)')
			conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?)', (self.parent, '', '', json.dumps([self.launcher.as_uri()])))
			conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?)', (self.child, self.parent, 'self', json.dumps([self.launcher.as_uri()])))
			conn.commit()
		finally:
			conn.close()
	# @used-by :meth:`NativeReviewBindingM4Tests.test_native_review_proof_binds_launcher_chat_with_user_request_and_uses_native_meta()`
	def _write_traces(self, db_payload: bytes, transcript_user_content: str) -> None:
		p_db = self.backend / 'conversations' / f'{self.parent}.db'
		conn = sqlite3.connect(p_db)
		try:
			conn.execute('CREATE TABLE IF NOT EXISTS steps(idx INTEGER,step_type INTEGER,status INTEGER,step_format INTEGER,step_payload BLOB,metadata BLOB)')
			conn.execute('DELETE FROM steps')
			conn.execute('INSERT INTO steps VALUES(0,14,3,0,?,NULL)', (db_payload,))
			conn.commit()
		finally:
			conn.close()
		prompt = 'Review ' + self.package['package']
		parent_rows = [
			{'step_index': 0, 'type': 'USER_INPUT', 'content': transcript_user_content},
			{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'self', 'Model': 'inherit', 'Prompt': prompt}]}}]},
		]
		child_rows = [
			{'step_index': 0, 'type': 'SYSTEM_MESSAGE', 'content': prompt},
			{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': 'Reviewed'},
		]
		for cid, rows in ((self.parent, parent_rows), (self.child, child_rows)):
			log = self.backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
			log.parent.mkdir(parents=True, exist_ok=True)
			log.write_text('\n'.join((json.dumps(r, ensure_ascii=False) for r in rows)) + '\n', encoding='utf-8')
		c_db = self.backend / 'conversations' / f'{self.child}.db'
		conn_c = sqlite3.connect(c_db)
		try:
			conn_c.execute('CREATE TABLE IF NOT EXISTS steps(idx INTEGER,step_type INTEGER,status INTEGER)')
			conn_c.execute('DELETE FROM steps')
			conn_c.execute('INSERT INTO steps VALUES(1,15,3)')
			conn_c.commit()
		finally:
			conn_c.close()
	# @used-by :mod:`unittest`
	def test_extract_leading_upwork_init_strips_outer_user_request_wrapper(self) -> None:
		url = f'https://upwork.com/jobs/{self.job_id}'
		wrapped = f'<USER_REQUEST>\n/upwork-init  {url}\n</USER_REQUEST>'
		with_meta = f'{wrapped}\n<ADDITIONAL_METADATA>\nThe current local time is: 2026-11-24T05:00:00+03:00.\n</ADDITIONAL_METADATA>'
		self.assertEqual([self.job_id], _extract_leading_upwork_init_ids(wrapped))
		self.assertEqual([self.job_id], _extract_leading_upwork_init_ids(with_meta))
		quoted = f'Inspect this log:\n<USER_REQUEST>\n/upwork-init  {url}\n</USER_REQUEST>'
		fenced = f'```\n<USER_REQUEST>\n/upwork-init  {url}\n</USER_REQUEST>\n```'
		self.assertEqual([], _extract_leading_upwork_init_ids(quoted))
		self.assertEqual([], _extract_leading_upwork_init_ids(fenced))
		sel, active, bnd = scoped_inputs(self.project, self.job_id, [(0, wrapped)], [(-1, str(self.launcher), 'antigravity-workspace-uris')])
		self.assertTrue(active)
		self.assertEqual(1, len(sel))
		self.assertEqual('explicit-upwork-init', bnd['kind'])
	# @used-by :mod:`unittest`
	def test_native_review_proof_binds_launcher_chat_with_user_request_and_uses_native_meta(self) -> None:
		url = f'https://upwork.com/jobs/{self.job_id}'
		cmd = f'/upwork-init  {url}'
		wrapped = f'<USER_REQUEST>\n{cmd}\n</USER_REQUEST>\n<ADDITIONAL_METADATA>\nnow\n</ADDITIONAL_METADATA>'
		self._write_traces(_chip_payload('', 'upwork-init', f'  {url}', cmd), wrapped)
		proof = antigravity.native_review_proof(self.project, self.parent, self.child, backend=self.backend, write=False)
		self.assertEqual('completed', proof['status'])
		self._write_traces(_chip_payload('', 'plan', f'  {url}', cmd), wrapped)
		with self.assertRaises(ValueError):
			antigravity.native_review_proof(self.project, self.parent, self.child, backend=self.backend, write=False)
if '__main__' == __name__:
	unittest.main()
