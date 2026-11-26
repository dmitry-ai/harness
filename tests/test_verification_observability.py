# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add verification observability gate for failed shadow-replay runs":
# https://github.com/dmitry-ai/harness/issues/296
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
for p in (SCRIPTS,):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
# @used-by :meth:`VerificationObservabilityTests.test_failed_shadow_replay_blocks_silent_reply_and_issue_close_and_passes_on_disclosure_or_rerun()`
# @used-by :meth:`VerificationObservabilityTests.test_prepare_enforces_verification_observability_check()`
def _seed_obs_turn(base: Path, rows: list[dict], *, issue_actions: list[dict]=()) -> tuple[Path, str, Path, dict, dict]:
	proj = base / 'proj'
	(proj / '\ua616/data/turns').mkdir(parents=True)
	(proj / '\ua66e').mkdir(parents=True)
	(proj / '\ua616/paths.json').write_text('{"version": 1}\n', encoding='utf-8')
	cid = '66666666-7777-8888-9999-aaaaaaaaaaaa'
	tx = base / 'tx.jsonl'
	tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
	turn = {'turn_id': f'ag-{cid}-0', 'start_step': 0, 'requests': [{'id': f'{cid}-0', 'text': 'Verify rename via shadow-replay.'}], 'owned': True, 'completed': False, 'aborted': False, 'touched_files': [], 'issue_actions': list(issue_actions), 'exec5_violations': [], 'http_fetch_violations': [], 'issue_first_events': [], 'tdd_events': [], 'compaction': {}, 'delegation': {}}
	native = {'platform': 'antigravity', 'conversation_id': cid, 'native_backend': str(base), 'source_file': str(tx), 'primary': True, 'turns': [turn], 'active_turn_id': turn['turn_id']}
	return (proj, cid, tx, turn, native)
# @used-by :mod:`unittest`
class VerificationObservabilityTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_failed_shadow_replay_blocks_silent_reply_and_issue_close_and_passes_on_disclosure_or_rerun(self) -> None:
		from agent_tools import completion
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			fail_rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Verify rename via shadow-replay.'},
				{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py shadow-replay "C:/work/proj" --exec-rename-domain blueskypeptide.com'}}]},
				{'step_index': 3, 'type': 'GENERIC', 'content': 'Command exited with code 2.\n{"valid": false, "errors": ["stage regressed"]}'},
			]
			proj, cid, tx, turn, native = _seed_obs_turn(base, fail_rows)
			with patch.object(completion, '_native', return_value=native):
				silent = completion.check_answer(proj, 'Everything looks good and completed cleanly.  \n', conversation=cid, platform='antigravity')
				self.assertFalse(silent['valid'], silent)
				self.assertFalse(silent['checks']['verification_observability'])
				disclosed = completion.check_answer(proj, 'The shadow-replay verification failed with valid: false (exit 2) due to stage regression.  \n', conversation=cid, platform='antigravity')
				self.assertTrue(disclosed['checks']['verification_observability'], disclosed)
				turn['issue_actions'] = [{'action': 'close', 'repo': 'dmitry-ai/harness', 'number': 277, 'step': 5}]
				closed_bad = completion.check_answer(proj, 'The shadow-replay verification failed with valid: false (exit 2), closed #277 anyway.  \n', conversation=cid, platform='antigravity')
				self.assertFalse(closed_bad['valid'], closed_bad)
				self.assertFalse(closed_bad['checks']['verification_observability'])
				rerun_rows = [*fail_rows, {'step_index': 6, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py shadow-replay "C:/work/proj" --exec-rename-domain blueskypeptide.com'}}]}, {'step_index': 7, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n{"valid": true, "stages_verified": ["command_exec", "post_rename_verify"]}'}]
				tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rerun_rows)), encoding='utf-8')
				rerun_ok = completion.check_answer(proj, 'Re-ran shadow-replay and verified all stages pass.  \n', conversation=cid, platform='antigravity')
				self.assertTrue(rerun_ok['checks']['verification_observability'], rerun_ok)
	# @used-by :mod:`unittest`
	def test_prepare_enforces_verification_observability_check(self) -> None:
		from agent_tools import completion
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			fail_rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Verify rename via shadow-replay.'},
				{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py shadow-replay "C:/work/proj" --exec-rename-domain blueskypeptide.com'}}]},
				{'step_index': 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n{"valid": false}'},
			]
			proj, cid, _tx, _turn, native = _seed_obs_turn(base, fail_rows)
			with patch.object(completion, '_native', return_value=native):
				with self.assertRaises(ValueError) as ctx:
					completion.prepare(proj, 'All checks completed without issues.  \n', conversation=cid, platform='antigravity')
				self.assertIn('verification_observability_check', str(ctx.exception))
if '__main__' == __name__:
	unittest.main()