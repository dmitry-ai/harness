# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Trigger DOC-5 four-track validation from active-turn bug-report signals":
# https://github.com/dmitry-ai/harness/issues/294
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
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
# @used-by :meth:`Doc5ContextTriggerTests.test_active_turn_cli_failure_plus_new_parent_issue_forces_doc5_four_tracks()`
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
				self.assertFalse(chk_bad['checks']['source_grounding'])
				self.assertTrue(any(('DOC-5' in str(i.get('message') or '') for i in chk_bad['issues'])), chk_bad['issues'])
				full_reply = _four_track_en(f'file:///{src_doc.as_posix()}')
				chk_good = completion.check_answer(proj, full_reply, conversation=cid, platform='antigravity')
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
if '__main__' == __name__:
	unittest.main()