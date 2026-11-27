# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
import json
import sqlite3
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
_CID = '22222222-3333-4444-5555-666666666666'
# 2026-11-27 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :mod:`unittest`
class DfHarnessS11Wave2dCompletionCovTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_blocked_report_and_workflow_sync_ops(self) -> None:
		from Df.Harness.lib import blocked_report_ops as bro
		from Df.Harness.lib.path_resolve import dfh_project_paths
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/data').mkdir(parents=True)
			(root / '\ua616/project.json').write_text(json.dumps({'job_id': '~1111111111'}), encoding='utf-8')
			(root / '\ua616/data/workflow.json').write_text(json.dumps({'schema_version': 1, 'project_root': str(root), 'job_id': '~1111111111', 'stages': {'finalize': {'status': 'pending'}}, 'questions': {}, 'reviews': [], 'events': [], 'requests': [{'id': 'r1', 'native_conversation_id': _CID, 'response_prepared': {'sha256': 'old'}}]}), encoding='utf-8')
			pp = dfh_project_paths(root, exact_root=True)
			pp.continuation_md.write_text('Active blocker: waiting for external portal access before final report.', encoding='utf-8')
			self.assertEqual(bro.dfh_blocked_report_issues(pp, 'Blocked due to error.\n', workflow_exists=True, is_finalized=False), [])
			doc5 = '# 0\n"Issue": null\n# 1\nDesc\n# 2\nH-1\n# 3\nSrc\n# 4\nM-1\n'
			self.assertTrue(bro._is_doc5_blocker_analysis(doc5))
			self.assertTrue(bro.dfh_pending_workflow_alignment_issues({'requests': [{'id': 'r1', 'native_conversation_id': _CID, 'response_prepared': {'sha256': 'old'}}]}, _CID, {'r1'}, response_sha='new'))
			wf_errs = bro.dfh_evaluate_check_workflow_errors(root, pp, 'primary', 'H-1 claim\n', [{'id': 'r2', 'text': 'analyze'}], {'touched_files': []}, {'conversation_id': _CID}, {'aa_subagent_step_count': 0}, blocked_report=False, journal_directory=None, factual_kb_fn=lambda _r, _t: {'issues': [], 'has_normative': False, 'has_analysis': False}, is_deliv_fn=lambda _p, _r: False, dir_fn=lambda r, _j: r / '\ua66e')
			self.assertTrue(wf_errs)
			fails: list[tuple[str, str]] = []
			rec_called = []
			runner = Namespace(root=root, native={'conversation_id': _CID}, wf_state={'requests': [{'id': 'r1', 'native_conversation_id': _CID, 'response_prepared': {'sha256': 'old'}}]}, wf_identifiers={'r1'}, sha='new', allow_reprepare=True, value={'journal': str(root / '\ua66e'), 'prepared': {'journal_steps': [1], 'group_file': str(root / 'g.json')}}, response='resp', _fail_gate=lambda g, d: fails.append((g, d)), _record_journal_entry=lambda: rec_called.append(True))
			with patch('agent_tools.workflow.update', lambda _r, _m, fn: fn(runner.wf_state)):
				bro.dfh_prepare_and_sync_authorized_workflow(runner, {'ok': True}, lambda: '2026-11-27T00:00:00Z')
				bro.dfh_record_blocked_report_entry(runner)
			self.assertTrue(rec_called)
			self.assertEqual(runner.value['completion_kind'], 'blocked_report')
	# @used-by :mod:`unittest`
	def test_child_trace_and_turn_routing(self) -> None:
		from Df.Harness.Completion.NarrowReconciler import NarrowReconciler
		from Df.Harness.lib import completion_child_trace as cct, turn_routing_ops as tro
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/data/turns').mkdir(parents=True)
			tx = root / 'child.jsonl'
			rows = [
				{'step_index': 0, 'type': 'CHECKPOINT'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'echo hi'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'file:///C:/work/.system_generated/steps/1/output.txt'},
				{'step_index': 3, 'type': 'response_item', 'payload': {'type': 'function_call', 'call_id': 'c1', 'name': 'exec_command', 'arguments': json.dumps({'cmd': 'python scripts/df_github_issue.py fetch 1'})}},
				{'step_index': 4, 'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'c1', 'output': 'ok'}},
			]
			tx.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			res = cct.dfh_scan_child_trace_turn(root, 'child-1', {'source_file': str(tx), 'turns': []})
			self.assertEqual(res['compaction']['checkpoint_steps'], [0])
			cdir = root / 'convs'
			cdir.mkdir()
			conn = sqlite3.connect(str(cdir / f'{_CID}.db'))
			conn.execute('CREATE TABLE steps (idx INTEGER, step_type INTEGER, step_payload BLOB)')
			conn.execute('INSERT INTO steps VALUES (0, 14, ?)', (b'\x9a\x01\x0c\x12\nhello user',))
			conn.commit()
			conn.close()
			self.assertIn('hello', tro._extract_step_text_from_db(cdir, _CID, 0) or '')
			st_a = {'conversation_id': _CID, 'start_step': 0, 'status': 'open', 'requests': [{'native_step': 0}]}
			self.assertGreater(tro._match_tier(st_a, _CID, 0), 0)
			self.assertIsInstance(tro._state_rank(st_a, 2), tuple)
			self.assertIsNotNone(tro._pick_higher(None, (1, 0, ''), st_a))
			self.assertIsNone(tro._handoff_rank(st_a, [], 0, None))
			nr = NarrowReconciler(root, {'conversation_id': _CID}, {'start_step': 0, 'requests': [{'id': 'r1'}]}, {'key': 'k', 'status': 'open', 'reserved_journal_steps': [1, 2], 'requests': [{'id': 'r1'}]}, recovered=False, same_req_fn=lambda _a, _b, _r: True, journal_dir_fn=lambda _r, _j: root / '\ua66e')
			self.assertIsInstance(nr.run(), list)
	# @used-by :mod:`unittest`
	def test_compaction_and_response_links(self) -> None:
		from Df.Harness.lib import completion_compaction as cc, completion_links as cl
		from Df.Harness.lib.path_resolve import dfh_project_paths
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/KB').mkdir(parents=True)
			(root / '\ua616/data/turns').mkdir(parents=True)
			(root / '\ua616/data/scratch').mkdir(parents=True)
			doc = root / 'doc.md'
			doc.write_text('# Heading\nLine 2\n', encoding='utf-8')
			jf = root / 'data.json'
			jf.write_text(json.dumps({'a': 1}), encoding='utf-8')
			(root / 'sub').mkdir()
			resp = 'See [ok](doc.md#heading), [ln](doc.md#L1-L2), [badln](doc.md#L99), [js](data.json#/a), [dir](sub#x), [miss](nope.md), [self](#missing), [url](https://bad host).\n'
			self.assertTrue(cl.dfh_response_link_issues(root, resp))
			self.assertTrue(cl._normalize_file_href_path('file:///C:/a/b.md', cl.urlsplit('file:///C:/a/b.md'), False).startswith('C:/'))
			src = root / '\ua616/KB/source.md'
			src.write_text('Source body\n', encoding='utf-8')
			pp = dfh_project_paths(root, exact_root=True)
			comp_turn = {'compaction': {'occurred': True, 'checkpoint_steps': [5], 'last_checkpoint_step': 5, 'pre_checkpoint_tool_steps': [1], 'pre_checkpoint_read_files': [str(src)], 'post_checkpoint_read_files': [], 'post_checkpoint_written_files': [], 'evicted_unreread_files': [str(src)], 'pre_checkpoint_records': [{'step': 1, 'tools': ['read_file'], 'outputs': ['out']}], 'recovered_in_trace': False}}
			st = cc.dfh_compaction_status(root, 'k1', comp_turn, folder_fn=lambda r: r / '\ua616/data/turns', read_fn=lambda p: json.loads(p.read_text(encoding='utf-8')), is_deliv_fn=lambda _p, _r: False)
			self.assertFalse(st['verified'])
			self.assertEqual(len(cc.dfh_find_evicted_cited_files(root, pp, 'k1', st, f'See [s]({src.as_posix()}).')), 1)
			idx_rel = cc.dfh_write_compaction_index_file(root, 'k1', comp_turn, st, folder_fn=lambda r: r / '\ua616/data/turns', now_fn=lambda: '2026-11-27T00:00:00Z', json_fn=lambda o: json.dumps(o).encode('utf-8'))
			self.assertIn('index.json', idx_rel)
	# @used-by :mod:`unittest`
	def test_completion_checks_and_admission_guard(self) -> None:
		from Df.Harness.Completion.AdmissionGuard import AdmissionGuard
		from Df.Harness.lib import completion_checks as cc, completion_core as ccore, completion_record as crec
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/KB/Notes').mkdir(parents=True)
			(root / '\ua616/data/turns').mkdir(parents=True)
			kb_note = root / '\ua616/KB/Notes/fact.md'
			kb_note.write_text('# Fact\nObserved value.\n', encoding='utf-8')
			self.assertIn('issues', cc.dfh_factual_kb_note_issues(root, {'touched_files': [str(kb_note)]}))
			self.assertIsInstance(cc.dfh_is_client_deliverable_path(str(root / 'draft.md'), root), bool)
			self.assertTrue(cc.dfh_gate_resolved(root, {'start_step': 0}, {'readiness_check': {'gate_id': 'tdd'}, 'tdd_check': {'verified': True}}))
			(root / '\ua616/project.json').write_text(json.dumps({'job_id': '~0211111111111111111'}), encoding='utf-8')
			(root / '\ua616/data/workflow.json').write_text(json.dumps({'schema_version': 1, 'project_root': str(root), 'job_id': '~0211111111111111111', 'stages': {}, 'questions': {}, 'reviews': [], 'events': [], 'requests': []}), encoding='utf-8')
			self.assertFalse(cc.dfh_workflow_gate_resolved(root, {'requests': [{'id': 'r1'}]}, 'workflow_adoption'))
			self.assertEqual(cc.dfh_violation_recovery(root, 'missing-key'), {})
			self.assertTrue(crec.dfh_matches_recorded_response({'response_sha256': 'abc'}, 'x', 'abc'))
			self.assertEqual(ccore.dfh_journal_dir(root), root / '\ua66e')
			with self.assertRaises(ValueError):
				AdmissionGuard('verify', paths=[root], requests=['r'], response='a', identity={}).run()
	# @used-by :mod:`unittest`
	def test_env_isolation_auditor_and_recovery_ops(self) -> None:
		from Df.Harness.Completion.EnvIsolationAuditor import EnvIsolationAuditor
		from Df.Harness.lib import completion_recovery as cr, env_isolation_ops as eio
		audit = EnvIsolationAuditor(WT_ROOT / 'tests', scripts_dir=WT_ROOT / 'scripts').run()
		self.assertIsInstance(audit, list)
		self.assertIn('FOO', eio.dfh_isolated_subprocess_env({'A': '1'}, FOO='bar'))
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			tdir = root / 'tests'
			tdir.mkdir()
			(tdir / 'test_sample.py').write_text('import os, subprocess, unittest\nfrom unittest.mock import patch\nclass T(unittest.TestCase):\n\tdef test_bad(self):\n\t\twith patch.dict("os.environ", {"CODEX_HOME": ""}):\n\t\t\tsubprocess.run(["harness.py", "problem-metadata"])\n', encoding='utf-8')
			self.assertTrue(eio.dfh_audit_metadata_test_env_isolation(tdir))
			proj, peer, launcher = (root / 'proj', root / 'peer', root / 'launcher')
			for d in (proj, peer, launcher):
				(d / '\ua616/data/turns').mkdir(parents=True)
			(proj / '\ua616/paths.json').write_text(json.dumps({'similar_projects': [str(peer)]}), encoding='utf-8')
			(launcher / '\ua616/data/turns/k0.json').write_text(json.dumps({'key': 'k0', 'conversation_id': _CID, 'status': 'open', 'requests': [{'id': 'r0', 'text': '/upwork-init https://www.upwork.com/jobs/~0212345678901234567'}]}), encoding='utf-8')
			self.assertEqual(len(cr.dfh_handoff_launcher_turn(launcher, proj, '~0212345678901234567', conversation_id=_CID)), 1)
			fake_nat = {'primary': True, 'platform': 'codex', 'conversation_id': _CID, 'native_backend': str(root), 'backend': str(root), 'active_turn_id': 't0', 'turns': [{'turn_id': 't0', 'start_step': 0, 'owned': True, 'aborted': False, 'requests': [{'id': 'r1', 'native_step': 0, 'text': 'hi'}], 'compaction': {'occurred': True, 'checkpoint_steps': [2], 'last_checkpoint_step': 2, 'pre_checkpoint_tool_steps': [1], 'pre_checkpoint_records': [{'step': 1, 'tools': ['read_file'], 'outputs': ['o']}]}}]}
			ops = {'native': lambda *_a, **_k: fake_nat, 'key': lambda _n, _t: 'k1', 'now': lambda: '2026-11-27T00:00:00Z'}
			self.assertTrue(cr.dfh_recover_checkpoint(proj, _CID, dry_run=True, ops=ops)['dry_run'])
			self.assertIn('recovery_file', cr.dfh_recover_checkpoint(proj, _CID, dry_run=False, ops=ops))
			self.assertIn('receipt_file', cr.dfh_ratchet_ok(proj, 'tests/test_a.py', 'Updated assertion for verified contract change in wave 2d', _CID, ops=ops))
			self.assertIn('valid', cr.dfh_issue_first_check_turn(proj, _CID, ops=ops))
			self.assertIn('valid', cr.dfh_tdd_check_turn(proj, _CID, ops=ops))
			self.assertIn('recovery_file', cr.dfh_recover_turn_violation(proj, _CID, reason='recovered', ops=ops))
			self.assertIn('journal', cr.dfh_sync_conversation_title(proj, _CID, ops=ops))
			self.assertIn('exemption_file', cr.dfh_similar_project_exempt(proj, str(peer), 'Verified peer repository does not share this refactored module', _CID, ops=ops))
if '__main__' == __name__:
	unittest.main()
