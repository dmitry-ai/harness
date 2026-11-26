# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.hook_runtime import iter_turn_state_files
import check_stop_gate
CID = '8001de65-315f-4a56-b144-3ae8e4fdc4eb'
# @used-by :meth:`StopGateContractTests.test_ag2_conversation_id_without_session_id_enforces_stop_gate()`
# @used-by :meth:`StopGateContractTests.test_continuation_active_guards_against_unchanged_readiness_loops_but_allows_progress()`
# @used-by :meth:`StopGateContractTests.test_fully_idle_false_pending_subagent_and_scope1_opt_out_allow_stop()`
# @used-by :meth:`StopGateContractTests.test_transcript_path_uuid_fallback_when_ids_absent()`
# @used-by :meth:`test_stop_gate_subagents_m1.StopGateSubagentsM1Tests.test_ag2_system_message_fallback_without_db_and_killed_or_prior_children()`
# @used-by :meth:`test_stop_gate_subagents_m1.StopGateSubagentsM1Tests.test_idle_children_in_summary_db_enforce_stop_gate_while_running_child_allows()`
def make_ag2_stop_payload(cwd: Path, conversation_id: str | None, transcript_path: Path, *, continuation_active: bool=False, execution_num: int=0, fully_idle: bool=True, last_user_input: str='Analyze skill namespaces.', include_cwd: bool=True) -> dict:
	payload: dict = {
		'hookEventName': 'Stop',
		'workspacePaths': [str(cwd)],
		'transcriptPath': str(transcript_path),
		'modelName': 'gemini-4-neon',
		'lastUserInput': last_user_input,
		'terminationReason': 'NO_TOOL_CALL',
		'error': '',
		'fullyIdle': fully_idle,
		'continuationActive': continuation_active,
		'executionNum': execution_num,
	}
	if include_cwd:
		payload['cwd'] = str(cwd)
	if None is not conversation_id:
		payload['conversationId'] = conversation_id
	return payload
# @used-by :meth:`StopGateContractTests.test_ag2_conversation_id_without_session_id_enforces_stop_gate()`
# @used-by :meth:`StopGateContractTests.test_continuation_active_guards_against_unchanged_readiness_loops_but_allows_progress()`
# @used-by :meth:`StopGateContractTests.test_fully_idle_false_pending_subagent_and_scope1_opt_out_allow_stop()`
# @used-by :meth:`StopGateContractTests.test_transcript_path_uuid_fallback_when_ids_absent()`
# @used-by :meth:`test_stop_gate_subagents_m1.StopGateSubagentsM1Tests.test_ag2_system_message_fallback_without_db_and_killed_or_prior_children()`
# @used-by :meth:`test_stop_gate_subagents_m1.StopGateSubagentsM1Tests.test_idle_children_in_summary_db_enforce_stop_gate_while_running_child_allows()`
def _setup_fixture(base: Path, cid: str, *, user_text: str='Analyze skill namespaces.', extra_rows: list[dict] | None=None, turn_state: dict | None=None) -> tuple[Path, Path, Path, Path]:
	proj = base / 'proj'
	backend = base / 'ag_backend'
	(proj / '\ua66e/\u227a').mkdir(parents=True)
	turns_dir = proj / '\ua616/data/turns'
	turns_dir.mkdir(parents=True)
	logs = backend / 'brain' / cid / '.system_generated/logs'
	logs.mkdir(parents=True)
	log_file = logs / 'transcript_full.jsonl'
	rows = [
		{'step_index': 0, 'type': 'USER_INPUT', 'content': user_text},
		*(extra_rows or ()),
		{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'content': 'Draft answer text.', 'tool_calls': []},
	]
	log_file.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
	state_file = turns_dir / 'turn001.json'
	if None is not turn_state:
		state_file.write_text(json.dumps(turn_state), encoding='utf-8')
	return (proj, backend, log_file, state_file)
# 2026-11-24
# "Align check_stop_gate with Antigravity 2.0 conversationId contract and continuation loop guard":
# https://github.com/dmitry-ai/harness/issues/197
class StopGateContractTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_ag2_conversation_id_without_session_id_enforces_stop_gate(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			state = {'key': 'turn001', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-0', 'native_start_step': 0, 'status': 'open', 'prepared': None, 'readiness_check': {'verified': False, 'gate_id': 'code_lifecycle', 'checked_at': '2026-11-24T01:27:05Z', 'detail': 'EXEC-5 violation'}}
			proj, backend, log_file, state_file = _setup_fixture(Path(tmp).resolve(), CID, turn_state=state)
			payload = make_ag2_stop_payload(proj, CID, log_file)
			self.assertNotIn('sessionId', payload)
			res = check_stop_gate.evaluate_stop_payload(payload, backend_override=backend)
			self.assertEqual('continue', res['decision'])
			self.assertIn('EXEC-5 violation', res['reason'])
			upper_res = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj, CID.upper(), log_file, include_cwd=False), backend_override=backend)
			self.assertEqual('continue', upper_res['decision'])
			res_file = proj / '\ua66e/\u227a/1.md'
			res_file.write_text('Draft answer text.', encoding='utf-8')
			state.update(status='prepared', readiness_check={'verified': True, 'checked_at': '2026-11-24T01:27:32Z'}, prepared={'response_file': str(res_file), 'response_sha256': '0', 'body_sha256': '0'})
			state_file.write_text(json.dumps(state), encoding='utf-8')
			ok_res = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj, CID, log_file, continuation_active=True, execution_num=1), backend_override=backend)
			self.assertEqual('allow', ok_res['decision'])
	# @used-by :mod:`unittest`
	def test_continuation_active_guards_against_unchanged_readiness_loops_but_allows_progress(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			state = {'key': 'turn001', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-0', 'native_start_step': 0, 'status': 'open', 'prepared': None, 'readiness_check': {'verified': False, 'gate_id': 'source_grounding', 'checked_at': '2026-11-24T01:20:00Z', 'detail': 'Missing link'}}
			proj, backend, log_file, state_file = _setup_fixture(Path(tmp).resolve(), CID, turn_state=state)
			r1 = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj, CID, log_file, continuation_active=False, execution_num=0), backend_override=backend)
			self.assertEqual('continue', r1['decision'])
			self.assertEqual(1, len(iter_turn_state_files(proj / '\ua616/data/turns')))
			r2_same = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj, CID, log_file, continuation_active=True, execution_num=1), backend_override=backend)
			self.assertEqual('allow', r2_same['decision'])
			state['readiness_check'] = {'verified': False, 'gate_id': 'code_lifecycle', 'checked_at': '2026-11-24T01:21:00Z', 'detail': 'Updated check'}
			state_file.write_text(json.dumps(state), encoding='utf-8')
			r3_prog = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj, CID, log_file, continuation_active=True, execution_num=1), backend_override=backend)
			self.assertEqual('continue', r3_prog['decision'])
			state['readiness_check'] = {'verified': False, 'gate_id': 'tdd', 'checked_at': '2026-11-24T01:22:00Z', 'detail': 'Third failure'}
			state_file.write_text(json.dumps(state), encoding='utf-8')
			r4_cap = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj, CID, log_file, continuation_active=True, execution_num=3), backend_override=backend)
			self.assertEqual('allow', r4_cap['decision'])
	# @used-by :mod:`unittest`
	def test_fully_idle_false_pending_subagent_and_scope1_opt_out_allow_stop(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			state = {'key': 'turn001', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-0', 'native_start_step': 0, 'status': 'open', 'prepared': None}
			proj, backend, log_file, _ = _setup_fixture(base / 'idle', CID, turn_state=state)
			r_idle = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj, CID, log_file, fully_idle=False), backend_override=backend)
			self.assertEqual('allow', r_idle['decision'])
			sub_rows = [{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'content': '', 'tool_calls': [{'name': 'invoke_subagent', 'args': {}}]}]
			proj_s, backend_s, log_s, _ = _setup_fixture(base / 'sub', CID, extra_rows=sub_rows, turn_state=state)
			r_sub = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj_s, CID, log_s), backend_override=backend_s)
			self.assertEqual('allow', r_sub['decision'])
			proj_ru, backend_ru, log_ru, _ = _setup_fixture(base / 'opt_ru', CID, user_text='\u041e\u0442\u0432\u0435\u0442\u044c \u043a\u0440\u0430\u0442\u043a\u043e, \u0431\u0435\u0437 \u0436\u0443\u0440\u043d\u0430\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f.', turn_state=state)
			r_ru = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj_ru, CID, log_ru, last_user_input='\u041e\u0442\u0432\u0435\u0442\u044c \u043a\u0440\u0430\u0442\u043a\u043e, \u0431\u0435\u0437 \u0436\u0443\u0440\u043d\u0430\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f.'), backend_override=backend_ru)
			self.assertEqual('allow', r_ru['decision'])
			proj_en, backend_en, log_en, _ = _setup_fixture(base / 'opt_en', CID, user_text='Answer briefly and skip journaling for this turn.', turn_state=state)
			r_en = check_stop_gate.evaluate_stop_payload(make_ag2_stop_payload(proj_en, CID, log_en, last_user_input='Answer briefly and skip journaling for this turn.'), backend_override=backend_en)
			self.assertEqual('allow', r_en['decision'])
	# @used-by :mod:`unittest`
	def test_transcript_path_uuid_fallback_when_ids_absent(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			state = {'key': 'turn001', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-0', 'native_start_step': 0, 'status': 'open', 'prepared': None}
			proj, backend, log_file, _ = _setup_fixture(Path(tmp).resolve(), CID, turn_state=state)
			payload = make_ag2_stop_payload(proj, None, log_file)
			self.assertNotIn('conversationId', payload)
			self.assertNotIn('sessionId', payload)
			res = check_stop_gate.evaluate_stop_payload(payload, backend_override=backend)
			self.assertEqual('continue', res['decision'])
if '__main__' == __name__:
	unittest.main()