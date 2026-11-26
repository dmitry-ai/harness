# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Separate top-level turn-begin status from foreign_reconciliation across trace auditors":
# https://github.com/dmitry-ai/harness/issues/370
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
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
# @used-by :mod:`unittest`
class TurnBeginStatusAndAuditorsTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_begin_returns_top_level_ok_true_for_primary_dry_run_and_child_with_foreign_reconciliation(self) -> None:
		from agent_tools import completion
		from test_stop_emergency_capture_and_foreign_sync import _reserve_foreign, _seed_ag_conversation
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj, backend = (base / 'proj', base / 'ag_backend')
			(proj / '\ua66e').mkdir(parents=True)
			(proj / '\ua616/data/turns').mkdir(parents=True)
			cid_old = '11111111-aaaa-bbbb-cccc-111111111111'
			cid_cur = '22222222-aaaa-bbbb-cccc-222222222222'
			cid_child = '33333333-aaaa-bbbb-cccc-333333333333'
			_reserve_foreign(backend, proj, cid_old, 'Old prompt', 'Old reply.')
			_seed_ag_conversation(backend, proj, cid_cur, 'Current prompt', None, status='CASCADE_RUN_STATUS_RUNNING', not_fully_idle=1)
			_seed_ag_conversation(backend, proj, cid_child, 'Child subagent task', None, status='CASCADE_RUN_STATUS_RUNNING', not_fully_idle=1)
			with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as conn:
				conn.execute('INSERT OR REPLACE INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (cid_child, cid_cur, json.dumps([proj.resolve().as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 0, 'self'))
				conn.commit()
			dry_res = completion.begin(proj, cid_cur, platform='antigravity', backend=backend, dry_run=True)
			self.assertIs(True, dry_res.get('ok'), dry_res)
			child_res = completion.begin(proj, cid_child, platform='antigravity', backend=backend)
			self.assertIs(True, child_res.get('ok'), child_res)
			beg_res = completion.begin(proj, cid_cur, platform='antigravity', backend=backend)
			self.assertIs(True, beg_res.get('ok'), beg_res)
			self.assertTrue(bool(beg_res.get('foreign_reconciliation')), beg_res)
	# @used-by :mod:`unittest`
	def test_all_trace_auditors_ignore_nested_foreign_reconciliation_and_flag_top_level_failure(self) -> None:
		from agent_tools.cli_command_grounding import _is_passing_output
		from agent_tools.doc5_context import _is_failed_cli_output
		from agent_tools.verification_observability import _classify_shadow_output
		nested_payload = {
			'ok': True,
			'valid': True,
			'turn_key': 'active-turn-1',
			'status': 'open',
			'foreign_reconciliation': [{'turn_key': 'legacy-turn', 'result': {'valid': False, 'turns': [{'admission_verification': {'status': 'legacy_proof_gap'}}]}}],
		}
		passing_out = 'Command exited with code 0.\n\nCommand output:\n' + json.dumps(nested_payload, indent=2)
		self.assertFalse(_is_failed_cli_output(passing_out))
		self.assertTrue(_is_passing_output(passing_out))
		shadow_ok = _classify_shadow_output(2, passing_out)
		self.assertTrue(shadow_ok['passed'], shadow_ok)
		self.assertFalse(shadow_ok['failed'], shadow_ok)
		for bad_json in ('{"valid": false, "errors": ["failed"]}', '{"ok": false, "stage": "lint"}'):
			bad_out = f'Command exited with code 0.\n\nCommand output:\n{bad_json}'
			self.assertTrue(_is_failed_cli_output(bad_out))
			self.assertFalse(_is_passing_output(bad_out))
			shadow_bad = _classify_shadow_output(4, bad_out)
			self.assertFalse(shadow_bad['passed'], shadow_bad)
			self.assertTrue(shadow_bad['failed'], shadow_bad)
if '__main__' == __name__:
	unittest.main()
