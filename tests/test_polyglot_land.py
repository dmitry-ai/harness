# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add sandboxed polyglot land tests and post-land health checks":
# https://github.com/dmitry-ai/harness/issues/304
from __future__ import annotations
from pathlib import Path
from unittest import mock
import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
WORKTREE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WORKTREE_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.issues.service import GitHubIssueService
from agent_tools.issues.workspace import IssueEvidenceWorkspace
from agent_tools.worktree_flow import worktree_begin, worktree_cleanup, worktree_land
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :class:`PolyglotLandTests`
class PolyglotLandTests(unittest.TestCase):
	# @used-by :meth:`PolyglotLandTests._init_node_repo()`
	# @used-by :meth:`PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly()`
	# @used-by :meth:`PolyglotLandTests.test_polyglot_node_repo_runs_in_workspace_sandbox_and_lands()`
	# @used-by :meth:`PolyglotLandTests.test_post_land_health_passes_ready_skips_unavailable_and_blocks_error()`
	# @used-by :meth:`PolyglotLandTests.test_worktree_land_allows_whitelisted_live_runtime_data_on_main_only()`
	def _git(self, repo: Path, *args: str) -> str:
		proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True, creationflags=_NO_WINDOW)
		return (proc.stdout or '').strip()
	# @used-by :meth:`PolyglotLandTests.test_close_blocks_on_unhealthy_repo_health_command()`
	# @used-by :meth:`PolyglotLandTests.test_host_state_mutation_fails_closed_while_heartbeat_timestamp_is_ignored()`
	# @used-by :meth:`PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly()`
	# @used-by :meth:`PolyglotLandTests.test_polyglot_node_repo_runs_in_workspace_sandbox_and_lands()`
	# @used-by :meth:`PolyglotLandTests.test_post_land_health_passes_ready_skips_unavailable_and_blocks_error()`
	# @used-by :meth:`PolyglotLandTests.test_worktree_land_allows_whitelisted_live_runtime_data_on_main_only()`
	def _init_node_repo(self, root: Path, *, slug: str='owner/node-demo', test_script: str='node --test demo.test.js') -> Path:
		proj = root / 'proj'
		repo = proj / 'code'
		repo.mkdir(parents=True)
		(proj / '\ua616/data').mkdir(parents=True)
		(repo / 'package.json').write_text(json.dumps({'name': 'demo', 'scripts': {'test': test_script}}), encoding='utf-8')
		(repo / 'demo.test.js').write_text("const test = require('node:test');\nconst assert = require('node:assert/strict');\ntest('sandboxed env', () => {\n\tassert.ok(process.env.APPDATA.includes('test-sandbox'));\n\tassert.ok(process.env.ANTIGRAVITY_TOOLS_STATE_DIR.includes('test-sandbox'));\n});\n", encoding='utf-8')
		self._git(repo, 'init', '-b', 'main')
		self._git(repo, 'config', 'user.email', 'test@example.com')
		self._git(repo, 'config', 'user.name', 'Test')
		self._git(repo, 'remote', 'add', 'origin', f'https://github.com/{slug}.git')
		self._git(repo, 'add', '.')
		self._git(repo, 'commit', '-m', 'init')
		return repo
	# @used-by :mod:`unittest`
	def test_close_blocks_on_unhealthy_repo_health_command(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_node_repo(root, slug='dmitry-ai/antigravity-addons')
			(repo / 'Upgrade').mkdir(parents=True, exist_ok=True)
			(repo / 'Upgrade/runtime-health.js').write_text("console.error('Tools runtime is not healthy');\nprocess.exit(1);\n", encoding='utf-8')
			rt_ok = root / 'ok-runtime.json'
			rt_ok.write_text(json.dumps({'state': 'connected', 'pid': os.getpid(), 'runtimePath': 'C:/work/Addons/Upgrade/cdp-companion.js', 'errors': {}}), encoding='utf-8')
			ws = IssueEvidenceWorkspace()
			svc = GitHubIssueService(api_fn=lambda *a, **kw: {'state': 'closed'}, workspace=ws)
			args = argparse.Namespace(repo='dmitry-ai/antigravity-addons', issue=75, reason='completed', comment_file=None, consume_input=False, project_root=str(repo.parent), repo_root=str(repo), target_locale='en-US')
			env_patch = {'HARNESS_COMPANION_RUNTIME_JSON': str(rt_ok), 'HARNESS_RUN_LIVE_HEALTH': '1'}
			with mock.patch.dict(os.environ, env_patch), mock.patch('agent_tools.issues.service.verify_repo_issue_ready_for_close', return_value={'verified': True}), mock.patch('agent_tools.issues.service.dump_json') as mocked_dump:
				rc = svc.cmd_close(args)
			self.assertEqual(2, rc)
			payload = mocked_dump.call_args[0][0]
			self.assertFalse(payload['ok'])
			self.assertIn('health', payload['error'].lower())
	# @used-by :mod:`unittest`
	def test_host_state_mutation_fails_closed_while_heartbeat_timestamp_is_ignored(self) -> None:
		from agent_tools.polyglot_land import run_polyglot_land_tests
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_node_repo(root)
			watched = root / 'live-runtime.json'
			watched.write_text(json.dumps({'instance': 'inst-1', 'pid': 1001, 'runtimePath': 'C:/main/cdp.js', 'version': 'v1', 'state': 'connected', 'updated': '2026-11-26T00:00:00Z', 'errors': {}}), encoding='utf-8')
			hb_cmd = [sys.executable, '-c', f"import json, pathlib; p = pathlib.Path({str(watched)!r}); d = json.loads(p.read_text()); d['updated'] = '2026-11-26T00:00:10Z'; p.write_text(json.dumps(d))"]
			spec_hb = {'test_command': hb_cmd, 'test_cwd': '.', 'watch_host_files': [str(watched)], 'timeout_seconds': 30}
			ok_hb, res_hb = run_polyglot_land_tests(repo, repo, spec=spec_hb)
			self.assertTrue(ok_hb, res_hb)
			self.assertEqual([], res_hb['mutated_host_files'])
			mut_cmd = [sys.executable, '-c', f"import json, pathlib; p = pathlib.Path({str(watched)!r}); d = json.loads(p.read_text()); d['pid'] = 9999; p.write_text(json.dumps(d))"]
			spec_mut = {'test_command': mut_cmd, 'test_cwd': '.', 'watch_host_files': [str(watched)], 'timeout_seconds': 30}
			ok_mut, res_mut = run_polyglot_land_tests(repo, repo, spec=spec_mut)
			self.assertFalse(ok_mut, res_mut)
			self.assertEqual('host_mutation', res_mut['failure_stage'])
			self.assertTrue(res_mut['mutated_host_files'])
	# @used-by :mod:`unittest`
	def test_polyglot_node_repo_runs_in_workspace_sandbox_and_lands(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_node_repo(root)
			wt = Path(worktree_begin(repo, 'node-ok', worktrees_dir=repo.parent / '\ua616/data/worktrees')['worktree'])
			(wt / 'extra.js').write_text('module.exports = 1;\n', encoding='utf-8')
			self._git(wt, 'add', 'extra.js')
			self._git(wt, 'commit', '-m', 'add extra')
			res = worktree_land(wt, run_tests=True, remove=True, owner='poly', leases_dir=root / 'leases')
			self.assertTrue(res['valid'], res)
			self.assertTrue(res['landed'])
			self.assertEqual(1, res['test_runs'])
			self.assertEqual('polyglot', res['test_result']['runner'])
			self.assertTrue((repo / 'extra.js').is_file())
			self.assertFalse((repo.parent / '\ua616/data/test-sandbox/node-ok').exists())
	# @used-by :mod:`unittest`
	def test_post_land_health_passes_ready_skips_unavailable_and_blocks_error(self) -> None:
		from agent_tools.polyglot_land import run_repo_health_check
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_node_repo(root)
			h_ready = run_repo_health_check(repo, spec={'health_command': [sys.executable, '-c', 'print(\'{"state":"ready"}\')'], 'health_ok_exit_codes': [0], 'health_skip_exit_codes': [2], 'health_skip_states': ['unavailable', 'waiting-for-sign-in']}, force=True)
			self.assertTrue(h_ready['ok'], h_ready)
			self.assertEqual('ready', h_ready['state'])
			h_skip = run_repo_health_check(repo, spec={'health_command': [sys.executable, '-c', 'import sys; print(\'{"state":"unavailable"}\'); sys.exit(2)'], 'health_ok_exit_codes': [0], 'health_skip_exit_codes': [2], 'health_skip_states': ['unavailable', 'waiting-for-sign-in']}, force=True)
			self.assertTrue(h_skip['ok'], h_skip)
			self.assertTrue(h_skip['skipped'])
			h_bad = run_repo_health_check(repo, spec={'health_command': [sys.executable, '-c', 'import sys; print("Tools runtime is not healthy", file=sys.stderr); sys.exit(1)'], 'health_ok_exit_codes': [0], 'health_skip_exit_codes': [2], 'health_skip_states': ['unavailable']}, force=True)
			self.assertFalse(h_bad['ok'], h_bad)
			wt = Path(worktree_begin(repo, 'bad-health', worktrees_dir=repo.parent / '\ua616/data/worktrees')['worktree'])
			(wt / 'bump.js').write_text('module.exports = 2;\n', encoding='utf-8')
			self._git(wt, 'add', 'bump.js')
			self._git(wt, 'commit', '-m', 'bump')
			with mock.patch('agent_tools.polyglot_land.run_repo_health_check', return_value={'ok': False, 'skipped': False, 'state': 'error', 'error': 'Tools runtime is not healthy'}):
				res = worktree_land(wt, run_tests=True, remove=True, owner='badh', leases_dir=root / 'leases')
			self.assertFalse(res['valid'])
			self.assertEqual('post_land_health', res['stage'])
			worktree_cleanup(repo, wt, force=True)
	# @used-by :mod:`unittest`
	def test_worktree_land_allows_whitelisted_live_runtime_data_on_main_only(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_node_repo(root, slug='dmitry-ai/antigravity-addons')
			(repo / 'Folders').mkdir(parents=True)
			(repo / 'Folders/folders.json').write_text('{"folders":[]}\n', encoding='utf-8')
			self._git(repo, 'add', 'Folders/folders.json')
			self._git(repo, 'commit', '-m', 'add folders')
			(repo / 'Folders/folders.json').write_text('{"folders":[{"id":"live"}]}\n', encoding='utf-8')
			wt = Path(worktree_begin(repo, 'live-folders', worktrees_dir=repo.parent / '\ua616/data/worktrees')['worktree'])
			(wt / 'safe.js').write_text('module.exports = true;\n', encoding='utf-8')
			self._git(wt, 'add', 'safe.js')
			self._git(wt, 'commit', '-m', 'safe edit')
			res = worktree_land(wt, run_tests=False, remove=True, owner='livef', leases_dir=root / 'leases')
			self.assertTrue(res['valid'], res)
			self.assertTrue(res['landed'])
			self.assertIn('live', (repo / 'Folders/folders.json').read_text(encoding='utf-8'))
	# 2026-11-26 "Handle worktree-land gate timeouts cleanly and add cross-cutting boundary regressions": https://github.com/dmitry-ai/harness/issues/365
	# @used-by :mod:`unittest`
	def test_polyglot_land_and_health_handle_subprocess_timeout_cleanly(self) -> None:
		from agent_tools.polyglot_land import run_polyglot_land_tests, run_repo_health_check
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_node_repo(root)
			spec = {'test_command': [sys.executable, '-c', 'pass'], 'test_cwd': '.', 'watch_host_files': [], 'timeout_seconds': 5}
			with mock.patch('agent_tools.polyglot_land.subprocess.run', side_effect=subprocess.TimeoutExpired(cmd=['node'], timeout=5)):
				ok_t, res_t = run_polyglot_land_tests(repo, repo, spec=spec)
			self.assertFalse(ok_t, res_t)
			self.assertTrue(res_t.get('timed_out'), res_t)
			self.assertEqual('tests', res_t['failure_stage'])
			self.assertEqual(-1, res_t['exit_code'])
			self.assertFalse((repo.parent / '\ua616/data/test-sandbox' / repo.name).exists())
			wt = Path(worktree_begin(repo, 'poly-timeout', worktrees_dir=repo.parent / '\ua616/data/worktrees')['worktree'])
			(wt / 'slow.js').write_text('module.exports = 3;\n', encoding='utf-8')
			self._git(wt, 'add', 'slow.js')
			self._git(wt, 'commit', '-m', 'add slow')
			real_run = subprocess.run
			# @used-by :meth:`PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly()`
			def _timeout_node(cmd, *args, **kwargs):
				if isinstance(cmd, (list, tuple)) and any(('demo.test.js' in str(c) for c in cmd)):
					raise subprocess.TimeoutExpired(cmd=cmd, timeout=5)
				return real_run(cmd, *args, **kwargs)
			with mock.patch('agent_tools.polyglot_land.subprocess.run', side_effect=_timeout_node):
				land = worktree_land(wt, run_tests=True, remove=False, owner='pt', leases_dir=root / 'leases')
			self.assertFalse(land['valid'], land)
			self.assertFalse(land['landed'], land)
			self.assertEqual('tests', land['stage'])
			self.assertTrue((land.get('test_result') or {}).get('timed_out'), land)
			self.assertFalse((repo.parent / '\ua616/data/test-sandbox/poly-timeout').exists())
			worktree_cleanup(repo, wt, force=True)
			with mock.patch('agent_tools.polyglot_land.subprocess.run', side_effect=subprocess.TimeoutExpired(cmd=['node'], timeout=5)):
				health = run_repo_health_check(repo, spec={'health_command': [sys.executable, '-c', 'pass']}, force=True)
			self.assertFalse(health['ok'], health)
			self.assertEqual(-1, health['exit_code'])
			self.assertEqual('error', health['state'])
if '__main__' == __name__:
	unittest.main()