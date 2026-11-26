# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
HARNESS_SCRIPT = SCRIPT_DIR / 'harness.py'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools import tdd_gate
# @used-by :meth:`ParallelTestRunnerTests.test_fail_fast_cancels_slow_sibling_processes_quickly()`
# @used-by :meth:`ParallelTestRunnerTests.test_module_timeout_terminates_hung_worker_and_fails_fast()`
def _is_pid_alive(pid: int) -> bool:
	r = False
	if 0 < pid:
		if 'nt' == os.name:
			proc = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True, check=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
			r = str(pid) in (proc.stdout or '')
		else:
			try:
				os.kill(pid, 0)
				r = True
			except OSError:
				r = False
	return r
# 2026-11-23
# "Add parallel fail-fast run-tests runner with module timeouts and TDD gate registration":
# https://github.com/dmitry-ai/harness/issues/160
class ParallelTestRunnerTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_classify_test_command_recognizes_harness_run_tests_full_and_filtered(self) -> None:
		full_cmd = f'python "{HARNESS_SCRIPT}" run-tests "C:/demo/tests" --workers 4 --module-timeout 120'
		full_info = tdd_gate.classify_test_command(full_cmd)
		self.assertTrue(full_info['is_test_cmd'])
		self.assertTrue(full_info['is_full_suite'])
		wild_cmd = f'python "{HARNESS_SCRIPT}" run-tests "C:/demo/tests" -p "test_*.py"'
		wild_info = tdd_gate.classify_test_command(wild_cmd)
		self.assertTrue(wild_info['is_test_cmd'])
		self.assertTrue(wild_info['is_full_suite'])
		mod_cmd = f'python "{HARNESS_SCRIPT}" run-tests "C:/demo/tests" --module test_alpha.py'
		mod_info = tdd_gate.classify_test_command(mod_cmd)
		self.assertTrue(mod_info['is_test_cmd'])
		self.assertFalse(mod_info['is_full_suite'])
		pat_cmd = f'python "{HARNESS_SCRIPT}" run-tests "C:/demo/tests" -p test_alpha.py'
		pat_info = tdd_gate.classify_test_command(pat_cmd)
		self.assertTrue(pat_info['is_test_cmd'])
		self.assertFalse(pat_info['is_full_suite'])
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve()
			(repo / 'tests').mkdir()
			(repo / 'tests/test_a.py').write_text('import unittest\n', encoding='utf-8')
			(repo / 'tests/test_b.py').write_text('import unittest\n', encoding='utf-8')
			(repo / 'app.py').write_text('x = 1\n', encoding='utf-8')
			events = [
				tdd_gate.build_file_write_tdd_event(1, repo / 'tests/test_a.py'),
				tdd_gate.build_command_tdd_event(2, f'python "{HARNESS_SCRIPT}" run-tests "{repo / "tests"}" --module test_a.py', 'Command exited with code 1.\n\nCommand output:\nFAILED (failures=1)\n', cwd=repo),
				tdd_gate.build_file_write_tdd_event(3, repo / 'app.py'),
				tdd_gate.build_command_tdd_event(4, f'python "{HARNESS_SCRIPT}" run-tests "{repo / "tests"}"', 'Command exited with code 0.\n\nCommand output:\nRan 2 tests in 0.25s\n\nOK\n', cwd=repo),
			]
			res = tdd_gate.evaluate_tdd_events(events, require_final_full_green=True)
			self.assertTrue(res['verified'], res)
			self.assertEqual(res['scopes'][str(repo)]['last_full_green_step'], 4)
	# @used-by :mod:`unittest`
	def test_cli_run_tests_executes_modules_in_parallel_with_lpt_ordering(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			tdir = Path(tmp).resolve() / 'tests'
			tdir.mkdir()
			pad = '# ' + ('x' * 500) + '\n'
			(tdir / 'test_heavy.py').write_text(pad * 8 + 'import time, unittest\nclass Heavy(unittest.TestCase):\n\tdef test_h(self):\n\t\ttime.sleep(0.5)\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
			(tdir / 'test_small_a.py').write_text('import time, unittest\nclass SmallA(unittest.TestCase):\n\tdef test_a(self):\n\t\ttime.sleep(0.5)\n\t\tself.assertEqual(2, 2)\n', encoding='utf-8')
			(tdir / 'test_small_b.py').write_text('import time, unittest\nclass SmallB(unittest.TestCase):\n\tdef test_b(self):\n\t\ttime.sleep(0.5)\n\t\tself.assertEqual(3, 3)\n', encoding='utf-8')
			started = time.monotonic()
			proc = subprocess.run([sys.executable, str(HARNESS_SCRIPT), 'run-tests', str(tdir), '--workers', '3', '--format', 'json'], capture_output=True, text=True, encoding='utf-8', check=False)
			elapsed = time.monotonic() - started
			self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
			data = json.loads(proc.stdout)
			self.assertTrue(data['ok'])
			self.assertEqual(data['total_modules'], 3)
			self.assertEqual(data['passed_modules'], 3)
			self.assertEqual(data['total_tests'], 3)
			self.assertEqual(data['scheduled_order'][0], 'test_heavy.py')
			self.assertLess(elapsed, 4.0)
	# @used-by :mod:`unittest`
	def test_fail_fast_cancels_slow_sibling_processes_quickly(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			tdir = Path(tmp).resolve() / 'tests'
			tdir.mkdir()
			pid_file = Path(tmp).resolve() / 'slow.pid'
			(tdir / 'test_fast_fail.py').write_text('import unittest\nclass FastFail(unittest.TestCase):\n\tdef test_fail(self):\n\t\tself.assertEqual(1, 2)\n', encoding='utf-8')
			(tdir / 'test_slow_sibling.py').write_text(f'import os, time, unittest\nfrom pathlib import Path\nclass Slow(unittest.TestCase):\n\tdef test_wait(self):\n\t\tPath({str(pid_file)!r}).write_text(str(os.getpid()), encoding="utf-8")\n\t\ttime.sleep(20)\n\t\tself.assertTrue(True)\n', encoding='utf-8')
			started = time.monotonic()
			proc = subprocess.run([sys.executable, str(HARNESS_SCRIPT), 'run-tests', str(tdir), '--workers', '2'], capture_output=True, text=True, encoding='utf-8', check=False)
			elapsed = time.monotonic() - started
			self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
			self.assertLess(elapsed, 3.0)
			self.assertIn('FAILED', proc.stdout + proc.stderr)
			if pid_file.is_file():
				time.sleep(0.2)
				self.assertFalse(_is_pid_alive(int(pid_file.read_text(encoding='utf-8').strip())))
	# @used-by :mod:`unittest`
	def test_module_timeout_terminates_hung_worker_and_fails_fast(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			tdir = Path(tmp).resolve() / 'tests'
			tdir.mkdir()
			pid_file = Path(tmp).resolve() / 'hung.pid'
			(tdir / 'test_hung.py').write_text(f'import os, time, unittest\nfrom pathlib import Path\nclass Hung(unittest.TestCase):\n\tdef test_hang(self):\n\t\tPath({str(pid_file)!r}).write_text(str(os.getpid()), encoding="utf-8")\n\t\ttime.sleep(20)\n\t\tself.assertTrue(True)\n', encoding='utf-8')
			started = time.monotonic()
			proc = subprocess.run([sys.executable, str(HARNESS_SCRIPT), 'run-tests', str(tdir), '--workers', '2', '--module-timeout', '0.6'], capture_output=True, text=True, encoding='utf-8', check=False)
			elapsed = time.monotonic() - started
			self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
			self.assertLess(elapsed, 4.0)
			self.assertIn('TIMEOUT', (proc.stdout + proc.stderr).upper())
			if pid_file.is_file():
				time.sleep(0.2)
				self.assertFalse(_is_pid_alive(int(pid_file.read_text(encoding='utf-8').strip())))
	# @used-by :mod:`unittest`
	def test_no_failfast_collects_all_module_failures(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			tdir = Path(tmp).resolve() / 'tests'
			tdir.mkdir()
			(tdir / 'test_one.py').write_text('import unittest\nclass One(unittest.TestCase):\n\tdef test_1(self):\n\t\tself.assertEqual(1, 2)\n', encoding='utf-8')
			(tdir / 'test_two.py').write_text('import unittest\nclass Two(unittest.TestCase):\n\tdef test_2(self):\n\t\tself.assertEqual(3, 4)\n', encoding='utf-8')
			proc = subprocess.run([sys.executable, str(HARNESS_SCRIPT), 'run-tests', str(tdir), '--workers', '2', '--no-failfast', '--format', 'json'], capture_output=True, text=True, encoding='utf-8', check=False)
			self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
			data = json.loads(proc.stdout)
			self.assertFalse(data['ok'])
			self.assertEqual(data['failed_modules'], 2)
	# @used-by :mod:`unittest`
	def test_linked_worktree_scope_accepts_full_suite_green_on_main_repo(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			main_repo = base / 'main_repo'
			wt_repo = base / 'wt_repo'
			main_repo.mkdir()
			subprocess.run(['git', 'init', str(main_repo)], check=True, capture_output=True)
			subprocess.run(['git', '-C', str(main_repo), 'config', 'user.email', 'test@example.com'], check=True, capture_output=True)
			subprocess.run(['git', '-C', str(main_repo), 'config', 'user.name', 'Test'], check=True, capture_output=True)
			(main_repo / 'tests').mkdir()
			(main_repo / 'tests/test_a.py').write_text('import unittest\n', encoding='utf-8')
			(main_repo / 'tests/test_b.py').write_text('import unittest\n', encoding='utf-8')
			(main_repo / 'app.py').write_text('x = 1\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(main_repo), 'add', '.'], check=True, capture_output=True)
			subprocess.run(['git', '-C', str(main_repo), 'commit', '-m', 'init'], check=True, capture_output=True)
			subprocess.run(['git', '-C', str(main_repo), 'worktree', 'add', '-b', 'feat', str(wt_repo)], check=True, capture_output=True)
			try:
				events = [
					tdd_gate.build_file_write_tdd_event(1, wt_repo / 'tests/test_a.py'),
					tdd_gate.build_command_tdd_event(2, f'python "{HARNESS_SCRIPT}" run-tests "{wt_repo / "tests"}" --module test_a.py', 'Command exited with code 1.\n\nCommand output:\nFAILED (failures=1)\n', cwd=wt_repo),
					tdd_gate.build_file_write_tdd_event(3, wt_repo / 'app.py'),
					tdd_gate.build_command_tdd_event(4, f'git -C "{wt_repo}" commit -m https://github.com/dmitry-ai/harness/issues/160', 'Command exited with code 0.\n\nCommand output:\n[feat 1111111] ok\n', cwd=wt_repo),
					tdd_gate.build_command_tdd_event(5, f'python "{HARNESS_SCRIPT}" run-tests "{main_repo / "tests"}"', 'Command exited with code 0.\n\nCommand output:\nRan 2 tests in 0.2s\n\nOK\n', cwd=main_repo),
				]
				res = tdd_gate.evaluate_tdd_events(events, require_final_full_green=True)
				self.assertTrue(res['verified'], res)
				self.assertEqual(res['scopes'][str(wt_repo.resolve())]['last_full_green_step'], 5)
			finally:
				subprocess.run(['git', '-C', str(main_repo), 'worktree', 'remove', '--force', str(wt_repo)], check=False, capture_output=True)
if '__main__' == __name__:
	unittest.main()
