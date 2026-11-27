# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import re
import sqlite3
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
_CID = '33333333-4444-5555-6666-777777777777'
_SUB = '44444444-5555-6666-7777-888888888888'
# 2026-11-27 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :mod:`unittest`
class DfHarnessS11Wave2dPlatformCovTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_ag_and_codex_registrars_verifiers_and_title_sync(self) -> None:
		from Df.Harness.Platform.Antigravity.ProjectRegistrar import ProjectRegistrar as AgReg
		from Df.Harness.Platform.Antigravity.ProofVerifier import ProofVerifier as AgPV
		from Df.Harness.Platform.Antigravity.TitleSyncer import TitleSyncer
		from Df.Harness.Platform.Codex.ProjectRegistrar import ProjectRegistrar as CxReg
		from Df.Harness.Platform.Codex.ProofVerifier import ProofVerifier as CxPV
		from Df.Harness.lib import ag_daemon as agd, ag_metadata as agm, codex_control as cxc
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/data').mkdir(parents=True)
			cx_home = root / 'cx'
			(cx_home / 'sessions').mkdir(parents=True)
			t_log = cx_home / 'sessions/rev.jsonl'
			t_log.write_text('{}\n', encoding='utf-8')
			obs, req = ({'model': None, 'effort': None, 'generation_model': 'm1'}, {'model': 'm1', 'effort': 'high'})
			agm.dfh_apply_requested_config(req, obs, 'Claude Opus 4.6 (High)', 'exact', 's1')
			self.assertEqual(req['selection'], 'exact')
			self.assertIsNotNone(agd.dfh_default_folders_json(settings_fn=lambda: {'platforms': {'antigravity': {'folders_json': str(root / 'folders.json'), 'instances': {}}}}))
			res_c = cxc.dfh_shared_control({'action': 'ping'}, platform_settings_fn=lambda _p: {'node': 'node', 'ui_manage': str(root / 'ui.py')}, run_fn=lambda *_a, **_k: type('R', (), {'returncode': 0, 'stdout': '{"ok": true}', 'stderr': ''})())
			self.assertTrue(res_c['ok'])
			p_ag = {'parent_id': 'p1', 'reviewer_id': _CID, 'surface': 'antigravity-ui', 'native_log': str(t_log), 'project_id': 'p1', 'project_kind': 'upwork', 'final_response_sha256': 'x', 'authored_response': 'missing.txt', 'final_step': 1, 'native_log_sha256': 'h', 'parent_log': str(t_log), 'agent_name': 'a'}
			self.assertIsInstance(AgPV(root, p_ag, _ops={'proof_paths': lambda _n: {'backend_dir': root, 'brain_dir': root, 'instance': 'A0'}, 'native_review_proof': lambda *_a, **_k: p_ag}).run(), dict)
			p_cx = {**p_ag, 'surface': 'codex-ui', 'native_profile_home': str(cx_home)}
			cx_cfg = {'platforms': {'codex': {'adapter': 'codex', 'instances': {'C1': {'enabled': True, 'home': str(cx_home)}}}}}
			self.assertIsInstance(CxPV(root, p_cx, _ops={'settings': lambda: cx_cfg, 'platform_settings': lambda _p: cx_cfg['platforms']['codex'], 'native_review_proof': lambda *_a, **_k: p_cx}).run(), dict)
			with patch('Df.Harness.Platform.Codex.ProjectRegistrar.validate_registration', lambda *_a: {'ok': True}), patch('Df.Harness.Platform.Codex.ProjectRegistrar.time.sleep', lambda _s: None):
				calls = [{'complete': False, 'shared_id': 's1', 'accounts': {'C1': {'state': 'connecting'}}}, {'complete': True, 'shared_id': 's1', 'accounts': {'C1': {'state': 'ready'}}}]
				self.assertTrue(CxReg(root, 'demo.com', '2026-11-27', _ops={'registration_profile_name': lambda: 'C1', 'shared_control': lambda _r: calls.pop(0), 'settings': lambda: cx_cfg}).run()['ok'])
			ts = TitleSyncer(_CID, 'My Title', backend=root / 'ag')
			with patch('urllib.request.urlopen', side_effect=OSError('offline')):
				self.assertIsInstance(ts._TitleSyncer__post_endpoints({'csrf_token': 't', 'https_port': 443, 'http_port': 80}, _CID, 'My Title', None, None), dict)
			fj = root / 'folders.json'
			fj.write_text('{"folders":[],"projectFolderMap":{}}\n', encoding='utf-8')
			(root / 'ag_p0').mkdir()
			(root / 'ag_p1').mkdir()
			ag_cfg = {'platforms': {'antigravity': {'adapter': 'antigravity', 'instances': {'A0': {'enabled': True, 'primary': True, 'system_paths': {'projects_dir': str(root / 'ag_p0'), 'folders_json': str(fj)}}, 'A1': {'enabled': True, 'system_paths': {'projects_dir': str(root / 'ag_p1'), 'folders_json': str(fj)}}}}}}
			self.assertIn('instances', AgReg(root, 'demo.com', '2026-11-27', multi_instance=True, _ops={'settings': lambda: ag_cfg}).run())
	# @used-by :mod:`unittest`
	def test_codex_and_ag_scanners_and_tool_trace(self) -> None:
		from Df.Harness.Platform.Antigravity.ToolTraceReader import ToolTraceReader
		from Df.Harness.Platform.Codex.TokenSummarizer import TokenSummarizer
		from Df.Harness.Platform.Codex.TurnScanner import TurnScanner as CxScanner
		from Df.Harness.lib import ag_metadata as agm
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			roll = root / 'rollout.jsonl'
			roll.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': _CID}}) + '\n' + json.dumps({'type': 'token_usage_record', 'payload': {'turn_id': 't1', 'response_id': 'r1', 'usage': {'input_tokens': 5, 'cached_input_tokens': 1, 'output_tokens': 2}}}) + '\n', encoding='utf-8')
			self.assertEqual(TokenSummarizer([str(roll)]).run()['generations'], 1)
			ag_be = root / 'ag_be'
			(ag_be / f'brain/{_CID}/.system_generated/logs').mkdir(parents=True)
			(ag_be / 'conversations').mkdir(parents=True)
			conn = sqlite3.connect(str(ag_be / f'conversations/{_CID}.db'))
			conn.execute('CREATE TABLE steps (idx INTEGER, status INTEGER)')
			conn.execute('INSERT INTO steps VALUES (2, 3)')
			conn.commit()
			conn.close()
			ag_log = ag_be / f'brain/{_CID}/.system_generated/logs/transcript_full.jsonl'
			ag_log.write_text(json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': 'a'}}]}) + '\n' + json.dumps({'step_index': 2, 'type': 'GENERIC', 'content': 'ok'}) + '\n', encoding='utf-8')
			ttr = ToolTraceReader(root, {'conversation_id': _CID, 'native_profile_home': str(root / 'ag_home'), 'step_indices': [1]}, _ops={'settings': lambda: {'platforms': {'antigravity': {'adapter': 'antigravity', 'instances': {'A0': {'enabled': True, 'home': str(root / 'ag_home'), 'system_paths': {'backend_dir': str(ag_be), 'brain_dir': str(ag_be / 'brain'), 'conversations_dir': str(ag_be / 'conversations')}}}}}}}).run()
			self.assertEqual(len(ttr['events']), 1)
			with patch('Df.Harness.lib.ag_metadata.dfh_default_platform_paths', return_value={'backend_dir': str(ag_be), 'brain_dir': str(ag_be / 'brain')}):
				self.assertIsInstance(agm.dfh_proof_paths({'native_log': str(ag_log), 'reviewer_id': _CID}, settings_fn=lambda: {'platforms': {'antigravity': {'instances': {}}}}), dict)
			cx_home = root / 'cx_home'
			sdir = cx_home / 'sessions/2026/11/27'
			sdir.mkdir(parents=True)
			p_roll, s_roll = (sdir / f'rollout-2026-11-27-{_CID}.jsonl', sdir / f'rollout-2026-11-27-{_SUB}.jsonl')
			p_rows = [{'type': 'session_meta', 'payload': {'id': _CID, 'cwd': str(root)}}, {'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': 't1'}}, {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': f'Work in {root.as_posix()}'}]}}, {'type': 'response_item', 'payload': {'type': 'function_call', 'call_id': 'c1', 'name': 'spawn_agent', 'arguments': json.dumps({'role': 'af'})}}, {'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'c1', 'output': json.dumps({'agent_id': _SUB})}}, {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'final_answer', 'content': [{'type': 'output_text', 'text': 'Done'}]}}, {'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': 't1', 'last_agent_message': 'Done'}}]
			s_rows = [{'type': 'session_meta', 'payload': {'id': _SUB, 'source': {'subagent': {'thread_spawn': {'parent_thread_id': _CID}}}}}, {'type': 'response_item', 'payload': {'type': 'function_call', 'call_id': 'sc1', 'name': 'exec_command', 'arguments': json.dumps({'cmd': 'echo sub'})}}, {'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'sc1', 'output': 'sub'}}]
			p_roll.write_text('\n'.join((json.dumps(r) for r in p_rows)) + '\n', encoding='utf-8')
			s_roll.write_text('\n'.join((json.dumps(r) for r in s_rows)) + '\n', encoding='utf-8')
			cdb = sqlite3.connect(str(cx_home / 'state_5.sqlite'))
			cdb.execute('CREATE TABLE threads (id TEXT, rollout_path TEXT, source TEXT, cwd TEXT, updated_at INTEGER, created_at INTEGER)')
			cdb.execute('INSERT INTO threads VALUES (?,?,?,?,?,?)', (_CID, str(p_roll), 'cli', str(root), 100, 100))
			cdb.execute('INSERT INTO threads VALUES (?,?,?,?,?,?)', (_SUB, str(s_roll), json.dumps({'subagent': {'thread_spawn': {'parent_thread_id': _CID}}}), str(root), 101, 101))
			cdb.commit()
			cdb.close()
			self.assertEqual(len(CxScanner(root, _CID, backend=cx_home).scan()['turns']), 1)
	# @used-by :mod:`unittest`
	def test_trace_effects_review_and_clarifications(self) -> None:
		from Df.Harness.lib import ag_daemon as agd, ag_inputs as agi, ag_review_wait as agrw, ag_wire as agw, clarifications_ops as clop, codex_trace as cxt, proof_metadata as pm, request_binding as rb, trace_effects as te, trace_review as tr
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/KB/Evidence/Reviews').mkdir(parents=True)
			acc = te.dfh_init_turn_accumulator()
			te.dfh_record_normalized_tool_effects(root, 1, 'run_command', {'CommandLine': 'git status'}, 'git status', acc, track_turn_steps=True, cmd_outputs=['ok'])
			te.dfh_record_normalized_tool_effects(root, 2, 'write_file', {'Path': str(root / '\ua616/KB/note.md'), 'Content': 'x'}, 'write', acc, track_turn_steps=True)
			te.dfh_record_normalized_tool_effects(root, 3, 'spawn_agent', {'role': 'af'}, '{"role": "af"}', acc, track_turn_steps=True)
			self.assertTrue(acc['exec5_violations'])
			self.assertEqual(te.dfh_summarize_token_records([('gen', 'o', 1, {'input_tokens': 10, 'cache_read_tokens': 2, 'output_tokens': 5}), ('duplicate',)], tools={'read_file': 1})['generations'], 1)
			seg = [{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-27T00:00:00Z', 'tool_calls': [{'name': 'ask_question', 'args': {'questions': [{'question': 'Q?'}]}}]}, {'step_index': 2, 'type': 'GENERIC', 'content': 'Created At: 2026-11-27T00:00:00Z\nCompleted At: 2026-11-27T00:00:05Z\nA1: Yes\nmore'}]
			self.assertEqual(len(clop.dfh_extract_ask_question_clarifications(seg)), 1)
			cand_f = root / '\ua616/data/scratch/answer.md'
			cand_f.parent.mkdir(parents=True, exist_ok=True)
			cand_f.write_text('l1\nl2\nl3\n', encoding='utf-8')
			self.assertTrue(tr.dfh_partial_candidate_read_issues(root, [{'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': str(cand_f), 'StartLine': 1, 'EndLine': 1}}]}, {'type': 'GENERIC', 'content': 'Total Lines: 3'}]))
			self.assertEqual(tr._merge_line_intervals([(1, 2), (2, 4), (6, 7)]), [[1, 4], [6, 7]])
			self.assertIsInstance(agd.dfh_is_live_language_server_pid(0), bool)
			self.assertEqual(agd.dfh_parse_pbtxt_title('title: "My Title"\n'), 'My Title')
			self.assertIsNone(agd._parse_daemon_file(root / 'missing.json', lambda _p: False))
			self.assertIsNone(agw.dfh_extract_step_text(b''))
			self.assertIsInstance(agw.dfh_generation_matches_executor('m1', 'm1'), bool)
			self.assertIsInstance(agi._uuids_from_generic_text(_CID, re.compile(r'[a-f0-9-]{36}')), list)
			self.assertIsInstance(cxt.dfh_extract_codex_spawn_output_uuids(_CID), list)
			self.assertIsInstance(cxt.dfh_extract_codex_target_subagents({'agent_id': _CID}), list)
			self.assertIsInstance(rb.dfh_explicit('https://www.upwork.com/jobs/~12345678901', '~12345678901'), tuple)
			proof_f = root / '\ua616/KB/Evidence/Reviews/p.json'
			p_obj = {'project_id': 'p1', 'project_kind': 'upwork', 'executor_metadata': {'requested': {'model': 'm'}, 'observed': {'model': 'm'}, 'observation_history': [{'model': 'm'}]}, 'final_response_sha256': 'x', 'authored_response': 'missing.txt'}
			proof_f.write_text(json.dumps(p_obj), encoding='utf-8')
			self.assertIsNotNone(pm.dfh_reuse_equivalent_proof(proof_f, p_obj))
			self.assertEqual(tr.dfh_verify_review_proof_core(root, p_obj, p_obj, ('project_id',)), p_obj)
			t_log = root / 'rev.jsonl'
			t_log.write_text(json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'Check pkg.json'}) + '\n', encoding='utf-8')
			self.assertTrue(agrw.dfh_reviewer_assigned_package(t_log, 'pkg.json'))
			self.assertFalse(agrw._is_reviewer_in_flight(root / 'missing.db', _CID))
if '__main__' == __name__:
	unittest.main()
