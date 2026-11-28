# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from Df.Harness.Tdd.Enforcement import Enforcement
from Df.Harness.Tdd.Evaluator import Evaluator
from Df.Harness.Tdd.EventsExtractor import EventsExtractor
from Df.Harness.Tdd.WorktreeScope import WorktreeScope
# 2026-11-28 "Reset TDD cycle on variable worktree commits and support rebase conflict state": https://github.com/dmitry-ai/harness/issues/441
class TddCommitResetAndRebaseTests(unittest.TestCase):
	# @used-by :meth:`TddCommitResetAndRebaseTests.__init_live_worktree()`
	@staticmethod
	def __git(repo: Path, *args: str) -> None:
		subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
	# @used-by :meth:`TddCommitResetAndRebaseTests.test_git_rebase_conflict_before_any_write_and_with_ps_var_in_pretool_enforcement()`
	@classmethod
	def __init_live_worktree(cls, root: Path) -> Path:
		repo = root / 'repo'
		repo.mkdir()
		cls.__git(repo, 'init', '-b', 'main')
		cls.__git(repo, 'config', 'user.email', 't@example.com')
		cls.__git(repo, 'config', 'user.name', 'Tester')
		(repo / 'scripts').mkdir()
		(repo / 'tests').mkdir()
		(repo / 'scripts/mod.py').write_text('VAL = 1\n', encoding='utf-8')
		(repo / 'tests/test_mod.py').write_text('import unittest\nclass T(unittest.TestCase):\n\tdef test_v(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
		cls.__git(repo, 'add', '.')
		cls.__git(repo, 'commit', '--no-verify', '-m', 'init')
		wt = root / '\ua616/data/worktrees/wt-live'
		wt.parent.mkdir(parents=True, exist_ok=True)
		cls.__git(repo, 'worktree', 'add', '-b', 'task/wt-live', str(wt), 'main')
		return wt
	# @used-by :mod:`unittest`
	def test_git_rebase_conflict_allows_resolution_and_enforces_full_green(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = root / 'repo'
			(repo / '.git').mkdir(parents=True)
			wt = root / '\ua616/data/worktrees/wt-reb'
			test_p, prod_p, bar_p = (wt / 'tests/test_foo.py', wt / 'scripts/foo.py', wt / 'scripts/bar.py')
			base_events = [
				EventsExtractor.build_file_write_event(1, test_p),
				EventsExtractor.build_command_event(2, f'python -m unittest "{test_p}"', 'Command exited with code 1.\nFAIL\n', cwd=root),
				EventsExtractor.build_file_write_event(3, prod_p),
				EventsExtractor.build_command_event(4, f'git -C "{wt}" commit -m "c1"', 'Command exited with code 0.\n[task/wt-reb 1111111] c1\n', cwd=root),
				EventsExtractor.build_command_event(5, f'git -C "{wt}" rebase main', 'Command exited with code 1.\nCONFLICT (content): Merge conflict in scripts/foo.py\nerror: could not apply 1111111\n', cwd=root),
				EventsExtractor.build_file_write_event(6, prod_p),
				EventsExtractor.build_command_event(7, f'git -C "{wt}" rebase --continue', 'Command exited with code 0.\nSuccessfully rebased and updated refs/heads/task/wt-reb.\n', cwd=root),
			]
			res_no_green = Evaluator(base_events, project_root=root).evaluate()
			self.assertFalse(res_no_green['verified'])
			self.assertTrue(any(('TDD-FULL-GATE' in v for v in res_no_green['violations'])), res_no_green['violations'])
			self.assertFalse(any(('TDD-RED-GATE' in v for v in res_no_green['violations'])), res_no_green['violations'])
			full_green = EventsExtractor.build_command_event(8, f'python -m unittest discover -s "{wt}/tests"', 'Command exited with code 0.\nRan 2 tests in 0.1s\nOK\n', cwd=root)
			res_ok = Evaluator([*base_events, full_green], project_root=root).evaluate()
			self.assertTrue(res_ok['verified'], res_ok['violations'])
			res_after = Evaluator([*base_events, EventsExtractor.build_file_write_event(8, bar_p), full_green], project_root=root).evaluate()
			self.assertFalse(res_after['verified'])
			self.assertTrue(any(('TDD-RED-GATE' in v for v in res_after['violations'])), res_after['violations'])
	# @used-by :mod:`unittest`
	def test_git_rebase_conflict_before_any_write_and_with_ps_var_in_pretool_enforcement(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			wt = self.__init_live_worktree(root)
			tx, prod_p = (root / 'transcript_full.jsonl', wt / 'scripts/mod.py')
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Resolve rebase'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'$wt = "{wt}"; git -C $wt rebase main')}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 1.\nCONFLICT (content): Merge conflict in scripts/mod.py\n'},
			]
			tx.write_text(''.join((json.dumps(r) + '\n' for r in rows)), encoding='utf-8')
			enf = Enforcement()
			self.assertIsNone(enf.evaluate_pre_tool_use('edit_file', {'Path': str(prod_p), 'Target': 'VAL = 1', 'Replacement': 'VAL = 2'}, {'cwd': str(root), 'transcriptPath': str(tx)}))
			rows.extend([{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'edit_file', 'args': {'Path': json.dumps(str(prod_p))}}]}, {'step_index': 4, 'type': 'GENERIC', 'content': 'Made 1 replacement.'}])
			tx.write_text(''.join((json.dumps(r) + '\n' for r in rows)), encoding='utf-8')
			st_mid = Evaluator(EventsExtractor(tx, cwd=root).extract(), require_final_full_green=False, project_root=root).evaluate()
			self.assertEqual('REBASE_CONFLICT', st_mid['scopes'][str(wt.resolve())]['state'])
			rows.extend([{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'$wt = "{wt}"; git -C $wt rebase --abort')}}]}, {'step_index': 6, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n'}])
			tx.write_text(''.join((json.dumps(r) + '\n' for r in rows)), encoding='utf-8')
			err_after = enf.evaluate_pre_tool_use('edit_file', {'Path': str(prod_p), 'Target': 'VAL = 1', 'Replacement': 'VAL = 3'}, {'cwd': str(root), 'transcriptPath': str(tx)})
			self.assertIsNotNone(err_after)
			self.assertIn('TDD-RED-GATE', str(err_after))
	# @used-by :mod:`unittest`
	def test_variable_wt_commit_resets_scope_and_blocks_untested_second_commit(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = root / 'repo'
			(repo / '.git').mkdir(parents=True)
			wt_a = root / '\ua616/data/worktrees/wt-alpha'
			test_a, prod_a, prod_b = (wt_a / 'tests/test_a.py', wt_a / 'scripts/a.py', wt_a / 'scripts/b.py')
			commit_ev = EventsExtractor.build_command_event(4, f'$wt = "{wt_a}"; git -C $wt commit -m "c1"', 'Command exited with code 0.\n[task/wt-alpha 1111111] c1\n', cwd=root)
			self.assertTrue(WorktreeScope.scope_matches_commit(f'{root}::wt:wt-alpha', commit_ev.get('commit_scope'), commit_ev))
			self.assertFalse(WorktreeScope.scope_matches_commit(f'{root}::wt:wt-beta', commit_ev.get('commit_scope'), commit_ev))
			events_gap = [
				EventsExtractor.build_file_write_event(1, test_a),
				EventsExtractor.build_command_event(2, f'python -m unittest "{test_a}"', 'Command exited with code 1.\nFAIL\n', cwd=root),
				EventsExtractor.build_file_write_event(3, prod_a),
				commit_ev,
				EventsExtractor.build_file_write_event(5, prod_b),
				EventsExtractor.build_command_event(6, f'python -m unittest discover -s "{wt_a}/tests"', 'Command exited with code 0.\nRan 2 tests in 0.1s\nOK\n', cwd=root),
			]
			res_gap = Evaluator(events_gap, project_root=root).evaluate()
			self.assertFalse(res_gap['verified'], 'Expected GAP A2 untested second commit to fail TDD-RED-GATE')
			self.assertTrue(any(('TDD-RED-GATE' in v for v in res_gap['violations'])), res_gap['violations'])
if '__main__' == __name__:
	unittest.main()
