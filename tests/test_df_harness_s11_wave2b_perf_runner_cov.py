# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
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
_MIX_SRC = 'import subprocess, sys, time, unittest\nclass Mix(unittest.TestCase):\n\tdef test_proc(self):\n\t\tp = subprocess.Popen([sys.executable, "-c", "print(1)"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)\n\t\tp.communicate()\n\t\tp2 = subprocess.Popen([sys.executable, "-c", "pass"])\n\t\tp2.wait()\n\t\ttime.sleep(0.005)\n\tdef test_fail(self):\n\t\tself.assertEqual(1, 2)\n\tdef test_err(self):\n\t\traise RuntimeError("boom")\n\t@unittest.skip("skip")\n\tdef test_skip(self):\n\t\tpass\n'
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`unittest`
class DfHarnessS11Wave2bPerfRunnerCovTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_perf_analyzers_and_timesheet_cli(self) -> None:
		from Df.Harness.Perf.AntigravityTimesheetAnalyzer import AntigravityTimesheetAnalyzer
		from Df.Harness.Perf.CodexTimesheetAnalyzer import CodexTimesheetAnalyzer
		from Df.Harness.Perf.TimesheetBuilder import TimesheetBuilder
		from Df.Harness.Perf.TimesheetCommon import TimesheetCommon
		bg_id = 'cid1/task-2'
		ag_rows = [
			{'step_index': 0, 'type': 'USER_INPUT', 'created_at': '2026-11-26T10:00:00Z'},
			{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-26T10:00:05Z', 'model': 'm1', 'input_tokens': 100, 'cache_read_tokens': 0, 'output_tokens': 20, 'tool_calls': [{'name': 'exit_plan_mode', 'args': {}}, {'name': 'run_command', 'args': {'CommandLine': 'python -m pytest -x'}}]},
			{'step_index': 2, 'type': 'GENERIC', 'created_at': '2026-11-26T10:00:06Z', 'content': 'Created At: 2026-11-26T10:00:05Z\nCompleted At: 2026-11-26T10:00:06Z\nOK'},
			{'step_index': 3, 'type': 'GENERIC', 'created_at': '2026-11-26T10:00:07Z', 'content': f'Tool is running as a background task with task id: {bg_id}'},
			{'step_index': 4, 'type': 'SYSTEM_MESSAGE', 'created_at': '2026-11-26T10:00:15Z', 'content': f'sender={bg_id} Task id "{bg_id}" finished with result:\nRan 3 tests in 4.0s\nOK'},
			{'step_index': 5, 'type': 'CHECKPOINT', 'created_at': '2026-11-26T10:00:16Z', 'input_tokens': 200, 'cache_read_tokens': 50},
			{'step_index': 6, 'type': 'PLANNER_RESPONSE', 'created_at': '2026-11-26T10:00:20Z', 'model': 'm2', 'input_tokens': 150, 'cache_read_tokens': 0, 'output_tokens': 30, 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'git status'}}]},
			{'step_index': 7, 'type': 'GENERIC', 'created_at': '2026-11-26T10:00:21Z', 'content': 'Created At: 2026-11-26T10:00:20Z\nCompleted At: 2026-11-26T10:00:21Z\nOK'},
		]
		self.assertEqual(1, AntigravityTimesheetAnalyzer(ag_rows).analyze()['models']['cold_switch_count'])
		cx_rows = [
			{'timestamp': '2026-11-26T10:00:00Z', 'type': 'turn_context', 'payload': {'model': 'gpt-5'}},
			{'timestamp': '2026-11-26T10:00:01Z', 'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'exec_command', 'call_id': 'c1', 'arguments': json.dumps({'cmd': 'pytest -x'})}},
			{'timestamp': '2026-11-26T10:00:05Z', 'type': 'response_item', 'payload': {'type': 'function_call_output', 'call_id': 'c1', 'output': 'x' * 15001}},
			{'timestamp': '2026-11-26T10:00:06Z', 'type': 'event_msg', 'payload': {'type': 'context_compacted'}},
			{'timestamp': '2026-11-26T10:00:08Z', 'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'last_token_usage': {'input_tokens': 500, 'cached_input_tokens': 100, 'output_tokens': 50}}}},
		]
		cx_rep = CodexTimesheetAnalyzer(cx_rows).analyze()
		self.assertEqual(400, cx_rep['tokens']['fresh_input_tokens'])
		self.assertIn('Surface:', TimesheetCommon.format_text({'surface': 'codex', **cx_rep}))
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			tr = root / 'trace.jsonl'
			tr.write_text('\n'.join((json.dumps(r) for r in ag_rows)) + '\n', encoding='utf-8')
			jfile = root / '\ua66e/\u227a/1\u201320/1.md'
			jfile.parent.mkdir(parents=True)
			jfile.write_text('```json\n' + json.dumps({'Trace': {'Conversation ID': 'cid1', 'Transcript': tr.as_posix(), 'Turn': {'Start Step': 0}}}) + '\n```\nBody.\n', encoding='utf-8')
			out_p = root / 'ts.json'
			with patch('agent_tools.runtime.find_conversation_instance', return_value=[{'id': 'ag1', 'trace_file': str(tr), 'system_paths': {}}]):
				self.assertEqual(tr.resolve(), TimesheetCommon.resolve_trace_source(conversation='cid1')['trace_path'])
				self.assertTrue(TimesheetBuilder.run_cli(SimpleNamespace(trace=None, conversation=None, project=root, journal_step=1, instance=None, platform=None, summary_db=None, turn_start_step=None, turn_end_step=None, top_gaps=5, output=str(out_p)))['valid'])
	# @used-by :mod:`unittest`
	def test_perf_profiler_worker_timed_result_and_tracked_popen(self) -> None:
		from Df.Harness.Perf.SuiteProfiler import SuiteProfiler
		from Df.Harness.Perf.SuiteWorker import SuiteWorker
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			tmod = root / 'test_prof_mix.py'
			tmod.write_text(_MIX_SRC, encoding='utf-8')
			wrep = SuiteWorker(tmod, root, cprofile_top=5).run()
			self.assertEqual(1, wrep['failures'])
			self.assertEqual(1, wrep['errors'])
			self.assertEqual(1, wrep['skipped'])
			self.assertTrue(wrep['cprofile'])
			out_p = root / 'prof.json'
			cli_rep = SuiteProfiler.run_cli(SimpleNamespace(target=str(root), workers=None, module_timeout=30.0, pattern='test_*.py', module=None, cprofile=True, top=5, cprofile_top=5, output=str(out_p)))
			self.assertIn('Tests dir:', SuiteProfiler.format_text(cli_rep))
			self.assertGreaterEqual(SuiteProfiler.default_workers(), 2)
			slow = root / 'test_slow_timeout.py'
			slow.write_text('import time, unittest\nclass S(unittest.TestCase):\n\tdef test_s(self):\n\t\ttime.sleep(5)\n', encoding='utf-8')
			self.assertFalse(SuiteProfiler(root, workers=1, module_timeout=0.05, modules=['test_slow_timeout']).profile()['valid'])
	# @used-by :mod:`unittest`
	def test_runner_process_tree_watchdog_semaphore_and_pytest_modes(self) -> None:
		from Df.Harness.TestRunner.ParallelRunner import ParallelRunner
		from Df.Harness.TestRunner.ProcessTree import ProcessTree
		from Df.Harness.TestRunner.PytestWorkstealRunner import PytestWorkstealRunner
		from Df.Harness.TestRunner.SuiteRunner import SuiteRunner
		from Df.Harness.TestRunner.WatchdogRunner import WatchdogRunner
		from Df.Harness.TestRunner.WorkerSemaphore import WorkerSemaphore
		self.assertGreaterEqual(ParallelRunner.default_worker_count(3), 1)
		self.assertGreaterEqual(SuiteRunner.default_workers(), 2)
		self.assertIsInstance(PytestWorkstealRunner.xdist_available(), bool)
		self.assertTrue(WatchdogRunner.run_cli(SimpleNamespace(cmd=[sys.executable, '-c', 'print(1)'], timeout=10.0, cwd=None))['ok'])
		fake_proc = MagicMock(pid=999999)
		fake_proc.poll.return_value = None
		with patch('Df.Harness.TestRunner.ProcessTree.df_is_windows', return_value=False), patch('os.getpgid', create=True, side_effect=OSError), patch('os.killpg', create=True), patch('signal.SIGKILL', 9, create=True):
			ProcessTree(fake_proc).kill()
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			sdir = root / 'slots'
			sdir.mkdir()
			(sdir / 'stale.json').write_text(json.dumps({'owner': 'old', 'pid': os.getpid(), 'slots': 1, 'expires_at': time.time() - 10}), encoding='utf-8')
			lease = WorkerSemaphore(1, max_slots=2, slots_dir=sdir).acquire()
			self.assertTrue(WorkerSemaphore.release(lease))
			m1 = root / 'test_ok_one.py'
			m1.write_text('import unittest\nclass A(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
			self.assertEqual(1, len(SuiteRunner.discover_modules(root, modules=['test_ok_one'])[1]))
			self.assertTrue(PytestWorkstealRunner.run_for_parallel(root, [m1], workers=1, failfast=True, module_timeout=30.0)['ok'])
			self.assertTrue(PytestWorkstealRunner.run_for_suite(root, [m1], workers=1, failfast=True, module_timeout=30.0)['ok'])
	# @used-by :mod:`unittest`
	def test_runner_failfast_timeout_and_format_text(self) -> None:
		from Df.Harness.TestRunner.ParallelRunner import ParallelRunner
		from Df.Harness.TestRunner.SuiteRunner import SuiteRunner
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / 'test_fast_fail.py').write_text('import unittest\nclass A(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(1, 2)\n', encoding='utf-8')
			(root / 'test_slow_sib.py').write_text('import time, unittest\nclass B(unittest.TestCase):\n\tdef test_b(self):\n\t\ttime.sleep(5)\n', encoding='utf-8')
			self.assertFalse(ParallelRunner(root, workers=2, failfast=True, module_timeout=10.0, runner='unittest').run()['ok'])
			s_res = SuiteRunner(root, workers=2, failfast=True, module_timeout=10.0, runner='unittest').run()
			self.assertFalse(s_res['ok'])
			self.assertIn('FAIL:', SuiteRunner.format_text(s_res))
			self.assertIn('TIMEOUT:', SuiteRunner.format_text({'ok': False, 'total_tests': 0, 'elapsed': 1.0, 'passed_modules': 0, 'total_modules': 1, 'workers': 1, 'failed_modules': 0, 'timed_out_modules': 1, 'skipped_tests': 0, 'module_timeout': 1.0, 'results': [{'module': 'm', 'status': 'timeout', 'elapsed': 1.0, 'output': 'hang'}]}))
			self.assertIn('OK', SuiteRunner.format_text({'ok': True, 'total_tests': 1, 'elapsed': 0.1, 'passed_modules': 1, 'total_modules': 1, 'workers': 1, 'failed_modules': 0, 'timed_out_modules': 0, 'skipped_tests': 0, 'module_timeout': 1.0, 'results': []}))
			(root / 'test_pipe_hang.py').write_text('import subprocess, sys, time, unittest\nclass H(unittest.TestCase):\n\tdef test_h(self):\n\t\tsubprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"])\n\t\ttime.sleep(5)\n', encoding='utf-8')
			self.assertFalse(ParallelRunner(root, workers=1, modules=['test_pipe_hang'], module_timeout=0.2, runner='unittest').run()['ok'])
if '__main__' == __name__:
	unittest.main()
