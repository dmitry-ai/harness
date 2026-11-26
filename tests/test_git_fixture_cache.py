# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Cache template Git repositories and in-process CLI helpers in slow test fixtures": https://github.com/dmitry-ai/harness/issues/355
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import os
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
# @used-by :meth:`GitFixtureCacheTests.test_clone_template_bare_repo_caches_init_and_supports_push()`
# @used-by :meth:`GitFixtureCacheTests.test_clone_template_git_repo_caches_init_and_isolates_clones()`
def _git_out(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=30, check=True)
	return (proc.stdout or '').strip()
class GitFixtureCacheTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_clone_template_bare_repo_caches_init_and_supports_push(self) -> None:
		import git_fixture_cache
		branch = 'bare-cache-test'
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			bare_a = base / 'bare_a.git'
			bare_b = base / 'bare_b.git'
			with patch('git_fixture_cache.subprocess.run', wraps=subprocess.run) as spy:
				res_a = git_fixture_cache.clone_template_bare_repo(bare_a, initial_branch=branch)
				res_b = git_fixture_cache.clone_template_bare_repo(bare_b, initial_branch=branch)
				self.assertEqual(1, spy.call_count)
			self.assertEqual(bare_a, res_a)
			self.assertEqual(bare_b, res_b)
			self.assertEqual('true', _git_out(bare_a, 'rev-parse', '--is-bare-repository'))
			self.assertEqual('true', _git_out(bare_b, 'rev-parse', '--is-bare-repository'))
			work = git_fixture_cache.clone_template_git_repo(base / 'work', initial_branch=branch, remote_url='https://github.com/acme/demo.git', push_url=bare_a.as_posix())
			(work / 'hello.txt').write_text('hi\n', encoding='utf-8')
			_git_out(work, 'add', 'hello.txt')
			_git_out(work, 'commit', '-m', 'init')
			_git_out(work, 'push', '-u', 'origin', branch)
			self.assertEqual(branch, _git_out(bare_a, 'rev-parse', '--abbrev-ref', 'HEAD'))
			self.assertNotEqual('', _git_out(bare_a, 'rev-parse', f'refs/heads/{branch}'))
			self.assertEqual('', _git_out(bare_b, 'branch', '--list'))
	# @used-by :mod:`unittest`
	def test_clone_template_git_repo_caches_init_and_isolates_clones(self) -> None:
		import git_fixture_cache
		branch = 'work-cache-test'
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			repo_a = base / 'repo_a'
			repo_b = base / 'repo_b'
			with patch('git_fixture_cache.subprocess.run', wraps=subprocess.run) as spy:
				out_a = git_fixture_cache.clone_template_git_repo(repo_a, initial_branch=branch)
				out_b = git_fixture_cache.clone_template_git_repo(repo_b, initial_branch=branch, remote_url='https://github.com/owner/demo.git', push_url=(base / 'push.git').as_posix())
				self.assertEqual(1, spy.call_count)
			self.assertEqual(repo_a, out_a)
			self.assertEqual(repo_b, out_b)
			self.assertEqual('test@example.com', _git_out(repo_a, 'config', '--local', '--get', 'user.email'))
			self.assertEqual('Test User', _git_out(repo_a, 'config', '--local', '--get', 'user.name'))
			self.assertEqual('https://github.com/owner/demo.git', _git_out(repo_b, 'remote', 'get-url', 'origin'))
			self.assertEqual((base / 'push.git').as_posix(), _git_out(repo_b, 'remote', 'get-url', '--push', 'origin'))
			(repo_a / 'only_a.txt').write_text('a\n', encoding='utf-8')
			_git_out(repo_a, 'add', 'only_a.txt')
			_git_out(repo_a, 'commit', '-m', 'only a')
			self.assertFalse((repo_b / 'only_a.txt').exists())
			self.assertEqual('', _git_out(repo_b, 'status', '--porcelain'))
	# @used-by :mod:`unittest`
	def test_run_harness_inprocess_executes_cli_isolates_env_cwd_and_clears_caches(self) -> None:
		from agent_tools import path_cache
		import git_fixture_cache
		orig_cwd = os.getcwd()
		orig_sentinel = os.environ.get('HARNESS_INPROC_TEST_SENTINEL')
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			iso_home = base / 'iso_home'
			sub_dir = base / 'workdir'
			iso_home.mkdir()
			sub_dir.mkdir()
			iso_env = {**os.environ, 'USERPROFILE': str(iso_home), 'HOME': str(iso_home), 'APPDATA': str(iso_home / 'AppData/Roaming'), 'HARNESS_INPROC_TEST_SENTINEL': 'inside'}
			with patch('agent_tools.path_cache.clear_path_cache', wraps=path_cache.clear_path_cache) as clear_spy:
				proc = git_fixture_cache.run_harness_inprocess(['paths', '--expand', '${ENV:USERPROFILE}/demo'], cwd=sub_dir, env=iso_env)
			self.assertEqual(0, proc.returncode, proc.stderr)
			self.assertEqual(['harness.py', 'paths', '--expand', '${ENV:USERPROFILE}/demo'], proc.args)
			payload = json.loads(proc.stdout)
			self.assertEqual(f'{iso_home.as_posix()}/demo', payload['expanded'])
			self.assertGreaterEqual(clear_spy.call_count, 2)
			self.assertEqual(orig_cwd, os.getcwd())
			self.assertEqual(orig_sentinel, os.environ.get('HARNESS_INPROC_TEST_SENTINEL'))
	# @used-by :mod:`unittest`
	def test_run_harness_inprocess_restores_env_and_cwd_on_system_exit_and_exception(self) -> None:
		from agent_tools import path_cache
		import git_fixture_cache
		orig_cwd = os.getcwd()
		orig_sentinel = os.environ.get('HARNESS_INPROC_ERR_SENTINEL')
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			sub_dir = base / 'err_cwd'
			sub_dir.mkdir()
			iso_env = {**os.environ, 'HARNESS_INPROC_ERR_SENTINEL': 'temporary'}
			help_proc = git_fixture_cache.run_harness_inprocess(['--help'], cwd=sub_dir, env=iso_env)
			self.assertEqual(0, help_proc.returncode)
			self.assertIn('usage:', help_proc.stdout.lower())
			self.assertEqual(orig_cwd, os.getcwd())
			self.assertEqual(orig_sentinel, os.environ.get('HARNESS_INPROC_ERR_SENTINEL'))
			bad_proc = git_fixture_cache.run_harness_inprocess(['no-such-harness-command'], cwd=sub_dir, env=iso_env)
			self.assertEqual(2, bad_proc.returncode)
			self.assertNotEqual('', bad_proc.stderr)
			self.assertEqual(orig_cwd, os.getcwd())
			self.assertEqual(orig_sentinel, os.environ.get('HARNESS_INPROC_ERR_SENTINEL'))
			with patch('agent_tools.path_cache.clear_path_cache', wraps=path_cache.clear_path_cache) as clear_spy:
				with patch('agent_tools.upwork_project.main', side_effect=RuntimeError('boom')):
					with self.assertRaisesRegex(RuntimeError, 'boom'):
						git_fixture_cache.run_harness_inprocess(['doctor'], cwd=sub_dir, env=iso_env)
			self.assertGreaterEqual(clear_spy.call_count, 2)
			self.assertEqual(orig_cwd, os.getcwd())
			self.assertEqual(orig_sentinel, os.environ.get('HARNESS_INPROC_ERR_SENTINEL'))
if '__main__' == __name__:
	unittest.main()
