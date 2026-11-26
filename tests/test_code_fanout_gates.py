# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import issue_first_gate, tdd_gate
from agent_tools.worktree_flow import worktree_begin, worktree_cleanup
# @used-by :func:`_setup_fanout_project()`
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', *args], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
# @used-by :meth:`CodeFanoutGatesTests.test_child_subagent_blocked_when_parent_issue_closed_or_missing_evidence()`
# @used-by :meth:`CodeFanoutGatesTests.test_child_subagent_inherits_verified_open_parent_from_turn_state_and_summary_db()`
# @used-by :meth:`CodeFanoutGatesTests.test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset()`
# @used-by :meth:`CodeFanoutGatesTests.test_parallel_deleted_worktrees_isolate_tdd_scopes_and_accept_main_full_green()`
def _setup_fanout_project(root: Path, slug: str='acme/demo') -> tuple[Path, Path]:
	proj = root / 'proj'
	(proj / '\ua616/data/turns').mkdir(parents=True, exist_ok=True)
	(proj / '\ua616/KB/Evidence/GitHub' / slug.replace('/', '__')).mkdir(parents=True, exist_ok=True)
	code = proj / 'code'
	code.mkdir(parents=True, exist_ok=True)
	_git(code, 'init', '-b', 'main')
	_git(code, 'config', 'user.email', 'test@example.com')
	_git(code, 'config', 'user.name', 'Test')
	_git(code, 'remote', 'add', 'origin', f'https://github.com/{slug}.git')
	(code / 'tests').mkdir()
	(code / 'tests/test_a.py').write_text('import unittest\nclass A(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertTrue(True)\n', encoding='utf-8')
	(code / 'tests/test_b.py').write_text('import unittest\nclass B(unittest.TestCase):\n\tdef test_b(self):\n\t\tself.assertTrue(True)\n', encoding='utf-8')
	(code / 'mod_a.py').write_text('x = 1\n', encoding='utf-8')
	(code / 'mod_b.py').write_text('y = 1\n', encoding='utf-8')
	_git(code, 'add', '.')
	_git(code, 'commit', '-m', 'init')
	return (proj, code)
# @used-by :meth:`CodeFanoutGatesTests.test_child_subagent_blocked_when_parent_issue_closed_or_missing_evidence()`
# @used-by :meth:`CodeFanoutGatesTests.test_child_subagent_inherits_verified_open_parent_from_turn_state_and_summary_db()`
# @used-by :meth:`CodeFanoutGatesTests.test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset()`
def _write_evidence(proj: Path, slug: str, number: int, *, state: str='open', parent_number: int | None=None) -> Path:
	ev_dir = proj / '\ua616/KB/Evidence/GitHub' / slug.replace('/', '__')
	ev_dir.mkdir(parents=True, exist_ok=True)
	body = f'Parent: #{parent_number}\n\n## Scope\nSubtask.\n' if None is not parent_number else '## Problem\nDetails.\n'
	data: dict = {'body': body, 'html_url': f'https://github.com/{slug}/issues/{number}', 'issue_number': number, 'kind': 'issue', 'number': number, 'repo': slug, 'state': state, 'title': f'Issue {number}', 'url': f'https://github.com/{slug}/issues/{number}'}
	if None is not parent_number:
		data['parent_number'] = parent_number
		data['parent_url'] = f'https://github.com/{slug}/issues/{parent_number}'
	out = ev_dir / f'issue-{number}.json'
	out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
	return out
# @used-by :meth:`CodeFanoutGatesTests.test_child_subagent_blocked_when_parent_issue_closed_or_missing_evidence()`
# @used-by :meth:`CodeFanoutGatesTests.test_child_subagent_inherits_verified_open_parent_from_turn_state_and_summary_db()`
# @used-by :meth:`CodeFanoutGatesTests.test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset()`
def _write_parent_turn(proj: Path, parent_cid: str, slug: str, issues: list[dict]) -> Path:
	gh_map: dict = {}
	for item in issues:
		num = item['number']
		url = f'https://github.com/{slug}/issues/{num}'
		entry: dict = {'actions': ['create'], 'last_action': 'create', 'number': num, 'repo': slug, 'state': item.get('state', 'open'), 'url': url}
		if None is not item.get('parent_number'):
			entry['parent_number'] = item['parent_number']
		gh_map[url] = entry
	tfile = proj / '\ua616/data/turns/parentturn.json'
	tfile.write_text(json.dumps({'conversation_id': parent_cid, 'github_issues': gh_map, 'role': 'primary', 'status': 'open'}, ensure_ascii=False, indent=2), encoding='utf-8')
	return tfile
# @used-by :meth:`CodeFanoutGatesTests.test_child_subagent_inherits_verified_open_parent_from_turn_state_and_summary_db()`
def _write_summary_db(backend: Path, child_cid: str, parent_cid: str) -> Path:
	db_path = backend / 'conversation_summaries.db'
	conn = sqlite3.connect(str(db_path))
	try:
		conn.execute('CREATE TABLE conversation_summaries (conversation_id TEXT PRIMARY KEY, parent_conversation_id TEXT, status TEXT)')
		conn.execute('INSERT INTO conversation_summaries VALUES (?, ?, ?)', (child_cid, parent_cid, 'RUNNING'))
		conn.commit()
	finally:
		conn.close()
	return db_path
# @used-by :meth:`CodeFanoutGatesTests.test_child_subagent_blocked_when_parent_issue_closed_or_missing_evidence()`
# @used-by :meth:`CodeFanoutGatesTests.test_child_subagent_inherits_verified_open_parent_from_turn_state_and_summary_db()`
def _write_tx(path: Path, rows: list[dict]) -> Path:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(''.join((json.dumps(row, ensure_ascii=False) + '\n' for row in rows)), encoding='utf-8')
	return path
# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
class CodeFanoutGatesTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_child_subagent_blocked_when_parent_issue_closed_or_missing_evidence(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			proj, code = _setup_fanout_project(root)
			wt = Path(worktree_begin(code, 'sub-blocked', worktrees_dir=proj / '\ua616/data/worktrees')['worktree'])
			child_tx = _write_tx(root / 'child/transcript.jsonl', [{'content': 'Work in sub-blocked', 'step_index': 0, 'type': 'SYSTEM_MESSAGE'}])
			target = wt / 'tests/test_sub.py'
			w_args = {'Content': 'import unittest\nclass S(unittest.TestCase):\n\tdef test_s(self):\n\t\tself.assertEqual(1, 1)\n', 'Path': str(target)}
			payload = {'conversationId': 'child-b', 'cwd': str(proj), 'parentConversationId': 'parent-b', 'transcriptPath': str(child_tx)}
			_write_parent_turn(proj, 'parent-b', 'acme/demo', [{'number': 20, 'state': 'open'}])
			err_missing = issue_first_gate.evaluate_pre_tool_use_issue_first('write_file', w_args, payload)
			self.assertIsNotNone(err_missing)
			self.assertIn('ISSUE-FIRST-GATE', err_missing)
			_write_evidence(proj, 'acme/demo', 21, state='closed')
			_write_parent_turn(proj, 'parent-b', 'acme/demo', [{'number': 21, 'state': 'open'}])
			err_closed = issue_first_gate.evaluate_pre_tool_use_issue_first('write_file', w_args, payload)
			self.assertIsNotNone(err_closed)
			self.assertIn('ISSUE-FIRST-GATE', err_closed)
			_write_evidence(proj, 'acme/demo', 22, state='open', parent_number=21)
			_write_parent_turn(proj, 'parent-b', 'acme/demo', [{'number': 22, 'parent_number': 21, 'state': 'open'}])
			err_closed_parent = issue_first_gate.evaluate_pre_tool_use_issue_first('write_file', w_args, payload)
			self.assertIsNotNone(err_closed_parent)
			self.assertIn('ISSUE-FIRST-GATE', err_closed_parent)
			worktree_cleanup(code, wt, force=True)
	# @used-by :mod:`unittest`
	def test_child_subagent_inherits_verified_open_parent_from_turn_state_and_summary_db(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			proj, code = _setup_fanout_project(root)
			parent_cid = '11111111-2222-3333-4444-555555555555'
			child_cid = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
			_write_evidence(proj, 'acme/demo', 10, state='open')
			_write_evidence(proj, 'acme/demo', 11, state='open', parent_number=10)
			_write_parent_turn(proj, parent_cid, 'acme/demo', [{'number': 10, 'state': 'open'}, {'number': 11, 'parent_number': 10, 'state': 'open'}])
			wt = Path(worktree_begin(code, 'sub-ok', worktrees_dir=proj / '\ua616/data/worktrees')['worktree'])
			backend = root / 'backend'
			child_tx = _write_tx(backend / f'brain/{child_cid}/.system_generated/logs/transcript.jsonl', [{'content': f'[Message] timestamp=2026-11-26T16:00:00Z sender={parent_cid} content=Implement #11', 'step_index': 0, 'type': 'SYSTEM_MESSAGE'}])
			_write_summary_db(backend, child_cid, parent_cid)
			w_args = {'Content': 'import unittest\nclass S(unittest.TestCase):\n\tdef test_s(self):\n\t\tself.assertEqual(1, 1)\n', 'Path': str(wt / 'tests/test_sub.py')}
			res_explicit = issue_first_gate.evaluate_pre_tool_use_issue_first('write_file', w_args, {'conversationId': child_cid, 'cwd': str(wt), 'parentConversationId': parent_cid, 'transcriptPath': str(child_tx)})
			self.assertIsNone(res_explicit)
			res_db = issue_first_gate.evaluate_pre_tool_use_issue_first('write_file', w_args, {'conversationId': child_cid, 'cwd': str(proj), 'transcriptPath': str(child_tx)})
			self.assertIsNone(res_db)
			sender_tx = _write_tx(root / 'isolated_child/transcript.jsonl', [{'content': f'[Message] timestamp=2026-11-26T16:00:00Z sender={parent_cid} content=Implement #11', 'step_index': 0, 'type': 'SYSTEM_MESSAGE'}])
			res_sender = issue_first_gate.evaluate_pre_tool_use_issue_first('write_file', w_args, {'cwd': str(proj), 'transcriptPath': str(sender_tx)})
			self.assertIsNone(res_sender)
			primary_tx = _write_tx(root / 'primary/transcript.jsonl', [{'content': 'Add new unrelated feature', 'step_index': 0, 'type': 'USER_INPUT'}])
			err_primary = issue_first_gate.evaluate_pre_tool_use_issue_first('write_file', w_args, {'conversationId': 'other-primary', 'cwd': str(proj), 'transcriptPath': str(primary_tx)})
			self.assertIsNotNone(err_primary)
			self.assertIn('ISSUE-FIRST-GATE', err_primary)
			worktree_cleanup(code, wt, force=True)
	# 2026-11-26 "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out": https://github.com/dmitry-ai/harness/issues/351
	# @used-by :mod:`unittest`
	def test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset(self) -> None:
		from agent_tools.tdd import worktree_scope
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			proj, code = _setup_fanout_project(root)
			_write_evidence(proj, 'acme/demo', 10, state='open')
			_write_parent_turn(proj, 'parent-cid-m', 'acme/demo', [{'number': 10, 'state': 'open'}])
			w_args = {'Content': 'import unittest\nclass M(unittest.TestCase):\n\tdef test_m(self):\n\t\tself.assertEqual(1, 1)\n', 'Path': str(code / 'tests/test_m.py')}
			self.assertIsNone(issue_first_gate.evaluate_pre_tool_use_issue_first('write_file', w_args, {'cwd': str(proj), 'parentConversationId': 'parent-cid-m'}))
			err_no_tx = issue_first_gate.evaluate_pre_tool_use_issue_first('write_file', w_args, {'cwd': str(proj)})
			self.assertIsNotNone(err_no_tx)
			self.assertIn('transcript unavailable', err_no_tx)
			ta_path = code / 'tests/test_a.py'
			ev_t = tdd_gate.build_file_write_tdd_event(1, ta_path, cwd=code)
			ev_r = tdd_gate.build_command_tdd_event(2, f'python -m unittest -f -b "{ta_path}"', 'Command exited with code 1.\nFAILED (failures=1)\n', cwd=code)
			ev_p = tdd_gate.build_file_write_tdd_event(3, code / 'mod_a.py', cwd=code)
			ev_c = tdd_gate.build_command_tdd_event(4, f'git -C "{code}" commit -m https://github.com/acme/demo/issues/10', 'Command exited with code 0.\n[main 2222222] ok\n', cwd=code)
			res = tdd_gate.evaluate_tdd_events([ev_t, ev_r, ev_p, ev_c], require_final_full_green=False)
			self.assertTrue(res['verified'], res)
			self.assertEqual('IDLE', res['scopes'][str(code)]['state'])
			self.assertTrue(worktree_scope.scope_matches_commit(str(code), str(code)))
			self.assertFalse(worktree_scope.scope_matches_commit(str(code), str(proj)))
			self.assertFalse(worktree_scope.scope_matches_commit(f'{code}::wt:wt-x', str(code)))
	# @used-by :mod:`unittest`
	def test_parallel_deleted_worktrees_isolate_tdd_scopes_and_accept_main_full_green(self) -> None:
		harness_py = SCRIPTS / 'harness.py'
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			proj, code = _setup_fanout_project(root)
			wt_base = proj / '\ua616/data/worktrees'
			wt_a = Path(worktree_begin(code, 'wt-alpha', worktrees_dir=wt_base)['worktree'])
			wt_b = Path(worktree_begin(code, 'wt-beta', worktrees_dir=wt_base)['worktree'])
			worktree_cleanup(code, wt_a, force=True)
			worktree_cleanup(code, wt_b, force=True)
			self.assertEqual(code.resolve(), tdd_gate.resolve_code_scope(wt_a / 'mod_a.py'))
			self.assertEqual(code.resolve(), tdd_gate.resolve_code_scope(wt_b / 'mod_b.py'))
			ta_path, tb_path = (wt_a / 'tests/test_a.py', wt_b / 'tests/test_b.py')
			wt_a_tests, code_tests = (wt_a / 'tests', code / 'tests')
			ev_ta = tdd_gate.build_file_write_tdd_event(1, ta_path, cwd=wt_a)
			ev_red_a = tdd_gate.build_command_tdd_event(2, f'python -m unittest -f -b "{ta_path}"', 'Command exited with code 1.\nFAILED (failures=1)\n', cwd=wt_a)
			ev_pa = tdd_gate.build_file_write_tdd_event(3, wt_a / 'mod_a.py', cwd=wt_a)
			ev_tb = tdd_gate.build_file_write_tdd_event(4, tb_path, cwd=wt_b)
			ev_pb = tdd_gate.build_file_write_tdd_event(5, wt_b / 'mod_b.py', cwd=wt_b)
			res_leak = tdd_gate.evaluate_tdd_events([ev_ta, ev_red_a, ev_pa, ev_tb, ev_pb], require_final_full_green=False)
			self.assertFalse(res_leak['verified'], res_leak)
			self.assertEqual(2, len(res_leak['scopes']), res_leak['scopes'])
			self.assertTrue(any(('TDD-RED-GATE' in v and 'mod_b.py' in v for v in res_leak['violations'])), res_leak['violations'])
			ev_red_b = tdd_gate.build_command_tdd_event(5, f'python -m unittest -f -b "{tb_path}"', 'Command exited with code 1.\nFAILED (failures=1)\n', cwd=wt_b)
			ev_pb_ok = tdd_gate.build_file_write_tdd_event(6, wt_b / 'mod_b.py', cwd=wt_b)
			ev_commit_a = tdd_gate.build_command_tdd_event(7, f'git -C "{wt_a}" commit -m https://github.com/acme/demo/issues/11', 'Command exited with code 0.\n[task/a 1111111] ok\n', cwd=wt_a)
			ev_full_a = tdd_gate.build_command_tdd_event(8, f'python "{harness_py}" run-tests "{wt_a_tests}"', 'Command exited with code 0.\nRan 2 tests in 0.1s\nOK\n', cwd=wt_a)
			res_only_a = tdd_gate.evaluate_tdd_events([ev_ta, ev_red_a, ev_pa, ev_tb, ev_red_b, ev_pb_ok, ev_commit_a, ev_full_a], require_final_full_green=True)
			self.assertFalse(res_only_a['verified'], res_only_a)
			self.assertTrue(any(('TDD-FULL-GATE' in v and 'wt-beta' in v for v in res_only_a['violations'])), res_only_a['violations'])
			ev_full_main = tdd_gate.build_command_tdd_event(9, f'python "{harness_py}" run-tests "{code_tests}"', 'Command exited with code 0.\nRan 2 tests in 0.1s\nOK\n', cwd=code)
			res_both = tdd_gate.evaluate_tdd_events([ev_ta, ev_red_a, ev_pa, ev_tb, ev_red_b, ev_pb_ok, ev_commit_a, ev_full_main], require_final_full_green=True)
			self.assertTrue(res_both['verified'], res_both)
			self.assertEqual(2, len(res_both['scopes']), res_both['scopes'])
			self.assertEqual('IDLE', res_both['scopes'][f'{code}::wt:wt-alpha']['state'])
			self.assertEqual('GREEN_IMPLEMENTING', res_both['scopes'][f'{code}::wt:wt-beta']['state'])
			for st in res_both['scopes'].values():
				self.assertEqual(9, st['last_full_green_step'])
if '__main__' == __name__:
	unittest.main()
