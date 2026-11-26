# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = HARNESS_ROOT / 'scripts'
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
if str(SCRIPTS_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPTS_DIR))
# @used-by :meth:`SubprocessHygieneAndTreeKillTests.test_pre_commit_and_pre_tool_use_enforce_subprocess_hygiene_ratchet()`
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=15, creationflags=_NO_WINDOW)
# @used-by :func:`_kill_pid()`
# @used-by :meth:`SubprocessHygieneAndTreeKillTests.test_parallel_runner_kills_grandchild_holding_stdout_on_timeout()`
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
# @used-by :meth:`SubprocessHygieneAndTreeKillTests.test_parallel_runner_kills_grandchild_holding_stdout_on_timeout()`
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
# "Unify process-tree termination in parallel_runner and enforce AST subprocess hygiene in pre-commit":
# https://github.com/dmitry-ai/harness/issues/206
class SubprocessHygieneAndTreeKillTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_ast_hygiene_flags_unguarded_subprocess_in_tests_and_launchers_with_ratchet(self) -> None:
		from agent_tools.subprocess_hygiene_gate import check_subprocess_hygiene_violations
		bad_test = 'import subprocess, sys\ndef run_it():\n\treturn subprocess.run([sys.executable, "-c", "pass"], capture_output=True)\n'
		errs_test = check_subprocess_hygiene_violations('tests/test_new_case.py', bad_test)
		self.assertEqual(2, len(errs_test), errs_test)
		self.assertTrue(any('stdin' in e for e in errs_test), errs_test)
		self.assertTrue(any('timeout' in e for e in errs_test), errs_test)
		bad_launcher = 'from subprocess import Popen\ndef launch(cmd):\n\treturn Popen(cmd)\n'
		errs_launch = check_subprocess_hygiene_violations('scripts/agent_tools/runtime_launchers.py', bad_launcher)
		self.assertEqual(1, len(errs_launch), errs_launch)
		self.assertIn('stdin', errs_launch[0])
		explicit_none = 'import subprocess\nsubprocess.run(["echo"], stdin=None, timeout=None)\n'
		self.assertEqual(2, len(check_subprocess_hygiene_violations('tests/test_none.py', explicit_none)))
		good_src = 'import subprocess\nsubprocess.run(["echo"], stdin=subprocess.DEVNULL, timeout=10)\nsubprocess.run(["echo"], input=b"", timeout=10)\nsubprocess.Popen(["echo"], stdin=subprocess.DEVNULL)\n'
		self.assertEqual([], check_subprocess_hygiene_violations('tests/test_ok.py', good_src))
		self.assertEqual([], check_subprocess_hygiene_violations('scripts/agent_tools/notes_helper.py', bad_test))
		legacy_edited = bad_test + 'X = 1\n'
		self.assertEqual([], check_subprocess_hygiene_violations('tests/test_legacy.py', legacy_edited, baseline_source=bad_test))
		legacy_worse = bad_test + 'def run_two():\n\treturn subprocess.run(["echo"], capture_output=True)\n'
		self.assertEqual(2, len(check_subprocess_hygiene_violations('tests/test_legacy.py', legacy_worse, baseline_source=bad_test)))
	# @used-by :mod:`unittest`
	def test_parallel_runner_kills_grandchild_holding_stdout_on_timeout(self) -> None:
		from agent_tools.parallel_runner import run_parallel_tests
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			parent_pid_file = root / 'parent.pid'
			child_pid_file = root / 'grandchild.pid'
			mod = root / 'test_orphan_tree.py'
			mod.write_text(f'from pathlib import Path\nimport os, subprocess, sys, time, unittest\nclass OrphanTests(unittest.TestCase):\n\tdef test_spawn_and_hang(self):\n\t\tPath({str(parent_pid_file)!r}).write_text(str(os.getpid()), encoding="utf-8")\n\t\tgc = subprocess.Popen([sys.executable, "-c", "import time; print(123, flush=True); time.sleep(60)"], stdin=subprocess.DEVNULL)\n\t\tPath({str(child_pid_file)!r}).write_text(str(gc.pid), encoding="utf-8")\n\t\ttime.sleep(60)\n', encoding='utf-8')
			started = time.monotonic()
			res = run_parallel_tests(root, workers=1, failfast=True, module_timeout=1.0)
			elapsed = time.monotonic() - started
			p_pid = int(parent_pid_file.read_text(encoding='utf-8').strip()) if parent_pid_file.is_file() else 0
			gc_pid = int(child_pid_file.read_text(encoding='utf-8').strip()) if child_pid_file.is_file() else 0
			try:
				self.assertFalse(res['ok'], res)
				self.assertTrue(res['timed_out'], res)
				self.assertLess(elapsed, 3.0, res)
				time.sleep(0.2)
				if 0 < p_pid:
					self.assertFalse(_is_pid_alive(p_pid), f'Worker PID {p_pid} survived module_timeout')
				self.assertGreater(gc_pid, 0, 'Expected test worker to spawn grandchild before timeout')
				self.assertFalse(_is_pid_alive(gc_pid), f'Grandchild PID {gc_pid} leaked after parallel_runner timeout')
			finally:
				_kill_pid(gc_pid)
				_kill_pid(p_pid)
	# @used-by :mod:`unittest`
	def test_pre_commit_and_pre_tool_use_enforce_subprocess_hygiene_ratchet(self) -> None:
		from agent_tools.git_gate import GitRepoGate
		from agent_tools.subprocess_hygiene_gate import evaluate_pre_tool_use_subprocess_hygiene
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			_git(repo, 'init', '-b', 'main')
			_git(repo, 'config', 'user.email', 'test@example.com')
			_git(repo, 'config', 'user.name', 'Test')
			(repo / 'tests').mkdir()
			legacy_body = '# https://github.com/dmitry-ai/harness/issues/206\nimport subprocess, unittest\nclass Legacy(unittest.TestCase):\n\tdef test_old(self):\n\t\tsubprocess.run(["echo", "ok"], capture_output=True)\n\t\tself.assertTrue(True)\n'
			(repo / 'tests/test_legacy.py').write_text(legacy_body, encoding='utf-8')
			_git(repo, 'add', 'tests/test_legacy.py')
			_git(repo, 'commit', '-m', 'init')
			bad_body = '# https://github.com/dmitry-ai/harness/issues/206\nimport subprocess, unittest\nclass Bad(unittest.TestCase):\n\tdef test_bad(self):\n\t\tsubprocess.run(["echo", "bad"], capture_output=True)\n\t\tself.assertTrue(True)\n'
			(repo / 'tests/test_bad.py').write_text(bad_body, encoding='utf-8')
			_git(repo, 'add', 'tests/test_bad.py')
			gate = GitRepoGate(repo)
			with self.assertRaises(ValueError) as ctx:
				gate.verify_subprocess_hygiene(['tests/test_bad.py'], use_index=True)
			self.assertIn('SUBPROCESS-HYGIENE', str(ctx.exception))
			good_body = bad_body.replace('capture_output=True)', 'stdin=subprocess.DEVNULL, capture_output=True, timeout=10)')
			(repo / 'tests/test_bad.py').write_text(good_body, encoding='utf-8')
			_git(repo, 'add', 'tests/test_bad.py')
			gate.verify_subprocess_hygiene(['tests/test_bad.py'], use_index=True)
			(repo / 'tests/test_legacy.py').write_text(legacy_body + '# comment\n', encoding='utf-8')
			_git(repo, 'add', 'tests/test_legacy.py')
			gate.verify_subprocess_hygiene(['tests/test_legacy.py'], use_index=True)
			deny_err = evaluate_pre_tool_use_subprocess_hygiene('write_file', {'Path': str(repo / 'tests/test_new_bad.py'), 'Content': bad_body}, {'cwd': str(repo)})
			self.assertIsNotNone(deny_err)
			self.assertIn('SUBPROCESS-HYGIENE', deny_err)
			allow_err = evaluate_pre_tool_use_subprocess_hygiene('write_file', {'Path': str(repo / 'tests/test_new_good.py'), 'Content': good_body}, {'cwd': str(repo)})
			self.assertIsNone(allow_err)
if '__main__' == __name__:
	unittest.main()
