# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', *args], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
def _init_repo(repo: Path) -> None:
	repo.mkdir(parents=True, exist_ok=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 't@example.com')
	_git(repo, 'config', 'user.name', 'Test')
def _commit_file(repo: Path, rel: str, text: str, msg: str) -> None:
	p = repo / rel
	p.parent.mkdir(parents=True, exist_ok=True)
	p.write_text(text, encoding='utf-8')
	_git(repo, 'add', rel)
	_git(repo, 'commit', '--no-verify', '-m', msg)
# 2026-11-26
# "Resolve deleted worktree paths in TDD comment-only exemption":
# https://github.com/dmitry-ai/harness/issues/278
class WorktreeCommentExemptionTests(unittest.TestCase):
	def test_deleted_sibling_and_nested_worktree_comment_only_commits_are_exempt(self) -> None:
		from agent_tools.tdd.evaluator import evaluate_tdd_events
		from agent_tools.tdd.events import build_file_write_tdd_event
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			sib_proj = root / 'sib'
			sib_repo = sib_proj / '\u2c0f/\u227b/\u2655/\u26ef'
			_init_repo(sib_repo)
			_commit_file(sib_repo, 'CSS/chat.css', '/* old */\n.a { color: red; }\n', 'seed')
			_commit_file(sib_repo, 'CSS/chat.css', '/* new */\n.a { color: red; }\n', 'comment')
			sib_wt_file = sib_proj / '\ua616/data/worktrees/task-a/CSS/chat.css'
			sib_ev = build_file_write_tdd_event(10, sib_wt_file)
			self.assertEqual(str(sib_repo), sib_ev['scope'])
			sib_res = evaluate_tdd_events([sib_ev], require_final_full_green=True)
			self.assertTrue(sib_res['verified'], sib_res)
			nest_repo = root / 'nest'
			_init_repo(nest_repo)
			_commit_file(nest_repo, '\u26ef/build.ps1', '# old\n$x = 1\n', 'seed')
			_commit_file(nest_repo, '\u26ef/build.ps1', '# new\n$x = 1\n', 'comment')
			nest_wt_file = nest_repo / '\ua616/data/worktrees/task-b/\u26ef/build.ps1'
			nest_ev = build_file_write_tdd_event(12, nest_wt_file)
			self.assertEqual(str(nest_repo), nest_ev['scope'])
			nest_res = evaluate_tdd_events([nest_ev], require_final_full_green=True)
			self.assertTrue(nest_res['verified'], nest_res)
	def test_deleted_worktree_non_comment_code_commit_remains_blocked(self) -> None:
		from agent_tools.tdd.evaluator import evaluate_tdd_events
		from agent_tools.tdd.events import build_file_write_tdd_event
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			proj = root / 'proj'
			repo = proj / '\u2c0f/\u227b/\u2655/\u26ef'
			_init_repo(repo)
			_commit_file(repo, 'app.py', '# c\nx = 1\n', 'seed')
			_commit_file(repo, 'app.py', '# c\nx = 2\n', 'code')
			wt_file = proj / '\ua616/data/worktrees/task-c/app.py'
			ev = build_file_write_tdd_event(15, wt_file)
			res = evaluate_tdd_events([ev], require_final_full_green=True)
			self.assertFalse(res['verified'])
			self.assertTrue(any(('TDD-RED-GATE' in v for v in res['violations'])), res)
if '__main__' == __name__:
	unittest.main()
