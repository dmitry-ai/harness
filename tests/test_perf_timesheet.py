# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = WT_ROOT / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
# @used-by :meth:`PerfTimesheetTests.test_antigravity_parallel_tool_calls_match_bg_task_result()`
# @used-by :meth:`PerfTimesheetTests.test_antigravity_timesheet_computes_chronometry_switches_checkpoints_and_bg_waits()`
# @used-by :meth:`PerfTimesheetTests.test_cli_help_text_format_and_journal_step_resolution()`
# @used-by :meth:`PerfTimesheetTests.test_codex_rollout_timesheet_and_step_slicing()`
def _write_jsonl(path: Path, rows: list[dict]) -> Path:
	path.parent.mkdir(parents=True, exist_ok=True)
	text = '\n'.join((json.dumps(r, ensure_ascii=False) for r in rows)) + '\n'
	path.write_text(text, encoding='utf-8')
	return path
# @used-by :meth:`PerfTimesheetTests.test_antigravity_timesheet_computes_chronometry_switches_checkpoints_and_bg_waits()`
def _make_summary_db(path: Path, cid: str, start_ts: str, end_ts: str) -> Path:
	conn = sqlite3.connect(str(path))
	try:
		conn.execute('CREATE TABLE conversation_summaries (conversation_id TEXT PRIMARY KEY, last_user_input_time TEXT, last_modified_time TEXT)')
		conn.execute('INSERT INTO conversation_summaries VALUES (?, ?, ?)', (cid, start_ts, end_ts))
		conn.commit()
	finally:
		conn.close()
	return path
# @used-by :meth:`PerfTimesheetTests.test_antigravity_timesheet_computes_chronometry_switches_checkpoints_and_bg_waits()`
# @used-by :meth:`PerfTimesheetTests.test_cli_help_text_format_and_journal_step_resolution()`
def _sample_antigravity_rows(cid: str) -> list[dict]:
	bg_id = f'{cid}/task-4'
	return [
		{'step_index': 0, 'source': 'USER_EXPLICIT', 'type': 'USER_INPUT', 'status': 'DONE', 'created_at': '2026-11-23T10:00:00Z', 'content': 'Audit performance'},
		{'step_index': 1, 'source': 'MODEL', 'type': 'PLANNER_RESPONSE', 'status': 'DONE', 'created_at': '2026-11-23T10:00:05Z', 'model': 'gemini-4-carbon-high', 'input_tokens': 20000, 'cache_read_tokens': 0, 'output_tokens': 1200, 'tool_calls': [{'name': 'exit_plan_mode', 'args': {'plan': 'step 1'}}]},
		{'step_index': 2, 'source': 'MODEL', 'type': 'GENERIC', 'status': 'DONE', 'created_at': '2026-11-23T10:00:35Z', 'content': 'Created At: 2026-11-23T13:00:35+03:00\nCompleted At: 2026-11-23T13:00:36+03:00\nOK'},
		{'step_index': 3, 'source': 'MODEL', 'type': 'PLANNER_RESPONSE', 'status': 'DONE', 'created_at': '2026-11-23T10:00:36Z', 'model': 'gemini-4-neon-xhigh', 'input_tokens': 35000, 'cache_read_tokens': 0, 'output_tokens': 300, 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python -m unittest discover -f -s tests -p test_*.py'}}]},
		{'step_index': 4, 'source': 'MODEL', 'type': 'GENERIC', 'status': 'RUNNING', 'created_at': '2026-11-23T10:00:40Z', 'content': f'Created At: 2026-11-23T13:00:40+03:00\nTool is running as a background task with task id: {bg_id}\nTask Description: python -m unittest discover -f -s tests -p test_*.py'},
		{'step_index': 5, 'source': 'MODEL', 'type': 'PLANNER_RESPONSE', 'status': 'DONE', 'created_at': '2026-11-23T10:00:45Z', 'model': 'gemini-4-neon-xhigh', 'input_tokens': 2000, 'cache_read_tokens': 36000, 'output_tokens': 150, 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py fetch --repo dmitry-ai/harness --issue 189'}}]},
		{'step_index': 6, 'source': 'MODEL', 'type': 'GENERIC', 'status': 'DONE', 'created_at': '2026-11-23T10:00:46Z', 'content': 'The tool\'s output was truncated due to being too long.\nCreated At: 2026-11-23T13:00:46+03:00\nCompleted At: 2026-11-23T13:00:52+03:00\nOK'},
		{'step_index': 7, 'source': 'SYSTEM', 'type': 'SYSTEM_MESSAGE', 'status': 'DONE', 'created_at': '2026-11-23T10:01:20Z', 'content': f'<SYSTEM_MESSAGE>\n[Message] timestamp=2026-11-23T10:01:20Z sender={bg_id} priority=MESSAGE_PRIORITY_HIGH content=Task id "{bg_id}" finished with result:\nCommand exited with code 0.\n\nRan 11 tests in 38.250s\n\nOK\n</SYSTEM_MESSAGE>'},
		{'step_index': 8, 'source': 'SYSTEM', 'type': 'CHECKPOINT', 'status': 'DONE', 'created_at': '2026-11-23T10:01:21Z', 'input_tokens': 4000, 'cache_read_tokens': 40000, 'output_tokens': 500, 'content': '# Resuming from a compaction'},
		{'step_index': 9, 'source': 'MODEL', 'type': 'PLANNER_RESPONSE', 'status': 'DONE', 'created_at': '2026-11-23T10:01:51Z', 'model': 'gemini-4-neon-xhigh', 'input_tokens': 18000, 'cache_read_tokens': 0, 'output_tokens': 400, 'content': 'Done'},
	]
# @used-by :meth:`PerfTimesheetTests.test_codex_rollout_timesheet_and_step_slicing()`
def _sample_codex_rows() -> list[dict]:
	return [
		{'timestamp': '2026-11-23T12:00:00Z', 'type': 'session_meta', 'payload': {'id': '11111111-2222-3333-4444-555555555555', 'cwd': 'C:/work/demo'}},
		{'timestamp': '2026-11-23T12:00:01Z', 'type': 'turn_context', 'payload': {'turn_id': 'turn-1', 'model': 'gpt-5.4', 'effort': 'high'}},
		{'timestamp': '2026-11-23T12:00:01Z', 'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': 'turn-1'}},
		{'timestamp': '2026-11-23T12:00:02Z', 'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'exec_command', 'call_id': 'c1', 'arguments': json.dumps({'cmd': 'python -m pytest tests -n auto --dist worksteal -x'})}},
		{'timestamp': '2026-11-23T12:00:22Z', 'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'c1', 'output': '12 passed in 19.40s'}},
		{'timestamp': '2026-11-23T12:00:23Z', 'type': 'event_msg', 'payload': {'type': 'context_compacted'}},
		{'timestamp': '2026-11-23T12:00:43Z', 'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'last_token_usage': {'input_tokens': 15000, 'cached_input_tokens': 5000, 'output_tokens': 600}}}},
		{'timestamp': '2026-11-23T12:00:44Z', 'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'exec_command', 'call_id': 'c2', 'arguments': json.dumps({'cmd': 'python scripts/harness.py answer-prepare . --response-file x.md'})}},
		{'timestamp': '2026-11-23T12:00:49Z', 'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'c2', 'output': '{"ready": true}'}},
		{'timestamp': '2026-11-23T12:00:50Z', 'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': 'turn-1'}},
	]
# 2026-11-24
# "Add harness perf-timesheet CLI for deterministic turn chronometry":
# https://github.com/dmitry-ai/harness/issues/191
class PerfTimesheetTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_antigravity_timesheet_computes_chronometry_switches_checkpoints_and_bg_waits(self) -> None:
		from agent_tools.perf.timesheet import build_timesheet
		cid = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
		with tempfile.TemporaryDirectory() as td:
			tmp = Path(td)
			trace = _write_jsonl(tmp / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl', _sample_antigravity_rows(cid))
			db = _make_summary_db(tmp / 'conversation_summaries.db', cid, '2026-11-23 10:00:00+00:00', '2026-11-23 10:02:00+00:00')
			out_file = tmp / 'timesheet.json'
			rep = build_timesheet(trace, summary_db=db, conversation_id=cid)
			self.assertEqual('antigravity', rep['surface'])
			self.assertEqual(10, rep['step_count'])
			self.assertAlmostEqual(111.0, rep['timestamps']['total_span_to_last_step_s'], places=1)
			self.assertAlmostEqual(120.0, rep['timestamps']['total_span_to_last_modified_s'], places=1)
			self.assertEqual({'gemini-4-carbon-high': 1, 'gemini-4-neon-xhigh': 3}, rep['models']['planner_steps_by_model'])
			self.assertEqual(1, rep['models']['cold_switch_count'])
			self.assertEqual(35000, rep['models']['cold_switch_uncached_input_tokens'])
			self.assertEqual(1, len(rep['models']['same_model_cache_misses']))
			self.assertEqual(44000, rep['models']['peak_context_tokens'])
			self.assertEqual(1200, rep['tokens']['plan_mode_output_tokens'])
			self.assertEqual(1, len(rep['checkpoints']))
			self.assertAlmostEqual(30.0, rep['checkpoints'][0]['dur_s'], places=1)
			self.assertEqual(1, len(rep['tools']['truncated_outputs']))
			self.assertEqual(1, rep['commands']['categories']['test_runs']['count'])
			self.assertEqual(1, rep['commands']['categories']['github_issue_cli']['count'])
			self.assertEqual(1, len(rep['commands']['bg_test_waits']))
			bg = rep['commands']['bg_test_waits'][0]
			self.assertAlmostEqual(44.0, bg['wall_s'], places=1)
			self.assertEqual(11, bg['tests_count'])
			self.assertAlmostEqual(38.25, bg['runner_s'], places=2)
			self.assertAlmostEqual(28.0, bg['idle_wait_s'], places=1)
			self.assertGreater(bg['overlapped_work_s'], 0.0)
			self.assertTrue(rep['top_gaps'])
			proc = subprocess.run([sys.executable, str(SCRIPT_DIR / 'harness.py'), 'perf-timesheet', '--trace', str(trace), '--summary-db', str(db), '--output', str(out_file)], capture_output=True, text=True, encoding='utf-8', check=True)
			cli_data = json.loads(proc.stdout)
			self.assertEqual(rep['trace_sha256'], cli_data['trace_sha256'])
			self.assertTrue(out_file.is_file())
			self.assertEqual(cli_data['step_count'], json.loads(out_file.read_text(encoding='utf-8'))['step_count'])
	# @used-by :mod:`unittest`
	def test_antigravity_parallel_tool_calls_match_bg_task_result(self) -> None:
		from agent_tools.perf.timesheet import build_timesheet
		cid = 'cccccccc-dddd-eeee-ffff-000000000000'
		bg_id = f'{cid}/task-3'
		rows = [
			{'step_index': 0, 'source': 'USER_EXPLICIT', 'type': 'USER_INPUT', 'status': 'DONE', 'created_at': '2026-11-23T10:00:00Z', 'content': 'Run full suite'},
			{'step_index': 1, 'source': 'MODEL', 'type': 'PLANNER_RESPONSE', 'status': 'DONE', 'created_at': '2026-11-23T10:00:05Z', 'model': 'gemini-4-neon-xhigh', 'input_tokens': 1000, 'cache_read_tokens': 0, 'output_tokens': 50, 'tool_calls': [{'name': 'update_focus', 'args': {'focus': 'Running tests'}}, {'name': 'run_command', 'args': {'CommandLine': 'python -m unittest discover -f -s tests'}}]},
			{'step_index': 2, 'source': 'MODEL', 'type': 'GENERIC', 'status': 'DONE', 'created_at': '2026-11-23T10:00:06Z', 'content': 'Created At: 2026-11-23T13:00:06+03:00\nCompleted At: 2026-11-23T13:00:06+03:00\nOK'},
			{'step_index': 3, 'source': 'MODEL', 'type': 'GENERIC', 'status': 'RUNNING', 'created_at': '2026-11-23T10:00:06Z', 'content': f'Created At: 2026-11-23T13:00:06+03:00\nTool is running as a background task with task id: {bg_id}\nTask Description: python -m unittest discover -f -s tests'},
			{'step_index': 4, 'source': 'SYSTEM', 'type': 'SYSTEM_MESSAGE', 'status': 'DONE', 'created_at': '2026-11-23T10:01:45Z', 'content': f'<SYSTEM_MESSAGE>\n[Message] timestamp=2026-11-23T10:01:45Z sender={bg_id} priority=MESSAGE_PRIORITY_HIGH content=Task id "{bg_id}" finished with result:\nCommand exited with code 0.\n\nRan 885 tests in 95.000s\n\nOK\n</SYSTEM_MESSAGE>'},
		]
		with tempfile.TemporaryDirectory() as td:
			trace = _write_jsonl(Path(td) / 'trace.jsonl', rows)
			rep = build_timesheet(trace, conversation_id=cid)
			self.assertEqual(1, len(rep['commands']['bg_test_waits']))
			self.assertAlmostEqual(100.0, rep['commands']['bg_test_waits'][0]['wall_s'], places=1)
			self.assertEqual(885, rep['commands']['bg_test_waits'][0]['tests_count'])
			self.assertAlmostEqual(100.0, rep['commands']['categories']['test_runs']['wall_s'], places=1)
	# @used-by :mod:`unittest`
	def test_cli_help_text_format_and_journal_step_resolution(self) -> None:
		cid = 'bbbbbbbb-cccc-dddd-eeee-ffffffffffff'
		with tempfile.TemporaryDirectory() as td:
			tmp = Path(td)
			trace = _write_jsonl(tmp / 'trace.jsonl', _sample_antigravity_rows(cid))
			proj = tmp / 'proj'
			res_md = proj / '\ua66e' / '\u227a' / '1\u201320' / '5.md'
			res_md.parent.mkdir(parents=True, exist_ok=True)
			header = {'Trace': {'Conversation ID': cid, 'Transcript': trace.as_posix(), 'Turn': {'Start Step': 3}}}
			res_md.write_text('```json\n' + json.dumps(header, indent='\t') + '\n```\n\n# Result\n', encoding='utf-8')
			p_help = subprocess.run([sys.executable, str(SCRIPT_DIR / 'harness.py'), 'perf-timesheet', '--help'], capture_output=True, text=True, encoding='utf-8', check=True)
			for flag in ('--trace', '--conversation', '--journal-step', '--turn-start-step', '--output', '--format'):
				self.assertIn(flag, p_help.stdout)
			p_txt = subprocess.run([sys.executable, str(SCRIPT_DIR / 'harness.py'), 'perf-timesheet', '--project', str(proj), '--journal-step', '5', '--format', 'text'], capture_output=True, text=True, encoding='utf-8', check=True)
			self.assertIn('Surface: antigravity', p_txt.stdout)
			self.assertIn('Step count: 7', p_txt.stdout)
			self.assertIn('test_runs', p_txt.stdout)
	# @used-by :mod:`unittest`
	def test_codex_rollout_timesheet_and_step_slicing(self) -> None:
		from agent_tools.perf.timesheet import build_timesheet
		with tempfile.TemporaryDirectory() as td:
			trace = _write_jsonl(Path(td) / 'rollout.jsonl', _sample_codex_rows())
			rep = build_timesheet(trace)
			self.assertEqual('codex', rep['surface'])
			self.assertEqual(10, rep['step_count'])
			self.assertAlmostEqual(50.0, rep['timestamps']['total_span_to_last_step_s'], places=1)
			self.assertEqual(1, len(rep['checkpoints']))
			self.assertAlmostEqual(20.0, rep['checkpoints'][0]['dur_s'], places=1)
			self.assertEqual(1, rep['commands']['categories']['test_runs']['count'])
			self.assertEqual(1, rep['commands']['categories']['answer_check_prepare']['count'])
			self.assertEqual(10000, rep['tokens']['fresh_input_tokens'])
			self.assertEqual(5000, rep['tokens']['cache_read_tokens'])
			sliced = build_timesheet(trace, turn_start_step=3, turn_end_step=7)
			self.assertEqual(5, sliced['step_count'])
			self.assertEqual({'start_step': 3, 'end_step': 7}, sliced['slice'])
if '__main__' == __name__:
	unittest.main()
