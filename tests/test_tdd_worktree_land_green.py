# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
from __future__ import annotations
from pathlib import Path
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
# @used-by :meth:`TddWorktreeLandGreenTests.test_antigravity_scanners_forward_untruncated_output_to_tdd_while_capping_tool_records()`
# @used-by :meth:`TddWorktreeLandGreenTests.test_evaluator_worktree_land_green_and_compound_soundness()`
# @used-by :meth:`TddWorktreeLandGreenTests.test_outcome_parser_worktree_land_json_truncation_and_log_fallback()`
def _land_json_output(main_repo: str, *, valid: bool=True, landed: bool=True, test_runs: object=1, test_result: object=None, pad_chars: int=0, exit_code: int=0) -> str:
	payload: dict[str, object] = {'valid': valid, 'landed': landed, 'main_repo': main_repo, 'test_runs': test_runs, 'test_result': test_result}
	if 0 < pad_chars:
		payload['padding'] = 'x' * pad_chars
	return f'Command exited with code {exit_code}.\n\nCommand output:\n' + json.dumps(payload, indent=2) + '\n'
# @used-by :mod:`unittest`
class TddWorktreeLandGreenTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_antigravity_scanners_forward_untruncated_output_to_tdd_while_capping_tool_records(self) -> None:
		from Df.Harness.Platform.Antigravity.TurnScanner import TurnScanner
		from Df.Harness.lib.completion_child_trace import _process_tool_calls_row
		from Df.Harness.lib.trace_effects import dfh_init_turn_accumulator
		from test_stop_emergency_capture_and_foreign_sync import _seed_ag_conversation
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj, backend = (base / 'proj', base / 'backend')
			proj.mkdir()
			big_out = _land_json_output(str(proj / 'repo'), test_result={'ok': True, 'total_tests': 12, 'summary': 'Ran 12 tests in 1s\nOK'}, pad_chars=4500)
			wt_p = proj / '\ua616/data/worktrees/big-wt'
			rows = [
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python scripts/harness.py worktree-land "{wt_p}"'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': big_out},
			]
			seg = dfh_init_turn_accumulator(extra={'issue_actions': []})
			_process_tool_calls_row(proj, rows, 0, 1, rows[0]['tool_calls'], seg, {})
			self.assertEqual(4000, len(seg['tool_records'][0]['outputs'][0]))
			self.assertTrue(seg['tdd_events'][0]['outcome'].get('worktree_land_full_green'))
			cid = '77777777-1111-2222-3333-444444444444'
			tx = _seed_ag_conversation(backend, proj, cid, 'Land task', 'Done.  \n')
			full_rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Land task'}, *rows, {'step_index': 3, 'type': 'PLANNER_RESPONSE', 'content': 'Done.  \n', 'tool_calls': []}]
			tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in full_rows)), encoding='utf-8')
			scanned = TurnScanner(proj, cid, backend=backend).scan()
			self.assertTrue(scanned['turns'][0]['tdd_events'][0]['outcome'].get('worktree_land_full_green'))
	# @used-by :mod:`unittest`
	def test_command_inspector_classifies_worktree_land_variants(self) -> None:
		from Df.Harness.Tdd.CommandInspector import CommandInspector
		c_land = CommandInspector('python "C:/x/scripts/harness.py" worktree-land "C:/x/wt" --push --tag').classify_test_command()
		self.assertTrue(c_land['is_test_cmd'])
		self.assertTrue(c_land['is_full_suite'])
		self.assertTrue(c_land['has_worktree_land'])
		self.assertTrue(c_land['worktree_land_only'])
		self.assertFalse(c_land['ordinary_full_suite'])
		self.assertFalse(c_land['has_ordinary_test'])
		c_reason = CommandInspector('python upwork_project.py worktree-land "C:/x/wt" --no-tests-reason "docs"').classify_test_command()
		self.assertTrue(c_reason['has_worktree_land'])
		c_skip = CommandInspector('python harness.py worktree-land "C:/x/wt" --no-tests').classify_test_command()
		self.assertFalse(c_skip['is_test_cmd'])
		self.assertFalse(c_skip['has_worktree_land'])
		c_echo = CommandInspector('echo "harness.py worktree-land C:/x/wt"').classify_test_command()
		self.assertFalse(c_echo['is_test_cmd'])
		c_comp = CommandInspector('python -m unittest -f tests/test_a.py && python harness.py worktree-land "C:/x/wt"').classify_test_command()
		self.assertTrue(c_comp['has_ordinary_test'])
		self.assertFalse(c_comp['ordinary_full_suite'])
		self.assertTrue(c_comp['has_worktree_land'])
		self.assertFalse(c_comp['worktree_land_only'])
	# @used-by :mod:`unittest`
	def test_evaluator_worktree_land_green_and_compound_soundness(self) -> None:
		from Df.Harness.Tdd.Evaluator import Evaluator
		from Df.Harness.Tdd.EventsExtractor import EventsExtractor
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			ext_repo = root / 'ext_repo'
			(ext_repo / '.git').mkdir(parents=True)
			(ext_repo / 'tests').mkdir()
			(ext_repo / 'tests/test_a.py').write_text('x = 1\n', encoding='utf-8')
			(ext_repo / 'tests/test_b.py').write_text('x = 1\n', encoding='utf-8')
			dead_wt = root / '\ua616/data/worktrees/land-wt'
			test_x = dead_wt / 'tests/test_x.py'
			ev_t = EventsExtractor.build_file_write_event(1, test_x, cwd=root)
			ev_t['scope'] = str(ext_repo)
			ev_bad_land = EventsExtractor.build_command_event(2, f'python harness.py worktree-land "{dead_wt}"', _land_json_output(str(ext_repo), valid=False, landed=False, test_runs=0, exit_code=1), cwd=root)
			ev_p = EventsExtractor.build_file_write_event(3, dead_wt / 'scripts/mod.py', cwd=root)
			ev_p['scope'] = str(ext_repo)
			self.assertFalse(Evaluator([ev_t, ev_bad_land, ev_p], require_final_full_green=False).evaluate()['verified'])
			ev_comp_err = EventsExtractor.build_command_event(2, f'python -m pytest -x "{test_x}" && python harness.py worktree-land "{dead_wt}"', 'Command exited with code 1.\nERROR: ValueError: dirty\n', cwd=root)
			self.assertFalse(Evaluator([ev_t, ev_comp_err, ev_p], require_final_full_green=False).evaluate()['verified'])
			ev_red = EventsExtractor.build_command_event(2, f'python -m pytest -x "{test_x}"', 'Command exited with code 1.\nFAILED tests/test_x.py\n', cwd=root)
			ev_skip_comp = EventsExtractor.build_command_event(4, f'python -m pytest -x "{test_x}" && python harness.py worktree-land "{dead_wt}"', _land_json_output(str(ext_repo), valid=True, landed=True, test_runs=0, test_result=None), cwd=root)
			self.assertFalse(Evaluator([ev_t, ev_red, ev_p, ev_skip_comp], require_final_full_green=True).evaluate()['verified'])
			ev_ok_land = EventsExtractor.build_command_event(4, f'python harness.py worktree-land "{dead_wt}" --push --tag', _land_json_output(str(ext_repo), test_result={'ok': True, 'total_tests': 50, 'summary': 'Ran 50 tests in 5s\nOK'}), cwd=root)
			ok_res = Evaluator([ev_t, ev_red, ev_p, ev_ok_land], require_final_full_green=True).evaluate()
			self.assertTrue(ok_res['verified'], ok_res)
	# @used-by :mod:`unittest`
	def test_outcome_parser_worktree_land_json_truncation_and_log_fallback(self) -> None:
		from Df.Harness.Tdd.OutcomeParser import OutcomeParser
		ok_out = _land_json_output('C:/repo', test_result={'ok': True, 'total_tests': 1751, 'summary': 'Ran 1751 tests in 200s\nOK'})
		parsed = OutcomeParser(ok_out).parse()
		self.assertTrue(parsed['worktree_land_full_green'])
		self.assertEqual('C:/repo', parsed['worktree_land_main_repo'])
		self.assertFalse(parsed['worktree_land_failed'])
		self.assertFalse(OutcomeParser(_land_json_output('C:/repo', test_runs=0, test_result=None)).parse()['worktree_land_full_green'])
		self.assertFalse(OutcomeParser(_land_json_output('C:/repo', test_runs=1, test_result={'ok': True, 'total_tests': 0, 'summary': 'Ran 0 tests in 0.1s\nOK'})).parse()['worktree_land_full_green'])
		self.assertFalse(OutcomeParser(_land_json_output('C:/repo', test_runs=True, test_result={'ok': True, 'total_tests': 5})).parse()['worktree_land_full_green'])
		self.assertFalse(OutcomeParser(_land_json_output('C:/repo', test_runs='abc', test_result={'ok': True, 'total_tests': 5})).parse()['worktree_land_full_green'])
		self.assertTrue(OutcomeParser('Command exited with code 1.\n{\n  "valid": false,\n  "stage": "rebase"\n').parse()['worktree_land_failed'])
		with tempfile.TemporaryDirectory() as td:
			log_p = Path(td).resolve() / 'task-1.log'
			log_p.write_text(_land_json_output('C:/repo', test_result={'ok': True, 'total_tests': 9, 'summary': 'Ran 9 tests in 1s\nOK'}, pad_chars=4500), encoding='utf-8')
			trunc_msg = f'Command exited with code 0.\n\nCommand output:\n{{\n  "valid": true\nLog: {log_p.as_uri()}\n'
			via_log = OutcomeParser(trunc_msg).parse()
			self.assertTrue(via_log['worktree_land_full_green'], via_log)
			self.assertEqual('C:/repo', via_log['worktree_land_main_repo'])
if '__main__' == __name__:
	unittest.main()
