# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add anonymized golden feature-turn JSONL smoke test for DOC-5":
# https://github.com/dmitry-ai/harness/issues/372
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
FIXTURE = WT_ROOT / 'tests/fixtures/doc5_golden_feature_turn.jsonl'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# @used-by :func:`_seed_golden_workspace()`
def _extract_fixture_issue_actions(tx_path: Path) -> list[dict]:
	from agent_tools.shell_audit import extract_issue_actions_from_outputs
	rows = [json.loads(ln) for ln in tx_path.read_text(encoding='utf-8').splitlines() if ln.strip()]
	actions: list[dict] = []
	for pos, row in enumerate(rows):
		if 'PLANNER_RESPONSE' == row.get('type') and row.get('tool_calls'):
			outs = [str(c.get('content') or '') for c in rows[pos + 1:pos + 2] if 'GENERIC' == c.get('type')]
			for item in extract_issue_actions_from_outputs(outs):
				actions.append({**item, 'step': int(row.get('step_index', pos))})
	return actions
# @used-by :meth:`Doc5GoldenFeatureTurnTests.test_golden_feature_turn_snapshot_does_not_enable_problem_mode()`
def _seed_golden_workspace(base: Path) -> tuple[Path, str, dict]:
	proj = base / 'harness_ws'
	code_dir = proj / '\u2c0f/\u227b/\u2655/\u26ef'
	(proj / '\ua616/data/turns').mkdir(parents=True)
	(proj / '\ua66e').mkdir(parents=True)
	(proj / '\ua616/paths.json').write_text('{"version": 1}\n', encoding='utf-8')
	code_dir.mkdir(parents=True, exist_ok=True)
	for args in (('init', '-b', 'main'), ('remote', 'add', 'origin', 'https://github.com/dmitry-ai/harness.git')):
		subprocess.run(['git', '--no-optional-locks', '-C', str(code_dir), *args], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=20)
	cid = '77777777-8888-9999-aaaa-bbbbbbbbbbbb'
	turn = {'turn_id': f'ag-{cid}-0', 'start_step': 0, 'requests': [{'id': f'{cid}-0', 'text': 'Port core utility library and file upstream defect issues.'}], 'owned': True, 'completed': False, 'aborted': False, 'touched_files': [], 'issue_actions': _extract_fixture_issue_actions(FIXTURE), 'exec5_violations': [], 'http_fetch_violations': [], 'issue_first_events': [], 'tdd_events': [], 'compaction': {}, 'delegation': {}}
	native = {'platform': 'antigravity', 'conversation_id': cid, 'native_backend': str(base), 'source_file': str(FIXTURE), 'primary': True, 'turns': [turn], 'active_turn_id': turn['turn_id']}
	return (proj, cid, native)
# @used-by :mod:`unittest`
class Doc5GoldenFeatureTurnTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_golden_feature_turn_snapshot_does_not_enable_problem_mode(self) -> None:
		from agent_tools import completion
		self.assertTrue(FIXTURE.is_file(), f'Missing golden fixture: {FIXTURE}')
		with tempfile.TemporaryDirectory() as td:
			proj, cid, native = _seed_golden_workspace(Path(td).resolve())
			feature_reply = 'Phase 1 port completed, landed to main, pushed, and verified with all tests passing.  \n'
			with patch.object(completion, '_native', return_value=native):
				chk = completion.check_answer(proj, feature_reply, conversation=cid, platform='antigravity')
				self.assertTrue(chk['checks']['source_grounding'], chk['issues'])
				# 2026-11-28 "Build ProblemReportFixtureBuilder and hierarchical DOC-5 regression test matrix": https://github.com/dmitry-ai/harness/issues/431
				self.assertTrue(chk['checks']['problem_report'], chk['issues'])
				self.assertFalse(any(('DOC-5' in str(i.get('message') or '') for i in chk['issues'])), chk['issues'])
				native['turns'][0]['issue_actions'].append({'action': 'create', 'repo': 'dmitry-ai/harness', 'number': 339, 'parent_number': None, 'step': 950})
				chk_bug = completion.check_answer(proj, feature_reply, conversation=cid, platform='antigravity')
				self.assertFalse(chk_bug['checks']['problem_report'], chk_bug)
				self.assertTrue(any(('DOC-5' in str(i.get('message') or '') for i in chk_bug['issues'])), chk_bug['issues'])
if '__main__' == __name__:
	unittest.main()
