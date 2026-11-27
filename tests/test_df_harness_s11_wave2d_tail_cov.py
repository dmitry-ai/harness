# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from argparse import Namespace
from copy import copy
from pathlib import Path
from unittest.mock import patch
import json
import os
import sqlite3
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
_CID = '44444444-5555-6666-7777-888888888888'
_SUB = '99999999-aaaa-bbbb-cccc-dddddddddddd'
# 2026-11-27 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :mod:`unittest`
class DfHarnessS11Wave2dTailCovTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_codex_roles_and_proof_metadata_tail(self) -> None:
		from Df.Harness.lib import native_codex_roles as ncr, native_links as nl, proof_metadata as pm
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			primary = root / 'harness/code'
			(root / 'harness/_').mkdir(parents=True)
			cfg_p = root / 'config.toml'
			defs = {'worker': {'config_file': 'w.toml', 'description': 'd'}}
			orig = 'model = "m"\n'
			orig_b = orig.encode('utf-8')
			gen = ncr.dfh_legacy_role_config(orig, defs)
			bk_file = nl.dfh_data_dir_for(primary) / 'native-profiles/backups/b1/orig.bin'
			bk_file.parent.mkdir(parents=True, exist_ok=True)
			bk_file.write_bytes(orig_b)
			state = {'backups': {f'{cfg_p}:{nl.dfh_hash(orig_b)}': str(bk_file)}}
			stripped = ncr.dfh_role_config(gen, defs, {'files': {str(cfg_p): nl.dfh_hash(gen.encode('utf-8'))}}, state, cfg_p, primary)
			self.assertEqual(stripped.strip(), orig.strip())
			saved_m = {'platform': 'codex', 'observed': {'model': 'm1'}, 'requested': {'model': 'm1'}, 'metadata_sources': [{'k': 'a'}], 'observation_history': {'m': [{'value': 'm1'}]}}
			live_m = {'platform': 'codex', 'observed': {'model': 'm1', 'generation_model': 'g1'}, 'requested': {'model': 'm1', 'x': 1}, 'metadata_sources': [{'k': 'a'}, {'k': 'b'}], 'observation_history': {'m': [{'value': 'm1'}, {'value': 'm1'}]}}
			self.assertTrue(pm.dfh_executor_metadata_equivalent(saved_m, live_m, allow_legacy_generation_model=True))
	# @used-by :mod:`unittest`
	def test_completion_tail(self) -> None:
		from Df.Harness.Completion.AnswerPreparer import AnswerPreparer
		from Df.Harness.Completion.JournalReconciler import JournalReconciler
		from Df.Harness.lib import completion_commands as cc
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/data/turns').mkdir(parents=True)
			(root / '\ua616/data/scratch').mkdir(parents=True)
			resp_f = root / '\ua616/data/scratch/r.md'
			resp_f.write_text('body\n', encoding='utf-8')
			st_p = root / '\ua616/data/turns/k1.json'
			ap = AnswerPreparer(root, 'body\n', {}, {'conversation_id': _CID, 'platform': 'antigravity'}, {'start_step': 0, 'requests': []}, _ops={'state': lambda *_a: (st_p, {'key': 'k1'})})
			ap.wf_identifiers, ap.allow_reprepare = ({'r1'}, True)
			wf_st = {'requests': [{'id': 'r1'}]}
			with patch('agent_tools.workflow.update', lambda _r, _m, fn: fn(wf_st)), patch.object(ap, '_record_journal_entry'):
				ap._AnswerPreparer__post_finalize_workflow(lambda: '2026-11-27T00:00:00Z')
			self.assertEqual(wf_st['requests'][0]['response_prepared']['sha256'], ap.sha)
			cf = root / 'conflict.json'
			cf.write_text('{}', encoding='utf-8')
			jr_obj = JournalReconciler(root, _CID, preloaded_native={'conversation_id': _CID, 'turns': []})
			jr_obj._JournalReconciler__cleanup_adopted_conflict({'admission_failure': {'g': 1}, 'delivery': {'conflict_evidence': str(cf)}})
			self.assertFalse(cf.exists())
			self.assertIn('exec5_check', cc._child_check_value(root, {'platform': 'antigravity', 'conversation_id': _CID}, 'k1', {'start_step': 0}, {}))
			ns_chk = Namespace(command='answer-check', project=str(root), response_file=str(resp_f), conversation=_CID, journal=None, consume_input=False, blocked_report=False)
			self.assertTrue(cc._execute_prepare_or_check(ns_chk, {'check_answer': lambda *_a, **_k: {'valid': True}})['valid'])
			ns_prp = Namespace(command='answer-prepare', project=str(root), response_file=str(resp_f), conversation=_CID, journal=None, no_watch=True, wait_timeout=1.0, consume_input=False, blocked_report=False)
			self.assertTrue(cc._execute_prepare_or_check(ns_prp, {'prepare': lambda *_a, **_k: {'valid': True}})['valid'])
			self.assertTrue(cc.dfh_reconcile_unprepared_delivery(root, _CID, ops={'sync': lambda *_a, **kw: {'adopt': kw['adopt_conflict']}})['adopt'])
	# @used-by :mod:`unittest`
	def test_hook_emergency_and_path_tail(self) -> None:
		from Df.Harness.Path.SimilarProjectAuditor import SimilarProjectAuditor
		from Df.Harness.lib import hook_stop_ops as hso, path_resolve as pr
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			p1, p2 = (root / 'p1', root / 'p2')
			for d in (p1, p2):
				(d / '\ua616/data/turns').mkdir(parents=True)
			nat = {'conversation_id': _CID, 'platform': 'antigravity', 'native_backend': str(root / 'ag'), 'backend': str(root / 'ag'), 'source_file': str(root / 'tx.jsonl')}
			trn = {'turn_id': 't0', 'start_step': 0, 'requests': [{'id': 'r1', 'native_step': 0, 'text': 'hello'}]}
			em = hso.dfh_record_emergency_locked(p1, nat, trn, 'Emergency answer.\n', 'timeout')
			self.assertTrue(em and em['captured'])
			pp = pr.dfh_project_paths(p1, exact_root=True)
			self.assertEqual(pp._direct_similar_projects, pp.direct_similar_projects)
			with self.assertRaises(AttributeError):
				_ = pp.no_such_attr_xyz
			f1 = p1 / 'a.py'
			f1.write_text('x = 1\n', encoding='utf-8')
			reg = copy(pr.dfh_load_registry())
			reg.similar_project_groups = ({'id': 'g1', 'members': ({'project': str(p1), 'affiliated_paths': ()}, {'project': str(p2), 'affiliated_paths': ()})},)
			self.assertTrue(SimilarProjectAuditor([f1], registry=reg).run())
	# @used-by :mod:`unittest`
	def test_journal_tail(self) -> None:
		from Df.Harness.Journal.Publisher import Publisher
		from Df.Harness.lib import journal_core as jc, journal_records as jr, journal_sync_ops as jso
		from Df.Harness.lib.admission_ops import dfh_admission_binding, dfh_capture_admission
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			jdir = root / '\ua66e'
			(root / '\ua616/data/turns').mkdir(parents=True)
			cap1 = dfh_capture_admission([root, jdir], ['req 1'], 'resp 1', dfh_admission_binding(jdir, ['req 1'], 'resp 1', 'tok1', ['r1']))
			self.assertEqual(Publisher(jdir, ['req 1'], 'resp 1', 'tok1', ['r1'], admission=cap1).run(), [1])
			cap2 = dfh_capture_admission([root, jdir], ['req 1'], 'resp 2', dfh_admission_binding(jdir, ['req 1'], 'resp 2', 'tok1', ['r1']))
			self.assertEqual(Publisher(jdir, ['req 1'], 'resp 2', 'tok1', ['r1'], admission=cap2, allow_reprepare=True).run(), [1])
			req_d, res_d = jc.dfh_journal_pair_dirs(jdir)
			self.assertFalse(jr._check_group_files(jdir, req_d, res_d, {'steps': [1], 'requests': ['other'], 'response_sha256': '0'}, {'r1'}))
			j2 = root / 'j2'
			jr.dfh_record_step(j2, 'req o', 'res o')
			rq2, rs2 = jc.dfh_journal_pair_dirs(j2)
			self.assertEqual(jr._scan_orphan_candidates(j2, rq2, rs2, ['req o'], 'res o', ['r1'])[0], [1])
			self.assertGreater(jso.dfh_candidate_recency(root / '\ua616/data/turns', 'k1', {'updated_at': '2026-11-27T00:00:00Z'}), 0.0)
			self.assertEqual(jso._parse_iso_epoch('bad'), 0.0)
	# @used-by :mod:`unittest`
	def test_narrow_reconciler_trim_tail(self) -> None:
		from Df.Harness.Completion.NarrowReconciler import NarrowReconciler
		from Df.Harness.lib.journal_reservations import dfh_reserve_turn_steps
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			jdir = root / '\ua66e'
			dfh_reserve_turn_steps(jdir, 'k1', _CID, ['r1', 'r2'])
			nat = {'conversation_id': _CID, 'turns': [{'turn_id': 't0', 'requests': [{'id': 'r1'}]}, {'turn_id': 't1', 'requests': [{'id': 'r2'}]}]}
			val = {'key': 'k1', 'status': 'open', 'journal': str(jdir), 'reserved_journal_steps': [1, 2], 'requests': [{'id': 'r1'}, {'id': 'r2'}]}
			nr = NarrowReconciler(root, nat, {'turn_id': 't0', 'requests': [{'id': 'r1'}]}, val, recovered=True, same_req_fn=lambda a, b, _r: a['id'] == b['id'], journal_dir_fn=lambda _r, _j: jdir)
			self.assertEqual(nr.run(), [{'id': 'r1'}])
			self.assertEqual(val['reserved_journal_steps'], [1])
	# @used-by :mod:`unittest`
	def test_platform_turn_scanner_and_ag_tail(self) -> None:
		from Df.Harness.Platform.Antigravity.TurnScanner import TurnScanner
		from Df.Harness.lib import ag_daemon as agd, ag_wire as agw
		self.assertFalse(agd._check_win32_ls_pid(os.getpid()))
		self.assertEqual(agw._decode_media_lines([(9, 2, b'*\x13file:///tmp/img.png')]), '[Image: file:///tmp/img.png]')
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			ag = root / 'ag'
			main_logs = ag / f'brain/{_CID}/.system_generated/logs'
			sub_logs = ag / f'brain/{_SUB}/.system_generated/logs'
			main_logs.mkdir(parents=True)
			sub_logs.mkdir(parents=True)
			(ag / 'conversations').mkdir(parents=True)
			sconn = sqlite3.connect(str(ag / 'conversation_summaries.db'))
			sconn.execute('CREATE TABLE conversation_summaries (conversation_id TEXT, parent_conversation_id TEXT, title TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_modified_time TEXT, workspace_uris TEXT)')
			sconn.execute('INSERT INTO conversation_summaries VALUES (?,?,?,?,?,?,?,?)', (_CID, '', 'T', 'IDLE', 0, 0, '2026-11-27T00:00:00Z', json.dumps([root.as_uri()])))
			sconn.commit()
			sconn.close()
			cconn = sqlite3.connect(str(ag / f'conversations/{_CID}.db'))
			cconn.execute('CREATE TABLE steps (idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
			cconn.execute('INSERT INTO steps VALUES (0, 14, 3, 0, ?)', (b'\x9a\x01\x0c\x12\nhello user',))
			cconn.commit()
			cconn.close()
			sub_rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'go'}, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'echo sub'}}]}, {'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 0.'}]
			(sub_logs / 'transcript.jsonl').write_text('\n'.join((json.dumps(r) for r in sub_rows)) + '\n', encoding='utf-8')
			main_rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'hello user'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'invoke_subagent', 'args': {'Role': 'W'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': json.dumps({'conversationId': _SUB}) + ' file:///C:/work/.system_generated/steps/1/output.txt'},
				{'step_index': 3, 'type': 'EPHEMERAL_MESSAGE', 'content': f'<SYSTEM_MESSAGE>[Message] timestamp=2026-11-27T00:00:00Z sender={_SUB} content=done</SYSTEM_MESSAGE>'},
			]
			(main_logs / 'transcript.jsonl').write_text('\n'.join((json.dumps(r) for r in main_rows)) + '\n', encoding='utf-8')
			scan = TurnScanner(root, _CID, backend=ag).scan()
			self.assertIn('delegation', scan['turns'][0])
	# @used-by :mod:`unittest`
	def test_runtime_tail(self) -> None:
		from Df.Harness.lib import runtime_context as rctx, runtime_conversations as rconv, runtime_resolve as rres
		self.assertIsInstance(rctx._default_settings(), dict)
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			ag = root / 'ag'
			(ag / f'brain/{_CID}/.system_generated/logs').mkdir(parents=True)
			ch = root / 'cx_home'
			sess = ch / f'sessions/2026/11/27/rollout-{_CID}.jsonl'
			sess.parent.mkdir(parents=True)
			sess.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': _CID, 'cwd': str(root)}}) + '\n', encoding='utf-8')
			with patch.dict(os.environ, {'CODEX_HOME': str(ch)}):
				self.assertEqual(rctx._resolve_profile_from_codex_home({'C1': str(ch)}), 'C1')
			self.assertEqual(rctx._resolve_registration_default({'instances': {'C1': {'enabled': True, 'default_registration': True, 'home': str(ch)}}}, 'codex'), 'C1')
			found = rconv._find_codex_conversation('codex', 'C1', {'enabled': True, 'system_paths': {'home': str(ch), 'sessions_dir': str(ch / 'sessions')}}, _CID)
			self.assertIsNotNone(found)
			m1 = {'id': 'A0', 'system_paths': {'brain_dir': str(ag / 'brain'), 'conversations_dir': str(ag / 'conversations')}}
			m2 = {'id': 'A1', 'system_paths': {'brain_dir': str(root / 'other/brain'), 'conversations_dir': str(root / 'other/conversations')}}
			self.assertEqual(rres._disambiguate_ag_matches([m1, m2], ag, _CID)['id'], 'A0')
			with patch.dict(os.environ, {'CODEX_HOME': ''}):
				resolved = rres._resolve_codex_home_by_conv_or_profile({'C1': str(ch)}, 'codex', {}, _CID, lambda: {}, lambda *_a, **_k: [{'id': 'C1', 'backend_dir': str(ch)}])
			self.assertEqual(resolved, ch.resolve())
	# @used-by :mod:`unittest`
	def test_shadow_tail(self) -> None:
		from Df.Harness.Shadow.ReplayPipeline import ReplayPipeline
		from Df.Harness.Shadow.ReplayRunner import ReplayRunner
		from Df.Harness.lib import journal_records as jr, shadow_clone as scl, shadow_command as scmd
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			src, dst = (root / 'src.txt', root / 'dst.txt')
			src.write_text('hi', encoding='utf-8')
			scl._copy_file(src, dst, hardlink=True)
			scl._copy_file(src, root / 'dst2.txt', hardlink=False)
			self.assertTrue(dst.is_file())
			prof = root / 'prof.json'
			prof.write_text(json.dumps({'p': str(root / 'old')}), encoding='utf-8')
			scmd._copy_native_profile(prof, root / 'out/prof.json', [(str(root / 'old'), str(root / 'new'))])
			self.assertIn('new', (root / 'out/prof.json').read_text(encoding='utf-8'))
			proj = root / 'proj'
			(proj / '\ua616/data/turns').mkdir(parents=True)
			(proj / '\ua616/project.json').write_text(json.dumps({'id': 'p1'}), encoding='utf-8')
			jr.dfh_record_step(proj / '\ua66e', 'q', 'a')
			self.assertIsNone(scmd.dfh_resolve_shadow_launcher(proj, None))
			checks, verified, errors = ({}, [], [])
			rp = ReplayPipeline(proj, None, root, _CID, 'antigravity', root / 'ag', None, None, checks, verified, errors)
			reply_p = rp._ReplayPipeline__find_reply_path()
			self.assertIsNotNone(reply_p)
			with patch('agent_tools.workflow.complete_stage', return_value={'stages': {'finalize': {'status': 'complete'}}}):
				rp._ReplayPipeline__execute_finalize_reply(reply_p)
			self.assertIn('stage_finalize', verified)
			ag = root / 'ag'
			logs = ag / f'brain/{_CID}/.system_generated/logs'
			logs.mkdir(parents=True)
			(logs / 'transcript.jsonl').write_text('{}\n', encoding='utf-8')
			rr = ReplayRunner(proj, _CID, backend=ag)
			with patch('Df.Harness.Shadow.ReplayRunner.dfh_resolve_antigravity_paths', return_value={'backend_dir': str(ag), 'brain_dir': str(ag / 'brain')}), patch('Df.Harness.Shadow.ReplayRunner.ReplayPipeline.run'):
				rr._ReplayRunner__run_shadow_mode(proj, None, None, root, {}, [], [])
if '__main__' == __name__:
	unittest.main()
