# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Preserve multi-turn handed-off Stop Gate routing and stateful loop guard":
# https://github.com/dmitry-ai/harness/issues/224
from __future__ import annotations
from contextlib import closing
import hashlib
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
from agent_tools.platforms import antigravity
from agent_tools.tdd.events import _antigravity_segment_is_interrupted
import check_stop_gate
CID = 'be6873ea-5b72-4a7f-82bd-420b873f13f9'
def _wire(field: int, payload: bytes) -> bytes:
	tag = (field << 3) | 2
	out = bytearray()
	val = tag
	while True:
		b = val & 127
		val >>= 7
		out.append(b | 128 if val else b)
		if not val:
			break
	val = len(payload)
	while True:
		b = val & 127
		val >>= 7
		out.append(b | 128 if val else b)
		if not val:
			break
	return bytes(out) + payload
def _payload(cwd: Path, log_file: Path, *, cont: bool=False) -> dict:
	return {
		'hookEventName': 'Stop',
		'cwd': str(cwd),
		'workspacePaths': [str(cwd)],
		'conversationId': CID,
		'transcriptPath': str(log_file),
		'terminationReason': 'NO_TOOL_CALL',
		'error': '',
		'fullyIdle': True,
		'continuationActive': cont,
		'executionNum': 0,
	}
class MultiturnHandoffStopGuardAndScheduleM1Tests(unittest.TestCase):
	def test_handed_off_launcher_routes_turn2_followup_but_not_new_job_id(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			launcher = base / 'proposals/init'
			daily = base / 'proposals/daily/2026/11/23/1 - topic'
			backend = base / 'ag_backend'
			for root in (launcher, daily):
				(root / '\ua66e/\u227a').mkdir(parents=True)
				(root / '\ua616/data/turns').mkdir(parents=True)
			logs = backend / 'brain' / CID / '.system_generated/logs'
			logs.mkdir(parents=True)
			log_file = logs / 'transcript_full.jsonl'
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': '/upwork-init https://upwork.com/jobs/~022124567641351805598'},
				{'step_index': 433, 'type': 'PLANNER_RESPONSE', 'content': 'Turn 1 blocked summary.', 'tool_calls': []},
				{'step_index': 434, 'type': 'USER_INPUT', 'content': 'Finish the task now.'},
				{'step_index': 450, 'type': 'PLANNER_RESPONSE', 'content': 'Final prepared response.', 'tool_calls': []},
			]
			log_file.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			launcher_state = {'key': 'k1', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-0', 'native_start_step': 0, 'status': 'handed_off', 'handed_off_to': {'project_root': str(daily), 'job_id': '022124567641351805598'}}
			(launcher / '\ua616/data/turns/k1.json').write_text(json.dumps(launcher_state), encoding='utf-8')
			res_file = daily / '\ua66e/\u227a/1.md'
			res_file.write_text('Final prepared response.', encoding='utf-8')
			sha = hashlib.sha256(b'Final prepared response.').hexdigest()
			daily_state = {'key': 'k1', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-434', 'native_start_step': 434, 'status': 'prepared', 'readiness_check': {'verified': True}, 'prepared': {'response_file': str(res_file), 'response_sha256': sha, 'body_sha256': sha}}
			(daily / '\ua616/data/turns/k1.json').write_text(json.dumps(daily_state), encoding='utf-8')
			res = check_stop_gate.evaluate_stop_payload(_payload(launcher, log_file), backend_override=backend)
			self.assertEqual('allow', res['decision'], res)
			new_job_rows = rows[:2] + [{'step_index': 434, 'type': 'USER_INPUT', 'content': '/upwork-init https://upwork.com/jobs/~099999999999999999999'}]
			matched_new = check_stop_gate._find_turn_state(launcher / '\ua616/data/turns', CID, 434, rows=new_job_rows)
			self.assertIsNone(matched_new)
	def test_stop_guard_breaks_loop_without_continuation_active_across_steps(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'proj'
			backend = base / 'ag_backend'
			(proj / '\ua66e/\u227a').mkdir(parents=True)
			(proj / '\ua616/data/turns').mkdir(parents=True)
			logs = backend / 'brain' / CID / '.system_generated/logs'
			logs.mkdir(parents=True)
			log_file = logs / 'transcript_full.jsonl'
			rows = [
				{'step_index': 434, 'type': 'USER_INPUT', 'content': 'Finish.'},
				{'step_index': 655, 'type': 'PLANNER_RESPONSE', 'content': 'Blocked report 1.', 'tool_calls': []},
			]
			log_file.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			r1 = check_stop_gate.evaluate_stop_payload(_payload(proj, log_file, cont=False), backend_override=backend)
			self.assertEqual('continue', r1['decision'])
			rows.append({'step_index': 659, 'type': 'PLANNER_RESPONSE', 'content': 'Blocked report 2.', 'tool_calls': []})
			log_file.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			r2 = check_stop_gate.evaluate_stop_payload(_payload(proj, log_file, cont=False), backend_override=backend)
			self.assertEqual('allow', r2['decision'], r2)
	def test_schedule_timers_and_stdout_prose_do_not_merge_completed_turn1_into_turn2(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'proj'
			(proj / '\ua66e/\u227a').mkdir(parents=True)
			(proj / '\ua66e/\u227b').mkdir(parents=True)
			ag_backend = base / 'ag_backend'
			(ag_backend / 'conversations').mkdir(parents=True)
			tx = ag_backend / 'brain' / CID / '.system_generated/logs/transcript_full.jsonl'
			tx.parent.mkdir(parents=True)
			req1, req2 = ('Analyze job.', 'Continue now.')
			turn1_body = [
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'schedule', 'args': {'DurationSeconds': 600, 'TimerCondition': 'any', 'Prompt': 'check'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': f'Tool is running as a background task with task id: {CID}/task-140'},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'echo done'}}]},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\nlog line task id: 8ec25783-99cc-40fa-99ff-a557eb0\n'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'content': 'Turn 1 complete response.', 'tool_calls': []},
			]
			self.assertFalse(_antigravity_segment_is_interrupted(turn1_body))
			rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': req1}, *turn1_body, {'step_index': 6, 'type': 'USER_INPUT', 'content': req2}]
			tx.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			with closing(sqlite3.connect(ag_backend / 'conversation_summaries.db')) as conn:
				conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, workspace_uris TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER, agent_name TEXT)')
				conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (CID, '', json.dumps([proj.as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 6, 'primary'))
				conn.commit()
			with closing(sqlite3.connect(ag_backend / 'conversations' / f'{CID}.db')) as conn:
				conn.execute('CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
				conn.execute('INSERT INTO steps VALUES(0, 14, 3, 0, ?)', (_wire(19, _wire(2, req1.encode('utf-8'))),))
				conn.execute('INSERT INTO steps VALUES(5, 15, 3, 0, NULL)')
				conn.execute('INSERT INTO steps VALUES(6, 14, 3, 0, ?)', (_wire(19, _wire(2, req2.encode('utf-8'))),))
				conn.commit()
			native = antigravity.native_answers(proj, CID, backend=ag_backend)
			self.assertEqual(2, len(native['turns']), native['turns'])
			self.assertTrue(native['turns'][0]['completed'])
			self.assertEqual(6, native['turns'][1]['start_step'])
if '__main__' == __name__:
	unittest.main()
