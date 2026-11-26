# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (str(SCRIPTS), str(TESTS)):
	if p not in sys.path:
		sys.path.insert(0, p)
from agent_tools import review, workflow as flow
from agent_tools.failfast_gate import evaluate_pre_tool_use_schedule
from agent_tools.gates import run_pre_tool_gates
from agent_tools.research import json_data
from agent_tools.stop_subagent_check import extract_segment_subagent_state
from test_analysis_workflow import ProjectCase
PARENT_CID = 'be6873ea-5b72-4a7f-82bd-420b873f13f9'
CHILD_CID = '8ec25783-99cc-40fa-99ff-a557eb04dde3'
# 2026-11-24
# "Enforce single falsifier review default and block duplicate send_message reports":
# https://github.com/dmitry-ai/harness/issues/226
class FalsifierDefaultSendMessageAndScheduleM8Tests(ProjectCase):
	def setUp(self) -> None:
		super().setUp()
		self.value = self.valid_review_analysis()
		self.parent = str(uuid.uuid4())
		flow.resume(self.project, 'm8 fixture', 'Show the saved client title.')
		self.answer = 'Client task\n'
		self.manifest = [{'claim_id': 'F-TITLE', 'response_excerpt': 'Client task', 'novelty': 'new'}]
	def _native_record(self, pkg: dict, report: dict) -> dict:
		reviewer = str(uuid.uuid4())
		raw = json_data(report).decode('utf-8')
		proof = {'parent_id': self.parent, 'reviewer_id': reviewer, 'status': 'completed', 'final_response': raw, 'final_response_sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest(), 'model_verification': 'verified'}
		proof_rel = f'\ua616/KB/Evidence/Reviews/{reviewer}-native.json'
		self.put_project(proof_rel, json.dumps(proof))
		with patch('agent_tools.metrics.verify_native_proof', return_value=proof):
			r = flow.record_review(self.project, raw.encode('utf-8'), parent_id=self.parent, reviewer_id=reviewer, native_evidence=proof_rel)
		return r
	def test_significant_prepare_review_defaults_to_falsifier_and_authorizes_single_auditor(self) -> None:
		claim = self.value['identity'][0]
		claim.update(verification_status='limited', missing_checks=['Check logs.'], properties=['content', 'causality'])
		self.put_project('\ua616/KB/Analysis.json', json.dumps(self.value))
		pkg = self.review_package(self.parent, self.answer, 'significant', self.manifest)
		self.assertEqual('falsifier', pkg.get('review_mode'))
		inp = flow.review_input(self.project, pkg['package'])
		self.assertEqual('falsifier', inp.get('review_mode'))
		self.assertIn('disproved_claims', inp['report_contract']['required_top_level_fields'])
		self.assertEqual(pkg['package'], inp['report_contract']['expected_package'])
		with self.assertRaisesRegex(ValueError, 'falsifier'):
			review.authorize(self.project, flow.load(self.project), response=self.answer)
		falsifier_rep = {
			'schema_version': review.REVIEW_SCHEMA,
			'review_mode': 'falsifier',
			'package': pkg['package'],
			'package_sha256': pkg['package_sha256'],
			'scope': list(review.SCOPES),
			'result': 'approved',
			'summary': 'No Tier 0 contradiction found.',
			'disproved_claims': [],
			'findings': [],
		}
		self._native_record(pkg, falsifier_rep)
		with patch('agent_tools.metrics.verify_native_proof', side_effect=lambda r, n, package=None: n):
			auth = review.authorize(self.project, flow.load(self.project), response=self.answer)
		self.assertEqual('significant', auth['risk'])
		self.assertEqual(1, len(auth['review_ids']))
	def test_send_message_gate_blocks_duplicate_json_verdicts_and_allows_prompts(self) -> None:
		dup_std = json.dumps({'schema_version': 2, 'package': 'p.json', 'result': 'approved', 'claim_reviews': [], 'findings': []})
		dec_std = run_pre_tool_gates('send_message', {'Recipient': PARENT_CID, 'Message': dup_std}, {'conversationId': CHILD_CID})
		self.assertEqual('deny', dec_std['decision'])
		self.assertIn('REVIEW-4-SEND-MESSAGE-GATE', dec_std['reason'])
		dup_fals = json.dumps({'schema_version': 2, 'review_mode': 'falsifier', 'result': 'approved', 'disproved_claims': [], 'findings': []})
		dec_fals = run_pre_tool_gates('send_message', {'Recipient': PARENT_CID, 'Message': dup_fals}, {'conversationId': CHILD_CID})
		self.assertEqual('deny', dec_fals['decision'])
		big_json = json.dumps({'schema_version': 2, 'result': 'approved', 'findings': [], 'padding': 'x' * 5000})
		dec_big = run_pre_tool_gates('send_message', {'Recipient': PARENT_CID, 'Message': big_json}, {'conversationId': CHILD_CID})
		self.assertEqual('deny', dec_big['decision'])
		ok_prompt = run_pre_tool_gates('send_message', {'Recipient': CHILD_CID, 'Message': 'Please run review-input on package abc-inputs.json.'}, {'conversationId': PARENT_CID})
		self.assertEqual('allow', ok_prompt['decision'])
		ok_short = run_pre_tool_gates('send_message', {'Recipient': PARENT_CID, 'Message': 'Audit finished; verdict is in final reply.'}, {'conversationId': CHILD_CID})
		self.assertEqual('allow', ok_short['decision'])
	def test_schedule_gate_blocks_after_send_message_and_ignores_task_sender(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Finish.'},
				{'step_index': 1, 'type': 'SYSTEM_MESSAGE', 'content': f'<SYSTEM_MESSAGE>\n[Message] timestamp=2026-11-24T03:15:26Z sender={PARENT_CID}/task-438 priority=MESSAGE_PRIORITY_HIGH content=Done\n</SYSTEM_MESSAGE>'},
				{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'name': 'send_message', 'args': {'Recipient': CHILD_CID, 'Message': 'Audit revised package.'}}]},
			]
			st = extract_segment_subagent_state(rows[1:])
			self.assertNotIn(PARENT_CID, st['spawned_uuids'])
			self.assertEqual(1, st['spawned'])
			log = base / 'brain' / PARENT_CID / '.system_generated/logs/transcript_full.jsonl'
			log.parent.mkdir(parents=True)
			log.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			deny_sm = evaluate_pre_tool_use_schedule('schedule', {'DurationSeconds': 600, 'TimerCondition': 'any', 'Prompt': 'check'}, {'conversationId': PARENT_CID, 'transcriptPath': str(log)})
			self.assertIsNotNone(deny_sm)
			self.assertIn('EXEC-4-SCHEDULE-GATE', deny_sm)
			empty_log = base / 'db_only' / 'brain' / PARENT_CID / '.system_generated/logs/transcript_full.jsonl'
			empty_log.parent.mkdir(parents=True)
			empty_log.write_text(json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'Finish.'}) + '\n', encoding='utf-8')
			db_path = base / 'db_only/conversation_summaries.db'
			conn = sqlite3.connect(db_path)
			try:
				conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,status TEXT,not_fully_idle INTEGER,killed INTEGER)')
				conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?)', (CHILD_CID, PARENT_CID, 'CASCADE_RUN_STATUS_RUNNING', 1, 0))
				conn.commit()
			finally:
				conn.close()
			deny_db = evaluate_pre_tool_use_schedule('schedule', {'DurationSeconds': 600, 'TimerCondition': 'any', 'Prompt': 'check'}, {'conversationId': PARENT_CID, 'transcriptPath': str(empty_log)})
			self.assertIsNotNone(deny_db)
			self.assertIn('EXEC-4-SCHEDULE-GATE', deny_db)
if '__main__' == __name__:
	unittest.main()
