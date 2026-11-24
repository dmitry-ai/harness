# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Clarify verbatim target_claim contract and add native-review-proof wait timeout":
# https://github.com/dmitry-ai/harness/issues/212
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import sys
import threading
import time
import unittest
import uuid
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (str(SCRIPTS), str(TESTS)):
	if p not in sys.path:
		sys.path.insert(0, p)
from agent_tools import cli_common, review, workflow as flow
from agent_tools.platforms import antigravity
from test_analysis_workflow import ProjectCase
from test_continuation_binding import wire
def _exec_sql(db_path: Path, statements: list[tuple[str, tuple]]) -> None:
	conn = sqlite3.connect(db_path)
	try:
		for sql, params in statements:
			conn.execute(sql, params)
		conn.commit()
	finally:
		conn.close()
class ReviewTargetClaimAndWaitM5Tests(ProjectCase):
	def setUp(self) -> None:
		super().setUp()
		self.value = self.valid_review_analysis()
		self.value['identity'][0]['essence'] = '\u0426\u0435\u043b\u0435\u0432\u043e\u0439 \u0441\u0430\u0439\u0442 \u043a\u043b\u0438\u0435\u043d\u0442\u0430 \u2014 https://example.org/.'
		self.put_project('\ua616/KB/Analysis.json', json.dumps(self.value, ensure_ascii=False))
		self.parent = str(uuid.uuid4())
		self.child = str(uuid.uuid4())
		flow.resume(self.project, 'm5 fixture', 'Verify client target website.')
		self.answer = 'Client task\n'
		self.manifest = [{'claim_id': 'F-TITLE', 'response_excerpt': 'Client task', 'novelty': 'new'}]
		self.package = self.review_package(self.parent, self.answer, 'routine', self.manifest)
	def _setup_antigravity_reviewer(self) -> tuple[Path, Path, Path]:
		backend = self.root / 'ag-home/.gemini/antigravity'
		(backend / 'conversations').mkdir(parents=True)
		_exec_sql(backend / 'conversation_summaries.db', [
			('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,agent_name TEXT,workspace_uris TEXT,status TEXT,not_fully_idle INTEGER)', ()),
			('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?)', (self.parent, '', '', json.dumps([self.project.as_uri()]), 'CASCADE_RUN_STATUS_IDLE', 0)),
			('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?)', (self.child, self.parent, 'self', json.dumps([self.project.as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1)),
		])
		_exec_sql(backend / 'conversations' / f'{self.parent}.db', [
			('CREATE TABLE steps(idx INTEGER,step_type INTEGER,status INTEGER,step_format INTEGER,step_payload BLOB,metadata BLOB)', ()),
			('INSERT INTO steps VALUES(0,14,3,0,?,NULL)', (wire(19, wire(2, b'Verify client target website.')),)),
		])
		prompt = 'Review ' + self.package['package']
		parent_log = backend / 'brain' / self.parent / '.system_generated/logs/transcript_full.jsonl'
		parent_log.parent.mkdir(parents=True, exist_ok=True)
		parent_log.write_text('\n'.join((json.dumps(r) for r in [
			{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Verify client target website.'},
			{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'self', 'Model': 'inherit', 'Prompt': prompt}]}}]},
		])) + '\n', encoding='utf-8')
		child_log = backend / 'brain' / self.child / '.system_generated/logs/transcript_full.jsonl'
		child_log.parent.mkdir(parents=True, exist_ok=True)
		child_log.write_text('\n'.join((json.dumps(r) for r in [
			{'step_index': 0, 'type': 'SYSTEM_MESSAGE', 'content': prompt},
			{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'name': 'send_message', 'args': {'Recipient': self.parent, 'Message': 'Done'}}]},
		])) + '\n', encoding='utf-8')
		c_db = backend / 'conversations' / f'{self.child}.db'
		_exec_sql(c_db, [('CREATE TABLE steps(idx INTEGER,step_type INTEGER,status INTEGER)', ()), ('INSERT INTO steps VALUES(1,15,2)', ())])
		return (backend, child_log, c_db)
	def test_review_input_and_validator_expose_verbatim_target_claim_rule_and_diff(self) -> None:
		receipt = review.input_receipt(self.project, self.package['package'])
		self.assertIn('claim_targets', receipt)
		expected_essence = self.value['identity'][0]['essence']
		self.assertEqual(expected_essence, receipt['claim_targets']['F-TITLE'])
		self.assertIn('target_claim_rule', receipt['report_contract'])
		self.assertIn('verbatim', receipt['report_contract']['target_claim_rule'].lower())
		report = self.review_report(self.package, self_review=True)
		report['claim_reviews'][0]['test_alignment']['target_claim'] = 'The target client website is https://example.org/.'
		issues = review.report_issues(report, self.package)
		self.assertTrue(any(('target_claim' in e and expected_essence in e and 'The target client website' in e for e in issues)), issues)
	def test_native_review_proof_retryable_flag_and_bounded_wait_for_final_response(self) -> None:
		backend, child_log, c_db = self._setup_antigravity_reviewer()
		with self.assertRaises(ValueError) as ctx:
			antigravity.native_review_proof(self.project, self.parent, self.child, backend=backend, write=False, wait_timeout=0.0)
		payload = cli_common.operation_error_payload(ctx.exception)
		self.assertTrue(payload['retryable'], payload)
		def _finish_reviewer() -> None:
			time.sleep(0.25)
			child_log.write_text(child_log.read_text(encoding='utf-8') + json.dumps({'step_index': 2, 'type': 'PLANNER_RESPONSE', 'content': 'Reviewed'}) + '\n', encoding='utf-8')
			_exec_sql(c_db, [('INSERT INTO steps VALUES(2,15,3)', ())])
			_exec_sql(backend / 'conversation_summaries.db', [("UPDATE conversation_summaries SET status='CASCADE_RUN_STATUS_IDLE', not_fully_idle=0 WHERE conversation_id=?", (self.child,))])
		worker = threading.Thread(target=_finish_reviewer, daemon=True)
		worker.start()
		proof = antigravity.native_review_proof(self.project, self.parent, self.child, backend=backend, write=False, wait_timeout=5.0)
		worker.join(timeout=3.0)
		self.assertEqual('completed', proof['status'])
if '__main__' == __name__:
	unittest.main()
