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
HARNESS_SCRIPT = SCRIPTS_DIR / 'harness.py'
GIT_SHIM_SCRIPT = SCRIPTS_DIR / 'git_shim.py'
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :func:`_run_with_open_stdin()`
def _kill_tree(proc: subprocess.Popen) -> None:
	if None is proc.poll():
		if 'nt' == os.name:
			subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=15, creationflags=_NO_WINDOW)
		try:
			proc.kill()
		except OSError:
			pass
		try:
			proc.wait(timeout=5)
		except (OSError, subprocess.TimeoutExpired):
			pass
# @used-by :meth:`StdinDetachmentTests.test_git_shim_pre_commit_completes_under_open_stdin_pipe()`
# @used-by :meth:`StdinDetachmentTests.test_parallel_runner_detaches_inherited_open_stdin()`
# @used-by :meth:`StdinDetachmentTests.test_suite_profiler_detaches_inherited_open_stdin()`
# @used-by :meth:`StdinDetachmentTests.test_suite_runner_cli_detaches_inherited_open_stdin()`
def _run_with_open_stdin(cmd: list[str], *, cwd: Path, timeout: float=4.0, env: dict[str, str] | None=None) -> tuple[int, str, str, float, bool]:
	r_fd, w_fd = os.pipe()
	timed_out = False
	started = time.monotonic()
	proc = subprocess.Popen(cmd, cwd=str(cwd), stdin=r_fd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', env=env, creationflags=_NO_WINDOW)
	os.close(r_fd)
	try:
		out, err = proc.communicate(timeout=timeout)
		rc = proc.returncode
	except subprocess.TimeoutExpired:
		timed_out = True
		_kill_tree(proc)
		out, err, rc = ('', 'TIMEOUT', -1)
	finally:
		os.close(w_fd)
	return (rc, out, err, round(time.monotonic() - started, 3), timed_out)
# @used-by :meth:`StdinDetachmentTests.test_parallel_runner_detaches_inherited_open_stdin()`
# @used-by :meth:`StdinDetachmentTests.test_suite_profiler_detaches_inherited_open_stdin()`
# @used-by :meth:`StdinDetachmentTests.test_suite_runner_cli_detaches_inherited_open_stdin()`
def _write_stdin_probe_module(tests_dir: Path) -> Path:
	tests_dir.mkdir(parents=True, exist_ok=True)
	mod = tests_dir / 'test_probe_stdin.py'
	mod.write_text('import sys\nimport unittest\nclass ProbeTests(unittest.TestCase):\n\tdef test_reads_stdin_eof(self):\n\t\tself.assertEqual("", sys.stdin.read())\n', encoding='utf-8')
	return mod
# 2026-11-24
# "Detach inherited stdin pipes in Harness test runners and Git hook helpers":
# https://github.com/dmitry-ai/harness/issues/204
class StdinDetachmentTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_git_shim_pre_commit_completes_under_open_stdin_pipe(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			for gargs in (['init', '-b', 'main'], ['config', 'user.email', 't@example.com'], ['config', 'user.name', 'Test']):
				subprocess.run(['git', '-C', str(repo), *gargs], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=15, creationflags=_NO_WINDOW)
			(repo / 'note.txt').write_text('hello\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'note.txt'], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=15, creationflags=_NO_WINDOW)
			rc, out, err, elapsed, timed_out = _run_with_open_stdin([sys.executable, str(GIT_SHIM_SCRIPT), '--hook', 'pre-commit'], cwd=repo, timeout=4.0)
			self.assertFalse(timed_out, f'pre-commit hung on open stdin ({elapsed}s): {out}{err}')
			self.assertEqual(0, rc, out + err)
			self.assertLess(elapsed, 4.0)
	# @used-by :mod:`unittest`
	def test_parallel_runner_detaches_inherited_open_stdin(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			tdir = root / 'tests'
			_write_stdin_probe_module(tdir)
			code = f'import json, sys; sys.path.insert(0, {str(SCRIPTS_DIR)!r}); from agent_tools.parallel_runner import run_parallel_tests; print(json.dumps(run_parallel_tests({str(tdir)!r}, workers=1, module_timeout=2.0)))'
			rc, out, err, elapsed, timed_out = _run_with_open_stdin([sys.executable, '-c', code], cwd=root, timeout=5.0)
			self.assertFalse(timed_out, f'parallel_runner hung on open stdin ({elapsed}s): {out}{err}')
			self.assertEqual(0, rc, out + err)
			data = json.loads(out)
			self.assertTrue(data['ok'], data)
			self.assertEqual(1, data['total_tests'])
	# @used-by :mod:`unittest`
	def test_suite_profiler_detaches_inherited_open_stdin(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			tdir = root / 'tests'
			_write_stdin_probe_module(tdir)
			code = f'import json, sys; sys.path.insert(0, {str(SCRIPTS_DIR)!r}); from agent_tools.perf.suite_profiler import profile_test_suite; print(json.dumps(profile_test_suite({str(tdir)!r}, workers=1, module_timeout=2.0)))'
			rc, out, err, elapsed, timed_out = _run_with_open_stdin([sys.executable, '-c', code], cwd=root, timeout=5.0)
			self.assertFalse(timed_out, f'suite_profiler hung on open stdin ({elapsed}s): {out}{err}')
			self.assertEqual(0, rc, out + err)
			data = json.loads(out)
			self.assertTrue(data['valid'], data)
			self.assertEqual(1, data['total_tests'])
	# @used-by :mod:`unittest`
	def test_suite_runner_cli_detaches_inherited_open_stdin(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			tdir = root / 'tests'
			_write_stdin_probe_module(tdir)
			rc, out, err, elapsed, timed_out = _run_with_open_stdin([sys.executable, str(HARNESS_SCRIPT), 'run-tests', str(tdir), '--workers', '1', '--module-timeout', '2', '--format', 'json'], cwd=root, timeout=5.0)
			self.assertFalse(timed_out, f'run-tests hung on open stdin ({elapsed}s): {out}{err}')
			self.assertEqual(0, rc, out + err)
			data = json.loads(out)
			self.assertTrue(data['ok'], data)
			self.assertEqual(1, data['total_tests'])
if '__main__' == __name__:
	unittest.main()
