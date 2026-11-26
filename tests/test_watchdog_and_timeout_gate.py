# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = HARNESS_ROOT / 'scripts'
HARNESS_SCRIPT = SCRIPTS_DIR / 'harness.py'
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
if str(SCRIPTS_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPTS_DIR))
from agent_tools import failfast_gate, tdd_gate
# @used-by :func:`_kill_pid()`
# @used-by :meth:`WatchdogAndTimeoutGateTests.test_watchdog_cli_kills_sleeping_test_and_grandchild_process_tree_on_timeout()`
def _is_pid_alive(pid: int) -> bool:
	r = False
	if 0 < pid:
		if 'nt' == os.name:
			proc = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False, timeout=15, creationflags=_NO_WINDOW)
			r = str(pid) in (proc.stdout or '')
		else:
			try:
				os.kill(pid, 0)
				r = True
			except OSError:
				r = False
	return r
# @used-by :meth:`WatchdogAndTimeoutGateTests.test_watchdog_cli_kills_sleeping_test_and_grandchild_process_tree_on_timeout()`
def _kill_pid(pid: int) -> None:
	if 0 < pid and _is_pid_alive(pid):
		if 'nt' == os.name:
			subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=15, creationflags=_NO_WINDOW)
		else:
			try:
				os.kill(pid, 9)
			except OSError:
				pass
# 2026-11-24
# "Enforce watchdog timeout and stdin isolation for unittest and pytest in failfast_gate":
# https://github.com/dmitry-ai/harness/issues/205
class WatchdogAndTimeoutGateTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_non_test_command_mentioning_pytest_in_quoted_arg_is_ignored(self) -> None:
		cmd = f'python "{SCRIPTS_DIR / "df_github_issue.py"}" create --title "Enforce timeout for unittest and pytest in failfast_gate"'
		info = tdd_gate.classify_test_command(cmd)
		self.assertFalse(info['is_test_cmd'])
		deny, overwrite = failfast_gate.evaluate_pre_tool_use_test_failfast('run_command', {'CommandLine': cmd, 'WaitMsBeforeAsync': 10000})
		self.assertIsNone(deny)
		self.assertIsNone(overwrite)
	# @used-by :mod:`unittest`
	def test_pre_tool_use_normalizes_unbounded_unittest_and_pytest_and_denies_multi_segment(self) -> None:
		u_deny, u_ov = failfast_gate.evaluate_pre_tool_use_test_failfast('run_command', {'CommandLine': 'python -m unittest -f tests/test_demo.py', 'WaitMsBeforeAsync': 10000})
		self.assertIsNone(u_deny)
		self.assertIsNotNone(u_ov)
		self.assertIn('test-watchdog', u_ov['CommandLine'])
		self.assertIn('--timeout', u_ov['CommandLine'])
		self.assertIn('-f', u_ov['CommandLine'])
		p_deny, p_ov = failfast_gate.evaluate_pre_tool_use_test_failfast('run_command', {'CommandLine': 'python -m pytest tests/test_demo.py -k test_ok -x', 'WaitMsBeforeAsync': 10000})
		self.assertIsNone(p_deny)
		self.assertIsNotNone(p_ov)
		self.assertIn('test-watchdog', p_ov['CommandLine'])
		self.assertIn('-k test_ok', p_ov['CommandLine'])
		pt_deny, pt_ov = failfast_gate.evaluate_pre_tool_use_test_failfast('run_command', {'CommandLine': 'python -m pytest tests/test_demo.py -x --timeout=60', 'WaitMsBeforeAsync': 10000})
		self.assertIsNone(pt_deny)
		self.assertIsNone(pt_ov)
		w_clean = f'python "{HARNESS_SCRIPT}" test-watchdog --timeout 60 python -m pytest tests/test_demo.py -x'
		wc_deny, wc_ov = failfast_gate.evaluate_pre_tool_use_test_failfast('run_command', {'CommandLine': w_clean, 'WaitMsBeforeAsync': 10000})
		self.assertIsNone(wc_deny)
		self.assertIsNone(wc_ov)
		w_nof = f'python "{HARNESS_SCRIPT}" test-watchdog --timeout 60 python -m pytest tests/test_demo.py'
		wn_deny, wn_ov = failfast_gate.evaluate_pre_tool_use_test_failfast('run_command', {'CommandLine': w_nof, 'WaitMsBeforeAsync': 10000})
		self.assertIsNone(wn_deny)
		self.assertIsNotNone(wn_ov)
		self.assertEqual(1, wn_ov['CommandLine'].count('test-watchdog'))
		self.assertIn('-x', wn_ov['CommandLine'])
		for multi in ('Set-Location tests; python -m unittest -f test_demo.py', 'Set-Location tests; python -m pytest test_demo.py -x', 'python -m unittest -f tests/test_demo.py > out.txt'):
			m_deny, _ = failfast_gate.evaluate_pre_tool_use_test_failfast('run_command', {'CommandLine': multi, 'WaitMsBeforeAsync': 10000})
			self.assertIsNotNone(m_deny, multi)
	# @used-by :mod:`unittest`
	def test_tdd_classify_unwraps_test_watchdog_prefix_for_scope_and_full_suite(self) -> None:
		full_w = f'python "{HARNESS_SCRIPT}" test-watchdog --timeout 300 python -m pytest -x'
		full_info = tdd_gate.classify_test_command(full_w)
		self.assertTrue(full_info['is_test_cmd'])
		self.assertTrue(full_info['is_full_suite'])
		self.assertEqual([], full_info['target_paths'])
		narrow_w = f'python "{HARNESS_SCRIPT}" test-watchdog --timeout 300 python -m pytest "D:/other/tests/test_x.py" -k foo -x'
		narrow_info = tdd_gate.classify_test_command(narrow_w)
		self.assertTrue(narrow_info['is_test_cmd'])
		self.assertFalse(narrow_info['is_full_suite'])
		self.assertEqual(['D:/other/tests/test_x.py'], narrow_info['target_paths'])
		u_disc = f'python "{HARNESS_SCRIPT}" test-watchdog --timeout 300 python -m unittest discover -f -s "D:/other/tests"'
		u_info = tdd_gate.classify_test_command(u_disc)
		self.assertTrue(u_info['is_test_cmd'])
		self.assertTrue(u_info['is_full_suite'])
	# @used-by :mod:`unittest`
	def test_watchdog_cli_detaches_open_stdin_pipe_and_preserves_exit_code(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			probe = root / 'test_stdin_ok.py'
			probe.write_text('import sys, unittest\nclass T(unittest.TestCase):\n\tdef test_eof(self):\n\t\tself.assertEqual("", sys.stdin.read())\n', encoding='utf-8')
			r_fd, w_fd = os.pipe()
			started = time.monotonic()
			proc = subprocess.Popen([sys.executable, str(HARNESS_SCRIPT), 'test-watchdog', '--timeout', '5', sys.executable, '-m', 'unittest', '-f', str(probe)], cwd=str(root), stdin=r_fd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', creationflags=_NO_WINDOW)
			os.close(r_fd)
			try:
				out, err = proc.communicate(timeout=5.0)
				rc = proc.returncode
			finally:
				os.close(w_fd)
			self.assertEqual(0, rc, out + err)
			self.assertLess(time.monotonic() - started, 4.5)
			fail_mod = root / 'test_fail_rc.py'
			fail_mod.write_text('import unittest\nclass F(unittest.TestCase):\n\tdef test_bad(self):\n\t\tself.assertEqual(1, 2)\n', encoding='utf-8')
			fproc = subprocess.run([sys.executable, str(HARNESS_SCRIPT), 'test-watchdog', '--timeout', '10', sys.executable, '-m', 'unittest', '-f', str(fail_mod)], cwd=str(root), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=False, timeout=15, creationflags=_NO_WINDOW)
			self.assertNotEqual(0, fproc.returncode)
			self.assertIn('FAILED', fproc.stdout + fproc.stderr)
	# @used-by :mod:`unittest`
	def test_watchdog_cli_kills_sleeping_test_and_grandchild_process_tree_on_timeout(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			child_pid_file = root / 'grandchild.pid'
			hang = root / 'test_sleep_tree.py'
			hang.write_text(f'from pathlib import Path\nimport subprocess, sys, time, unittest\nclass H(unittest.TestCase):\n\tdef test_hang(self):\n\t\tc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(999)"], stdin=subprocess.DEVNULL)\n\t\tPath({str(child_pid_file)!r}).write_text(str(c.pid), encoding="utf-8")\n\t\ttime.sleep(999)\n', encoding='utf-8')
			started = time.monotonic()
			proc = subprocess.run([sys.executable, str(HARNESS_SCRIPT), 'test-watchdog', '--module-timeout', '1.0', sys.executable, '-m', 'unittest', '-f', str(hang)], cwd=str(root), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=False, timeout=10, creationflags=_NO_WINDOW)
			elapsed = time.monotonic() - started
			gc_pid = int(child_pid_file.read_text(encoding='utf-8').strip()) if child_pid_file.is_file() else 0
			try:
				self.assertEqual(124, proc.returncode, proc.stdout + proc.stderr)
				self.assertIn('TIMEOUT', (proc.stdout + proc.stderr).upper())
				self.assertLess(elapsed, 6.0)
				if 0 < gc_pid:
					time.sleep(0.2)
					self.assertFalse(_is_pid_alive(gc_pid), f'Grandchild PID {gc_pid} leaked after watchdog timeout')
			finally:
				_kill_pid(gc_pid)
if '__main__' == __name__:
	unittest.main()
