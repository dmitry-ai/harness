# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify handed-off turn routing and deterministic state selection across hooks":
# https://github.com/dmitry-ai/harness/issues/231
from __future__ import annotations
from contextlib import closing
from pathlib import Path
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
import check_pre_invocation
import check_stop_gate
CID = 'be6873ea-5b72-4a7f-82bd-420b873f13f9'
JOB_1 = '022124567641351805598'
JOB_2 = '099999999999999999999'
def _wire(field: int, payload: bytes) -> bytes:
	out = bytearray()
	for val in ((field << 3) | 2, len(payload)):
		while True:
			b = val & 127
			val >>= 7
			out.append(b | 128 if val else b)
			if not val:
				break
	return bytes(out) + payload
def _build_ag_env(base: Path, ws_root: Path, turn1_text: str, turn2_text: str, *, turn2_reply: str='') -> tuple[Path, Path]:
	backend = base / 'ag_backend'
	(backend / 'conversations').mkdir(parents=True, exist_ok=True)
	log_file = backend / 'brain' / CID / '.system_generated/logs/transcript_full.jsonl'
	log_file.parent.mkdir(parents=True, exist_ok=True)
	rows = [
		{'step_index': 0, 'type': 'USER_INPUT', 'content': turn1_text},
		{'step_index': 10, 'type': 'PLANNER_RESPONSE', 'content': 'Turn 1 complete.', 'tool_calls': []},
		{'step_index': 434, 'type': 'USER_INPUT', 'content': turn2_text},
	]
	if turn2_reply:
		rows.append({'step_index': 450, 'type': 'PLANNER_RESPONSE', 'content': turn2_reply, 'tool_calls': []})
	log_file.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
	with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as conn:
		conn.execute('CREATE TABLE conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, workspace_uris TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER, agent_name TEXT)')
		conn.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (CID, '', json.dumps([ws_root.as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 434, 'primary'))
		conn.commit()
	with closing(sqlite3.connect(backend / 'conversations' / f'{CID}.db')) as conn:
		conn.execute('CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
		conn.execute('INSERT INTO steps VALUES(0, 14, 3, 0, ?)', (_wire(19, _wire(2, turn1_text.encode('utf-8'))),))
		conn.execute('INSERT INTO steps VALUES(10, 15, 3, 0, NULL)')
		conn.execute('INSERT INTO steps VALUES(434, 14, 3, 0, ?)', (_wire(19, _wire(2, turn2_text.encode('utf-8'))),))
		if turn2_reply:
			conn.execute('INSERT INTO steps VALUES(450, 15, 3, 0, NULL)')
		conn.commit()
	return (backend, log_file)
def _stop_payload(cwd: Path, log_file: Path) -> dict:
	return {
		'hookEventName': 'Stop',
		'cwd': str(cwd),
		'workspacePaths': [str(cwd)],
		'conversationId': CID,
		'transcriptPath': str(log_file),
		'terminationReason': 'NO_TOOL_CALL',
		'error': '',
		'fullyIdle': True,
		'continuationActive': False,
		'executionNum': 0,
	}
def _setup_launcher_and_daily(base: Path) -> tuple[Path, Path]:
	launcher = base / 'proposals/init'
	daily = base / 'proposals/daily/2026/11/23/1 - magento-nextjs-ga4-reporting'
	for root in (launcher, daily):
		(root / '\ua66e/\u227a').mkdir(parents=True)
		(root / '\ua66e/\u227b').mkdir(parents=True)
		(root / '\ua616/data/turns').mkdir(parents=True)
	(daily / '\ua616/project.json').write_text(json.dumps({'job_id': f'~{JOB_1}', 'snapshot': '\ua616/KB/Evidence/intake.json'}), encoding='utf-8')
	handed_off = {'key': '0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-0', 'native_start_step': 0, 'status': 'handed_off', 'handed_off_to': {'project_root': str(daily), 'job_id': JOB_1}}
	(launcher / '\ua616/data/turns/0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73.json').write_text(json.dumps(handed_off), encoding='utf-8')
	return (launcher, daily)
class TurnRoutingAndHandoffM6Tests(unittest.TestCase):
	def test_pre_invocation_allows_new_job_in_launcher_instead_of_routing(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			launcher, daily = _setup_launcher_and_daily(base)
			backend, log_file = _build_ag_env(base, launcher, f'/upwork-init https://upwork.com/jobs/~{JOB_1}', f'/upwork-init https://upwork.com/jobs/~{JOB_2}')
			out = check_pre_invocation.evaluate_pre_invocation_payload({'conversationId': CID, 'cwd': str(launcher), 'transcriptPath': str(log_file)}, backend_override=backend)
			msg = str(((out.get('injectSteps') or [{}])[0].get('systemMessage') or {}).get('systemMessage') or '')
			self.assertIn(launcher.as_posix(), msg, out)
			self.assertEqual([], list((daily / '\ua616/data/turns').glob('*.json')))
	def test_pre_invocation_fast_exits_on_same_turn1_handed_off_step(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			launcher, daily = _setup_launcher_and_daily(base)
			req1 = f'/upwork-init https://upwork.com/jobs/~{JOB_1}'
			backend, log_file = _build_ag_env(base, launcher, req1, 'unused')
			log_file.write_text(json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': req1}) + '\n', encoding='utf-8')
			with closing(sqlite3.connect(backend / 'conversations' / f'{CID}.db')) as conn:
				conn.execute('DELETE FROM steps WHERE idx > 0')
				conn.commit()
			out = check_pre_invocation.evaluate_pre_invocation_payload({'conversationId': CID, 'cwd': str(launcher), 'transcriptPath': str(log_file), 'invocationNum': 1}, backend_override=backend)
			self.assertEqual({}, out)
			self.assertEqual([], list((daily / '\ua616/data/turns').glob('*.json')))
	def test_pre_invocation_routes_turn2_handed_off_to_daily_without_launcher_orphan(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			launcher, daily = _setup_launcher_and_daily(base)
			backend, log_file = _build_ag_env(base, launcher, f'/upwork-init https://upwork.com/jobs/~{JOB_1}', 'Finish the analysis now.')
			out = check_pre_invocation.evaluate_pre_invocation_payload({'conversationId': CID, 'cwd': str(launcher), 'transcriptPath': str(log_file)}, backend_override=backend)
			msg = str(((out.get('injectSteps') or [{}])[0].get('systemMessage') or {}).get('systemMessage') or '')
			self.assertIn(daily.as_posix(), msg, out)
			self.assertEqual(['0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73.json'], sorted(p.name for p in (launcher / '\ua616/data/turns').glob('*.json')))
			self.assertEqual([], list((launcher / '\ua616/data').rglob('turn-reservations.json')))
			all_daily = list((daily / '\ua616/data/turns').glob('*.json'))
			self.assertEqual(2, len(all_daily))
			daily_turns = [p for p in all_daily if 'open' == json.loads(p.read_text(encoding='utf-8')).get('status')]
			self.assertEqual(1, len(daily_turns))
			self.assertEqual(434, json.loads(daily_turns[0].read_text(encoding='utf-8'))['native_start_step'])
			self.assertEqual({}, check_pre_invocation.evaluate_pre_invocation_payload({'conversationId': CID, 'cwd': str(launcher), 'transcriptPath': str(log_file)}, backend_override=backend))
	def test_stop_gate_deterministic_priority_prevents_alphabetical_shadowing(self) -> None:
		from agent_tools.turn_routing import resolve_active_turn_state
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			_launcher, daily = _setup_launcher_and_daily(base)
			reply_text = 'Final prepared response.'
			backend, log_file = _build_ag_env(base, daily, f'/upwork-init https://upwork.com/jobs/~{JOB_1}', 'Finish now.', turn2_reply=reply_text)
			res_file = daily / '\ua66e/\u227a/1\u201320/3.md'
			res_file.parent.mkdir(parents=True, exist_ok=True)
			res_file.write_text(reply_text, encoding='utf-8')
			sha = hashlib.sha256(reply_text.encode('utf-8')).hexdigest()
			stale_open = {'key': '0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-0', 'native_start_step': 0, 'status': 'open', 'requests': [{'id': f'{CID}-0', 'native_step': 0}, {'id': f'{CID}-434', 'native_step': 434}], 'readiness_check': {'verified': False, 'gate_id': 'issue_first', 'detail': 'EXEC-5 ISSUE-FIRST-GATE: step 269'}}
			fresh_prep = {'key': '6f7be571e32c539377281da738e4fb213fb504c8', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-434', 'native_start_step': 434, 'status': 'prepared', 'requests': [{'id': f'{CID}-434', 'native_step': 434}], 'readiness_check': {'verified': True}, 'prepared': {'response_file': str(res_file), 'response_sha256': sha, 'body_sha256': sha}}
			(daily / '\ua616/data/turns/0d2d6db4bdc4b0a412770e7aec3fe1fdf8688d73.json').write_text(json.dumps(stale_open), encoding='utf-8')
			(daily / '\ua616/data/turns/6f7be571e32c539377281da738e4fb213fb504c8.json').write_text(json.dumps(fresh_prep), encoding='utf-8')
			picked = resolve_active_turn_state(daily / '\ua616/data/turns', CID, 434)
			self.assertIsNotNone(picked)
			self.assertEqual('6f7be571e32c539377281da738e4fb213fb504c8', picked['key'])
			res = check_stop_gate.evaluate_stop_payload(_stop_payload(daily, log_file), backend_override=backend)
			self.assertEqual('allow', res['decision'], res)
	def test_stop_gate_ignores_launcher_orphan_open_when_handed_off_matches(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			launcher, daily = _setup_launcher_and_daily(base)
			reply_text = 'Final prepared response.'
			backend, log_file = _build_ag_env(base, launcher, f'/upwork-init https://upwork.com/jobs/~{JOB_1}', 'Finish now.', turn2_reply=reply_text)
			orphan = {'key': '6f7be571e32c539377281da738e4fb213fb504c8', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-434', 'native_start_step': 434, 'status': 'open', 'requests': [{'id': f'{CID}-434', 'native_step': 434}]}
			(launcher / '\ua616/data/turns/6f7be571e32c539377281da738e4fb213fb504c8.json').write_text(json.dumps(orphan), encoding='utf-8')
			res_file = daily / '\ua66e/\u227a/1\u201320/3.md'
			res_file.parent.mkdir(parents=True, exist_ok=True)
			res_file.write_text(reply_text, encoding='utf-8')
			sha = hashlib.sha256(reply_text.encode('utf-8')).hexdigest()
			daily_prep = {'key': '6f7be571e32c539377281da738e4fb213fb504c8', 'conversation_id': CID, 'native_turn_id': f'ag-{CID}-434', 'native_start_step': 434, 'status': 'prepared', 'requests': [{'id': f'{CID}-434', 'native_step': 434}], 'readiness_check': {'verified': True}, 'prepared': {'response_file': str(res_file), 'response_sha256': sha, 'body_sha256': sha}}
			(daily / '\ua616/data/turns/6f7be571e32c539377281da738e4fb213fb504c8.json').write_text(json.dumps(daily_prep), encoding='utf-8')
			res = check_stop_gate.evaluate_stop_payload(_stop_payload(launcher, log_file), backend_override=backend)
			self.assertEqual('allow', res['decision'], res)
if '__main__' == __name__:
	unittest.main()
