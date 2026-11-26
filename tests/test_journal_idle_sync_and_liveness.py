# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reconcile idle prepared turns and verify liveness for orphaned reservations":
# https://github.com/dmitry-ai/harness/issues/295
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
# @used-by :mod:`unittest`
class JournalIdleSyncAndLivenessTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_idle_prepared_turn_transitions_to_delivered_via_foreign_sync_and_all_open_without_mutating_journal(self) -> None:
		from agent_tools import completion
		from test_stop_emergency_capture_and_foreign_sync import _seed_ag_conversation
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj, backend = (base / 'proj', base / 'ag_backend')
			(proj / '\ua66e').mkdir(parents=True)
			(proj / '\ua616/data/turns').mkdir(parents=True)
			cid1 = 'aaaaaaaa-1111-2222-3333-444444444441'
			cid2 = 'bbbbbbbb-1111-2222-3333-444444444442'
			reply1 = 'Prepared final response from chat one.  \n'
			_seed_ag_conversation(backend, proj, cid1, 'First user prompt', None, status='CASCADE_RUN_STATUS_RUNNING', not_fully_idle=1)
			prep = completion.prepare(proj, reply1, conversation=cid1, platform='antigravity', backend=backend)
			turn1_file = proj / '\ua616/data/turns' / f"{prep['turn_key']}.json"
			self.assertEqual('prepared', json.loads(turn1_file.read_text(encoding='utf-8'))['status'])
			self.assertIsNone(json.loads(turn1_file.read_text(encoding='utf-8')).get('delivery'))
			res_file = Path(prep['response_file'])
			res_sha_before = hashlib.sha256(res_file.read_bytes()).hexdigest()
			_seed_ag_conversation(backend, proj, cid1, 'First user prompt', reply1, status='CASCADE_RUN_STATUS_IDLE', not_fully_idle=0)
			_seed_ag_conversation(backend, proj, cid2, 'Second user prompt', None, status='CASCADE_RUN_STATUS_RUNNING', not_fully_idle=1)
			beg2 = completion.begin(proj, cid2, platform='antigravity', backend=backend)
			synced_keys = [item['turn_key'] for item in (beg2.get('foreign_reconciliation') or ())]
			self.assertIn(prep['turn_key'], synced_keys, beg2)
			turn1_after = json.loads(turn1_file.read_text(encoding='utf-8'))
			self.assertEqual('delivered', turn1_after['status'], turn1_after)
			self.assertTrue((turn1_after.get('delivery') or {}).get('verified'), turn1_after)
			self.assertEqual(res_sha_before, hashlib.sha256(res_file.read_bytes()).hexdigest())
	# @used-by :mod:`unittest`
	def test_all_open_syncs_idle_prepared_turn(self) -> None:
		from agent_tools import completion
		from test_stop_emergency_capture_and_foreign_sync import _seed_ag_conversation
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj, backend = (base / 'proj', base / 'ag_backend')
			(proj / '\ua66e').mkdir(parents=True)
			(proj / '\ua616/data/turns').mkdir(parents=True)
			cid1 = 'cccccccc-1111-2222-3333-444444444443'
			reply1 = 'Prepared final response for all-open sync.  \n'
			_seed_ag_conversation(backend, proj, cid1, 'All-open prompt', None, status='CASCADE_RUN_STATUS_RUNNING', not_fully_idle=1)
			prep = completion.prepare(proj, reply1, conversation=cid1, platform='antigravity', backend=backend)
			_seed_ag_conversation(backend, proj, cid1, 'All-open prompt', reply1, status='CASCADE_RUN_STATUS_IDLE', not_fully_idle=0)
			sync_res = completion.sync(proj, all_open=True)
			self.assertTrue(sync_res['valid'], sync_res)
			self.assertGreaterEqual(sync_res['synced_count'], 1, sync_res)
			st_after = json.loads((proj / '\ua616/data/turns' / f"{prep['turn_key']}.json").read_text(encoding='utf-8'))
			self.assertEqual('delivered', st_after['status'], st_after)
			self.assertTrue((st_after.get('delivery') or {}).get('verified'), st_after)
	# @used-by :mod:`unittest`
	def test_live_running_parallel_reservation_not_orphaned_while_idle_stuck_is_orphaned(self) -> None:
		from agent_tools import journal, journal_integrity as ji
		from test_journal_integrity import _write_step_pair, _write_turn_json
		from test_stop_emergency_capture_and_foreign_sync import _seed_ag_conversation
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj, backend = (base / 'proj', base / 'ag_backend')
			jdir = proj / '\ua66e'
			(jdir / '\u227b').mkdir(parents=True)
			(jdir / '\u227a').mkdir(parents=True)
			(proj / '\ua616/data/turns').mkdir(parents=True)
			cid_live = 'dddddddd-1111-2222-3333-444444444444'
			cid_stuck = 'eeeeeeee-1111-2222-3333-444444444445'
			_seed_ag_conversation(backend, proj, cid_live, 'Live parallel chat', None, status='CASCADE_RUN_STATUS_RUNNING', not_fully_idle=1, killed=0)
			_seed_ag_conversation(backend, proj, cid_stuck, 'Stuck idle chat', None, status='CASCADE_RUN_STATUS_IDLE', not_fully_idle=0, killed=0)
			_write_step_pair(jdir, 1)
			_write_step_pair(jdir, 3)
			journal.reserve_turn_steps(jdir, 'livekey01', cid_live, [f'{cid_live}-0'])
			res_f = journal.state_dir(jdir) / journal.TURN_RESERVATIONS_FILE
			res_data = json.loads(res_f.read_text(encoding='utf-8'))
			res_data['reservations']['livekey01']['steps'] = [2]
			res_data['reservations']['stuckkey1'] = {'conversation_id': cid_stuck, 'request_ids': [f'{cid_stuck}-0'], 'steps': [2]}
			res_f.write_text(json.dumps(res_data, indent=2), encoding='utf-8')
			_write_turn_json(proj, 'livekey01', {'key': 'livekey01', 'conversation_id': cid_live, 'platform': 'antigravity', 'native_backend': str(backend), 'native_start_step': 0, 'status': 'open', 'journal': str(jdir)})
			_write_turn_json(proj, 'stuckkey1', {'key': 'stuckkey1', 'conversation_id': cid_stuck, 'platform': 'antigravity', 'native_backend': str(backend), 'native_start_step': 0, 'status': 'open', 'journal': str(jdir)})
			classified = ji.classify_reservations(jdir, project_root=proj)
			self.assertEqual(['livekey01'], [x['turn_key'] for x in classified['active_parallel']], classified)
			self.assertTrue(any(('stuckkey1' in msg for msg in classified['orphaned'])), classified)
			self.assertFalse(any(('livekey01' in msg for msg in classified['orphaned'])), classified)
if '__main__' == __name__:
	unittest.main()