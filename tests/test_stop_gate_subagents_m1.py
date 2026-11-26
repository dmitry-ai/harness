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
TESTS = WT_ROOT / 'tests'
for p in (str(SCRIPTS), str(TESTS)):
	if p not in sys.path:
		sys.path.insert(0, p)
import check_stop_gate
from test_stop_gate_contract import _setup_fixture, make_ag2_stop_payload
PARENT_CID = 'be6873ea-5b72-4a7f-82bd-420b873f13f9'
CHILD_A = '8ec25783-99cc-40fa-99ff-a557eb04dde3'
CHILD_B = 'd5bbfade-006b-4f5e-8423-bb87a1c611b3'
OLD_CHILD = '0ea3513e-6dde-4e3c-88e6-caca5d08667e'
# @used-by :meth:`StopGateSubagentsM1Tests.test_ag2_system_message_fallback_without_db_and_killed_or_prior_children()`
# @used-by :meth:`StopGateSubagentsM1Tests.test_idle_children_in_summary_db_enforce_stop_gate_while_running_child_allows()`
def _create_summary_db(backend: Path, rows: list[tuple[str, str, str, int, int, str]]) -> None:
	db = backend / 'conversation_summaries.db'
	db.parent.mkdir(parents=True, exist_ok=True)
	conn = sqlite3.connect(db)
	try:
		conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT,parent_conversation_id TEXT,status TEXT,not_fully_idle INTEGER,killed INTEGER,last_modified_time TEXT)')
		for row in rows:
			conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?)', row)
		conn.commit()
	finally:
		conn.close()
# @used-by :meth:`StopGateSubagentsM1Tests.test_ag2_system_message_fallback_without_db_and_killed_or_prior_children()`
# @used-by :meth:`StopGateSubagentsM1Tests.test_idle_children_in_summary_db_enforce_stop_gate_while_running_child_allows()`
def _spawn_row(step: int, child_id: str) -> list[dict]:
	return [
		{'step_index': step, 'type': 'PLANNER_RESPONSE', 'content': '', 'created_at': '2026-11-22T23:10:00Z', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'TypeName': 'self', 'Role': 'Auditor', 'Prompt': 'Audit'}}]},
		{'step_index': step + 1, 'type': 'GENERIC', 'content': json.dumps({'conversationId': child_id}), 'created_at': '2026-11-22T23:10:01Z'},
	]
# @used-by :meth:`StopGateSubagentsM1Tests.test_ag2_system_message_fallback_without_db_and_killed_or_prior_children()`
# @used-by :meth:`StopGateSubagentsM1Tests.test_idle_children_in_summary_db_enforce_stop_gate_while_running_child_allows()`
def _sys_msg_row(step: int, sender_id: str) -> dict:
	return {'step_index': step, 'type': 'SYSTEM_MESSAGE', 'content': f'<SYSTEM_MESSAGE>\n[Message] timestamp=2026-11-22T23:18:00Z sender={sender_id} priority=MESSAGE_PRIORITY_HIGH content=Done\n</SYSTEM_MESSAGE>'}
# 2026-11-24
# "Detect active Antigravity 2.0 subagents in check_stop_gate via summary DB":
# https://github.com/dmitry-ai/harness/issues/211
class StopGateSubagentsM1Tests(unittest.TestCase):
	# @used-by :meth:`StopGateSubagentsM1Tests.test_ag2_system_message_fallback_without_db_and_killed_or_prior_children()`
	# @used-by :meth:`StopGateSubagentsM1Tests.test_idle_children_in_summary_db_enforce_stop_gate_while_running_child_allows()`
	def _base_state(self) -> dict:
		return {'key': 'turn001', 'conversation_id': PARENT_CID, 'native_turn_id': f'ag-{PARENT_CID}-0', 'native_start_step': 0, 'status': 'open', 'prepared': None}
	# @used-by :mod:`unittest`
	def test_idle_children_in_summary_db_enforce_stop_gate_while_running_child_allows(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			extra = [*_spawn_row(1, CHILD_A), *_spawn_row(3, CHILD_B), _sys_msg_row(4, CHILD_A), _sys_msg_row(5, CHILD_B)]
			proj, backend, log_file, _ = _setup_fixture(base / 'idle', PARENT_CID, extra_rows=extra, turn_state=self._base_state())
			_create_summary_db(backend, [
				(PARENT_CID, '', 'CASCADE_RUN_STATUS_IDLE', 0, 0, '2026-11-22 23:22:00+00:00'),
				(CHILD_A, PARENT_CID, 'CASCADE_RUN_STATUS_IDLE', 0, 0, '2026-11-22 23:19:00+00:00'),
				(CHILD_B, PARENT_CID, 'CASCADE_RUN_STATUS_IDLE', 0, 0, '2026-11-22 23:20:00+00:00'),
			])
			res_idle = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj, PARENT_CID, log_file), backend_override=backend)
			self.assertEqual('continue', res_idle['decision'])
			proj_r, backend_r, log_r, _ = _setup_fixture(base / 'running', PARENT_CID, extra_rows=extra, turn_state=self._base_state())
			_create_summary_db(backend_r, [
				(PARENT_CID, '', 'CASCADE_RUN_STATUS_IDLE', 0, 0, '2026-11-22 23:22:00+00:00'),
				(CHILD_A, PARENT_CID, 'CASCADE_RUN_STATUS_IDLE', 0, 0, '2026-11-22 23:19:00+00:00'),
				(CHILD_B, PARENT_CID, 'CASCADE_RUN_STATUS_RUNNING', 1, 0, '2026-11-22 23:20:00+00:00'),
			])
			res_run = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj_r, PARENT_CID, log_r), backend_override=backend_r)
			self.assertEqual('allow', res_run['decision'])
	# @used-by :mod:`unittest`
	def test_ag2_system_message_fallback_without_db_and_killed_or_prior_children(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			extra = [*_spawn_row(1, CHILD_A), _sys_msg_row(3, CHILD_A)]
			proj, backend, log_file, _ = _setup_fixture(base / 'nodb', PARENT_CID, extra_rows=extra, turn_state=self._base_state())
			res_nodb = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj, PARENT_CID, log_file), backend_override=backend)
			self.assertEqual('continue', res_nodb['decision'])
			kill_rows = [
				*_spawn_row(1, CHILD_A),
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'name': 'manage_subagents', 'args': {'Action': 'kill', 'ConversationIds': [CHILD_A]}}]},
			]
			proj_k, backend_k, log_k, _ = _setup_fixture(base / 'killed', PARENT_CID, extra_rows=kill_rows, turn_state=self._base_state())
			_create_summary_db(backend_k, [
				(PARENT_CID, '', 'CASCADE_RUN_STATUS_IDLE', 0, 0, '2026-11-22 23:22:00+00:00'),
				(CHILD_A, PARENT_CID, 'CASCADE_RUN_STATUS_RUNNING', 1, 1, '2026-11-22 23:19:00+00:00'),
				(OLD_CHILD, PARENT_CID, 'CASCADE_RUN_STATUS_RUNNING', 1, 0, '2026-11-21 10:00:00+00:00'),
			])
			res_k = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj_k, PARENT_CID, log_k), backend_override=backend_k)
			self.assertEqual('continue', res_k['decision'])
if '__main__' == __name__:
	unittest.main()
