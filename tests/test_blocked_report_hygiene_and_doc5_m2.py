# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Allow blocked-report journaling over hygiene gates with DOC-5 compatibility":
# https://github.com/dmitry-ai/harness/issues/225
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
import uuid
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (str(SCRIPTS), str(TESTS)):
	if p not in sys.path:
		sys.path.insert(0, p)
from agent_tools import blocked_report, completion, workflow as flow
from agent_tools.path_registry import project_paths
from test_analysis_workflow import ProjectCase
from test_continuation_binding import wire
DOC5_HARNESS_BLOCKER = (
	'# 0. \u041c\u0435\u0442\u0430\u0434\u0430\u043d\u043d\u044b\u0435 \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u044b\n\n'
	'```json\n'
	'{\n'
	'\t"Time": "2026-11-24 06:43:44 UTC+3",\n'
	'\t"Issue": null,\n'
	'\t"Project": {\n'
	'\t\t"Name": "Demo",\n'
	'\t\t"Path": "demo"\n'
	'\t},\n'
	'\t"Source Project": {\n'
	'\t\t"Name": "Harness"\n'
	'\t}\n'
	'}\n'
	'```\n\n'
	'# 1. \u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u044b\n\n'
	'\u041a\u043e\u043c\u0430\u043d\u0434\u0430 `answer-prepare` \u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d\u0430 \u0438\u0437-\u0437\u0430 \u043b\u043e\u0436\u043d\u043e\u0433\u043e \u0441\u0440\u0430\u0431\u0430\u0442\u044b\u0432\u0430\u043d\u0438\u044f \u0433\u0435\u0439\u0442\u0430 Harness ([continuation.md](\ua616/data/continuation.md)).  \n\n'
	'# 2. \u0410\u043d\u0430\u043b\u0438\u0437 \u043f\u0435\u0440\u0432\u043e\u043f\u0440\u0438\u0447\u0438\u043d\n\n'
	'## H-1: \u041b\u043e\u0436\u043d\u043e\u0435 \u0441\u0440\u0430\u0431\u0430\u0442\u044b\u0432\u0430\u043d\u0438\u0435 \u043f\u0430\u0440\u0441\u0435\u0440\u0430 \u0440\u0435\u0434\u0438\u0440\u0435\u043a\u0442\u043e\u0432\n\n'
	'- **\u0421\u0443\u0442\u044c:** \u041e\u0448\u0438\u0431\u043a\u0430 \u0432 \u0440\u0430\u0437\u0431\u043e\u0440\u0435 here-string ([continuation.md](\ua616/data/continuation.md)).  \n'
	'- **\u0414\u043e\u0432\u043e\u0434\u044b \u0437\u0430:** \u041d\u0435\u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u044e\u0449\u0438\u0439 \u0444\u0430\u0439\u043b \u043e\u0442\u043c\u0435\u0447\u0435\u043d \u043a\u0430\u043a \u043f\u0440\u0430\u0432\u043a\u0430 \u043a\u043e\u0434\u0430.  \n'
	'- **\u0414\u043e\u0432\u043e\u0434\u044b \u043f\u0440\u043e\u0442\u0438\u0432:** \u041a\u043e\u043d\u0442\u0440\u0441\u0432\u0438\u0434\u0435\u0442\u0435\u043b\u044c\u0441\u0442\u0432 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e.  \n'
	'- **\u041e\u0446\u0435\u043d\u043a\u0430:** 95% (\u043f\u0440\u044f\u043c\u043e\u0435 \u0432\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0434\u0435\u043d\u0438\u0435).  \n\n'
	'## H-2: \u0421\u043b\u0438\u044f\u043d\u0438\u0435 \u0445\u043e\u0434\u043e\u0432 \u0438\u0437-\u0437\u0430 \u0442\u0430\u0439\u043c\u0435\u0440\u0430\n\n'
	'- **\u0421\u0443\u0442\u044c:** \u041d\u0435\u0437\u0430\u043a\u0440\u044b\u0442\u044b\u0439 \u0442\u0430\u0439\u043c\u0435\u0440 \u0441\u043b\u0438\u043b \u0445\u043e\u0434 1 \u0438 \u0445\u043e\u0434 2 ([continuation.md](\ua616/data/continuation.md)).  \n'
	'- **\u0414\u043e\u0432\u043e\u0434\u044b \u0437\u0430:** \u0422\u0430\u0439\u043c\u0435\u0440 \u043e\u0441\u0442\u0430\u043b\u0441\u044f \u0432 \u0441\u043f\u0438\u0441\u043a\u0435 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0445 \u0437\u0430\u0434\u0430\u0447.  \n'
	'- **\u0414\u043e\u0432\u043e\u0434\u044b \u043f\u0440\u043e\u0442\u0438\u0432:** \u0412\u0442\u043e\u0440\u0438\u0447\u043d\u0430\u044f \u043f\u0440\u0438\u0447\u0438\u043d\u0430.  \n'
	'- **\u041e\u0446\u0435\u043d\u043a\u0430:** 80% (\u043f\u043e \u0441\u043a\u0430\u043d\u0443 \u0442\u0440\u0430\u043d\u0441\u043a\u0440\u0438\u043f\u0442\u0430).  \n\n'
	'# 3. \u0410\u0442\u0440\u0438\u0431\u0443\u0446\u0438\u044f \u0438\u0441\u0445\u043e\u0434\u043d\u043e\u0433\u043e \u043f\u0440\u043e\u0435\u043a\u0442\u0430\n\n'
	'\u0412\u043b\u0430\u0434\u0435\u043b\u0435\u0446 \u0434\u0435\u0444\u0435\u043a\u0442\u0430 \u2014 Harness.  \n\n'
	'# 4. \u041f\u043e\u0441\u0442\u043e\u044f\u043d\u043d\u044b\u0435 \u0441\u0438\u0441\u0442\u0435\u043c\u043d\u044b\u0435 \u0440\u0435\u0448\u0435\u043d\u0438\u044f\n\n'
	'## M-1: \u0418\u0441\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043f\u0430\u0440\u0441\u0435\u0440 here-string\n\n'
	'- **\u0421\u0443\u0442\u044c:** \u0421\u043d\u0438\u043c\u0430\u0442\u044c here-string \u0434\u043e \u043f\u043e\u0438\u0441\u043a\u0430 \u0440\u0435\u0434\u0438\u0440\u0435\u043a\u0442\u043e\u0432.  \n'
	'- **\u0414\u043e\u0432\u043e\u0434\u044b \u0437\u0430:** \u0423\u0431\u0438\u0440\u0430\u0435\u0442 \u043b\u043e\u0436\u043d\u044b\u0435 \u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u043a\u0438.  \n'
	'- **\u0414\u043e\u0432\u043e\u0434\u044b \u043f\u0440\u043e\u0442\u0438\u0432:** \u0422\u0440\u0435\u0431\u0443\u044e\u0442\u0441\u044f \u0442\u0435\u0441\u0442\u044b.  \n'
	'- **\u041e\u0446\u0435\u043d\u043a\u0430:** 95% (\u043a\u0440\u0438\u0442\u0435\u0440\u0438\u0439 \u043d\u0430\u0434\u0451\u0436\u043d\u043e\u0441\u0442\u0438).  \n\n'
	'## M-2: \u041e\u0442\u0434\u0435\u043b\u0438\u0442\u044c \u0442\u0430\u0439\u043c\u0435\u0440\u044b schedule\n\n'
	'- **\u0421\u0443\u0442\u044c:** \u041d\u0435 \u0434\u043e\u0431\u0430\u0432\u043b\u044f\u0442\u044c schedule \u0432 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0435 \u0444\u043e\u043d\u043e\u0432\u044b\u0435 \u0437\u0430\u0434\u0430\u0447\u0438.  \n'
	'- **\u0414\u043e\u0432\u043e\u0434\u044b \u0437\u0430:** \u0418\u0441\u043a\u043b\u044e\u0447\u0430\u0435\u0442 \u0441\u043b\u0438\u044f\u043d\u0438\u0435 \u0445\u043e\u0434\u043e\u0432.  \n'
	'- **\u0414\u043e\u0432\u043e\u0434\u044b \u043f\u0440\u043e\u0442\u0438\u0432:** \u0422\u0440\u0435\u0431\u0443\u0435\u0442 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u0441\u043a\u0430\u043d\u0435\u0440\u0430.  \n'
	'- **\u041e\u0446\u0435\u043d\u043a\u0430:** 90% (\u043a\u0440\u0438\u0442\u0435\u0440\u0438\u0439 \u0438\u0437\u043e\u043b\u044f\u0446\u0438\u0438).  \n'
)
class BlockedReportHygieneAndDoc5M2Tests(ProjectCase):
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
		self.put_project('\ua616/data/continuation.md', '# Continuation\n\n\u0411\u043b\u043e\u043a\u0435\u0440: \u043b\u043e\u0436\u043d\u043e\u0435 \u0441\u0440\u0430\u0431\u0430\u0442\u044b\u0432\u0430\u043d\u0438\u0435 ISSUE-FIRST-GATE \u0432 Harness.\n')
	def test_blocked_report_records_journal_despite_hygiene_failures_and_allows_doc5(self) -> None:
		fake_if = {'verified': False, 'repos': {}, 'violations': ['EXEC-5 ISSUE-FIRST-GATE: fake.js']}
		fake_tdd = {'verified': False, 'scopes': {}, 'violations': ['EXEC-2 TDD-RED-GATE: fake.js']}
		fake_lc = {'verified': False, 'violations': ['EXEC-5 code lifecycle incomplete']}
		with patch.object(completion, '_issue_first_status', return_value=fake_if), patch.object(completion, '_tdd_status', return_value=fake_tdd), patch.object(completion, '_code_and_issue_lifecycle_status', return_value=fake_lc):
			chk = completion.check_answer(self.project, DOC5_HARNESS_BLOCKER, self.cid, platform='antigravity', backend=self.backend, blocked_report=True)
			self.assertTrue(chk['valid'], chk)
			res = completion.prepare(self.project, DOC5_HARNESS_BLOCKER, self.cid, platform='antigravity', backend=self.backend, blocked_report=True)
		self.assertTrue(res['ready'])
		self.assertEqual('blocked_report', res.get('completion_kind'))
		state_file = project_paths(self.project).turns_dir / f"{res['turn_key']}.json"
		saved_state = json.loads(state_file.read_text(encoding='utf-8'))
		self.assertIn('blocked_hygiene_diagnostics', saved_state)
		self.assertIn('issue_first', saved_state['blocked_hygiene_diagnostics'])
		self.assertIn('tdd', saved_state['blocked_hygiene_diagnostics'])
	def test_blocked_report_still_rejects_client_claim_ids_inside_doc5(self) -> None:
		pp = project_paths(self.project)
		smuggled_client = DOC5_HARNESS_BLOCKER + '\n## H-CAUSE-1: Client GA4 bug\n'
		issues = blocked_report.blocked_report_issues(pp, smuggled_client, workflow_exists=True, is_finalized=False)
		self.assertTrue(any(('blocked-report' in item for item in issues)), issues)
		smuggled_stage = DOC5_HARNESS_BLOCKER + '\n# 1. \u0418\u0434\u0435\u043d\u0442\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u044f \u043a\u043b\u0438\u0435\u043d\u0442\u0430\n'
		stage_issues = blocked_report.blocked_report_issues(pp, smuggled_stage, workflow_exists=True, is_finalized=False)
		self.assertTrue(any(('five-stage' in item for item in stage_issues)), stage_issues)
if '__main__' == __name__:
	unittest.main()
