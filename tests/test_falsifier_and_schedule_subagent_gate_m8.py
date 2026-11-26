# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.failfast_gate import evaluate_pre_tool_use_schedule
PARENT_CID = 'be6873ea-5b72-4a7f-82bd-420b873f13f9'
CHILD_CID = '8ec25783-99cc-40fa-99ff-a557eb04dde3'
# @used-by :meth:`FalsifierAndScheduleSubagentGateM8Tests.test_allows_schedule_after_subagent_finishes_or_on_explicit_slash_schedule()`
# @used-by :meth:`FalsifierAndScheduleSubagentGateM8Tests.test_blocks_one_shot_schedule_while_invoke_subagent_is_active()`
def _write_transcript(base: Path, cid: str, rows: list[dict]) -> Path:
	log = base / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
	log.parent.mkdir(parents=True, exist_ok=True)
	log.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
	return log
# 2026-11-24
# "Default upwork-init review to single falsifier and block subagent schedule timers":
# https://github.com/dmitry-ai/harness/issues/215
class FalsifierAndScheduleSubagentGateM8Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_blocks_one_shot_schedule_while_invoke_subagent_is_active(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Run audit.'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'TypeName': 'self', 'Role': 'Auditor', 'Prompt': 'Audit'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': json.dumps({'conversationId': CHILD_CID})},
			]
			log = _write_transcript(base, PARENT_CID, rows)
			deny_active = evaluate_pre_tool_use_schedule('schedule', {'DurationSeconds': 600, 'Prompt': 'Wait for auditor'}, {'conversationId': PARENT_CID, 'transcriptPath': str(log)})
			self.assertIsNotNone(deny_active)
			self.assertIn('EXEC-4-SCHEDULE-GATE', deny_active)
			self.assertIn('invoke_subagent', deny_active)
			deny_cond = evaluate_pre_tool_use_schedule('schedule', {'DurationSeconds': 120, 'TimerCondition': CHILD_CID, 'Prompt': 'Check'}, {'conversationId': PARENT_CID, 'transcriptPath': str(log)})
			self.assertIsNotNone(deny_cond)
			self.assertIn(CHILD_CID, deny_cond)
	# @used-by :mod:`unittest`
	def test_allows_schedule_after_subagent_finishes_or_on_explicit_slash_schedule(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			done_rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Run audit.'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'TypeName': 'self', 'Role': 'Auditor', 'Prompt': 'Audit'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': json.dumps({'conversationId': CHILD_CID})},
				{'step_index': 3, 'type': 'SYSTEM_MESSAGE', 'content': f'<SYSTEM_MESSAGE>\n[Message] timestamp=2026-11-22T23:18:00Z sender={CHILD_CID} priority=MESSAGE_PRIORITY_HIGH content=Done\n</SYSTEM_MESSAGE>'},
			]
			log_done = _write_transcript(base / 'done', PARENT_CID, done_rows)
			db_path = base / 'done/conversation_summaries.db'
			conn = sqlite3.connect(db_path)
			try:
				conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,status TEXT,not_fully_idle INTEGER,killed INTEGER)')
				conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?)', (CHILD_CID, PARENT_CID, 'CASCADE_RUN_STATUS_IDLE', 0, 0))
				conn.commit()
			finally:
				conn.close()
			self.assertIsNone(evaluate_pre_tool_use_schedule('schedule', {'DurationSeconds': 60, 'Prompt': 'Follow up later'}, {'conversationId': PARENT_CID, 'transcriptPath': str(log_done)}))
			explicit_rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': '/schedule remind me in 10 minutes'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'TypeName': 'self', 'Role': 'Auditor', 'Prompt': 'Audit'}}]},
			]
			log_exp = _write_transcript(base / 'exp', PARENT_CID, explicit_rows)
			self.assertIsNone(evaluate_pre_tool_use_schedule('schedule', {'DurationSeconds': 600, 'Prompt': 'User reminder'}, {'conversationId': PARENT_CID, 'transcriptPath': str(log_exp)}))
if '__main__' == __name__:
	unittest.main()
