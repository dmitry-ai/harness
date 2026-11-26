# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce verified CLI execution grounding in answer checks and restore EXEC-2 rule":
# https://github.com/dmitry-ai/harness/issues/290
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
# @used-by :meth:`CliCommandGroundingTests.test_answer_check_blocks_unverified_and_allows_shadow_replay_or_disclaimer()`
# @used-by :meth:`CliCommandGroundingTests.test_prepare_rejects_unverified_cli_recommendation()`
def _seed_turn_native(base: Path, rows: list[dict], *, req_text: str) -> tuple[Path, str, Path, dict]:
	proj = base / 'proj'
	(proj / '\ua616/data/turns').mkdir(parents=True)
	(proj / '\ua66e').mkdir(parents=True)
	(proj / '\ua616/paths.json').write_text('{"version": 1}\n', encoding='utf-8')
	cid = '11111111-2222-3333-4444-555555555555'
	tx = base / 'tx.jsonl'
	tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
	turn = {'turn_id': f'ag-{cid}-0', 'start_step': 0, 'requests': [{'id': f'{cid}-0', 'text': req_text}], 'owned': True, 'completed': False, 'aborted': False, 'touched_files': [], 'issue_actions': [], 'exec5_violations': [], 'http_fetch_violations': [], 'issue_first_events': [], 'tdd_events': [], 'compaction': {}, 'delegation': {}}
	native = {'platform': 'antigravity', 'conversation_id': cid, 'native_backend': str(base), 'source_file': str(tx), 'primary': True, 'turns': [turn], 'active_turn_id': turn['turn_id']}
	return (proj, cid, tx, native)
# @used-by :mod:`unittest`
class CliCommandGroundingTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_answer_check_blocks_unverified_and_allows_shadow_replay_or_disclaimer(self) -> None:
		from agent_tools import completion
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			base_rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Rename the project to blueskypeptide.com.'}]
			proj, cid, tx, native = _seed_turn_native(base, base_rows, req_text='Rename the project to blueskypeptide.com.')
			rec_reply = 'Run this command to promote the folder:  \n`python "C:/work/harness/scripts/harness.py" rename-project "C:/work/upwork/2026/11/23/1 - Magento & GA4" --domain blueskypeptide.com`.  \n'
			with patch.object(completion, '_native', return_value=native):
				chk_fail = completion.check_answer(proj, rec_reply, conversation=cid, platform='antigravity')
				self.assertFalse(chk_fail['valid'], chk_fail)
				self.assertFalse(chk_fail['checks']['source_grounding'])
				self.assertTrue(any(('EXEC-2' in str(i.get('message') or '') for i in chk_fail['issues'])), chk_fail['issues'])
				warned_reply = rec_reply + 'Warning: not tested on a live or shadow project.  \n'
				chk_warn = completion.check_answer(proj, warned_reply, conversation=cid, platform='antigravity')
				self.assertTrue(chk_warn['valid'], chk_warn)
				template_reply = 'Template usage: `harness.py rename-project "<project>" --domain <host>`.  \n'
				chk_tpl = completion.check_answer(proj, template_reply, conversation=cid, platform='antigravity')
				self.assertTrue(chk_tpl['valid'], chk_tpl)
				quoted_reply = '> `python "C:/work/harness/scripts/harness.py" rename-project "C:/work/upwork/2026/11/23/1 - Magento & GA4" --domain blueskypeptide.com`  \n\nObserved the quoted command in prior logs.  \n'
				chk_q = completion.check_answer(proj, quoted_reply, conversation=cid, platform='antigravity')
				self.assertTrue(chk_q['valid'], chk_q)
				shadow_rows = [*base_rows, {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py shadow-replay "C:/work/upwork/2026/11/23/1 - Magento & GA4" --exec-rename-domain blueskypeptide.com'}}]}, {'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n{"valid": true, "stages_verified": ["command_exec", "post_rename_verify"]}'}]
				tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in shadow_rows)), encoding='utf-8')
				chk_ok = completion.check_answer(proj, rec_reply, conversation=cid, platform='antigravity')
				self.assertTrue(chk_ok['valid'], chk_ok)
	# @used-by :mod:`unittest`
	def test_prepare_rejects_unverified_cli_recommendation(self) -> None:
		from agent_tools import completion
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Promote the project directory.'}]
			proj, cid, _tx, native = _seed_turn_native(base, rows, req_text='Promote the project directory.')
			rec_reply = 'Execute `python "C:/work/harness/scripts/harness.py" rename-project "C:/work/upwork/2026/11/23/1 - Magento & GA4" --domain blueskypeptide.com`.  \n'
			with patch.object(completion, '_native', return_value=native):
				with self.assertRaises(ValueError) as ctx:
					completion.prepare(proj, rec_reply, conversation=cid, platform='antigravity')
				self.assertIn('EXEC-2', str(ctx.exception))
	# @used-by :mod:`unittest`
	def test_exec2_rule_contains_shadow_replay_requirement_and_passes_rules_audit(self) -> None:
		from agent_tools.rules_audit import audit_rules
		rule_text = (WT_ROOT / 'rules/08-execution-and-tools.md').read_text(encoding='utf-8')
		self.assertIn('shadow-replay', rule_text)
		self.assertIn('mutating commands', rule_text)
		audit = audit_rules(WT_ROOT)
		self.assertTrue(audit['valid'], audit)
if '__main__' == __name__:
	unittest.main()