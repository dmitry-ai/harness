# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
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
from agent_tools import completion, workflow as flow
from test_analysis_workflow import ProjectCase
from test_continuation_binding import wire
# 2026-11-24
# "Add blocked-report mode to answer-prepare for pre-finalize workflow blockers":
# https://github.com/dmitry-ai/harness/issues/213
class BlockedReportM2Tests(ProjectCase):
	def setUp(self) -> None:
		super().setUp()
		self.valid_review_analysis()
		self.home = self.root / 'ag-home'
		self.backend = self.home / '.gemini/antigravity'
		(self.backend / 'conversations').mkdir(parents=True)
		self.cid = str(uuid.uuid4())
		self.job_id = flow.load(self.project)['job_id']
		self.req_text = f'/upwork-init https://www.upwork.com/jobs/{self.job_id}'
		conn_s = sqlite3.connect(self.backend / 'conversation_summaries.db')
		try:
			conn_s.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,agent_name TEXT,workspace_uris TEXT)')
			conn_s.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?)', (self.cid, '', '', json.dumps([self.project.as_uri()])))
			conn_s.commit()
		finally:
			conn_s.close()
		conn_c = sqlite3.connect(self.backend / 'conversations' / f'{self.cid}.db')
		try:
			conn_c.execute('CREATE TABLE steps(idx INTEGER,step_type INTEGER,status INTEGER,step_format INTEGER,step_payload BLOB,metadata BLOB)')
			conn_c.execute('INSERT INTO steps VALUES(0,14,3,0,?,NULL)', (wire(19, wire(2, self.req_text.encode('utf-8'))),))
			conn_c.commit()
		finally:
			conn_c.close()
		log = self.backend / 'brain' / self.cid / '.system_generated/logs/transcript_full.jsonl'
		log.parent.mkdir(parents=True, exist_ok=True)
		log.write_text(json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': self.req_text}) + '\n', encoding='utf-8')
		flow.adopt_requests(self.project, self.cid, backend=self.backend, platform='antigravity')
	def _write_continuation(self, body: str) -> None:
		self.put_project('\ua616/data/continuation.md', body)
	def test_blocked_report_records_journal_without_closing_workflow_or_allowing_finalize(self) -> None:
		report = '\u0410\u043d\u0430\u043b\u0438\u0437 \u043f\u0440\u0438\u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d \u0434\u043e \u043d\u0435\u0437\u0430\u0432\u0438\u0441\u0438\u043c\u043e\u0439 \u0440\u0435\u0446\u0435\u043d\u0437\u0438\u0438 \u0438\u0437-\u0437\u0430 \u0432\u043d\u0435\u0448\u043d\u0435\u0433\u043e \u0431\u043b\u043e\u043a\u0435\u0440\u0430.\n\n\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0448\u0430\u0433: \u043f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u044c \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0443 \u043f\u043e\u0441\u043b\u0435 \u0443\u0441\u0442\u0440\u0430\u043d\u0435\u043d\u0438\u044f \u0431\u043b\u043e\u043a\u0435\u0440\u0430.\n'
		with self.assertRaisesRegex(ValueError, 'continuation\\.md'):
			completion.prepare(self.project, report, self.cid, platform='antigravity', backend=self.backend, blocked_report=True)
		self._write_continuation('# Continuation\n\n\u0411\u043b\u043e\u043a\u0435\u0440: \u043e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438\u0432\u044f\u0437\u043a\u0438 \u043d\u0430 \u044d\u0442\u0430\u043f\u0435 native-review-proof.\n\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0448\u0430\u0433: \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u043f\u043e\u0441\u043b\u0435 \u0438\u0441\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f.\n')
		chk_ok = completion.check_answer(self.project, report, self.cid, platform='antigravity', backend=self.backend, blocked_report=True)
		self.assertTrue(chk_ok['valid'], chk_ok)
		res = completion.prepare(self.project, report, self.cid, platform='antigravity', backend=self.backend, blocked_report=True)
		self.assertTrue(res['ready'])
		self.assertEqual('blocked_report', res.get('completion_kind'))
		self.assertTrue((self.project / '\ua66e/\u227b/1\u201320/1.md').is_file())
		self.assertTrue((self.project / '\ua66e/\u227a/1\u201320/1.md').is_file())
		wf = flow.load(self.project)
		self.assertFalse(any((req.get('response_prepared') for req in wf['requests'])))
		self.assertNotEqual('complete', wf.get('stages', {}).get('finalize', {}).get('status'))
		with self.assertRaises(ValueError):
			flow.complete_stage(self.project, 'finalize', flow.kb_paths(self.project), ['\ua66e/\u227a/1\u201320/1.md'])
	def test_blocked_report_rejects_analytical_hm_claims_and_five_stage_content(self) -> None:
		self._write_continuation('# Continuation\n\n\u0411\u043b\u043e\u043a\u0435\u0440: \u0438\u0441\u0442\u0435\u043a\u043b\u0430 \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f \u0432\u043d\u0435\u0448\u043d\u0435\u0433\u043e \u043f\u043e\u0440\u0442\u0430\u043b\u0430.\n')
		bad_hm = '\u0410\u043d\u0430\u043b\u0438\u0437 \u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d. \u041f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u0430\u044f \u043f\u0440\u0438\u0447\u0438\u043d\u0430 H-1 \u0438 \u043c\u0435\u0442\u043e\u0434 M-1.\n'
		chk_bad = completion.check_answer(self.project, bad_hm, self.cid, platform='antigravity', backend=self.backend, blocked_report=True)
		self.assertFalse(chk_bad['valid'])
		with self.assertRaisesRegex(ValueError, 'blocked-report'):
			completion.prepare(self.project, bad_hm, self.cid, platform='antigravity', backend=self.backend, blocked_report=True)
		bad_stage = '# 4. \u041f\u0440\u0438\u0447\u0438\u043d\u044b \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u044b\n\n\u041f\u043e\u0434\u0440\u043e\u0431\u043d\u044b\u0439 \u0440\u0430\u0437\u0431\u043e\u0440 \u0431\u0435\u0437 \u0440\u0435\u0446\u0435\u043d\u0437\u0438\u0438.\n'
		with self.assertRaisesRegex(ValueError, 'blocked-report'):
			completion.prepare(self.project, bad_stage, self.cid, platform='antigravity', backend=self.backend, blocked_report=True)
if '__main__' == __name__:
	unittest.main()
