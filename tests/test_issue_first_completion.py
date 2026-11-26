# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))

from agent_tools import completion, git_gate
# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
from agent_tools.repo_tags import ensure_commit_tag
import check_stop_gate


# @used-by :func:`_wire()`
def _varint(val: int) -> bytes:
	out = bytearray()
	while True:
		b = val & 0x7F
		val >>= 7
		if val:
			out.append(b | 0x80)
		else:
			out.append(b)
			return bytes(out)


# @used-by :func:`_setup_antigravity_conv()`
def _wire(field_num: int, payload: bytes) -> bytes:
	return _varint((field_num << 3) | 2) + _varint(len(payload)) + payload


# @used-by :meth:`IssueFirstTurnCompletionAndGitTests.test_antigravity_issue_first_gate_blocks_retroactive_and_passes_parent_then_tdd()`
# @used-by :meth:`IssueFirstTurnCompletionAndGitTests.test_codex_apply_patch_and_exec_command_issue_first_gate()`
# @used-by :meth:`IssueFirstTurnCompletionAndGitTests.test_git_gate_verify_issue_workflow_enforces_slug_and_saved_evidence_in_github_code_repo()`
def _write_issue_ev(proj: Path, slug: str, num: int, *, state: str = 'closed', parent_number: int | None = None) -> Path:
	ev_dir = proj / '_/ꘖ/KB/Evidence/GitHub' / slug.replace('/', '__')
	ev_dir.mkdir(parents=True, exist_ok=True)
	body = f'Parent: #{parent_number}\n\n## Scope\nSubtask.\n' if parent_number else '## Problem\nRoot causes.\n'
	data: dict = {
		'url': f'https://github.com/{slug}/issues/{num}',
		'html_url': f'https://github.com/{slug}/issues/{num}',
		'repo': slug,
		'kind': 'issue',
		'number': num,
		'issue_number': num,
		'state': state,
		'title': f'Issue {num}',
		'body': body,
	}
	if parent_number is not None:
		data['parent_number'] = parent_number
		data['parent_url'] = f'https://github.com/{slug}/issues/{parent_number}'
	p = ev_dir / f'issue-{num}.json'
	p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
	return p


# 2026-11-24
# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/175
_EMPTY_TEMPLATE: list[tuple[tempfile.TemporaryDirectory, Path, Path]] = []


# @used-by :func:`_init_github_project()`
def _get_empty_git_template() -> tuple[Path, Path]:
	if not _EMPTY_TEMPLATE:
		td = tempfile.TemporaryDirectory()
		root = Path(td.name).resolve()
		bare = root / 'bare.git'
		code = root / 'code'
		code.mkdir()
		subprocess.run(['git', 'init', '--bare', '-b', 'main', str(bare)], check=True, capture_output=True)
		subprocess.run(['git', 'init', '-b', 'main', str(code)], check=True, capture_output=True)
		cfg = code / '.git/config'
		cfg.write_text(cfg.read_text(encoding='utf-8') + '[user]\n\temail = test@example.com\n\tname = Test User\n', encoding='utf-8')
		_EMPTY_TEMPLATE.append((td, bare, code))
	_, bare, code = _EMPTY_TEMPLATE[0]
	return (bare, code)


# @used-by :meth:`IssueFirstTurnCompletionAndGitTests.test_antigravity_issue_first_gate_blocks_retroactive_and_passes_parent_then_tdd()`
# @used-by :meth:`IssueFirstTurnCompletionAndGitTests.test_cli_issue_first_check_read_only_and_legacy_delivered_immutability()`
# @used-by :meth:`IssueFirstTurnCompletionAndGitTests.test_codex_apply_patch_and_exec_command_issue_first_gate()`
# @used-by :meth:`IssueFirstTurnCompletionAndGitTests.test_git_gate_verify_issue_workflow_enforces_slug_and_saved_evidence_in_github_code_repo()`
def _init_github_project(base: Path, *, slug: str = 'acme/demo', commit_issue: int = 51) -> tuple[Path, Path, Path]:
	# 2026-11-24
	# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
	# https://github.com/dmitry-ai/harness/issues/175
	t_bare, t_code = _get_empty_git_template()
	proj = base / 'proj'
	code = proj / 'code'
	bare = base / 'remote.git'
	(proj / '_/ꘖ/KB/Evidence/GitHub' / slug.replace('/', '__')).mkdir(parents=True, exist_ok=True)
	(proj / '_/ꙮ/≻').mkdir(parents=True, exist_ok=True)
	(proj / '_/ꙮ/≺').mkdir(parents=True, exist_ok=True)
	shutil.copytree(t_bare, bare)
	shutil.copytree(t_code, code)
	cfg = code / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + f'[remote "origin"]\n\turl = https://github.com/{slug}.git\n\tpushurl = {bare.as_posix()}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n', encoding='utf-8')
	(code / 'tests').mkdir(parents=True, exist_ok=True)
	(code / 'tests/test_existing.py').write_text(
		f'# https://github.com/{slug}/issues/{commit_issue}\nimport unittest\nclass E(unittest.TestCase):\n\tdef test_e(self):\n\t\tself.assertEqual(1, 1)\n',
		encoding='utf-8',
	)
	(code / 'tests/test_app.py').write_text(
		f'# https://github.com/{slug}/issues/{commit_issue}\nimport unittest\nclass A(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(2, 2)\n',
		encoding='utf-8',
	)
	(code / 'app.py').write_text(f'# https://github.com/{slug}/issues/{commit_issue}\nVAL = 2\n', encoding='utf-8')
	subprocess.run(['git', '-C', str(code), 'add', 'app.py', 'tests/test_existing.py', 'tests/test_app.py'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(code), 'commit', '-m', f'https://github.com/{slug}/issues/{commit_issue}'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(code), 'push', '-u', 'origin', 'main'], check=True, capture_output=True)
	# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
	ensure_commit_tag(code, push=True)
	return (proj, code, bare)


# @used-by :meth:`IssueFirstTurnCompletionAndGitTests.test_antigravity_issue_first_gate_blocks_retroactive_and_passes_parent_then_tdd()`
# @used-by :meth:`IssueFirstTurnCompletionAndGitTests.test_cli_issue_first_check_read_only_and_legacy_delivered_immutability()`
def _setup_antigravity_conv(base: Path, proj: Path, prompt_text: str) -> tuple[Path, Path, str, Path, list[dict]]:
	ag_home = base / 'ag_home'
	backend = ag_home / '.gemini/antigravity'
	(ag_home / '.gemini/config/projects').mkdir(parents=True, exist_ok=True)
	(backend / 'conversations').mkdir(parents=True, exist_ok=True)
	summaries_db = backend / 'conversation_summaries.db'
	cid = str(uuid.uuid4())
	t_log = backend / 'brain' / cid / '.system_generated/logs/transcript_full.jsonl'
	t_log.parent.mkdir(parents=True, exist_ok=True)
	rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': prompt_text}]
	t_log.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
	with closing(sqlite3.connect(summaries_db)) as c:
		c.execute('CREATE TABLE IF NOT EXISTS conversation_summaries(conversation_id TEXT, parent_conversation_id TEXT, workspace_uris TEXT, status TEXT, not_fully_idle INTEGER, killed INTEGER, last_user_input_step_index INTEGER, agent_name TEXT)')
		c.execute('INSERT INTO conversation_summaries VALUES(?,?,?,?,?,?,?,?)', (cid, '', json.dumps([proj.as_uri()]), 'CASCADE_RUN_STATUS_RUNNING', 1, 0, 0, 'primary'))
		c.commit()
	with closing(sqlite3.connect(backend / 'conversations' / f'{cid}.db')) as c:
		c.execute('CREATE TABLE steps(idx INTEGER, step_type INTEGER, status INTEGER, step_format INTEGER, step_payload BLOB)')
		c.execute('INSERT INTO steps VALUES(0, 14, 3, 0, ?)', (_wire(19, _wire(2, prompt_text.encode('utf-8'))),))
		c.commit()
	return (ag_home, backend, cid, t_log, rows)


# @used-by :meth:`IssueFirstTurnCompletionAndGitTests.test_codex_apply_patch_and_exec_command_issue_first_gate()`
def _setup_codex_conv(base: Path, proj: Path, prompt_text: str, extra_rows: list[dict]) -> tuple[Path, str, Path]:
	codex_home = base / 'codex_home'
	sess_dir = codex_home / 'sessions/2026/11/23'
	sess_dir.mkdir(parents=True, exist_ok=True)
	tid = str(uuid.uuid4())
	turn_id = 'turn-1'
	rollout = sess_dir / f'rollout-{tid}.jsonl'
	base_rows = [
		{'type': 'session_meta', 'payload': {'id': tid, 'cwd': str(proj), 'source': 'vscode'}},
		{'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': turn_id}},
		{'type': 'turn_context', 'payload': {'turn_id': turn_id, 'cwd': str(proj)}},
		{
			'type': 'response_item',
			'payload': {
				'type': 'message', 'role': 'user',
				'internal_chat_message_metadata_passthrough': {'content_item_kinds': ['user.text'], 'turn_id': turn_id},
				'content': [{'type': 'input_text', 'text': prompt_text}],
			},
		},
		*extra_rows,
	]
	rollout.write_text(''.join(json.dumps(r) + '\n' for r in base_rows), encoding='utf-8')
	with closing(sqlite3.connect(codex_home / 'state_1.sqlite')) as c:
		c.execute('CREATE TABLE threads(id TEXT PRIMARY KEY, rollout_path TEXT, agent_path TEXT)')
		c.execute('INSERT INTO threads VALUES(?,?,?)', (tid, str(rollout), ''))
		c.commit()
	return (codex_home, tid, rollout)


# 2026-11-23
# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
# https://github.com/dmitry-ai/harness/issues/146
class IssueFirstTurnCompletionAndGitTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_antigravity_issue_first_gate_blocks_retroactive_and_passes_parent_then_tdd(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, code, _ = _init_github_project(base, slug='acme/demo', commit_issue=51)
			_write_issue_ev(proj, 'acme/demo', 50, state='closed')
			_write_issue_ev(proj, 'acme/demo', 51, state='closed', parent_number=50)
			prod = code / 'app.py'
			test_f = code / 'tests/test_app.py'

			# Case 1: Retroactive issue creation AFTER writing test and prod -> BLOCKED everywhere, non-recoverable
			_, backend, cid_bad, t_bad, rows_bad = _setup_antigravity_conv(base, proj, 'Implement feature retroactively.')
			rows_bad.extend([
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(test_f)}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest "{test_f}"'}}]},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nAssertionError\nFAILED (failures=1)\n'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(prod)}}]},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'Created file.'},
				{'step_index': 7, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest discover -s "{code / "tests"}" -p "test_*.py"'}}]},
				{'step_index': 8, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\nRan 2 tests in 0.01s\nOK\n'},
				{'step_index': 9, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py create --repo acme/demo --title "Retroactive parent" --body-file p.md'}}]},
				{'step_index': 10, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'create', 'repo': 'acme/demo', 'number': 50, 'state': 'open', 'html_url': 'https://github.com/acme/demo/issues/50', 'verified': True}) + '\n'},
			])
			t_bad.write_text(''.join(json.dumps(r) + '\n' for r in rows_bad), encoding='utf-8')

			chk_bad = completion.check_answer(proj, 'Implemented feature.  \n', cid_bad, platform='antigravity', backend=backend)
			self.assertFalse(chk_bad['valid'])
			self.assertFalse(chk_bad['checks']['issue_first'])
			self.assertTrue(any('ISSUE-FIRST-GATE' in it['message'] for it in chk_bad['issues']), chk_bad['issues'])

			with self.assertRaisesRegex(ValueError, 'ISSUE-FIRST-GATE'):
				completion.prepare(proj, 'Implemented feature.  \n', cid_bad, platform='antigravity', backend=backend)

			stop_bad = check_stop_gate.evaluate_stop_payload(
				{'terminationReason': 'NO_TOOL_CALL', 'sessionId': cid_bad, 'cwd': str(proj), 'transcriptPath': str(t_bad)},
				backend_override=backend,
			)
			self.assertEqual(stop_bad['decision'], 'continue', stop_bad)
			self.assertIn('ISSUE-FIRST', stop_bad['reason'])

			# recover-turn-violation MUST NOT bypass Issue-First violations
			completion.recover_turn_violation(proj, cid_bad, reason='Attempting bypass', platform='antigravity', backend=backend)
			with self.assertRaisesRegex(ValueError, 'ISSUE-FIRST-GATE'):
				completion.prepare(proj, 'Implemented feature.  \n', cid_bad, platform='antigravity', backend=backend)

			# Case 2: Parent issue created FIRST -> test (Red) -> prod (Full Green) -> child #51 -> close child & parent -> PASS
			_, _, cid_ok, t_ok, rows_ok = _setup_antigravity_conv(base, proj, 'Implement feature properly with Issue-First and TDD.')
			rows_ok.extend([
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py create --repo acme/demo --title "Problem report" --body-file p.md'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'create', 'repo': 'acme/demo', 'number': 50, 'state': 'open', 'html_url': 'https://github.com/acme/demo/issues/50', 'verified': True}) + '\n'},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(test_f)}}]},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Created file.'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest "{test_f}"'}}]},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nAssertionError\nFAILED (failures=1)\n'},
				{'step_index': 7, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(prod)}}]},
				{'step_index': 8, 'type': 'GENERIC', 'content': 'Created file.'},
				{'step_index': 9, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest discover -s "{code / "tests"}" -p "test_*.py"'}}]},
				{'step_index': 10, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\nRan 2 tests in 0.02s\nOK\n'},
				{'step_index': 11, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py create --repo acme/demo --parent 50 --title "Subtask 1" --body-file c1.md'}}]},
				{'step_index': 12, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'create', 'repo': 'acme/demo', 'number': 51, 'state': 'open', 'parent_number': 50, 'html_url': 'https://github.com/acme/demo/issues/51', 'verified': True}) + '\n'},
				{'step_index': 13, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py close --repo acme/demo --issue 51'}}]},
				{'step_index': 14, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'close', 'repo': 'acme/demo', 'number': 51, 'state': 'closed', 'html_url': 'https://github.com/acme/demo/issues/51', 'verified': True}) + '\n'},
				{'step_index': 15, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py close --repo acme/demo --issue 50'}}]},
				{'step_index': 16, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'close', 'repo': 'acme/demo', 'number': 50, 'state': 'closed', 'html_url': 'https://github.com/acme/demo/issues/50', 'verified': True}) + '\n'},
			])
			t_ok.write_text(''.join(json.dumps(r) + '\n' for r in rows_ok), encoding='utf-8')

			chk_ok = completion.check_answer(proj, 'Implemented feature with Issue-First and TDD.  \n', cid_ok, platform='antigravity', backend=backend)
			self.assertTrue(chk_ok['valid'], chk_ok)
			self.assertTrue(chk_ok['checks']['issue_first'])
			self.assertTrue(chk_ok['checks']['tdd'])

			prep_ok = completion.prepare(proj, 'Implemented feature with Issue-First and TDD.  \n', cid_ok, platform='antigravity', backend=backend)
			self.assertTrue(prep_ok['ready'])
			self.assertTrue(prep_ok['issue_first_check']['verified'])

			rows_ok.append({'step_index': 17, 'type': 'PLANNER_RESPONSE', 'content': 'Implemented feature with Issue-First and TDD.  \n'})
			t_ok.write_text(''.join(json.dumps(r) + '\n' for r in rows_ok), encoding='utf-8')
			stop_ok = check_stop_gate.evaluate_stop_payload(
				{'terminationReason': 'NO_TOOL_CALL', 'sessionId': cid_ok, 'cwd': str(proj), 'transcriptPath': str(t_ok)},
				backend_override=backend,
			)
			self.assertEqual(stop_ok['decision'], 'allow', stop_ok)

	# @used-by :mod:`unittest`
	def test_codex_apply_patch_and_exec_command_issue_first_gate(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, code, _ = _init_github_project(base, slug='acme/demo', commit_issue=60)
			_write_issue_ev(proj, 'acme/demo', 60, state='closed')
			prod = code / 'app.py'
			test_f = code / 'tests/test_app.py'

			# Codex Turn 1: apply_patch edits test before any parent issue -> BLOCKED
			bad_rows = [
				{
					'type': 'response_item',
					'payload': {
						'type': 'custom_tool_call', 'name': 'apply_patch', 'call_id': 'p1',
						'input': f'*** Begin Patch\n*** Update File: {test_f.as_posix()}\n@@\n*** End Patch\n',
					},
				},
				{'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'p1', 'output': 'Success.'}},
			]
			codex_home, tid_bad, _ = _setup_codex_conv(base / 'c1', proj, 'Write test before issue in Codex.', bad_rows)
			chk_bad = completion.check_answer(proj, 'Updated tests.  \n', tid_bad, platform='codex', backend=codex_home)
			self.assertFalse(chk_bad['valid'])
			self.assertFalse(chk_bad['checks']['issue_first'])

			# Codex Turn 2: df_github_issue.py create -> apply_patch test -> Red -> apply_patch prod -> Full Green -> close -> PASS
			good_rows = [
				{
					'type': 'response_item',
					'payload': {
						'type': 'function_call', 'name': 'exec_command', 'call_id': 'g1',
						'arguments': json.dumps({'cmd': 'python scripts/df_github_issue.py create --repo acme/demo --title "Problem" --body-file p.md', 'workdir': str(proj)}),
					},
				},
				{
					'type': 'response_item',
					'payload': {'type': 'function_call_output', 'call_id': 'g1', 'output': json.dumps({'ok': True, 'action': 'create', 'repo': 'acme/demo', 'number': 60, 'state': 'open', 'html_url': 'https://github.com/acme/demo/issues/60', 'verified': True})},
				},
				{
					'type': 'response_item',
					'payload': {
						'type': 'custom_tool_call', 'name': 'apply_patch', 'call_id': 'p1',
						'input': f'*** Begin Patch\n*** Update File: {test_f.as_posix()}\n@@\n*** End Patch\n',
					},
				},
				{'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'p1', 'output': 'Success.'}},
				{
					'type': 'response_item',
					'payload': {
						'type': 'function_call', 'name': 'exec_command', 'call_id': 'c1',
						'arguments': json.dumps({'cmd': f'python -m unittest "{test_f}"', 'workdir': str(code)}),
					},
				},
				{
					'type': 'response_item',
					'payload': {'type': 'function_call_output', 'call_id': 'c1', 'output': 'Process exited with code 1\nOutput:\nAssertionError\nFAILED (failures=1)\n'},
				},
				{
					'type': 'response_item',
					'payload': {
						'type': 'custom_tool_call', 'name': 'apply_patch', 'call_id': 'p2',
						'input': f'*** Begin Patch\n*** Update File: {prod.as_posix()}\n@@\n*** End Patch\n',
					},
				},
				{'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'p2', 'output': 'Success.'}},
				{
					'type': 'response_item',
					'payload': {
						'type': 'function_call', 'name': 'exec_command', 'call_id': 'c2',
						'arguments': json.dumps({'cmd': f'python -m unittest discover -s "{code / "tests"}" -p "test_*.py"', 'workdir': str(code)}),
					},
				},
				{
					'type': 'response_item',
					'payload': {'type': 'function_call_output', 'call_id': 'c2', 'output': 'Process exited with code 0\nOutput:\nRan 2 tests in 0.02s\nOK\n'},
				},
				{
					'type': 'response_item',
					'payload': {
						'type': 'function_call', 'name': 'exec_command', 'call_id': 'g2',
						'arguments': json.dumps({'cmd': 'python scripts/df_github_issue.py close --repo acme/demo --issue 60', 'workdir': str(proj)}),
					},
				},
				{
					'type': 'response_item',
					'payload': {'type': 'function_call_output', 'call_id': 'g2', 'output': json.dumps({'ok': True, 'action': 'close', 'repo': 'acme/demo', 'number': 60, 'state': 'closed', 'html_url': 'https://github.com/acme/demo/issues/60', 'verified': True})},
				},
			]
			codex_home2, tid_ok, _ = _setup_codex_conv(base / 'c2', proj, 'Implement with Issue-First and TDD in Codex.', good_rows)
			chk_ok = completion.check_answer(proj, 'Implemented in Codex with Issue-First and TDD.  \n', tid_ok, platform='codex', backend=codex_home2)
			self.assertTrue(chk_ok['valid'], chk_ok)
			self.assertTrue(chk_ok['checks']['issue_first'])
			prep_ok = completion.prepare(proj, 'Implemented in Codex with Issue-First and TDD.  \n', tid_ok, platform='codex', backend=codex_home2)
			self.assertTrue(prep_ok['ready'])
			self.assertTrue(prep_ok['issue_first_check']['verified'])

	# @used-by :mod:`unittest`
	def test_cli_issue_first_check_read_only_and_legacy_delivered_immutability(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, code, _ = _init_github_project(base, slug='acme/demo', commit_issue=65)
			ag_home, backend, cid, t_log, rows = _setup_antigravity_conv(base, proj, 'Check CLI diagnostics.')
			sub_env = {**os.environ, 'USERPROFILE': str(ag_home), 'APPDATA': str(base / 'roaming')}

			rows.append({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(code / 'tests/test_app.py')}}]})
			t_log.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
			p_bad = subprocess.run(
				[sys.executable, str(SCRIPT_DIR / 'harness.py'), 'issue-first-check', str(proj), '--conversation', cid, '--platform', 'antigravity'],
				env=sub_env, capture_output=True, text=True, encoding='utf-8', check=False,
			)
			self.assertEqual(p_bad.returncode, 2, p_bad.stderr or p_bad.stdout)
			d_bad = json.loads(p_bad.stdout)
			self.assertFalse(d_bad['valid'])
			self.assertTrue(d_bad['read_only'])
			self.assertFalse((proj / '_/ꘖ/data/turns').exists())

			# Legacy delivered turn bytes without issue_first_check stay untouched on sync
			_, _, cid_leg, t_leg, rows_leg = _setup_antigravity_conv(base, proj, 'Legacy delivered turn.')
			reply = 'Delivered before issue_first_check existed.  \n'
			rows_leg.append({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': reply})
			t_leg.write_text(''.join(json.dumps(r) + '\n' for r in rows_leg), encoding='utf-8')
			with closing(sqlite3.connect(backend / 'conversations' / f'{cid_leg}.db')) as c:
				c.execute('INSERT INTO steps VALUES(1, 15, 3, 0, ?)', (b'',))
				c.commit()
			with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as c:
				c.execute("UPDATE conversation_summaries SET status='CASCADE_RUN_STATUS_IDLE', not_fully_idle=0 WHERE conversation_id=?", (cid_leg,))
				c.commit()
			sync1 = completion.sync(proj, cid_leg, platform='antigravity', backend=backend)
			self.assertTrue(sync1['valid'], sync1)
			t_key = sync1['turns'][0]['turn_key']
			state_file = proj / '_/ꘖ/data/turns' / f'{t_key}.json'
			state_obj = json.loads(state_file.read_text(encoding='utf-8'))
			state_obj.pop('issue_first_check', None)
			legacy_bytes = completion._json(state_obj)
			state_file.write_bytes(legacy_bytes)
			sync2 = completion.sync(proj, cid_leg, platform='antigravity', backend=backend)
			self.assertTrue(sync2['valid'], sync2)
			self.assertEqual(state_file.read_bytes(), legacy_bytes)

	# @used-by :mod:`unittest`
	def test_git_gate_verify_issue_workflow_enforces_slug_and_saved_evidence_in_github_code_repo(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, code, _ = _init_github_project(base, slug='acme/demo', commit_issue=1)
			test_f = code / 'tests/test_new.py'
			prod_f = code / 'new_mod.py'

			# 1. Wrong repository slug -> REJECTED
			wrong_url = 'https://github.com/other/repo/issues/70'
			test_f.write_text(f'# {wrong_url}\nimport unittest\nclass T(unittest.TestCase):\n\tdef test_x(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
			prod_f.write_text(f'# {wrong_url}\nX = 1\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(code), 'add', 'new_mod.py', 'tests/test_new.py'], check=True, capture_output=True)
			with self.assertRaisesRegex(ValueError, 'ISSUE-FIRST-GATE|does not match repository'):
				git_gate.check_commit(code, ['new_mod.py', 'tests/test_new.py'])
			with self.assertRaisesRegex(ValueError, 'ISSUE-FIRST-GATE|does not match repository'):
				git_gate.verify_issue_workflow(code, ['new_mod.py', 'tests/test_new.py'], message=wrong_url)

			# 2. Correct repo slug but NO saved issue-71.json Evidence -> REJECTED
			child_url = 'https://github.com/acme/demo/issues/71'
			test_f.write_text(f'# {child_url}\nimport unittest\nclass T(unittest.TestCase):\n\tdef test_x(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
			prod_f.write_text(f'# {child_url}\nX = 1\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(code), 'add', 'new_mod.py', 'tests/test_new.py'], check=True, capture_output=True)
			with self.assertRaisesRegex(ValueError, 'ISSUE-FIRST-GATE'):
				git_gate.verify_issue_workflow(code, ['new_mod.py', 'tests/test_new.py'], message=child_url)
			self.assertEqual(git_gate.run_git_hook('pre-commit', cwd=code, agent_context=True), 2)

			# 3. Child issue-71.json exists WITHOUT parent issue-70.json -> REJECTED
			_write_issue_ev(proj, 'acme/demo', 71, state='open', parent_number=70)
			with self.assertRaisesRegex(ValueError, 'ISSUE-FIRST-GATE'):
				git_gate.verify_issue_workflow(code, ['new_mod.py', 'tests/test_new.py'], message=child_url)

			# 4. Parent issue-70.json ALSO exists -> ALLOWED and commits cleanly
			_write_issue_ev(proj, 'acme/demo', 70, state='open')
			self.assertEqual(git_gate.run_git_hook('pre-commit', cwd=code, agent_context=True), 0)
			committed = git_gate.commit(code, ['new_mod.py', 'tests/test_new.py'], child_url, execute=True)
			self.assertEqual(committed, ['new_mod.py', 'tests/test_new.py'])


if '__main__' == __name__:
	unittest.main()
