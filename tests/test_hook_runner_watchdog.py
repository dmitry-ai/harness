# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# @used-by :func:`_seed_two_releases()`
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
# @used-by :meth:`HookRunnerWatchdogTests.test_watchdog_env_override_terminates_hung_child_process_and_keeps_ascii_header()`
def _is_pid_alive(pid: int) -> bool:
	r = False
	if 0 < pid:
		if 'nt' == os.name:
			import ctypes
			h = ctypes.windll.kernel32.OpenProcess(0x100000, False, pid)
			if h:
				code = ctypes.windll.kernel32.WaitForSingleObject(h, 0)
				ctypes.windll.kernel32.CloseHandle(h)
				r = 0 != code
		else:
			try:
				os.kill(pid, 0)
				r = True
			except OSError:
				r = False
	return r
# @used-by :meth:`HookRunnerWatchdogTests.test_default_watchdog_falls_back_to_lkg_on_8s_delay_within_10s()`
# @used-by :meth:`HookRunnerWatchdogTests.test_watchdog_env_override_terminates_hung_child_process_and_keeps_ascii_header()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_single_process_watchdog_and_hung_timeout_lkg_fallback()`
def _seed_two_releases(base: Path) -> tuple[Path, Path, Path, str, str]:
	from agent_tools.runtime_snapshot import harness_hook_runner_source, promote_runtime_snapshot
	repo = base / 'proj/\u2c0f/\u227b/\u2655/\u26ef'
	(repo / 'scripts/agent_tools/gates').mkdir(parents=True, exist_ok=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	(repo / 'paths.json').write_text((WT_ROOT / 'paths.json').read_text(encoding='utf-8'), encoding='utf-8')
	(repo / 'runtime.json').write_text((WT_ROOT / 'runtime.json').read_text(encoding='utf-8'), encoding='utf-8')
	(repo / 'scripts/agent_tools/__init__.py').write_text('', encoding='utf-8')
	(repo / 'scripts/agent_tools/gates/__init__.py').write_text('def discover_pre_tool_gates():\n\treturn []\n', encoding='utf-8')
	# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
	# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
	for rel in ('scripts/Df/__init__.py', 'scripts/Df/Core/lib/fs/.py', 'scripts/Df/Core/lib/git.py', 'scripts/Df/Harness/Path/CacheStore.py', 'scripts/Df/Harness/Path/PathReporter.py', 'scripts/Df/Harness/Path/ProjectPaths.py', 'scripts/Df/Harness/Path/Registry.py', 'scripts/Df/Harness/Path/SimilarProjectAuditor.py', 'scripts/Df/Harness/Path/SlotResolver.py', 'scripts/Df/Harness/lib/path_discovery.py', 'scripts/Df/Harness/lib/path_resolve.py', 'scripts/Df/Harness/lib/path_schema.py', 'scripts/Df/Harness/lib/path_state.py', 'scripts/Df/Harness/lib/path_template.py', 'scripts/Df/Harness/lib/uri.py', 'scripts/agent_tools/path_cache.py', 'scripts/agent_tools/path_registry.py', 'scripts/agent_tools/runtime_snapshot.py'):
		src = WT_ROOT / rel
		if src.is_file():
			dst = repo / rel
			dst.parent.mkdir(parents=True, exist_ok=True)
			dst.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')
	lkg_slop = 'import json\nimport sys\nsys.stdin.read()\nsys.stdout.write(json.dumps({"decision": "deny", "reason": "LKG-PREVIOUS-OK"}))\n'
	allow_src = 'import json\nimport sys\nsys.stdout.write(json.dumps({"decision": "allow"}))\n'
	(repo / 'scripts/check_markdown_slop.py').write_text(lkg_slop, encoding='utf-8')
	(repo / 'scripts/check_rules_and_server_gate.py').write_text(allow_src, encoding='utf-8')
	(repo / 'scripts/check_pre_invocation.py').write_text(allow_src, encoding='utf-8')
	(repo / 'scripts/check_stop_gate.py').write_text(allow_src, encoding='utf-8')
	(repo / 'scripts/git_shim.py').write_text('raise SystemExit(0)\n', encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'release 1')
	store = base / 'store'
	sha1 = promote_runtime_snapshot(repo, store_dir=store)['commit_sha']
	(repo / 'scripts/marker.py').write_text('V = 2\n', encoding='utf-8')
	_git(repo, 'add', 'scripts/marker.py')
	_git(repo, 'commit', '--no-verify', '-m', 'release 2')
	sha2 = promote_runtime_snapshot(repo, store_dir=store)['commit_sha']
	runner = base / 'harness_hook_runner.py'
	runner.write_text(harness_hook_runner_source(repo, store_dir=store), encoding='utf-8')
	return (repo, store, runner, sha1, sha2)
# 2026-11-25
# "Add soft watchdog timeout with LKG fallback to harness_hook_runner":
# https://github.com/dmitry-ai/harness/issues/252
class HookRunnerWatchdogTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_default_watchdog_falls_back_to_lkg_on_8s_delay_within_10s(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			_, store, runner, sha1, sha2 = _seed_two_releases(Path(td).resolve())
			(store / 'releases' / sha2 / 'scripts/check_markdown_slop.py').write_text('import time\ntime.sleep(8.0)\n', encoding='utf-8')
			payload = json.dumps({'toolCall': {'name': 'write_file', 'args': {'Path': 'x.md', 'Content': 'ok'}}})
			t0 = time.perf_counter()
			proc = subprocess.run([sys.executable, str(runner), 'check_markdown_slop.py'], input=payload, text=True, encoding='utf-8', capture_output=True, timeout=15, check=False)
			elapsed = time.perf_counter() - t0
			self.assertEqual(0, proc.returncode, proc.stderr)
			self.assertLess(elapsed, 9.5, f'Watchdog fallback took {elapsed:.2f}s (expected < 9.5s)')
			self.assertEqual('LKG-PREVIOUS-OK', json.loads(proc.stdout)['reason'])
			self.assertIn('TimeoutError', proc.stderr)
			fb_log = (store / 'fallback.log').read_text(encoding='utf-8')
			self.assertIn('TimeoutError', fb_log)
			self.assertIn(sha1, fb_log)
			self.assertIn(sha2, fb_log)
	# @used-by :mod:`unittest`
	def test_watchdog_env_override_terminates_hung_child_process_and_keeps_ascii_header(self) -> None:
		from agent_tools.runtime_launchers import HOOK_RUNNER_HEADER, harness_hook_runner_source
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			repo, store, runner, sha1, sha2 = _seed_two_releases(base)
			src = harness_hook_runner_source(repo, store_dir=store)
			self.assertTrue(src.startswith(HOOK_RUNNER_HEADER))
			self.assertTrue(src.isascii())
			pid_file = base / 'hung.pid'
			(store / 'releases' / sha2 / 'scripts/check_markdown_slop.py').write_text(f'import os, pathlib, time\npathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()), encoding="utf-8")\ntime.sleep(30.0)\n', encoding='utf-8')
			env = {**os.environ, 'HARNESS_HOOK_WATCHDOG_SECONDS': '0.6'}
			t0 = time.perf_counter()
			proc = subprocess.run([sys.executable, str(runner), 'check_markdown_slop.py'], input='{}', text=True, encoding='utf-8', capture_output=True, env=env, timeout=10, check=False)
			elapsed = time.perf_counter() - t0
			self.assertEqual(0, proc.returncode, proc.stderr)
			self.assertLess(elapsed, 4.0)
			self.assertEqual('LKG-PREVIOUS-OK', json.loads(proc.stdout)['reason'])
			self.assertTrue(pid_file.is_file())
			hung_pid = int(pid_file.read_text(encoding='utf-8').strip())
			time.sleep(0.1)
			self.assertFalse(_is_pid_alive(hung_pid), f'Hung child PID {hung_pid} was not terminated')
			self.assertIn(sha1, (store / 'fallback.log').read_text(encoding='utf-8'))
if '__main__' == __name__:
	unittest.main()
