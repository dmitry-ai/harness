# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/175
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce live PreToolUse Issue-First gate before TDD in check_rules_and_server_gate.py":
# https://github.com/dmitry-ai/harness/issues/145
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
HOOK_SCRIPT = SCRIPT_DIR / 'check_rules_and_server_gate.py'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))

import check_rules_and_server_gate as gate


def _run_hook(payload: dict) -> dict:
	buf = io.StringIO()
	with patch.object(sys, 'stdin', io.StringIO(json.dumps(payload, ensure_ascii=False))), redirect_stdout(buf):
		gate.main()
	return json.loads(buf.getvalue())


def _init_github_project(base: Path, slug: str = 'acme/demo') -> tuple[Path, Path]:
	proj = base / 'proj'
	(proj / '_/ꘖ/data/scratch').mkdir(parents=True, exist_ok=True)
	(proj / '_/ꘖ/KB/Evidence/GitHub' / slug.replace('/', '__')).mkdir(parents=True, exist_ok=True)
	code = proj / 'code'
	code.mkdir(parents=True, exist_ok=True)
	subprocess.run(['git', 'init', '-b', 'main', str(code)], check=True, capture_output=True)
	cfg = code / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + f'[user]\n\temail = test@example.com\n\tname = Test User\n[remote "origin"]\n\turl = https://github.com/{slug}.git\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n', encoding='utf-8')
	return (proj, code)


def _write_tx(path: Path, rows: list[dict]) -> Path:
	path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
	return path


class IssueFirstPreToolUseGateTests(unittest.TestCase):
	def test_blocks_tests_production_docs_and_shell_writes_before_parent_issue(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, code = _init_github_project(base)
			tx = _write_tx(base / 'transcript.jsonl', [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Add calculator feature.'},
			])

			# 1. Test file blocked BEFORE TDD can even start (§2)
			d_test = _run_hook({
				'cwd': str(proj),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'write_file',
					'args': {
						'Path': str(code / 'tests/test_calc.py'),
						'Content': 'import unittest\nclass T(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(1, 1)\n',
					},
				},
			})
			self.assertEqual(d_test['decision'], 'deny', d_test)
			self.assertIn('EXEC-5-ISSUE-FIRST-GATE', d_test.get('reason', ''))

			# 2. Production code hits EXEC-5-ISSUE-FIRST-GATE strictly BEFORE EXEC-2-TDD-GATE
			d_prod = _run_hook({
				'cwd': str(proj),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'write_file',
					'args': {'Path': str(code / 'src/calc.py'), 'Content': 'def add(a, b): return a + b\n'},
				},
			})
			self.assertEqual(d_prod['decision'], 'deny', d_prod)
			self.assertIn('EXEC-5-ISSUE-FIRST-GATE', d_prod.get('reason', ''))

			# 3. Versioned rule/doc file in issue-tracked code repo blocked before parent issue
			d_doc = _run_hook({
				'cwd': str(proj),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'write_file',
					'args': {'Path': str(code / 'rules/08-execution-and-tools.md'), 'Content': '# Rules\nLine one.  \n'},
				},
			})
			self.assertEqual(d_doc['decision'], 'deny', d_doc)
			self.assertIn('EXEC-5-ISSUE-FIRST-GATE', d_doc.get('reason', ''))

			# 4. Shell write bypass to test file blocked before parent issue
			d_sh = _run_hook({
				'cwd': str(proj),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'run_command',
					'args': {'CommandLine': f'Set-Content -Path "{code / "tests/test_calc.py"}" -Value "assert True"'},
				},
			})
			self.assertEqual(d_sh['decision'], 'deny', d_sh)
			self.assertIn('EXEC-5-ISSUE-FIRST-GATE', d_sh.get('reason', ''))

			# 5. Scratch issue body file inside _/ꘖ/data/scratch/ MUST remain allowed
			d_scratch = _run_hook({
				'cwd': str(proj),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'write_file',
					'args': {'Path': str(proj / '_/ꘖ/data/scratch/issue-body.md'), 'Content': '## Problem\nDetails.  \n'},
				},
			})
			self.assertEqual(d_scratch['decision'], 'allow', d_scratch)

			# 6. Direct check_issue_first_gate symbol exposed on hook module
			self.assertIsNotNone(
				gate.check_issue_first_gate(
					'write_file',
					{'Path': str(code / 'tests/test_calc.py'), 'Content': 'assert True\n'},
					{'cwd': str(proj), 'transcriptPath': str(tx)},
				)
			)

	def test_full_issue_first_then_tdd_red_green_child_and_parent_close_reset_in_live_hook(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, code = _init_github_project(base)
			test_f = code / 'tests/test_calc.py'
			test_f2 = code / 'tests/test_calc2.py'
			prod_f = code / 'src/calc.py'
			tx = base / 'transcript.jsonl'
			test_body = 'import unittest\nclass T(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(1, 2)\n'

			# Step 1: Parent issue #100 created -> test file ALLOWED, production code DENIED by TDD-RED-GATE
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Build calc'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py create --repo acme/demo --title "Calc problem" --body-file b.md'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'create', 'repo': 'acme/demo', 'number': 100, 'state': 'open', 'html_url': 'https://github.com/acme/demo/issues/100', 'verified': True}) + '\n'},
			]
			_write_tx(tx, rows)

			d_test_ok = _run_hook({
				'cwd': str(proj),
				'transcriptPath': str(tx),
				'toolCall': {'name': 'write_file', 'args': {'Path': str(test_f), 'Content': test_body}},
			})
			self.assertEqual(d_test_ok['decision'], 'allow', d_test_ok)

			d_prod_red = _run_hook({
				'cwd': str(proj),
				'transcriptPath': str(tx),
				'toolCall': {'name': 'write_file', 'args': {'Path': str(prod_f), 'Content': 'def add(a, b): return a + b\n'}},
			})
			self.assertEqual(d_prod_red['decision'], 'deny', d_prod_red)
			self.assertIn('EXEC-2-TDD-GATE', d_prod_red.get('reason', ''))

			# Step 2: Test written and observed RED -> production code ALLOWED
			rows.extend([
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(test_f)}}]},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Created file.'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest "{test_f}"'}}]},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nAssertionError: 1 != 2\nFAILED (failures=1)\n'},
			])
			_write_tx(tx, rows)
			d_prod_ok = _run_hook({
				'cwd': str(proj),
				'transcriptPath': str(tx),
				'toolCall': {'name': 'write_file', 'args': {'Path': str(prod_f), 'Content': 'def add(a, b): return a + b\n'}},
			})
			self.assertEqual(d_prod_ok['decision'], 'allow', d_prod_ok)

			# Step 3: Child issue #101 created and closed while parent #100 stays OPEN -> next subtask test ALLOWED
			rows.extend([
				{'step_index': 7, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py create --repo acme/demo --parent 100 --title "Child 1" --body-file c1.md'}}]},
				{'step_index': 8, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'create', 'repo': 'acme/demo', 'number': 101, 'state': 'open', 'parent_number': 100, 'html_url': 'https://github.com/acme/demo/issues/101', 'verified': True}) + '\n'},
				{'step_index': 9, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py close --repo acme/demo --issue 101'}}]},
				{'step_index': 10, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'close', 'repo': 'acme/demo', 'number': 101, 'state': 'closed', 'html_url': 'https://github.com/acme/demo/issues/101', 'verified': True}) + '\n'},
			])
			_write_tx(tx, rows)
			d_next_subtask = _run_hook({
				'cwd': str(proj),
				'transcriptPath': str(tx),
				'toolCall': {'name': 'write_file', 'args': {'Path': str(test_f2), 'Content': test_body}},
			})
			self.assertEqual(d_next_subtask['decision'], 'allow', d_next_subtask)

			# Step 4: Parent #100 closed -> subsequent test write DENIED until a new parent issue is opened or fetched
			rows.extend([
				{'step_index': 11, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py close --repo acme/demo --issue 100'}}]},
				{'step_index': 12, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'close', 'repo': 'acme/demo', 'number': 100, 'state': 'closed', 'html_url': 'https://github.com/acme/demo/issues/100', 'verified': True}) + '\n'},
			])
			_write_tx(tx, rows)
			d_after_close = _run_hook({
				'cwd': str(proj),
				'transcriptPath': str(tx),
				'toolCall': {'name': 'write_file', 'args': {'Path': str(code / 'tests/test_reg.py'), 'Content': test_body}},
			})
			self.assertEqual(d_after_close['decision'], 'deny', d_after_close)
			self.assertIn('EXEC-5-ISSUE-FIRST-GATE', d_after_close.get('reason', ''))

			# Step 5: Fetching existing open parent #105 unlocks again
			rows.extend([
				{'step_index': 13, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python scripts/df_github_issue.py fetch --repo acme/demo --issue 105'}}]},
				{'step_index': 14, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n' + json.dumps({'ok': True, 'action': 'fetch', 'repo': 'acme/demo', 'number': 105, 'state': 'open', 'html_url': 'https://github.com/acme/demo/issues/105', 'verified': True}) + '\n'},
			])
			_write_tx(tx, rows)
			d_after_fetch = _run_hook({
				'cwd': str(proj),
				'transcriptPath': str(tx),
				'toolCall': {'name': 'write_file', 'args': {'Path': str(code / 'tests/test_reg.py'), 'Content': test_body}},
			})
			self.assertEqual(d_after_fetch['decision'], 'allow', d_after_fetch)

	def test_cli_subprocess_smoke(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, code = _init_github_project(base)
			tx = _write_tx(base / 'transcript.jsonl', [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Smoke'}])
			payload = {'cwd': str(proj), 'transcriptPath': str(tx), 'toolCall': {'name': 'write_file', 'args': {'Path': str(code / 'tests/test_x.py'), 'Content': 'assert True\n'}}}
			proc = subprocess.run([sys.executable, str(HOOK_SCRIPT)], input=json.dumps(payload, ensure_ascii=False).encode('utf-8'), capture_output=True, check=True)
			decision = json.loads(proc.stdout.decode('utf-8'))
			self.assertEqual(decision['decision'], 'deny', decision)
			self.assertIn('EXEC-5-ISSUE-FIRST-GATE', decision.get('reason', ''))


if '__main__' == __name__:
	unittest.main()
