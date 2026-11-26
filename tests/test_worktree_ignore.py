# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
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
from agent_tools.git_gate import GitRepoGate, WorktreeCommitTransaction
from agent_tools.worktree_flow import worktree_begin, worktree_cleanup
# 2026-11-24
# "Auto-exclude worktrees_dir in enclosing repo info/exclude on worktree creation":
# https://github.com/dmitry-ai/harness/issues/201
class WorktreeIgnoreInvariantTests(unittest.TestCase):
	# @used-by :meth:`WorktreeIgnoreInvariantTests._init_meta_and_code()`
	# @used-by :meth:`WorktreeIgnoreInvariantTests.test_worktree_begin_adds_info_exclude_without_touching_gitignore_and_blocks_160000()`
	# @used-by :meth:`WorktreeIgnoreInvariantTests.test_worktree_begin_detects_previously_tracked_160000_gitlinks()`
	# @used-by :meth:`WorktreeIgnoreInvariantTests.test_worktree_commit_transaction_create_protects_enclosing_repo()`
	def _git(self, cwd: Path, *args: str, env: dict[str, str] | None=None, check: bool=True) -> subprocess.CompletedProcess:
		return subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, check=check)
	# @used-by :meth:`WorktreeIgnoreInvariantTests.test_ensure_worktree_dir_ignored_skips_exclude_edit_when_already_ignored()`
	# @used-by :meth:`WorktreeIgnoreInvariantTests.test_worktree_begin_adds_info_exclude_without_touching_gitignore_and_blocks_160000()`
	# @used-by :meth:`WorktreeIgnoreInvariantTests.test_worktree_begin_detects_previously_tracked_160000_gitlinks()`
	# @used-by :meth:`WorktreeIgnoreInvariantTests.test_worktree_commit_transaction_create_protects_enclosing_repo()`
	def _init_meta_and_code(self, root: Path, env: dict[str, str], *, v2_layout: bool=False) -> tuple[Path, Path]:
		meta = root / 'meta'
		code = (meta / '\u2c0f/\u227b/\u2655/\u26ef') if v2_layout else (meta / 'code')
		code.mkdir(parents=True)
		self._git(meta, 'init', '-b', 'main', env=env)
		self._git(meta, 'config', 'user.email', 'test@example.com', env=env)
		self._git(meta, 'config', 'user.name', 'Test', env=env)
		ignore_line = '/\u2c0f/\u227b/\u2655/\u26ef/\n' if v2_layout else '/code/\n'
		(meta / '.gitignore').write_text(ignore_line, encoding='utf-8')
		if v2_layout:
			(meta / '\ua616').mkdir(parents=True, exist_ok=True)
			(meta / '\ua616/paths.json').write_text(json.dumps({'profile': 'v2_software'}), encoding='utf-8')
		self._git(meta, 'add', '.', env=env)
		self._git(meta, 'commit', '-m', 'init meta', env=env)
		self._git(code, 'init', '-b', 'main', env=env)
		self._git(code, 'config', 'user.email', 'test@example.com', env=env)
		self._git(code, 'config', 'user.name', 'Test', env=env)
		(code / 'README.md').write_text('# Code\n', encoding='utf-8')
		self._git(code, 'add', '.', env=env)
		self._git(code, 'commit', '-m', 'init code', env=env)
		return (meta, code)
	# @used-by :meth:`WorktreeIgnoreInvariantTests.test_ensure_worktree_dir_ignored_skips_exclude_edit_when_already_ignored()`
	# @used-by :meth:`WorktreeIgnoreInvariantTests.test_worktree_begin_adds_info_exclude_without_touching_gitignore_and_blocks_160000()`
	# @used-by :meth:`WorktreeIgnoreInvariantTests.test_worktree_begin_detects_previously_tracked_160000_gitlinks()`
	# @used-by :meth:`WorktreeIgnoreInvariantTests.test_worktree_commit_transaction_create_protects_enclosing_repo()`
	def _isolated_env(self, root: Path) -> dict[str, str]:
		empty_home = root / 'empty_home'
		empty_home.mkdir(exist_ok=True)
		return {**os.environ, 'HOME': str(empty_home), 'XDG_CONFIG_HOME': '', 'GIT_CONFIG_NOSYSTEM': '1'}
	# @used-by :mod:`unittest`
	def test_ensure_worktree_dir_ignored_handles_non_git_directory(self) -> None:
		from agent_tools.git_ignore import ensure_worktree_dir_ignored
		with tempfile.TemporaryDirectory() as td:
			plain = Path(td).resolve() / 'plain_worktrees'
			res = ensure_worktree_dir_ignored(plain)
			self.assertIsNone(res['enclosing_repo'])
			self.assertFalse(res['excluded'])
			self.assertEqual(res['tracked_gitlinks'], [])
			self.assertEqual(res['warnings'], [])
	# @used-by :mod:`unittest`
	def test_ensure_worktree_dir_ignored_skips_exclude_edit_when_already_ignored(self) -> None:
		from agent_tools.git_ignore import ensure_worktree_dir_ignored
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			env = self._isolated_env(root)
			meta, _ = self._init_meta_and_code(root, env)
			(meta / '.gitignore').write_text('/code/\n\ua616/data/worktrees/\n', encoding='utf-8')
			exclude_file = meta / '.git/info/exclude'
			before_exclude = exclude_file.read_text(encoding='utf-8')
			with patch.dict(os.environ, env, clear=True):
				res = ensure_worktree_dir_ignored(meta / '\ua616/data/worktrees')
			self.assertTrue(res['already_ignored'])
			self.assertFalse(res['excluded'])
			self.assertEqual(exclude_file.read_text(encoding='utf-8'), before_exclude)
	# @used-by :mod:`unittest`
	def test_worktree_begin_adds_info_exclude_without_touching_gitignore_and_blocks_160000(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			env = self._isolated_env(root)
			meta, code = self._init_meta_and_code(root, env)
			wt_base = meta / '\ua616/data/worktrees'
			gitignore_before = (meta / '.gitignore').read_bytes()
			with patch.dict(os.environ, env, clear=True):
				first = worktree_begin(code, 'task-alpha', worktrees_dir=wt_base)
				second = worktree_begin(code, 'task-beta', worktrees_dir=wt_base)
			self.assertEqual((meta / '.gitignore').read_bytes(), gitignore_before)
			exclude_text = (meta / '.git/info/exclude').read_text(encoding='utf-8')
			self.assertEqual(1, exclude_text.splitlines().count('/\ua616/data/worktrees/'))
			self.assertTrue(first['enclosing_ignore']['excluded'])
			self.assertFalse(first['enclosing_ignore']['already_ignored'])
			self.assertTrue(second['enclosing_ignore']['already_ignored'])
			self.assertFalse(second['enclosing_ignore']['excluded'])
			chk = self._git(meta, 'check-ignore', '-v', '\ua616/data/worktrees/task-alpha', env=env, check=False)
			self.assertEqual(0, chk.returncode, chk.stdout + chk.stderr)
			add_proc = self._git(meta, 'add', '.', env=env, check=False)
			self.assertEqual(0, add_proc.returncode, add_proc.stderr)
			self.assertNotIn('adding embedded git repository', add_proc.stderr)
			self.assertNotIn('160000 ', self._git(meta, 'ls-files', '--stage', env=env).stdout)
			worktree_cleanup(code, Path(first['worktree']), force=True)
			worktree_cleanup(code, Path(second['worktree']), force=True)
	# @used-by :mod:`unittest`
	def test_worktree_begin_detects_previously_tracked_160000_gitlinks(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			env = self._isolated_env(root)
			meta, code = self._init_meta_and_code(root, env)
			wt_base = meta / '\ua616/data/worktrees'
			legacy_wt = wt_base / 'legacy-141'
			legacy_wt.mkdir(parents=True)
			self._git(legacy_wt, 'init', '-b', 'main', env=env)
			self._git(legacy_wt, 'config', 'user.email', 'test@example.com', env=env)
			self._git(legacy_wt, 'config', 'user.name', 'Test', env=env)
			(legacy_wt / 'f.txt').write_text('x\n', encoding='utf-8')
			self._git(legacy_wt, 'add', '.', env=env)
			self._git(legacy_wt, 'commit', '-m', 'legacy', env=env)
			self._git(meta, 'add', '\ua616/data/worktrees/legacy-141', env=env)
			with patch.dict(os.environ, env, clear=True):
				res = worktree_begin(code, 'task-new', worktrees_dir=wt_base)
			info = res['enclosing_ignore']
			self.assertIn('\ua616/data/worktrees/legacy-141', info['tracked_gitlinks'])
			self.assertTrue(any(('rm --cached' in w and 'legacy-141' in w for w in info['warnings'])), info)
			worktree_cleanup(code, Path(res['worktree']), force=True)
	# @used-by :mod:`unittest`
	def test_worktree_commit_transaction_create_protects_enclosing_repo(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			env = self._isolated_env(root)
			meta, code = self._init_meta_and_code(root, env, v2_layout=True)
			tx = WorktreeCommitTransaction(GitRepoGate(code), label='tx')
			with patch.dict(os.environ, env, clear=True):
				wt_dir = tx.create()
			try:
				exclude_text = (meta / '.git/info/exclude').read_text(encoding='utf-8')
				self.assertIn('/\ua616/data/worktrees/', exclude_text.splitlines())
				add_proc = self._git(meta, 'add', '.', env=env, check=False)
				self.assertEqual(0, add_proc.returncode, add_proc.stderr)
				self.assertNotIn('adding embedded git repository', add_proc.stderr)
				self.assertNotIn('160000 ', self._git(meta, 'ls-files', '--stage', env=env).stdout)
			finally:
				tx.remove(wt_dir)
if '__main__' == __name__:
	unittest.main()
