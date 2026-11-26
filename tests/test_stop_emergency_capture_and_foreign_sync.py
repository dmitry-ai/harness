# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion, journal, metadata
import check_stop_gate
def _reserve_foreign(backend: Path, proj: Path, cid: str, req_text: str, resp_text: str | None, *, patch_state: dict | None=None, final_status: str='CASCADE_RUN_STATUS_IDLE') -> dict:
	_seed_ag_conversation(backend, proj, cid, req_text, None, status='CASCADE_RUN_STATUS_RUNNING', not_fully_idle=1)
	beg = completion.begin(proj, cid, platform='antigravity', backend=backend)
	if None is not patch_state:
		st_p = proj / '\ua616/data/turns' / f"{beg['turn_key']}.json"
		st_d = json.loads(st_p.read_text(encoding='utf-8'))
		st_d.update(patch_state)
		st_p.write_text(json.dumps(st_d), encoding='utf-8')
	if None is not resp_text:
		_seed_ag_conversation(backend, proj, cid, req_text, resp_text, status=final_status, not_fully_idle=0 if 'CASCADE_RUN_STATUS_IDLE' == final_status else 1)
	return beg
def _seed_ag_conversation(backend: Path, proj: Path, cid: str, req_text: str, resp_text: str | None, *, status: str='CASCADE_RUN_STATUS_IDLE', not_fully_idle: int=0, killed: int=0) -> Path:
	(backend / 'conversations').mkdir(parents=True, exist_ok=True)
	logs = backend / 'brain' / cid / '.system_generated/logs'
	logs.mkdir(parents=True, exist_ok=True)
	tx = logs / 'transcript_full.jsonl'
	rows: list[dict] = [{'step_index': 0, 'type': 'USER_INPUT', 'content': req_text, 'created_at': '2026-11-25T17:00:00Z'}]
	if None is not resp_text:
		rows.append({'step_index': 5, 'type': 'PLANNER_RESPONSE', 'content': resp_text, 'tool_calls': [], 'created_at': '2026-11-25T17:01:00Z'})
	tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
	with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as conn:
		conn.execute('CREATE TABLE IF NOT EXISTS conversation_summaries(conversation_id TEXT PRIMARY KEY, parent_conversation_id TEXT, workspace_uris TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER, agent_name TEXT)')
		conn.execute('INSERT OR REPLACE INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (cid, '', json.dumps([proj.resolve().as_uri()]), status, not_fully_idle, killed, 0, 'primary'))
		conn.commit()
	with closing(sqlite3.connect(backend / 'conversations' / f'{cid}.db')) as conn:
		conn.execute('CREATE TABLE IF NOT EXISTS steps(idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
		conn.execute('DELETE FROM steps')
		conn.execute('INSERT INTO steps VALUES(0, 14, 3, 0, ?)', (_wire(19, _wire(2, req_text.encode('utf-8'))),))
		if None is not resp_text:
			conn.execute('INSERT INTO steps VALUES(5, 15, 3, 0, ?)', (b'',))
		conn.commit()
	return tx
def _stop_payload(proj: Path, cid: str, tx: Path, req_text: str, *, continuation_active: bool=False, execution_num: int=0) -> dict:
	return {
		'hookEventName': 'Stop',
		'cwd': str(proj),
		'workspacePaths': [str(proj)],
		'conversationId': cid,
		'transcriptPath': str(tx),
		'lastUserInput': req_text,
		'terminationReason': 'NO_TOOL_CALL',
		'error': '',
		'fullyIdle': True,
		'continuationActive': continuation_active,
		'executionNum': execution_num,
	}
def _wire(field: int, payload: bytes) -> bytes:
	out = bytearray()
	val = field << 3 | 2
	while 128 <= val:
		out.append(val & 127 | 128)
		val >>= 7
	out.append(val)
	ln = len(payload)
	while 128 <= ln:
		out.append(ln & 127 | 128)
		ln >>= 7
	out.append(ln)
	return bytes(out) + payload
# 2026-11-25
# "Persist emergency journal capture on Stop Gate fail-open and sync idle foreign reservations in turn-begin":
# https://github.com/dmitry-ai/harness/issues/255
class StopEmergencyCaptureAndForeignSyncTests(unittest.TestCase):
	def test_begin_syncs_idle_open_foreign_reservation_and_skips_conflict_failed_and_running(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj, backend = (base / 'proj', base / 'ag_backend')
			(proj / '\ua66e').mkdir(parents=True)
			(proj / '\ua616/data/turns').mkdir(parents=True)
			beg_a = _reserve_foreign(backend, proj, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Foreign idle open req', 'Foreign idle open reply.')
			beg_b = _reserve_foreign(backend, proj, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Foreign conflict req', 'Conflict reply.', patch_state={'status': 'conflict'})
			beg_c = _reserve_foreign(backend, proj, 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'Foreign failed req', 'Failed reply.', patch_state={'readiness_check': {'verified': False, 'gate_id': 'code_lifecycle', 'detail': 'Unpushed'}})
			beg_d = _reserve_foreign(backend, proj, 'dddddddd-dddd-dddd-dddd-dddddddddddd', 'Foreign running req', None)
			_seed_ag_conversation(backend, proj, 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'Fresh active req', None, status='CASCADE_RUN_STATUS_RUNNING', not_fully_idle=1)
			beg_e = completion.begin(proj, 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', platform='antigravity', backend=backend)
			self.assertEqual([5], beg_e['reserved_journal_steps'])
			self.assertTrue((proj / '\ua66e/\u227b/1\u201320/1.md').is_file())
			self.assertTrue((proj / '\ua66e/\u227a/1\u201320/1.md').is_file())
			self.assertFalse((proj / '\ua66e/\u227a/1\u201320/2.md').exists())
			self.assertFalse((proj / '\ua66e/\u227a/1\u201320/3.md').exists())
			self.assertFalse((proj / '\ua66e/\u227a/1\u201320/4.md').exists())
			res_map = journal.iter_turn_reservations(proj / '\ua66e')
			self.assertNotIn(beg_a['turn_key'], res_map)
			self.assertIn(beg_b['turn_key'], res_map)
			self.assertIn(beg_c['turn_key'], res_map)
			self.assertIn(beg_d['turn_key'], res_map)
	def test_stop_gate_fail_open_persists_emergency_capture_and_sync_avoids_duplicate(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj, backend = (base / 'proj', base / 'ag_backend')
			(proj / '\ua66e').mkdir(parents=True)
			(proj / '\ua616/data/turns').mkdir(parents=True)
			cid, req_text, reply_text = ('12121212-1212-1212-1212-121212121212', 'Analyze failing PreToolUse hook.', 'Emergency unjournaled report text.')
			_seed_ag_conversation(backend, proj, cid, req_text, None, status='CASCADE_RUN_STATUS_RUNNING', not_fully_idle=1)
			beg = completion.begin(proj, cid, platform='antigravity', backend=backend)
			tx = _seed_ag_conversation(backend, proj, cid, req_text, reply_text, status='CASCADE_RUN_STATUS_IDLE', not_fully_idle=0)
			self.assertEqual('continue', check_stop_gate.evaluate_stop_payload(_stop_payload(proj, cid, tx, req_text, continuation_active=False, execution_num=0), backend_override=backend)['decision'])
			self.assertEqual('allow', check_stop_gate.evaluate_stop_payload(_stop_payload(proj, cid, tx, req_text, continuation_active=True, execution_num=1), backend_override=backend)['decision'])
			self.assertEqual(req_text, (proj / '\ua66e/\u227b/1\u201320/1.md').read_text(encoding='utf-8'))
			hdr, body = metadata.extract_leading_metadata_header((proj / '\ua66e/\u227a/1\u201320/1.md').read_text(encoding='utf-8'))
			self.assertEqual('stop_gate_emergency_capture', hdr['Journal']['Provenance'])
			self.assertFalse(hdr['Journal']['Preparation Verified'])
			self.assertTrue(bool(hdr['Journal'].get('FILE-3 Warning')))
			self.assertEqual(reply_text, body)
			st_after = json.loads((proj / '\ua616/data/turns' / f"{beg['turn_key']}.json").read_text(encoding='utf-8'))
			self.assertEqual(('stop_gate_emergency_capture', False, True, None), (st_after['completion_provenance'], st_after['preparation_verified'], st_after['recovered_after_delivery'], st_after['prepared']))
			self.assertNotIn(beg['turn_key'], journal.iter_turn_reservations(proj / '\ua66e'))
			synced = completion.sync(proj, cid, platform='antigravity', backend=backend)
			self.assertTrue(synced['valid'], synced)
			self.assertEqual(([1], 'stop_gate_emergency_capture', False), (synced['turns'][0]['journal_steps'], synced['turns'][0]['completion_provenance'], synced['turns'][0]['preparation_verified']))
			self.assertEqual(['1.md'], sorted((p.name for p in (proj / '\ua66e/\u227a/1\u201320').glob('*.md'))))
if '__main__' == __name__:
	unittest.main()
