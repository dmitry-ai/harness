# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix top-level JSON parsing and workspace repo scoping in doc5_context.py":
# https://github.com/dmitry-ai/harness/issues/368
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# @used-by :meth:`CliOutputJsonAndDoc5Tests.test_local_repo_scoping_ignores_external_upstream_issues_and_preserves_fallback()`
def _init_git_origin(repo: Path, slug: str) -> None:
	repo.mkdir(parents=True, exist_ok=True)
	for args in (('init', '-b', 'main'), ('remote', 'add', 'origin', f'https://github.com/{slug}.git')):
		subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=20)
# @used-by :meth:`CliOutputJsonAndDoc5Tests.test_excluded_fetchers_and_readonly_linters_do_not_trigger_doc5()`
# @used-by :meth:`CliOutputJsonAndDoc5Tests.test_local_repo_scoping_ignores_external_upstream_issues_and_preserves_fallback()`
def _write_trace(base: Path, rows: list[dict], issue_actions: list[dict]) -> tuple[dict, dict]:
	cid = 'aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb'
	tx = base / 'tx.jsonl'
	tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
	turn = {'turn_id': f'ag-{cid}-0', 'start_step': 0, 'requests': [{'id': f'{cid}-0', 'text': 'Implement planned feature.'}], 'owned': True, 'completed': False, 'aborted': False, 'issue_actions': issue_actions}
	native = {'platform': 'antigravity', 'conversation_id': cid, 'native_backend': str(base), 'source_file': str(tx), 'primary': True, 'turns': [turn], 'active_turn_id': turn['turn_id']}
	return (turn, native)
# @used-by :mod:`unittest`
class CliOutputJsonAndDoc5Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_top_level_json_parser_ignores_nested_valid_false_and_catches_top_level_failures(self) -> None:
		from agent_tools.cli_output_json import extract_top_level_json_objects, top_level_json_has_failure
		nested_ok = 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'turn_key': 'k1', 'foreign_reconciliation': [{'turn_key': 'old', 'result': {'valid': False, 'status': 'legacy_proof_gap'}}]}, indent=2) + '\nLog: file:///tmp/task.log\n'
		objs, trunc_fail = extract_top_level_json_objects(nested_ok)
		self.assertEqual(1, len(objs))
		self.assertFalse(trunc_fail)
		self.assertFalse(top_level_json_has_failure(nested_ok))
		multi_json = 'Command exited with code 0.\n\nCommand output:\n{"ok": true}\n{"valid": false, "issues": ["bad"]}\n'
		self.assertEqual(2, len(extract_top_level_json_objects(multi_json)[0]))
		self.assertTrue(top_level_json_has_failure(multi_json))
		top_ok_false = 'Command exited with code 0.\n\nCommand output:\n{\n  "ok": false,\n  "stage": "lint"\n}\n'
		self.assertTrue(top_level_json_has_failure(top_ok_false))
		trunc_nested = 'Command exited with code 0.\n\nCommand output:\n{\n  "turn_key": "k1",\n  "foreign_reconciliation": [\n    {\n      "result": {\n        "valid": false\n'
		self.assertFalse(top_level_json_has_failure(trunc_nested))
		trunc_top = 'Command exited with code 0.\n\nCommand output:\n{\n  "valid": false,\n  "issues": [\n    "still open'
		self.assertTrue(top_level_json_has_failure(trunc_top))
	# @used-by :mod:`unittest`
	def test_excluded_fetchers_and_readonly_linters_do_not_trigger_doc5(self) -> None:
		from agent_tools.doc5_context import turn_requires_doc5_problem_analysis
		for subcmd in ('collect', 'collect-http', 'collect-browser', 'xref-check', 'git-read'):
			with self.subTest(subcmd=subcmd), tempfile.TemporaryDirectory() as td:
				base = Path(td).resolve()
				rows = [
					{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Implement planned task.'},
					{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python harness.py {subcmd} "C:/work/proj"'}}]},
					{'step_index': 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n{"valid": false}'},
				]
				turn, native = _write_trace(base, rows, [{'action': 'create', 'repo': 'dmitry-ai/harness', 'number': 319, 'parent_number': None, 'step': 10}])
				self.assertFalse(turn_requires_doc5_problem_analysis({'root': base, 'turn': turn, 'native': native}))
	# @used-by :mod:`unittest`
	def test_local_repo_scoping_ignores_external_upstream_issues_and_preserves_fallback(self) -> None:
		from agent_tools.doc5_context import turn_requires_doc5_problem_analysis
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			ws = base / 'ws'
			_init_git_origin(ws / '\u2c0f/\u227b/\u2655/\u26ef', 'dmitry-ai/harness')
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Port library.'},
				{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python harness.py worktree-land "C:/work/wt"'}}]},
				{'step_index': 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n{"valid": false}'},
			]
			turn_ext, nat_ext = _write_trace(base, rows, [{'action': 'create', 'repo': 'mage2pro/core', 'number': 469, 'parent_number': None, 'step': 10}])
			self.assertFalse(turn_requires_doc5_problem_analysis({'root': ws, 'turn': turn_ext, 'native': nat_ext}))
			turn_loc, nat_loc = _write_trace(base, rows, [{'action': 'create', 'repo': 'dmitry-ai/harness', 'number': 339, 'parent_number': None, 'step': 10}])
			self.assertTrue(turn_requires_doc5_problem_analysis({'root': ws, 'turn': turn_loc, 'native': nat_loc}))
			no_git_ws = base / 'plain_proj'
			no_git_ws.mkdir()
			self.assertTrue(turn_requires_doc5_problem_analysis({'root': no_git_ws, 'turn': turn_ext, 'native': nat_ext}))
if '__main__' == __name__:
	unittest.main()
