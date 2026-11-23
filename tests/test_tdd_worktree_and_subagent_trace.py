# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/173
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from agent_tools import tdd_gate
from agent_tools.platforms.trace_common import init_turn_accumulator, record_normalized_tool_effects
class TddWorktreeAndSubagentTraceTests(unittest.TestCase):
	def test_combined_git_commit_and_full_test_command_updates_full_green(self):
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve()
			(repo / '.git').mkdir()
			(repo / 'tests').mkdir()
			(repo / 'tests' / 'test_a.py').write_text('x = 1\n', encoding='utf-8')
			(repo / 'tests' / 'test_b.py').write_text('x = 1\n', encoding='utf-8')
			ev_test = tdd_gate.build_file_write_tdd_event(1, repo / 'tests' / 'test_a.py', cwd=repo)
			ev_red = tdd_gate.build_command_tdd_event(2, f'python -m unittest discover -s "{repo / "tests"}" -p test_a.py', 'Command exited with code 1.\nFAILED (errors=1)\n', cwd=repo)
			ev_prod = tdd_gate.build_file_write_tdd_event(3, repo / 'mod.py', cwd=repo)
			ev_comb = tdd_gate.build_command_tdd_event(4, f'git -C "{repo}" commit -m "x"; python harness.py run-tests "{repo / "tests"}" --workers 2', 'Command exited with code 0.\nRan 2 tests in 0.1s\nOK\n', cwd=repo)
			res = tdd_gate.evaluate_tdd_events([ev_test, ev_red, ev_prod, ev_comb])
			self.assertTrue(res['verified'], res)
			self.assertEqual(4, res['scopes'][str(repo)]['last_full_green_step'])
	def test_denied_write_tool_call_is_excluded_from_tdd_events(self):
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve()
			(repo / '.git').mkdir()
			target = repo / 'prod.py'
			acc = init_turn_accumulator()
			denied_out = ['Encountered error in tool execution: tool call denied by pre-tool hook: REJECTED (EXEC-2-TDD-GATE)']
			record_normalized_tool_effects(repo, 10, 'edit_file', {'Path': str(target), 'Target': 'a', 'Replacement': 'b'}, '', acc, cmd_outputs=denied_out)
			self.assertEqual([], acc['tdd_events'])
			tfile = repo / 'transcript_full.jsonl'
			rows = [
				{'step_index': 1, 'type': 'USER_INPUT', 'content': 'fix bug'},
				{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'edit_file', 'args': {'Path': str(target)}}]},
				{'step_index': 3, 'type': 'GENERIC', 'content': denied_out[0]},
			]
			tfile.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			self.assertEqual([], tdd_gate.extract_antigravity_tdd_events(tfile, cwd=repo))
	def test_resolve_code_scope_maps_deleted_worktree_to_main_code_repo(self):
		with tempfile.TemporaryDirectory() as tmp:
			meta = Path(tmp).resolve()
			(meta / '.git').mkdir()
			code_repo = meta / '\u2c0f' / '\u227b' / '\u2655' / '\u26ef'
			(code_repo / '.git').mkdir(parents=True)
			deleted_wt_file = meta / '\ua616' / 'data' / 'worktrees' / 'dead-task' / 'scripts' / 'agent_tools' / 'x.py'
			self.assertEqual(code_repo, tdd_gate.resolve_code_scope(deleted_wt_file))
	def test_subagent_events_sharing_parent_step_preserve_sub_step_order(self):
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve()
			(repo / '.git').mkdir()
			(repo / 'tests').mkdir()
			(repo / 'tests' / 'test_a.py').write_text('x = 1\n', encoding='utf-8')
			(repo / 'tests' / 'test_b.py').write_text('x = 1\n', encoding='utf-8')
			ev_test = tdd_gate.build_file_write_tdd_event(635, repo / 'tests' / 'test_a.py', cwd=repo, sub_step=10, subagent_id='sub-1')
			ev_red = tdd_gate.build_command_tdd_event(635, f'python -m unittest discover -s "{repo / "tests"}" -p test_a.py', 'Command exited with code 1.\nFAILED (errors=1)\n', cwd=repo, sub_step=14, subagent_id='sub-1')
			ev_prod = tdd_gate.build_file_write_tdd_event(635, repo / 'mod.py', cwd=repo, sub_step=18, subagent_id='sub-1')
			ev_green = tdd_gate.build_command_tdd_event(635, f'python harness.py run-tests "{repo / "tests"}" --workers 2', 'Command exited with code 0.\nRan 2 tests in 0.1s\nOK\n', cwd=repo, sub_step=25, subagent_id='sub-1')
			res_ok = tdd_gate.evaluate_tdd_events([ev_test, ev_red, ev_prod, ev_green])
			self.assertTrue(res_ok['verified'], res_ok)
			ev_same_batch_red = tdd_gate.build_command_tdd_event(635, f'python -m unittest discover -s "{repo / "tests"}" -p test_a.py', 'Command exited with code 1.\nFAILED (errors=1)\n', cwd=repo, sub_step=10, subagent_id='sub-1')
			res_bad = tdd_gate.evaluate_tdd_events([ev_test, ev_same_batch_red, ev_prod, ev_green])
			self.assertFalse(res_bad['verified'])
if '__main__' == __name__:
	unittest.main()
