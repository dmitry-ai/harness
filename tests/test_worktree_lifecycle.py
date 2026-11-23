# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Remove landed worktrees by default and flag stale worktrees in worktree-status":
# https://github.com/dmitry-ai/harness/issues/203
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
WORKTREE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WORKTREE_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.upwork_project import main as cli_main
from agent_tools.worktree_flow import worktree_begin, worktree_cleanup, worktree_land, worktree_status
class WorktreeLifecycleTests(unittest.TestCase):
	def _git(self, repo: Path, *args: str) -> str:
		proc = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
		return (proc.stdout or '').strip()
	def _init_repo(self, root: Path) -> Path:
		repo = root / 'repo'
		repo.mkdir(parents=True)
		self._git(repo, 'init', '-b', 'main')
		self._git(repo, 'config', 'user.email', 'test@example.com')
		self._git(repo, 'config', 'user.name', 'Test')
		(repo / 'README.md').write_text('# Demo\n', encoding='utf-8')
		tdir = repo / 'tests'
		tdir.mkdir()
		(tdir / 'test_ok.py').write_text('import unittest\nclass OkT(unittest.TestCase):\n\tdef test_ok(self):\n\t\tself.assertTrue(True)\n', encoding='utf-8')
		self._git(repo, 'add', '.')
		self._git(repo, 'commit', '-m', 'init')
		return repo
	def test_cli_worktree_land_default_removes_and_keep_preserves(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_repo(root)
			wt_base = root / 'wts'
			wt_def = Path(worktree_begin(repo, 'cli-default', worktrees_dir=wt_base)['worktree'])
			(wt_def / 'def.txt').write_text('default\n', encoding='utf-8')
			self._git(wt_def, 'add', 'def.txt')
			self._git(wt_def, 'commit', '-m', 'default remove')
			self.assertEqual(0, cli_main(['worktree-land', str(wt_def), '--no-tests']))
			self.assertFalse(wt_def.exists())
			self.assertTrue((repo / 'def.txt').is_file())
			wt_keep = Path(worktree_begin(repo, 'cli-keep', worktrees_dir=wt_base)['worktree'])
			(wt_keep / 'keep.txt').write_text('keep\n', encoding='utf-8')
			self._git(wt_keep, 'add', 'keep.txt')
			self._git(wt_keep, 'commit', '-m', 'keep worktree')
			self.assertEqual(1, cli_main(['worktree-land', str(wt_keep), '--no-tests', '--keep', '--remove']))
			self.assertEqual(0, cli_main(['worktree-land', str(wt_keep), '--no-tests', '--keep']))
			self.assertTrue(wt_keep.is_dir())
			self.assertTrue((repo / 'keep.txt').is_file())
			worktree_cleanup(repo, wt_keep, force=True)
	def test_worktree_land_removes_worktree_and_branch_by_default(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_repo(root)
			wt_base = root / 'wts'
			leases = root / 'leases'
			wt = Path(worktree_begin(repo, 'auto-clean', worktrees_dir=wt_base)['worktree'])
			(wt / 'one.txt').write_text('one\n', encoding='utf-8')
			self._git(wt, 'add', 'one.txt')
			self._git(wt, 'commit', '-m', 'add one')
			res = worktree_land(wt, run_tests=True, owner='auto', leases_dir=leases)
			self.assertTrue(res['landed'], res)
			self.assertTrue(res['removed'], res)
			self.assertFalse(wt.exists())
			self.assertNotIn('task/auto-clean', self._git(repo, 'branch', '--list'))
			wt_kept = Path(worktree_begin(repo, 'opt-keep', worktrees_dir=wt_base)['worktree'])
			(wt_kept / 'two.txt').write_text('two\n', encoding='utf-8')
			self._git(wt_kept, 'add', 'two.txt')
			self._git(wt_kept, 'commit', '-m', 'add two')
			res_keep = worktree_land(wt_kept, run_tests=True, remove=False, owner='keep', leases_dir=leases)
			self.assertTrue(res_keep['landed'], res_keep)
			self.assertFalse(res_keep['removed'], res_keep)
			self.assertTrue(wt_kept.is_dir())
			worktree_cleanup(repo, wt_kept, force=True)
	def test_worktree_status_flags_stale_behind_and_preserves_active_worktrees(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_repo(root)
			wt_base = root / 'wts'
			abandoned = Path(worktree_begin(repo, 'abandoned-141', worktrees_dir=wt_base)['worktree'])
			active_dirty = Path(worktree_begin(repo, 'active-dirty', worktrees_dir=wt_base)['worktree'])
			active_ahead = Path(worktree_begin(repo, 'active-ahead', worktrees_dir=wt_base)['worktree'])
			(active_dirty / 'wip.txt').write_text('uncommitted\n', encoding='utf-8')
			(active_ahead / 'feat.txt').write_text('feature\n', encoding='utf-8')
			self._git(active_ahead, 'add', 'feat.txt')
			self._git(active_ahead, 'commit', '-m', 'feature commit')
			(repo / 'main_next.txt').write_text('advance main\n', encoding='utf-8')
			self._git(repo, 'add', 'main_next.txt')
			self._git(repo, 'commit', '-m', 'advance main')
			fresh = Path(worktree_begin(repo, 'fresh-wt', worktrees_dir=wt_base)['worktree'])
			status = worktree_status(repo)
			self.assertEqual('main', status['base_ref'])
			self.assertEqual([abandoned.as_posix()], status['stale_worktrees'])
			self.assertEqual({abandoned.as_posix(), active_dirty.as_posix(), active_ahead.as_posix()}, set(status['behind_worktrees']))
			by_path = {e['path']: e for e in status['worktrees']}
			self.assertTrue(by_path[repo.as_posix()]['is_main'])
			self.assertFalse(by_path[repo.as_posix()]['stale'])
			self.assertTrue(by_path[abandoned.as_posix()]['stale'])
			self.assertEqual((0, 1), (by_path[abandoned.as_posix()]['ahead'], by_path[abandoned.as_posix()]['behind']))
			self.assertFalse(by_path[active_dirty.as_posix()]['stale'])
			self.assertTrue(by_path[active_dirty.as_posix()]['dirty'])
			self.assertFalse(by_path[active_ahead.as_posix()]['stale'])
			self.assertEqual((1, 1), (by_path[active_ahead.as_posix()]['ahead'], by_path[active_ahead.as_posix()]['behind']))
			self.assertFalse(by_path[fresh.as_posix()]['stale'])
			self.assertEqual((0, 0), (by_path[fresh.as_posix()]['ahead'], by_path[fresh.as_posix()]['behind']))
			for wt in (abandoned, active_dirty, active_ahead, fresh):
				worktree_cleanup(repo, wt, force=True)
	def test_worktree_status_flags_missing_worktree_as_stale(self) -> None:
		import shutil
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_repo(root)
			wt_base = root / 'wts'
			missing_wt = Path(worktree_begin(repo, 'gone-wt', worktrees_dir=wt_base)['worktree'])
			shutil.rmtree(missing_wt)
			status = worktree_status(repo)
			by_path = {e['path']: e for e in status['worktrees']}
			self.assertTrue(by_path[missing_wt.as_posix()]['missing'])
			self.assertTrue(by_path[missing_wt.as_posix()]['stale'])
			self.assertIn(missing_wt.as_posix(), status['stale_worktrees'])
			worktree_cleanup(repo, missing_wt, force=True)
if '__main__' == __name__:
	unittest.main()
