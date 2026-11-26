# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
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


# 2026-11-24
# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/175
# @used-by :meth:`TddPreToolUseGateTests.test_blocks_production_code_across_languages_before_red_test()`
# @used-by :meth:`TddPreToolUseGateTests.test_ratchet_anti_fitting_substantive_and_behavioral_test_guards()`
# @used-by :meth:`TddPreToolUseGateTests.test_red_green_commit_reset_cycle_in_live_hook()`
# @used-by :meth:`TddPreToolUseGateTests.test_shell_write_bypass_and_test_deletion_blocked()`
def _run_hook(payload: dict) -> dict:
	buf = io.StringIO()
	with patch.object(sys, 'stdin', io.StringIO(json.dumps(payload, ensure_ascii=False))), redirect_stdout(buf):
		gate.main()
	return json.loads(buf.getvalue())


# @used-by :meth:`TddPreToolUseGateTests.test_blocks_production_code_across_languages_before_red_test()`
# @used-by :meth:`TddPreToolUseGateTests.test_cli_subprocess_smoke()`
# @used-by :meth:`TddPreToolUseGateTests.test_ratchet_anti_fitting_substantive_and_behavioral_test_guards()`
# @used-by :meth:`TddPreToolUseGateTests.test_red_green_commit_reset_cycle_in_live_hook()`
# @used-by :meth:`TddPreToolUseGateTests.test_shell_write_bypass_and_test_deletion_blocked()`
def _init_git_repo(repo: Path) -> None:
	repo.mkdir(parents=True, exist_ok=True)
	# 2026-11-24
	# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
	# https://github.com/dmitry-ai/harness/issues/175
	subprocess.run(['git', 'init', '-b', 'main', str(repo)], check=True, capture_output=True)
	cfg = repo / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + '[user]\n\temail = test@example.com\n\tname = Test User\n', encoding='utf-8')


# @used-by :meth:`TddPreToolUseGateTests.test_blocks_production_code_across_languages_before_red_test()`
# @used-by :meth:`TddPreToolUseGateTests.test_cli_subprocess_smoke()`
# @used-by :meth:`TddPreToolUseGateTests.test_ratchet_anti_fitting_substantive_and_behavioral_test_guards()`
# @used-by :meth:`TddPreToolUseGateTests.test_red_green_commit_reset_cycle_in_live_hook()`
# @used-by :meth:`TddPreToolUseGateTests.test_shell_write_bypass_and_test_deletion_blocked()`
def _write_transcript(path: Path, rows: list[dict]) -> Path:
	path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
	return path


# 2026-11-23
# "Enforce live TDD PreToolUse gate in check_rules_and_server_gate.py":
# https://github.com/dmitry-ai/harness/issues/136
class TddPreToolUseGateTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_blocks_production_code_across_languages_before_red_test(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			repo = base / 'app_repo'
			_init_git_repo(repo)
			tx = _write_transcript(base / 'transcript.jsonl', [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Implement feature'},
			])
			for rel in ('src/app.py', 'src/index.js', 'scripts/deploy.ps1', 'UI/View.cs', 'Model/Order.php', 'bin/run.sh', 'styles/main.css'):
				decision = _run_hook({
					'cwd': str(repo),
					'transcriptPath': str(tx),
					'toolCall': {
						'name': 'write_file',
						'args': {'Path': str(repo / rel), 'Content': '// code\n'},
					},
				})
				self.assertEqual(decision['decision'], 'deny', f'Expected deny for {rel}: {decision}')
				self.assertIn('TDD-RED-GATE', decision.get('reason', ''))

			# Even without transcriptPath, production code write must fail-closed (deny)
			no_tx = _run_hook({
				'cwd': str(repo),
				'toolCall': {
					'name': 'write_file',
					'args': {'Path': str(repo / 'src/app.py'), 'Content': 'x = 1\n'},
				},
			})
			self.assertEqual(no_tx['decision'], 'deny', no_tx)

			# Non-code docs/configs must remain allowed without any prior tests
			for rel in ('README.md', 'config/settings.json', 'pyproject.toml'):
				allow_doc = _run_hook({
					'cwd': str(repo),
					'transcriptPath': str(tx),
					'toolCall': {
						'name': 'write_file',
						'args': {'Path': str(repo / rel), 'Content': 'content\n'},
					},
				})
				self.assertEqual(allow_doc['decision'], 'allow', f'Non-code {rel} should be allowed: {allow_doc}')

	# @used-by :mod:`unittest`
	def test_red_green_commit_reset_cycle_in_live_hook(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			repo = base / 'svc'
			_init_git_repo(repo)
			test_f = repo / 'tests/test_calc.py'
			prod_f = repo / 'src/calc.py'
			tx = base / 'transcript.jsonl'

			# Step A: test written, NOT yet run -> production code still DENIED
			_write_transcript(tx, [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Build calc'},
				{
					'step_index': 1, 'type': 'PLANNER_RESPONSE',
					'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(test_f))}}],
				},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
			])
			d_unrun = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx),
				'toolCall': {'name': 'write_file', 'args': {'Path': str(prod_f), 'Content': 'def add(a, b): return a + b\n'}},
			})
			self.assertEqual(d_unrun['decision'], 'deny', d_unrun)

			# Step B: test run PASSED (never Red!) -> production code still DENIED
			_write_transcript(tx, [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Build calc'},
				{
					'step_index': 1, 'type': 'PLANNER_RESPONSE',
					'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(test_f))}}],
				},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
				{
					'step_index': 3, 'type': 'PLANNER_RESPONSE',
					'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'python -m unittest "{test_f}"')}}],
				},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\nRan 1 test in 0.01s\nOK\n'},
			])
			d_green_only = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx),
				'toolCall': {'name': 'write_file', 'args': {'Path': str(prod_f), 'Content': 'def add(a, b): return a + b\n'}},
			})
			self.assertEqual(d_green_only['decision'], 'deny', d_green_only)

			# Step C: test run FAILED (observed RED!) -> production code ALLOWED
			rows_red = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Build calc'},
				{
					'step_index': 1, 'type': 'PLANNER_RESPONSE',
					'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(test_f))}}],
				},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
				{
					'step_index': 3, 'type': 'PLANNER_RESPONSE',
					'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'python -m unittest "{test_f}"')}}],
				},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nImportError: No module named calc\n'},
			]
			_write_transcript(tx, rows_red)
			d_red = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx),
				'toolCall': {'name': 'write_file', 'args': {'Path': str(prod_f), 'Content': 'def add(a, b): return a + b\n'}},
			})
			self.assertEqual(d_red['decision'], 'allow', d_red)

			# Step D: git commit resets cycle -> next production edit DENIED again
			rows_committed = [
				*rows_red,
				{
					'step_index': 5, 'type': 'PLANNER_RESPONSE',
					'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(prod_f))}}],
				},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'Created file.'},
				{
					'step_index': 7, 'type': 'PLANNER_RESPONSE',
					'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'git -C "{repo}" commit -m https://github.com/dmitry-ai/harness/issues/136')}}],
				},
				{'step_index': 8, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n[main 1111111] ok\n'},
			]
			_write_transcript(tx, rows_committed)
			d_post_commit = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx),
				'toolCall': {'name': 'write_file', 'args': {'Path': str(repo / 'src/other.py'), 'Content': 'y = 2\n'}},
			})
			self.assertEqual(d_post_commit['decision'], 'deny', d_post_commit)

	# @used-by :mod:`unittest`
	def test_shell_write_bypass_and_test_deletion_blocked(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			repo = base / 'sh_repo'
			_init_git_repo(repo)
			(repo / 'tests').mkdir()
			tracked_test = repo / 'tests/test_existing.py'
			tracked_test.write_text('import unittest\nclass T(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'tests/test_existing.py'], check=True, capture_output=True)
			subprocess.run(['git', '-C', str(repo), 'commit', '-m', 'init'], check=True, capture_output=True)

			tx = _write_transcript(base / 'transcript.jsonl', [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Edit via shell'},
			])
			# Shell-write to production code before Red -> DENIED
			d_shell_write = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'run_command',
					'args': {'CommandLine': f'Set-Content -Path "{repo / "app.py"}" -Value "x = 1"'},
				},
			})
			self.assertEqual(d_shell_write['decision'], 'deny', d_shell_write)
			self.assertIn('TDD-RED-GATE', d_shell_write.get('reason', ''))

			# Shell deletion of tracked test file without RATCHET-OK -> DENIED
			d_shell_del = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'run_command',
					'args': {'CommandLine': f'Remove-Item "{tracked_test}"'},
				},
			})
			self.assertEqual(d_shell_del['decision'], 'deny', d_shell_del)
			self.assertIn('TDD-RATCHET-GATE', d_shell_del.get('reason', ''))

	# @used-by :mod:`unittest`
	def test_ratchet_anti_fitting_substantive_and_behavioral_test_guards(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			repo = base / 'guard_repo'
			_init_git_repo(repo)
			(repo / 'tests').mkdir()
			tracked = repo / 'tests/test_core.py'
			orig_code = (
				'import unittest\n'
				'class CoreTests(unittest.TestCase):\n'
				'\tdef test_one(self):\n'
				'\t\tself.assertEqual(1 + 1, 2)\n'
			)
			tracked.write_text(orig_code, encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'tests/test_core.py'], check=True, capture_output=True)
			subprocess.run(['git', '-C', str(repo), 'commit', '-m', 'init'], check=True, capture_output=True)

			tx = _write_transcript(base / 'transcript.jsonl', [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Work on tests'},
			])

			# 1. Pure addition to tracked test file -> ALLOWED
			d_add = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'edit_file',
					'args': {
						'Path': str(tracked),
						'Target': '\t\tself.assertEqual(1 + 1, 2)\n',
						'Replacement': '\t\tself.assertEqual(1 + 1, 2)\n\tdef test_two(self):\n\t\tself.assertEqual(2 + 2, 4)\n',
					},
				},
			})
			self.assertEqual(d_add['decision'], 'allow', d_add)

			# 2. Altering existing assertion in tracked test file without RATCHET-OK -> DENIED
			d_weaken = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'edit_file',
					'args': {
						'Path': str(tracked),
						'Target': 'self.assertEqual(1 + 1, 2)',
						'Replacement': 'self.assertEqual(1 + 1, 3)',
					},
				},
			})
			self.assertEqual(d_weaken['decision'], 'deny', d_weaken)
			self.assertIn('TDD-RATCHET-GATE', d_weaken.get('reason', ''))

			# 3. Audited RATCHET-OK turn receipt unlocks the tracked test edit -> ALLOWED
			turns_dir = repo / 'ꘖ/data/turns'
			turns_dir.mkdir(parents=True)
			(turns_dir / 'turn1-ratchet-ok.json').write_text(
				json.dumps({
					'approvals': [{
						'file': 'tests/test_core.py',
						'reason': 'User explicitly changed the arithmetic specification in Issue #136 for this test case.',
					}],
				}),
				encoding='utf-8',
			)
			d_unlocked = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'edit_file',
					'args': {
						'Path': str(tracked),
						'Target': 'self.assertEqual(1 + 1, 2)',
						'Replacement': 'self.assertEqual(1 + 1, 3)',
					},
				},
			})
			self.assertEqual(d_unlocked['decision'], 'allow', d_unlocked)

			# 4. Anti-test-fitting: after prod edit in active cycle, weakening even a NEW untracked test is DENIED
			new_test = repo / 'tests/test_new_feature.py'
			new_test.write_text(
				'import unittest\nclass NewTests(unittest.TestCase):\n\tdef test_spec(self):\n\t\tself.assertEqual(run(), "expected")\n',
				encoding='utf-8',
			)
			prod_f = repo / 'src/feature.py'
			tx_green = _write_transcript(base / 'transcript_green.jsonl', [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Add feature'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(new_test)}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest "{new_test}"'}}]},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nAssertionError\n'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(prod_f)}}]},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'Created file.'},
			])
			d_fit = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx_green),
				'toolCall': {
					'name': 'edit_file',
					'args': {
						'Path': str(new_test),
						'Target': 'self.assertEqual(run(), "expected")',
						'Replacement': 'self.assertEqual(run(), "actual_buggy")',
					},
				},
			})
			self.assertEqual(d_fit['decision'], 'deny', d_fit)
			self.assertIn('TDD-ANTI-FITTING-GATE', d_fit.get('reason', ''))

			# 5. Assertionless test stub -> DENIED
			d_stub = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'write_file',
					'args': {'Path': str(repo / 'tests/test_stub.py'), 'Content': 'def test_nothing():\n\tpass\n'},
				},
			})
			self.assertEqual(d_stub['decision'], 'deny', d_stub)
			self.assertIn('TDD-SUBSTANTIVE-TEST-GATE', d_stub.get('reason', ''))

			# 6. Source-text grep test -> DENIED
			bad_test_src = (
				'from pathlib import Path\n'
				'def test_source_grep():\n'
				'\ttext = (Path(__file__).resolve().parents[1] / "scripts/app.py").read_text(encoding="utf-8")\n'
				'\tassert "def main" in text\n'
			)
			d_src = _run_hook({
				'cwd': str(repo),
				'transcriptPath': str(tx),
				'toolCall': {
					'name': 'write_file',
					'args': {'Path': str(repo / 'tests/test_grep.py'), 'Content': bad_test_src},
				},
			})
			self.assertEqual(d_src['decision'], 'deny', d_src)
			self.assertIn('TDD-BEHAVIORAL-GATE', d_src.get('reason', ''))

			# 7. Direct API check_tdd_gate symbol is exposed
			self.assertIsNotNone(
				gate.check_tdd_gate('write_file', {'Path': str(repo / 'src/untested.py'), 'Content': 'a = 1\n'}, {'cwd': str(repo), 'transcriptPath': str(tx)})
			)

	# 2026-11-24
	# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
	# https://github.com/dmitry-ai/harness/issues/175
	# @used-by :mod:`unittest`
	def test_cli_subprocess_smoke(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			repo = base / 'cli_repo'
			_init_git_repo(repo)
			tx = _write_transcript(base / 'transcript.jsonl', [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Smoke'}])
			payload = {'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo / 'src/app.py'), 'Content': 'x = 1\n'}}}
			proc = subprocess.run([sys.executable, str(HOOK_SCRIPT)], input=json.dumps(payload, ensure_ascii=False).encode('utf-8'), capture_output=True, check=True)
			decision = json.loads(proc.stdout.decode('utf-8'))
			self.assertEqual(decision['decision'], 'deny', decision)
			self.assertIn('TDD-RED-GATE', decision.get('reason', ''))


if '__main__' == __name__:
	unittest.main()
