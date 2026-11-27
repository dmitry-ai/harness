# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-27 "Extract worktree scope IDs from shell command paths in WorktreeScope": https://github.com/dmitry-ai/harness/issues/397
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# @used-by :mod:`unittest`
class TddWorktreeCmdScopeTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_deleted_worktree_set_location_red_run_remains_verified(self) -> None:
		from Df.Harness.Tdd.Evaluator import Evaluator
		from Df.Harness.Tdd.EventsExtractor import EventsExtractor
		from Df.Harness.Tdd.WorktreeScope import WorktreeScope
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			main_repo = root / '\u2c0f/\u227b/\u2655/\u26ef'
			tests_dir = main_repo / 'tests'
			(main_repo / '.git').mkdir(parents=True)
			tests_dir.mkdir(parents=True)
			(tests_dir / 'test_a.py').write_text('x = 1\n', encoding='utf-8')
			(tests_dir / 'test_b.py').write_text('x = 1\n', encoding='utf-8')
			dead_wt = root / '\ua616/data/worktrees/s11-wave2c'
			ev_test = EventsExtractor.build_file_write_event(10, dead_wt / 'tests/test_mod.py', cwd=root, sub_step=1, subagent_id='sub-1')
			red_cmd = f"Set-Location '{dead_wt}'\npython scripts/harness.py test-watchdog --timeout 60 -- python -m pytest -x tests/test_mod.py"
			ev_red = EventsExtractor.build_command_event(10, red_cmd, 'Command exited with code 1.\nFAILED tests/test_mod.py\n', cwd=root, sub_step=2, subagent_id='sub-1')
			self.assertEqual({'s11-wave2c'}, WorktreeScope.extract_command_worktree_ids(ev_red))
			ev_prod = EventsExtractor.build_file_write_event(10, dead_wt / 'scripts/Df/Harness/Mod.py', cwd=root, sub_step=3, subagent_id='sub-1')
			ev_green = EventsExtractor.build_command_event(10, f'python scripts/harness.py run-tests "{tests_dir}"', 'Command exited with code 0.\nRan 2 tests in 0.1s\nOK\n', cwd=root, sub_step=4, subagent_id='sub-1')
			res = Evaluator([ev_test, ev_red, ev_prod, ev_green], require_final_full_green=True).evaluate()
			self.assertTrue(res['verified'], res)
	# @used-by :mod:`unittest`
	def test_runner_script_worktree_ignored_while_var_assignment_and_cd_extracted(self) -> None:
		from Df.Harness.Tdd.EventsExtractor import EventsExtractor
		from Df.Harness.Tdd.WorktreeScope import WorktreeScope
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			other_wt = root / '\ua616/data/worktrees/other-wt'
			target_wt = root / '\ua616/data/worktrees/target-wt'
			runner_p = other_wt / 'scripts/harness.py'
			target_test = target_wt / 'tests/test_a.py'
			cmd_runner = f'python "{runner_p}" test-watchdog -- python -m pytest -x "{target_test}"'
			ev_runner = EventsExtractor.build_command_event(1, cmd_runner, 'Command exited with code 1.\nFAILED\n', cwd=root)
			self.assertEqual({'target-wt'}, WorktreeScope.extract_command_worktree_ids(ev_runner))
			ps_wt = root / '\ua616/data/worktrees/ps-wt'
			cmd_ps = f"$wt = '{ps_wt}'; Set-Location $wt; python -m pytest -x tests/test_a.py"
			ev_ps = EventsExtractor.build_command_event(2, cmd_ps, 'Command exited with code 1.\nFAILED\n', cwd=root)
			self.assertEqual({'ps-wt'}, WorktreeScope.extract_command_worktree_ids(ev_ps))
if '__main__' == __name__:
	unittest.main()
