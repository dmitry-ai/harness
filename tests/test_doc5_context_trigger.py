# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Trigger DOC-5 four-track validation from active-turn bug-report signals":
# https://github.com/dmitry-ai/harness/issues/294
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
# 2026-11-26 "Add parameterized negative regression matrix to test_doc5_context_trigger.py": https://github.com/dmitry-ai/harness/issues/371
# @used-by :meth:`Doc5ContextTriggerTests.test_external_repo_unparented_issues_do_not_force_doc5_while_local_bug_issue_does()`
def _init_local_github_repo(proj: Path, slug: str) -> None:
	code_dir = proj / '\u2c0f/\u227b/\u2655/\u26ef'
	code_dir.mkdir(parents=True, exist_ok=True)
	for args in (('init', '-b', 'main'), ('remote', 'add', 'origin', f'https://github.com/{slug}.git')):
		subprocess.run(['git', '--no-optional-locks', '-C', str(code_dir), *args], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=20)
# @used-by :meth:`Doc5ContextTriggerTests.test_active_turn_cli_failure_plus_new_parent_issue_forces_doc5_four_tracks()`
# @used-by :meth:`Doc5ContextTriggerTests.test_external_repo_unparented_issues_do_not_force_doc5_while_local_bug_issue_does()`
# @used-by :meth:`Doc5ContextTriggerTests.test_negative_regression_matrix_does_not_force_doc5()`
# @used-by :meth:`Doc5ContextTriggerTests.test_planned_child_issue_turn_with_tdd_red_failure_does_not_force_doc5()`
def _seed_bug_turn(base: Path, rows: list[dict], *, issue_actions: list[dict]) -> tuple[Path, str, dict]:
	proj = base / 'proj'
	(proj / '\ua616/data/turns').mkdir(parents=True)
	(proj / '\ua66e').mkdir(parents=True)
	(proj / '\ua616/paths.json').write_text('{"version": 1}\n', encoding='utf-8')
	cid = '55555555-6666-7777-8888-999999999999'
	tx = base / 'tx.jsonl'
	tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
	turn = {'turn_id': f'ag-{cid}-0', 'start_step': 0, 'requests': [{'id': f'{cid}-0', 'text': 'Verify rename-project live.'}], 'owned': True, 'completed': False, 'aborted': False, 'touched_files': [], 'issue_actions': issue_actions, 'exec5_violations': [], 'http_fetch_violations': [], 'issue_first_events': [], 'tdd_events': [], 'compaction': {}, 'delegation': {}}
	native = {'platform': 'antigravity', 'conversation_id': cid, 'native_backend': str(base), 'source_file': str(tx), 'primary': True, 'turns': [turn], 'active_turn_id': turn['turn_id']}
	return (proj, cid, native)
# @used-by :mod:`unittest`
class Doc5ContextTriggerTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_active_turn_cli_failure_plus_new_parent_issue_forces_doc5_four_tracks(self) -> None:
		from agent_tools import completion
		from test_df_analysis_companion_tracks import _four_track_en
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Verify rename-project live.'},
				{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py rename-project "C:/work/proj" --domain blueskypeptide.com'}}]},
				{'step_index': 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\nValueError: workflow stage degraded'},
			]
			issue_actions = [{'action': 'create', 'repo': 'dmitry-ai/harness', 'number': 277, 'parent_number': None, 'step': 5}]
			proj, cid, native = _seed_bug_turn(base, rows, issue_actions=issue_actions)
			src_doc = proj / 'notes.md'
			src_doc.write_text('Observed log details.\n', encoding='utf-8')
			dodged_reply = '# Fixes found during live check\n\nFiled issue and patched rename helper cleanly.  \n'
			with patch.object(completion, '_native', return_value=native):
				chk_bad = completion.check_answer(proj, dodged_reply, conversation=cid, platform='antigravity')
				self.assertFalse(chk_bad['valid'], chk_bad)
				# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
				self.assertFalse(chk_bad['checks']['problem_report'], chk_bad)
				self.assertTrue(chk_bad['checks']['source_grounding'], chk_bad['issues'])
				self.assertTrue(any(('DOC-5' in str(i.get('message') or '') for i in chk_bad['issues'])), chk_bad['issues'])
				full_reply = _four_track_en(f'file:///{src_doc.as_posix()}')
				chk_good = completion.check_answer(proj, full_reply, conversation=cid, platform='antigravity')
				self.assertTrue(chk_good['checks']['problem_report'], chk_good['issues'])
				self.assertTrue(chk_good['checks']['source_grounding'], chk_good['issues'])
	# @used-by :mod:`unittest`
	def test_planned_child_issue_turn_with_tdd_red_failure_does_not_force_doc5(self) -> None:
		from agent_tools import completion
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Implement M-1-1.'},
				{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py test-watchdog --timeout 120 -- python -m pytest tests/test_demo.py -x'}}]},
				{'step_index': 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\nAssertionError: Red TDD'},
			]
			issue_actions = [{'action': 'create', 'repo': 'dmitry-ai/harness', 'number': 288, 'parent_number': 282, 'step': 1}]
			proj, cid, native = _seed_bug_turn(base, rows, issue_actions=issue_actions)
			normal_reply = 'Implemented the planned subtask and verified all tests pass.  \n'
			with patch.object(completion, '_native', return_value=native):
				chk = completion.check_answer(proj, normal_reply, conversation=cid, platform='antigravity')
				self.assertTrue(chk['checks']['source_grounding'], chk['issues'])
	# 2026-11-26 "Add parameterized negative regression matrix to test_doc5_context_trigger.py": https://github.com/dmitry-ai/harness/issues/371
	# @used-by :mod:`unittest`
	def test_negative_regression_matrix_does_not_force_doc5(self) -> None:
		from agent_tools import completion
		nested_tb = json.dumps({'ok': True, 'turn_key': 'k1', 'status': 'open', 'foreign_reconciliation': [{'turn_key': 'old', 'result': {'valid': False, 'turns': [{'admission_verification': {'status': 'legacy_proof_gap'}}]}}]}, indent=2)
		matrix = (
			('turn_begin_sync_foreign_reconciliation', [{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py turn-begin "C:/work/proj" --platform antigravity'}}]}, {'step_index': 3, 'type': 'GENERIC', 'content': f'Command exited with code 0.\n\nCommand output:\n{nested_tb}'}]),
			('turn_begin_bg_foreign_reconciliation', [{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py turn-begin "C:/work/proj" --platform antigravity'}}]}, {'step_index': 3, 'type': 'GENERIC', 'content': 'Tool is running as a background task with task id: cid/task-16'}, {'step_index': 4, 'type': 'SYSTEM_MESSAGE', 'content': f'Task id "cid/task-16" finished with result:\nCommand exited with code 0.\n\nCommand output:\n{nested_tb}'}]),
			('collect_browser_external_url_failure', [{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py collect-browser "C:/work/proj" "https://example.invalid/doc"'}}]}, {'step_index': 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n{"url": "https://example.invalid/doc", "final_url": "about:blank"}'}]),
			('collect_http_external_url_failure', [{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py collect-http "C:/work/proj" "https://example.invalid/doc"'}}]}, {'step_index': 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n{"valid": false}'}]),
			('xref_check_nonzero_exit', [{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py xref-check "C:/work/proj" --lang python'}}]}, {'step_index': 3, 'type': 'GENERIC', 'content': 'Command exited with code 2.\n{"valid": false, "issues": ["drift"]}'}]),
			('git_read_nonzero_exit', [{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py git-read "C:/work/proj" status'}}]}, {'step_index': 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\nValueError: bad revision'}]),
		)
		planned_issue = [{'action': 'create', 'repo': 'dmitry-ai/harness', 'number': 319, 'parent_number': None, 'step': 10}]
		normal_reply = 'Completed planned Phase 1 implementation and verified tests pass.  \n'
		for case_name, cmd_rows in matrix:
			with self.subTest(case=case_name), tempfile.TemporaryDirectory() as tmp:
				rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Implement Phase 1.'}, *cmd_rows]
				proj, cid, native = _seed_bug_turn(Path(tmp).resolve(), rows, issue_actions=planned_issue)
				with patch.object(completion, '_native', return_value=native):
					chk = completion.check_answer(proj, normal_reply, conversation=cid, platform='antigravity')
					self.assertTrue(chk['checks']['source_grounding'], (case_name, chk['issues']))
					self.assertFalse(any(('DOC-5' in str(i.get('message') or '') for i in chk['issues'])), (case_name, chk['issues']))
	# 2026-11-26 "Add parameterized negative regression matrix to test_doc5_context_trigger.py": https://github.com/dmitry-ai/harness/issues/371
	# @used-by :mod:`unittest`
	def test_external_repo_unparented_issues_do_not_force_doc5_while_local_bug_issue_does(self) -> None:
		from agent_tools import completion
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Port library and file upstream defects.'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py worktree-land "C:/work/wt"'}}]},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n{"valid": false, "stage": "tests"}'},
			]
			ext_only = [{'action': 'create', 'repo': 'dmitry-ai/harness', 'number': 319, 'parent_number': None, 'step': 2}, {'action': 'create', 'repo': 'mage2pro/core', 'number': 469, 'parent_number': None, 'step': 10}]
			proj, cid, native = _seed_bug_turn(base, rows, issue_actions=ext_only)
			_init_local_github_repo(proj, 'dmitry-ai/harness')
			reply = 'Completed planned Phase 1 port and filed upstream defect issue.  \n'
			with patch.object(completion, '_native', return_value=native):
				chk_ok = completion.check_answer(proj, reply, conversation=cid, platform='antigravity')
				self.assertTrue(chk_ok['checks']['problem_report'], chk_ok['issues'])
				self.assertTrue(chk_ok['checks']['source_grounding'], chk_ok['issues'])
				native['turns'][0]['issue_actions'].append({'action': 'create', 'repo': 'dmitry-ai/harness', 'number': 339, 'parent_number': None, 'step': 12})
				chk_bug = completion.check_answer(proj, reply, conversation=cid, platform='antigravity')
				self.assertFalse(chk_bug['checks']['problem_report'], chk_bug)
				self.assertTrue(any(('DOC-5' in str(i.get('message') or '') for i in chk_bug['issues'])), chk_bug['issues'])
if '__main__' == __name__:
	unittest.main()