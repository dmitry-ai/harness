# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Detect unfinished background tasks in Antigravity turns and inherit unclosed TDD-FULL-GATE":
# https://github.com/dmitry-ai/harness/issues/166
from __future__ import annotations
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid
SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools import completion, tdd_gate
from agent_tools.platforms import antigravity, trace_common
def _varint(val: int) -> bytes:
	out = bytearray()
	while True:
		b = val & 0x7F
		val >>= 7
		if val:
			out.append(b | 0x80)
		else:
			out.append(b)
			return bytes(out)
def _wire(field_num: int, payload: bytes) -> bytes:
	return _varint((field_num << 3) | 2) + _varint(len(payload)) + payload
class BackgroundWaitAndTddInheritanceTests(unittest.TestCase):
	def test_completed_prior_turn_does_not_bleed_tdd_events_into_unrelated_followup(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			repo = base / 'repo'
			(repo / 'tests').mkdir(parents=True)
			(repo / 'tests/test_a.py').write_text('import unittest\n', encoding='utf-8')
			(repo / 'tests/test_b.py').write_text('import unittest\n', encoding='utf-8')
			(repo / 'app.py').write_text('x = 1\n', encoding='utf-8')
			tx = base / 'transcript_full.jsonl'
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Fix app.py'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(repo / 'tests/test_a.py')}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest -f "{repo / "tests/test_a.py"}"'}}]},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nFAILED (failures=1)\n'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(repo / 'app.py')}}]},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'Edited file.'},
				{'step_index': 7, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py answer-prepare repo --response-file x.md'}}]},
				{'step_index': 8, 'type': 'GENERIC', 'content': '{"ready": true}'},
				{'step_index': 9, 'type': 'PLANNER_RESPONSE', 'content': 'Исправление в app.py выполнено и зафиксировано.'},
				{'step_index': 10, 'type': 'USER_INPUT', 'content': 'Объясни, как работает кэш.'},
			]
			tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
			events = tdd_gate.extract_antigravity_tdd_events(tx, cwd=repo)
			self.assertEqual(events, [])
			res = tdd_gate.evaluate_tdd_events(events, require_final_full_green=True)
			self.assertTrue(res['verified'], res)
	def test_unfinished_background_run_command_and_russian_stub_merge_and_preserve_tdd_full_gate(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'proj'
			code = proj / 'code'
			(proj / '_/ꙮ/≻').mkdir(parents=True)
			(proj / '_/ꙮ/≺').mkdir(parents=True)
			(code / 'tests').mkdir(parents=True)
			subprocess.run(['git', 'init', str(code)], check=True, capture_output=True)
			(code / 'tests/test_a.py').write_text('import unittest\n', encoding='utf-8')
			(code / 'tests/test_b.py').write_text('import unittest\n', encoding='utf-8')
			(code / 'app.py').write_text('x = 1\n', encoding='utf-8')
			ag_backend = base / 'ag_home/.gemini/antigravity'
			(ag_backend / 'conversations').mkdir(parents=True)
			cid = str(uuid.uuid4())
			tx = ag_backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
			tx.parent.mkdir(parents=True)
			req1 = 'Исправь ошибку в app.py.'
			req2 = 'Почему тест идёт так долго?'
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': req1},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(code / 'tests/test_a.py')}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest -f "{code / "tests/test_a.py"}"'}}]},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nFAILED (failures=1)\n'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(code / 'app.py')}}]},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'Edited file.'},
				{'step_index': 7, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest discover -s "{code / "tests"}" -p test_*.py'}}]},
				{'step_index': 8, 'type': 'GENERIC', 'content': f'Tool is running as a background task with task id: {cid}/task-464'},
				{'step_index': 9, 'type': 'PLANNER_RESPONSE', 'content': 'Ожидаю завершения прогона тестов (`task-464`).'},
				{'step_index': 10, 'type': 'USER_INPUT', 'content': req2},
			]
			tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
			with closing(sqlite3.connect(ag_backend / 'conversation_summaries.db')) as conn:
				conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, workspace_uris TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER, agent_name TEXT)')
				conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (cid, '', json.dumps([proj.as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 10, 'primary'))
				conn.commit()
			with closing(sqlite3.connect(ag_backend / 'conversations' / f'{cid}.db')) as conn:
				conn.execute('CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
				conn.execute('INSERT INTO steps VALUES(0, 14, 3, 0, ?)', (_wire(19, _wire(2, req1.encode('utf-8'))),))
				conn.execute('INSERT INTO steps VALUES(9, 15, 3, 0, NULL)')
				conn.execute('INSERT INTO steps VALUES(10, 14, 3, 0, ?)', (_wire(19, _wire(2, req2.encode('utf-8'))),))
				conn.commit()
			native = antigravity.native_answers(proj, cid, backend=ag_backend)
			self.assertEqual(len(native['turns']), 1, native['turns'])
			self.assertEqual([r['id'] for r in native['turns'][0]['requests']], [f'{cid}-0', f'{cid}-10'])
			chk_stub = completion.check_answer(proj, 'Ожидаю завершения прогона тестов (`task-464`).  \n', cid, platform='antigravity', backend=ag_backend)
			self.assertFalse(chk_stub['checks']['language_and_stub'], chk_stub)
			self.assertFalse(chk_stub['checks']['tdd'], chk_stub)
			extracted = tdd_gate.extract_antigravity_tdd_events(tx, cwd=code)
			eval_before = tdd_gate.evaluate_tdd_events(extracted, require_final_full_green=True)
			self.assertFalse(eval_before['verified'], eval_before)
			self.assertTrue(any(('TDD-FULL-GATE' in v for v in eval_before['violations'])), eval_before)
			rows.extend([
				{'step_index': 11, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest discover -f -s "{code / "tests"}" -p test_*.py'}}]},
				{'step_index': 12, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\nRan 2 tests in 0.05s\n\nOK\n'},
			])
			tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
			eval_after = tdd_gate.evaluate_tdd_events(tdd_gate.extract_antigravity_tdd_events(tx, cwd=code), require_final_full_green=True)
			self.assertTrue(eval_after['verified'], eval_after)
	def test_waiting_stub_classifier_handles_ru_en_and_avoids_false_positives(self) -> None:
		self.assertTrue(trace_common.is_waiting_status_stub('Waiting for the remaining 1 subagent to complete.'))
		self.assertTrue(trace_common.is_waiting_status_stub('Subagent 1 finished. Waiting for background task task-12 to finish.'))
		self.assertTrue(trace_common.is_waiting_status_stub('Ожидаю завершения прогона тестов (`task-464`).'))
		self.assertTrue(trace_common.is_waiting_status_stub('Полный прогон тестов репозитория (`task-523`) запущен в фоне; после завершения закрою issue.'))
		self.assertFalse(trace_common.is_waiting_status_stub('Обе задачи выполнены и проверены.'))
		self.assertFalse(trace_common.is_waiting_status_stub('# Итоги\n\nИсправлен детектор заглушек вида «Ожидаю завершения прогона тестов» и «Waiting for task to complete».  \n'))
if '__main__' == __name__:
	unittest.main()
