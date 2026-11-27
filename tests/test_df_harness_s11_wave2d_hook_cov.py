# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import io
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
_CID = '11111111-2222-3333-4444-555555555555'
_SUB_ID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
# 2026-11-27 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :mod:`unittest`
class DfHarnessS11Wave2dHookCovTests(unittest.TestCase):
	# @used-by :meth:`DfHarnessS11Wave2dHookCovTests.test_stop_gate_continuation_guard_and_emergency_capture()`
	# @used-by :meth:`DfHarnessS11Wave2dHookCovTests.test_subagent_checker_and_schedule_block()`
	def _make_summary_db(self, db_path: Path, rows: list[tuple[str, str, str, int, int, str]]) -> None:
		db_path.parent.mkdir(parents=True, exist_ok=True)
		conn = sqlite3.connect(str(db_path))
		conn.execute('CREATE TABLE conversation_summaries (conversation_id TEXT, parent_conversation_id TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_modified_time TEXT)')
		conn.executemany('INSERT INTO conversation_summaries VALUES (?,?,?,?,?,?)', rows)
		conn.commit()
		conn.close()
	# @used-by :mod:`unittest`
	def test_addon_and_markdown_ops(self) -> None:
		from Df.Harness.Hook.JsonRunner import JsonRunner
		from Df.Harness.Hook.RulesServerGate import RulesServerGate
		from Df.Harness.lib import hook_addon_ops as hao, hook_markdown_ops as hmo
		from Df.Harness.lib.path_resolve import dfh_project_paths
		out = io.StringIO()
		jr = JsonRunner(lambda p: {'decision': 'allow', 'x': p.get('a')}, stdin=io.StringIO('{"a": 1}'), stdout=out).run()
		self.assertEqual(jr['x'], 1)
		rs = RulesServerGate({'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'pytest tests/x.py', 'WaitMsBeforeAsync': 500}}}).run()
		self.assertIn('decision', rs)
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/data/turns').mkdir(parents=True)
			rt = root / 'runtime.json'
			rt.write_text(json.dumps({'state': 'error', 'pid': 999999, 'runtimePath': str(root / '\ua616/data/worktrees/w1'), 'errors': {'a': 'b'}}), encoding='utf-8')
			health = hao.dfh_inspect_companion_runtime_health(rt, pid_alive_fn=lambda _p: False)
			self.assertFalse(health['healthy'])
			self.assertIn('companion_warning=', hao.dfh_format_pre_invocation_companion_warning(rt, pid_alive_fn=lambda _p: False))
			self.assertTrue(hao.dfh_is_pid_alive(os.getpid()))
			self.assertFalse(hao.dfh_is_pid_alive(0))
			with patch('Df.Harness.lib.hook_addon_ops.dfh_inspect_companion_runtime_health', return_value=health), patch('agent_tools.polyglot_land.run_repo_health_check', return_value={'ok': True}):
				self.assertIsNotNone(hao.dfh_check_close_companion_health('dmitry-ai/antigravity-addons', code_repo=root))
			with patch.dict(os.environ, {'HARNESS_COMPANION_RUNTIME_JSON': str(rt)}):
				self.assertEqual(hao.dfh_default_companion_runtime_path(), rt)
			self.assertFalse(hao.dfh_is_live_runtime_data_file(root, 'foo.json'))
			(root / '\ua616/data/turns/t1.json').write_text(json.dumps({'status': 'open', 'budget_check': {'graceful_checkpoint_required': True, 'continuation_saved': False}}), encoding='utf-8')
			seg = dfh_project_paths(root, exact_root=True).deliverable_segments[0].strip('/')
			self.assertIsNotNone(hmo.dfh_check_markdown_content('| a | b |\n| --- | --- |\n| 1 | 2 |\n', path=str(root / 'a.md')))
			self.assertIsNotNone(hmo.dfh_check_markdown_content('Clean.  \n', path=str(root / seg / 'draft.md')))
			(root / '\ua616/data/turns/t1.json').unlink()
			doc = root / 'notes.md'
			doc.write_text('Old line\n', encoding='utf-8')
			self.assertIsNotNone(hmo.dfh_check_markdown_content('See [f](file:///C:/work/research/provision/code/AI/harness/scripts/harness.py).  \n', path=str(WT_ROOT / 'README.md')))
			self.assertTrue(hmo.dfh_is_abbreviation_end('e.g.'))
			self.assertEqual(hmo.dfh_resolve_markdown_content('write_file', {'Content': 'abc'}, str(doc)), 'abc')
			self.assertIn('New', hmo.dfh_resolve_markdown_content('edit_file', {'Target': 'Old', 'Replacement': 'New'}, str(doc)))
	# @used-by :mod:`unittest`
	def test_stop_gate_continuation_guard_and_emergency_capture(self) -> None:
		from Df.Harness.Hook.StopGate import StopGate
		from Df.Harness.lib import hook_stop_ops as hso
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/data/turns').mkdir(parents=True)
			(root / '\ua616/project.json').write_text(json.dumps({'id': 'p1'}), encoding='utf-8')
			backend = root / 'ag'
			t_dir = backend / f'brain/{_CID}/.system_generated/logs'
			t_dir.mkdir(parents=True)
			tx = t_dir / 'transcript_full.jsonl'
			rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': f'Work in {root.as_posix()}'}, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': 'Final answer body.'}]
			tx.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			self._make_summary_db(backend / 'conversation_summaries.db', [(_CID, '', 'IDLE', 0, 0, '2026-11-27T00:00:00Z')])
			payload = {'terminationReason': 'NO_TOOL_CALL', 'fullyIdle': True, 'cwd': str(root), 'conversationId': _CID, 'transcriptPath': str(tx)}
			d1 = StopGate(payload, backend_override=backend).run()
			self.assertEqual(d1['decision'], 'continue')
			fake_native = {'conversation_id': _CID, 'backend': str(backend), 'platform': 'antigravity', 'native_log': str(tx), 'turns': [{'start_step': 0, 'owned': True, 'requests': [{'id': f'ag-{_CID}-0', 'native_step': 0, 'text': f'Work in {root.as_posix()}'}]}]}
			with patch('Df.Harness.lib.completion_core.dfh_native_scan', return_value=fake_native):
				d2 = StopGate({**payload, 'continuationActive': True, 'executionNum': 1}, backend_override=backend).run()
			self.assertEqual(d2['decision'], 'allow')
			self.assertEqual(hso.dfh_evaluate_prepared_match({'prepared': {'response_sha256': '0', 'body_sha256': '0', 'response_file': ''}}, 'other')['decision'], 'continue')
			self.assertTrue(hso.dfh_is_journal_opt_out({'lastUserInput': 'skip journaling please'}, [], 0, None))
			self.assertFalse(hso.dfh_handoff_matches_user_step({'handed_off_to': {'job_id': '~0211111111111111111'}}, [{'step_index': 0, 'type': 'USER_INPUT', 'content': '/upwork-init https://www.upwork.com/jobs/~0222222222222222222'}], 0))
			self.assertEqual(len(hso._fallback_ag_hook_paths(tx, None, swallow_errors=True)), 5)
			self.assertEqual(len(hso._fallback_default_ag_paths(True)), 5)
			ag_cfg = {'platforms': {'antigravity': {'instances': {'A0': {'enabled': True, 'home': str(root / 'ag_home')}}}}}
			self.assertIsNone(hso._match_ag_instance_by_transcript(tx, {'A0': {'id': 'A0', 'system_paths': {'brain_dir': str(root / 'other')}}}, _CID, ag_cfg))
			ho_root = root / 'handoff_target'
			ho_root.mkdir()
			(root / '\ua616/data/turns/ho.json').write_text(json.dumps({'key': 'ho1', 'conversation_id': _CID, 'start_step': 0, 'status': 'handed_off', 'handed_off_to': {'project_root': str(ho_root)}}), encoding='utf-8')
			self.assertIn('decision', StopGate(payload, backend_override=backend).run())
			gf = root / '\ua616/data/turns/stop-guards/x.json'
			hso.dfh_save_guard(gf, {'a': 1})
			self.assertEqual(hso.dfh_load_guard(gf)['a'], 1)
			hso.dfh_unlink_guard(gf)
			self.assertFalse(gf.exists())
	# @used-by :mod:`unittest`
	def test_subagent_checker_and_schedule_block(self) -> None:
		from Df.Harness.Hook.SubagentChecker import SubagentChecker
		from Df.Harness.lib import hook_runtime_ops as hro, hook_subagent_ops as hsub
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			logs = root / f'ag/brain/{_CID}/.system_generated/logs'
			logs.mkdir(parents=True)
			tx = logs / 'transcript.jsonl'
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'start'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-27T01:00:00Z', 'tool_calls': [{'name': 'invoke_subagent', 'args': json.dumps({'Role': 'W'})}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': json.dumps({'conversationId': _SUB_ID})},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'send_message', 'args': {'Recipient': _SUB_ID}}, {'name': 'manage_subagents', 'args': {'Action': 'kill', 'ConversationIds': ['99999999-9999-9999-9999-999999999999']}}]},
				{'step_index': 4, 'type': 'EPHEMERAL_MESSAGE', 'content': '[Message] timestamp=2026-11-27T01:01:00Z sender=88888888-8888-8888-8888-888888888888 content=done'},
			]
			tx.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			db = root / 'ag/conversation_summaries.db'
			self._make_summary_db(db, [(_SUB_ID, _CID, 'RUNNING', 1, 0, '2026-11-27T01:02:00Z')])
			all_rows, last_u, seg = hro.dfh_read_last_user_segment(tx, by_step_index=True)
			self.assertEqual(last_u, 0)
			self.assertEqual(len(all_rows), 5)
			st = hsub.dfh_extract_segment_subagent_state(seg)
			self.assertTrue(SubagentChecker(st, _CID, db).run())
			self.assertIsNotNone(hsub.dfh_evaluate_schedule_subagent_block(str(tx), {'TimerCondition': _SUB_ID}, {'conversationId': _CID}))
			self.assertIsNotNone(hsub.dfh_evaluate_schedule_subagent_block(str(tx), {}, {'conversationId': _CID}))
			st2 = hsub.dfh_extract_segment_subagent_state([{'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'manage_subagents', 'args': {'Action': 'kill_all'}}]}])
			self.assertTrue(st2['killed_all'])
	# @used-by :mod:`unittest`
	def test_trace_event_cache_full_incremental_and_clear(self) -> None:
		from Df.Harness.Hook.TraceEventCache import TraceEventCache
		from Df.Harness.lib import hook_trace_cache as htc
		htc.dfh_clear_in_process_trace_cache()
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/data/turns').mkdir(parents=True)
			logs = root / f'brain/{_CID}/.system_generated/logs'
			logs.mkdir(parents=True)
			comp = logs / 'transcript.jsonl'
			full = logs / 'transcript_full.jsonl'
			comp.write_text(json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'a'}) + '\n', encoding='utf-8')
			full.write_text(json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'content': 'a'}) + '\n', encoding='utf-8')
			r1, s1 = TraceEventCache(comp, cwd=root, return_stats=True).run()
			self.assertEqual(len(r1), 1)
			self.assertIsInstance(s1, dict)
			with open(full, 'ab') as fh:
				fh.write((json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': 'b'}) + '\n').encode('utf-8'))
			htc.dfh_clear_in_process_trace_cache()
			r2, s2 = TraceEventCache(comp, cwd=root, return_stats=True).run()
			self.assertEqual(len(r2), 2)
			self.assertIsInstance(s2, dict)
	# @used-by :mod:`unittest`
	def test_verif_pre_invocation_and_crash_ops(self) -> None:
		from Df.Harness.lib import hook_crash_ops as hco, hook_pre_invocation_ops as hpi, hook_verif_ops as hvo
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / '\ua616/data').mkdir(parents=True)
			self.assertTrue(hvo.dfh_is_shadow_replay_cmd('python harness.py shadow-replay .'))
			self.assertTrue(hvo.dfh_classify_shadow_output(3, '{"valid": false}\nCommand exited with code 1.')['failed'])
			self.assertEqual(hvo.dfh_closed_issues_after({'issue_actions': [{'action': 'close', 'repo': 'a/b', 'number': 1, 'step': 4}]}, 3), ['a/b#1'])
			self.assertTrue(hvo.dfh_response_discloses_shadow_failure('shadow-replay failed with exit code 1'))
			tx = root / 'tx.jsonl'
			tx.write_text(json.dumps({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py shadow-replay .'}}]}) + '\n' + json.dumps({'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 1.'}) + '\n', encoding='utf-8')
			self.assertEqual(len(hvo.dfh_detect_shadow_replay_runs({'source_file': str(tx)}, {'start_step': 0})), 1)
			conv_dir = root / 'conversations'
			conv_dir.mkdir()
			conn = sqlite3.connect(str(conv_dir / f'{_CID}.db'))
			conn.execute('CREATE TABLE steps (idx INTEGER, step_type INTEGER, status INTEGER)')
			conn.execute('INSERT INTO steps VALUES (1, 15, 3)')
			conn.commit()
			conn.close()
			self.assertTrue(hpi._has_planner_steps(conv_dir, _CID))
			self.assertEqual(len(hpi.dfh_expected_turn_key(root, _CID, 1)), 40)
			self.assertIn('injectSteps', hpi.dfh_format_turn_begin_message(root, {'turn_key': 'k1', 'conversation_title_sync': {'title': 'T'}, 'similar_projects': ['p1']}))
			rec, _ = hco.dfh_build_violation_recovery_receipt(root, 'k1', {'start_step': 1}, 'fixed', lambda: '2026-11-27T00:00:00Z', native={'native_log': str(tx)})
			self.assertEqual(rec['turn_key'], 'k1')
if '__main__' == __name__:
	unittest.main()
