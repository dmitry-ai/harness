# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Block raw worktree removal and fail closed on locked cleanup":
# https://github.com/dmitry-ai/harness/issues/303
from __future__ import annotations
from pathlib import Path
from unittest import mock
import subprocess
import sys
import tempfile
import unittest
WORKTREE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WORKTREE_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.gates import run_pre_tool_gates
from agent_tools.worktree_flow import worktree_begin, worktree_cleanup, worktree_land
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :class:`WorktreeCleanupGuardTests`
class WorktreeCleanupGuardTests(unittest.TestCase):
	# @used-by :meth:`WorktreeCleanupGuardTests._init_repo`
	# @used-by :meth:`WorktreeCleanupGuardTests.test_worktree_land_fails_closed_when_cleanup_is_locked`
	def _git(self, repo: Path, *args: str) -> str:
		proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True, creationflags=_NO_WINDOW)
		return (proc.stdout or '').strip()
	# @used-by :meth:`WorktreeCleanupGuardTests.test_worktree_cleanup_fails_closed_with_lock_holders_on_locked_dir`
	# @used-by :meth:`WorktreeCleanupGuardTests.test_worktree_land_fails_closed_when_cleanup_is_locked`
	def _init_repo(self, root: Path) -> Path:
		repo = root / 'repo'
		repo.mkdir(parents=True)
		self._git(repo, 'init', '-b', 'main')
		self._git(repo, 'config', 'user.email', 'test@example.com')
		self._git(repo, 'config', 'user.name', 'Test')
		(repo / 'README.md').write_text('# Demo\n', encoding='utf-8')
		self._git(repo, 'add', '.')
		self._git(repo, 'commit', '-m', 'init')
		return repo
	# @used-by :mod:`unittest`
	def test_pre_tool_use_blocks_raw_git_worktree_remove(self) -> None:
		for cmd in (
			'git -C repo worktree remove wt',
			'git worktree remove --force "C:/work/x/\ua616/data/worktrees/demo"',
			'git -C "C:/work/repo" worktree remove -f "C:/work/x/\ua616/data/worktrees/demo"',
		):
			res = run_pre_tool_gates('run_command', {'CommandLine': cmd}, {})
			self.assertEqual('deny', res['decision'], cmd)
			self.assertIn('worktree', res['reason'].lower())
		for ok_cmd in (
			'python scripts/harness.py worktree-land "C:/work/x/\ua616/data/worktrees/demo" --push',
			'python scripts/harness.py worktree-cleanup repo "C:/work/x/\ua616/data/worktrees/demo"',
			'git --no-optional-locks worktree list --porcelain',
		):
			res = run_pre_tool_gates('run_command', {'CommandLine': ok_cmd}, {})
			self.assertEqual('allow', res['decision'], ok_cmd)
	# @used-by :mod:`unittest`
	def test_pre_tool_use_blocks_silent_shell_deletion_of_managed_worktrees(self) -> None:
		for bad_cmd in (
			'Remove-Item -LiteralPath "C:/work/p/\ua616/data/worktrees/demo" -Recurse -Force -ErrorAction SilentlyContinue',
			'$ag_wt = "C:/work/p/\ua616/data/worktrees/demo"; if (Test-Path -LiteralPath $ag_wt) { Remove-Item -LiteralPath $ag_wt -Recurse -Force -ErrorAction SilentlyContinue }',
			'rm -rf C:/work/p/\ua616/data/worktrees/demo',
			'python -c "import shutil; shutil.rmtree(\'C:/work/p/\ua616/data/worktrees/demo\', ignore_errors=True)"',
		):
			res = run_pre_tool_gates('run_command', {'CommandLine': bad_cmd}, {})
			self.assertEqual('deny', res['decision'], bad_cmd)
		ok = run_pre_tool_gates('run_command', {'CommandLine': 'Remove-Item -LiteralPath "C:/work/p/\ua616/data/scratch/tmp.txt" -Force'}, {})
		self.assertEqual('allow', ok['decision'])
	# @used-by :mod:`unittest`
	def test_worktree_cleanup_fails_closed_with_lock_holders_on_locked_dir(self) -> None:
		from agent_tools.worktree_guard import find_worktree_lock_holders
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_repo(root)
			wt = Path(worktree_begin(repo, 'locked-wt', worktrees_dir=root / 'wts')['worktree'])
			fake_holders = [{'pid': 18024, 'name': 'node.exe', 'command_line': f'node {wt.as_posix()}/Upgrade/cdp-companion.js'}]
			fake_fail = subprocess.CompletedProcess(['git'], 128, '', f"error: failed to delete '{wt.as_posix()}': Permission denied\n")
			real_exec = __import__('agent_tools.worktree_flow', fromlist=['_git_exec'])._git_exec
			def _exec_side_effect(r_path: Path, *args: str):
				return fake_fail if 2 <= len(args) and 'worktree' == args[0] and 'remove' == args[1] else real_exec(r_path, *args)
			with mock.patch('agent_tools.worktree_flow._git_exec', side_effect=_exec_side_effect), mock.patch('agent_tools.worktree_guard.find_worktree_lock_holders', return_value=fake_holders):
				res = worktree_cleanup(repo, wt, force=True)
			self.assertFalse(res['valid'])
			self.assertEqual(fake_holders, res['locking_processes'])
			self.assertIn('Permission denied', res['error'])
			self.assertTrue(wt.is_dir())
			self.assertEqual([], find_worktree_lock_holders(wt, process_rows=[]))
			cleaned = worktree_cleanup(repo, wt, force=True)
			self.assertTrue(cleaned['valid'])
			self.assertFalse(wt.exists())
	# @used-by :mod:`unittest`
	def test_worktree_land_fails_closed_when_cleanup_is_locked(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_repo(root)
			wt = Path(worktree_begin(repo, 'locked-land', worktrees_dir=root / 'wts')['worktree'])
			(wt / 'note.txt').write_text('ok\n', encoding='utf-8')
			self._git(wt, 'add', 'note.txt')
			self._git(wt, 'commit', '-m', 'add note')
			fake_cleanup = {'valid': False, 'main_repo': repo.as_posix(), 'worktree': wt.as_posix(), 'branch': 'task/locked-land', 'branch_deleted': False, 'error': 'Permission denied', 'locking_processes': [{'pid': 18024, 'name': 'node.exe', 'command_line': 'node wt/cdp.js'}]}
			with mock.patch('agent_tools.worktree_flow.worktree_cleanup', return_value=fake_cleanup):
				res = worktree_land(wt, run_tests=False, remove=True, owner='lock-test', leases_dir=root / 'leases')
			self.assertFalse(res['valid'])
			self.assertTrue(res['landed'])
			self.assertFalse(res['removed'])
			self.assertEqual('worktree_cleanup', res['stage'])
			self.assertEqual(fake_cleanup['locking_processes'], res['cleanup']['locking_processes'])
			worktree_cleanup(repo, wt, force=True)
if '__main__' == __name__:
	unittest.main()
