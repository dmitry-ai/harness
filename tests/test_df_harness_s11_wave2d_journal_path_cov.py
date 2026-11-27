# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from argparse import Namespace
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
_CID = '33333333-4444-5555-6666-777777777777'
# 2026-11-27 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :mod:`unittest`
class DfHarnessS11Wave2dJournalPathCovTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_cleanup_resolvers(self) -> None:
		from Df.Harness.Cleanup.StoreResolver import StoreResolver
		from Df.Harness.lib import cleanup_lifecycle_ops as clo, cleanup_store_ops as cso
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			p1, daily = (root / 'p1', root / 'daily')
			p1.mkdir()
			daily.mkdir()
			(root / 'h0').mkdir()
			db_c = sqlite3.connect(str(root / 'conversation_summaries.db'))
			db_c.execute('CREATE TABLE conversation_summaries (project_id TEXT, workspace_uris TEXT)')
			db_c.commit()
			db_c.close()
			ag_cfg = {'platforms': {'antigravity': {'adapter': 'antigravity', 'instances': {'A0': {'enabled': True, 'home': str(root / 'h0')}, 'A1': {'enabled': False, 'home': str(root / 'h1')}}}, 'codex': {'adapter': 'codex', 'instances': {}}}}
			self.assertIsInstance(StoreResolver(ag_cfg, daily, folders=root / 'f.json').run(), dict)
			self.assertIsNotNone(clo._parse_iso_dt('2026-11-27T00:00:00Z'))
			self.assertIsInstance(clo._disabled_ag_history(ag_cfg, root, {}), dict)
			res_f = p1 / 'r.md'
			res_f.write_text('hi', encoding='utf-8')
			self.assertIsNotNone(clo._step_response_time(res_f))
			self.assertTrue(clo._turn_matches_project({'project_root': str(p1)}, {str(p1).lower()}, 'j1', lambda s: str(s).lower()))
			self.assertIsInstance(cso._read_ag_entry((root / 'no_brain', True)), list)
			self.assertIsInstance(cso.dfh_conversations(p1, {}, root, {}, {}), dict)
	# @used-by :mod:`unittest`
	def test_journal_integrity_and_records(self) -> None:
		from Df.Harness.Journal.LivenessProbe import LivenessProbe
		from Df.Harness.lib import journal_core as jc, journal_integrity_ops as jio, journal_records as jr, journal_reservations as jres
		from Df.Harness.lib.path_resolve import dfh_project_paths
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/data/turns').mkdir(parents=True)
			jdir = root / '\ua66e'
			self.assertEqual(jr.dfh_record_step(jdir, 'req 1', 'res 1'), 1)
			self.assertEqual(jr.dfh_step_errors(jdir, 1), [])
			self.assertTrue(jr.dfh_validate_step(jdir, 1))
			self.assertEqual(jr.dfh_record_step(jdir, 'req 3', 'res 3', target_step=3), 3)
			self.assertEqual(jio.dfh_missing_contiguous_steps(jdir, {1, 3}), [2])
			self.assertTrue(jio.dfh_journal_validation_errors(jdir, project_root=root, strict_sequence=True))
			pp = dfh_project_paths(root, exact_root=True)
			self.assertFalse(jio.dfh_finalize_project_check(pp, [], root)['valid'])
			jio._subtract_entry_overlap({'request_ids': ['a', 'b'], 'steps': [1, 2]}, {'a'}, {1})
			self.assertTrue(jio._mentioned_other_job([{'text': '/upwork-init ~9999999999'}], '~1111111111'))
			st_conf = {'key': 'k2', 'conversation_id': _CID, 'status': 'conflict', 'delivery': {'retryable': False}}
			self.assertTrue(jio._is_terminal_conflict(st_conf, {'steps': [1]}, 3))
			self.assertIsNotNone(LivenessProbe('k2', {'conversation_id': _CID, 'steps': [1]}, 3, set(), {'k2': st_conf}, {_CID: 1}, require_empty=False, turn_reason_fn=jio.dfh_turn_state_orphan_reason).run())
			self.assertEqual(jc._resolve_dual_pair_names(jdir)[0], '\u227b')
			self.assertIsInstance(jres.dfh_reserved_step_ids(jdir), set)
			jr.dfh_matching_group_response(jdir, ['r1'], 'res 1')
			jr._check_overwritten_conflict([1], ['a'], ['b'], {}, ['r1'])
			jr._match_orphan_window([1], {1: jdir / '\u227b/1-20/1.md'}, {1: jdir / '\u227a/1-20/1.md'}, ['req 1'], 'res 1')
			self.assertIn('Checked 1 journal pairs', jio.dfh_validate_step_cli(Namespace(dir=jdir, all=False, step=1, strict_sequence=False, file=[])))
			(root / '\ua616/data/turns/rec_fail.json').write_text(json.dumps({'key': 'rf', 'conversation_id': _CID, 'native_reconciliation': {'valid': False, 'error': 'boom'}}), encoding='utf-8')
			with self.assertRaises(ValueError):
				jio._check_reconciliation_failures(root, {_CID})
			with self.assertRaises(ValueError):
				jio.dfh_validate_finalize_journal(root, jdir, {'requests': []})
			with self.assertRaises((FileNotFoundError, ValueError)):
				jr.dfh_recover_step(jdir, 1, 'bad-token')
	# @used-by :mod:`unittest`
	def test_journal_sync_and_upgrade(self) -> None:
		from Df.Harness.Journal.OpenTurnSyncer import OpenTurnSyncer
		from Df.Harness.lib import journal_integrity_ops as jio, journal_sync_ops as jso, journal_upgrade as ju
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/data/turns').mkdir(parents=True)
			db = root / 'ag/conversation_summaries.db'
			db.parent.mkdir()
			conn = sqlite3.connect(str(db))
			conn.execute('CREATE TABLE conversation_summaries (conversation_id TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER)')
			conn.execute('INSERT INTO conversation_summaries VALUES (?,?,?,?)', (_CID, 'CASCADE_RUN_STATUS_IDLE', 0, 0))
			conn.commit()
			conn.close()
			st_open = {'key': 'k1', 'conversation_id': _CID, 'platform': 'antigravity', 'native_backend': str(db.parent), 'status': 'prepared', 'prepared': {'journal_steps': [1]}, 'delivery': None, 'updated_at': '2026-11-27T00:00:00Z'}
			(root / '\ua616/data/turns/k1.json').write_text(json.dumps(st_open), encoding='utf-8')
			self.assertFalse(jio.dfh_is_conversation_running_live('k1', {'conversation_id': _CID}, {'k1': st_open}))
			read_fn = lambda p: json.loads(p.read_text(encoding='utf-8'))
			synced = OpenTurnSyncer(root, folder_fn=lambda r: r / '\ua616/data/turns', dir_fn=lambda r, _j: r / '\ua66e', read_fn=read_fn, sync_fn=lambda *_a, **_k: {'synced': True}).run()
			self.assertIn('synced', synced)
			jso.dfh_prune_resolved_from_index(root / '\ua616/data/turns', {'k1': {'conversation_id': _CID}}, {'k1'}, read_fn=read_fn, had_entries=True)
			jso._resolve_current_sync_journal(root, 'k1', None, folder_fn=lambda r: r / '\ua616/data/turns', dir_fn=lambda r, _j: r / '\ua66e', read_fn=read_fn)
			src_s, dst_s = (root / 'old_s', root / 'new_s')
			(src_s / 'answer-groups').mkdir(parents=True)
			(src_s / 'answer-groups/a.json').write_text('{}', encoding='utf-8')
			ju._merge_state_subdirs(src_s, dst_s)
			self.assertTrue((dst_s / 'answer-groups/a.json').is_file())
	# @used-by :mod:`unittest`
	def test_paths_and_uri(self) -> None:
		from Df.Harness.Path.CacheStore import CacheStore
		from Df.Harness.Path.PathReporter import PathReporter
		from Df.Harness.Path.SimilarProjectAuditor import SimilarProjectAuditor
		from Df.Harness.lib import path_discovery as pd, path_resolve as pr, uri as u
		self.assertEqual(u.dfh_extract_resource_uri({'folderUri': 'file:///C:/a/b.txt'}), 'file:///C:/a/b.txt')
		self.assertIsNotNone(u.dfh_local_uri_to_path('file:///C:/work/test.md'))
		self.assertEqual(u._strip_win_extended_prefix('\\\\?\\C:\\a'), 'C:\\a')
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			p1, p2 = (root / 'p1', root / 'p2')
			for d in (p1, p2):
				(d / '\ua616/data').mkdir(parents=True)
			(p1 / '\ua616/paths.json').write_text(json.dumps({'similar_projects': [str(p2)]}), encoding='utf-8')
			f1 = p1 / 'code.py'
			f1.write_text('x = 1\n', encoding='utf-8')
			pp = pr.dfh_project_paths(p1, exact_root=True)
			self.assertIn('project_root', pp.to_dict())
			self.assertEqual(pp.var('MISSING_VAR_XYZ', 'def'), 'def')
			self.assertTrue(str(pp.executors_json).endswith('.json'))
			self.assertTrue(str(pp.worktrees_dir).endswith('worktrees'))
			self.assertIn(p1.as_posix(), pp.expand('${PROJECT_ROOT}'))
			self.assertIn('expanded', PathReporter(p1, expand='${PROJECT_ROOT}', check=True).run())
			self.assertIn('expanded', PathReporter(None, expand='${HARNESS_CODE}', check=False).run())
			self.assertTrue(SimilarProjectAuditor([f1]).run())
			pdir = root / 'ag_projects'
			pdir.mkdir()
			(pdir / 'p1.json').write_text(json.dumps({'root_path': str(p1)}), encoding='utf-8')
			self.assertIsInstance(pd.dfh_is_registered_single_project(p1, registry=pr.dfh_load_registry(), projects_dirs=(pdir,)), bool)
			self.assertIsInstance(pd._runtime_ag_projects_dirs(), list)
			self.assertEqual(pd._match_journal_fallback([(0, p1)], pr.dfh_load_registry(), '\ua66e'), (None, None))
			(root / 'meta.json').write_text(json.dumps({'canonical_primary': str(p1)}), encoding='utf-8')
			cs = CacheStore(root / 'cache.json')
			self.assertEqual(cs._CacheStore__snapshot_canonical_primary(root / 'meta.json'), p1.resolve())
if '__main__' == __name__:
	unittest.main()
