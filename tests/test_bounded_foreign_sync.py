# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Bound synchronous foreign turn reconciliation with pending-sync index":
# https://github.com/dmitry-ai/harness/issues/341
from __future__ import annotations
from pathlib import Path
import json
import os
import sys
import tempfile
import time
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import journal_sync_all
# @used-by :meth:`BoundedForeignSyncTests.test_reconcile_foreign_enforces_batch_cap_recency_order_and_index()`
# @used-by :meth:`BoundedForeignSyncTests.test_reconcile_foreign_stops_on_time_budget_while_all_open_sweeps_all()`
def _seed_prepared_turns(root: Path, count: int) -> list[tuple[str, str]]:
	tdir = root / '\ua616/data/turns'
	tdir.mkdir(parents=True, exist_ok=True)
	(root / '\ua66e/\u227b').mkdir(parents=True, exist_ok=True)
	(root / '\ua66e/\u227a').mkdir(parents=True, exist_ok=True)
	seeded: list[tuple[str, str]] = []
	base_t = time.time() - (count + 5) * 10
	for idx in range(count):
		tk = f'tk{idx:04d}'
		cid = f'00000000-0000-4000-8000-{idx:012d}'
		fp = tdir / f'{tk}.json'
		fp.write_text(json.dumps({'key': tk, 'conversation_id': cid, 'platform': 'codex', 'status': 'prepared', 'delivery': None, 'journal': str(root / '\ua66e')}), encoding='utf-8')
		ts = base_t + idx * 10
		os.utime(fp, (ts, ts))
		seeded.append((tk, cid))
	return seeded
class BoundedForeignSyncTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_reconcile_foreign_enforces_batch_cap_recency_order_and_index(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			seeded = _seed_prepared_turns(root, 80)
			synced_cids: list[str] = []
			tdir = root / '\ua616/data/turns'
			# @used-by :meth:`BoundedForeignSyncTests.test_reconcile_foreign_enforces_batch_cap_recency_order_and_index()`
			def _fake_sync(_root, cid, **_kw):
				synced_cids.append(cid)
				tk = next((k for k, c in seeded if c == cid))
				fp = tdir / f'{tk}.json'
				obj = json.loads(fp.read_text(encoding='utf-8'))
				obj.update(status='delivered', delivery={'verified': True})
				fp.write_text(json.dumps(obj), encoding='utf-8')
				return {'valid': True, 'turns': [{'turn_key': tk, 'status': 'delivered'}]}
			t0 = time.monotonic()
			res1 = journal_sync_all.reconcile_foreign_open_reservations(root, 'ffffffff-ffff-4fff-8fff-ffffffffffff', folder_fn=lambda r: r / '\ua616/data/turns', dir_fn=lambda r, _j: r / '\ua66e', read_fn=lambda p: json.loads(p.read_text(encoding='utf-8')), sync_fn=_fake_sync, max_entries=5, time_budget_s=2.5)
			elapsed = time.monotonic() - t0
			self.assertLess(elapsed, 3.0)
			self.assertEqual(5, len(res1))
			self.assertEqual([c for _, c in reversed(seeded[-5:])], synced_cids)
			idx_file = tdir / 'pending-sync.json'
			self.assertTrue(idx_file.is_file())
			idx_data = json.loads(idx_file.read_text(encoding='utf-8'))
			self.assertEqual(75, len(idx_data.get('entries') or {}))
			res2 = journal_sync_all.reconcile_foreign_open_reservations(root, 'ffffffff-ffff-4fff-8fff-ffffffffffff', folder_fn=lambda r: r / '\ua616/data/turns', dir_fn=lambda r, _j: r / '\ua66e', read_fn=lambda p: json.loads(p.read_text(encoding='utf-8')), sync_fn=_fake_sync, max_entries=5, time_budget_s=2.5)
			self.assertEqual(5, len(res2))
			self.assertEqual(10, len(synced_cids))
			self.assertEqual(70, len((json.loads(idx_file.read_text(encoding='utf-8')).get('entries') or {})))
	# @used-by :mod:`unittest`
	def test_reconcile_foreign_stops_on_time_budget_while_all_open_sweeps_all(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			seeded = _seed_prepared_turns(root, 12)
			calls: list[str] = []
			tdir = root / '\ua616/data/turns'
			# @used-by :meth:`BoundedForeignSyncTests.test_reconcile_foreign_stops_on_time_budget_while_all_open_sweeps_all()`
			def _slow_sync(_root, cid, **_kw):
				time.sleep(0.06)
				calls.append(cid)
				tk = next((k for k, c in seeded if c == cid))
				fp = tdir / f'{tk}.json'
				obj = json.loads(fp.read_text(encoding='utf-8'))
				obj.update(status='delivered', delivery={'verified': True})
				fp.write_text(json.dumps(obj), encoding='utf-8')
				return {'valid': True, 'turns': [{'turn_key': tk, 'status': 'delivered'}]}
			res = journal_sync_all.reconcile_foreign_open_reservations(root, 'ffffffff-ffff-4fff-8fff-ffffffffffff', folder_fn=lambda r: r / '\ua616/data/turns', dir_fn=lambda r, _j: r / '\ua66e', read_fn=lambda p: json.loads(p.read_text(encoding='utf-8')), sync_fn=_slow_sync, max_entries=10, time_budget_s=0.11)
			self.assertGreaterEqual(len(res), 1)
			self.assertLess(len(res), 5)
			full = journal_sync_all.sync_all_open(root, folder_fn=lambda r: r / '\ua616/data/turns', dir_fn=lambda r, _j: r / '\ua66e', read_fn=lambda p: json.loads(p.read_text(encoding='utf-8')), sync_fn=_slow_sync)
			self.assertTrue(full['valid'], full)
			self.assertEqual(12, len(calls))
			idx_data = json.loads((tdir / 'pending-sync.json').read_text(encoding='utf-8'))
			self.assertEqual({}, idx_data.get('entries'))
if '__main__' == __name__:
	unittest.main()
