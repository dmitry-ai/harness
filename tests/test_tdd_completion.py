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

# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
from agent_tools import completion, repo_tags, tdd_gate
import check_pre_invocation
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


# 2026-11-24
# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/175
_TEMPLATE_CACHE: dict[int, tuple[tempfile.TemporaryDirectory, Path, Path]] = {}


# @used-by :func:`_init_project_with_git_code()`
def _build_template_project(issue_num: int) -> tuple[Path, Path]:
	if issue_num not in _TEMPLATE_CACHE:
		td = tempfile.TemporaryDirectory()
		root = Path(td.name).resolve()
		proj = root / 'proj'
		code = proj / 'code'
		bare = root / 'remote.git'
		(proj / '_/ꘖ/KB/Evidence/GitHub/test-org__demo').mkdir(parents=True, exist_ok=True)
		(proj / '_/ꙮ/≻').mkdir(parents=True, exist_ok=True)
		(proj / '_/ꙮ/≺').mkdir(parents=True, exist_ok=True)
		code.mkdir(parents=True, exist_ok=True)
		subprocess.run(['git', 'init', '--bare', '-b', 'main', str(bare)], check=True, capture_output=True)
		subprocess.run(['git', 'init', '-b', 'main', str(code)], check=True, capture_output=True)
		cfg = code / '.git/config'
		cfg.write_text(cfg.read_text(encoding='utf-8') + f'[user]\n\temail = test@example.com\n\tname = Test User\n[remote "origin"]\n\turl = {bare.as_posix()}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n', encoding='utf-8')
		(code / 'tests').mkdir(parents=True, exist_ok=True)
		(code / 'tests/test_existing.py').write_text(
			f'# https://github.com/test-org/demo/issues/{issue_num}\nimport unittest\nclass E(unittest.TestCase):\n\tdef test_e(self):\n\t\tself.assertEqual(1, 1)\n',
			encoding='utf-8',
		)
		(code / 'tests/test_app.py').write_text(
			f'# https://github.com/test-org/demo/issues/{issue_num}\nimport unittest\nclass A(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(2, 2)\n',
			encoding='utf-8',
		)
		(code / 'app.py').write_text(f'# https://github.com/test-org/demo/issues/{issue_num}\nVAL = 2\n', encoding='utf-8')
		subprocess.run(['git', '-C', str(code), 'add', 'app.py', 'tests/test_existing.py', 'tests/test_app.py'], check=True, capture_output=True)
		subprocess.run(['git', '-C', str(code), 'commit', '-m', f'https://github.com/test-org/demo/issues/{issue_num}'], check=True, capture_output=True)
		# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
		subprocess.run(['git', '-C', str(code), 'push', '-u', 'origin', 'main'], check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
		repo_tags.ensure_commit_tag(code, push=True)
		ev = proj / f'_/ꘖ/KB/Evidence/GitHub/test-org__demo/issue-{issue_num}.json'
		ev.write_text(
			json.dumps({'url': f'https://github.com/test-org/demo/issues/{issue_num}', 'issue': {'number': issue_num, 'state': 'CLOSED'}}),
			encoding='utf-8',
		)
		_TEMPLATE_CACHE[issue_num] = (td, proj, bare)
	_, t_proj, t_bare = _TEMPLATE_CACHE[issue_num]
	return (t_proj, t_bare)


# 2026-11-24
# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/175
# @used-by :meth:`TddTurnCompletionAndCliTests.test_antigravity_tdd_gate_blocks_violations_and_passes_full_bg_green()`
# @used-by :meth:`TddTurnCompletionAndCliTests.test_cli_ratchet_ok_and_tdd_check_commands()`
# @used-by :meth:`TddTurnCompletionAndCliTests.test_codex_apply_patch_and_exec_command_tdd_gate()`
# @used-by :meth:`TddTurnCompletionAndCliTests.test_sync_preserves_legacy_delivered_turn_bytes_without_tdd_check()`
def _init_project_with_git_code(root: Path, *, issue_num: int = 42) -> tuple[Path, Path, Path]:
	t_proj, t_bare = _build_template_project(issue_num)
	proj = root / 'proj'
	bare = root / 'remote.git'
	shutil.copytree(t_proj, proj)
	shutil.copytree(t_bare, bare)
	code = proj / 'code'
	cfg = code / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8').replace(t_bare.as_posix(), bare.as_posix()), encoding='utf-8')
	return (proj, code, bare)


# @used-by :meth:`TddTurnCompletionAndCliTests.test_antigravity_tdd_gate_blocks_violations_and_passes_full_bg_green()`
# @used-by :meth:`TddTurnCompletionAndCliTests.test_cli_ratchet_ok_and_tdd_check_commands()`
# @used-by :meth:`TddTurnCompletionAndCliTests.test_sync_preserves_legacy_delivered_turn_bytes_without_tdd_check()`
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


# @used-by :meth:`TddTurnCompletionAndCliTests.test_codex_apply_patch_and_exec_command_tdd_gate()`
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
# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
# https://github.com/dmitry-ai/harness/issues/138
class TddTurnCompletionAndCliTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_antigravity_tdd_gate_blocks_violations_and_passes_full_bg_green(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, code, _ = _init_project_with_git_code(base)
			ag_home, backend, cid, t_log, rows = _setup_antigravity_conv(base, proj, 'Implement new calculation in code/app.py.')
			prod = code / 'app.py'
			test_f = code / 'tests/test_app.py'

			# Case 1: Production edit with NO prior failing test -> check_answer, prepare, Stop gate all BLOCK
			rows.append({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(prod)}}]})
			rows.append({'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'})
			t_log.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')

			chk_bad = completion.check_answer(proj, 'Updated calculation.  \n', cid, platform='antigravity', backend=backend)
			self.assertFalse(chk_bad['valid'])
			self.assertFalse(chk_bad['checks']['tdd'])
			self.assertTrue(any('TDD-RED-GATE' in it['message'] for it in chk_bad['issues']), chk_bad['issues'])

			with self.assertRaisesRegex(ValueError, 'TDD-RED-GATE'):
				completion.prepare(proj, 'Updated calculation.  \n', cid, platform='antigravity', backend=backend)

			stop_bad = check_stop_gate.evaluate_stop_payload(
				{'terminationReason': 'NO_TOOL_CALL', 'sessionId': cid, 'cwd': str(proj), 'transcriptPath': str(t_log)},
				backend_override=backend,
			)
			self.assertEqual(stop_bad['decision'], 'continue', stop_bad)
			self.assertIn('TDD', stop_bad['reason'])

			# recover_turn_violation must NOT bypass TDD violations
			completion.recover_turn_violation(proj, cid, reason='Attempting bypass', platform='antigravity', backend=backend)
			with self.assertRaisesRegex(ValueError, 'TDD-RED-GATE'):
				completion.prepare(proj, 'Updated calculation.  \n', cid, platform='antigravity', backend=backend)

			# Case 2: Fresh turn with Red -> prod -> ONLY single-file Green -> fails TDD-FULL-GATE
			_, _, cid2, t_log2, rows2 = _setup_antigravity_conv(base, proj, 'Add feature with TDD.')
			rows2.extend([
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(test_f)}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest "{test_f}"'}}]},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nAssertionError\nFAILED (failures=1)\n'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(prod)}}]},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'Created file.'},
				{'step_index': 7, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest "{test_f}"'}}]},
				{'step_index': 8, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\nRan 1 test in 0.01s\nOK\n'},
			])
			t_log2.write_text(''.join(json.dumps(r) + '\n' for r in rows2), encoding='utf-8')
			chk_single = completion.check_answer(proj, 'Implemented feature with tests.  \n', cid2, platform='antigravity', backend=backend)
			self.assertFalse(chk_single['valid'])
			self.assertFalse(chk_single['checks']['tdd'])
			self.assertTrue(any('TDD-FULL-GATE' in it['message'] for it in chk_single['issues']), chk_single['issues'])

			# Case 3: Full test suite runs via background task and completes GREEN -> PASSES check_answer, prepare, Stop gate!
			rows2.extend([
				{'step_index': 9, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest discover -s "{code / "tests"}" -p "test_*.py"'}}]},
				{'step_index': 10, 'type': 'GENERIC', 'content': f'Tool is running as a background task with task id: {cid2}/task-10'},
				{'step_index': 11, 'type': 'SYSTEM_MESSAGE', 'content': f'Task id "{cid2}/task-10" finished with result:\nCommand exited with code 0.\n\nCommand output:\nRan 2 tests in 0.05s\n\nOK\n'},
			])
			t_log2.write_text(''.join(json.dumps(r) + '\n' for r in rows2), encoding='utf-8')
			chk_ok = completion.check_answer(proj, 'Implemented feature with full suite passing.  \n', cid2, platform='antigravity', backend=backend)
			self.assertTrue(chk_ok['valid'], chk_ok)
			self.assertTrue(chk_ok['checks']['tdd'])

			prep_ok = completion.prepare(proj, 'Implemented feature with full suite passing.  \n', cid2, platform='antigravity', backend=backend)
			self.assertTrue(prep_ok['ready'])
			self.assertTrue(prep_ok['tdd_check']['verified'])

			rows2.append({'step_index': 12, 'type': 'PLANNER_RESPONSE', 'content': 'Implemented feature with full suite passing.  \n'})
			t_log2.write_text(''.join(json.dumps(r) + '\n' for r in rows2), encoding='utf-8')
			stop_ok = check_stop_gate.evaluate_stop_payload(
				{'terminationReason': 'NO_TOOL_CALL', 'sessionId': cid2, 'cwd': str(proj), 'transcriptPath': str(t_log2)},
				backend_override=backend,
			)
			self.assertEqual(stop_ok['decision'], 'allow', stop_ok)

	# @used-by :mod:`unittest`
	def test_codex_apply_patch_and_exec_command_tdd_gate(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, code, _ = _init_project_with_git_code(base)
			prod = code / 'app.py'
			test_f = code / 'tests/test_app.py'

			# Codex Turn 1: apply_patch edits production code without prior failing test -> BLOCKED
			bad_rows = [
				{
					'type': 'response_item',
					'payload': {
						'type': 'custom_tool_call', 'name': 'apply_patch', 'call_id': 'p1',
						'input': f'*** Begin Patch\n*** Update File: {prod.as_posix()}\n@@\n-VAL = 2\n+VAL = 3\n*** End Patch\n',
					},
				},
				{'type': 'response_item', 'payload': {'type': 'custom_tool_call_output', 'call_id': 'p1', 'output': 'Success.'}},
			]
			codex_home, tid_bad, _ = _setup_codex_conv(base, proj, 'Change VAL in Codex.', bad_rows)
			chk_bad = completion.check_answer(proj, 'Changed VAL.  \n', tid_bad, platform='codex', backend=codex_home)
			self.assertFalse(chk_bad['valid'])
			self.assertFalse(chk_bad['checks']['tdd'])

			# Codex Turn 2: full Red -> Green -> Full-suite Green -> ALLOWED
			good_rows = [
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
					'payload': {'type': 'function_call_output', 'call_id': 'c1', 'output': 'Process exited with code 1\nOutput:\nAssertionError: 2 != 3\nFAILED (failures=1)\n'},
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
			]
			codex_home2, tid_ok, _ = _setup_codex_conv(base / 'c2', proj, 'Change VAL with TDD in Codex.', good_rows)
			chk_ok = completion.check_answer(proj, 'Changed VAL with TDD.  \n', tid_ok, platform='codex', backend=codex_home2)
			self.assertTrue(chk_ok['valid'], chk_ok)
			self.assertTrue(chk_ok['checks']['tdd'])
			prep_ok = completion.prepare(proj, 'Changed VAL with TDD.  \n', tid_ok, platform='codex', backend=codex_home2)
			self.assertTrue(prep_ok['ready'])
			self.assertTrue(prep_ok['tdd_check']['verified'])

	# @used-by :mod:`unittest`
	def test_cli_ratchet_ok_and_tdd_check_commands(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, code, _ = _init_project_with_git_code(base)
			ag_home, backend, cid, t_log, rows = _setup_antigravity_conv(base, proj, 'CLI TDD check and ratchet-ok test.')
			sub_env = {**os.environ, 'USERPROFILE': str(ag_home), 'APPDATA': str(base / 'roaming')}

			# Production edit without test -> harness.py tdd-check exits 2 and is read-only
			rows.append({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(code / 'app.py')}}]})
			t_log.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
			p_bad = subprocess.run(
				[sys.executable, str(SCRIPT_DIR / 'harness.py'), 'tdd-check', str(proj), '--conversation', cid, '--platform', 'antigravity'],
				env=sub_env, capture_output=True, text=True, encoding='utf-8', check=False,
			)
			self.assertEqual(p_bad.returncode, 2, p_bad.stderr or p_bad.stdout)
			d_bad = json.loads(p_bad.stdout)
			self.assertFalse(d_bad['valid'])
			self.assertTrue(d_bad['read_only'])
			self.assertFalse((proj / '_/ꘖ/data/turns').exists())

			# harness.py ratchet-ok rejects short and test-fitting excuses
			p_short = subprocess.run(
				[sys.executable, str(SCRIPT_DIR / 'harness.py'), 'ratchet-ok', str(proj), '--file', 'tests/test_app.py', '--reason', 'short', '--conversation', cid, '--platform', 'antigravity'],
				env=sub_env, capture_output=True, text=True, encoding='utf-8', check=False,
			)
			self.assertNotEqual(p_short.returncode, 0)
			p_slop = subprocess.run(
				[sys.executable, str(SCRIPT_DIR / 'harness.py'), 'ratchet-ok', str(proj), '--file', 'tests/test_app.py', '--reason', 'Updating test expectations to match new implementation.', '--conversation', cid, '--platform', 'antigravity'],
				env=sub_env, capture_output=True, text=True, encoding='utf-8', check=False,
			)
			self.assertNotEqual(p_slop.returncode, 0)

			# harness.py ratchet-ok with valid audited reason writes receipt and unlocks find_ratchet_approval
			valid_reason = 'User explicitly revised tax specification in Issue #138 requiring updated expected total.'
			p_ok = subprocess.run(
				[sys.executable, str(SCRIPT_DIR / 'harness.py'), 'ratchet-ok', str(proj), '--file', 'tests/test_app.py', '--reason', valid_reason, '--conversation', cid, '--platform', 'antigravity'],
				env=sub_env, capture_output=True, text=True, encoding='utf-8', check=False,
			)
			self.assertEqual(p_ok.returncode, 0, p_ok.stderr or p_ok.stdout)
			d_ok = json.loads(p_ok.stdout)
			self.assertEqual(d_ok['file'], 'tests/test_app.py')
			found = tdd_gate.find_ratchet_approval('tests/test_app.py', repo_root=code, project_root=proj)
			self.assertIsNotNone(found)
			self.assertEqual(found['reason'], valid_reason)
			# Ensure *-ratchet-ok.json sidecar does not confuse PreInvocation hook
			pre_out = check_pre_invocation.evaluate_pre_invocation_payload(
				{'conversationId': cid, 'cwd': str(proj), 'transcriptPath': str(t_log), 'invocationNum': 1},
				backend_override=backend,
			)
			self.assertIsInstance(pre_out, dict)

	# 2026-11-23
	# "Preserve historical delivered turn bytes when tdd_check is absent":
	# https://github.com/dmitry-ai/harness/issues/140
	# @used-by :mod:`unittest`
	def test_sync_preserves_legacy_delivered_turn_bytes_without_tdd_check(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, _, _ = _init_project_with_git_code(base)
			_, backend, cid, t_log, rows = _setup_antigravity_conv(base, proj, 'Legacy delivered turn.')
			reply = 'Delivered before tdd_check existed.  \n'
			rows.append({'step_index': 1, 'type': 'PLANNER_RESPONSE', 'content': reply})
			t_log.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
			with closing(sqlite3.connect(backend / 'conversations' / f'{cid}.db')) as c:
				c.execute('INSERT INTO steps VALUES(1, 15, 3, 0, ?)', (b'',))
				c.commit()
			with closing(sqlite3.connect(backend / 'conversation_summaries.db')) as c:
				c.execute("UPDATE conversation_summaries SET status='CASCADE_RUN_STATUS_IDLE', not_fully_idle=0 WHERE conversation_id=?", (cid,))
				c.commit()
			sync1 = completion.sync(proj, cid, platform='antigravity', backend=backend)
			self.assertTrue(sync1['valid'], sync1)
			t_key = sync1['turns'][0]['turn_key']
			state_file = proj / '_/ꘖ/data/turns' / f'{t_key}.json'
			state_obj = json.loads(state_file.read_text(encoding='utf-8'))
			state_obj.pop('tdd_check', None)
			legacy_bytes = completion._json(state_obj)
			state_file.write_bytes(legacy_bytes)
			sync2 = completion.sync(proj, cid, platform='antigravity', backend=backend)
			self.assertTrue(sync2['valid'], sync2)
			self.assertEqual(state_file.read_bytes(), legacy_bytes)


if '__main__' == __name__:
	unittest.main()
