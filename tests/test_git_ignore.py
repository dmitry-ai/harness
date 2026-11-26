# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
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
from agent_tools import native_profiles as native, runtime, upwork_project as up
# 2026-11-24
# "Manage Harness ephemeral Git exclusions in install-global and doctor":
# https://github.com/dmitry-ai/harness/issues/198
class GlobalGitIgnoreTests(unittest.TestCase):
	# @used-by :meth:`GlobalGitIgnoreTests.test_real_git_ignores_embedded_worktree_via_global_ignore()`
	def _git(self, cwd: Path, *args: str, env: dict[str, str] | None=None, check: bool=True) -> subprocess.CompletedProcess:
		return subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, check=check)
	# @used-by :meth:`GlobalGitIgnoreTests.test_doctor_reports_and_validates_global_git_ignore()`
	# @used-by :meth:`GlobalGitIgnoreTests.test_install_global_check_and_apply_preserve_user_rules_and_are_idempotent()`
	# @used-by :meth:`GlobalGitIgnoreTests.test_isolated_synthetic_primary_skips_host_git_ignore_mutation()`
	def _make_primary(self, root: Path) -> tuple[Path, dict]:
		primary = root / 'harness/code'
		(primary / 'rules').mkdir(parents=True)
		(primary / 'skills/upwork-init').mkdir(parents=True)
		(primary / 'agents').mkdir(parents=True)
		(primary / 'platforms').mkdir(parents=True)
		(primary / 'rules/00-scope.md').write_text('---\ntrigger: always_on\n---\n# Scope\nUse canonical sources.  \n', encoding='utf-8')
		(primary / 'skills/upwork-init/SKILL.md').write_text('---\nname: upwork-init\ndescription: Init workflow.\n---\nBody.\n', encoding='utf-8')
		(primary / 'agents/worker.md').write_text('# Worker\n', encoding='utf-8')
		(primary / 'platforms/antigravity.md').write_text('# Antigravity\n', encoding='utf-8')
		ag_home = root / 'profiles/A0'
		(ag_home / '.gemini/config').mkdir(parents=True)
		cfg = deepcopy(runtime.settings())
		cfg['workspace_root'] = str(root / 'workspace')
		cfg['platforms'] = {'antigravity': deepcopy(cfg['platforms']['antigravity'])}
		cfg['platforms']['antigravity']['instances'] = {'A0': {'enabled': True, 'primary': True, 'home': str(ag_home)}}
		(primary / 'runtime.json').write_text(json.dumps(cfg), encoding='utf-8')
		return (primary, cfg)
	# @used-by :mod:`unittest`
	def test_doctor_reports_and_validates_global_git_ignore(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			primary, cfg = self._make_primary(root)
			ignore_file = root / 'git/ignore'
			ag_cfg = {'A0': root / 'profiles/A0/.gemini/config'}
			inst_only_ag = native.install_native_profiles(('A0',), primary=primary, config_dirs=ag_cfg, codex_homes={})
			self.assertTrue(inst_only_ag['valid'], inst_only_ag)
			with patch.object(up, 'antigravity_global_config_dirs', return_value=ag_cfg), patch.object(runtime, 'settings', return_value=cfg):
				before = up.doctor(primary=primary, git_ignore_path=ignore_file)
				self.assertFalse(before['valid'])
				self.assertFalse(before['git_ignore']['valid'])
				self.assertFalse(before['global_customizations']['valid'])
				applied = native.install_native_profiles(('A0',), primary=primary, config_dirs=ag_cfg, codex_homes={}, git_ignore_path=ignore_file)
				self.assertTrue(applied['valid'], applied)
				self.assertTrue(applied['git_ignore']['changed'])
				after = up.doctor(primary=primary, git_ignore_path=ignore_file)
				self.assertTrue(after['valid'], after)
				self.assertTrue(after['git_ignore']['valid'])
				self.assertEqual(Path(after['git_ignore']['path']).resolve(), ignore_file.resolve())
	# @used-by :mod:`unittest`
	def test_install_global_check_and_apply_preserve_user_rules_and_are_idempotent(self) -> None:
		from agent_tools.git_ignore import HARNESS_GLOBAL_IGNORE_PATTERNS
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			primary, _ = self._make_primary(root)
			ignore_file = root / 'user_home/.config/git/ignore'
			ignore_file.parent.mkdir(parents=True)
			initial = '# personal rules\n*.tmp\n.idea/\n'
			ignore_file.write_text(initial, encoding='utf-8')
			ag_cfg = {'A0': root / 'profiles/A0/.gemini/config'}
			self.assertTrue(native.install_native_profiles(('A0',), primary=primary, config_dirs=ag_cfg, codex_homes={})['valid'])
			chk_before = native.install_native_profiles(('A0',), primary=primary, check=True, config_dirs=ag_cfg, codex_homes={}, git_ignore_path=ignore_file)
			self.assertFalse(chk_before['valid'])
			self.assertFalse(chk_before['git_ignore']['valid'])
			self.assertEqual(ignore_file.read_text(encoding='utf-8'), initial)
			applied = native.install_native_profiles(('A0',), primary=primary, check=False, config_dirs=ag_cfg, codex_homes={}, git_ignore_path=ignore_file)
			self.assertTrue(applied['valid'], applied)
			self.assertTrue(applied['git_ignore']['changed'])
			text_after = ignore_file.read_text(encoding='utf-8')
			self.assertTrue(text_after.startswith(initial))
			for pat in HARNESS_GLOBAL_IGNORE_PATTERNS:
				self.assertIn(pat, text_after)
			again = native.install_native_profiles(('A0',), primary=primary, check=False, config_dirs=ag_cfg, codex_homes={}, git_ignore_path=ignore_file)
			self.assertTrue(again['valid'], again)
			self.assertFalse(again['git_ignore']['changed'])
			self.assertEqual(again['written'], [])
			self.assertEqual(ignore_file.read_text(encoding='utf-8'), text_after)
			ignore_file.write_text(text_after + 'my_trailing.bak\n', encoding='utf-8')
			preserved = native.install_native_profiles(('A0',), primary=primary, check=False, config_dirs=ag_cfg, codex_homes={}, git_ignore_path=ignore_file)
			self.assertTrue(preserved['valid'])
			self.assertIn('my_trailing.bak\n', ignore_file.read_text(encoding='utf-8'))
			self.assertTrue(native.install_native_profiles(('A0',), primary=primary, check=True, config_dirs=ag_cfg, codex_homes={}, git_ignore_path=ignore_file)['valid'])
	# @used-by :mod:`unittest`
	def test_isolated_synthetic_primary_skips_host_git_ignore_mutation(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			primary, _ = self._make_primary(root)
			fake_home = root / 'fake_home'
			fake_home.mkdir()
			ag_cfg = {'A0': root / 'profiles/A0/.gemini/config'}
			with patch.dict(os.environ, {'HOME': str(fake_home), 'XDG_CONFIG_HOME': ''}, clear=False):
				res = native.install_native_profiles(('A0',), primary=primary, config_dirs=ag_cfg, codex_homes={})
			self.assertTrue(res['valid'], res)
			self.assertTrue(res['git_ignore']['skipped'])
			self.assertFalse((fake_home / '.config/git/ignore').exists())
	# @used-by :mod:`unittest`
	def test_malformed_managed_markers_fail_without_corrupting_file(self) -> None:
		from agent_tools.git_ignore import GIT_IGNORE_START, sync_global_git_ignore
		with tempfile.TemporaryDirectory() as td:
			ignore_file = Path(td).resolve() / 'ignore'
			broken = f'*.log\n{GIT_IGNORE_START}\n\ua616/data/worktrees/\n'
			ignore_file.write_text(broken, encoding='utf-8')
			res = sync_global_git_ignore(check=False, ignore_path=ignore_file)
			self.assertFalse(res['valid'])
			self.assertTrue(res['issues'])
			self.assertEqual(ignore_file.read_text(encoding='utf-8'), broken)
	# @used-by :mod:`unittest`
	def test_real_git_ignores_embedded_worktree_via_global_ignore(self) -> None:
		from agent_tools.git_ignore import sync_global_git_ignore
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			fake_home = root / 'home'
			fake_home.mkdir()
			env = {**os.environ, 'HOME': str(fake_home), 'XDG_CONFIG_HOME': '', 'GIT_CONFIG_NOSYSTEM': '1'}
			synced = sync_global_git_ignore(check=False, env=env)
			self.assertTrue(synced['valid'], synced)
			self.assertTrue(synced['changed'])
			meta = root / 'meta'
			code = root / 'code_repo'
			meta.mkdir()
			code.mkdir()
			for repo in (meta, code):
				self._git(repo, 'init', '-b', 'main', env=env)
				self._git(repo, 'config', 'user.email', 'test@example.com', env=env)
				self._git(repo, 'config', 'user.name', 'Test', env=env)
				(repo / 'README.md').write_text('# Demo\n', encoding='utf-8')
				self._git(repo, 'add', '.', env=env)
				self._git(repo, 'commit', '-m', 'init', env=env)
			wt_dir = meta / '\ua616/data/worktrees/task-1'
			wt_dir.parent.mkdir(parents=True)
			self._git(code, 'worktree', 'add', '-b', 'task/1', str(wt_dir), 'main', env=env)
			chk = self._git(meta, 'check-ignore', '-v', '\ua616/data/worktrees/task-1', env=env, check=False)
			self.assertEqual(0, chk.returncode, chk.stdout + chk.stderr)
			add_proc = self._git(meta, 'add', '.', env=env, check=False)
			self.assertEqual(0, add_proc.returncode, add_proc.stderr)
			self.assertNotIn('adding embedded git repository', add_proc.stderr)
			stage = self._git(meta, 'ls-files', '--stage', env=env).stdout
			self.assertNotIn('160000 ', stage)
	# @used-by :mod:`unittest`
	def test_resolve_global_git_ignore_path_precedence(self) -> None:
		from agent_tools.git_ignore import resolve_global_git_ignore_path
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			fake_home = root / 'home'
			fake_xdg = root / 'xdg'
			custom = root / 'custom.gitignore'
			fake_home.mkdir()
			env_home = {**os.environ, 'HOME': str(fake_home), 'XDG_CONFIG_HOME': '', 'GIT_CONFIG_NOSYSTEM': '1'}
			self.assertEqual(resolve_global_git_ignore_path(env=env_home), (fake_home / '.config/git/ignore').resolve())
			env_xdg = {**env_home, 'XDG_CONFIG_HOME': str(fake_xdg)}
			self.assertEqual(resolve_global_git_ignore_path(env=env_xdg), (fake_xdg / 'git/ignore').resolve())
			(fake_home / '.gitconfig').write_text(f'[core]\n\texcludesFile = {custom.as_posix()}\n', encoding='utf-8')
			self.assertEqual(resolve_global_git_ignore_path(env=env_xdg), custom.resolve())
if '__main__' == __name__:
	unittest.main()
