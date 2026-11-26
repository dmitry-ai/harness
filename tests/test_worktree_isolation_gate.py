# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = HARNESS_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# @used-by :func:`_init_git_repo()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True)
	return (proc.stdout or '').strip()
# @used-by :meth:`WorktreeIsolationGateTests.test_agent_metadata_and_read_only_tools_are_allowed()`
# @used-by :meth:`WorktreeIsolationGateTests.test_harness_main_blocks_write_and_edit_while_linked_worktree_allows()`
# @used-by :meth:`WorktreeIsolationGateTests.test_non_harness_repo_allows_single_turn_and_blocks_concurrent_open_turns()`
def _init_git_repo(repo: Path, files: dict[str, str]) -> Path:
	repo.mkdir(parents=True, exist_ok=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	for rel, body in files.items():
		fp = repo / rel
		fp.parent.mkdir(parents=True, exist_ok=True)
		fp.write_text(body, encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '-m', 'init')
	return repo
# @used-by :meth:`WorktreeIsolationGateTests.test_agent_metadata_and_read_only_tools_are_allowed()`
# @used-by :meth:`WorktreeIsolationGateTests.test_non_harness_repo_allows_single_turn_and_blocks_concurrent_open_turns()`
def _write_turn(turns_dir: Path, name: str, *, status: str, conv_id: str, age_hours: float=0.0) -> None:
	turns_dir.mkdir(parents=True, exist_ok=True)
	ts = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
	payload = {'status': status, 'conversation_id': conv_id, 'updated_at': ts, 'created_at': ts}
	(turns_dir / f'{name}.json').write_text(json.dumps(payload), encoding='utf-8')
# 2026-11-24
# "Add PreToolUse worktree isolation gate for live main checkouts":
# https://github.com/dmitry-ai/harness/issues/185
class WorktreeIsolationGateTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_agent_metadata_and_read_only_tools_are_allowed(self) -> None:
		from agent_tools.gates.worktree_isolation import check
		with tempfile.TemporaryDirectory() as td:
			proj = Path(td).resolve()
			_init_git_repo(proj, {'readme.md': '# proj\n'})
			turns = proj / '\ua616/data/turns'
			_write_turn(turns, 't1', status='open', conv_id='c1')
			_write_turn(turns, 't2', status='open', conv_id='c2')
			self.assertIsNone(check('write_file', {'Path': str(proj / '\ua616/data/scratch/answer.md'), 'Content': 'ok'}, {'cwd': str(proj)}))
			self.assertIsNone(check('write_file', {'Path': str(proj / '\ua616/KB/note.md'), 'Content': 'ok'}, {'cwd': str(proj)}))
			self.assertIsNone(check('read_file', {'Path': str(proj / 'readme.md')}, {'cwd': str(proj)}))
			self.assertIsNone(check('run_command', {'CommandLine': 'echo hi'}, {'cwd': str(proj)}))
	# @used-by :mod:`unittest`
	def test_harness_main_blocks_write_and_edit_while_linked_worktree_allows(self) -> None:
		from agent_tools.gates import discover_pre_tool_gates, run_pre_tool_gates
		from agent_tools.gates.worktree_isolation import check
		from agent_tools.worktree_flow import worktree_begin
		gates = discover_pre_tool_gates()
		names = [g['name'] for g in gates]
		self.assertIn('EXEC-5-WORKTREE-GATE', names)
		self.assertLess(names.index('EXEC-4-SCHEDULE-GATE'), names.index('EXEC-5-WORKTREE-GATE'))
		self.assertLess(names.index('EXEC-5-WORKTREE-GATE'), names.index('EXEC-5-ISSUE-FIRST-GATE'))
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_git_repo(root / 'harness/\u2c0f/\u227b/\u2655/\u26ef', {'paths.json': '{}\n', 'runtime.json': '{}\n', 'scripts/check_rules_and_server_gate.py': 'X = 1\n'})
			d_edit = run_pre_tool_gates('edit_file', {'Path': str(repo / 'scripts/check_rules_and_server_gate.py'), 'Target': '1', 'Replacement': '2'}, {'cwd': str(repo)})
			self.assertEqual('deny', d_edit['decision'])
			self.assertIn('EXEC-5-WORKTREE-GATE', d_edit['reason'])
			self.assertIn('worktree-begin', d_edit['reason'])
			d_write = run_pre_tool_gates('write_file', {'Path': str(repo / 'scripts/new_mod.py'), 'Content': 'Y = 2\n'}, {'cwd': str(repo)})
			self.assertEqual('deny', d_write['decision'])
			self.assertIn('EXEC-5-WORKTREE-GATE', d_write['reason'])
			wt = Path(worktree_begin(repo, 'iso-ok', worktrees_dir=root / 'wts')['worktree'])
			self.assertIsNone(check('edit_file', {'Path': str(wt / 'scripts/check_rules_and_server_gate.py')}, {'cwd': str(wt)}))
			self.assertIsNone(check('write_file', {'Path': str(wt / 'scripts/new_mod.py')}, {'cwd': str(wt)}))
	# @used-by :mod:`unittest`
	def test_non_harness_repo_allows_single_turn_and_blocks_concurrent_open_turns(self) -> None:
		from agent_tools.gates import run_pre_tool_gates
		from agent_tools.gates.worktree_isolation import check
		from agent_tools.worktree_flow import worktree_begin
		with tempfile.TemporaryDirectory() as td:
			proj = Path(td).resolve()
			code = _init_git_repo(proj / 'code', {'app.py': 'VALUE = 1\n'})
			turns = proj / '\ua616/data/turns'
			self.assertIsNone(check('edit_file', {'Path': str(code / 'app.py')}, {'cwd': str(proj)}))
			_write_turn(turns, 't1', status='open', conv_id='conv-1', age_hours=0.1)
			_write_turn(turns, 't2', status='prepared', conv_id='conv-2', age_hours=0.1)
			_write_turn(turns, 't3', status='open', conv_id='conv-stale', age_hours=48.0)
			self.assertIsNone(check('edit_file', {'Path': str(code / 'app.py')}, {'cwd': str(proj)}))
			_write_turn(turns, 't4', status='open', conv_id='conv-3', age_hours=0.1)
			err = check('edit_file', {'Path': str(code / 'app.py')}, {'cwd': str(proj)})
			self.assertIsNotNone(err)
			self.assertIn('worktree-begin', err or '')
			dec = run_pre_tool_gates('write_file', {'Path': str(code / 'new.py'), 'Content': 'Z = 3\n'}, {'cwd': str(proj)})
			self.assertEqual('deny', dec['decision'])
			self.assertIn('EXEC-5-WORKTREE-GATE', dec['reason'])
			wt = Path(worktree_begin(code, 'concurrent-ok', worktrees_dir=proj / '\ua616/data/worktrees')['worktree'])
			self.assertIsNone(check('write_file', {'Path': str(wt / 'new.py')}, {'cwd': str(proj)}))
if '__main__' == __name__:
	unittest.main()
