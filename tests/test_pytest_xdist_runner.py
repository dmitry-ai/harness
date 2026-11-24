# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce watchdog timeout and stdin isolation for unittest and pytest in failfast_gate":
# https://github.com/dmitry-ai/harness/issues/205
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enable parallel pytest-xdist full-suite execution and outcome parsing":
# https://github.com/dmitry-ai/harness/issues/178
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import importlib
import os
import sys
import tempfile
import unittest
TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / 'scripts'
for _p in (str(TESTS_DIR), str(SCRIPTS_DIR)):
	if _p not in sys.path:
		sys.path.insert(0, _p)
from agent_tools import failfast_gate, tdd_gate
class PytestXdistRunnerTests(unittest.TestCase):
	def test_classify_pytest_xdist_full_suite_and_filtered(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve()
			(repo / 'tests').mkdir()
			(repo / 'tests/test_a.py').write_text('def test_a(): assert 1 == 1\n', encoding='utf-8')
			(repo / 'tests/test_b.py').write_text('def test_b(): assert 2 == 2\n', encoding='utf-8')
			full_cmd = f'python -m pytest "{repo / "tests"}" -n auto --dist worksteal -x'
			info_full = tdd_gate.classify_test_command(full_cmd, scope_root=repo)
			self.assertTrue(info_full['is_test_cmd'])
			self.assertTrue(info_full['is_full_suite'])
			deny, overwrite = failfast_gate.evaluate_pre_tool_use_test_failfast('run_command', {'CommandLine': full_cmd, 'WaitMsBeforeAsync': 10000})
			self.assertIsNone(deny)
			self.assertIn('test-watchdog', (overwrite or {}).get('CommandLine', ''))
			bounded_cmd = f'{full_cmd} --timeout=120'
			b_deny, b_overwrite = failfast_gate.evaluate_pre_tool_use_test_failfast('run_command', {'CommandLine': bounded_cmd, 'WaitMsBeforeAsync': 10000})
			self.assertIsNone(b_deny)
			self.assertIsNone(b_overwrite)
			for narrowed in (f'python -m pytest "{repo / "tests/test_a.py"}" -k test_a -x', f'python -m pytest "{repo / "tests"}" -k test_a -x'):
				info_part = tdd_gate.classify_test_command(narrowed, scope_root=repo)
				self.assertTrue(info_part['is_test_cmd'])
				self.assertFalse(info_part['is_full_suite'])
	def test_conftest_adds_scripts_and_tests_paths_and_sets_default_no_fsync(self) -> None:
		conftest_mod = importlib.import_module('conftest')
		with patch.dict(os.environ, {}, clear=False):
			os.environ.pop('HARNESS_TEST_NO_FSYNC', None)
			paths: list[str] = []
			conftest_mod.configure_test_environment(sys_path=paths, env=os.environ)
			self.assertEqual('1', os.environ.get('HARNESS_TEST_NO_FSYNC'))
			self.assertIn(str(SCRIPTS_DIR), paths)
			self.assertIn(str(TESTS_DIR), paths)
		with patch.dict(os.environ, {'HARNESS_TEST_NO_FSYNC': '0'}, clear=False):
			paths_keep: list[str] = []
			conftest_mod.configure_test_environment(sys_path=paths_keep, env=os.environ)
			self.assertEqual('0', os.environ.get('HARNESS_TEST_NO_FSYNC'))
	def test_parse_command_outcome_handles_pytest_xdist_pass_fail_and_exit_code_5(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			t = Path(tmp).resolve()
			zero_out = 'Command exited with code 5.\n\nCommand output:\ncollected 20 items / 20 deselected / 0 selected\n=== no tests ran in 0.15s ===\n'
			zero_res = tdd_gate.parse_command_outcome(zero_out)
			self.assertTrue(zero_res['ran_zero_tests'])
			self.assertFalse(zero_res['is_pass'])
			self.assertFalse(zero_res['is_failure'])
			pass_log = t / 'task-xdist-pass.log'
			pass_log.write_text('8 workers [900 items]\n======================= 900 passed, 1 skipped in 34.12s =======================\n', encoding='utf-8')
			pass_bg = f'Tool is running as a background task with task id: conv-1/task-p\nTask logs are available at: {pass_log.as_uri()}\nLog output:\n...'
			pass_res = tdd_gate.parse_command_outcome(pass_bg)
			self.assertEqual(0, pass_res['exit_code'])
			self.assertTrue(pass_res['is_pass'])
			self.assertFalse(pass_res['is_failure'])
			fail_log = t / 'task-xdist-fail.log'
			fail_log.write_text('FAILED tests/test_demo.py::TestDemo::test_bad - AssertionError: 1 != 2\n================= 1 failed, 2 passed in 1.23s =================\n', encoding='utf-8')
			fail_bg = f'Tool is running as a background task with task id: conv-1/task-f\nTask logs are available at: {fail_log.as_uri()}\nLog output:\n...'
			fail_res = tdd_gate.parse_command_outcome(fail_bg)
			self.assertEqual(1, fail_res['exit_code'])
			self.assertTrue(fail_res['is_failure'])
			self.assertFalse(fail_res['is_pass'])
	def test_tdd_state_machine_rejects_exit_5_red_and_accepts_xdist_full_green(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve()
			(repo / '.git').mkdir()
			(repo / 'tests').mkdir()
			(repo / 'tests/test_a.py').write_text('def test_a(): assert 1 == 1\n', encoding='utf-8')
			(repo / 'tests/test_b.py').write_text('def test_b(): assert 2 == 2\n', encoding='utf-8')
			(repo / 'app.py').write_text('x = 1\n', encoding='utf-8')
			zero_events = [
				tdd_gate.build_file_write_tdd_event(1, repo / 'tests/test_a.py'),
				tdd_gate.build_command_tdd_event(2, f'python -m pytest "{repo / "tests/test_a.py"}" -k typo -x', 'Command exited with code 5.\n\nCommand output:\n=== no tests ran in 0.12s ===\n', cwd=repo),
				tdd_gate.build_file_write_tdd_event(3, repo / 'app.py'),
			]
			res_zero = tdd_gate.evaluate_tdd_events(zero_events, require_final_full_green=False)
			self.assertFalse(res_zero['verified'])
			pass_log = repo / 'xdist-full.log'
			pass_log.write_text('======================= 2 passed in 0.42s =======================\n', encoding='utf-8')
			good_events = [
				tdd_gate.build_file_write_tdd_event(1, repo / 'tests/test_a.py'),
				tdd_gate.build_command_tdd_event(2, f'python -m pytest "{repo / "tests/test_a.py"}" -k test_a -x', 'Command exited with code 1.\n\nCommand output:\nFAILED tests/test_a.py::test_a - AssertionError\n', cwd=repo),
				tdd_gate.build_file_write_tdd_event(3, repo / 'app.py'),
				tdd_gate.build_command_tdd_event(4, f'python -m pytest "{repo / "tests"}" -n auto --dist worksteal -x', f'Tool is running as a background task with task id: conv-1/task-g\nTask logs are available at: {pass_log.as_uri()}\nLog output:\n...', cwd=repo),
			]
			res_good = tdd_gate.evaluate_tdd_events(good_events, require_final_full_green=True)
			self.assertTrue(res_good['verified'], res_good)
			self.assertEqual(4, res_good['scopes'][str(repo)]['last_full_green_step'])
if '__main__' == __name__:
	unittest.main()
