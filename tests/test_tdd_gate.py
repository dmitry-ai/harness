# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement universal TDD verification engine in agent_tools/tdd_gate.py":
# https://github.com/dmitry-ai/harness/issues/135
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))

from agent_tools import tdd_gate


class TddGateCoreTests(unittest.TestCase):
	def test_universal_code_vs_test_vs_non_code_classification(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			# Production code across many languages
			for rel in (
				'scripts/agent_tools/tdd_gate.py',
				'src/app.js',
				'src/util.mjs',
				'src/view.tsx',
				'src/styles.css',
				'app/code/Vendor/Mod/Model/Order.php',
				'app/code/Vendor/Mod/view/frontend/templates/item.phtml',
				'UI/C1Runtime.cs',
				'UI/install.ps1',
				'bin/deploy.sh',
				'cmd/run.cmd',
				'pkg/server.go',
				'src/lib.rs',
				'src/Main.java',
				'queries/report.sql',
				'scripts/git_hooks/pre-commit',
			):
				self.assertEqual(
					tdd_gate.classify_code_path(root / rel),
					'production',
					f'Expected production for {rel}',
				)
			# Shebang extensionless script
			self.assertEqual(
				tdd_gate.classify_code_path(root / 'bin/mytool', content='#!/usr/bin/env bash\necho hi\n'),
				'production',
			)
			# Test files across many ecosystems
			for rel in (
				'tests/test_tdd_gate.py',
				'tests/helpers.py',
				'src/foo_test.py',
				'src/app.test.js',
				'src/catalog.test.mjs',
				'src/view.spec.tsx',
				'__tests__/button.jsx',
				'app/code/Vendor/Mod/Test/Unit/OrderTest.php',
				'Multi-Account/tests/AliasActivationRegression.cs',
				'UI/RecoveryNativeTests.cs',
				'UI/test-native.ps1',
				'scripts/deploy.Tests.ps1',
				'scripts/test_deploy.sh',
				'pkg/server_test.go',
				'tests/integration.rs',
				'src/test/java/MainTest.java',
				'spec/user_spec.rb',
			):
				self.assertEqual(
					tdd_gate.classify_code_path(root / rel),
					'test',
					f'Expected test for {rel}',
				)
			# Non-code docs, JSON configs, Harness data/journal/evidence
			for rel in (
				'readme.md',
				'rules/08-execution-and-tools.md',
				'tests/README.md',
				'paths.json',
				'runtime.json',
				'config.toml',
				'settings.yaml',
				'ꘖ/data/scratch/answer-abc.md',
				'ꘖ/KB/Evidence/HTTP/a/b/observation.json',
				'ꙮ/≺/1–20/1.md',
			):
				self.assertEqual(
					tdd_gate.classify_code_path(root / rel),
					'non_code',
					f'Expected non_code for {rel}',
				)

	def test_resolve_code_scope_normalizes_git_and_non_git_test_dirs(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			# Git repo scope
			repo = base / 'my_repo'
			(repo / '.git').mkdir(parents=True)
			self.assertEqual(tdd_gate.resolve_code_scope(repo / 'scripts/agent_tools/mod.py'), repo)
			self.assertEqual(tdd_gate.resolve_code_scope(repo / 'tests/test_mod.py'), repo)
			# Non-git standalone project with tests/ subdir
			standalone = base / 'standalone_app'
			(standalone / 'src').mkdir(parents=True)
			(standalone / 'tests').mkdir(parents=True)
			self.assertEqual(tdd_gate.resolve_code_scope(standalone / 'tests/test_app.py'), standalone)
			self.assertEqual(tdd_gate.resolve_code_scope(standalone / 'src/app.py'), standalone)
			self.assertEqual(tdd_gate.resolve_code_scope(standalone / 'app.py'), standalone)

	def test_test_command_detection_full_suite_vs_single_and_rigged_rejection(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve()
			(repo / 'tests').mkdir()
			(repo / 'tests/test_a.py').write_text('def test_a(): assert True\n', encoding='utf-8')
			(repo / 'tests/test_b.py').write_text('def test_b(): assert True\n', encoding='utf-8')

			# Full suite commands in a 2-test repo
			for cmd in (
				f'python -m unittest discover -s "{repo / "tests"}" -p "test_*.py"',
				'python -m unittest discover -s tests -p test_*.py -v',
				'pytest',
				'python -m pytest tests',
				'npm test',
				'pnpm test',
				'yarn test',
				'vitest run',
				'npx jest',
				'vendor/bin/phpunit',
				'dotnet test',
				'go test ./...',
				'cargo test',
				'Invoke-Pester',
				'node --test tests/*.test.mjs',
			):
				info = tdd_gate.classify_test_command(cmd, scope_root=repo)
				self.assertTrue(info['is_test_cmd'], f'Expected test cmd: {cmd}')
				self.assertTrue(info['is_full_suite'], f'Expected full suite: {cmd}')
				self.assertFalse(info['rigged_failure'], f'Unexpected rigged flag: {cmd}')

			# Single-file or filtered commands in a 2-test repo -> NOT full suite
			for cmd in (
				'python -m unittest tests/test_a.py',
				'python -m unittest discover -s tests -p test_a.py',
				'pytest tests/test_a.py',
				'pytest -k test_a',
				'node --test tests/catalog.test.mjs',
				'dotnet test --filter FullyQualifiedName~MyTest',
				'cargo test my_single_test',
				'go test ./pkg -run TestFoo',
			):
				info = tdd_gate.classify_test_command(cmd, scope_root=repo)
				self.assertTrue(info['is_test_cmd'], f'Expected test cmd: {cmd}')
				self.assertFalse(info['is_full_suite'], f'Expected non-full suite: {cmd}')

			# Single-file test in a 1-test repo IS the full suite
			with tempfile.TemporaryDirectory() as solo_tmp:
				solo = Path(solo_tmp).resolve()
				(solo / 'tests').mkdir(parents=True)
				(solo / 'tests/test_only.py').write_text('def test_only(): assert 1 == 1\n', encoding='utf-8')
				solo_info = tdd_gate.classify_test_command('python -m unittest tests/test_only.py', scope_root=solo)
				self.assertTrue(solo_info['is_test_cmd'])
				self.assertTrue(solo_info['is_full_suite'])

			# Non-test and rigged-failure commands must be rejected
			for bad_cmd in (
				'python -c "assert False"',
				'exit 1',
				'git status --no-optional-locks',
				'python scripts/harness.py doctor',
			):
				info = tdd_gate.classify_test_command(bad_cmd, scope_root=repo)
				self.assertFalse(info['is_test_cmd'], f'Must not classify as test cmd: {bad_cmd}')

			for rigged in (
				'python -m unittest tests/test_a.py; exit 1',
				'pytest && false',
				'npm test || exit 1',
			):
				info = tdd_gate.classify_test_command(rigged, scope_root=repo)
				self.assertTrue(info['rigged_failure'], f'Must flag rigged failure: {rigged}')

	def test_parse_command_outcome_sync_codex_and_background_task_log(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			t = Path(tmp).resolve()
			# Sync Antigravity failure (Red)
			red = tdd_gate.parse_command_outcome(
				'Command exited with code 1.\n\nCommand output:\nFAIL: test_x\nAssertionError: 1 != 2\nRan 1 test in 0.01s\nFAILED (failures=1)\n'
			)
			self.assertEqual(red['exit_code'], 1)
			self.assertTrue(red['is_failure'])
			self.assertFalse(red['is_pass'])
			self.assertFalse(red['is_invocation_error'])

			# CLI invocation error must NOT count as valid Red failure
			cli_err = tdd_gate.parse_command_outcome(
				"Command exited with code 1.\n\nCommand output:\n'pytest' is not recognized as an internal or external command.\n"
			)
			self.assertTrue(cli_err['is_invocation_error'])
			self.assertFalse(cli_err['is_failure'])

			# Zero tests ran with exit 0 must NOT count as valid Green pass
			zero_run = tdd_gate.parse_command_outcome(
				'Command exited with code 0.\n\nCommand output:\n----------------------------------------------------------------------\nRan 0 tests in 0.000s\n\nOK\n'
			)
			self.assertTrue(zero_run['ran_zero_tests'])
			self.assertFalse(zero_run['is_pass'])

			# Codex output format
			codex_pass = tdd_gate.parse_command_outcome(
				'Process exited with code 0\nOutput:\n....\nRan 4 tests in 0.12s\nOK\n'
			)
			self.assertEqual(codex_pass['exit_code'], 0)
			self.assertTrue(codex_pass['is_pass'])

			# Antigravity background task log resolution
			log_file = t / 'task-99.log'
			log_file.write_text('....................\n----------------------------------------------------------------------\nRan 20 tests in 12.3s\n\nOK\n', encoding='utf-8')
			bg_out = (
				'Tool is running as a background task with task id: conv-1/task-99\n'
				f'Task logs are available at: {log_file.as_uri()}\n'
				'Log output:\n...'
			)
			bg_res = tdd_gate.parse_command_outcome(bg_out)
			self.assertEqual(bg_res['background_task_id'], 'conv-1/task-99')
			self.assertTrue(bg_res['is_pass'])
			self.assertEqual(bg_res['exit_code'], 0)

	def test_chronological_tdd_state_machine_and_commit_reset(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve()
			(repo / '.git').mkdir()
			(repo / 'tests').mkdir()
			(repo / 'tests/test_a.py').write_text('def test_a(): assert 1 == 1\n', encoding='utf-8')
			(repo / 'tests/test_b.py').write_text('def test_b(): assert 2 == 2\n', encoding='utf-8')
			prod_a = str(repo / 'src/a.py')
			prod_b = str(repo / 'src/b.py')
			test_a = str(repo / 'tests/test_a.py')
			test_b = str(repo / 'tests/test_b.py')

			# 1. Prod write with no prior test -> FAIL
			ev_no_test = [
				{'kind': 'file_write', 'step': 1, 'path': prod_a, 'classification': 'production', 'scope': str(repo)},
			]
			res1 = tdd_gate.evaluate_tdd_events(ev_no_test, require_final_full_green=False)
			self.assertFalse(res1['verified'])
			self.assertTrue(any('without first writing a test' in v or 'failing (RED)' in v for v in res1['violations']))

			# 2. Test written, NOT run before prod write -> FAIL
			ev_unrun = [
				{'kind': 'file_write', 'step': 1, 'path': test_a, 'classification': 'test', 'scope': str(repo)},
				{'kind': 'file_write', 'step': 2, 'path': prod_a, 'classification': 'production', 'scope': str(repo)},
			]
			res2 = tdd_gate.evaluate_tdd_events(ev_unrun, require_final_full_green=False)
			self.assertFalse(res2['verified'])

			# 3. Test written -> test PASSED (never Red!) -> prod write -> FAIL
			ev_green_only = [
				{'kind': 'file_write', 'step': 1, 'path': test_a, 'classification': 'test', 'scope': str(repo)},
				{
					'kind': 'command', 'step': 2, 'cmd': 'python -m unittest tests/test_a.py', 'cwd': str(repo),
					'outcome': tdd_gate.parse_command_outcome('Command exited with code 0.\nRan 1 test in 0.01s\nOK\n'),
					'test_info': tdd_gate.classify_test_command('python -m unittest tests/test_a.py', scope_root=repo),
					'is_git_commit': False, 'commit_scope': None,
				},
				{'kind': 'file_write', 'step': 3, 'path': prod_a, 'classification': 'production', 'scope': str(repo)},
			]
			res3 = tdd_gate.evaluate_tdd_events(ev_green_only, require_final_full_green=False)
			self.assertFalse(res3['verified'])

			# 4. Full Red -> Green -> ONLY single-file Green in 2-test repo -> FAIL full-suite check
			ev_single_green = [
				{'kind': 'file_write', 'step': 1, 'path': test_a, 'classification': 'test', 'scope': str(repo)},
				{
					'kind': 'command', 'step': 2, 'cmd': 'python -m unittest tests/test_a.py', 'cwd': str(repo),
					'outcome': tdd_gate.parse_command_outcome('Command exited with code 1.\nAssertionError\nFAILED (failures=1)\n'),
					'test_info': tdd_gate.classify_test_command('python -m unittest tests/test_a.py', scope_root=repo),
					'is_git_commit': False, 'commit_scope': None,
				},
				{'kind': 'file_write', 'step': 3, 'path': prod_a, 'classification': 'production', 'scope': str(repo)},
				{
					'kind': 'command', 'step': 4, 'cmd': 'python -m unittest tests/test_a.py', 'cwd': str(repo),
					'outcome': tdd_gate.parse_command_outcome('Command exited with code 0.\nRan 1 test in 0.01s\nOK\n'),
					'test_info': tdd_gate.classify_test_command('python -m unittest tests/test_a.py', scope_root=repo),
					'is_git_commit': False, 'commit_scope': None,
				},
			]
			res4_mid = tdd_gate.evaluate_tdd_events(ev_single_green, require_final_full_green=False)
			self.assertTrue(res4_mid['verified'], res4_mid)
			res4_final = tdd_gate.evaluate_tdd_events(ev_single_green, require_final_full_green=True)
			self.assertFalse(res4_final['verified'])
			self.assertTrue(any('full test suite' in v.lower() for v in res4_final['violations']), res4_final['violations'])

			# 5. Full Red -> Green -> Full-suite Green -> PASS
			ev_full_green = [
				*ev_single_green,
				{
					'kind': 'command', 'step': 5, 'cmd': 'python -m unittest discover -s tests -p "test_*.py"', 'cwd': str(repo),
					'outcome': tdd_gate.parse_command_outcome('Command exited with code 0.\nRan 2 tests in 0.02s\nOK\n'),
					'test_info': tdd_gate.classify_test_command('python -m unittest discover -s tests -p "test_*.py"', scope_root=repo),
					'is_git_commit': False, 'commit_scope': None,
				},
			]
			res5 = tdd_gate.evaluate_tdd_events(ev_full_green, require_final_full_green=True)
			self.assertTrue(res5['verified'], res5)

			# 6. Git commit resets TDD cycle -> next prod edit WITHOUT new failing test -> FAIL
			ev_after_commit = [
				*ev_full_green,
				{
					'kind': 'command', 'step': 6, 'cmd': f'git -C "{repo}" commit -m https://github.com/dmitry-ai/harness/issues/135',
					'cwd': str(repo),
					'outcome': tdd_gate.parse_command_outcome('Command exited with code 0.\n[main abc1234]\n'),
					'test_info': tdd_gate.classify_test_command('git commit', scope_root=repo),
					'is_git_commit': True, 'commit_scope': str(repo),
				},
				{'kind': 'file_write', 'step': 7, 'path': prod_b, 'classification': 'production', 'scope': str(repo)},
			]
			res6 = tdd_gate.evaluate_tdd_events(ev_after_commit, require_final_full_green=False)
			self.assertFalse(res6['verified'])
			self.assertTrue(any('b.py' in v for v in res6['violations']), res6['violations'])

			# 7. After commit, writing test_b -> Red -> prod_b -> full Green -> PASS
			ev_two_cycles = [
				*ev_after_commit[:-1],
				{'kind': 'file_write', 'step': 7, 'path': test_b, 'classification': 'test', 'scope': str(repo)},
				{
					'kind': 'command', 'step': 8, 'cmd': 'python -m unittest tests/test_b.py', 'cwd': str(repo),
					'outcome': tdd_gate.parse_command_outcome('Command exited with code 1.\nFAILED (errors=1)\n'),
					'test_info': tdd_gate.classify_test_command('python -m unittest tests/test_b.py', scope_root=repo),
					'is_git_commit': False, 'commit_scope': None,
				},
				{'kind': 'file_write', 'step': 9, 'path': prod_b, 'classification': 'production', 'scope': str(repo)},
				{
					'kind': 'command', 'step': 10, 'cmd': 'python -m unittest discover -s tests -p "test_*.py"', 'cwd': str(repo),
					'outcome': tdd_gate.parse_command_outcome('Command exited with code 0.\nRan 2 tests in 0.02s\nOK\n'),
					'test_info': tdd_gate.classify_test_command('python -m unittest discover -s tests -p "test_*.py"', scope_root=repo),
					'is_git_commit': False, 'commit_scope': None,
				},
			]
			res7 = tdd_gate.evaluate_tdd_events(ev_two_cycles, require_final_full_green=True)
			self.assertTrue(res7['verified'], res7)

	def test_ratchet_diff_guard_and_ratchet_ok_validation(self) -> None:
		old_py = (
			'import unittest\n'
			'class DemoTests(unittest.TestCase):\n'
			'\tdef test_addition(self):\n'
			'\t\tself.assertEqual(add(2, 2), 4)\n'
			'\tdef test_subtraction(self):\n'
			'\t\tself.assertEqual(sub(5, 3), 2)\n'
		)
		# Pure addition of a new test -> ALLOWED
		added_py = old_py + '\tdef test_mul(self):\n\t\tself.assertEqual(mul(3, 4), 12)\n'
		self.assertEqual(tdd_gate.ratchet_diff_violations('tests/test_math.py', old_py, added_py), [])

		# Pure re-indentation keeping exact stripped assertion verbatim -> ALLOWED
		reindented_py = (
			'import unittest\n'
			'class DemoTests(unittest.TestCase):\n'
			'\tdef test_addition(self):\n'
			'\t\tif True:\n'
			'\t\t\tself.assertEqual(add(2, 2), 4)\n'
			'\tdef test_subtraction(self):\n'
			'\t\tself.assertEqual(sub(5, 3), 2)\n'
		)
		self.assertEqual(tdd_gate.ratchet_diff_violations('tests/test_math.py', old_py, reindented_py), [])

		# Deleting an assertion -> BLOCKED
		deleted_assert = old_py.replace('\t\tself.assertEqual(sub(5, 3), 2)\n', '\t\tpass\n')
		v_del = tdd_gate.ratchet_diff_violations('tests/test_math.py', old_py, deleted_assert)
		self.assertTrue(v_del, 'Expected ratchet block when deleting assertion')

		# Altering expected value in existing assertion -> BLOCKED
		altered_assert = old_py.replace('self.assertEqual(add(2, 2), 4)', 'self.assertEqual(add(2, 2), 5)')
		v_alt = tdd_gate.ratchet_diff_violations('tests/test_math.py', old_py, altered_assert)
		self.assertTrue(v_alt, 'Expected ratchet block when altering assertion')

		# Adding @unittest.skip to disable existing test -> BLOCKED
		skipped_test = old_py.replace('\tdef test_subtraction(self):\n', '\t@unittest.skip("broken")\n\tdef test_subtraction(self):\n')
		v_skip = tdd_gate.ratchet_diff_violations('tests/test_math.py', old_py, skipped_test)
		self.assertTrue(v_skip, 'Expected ratchet block when skipping existing test')

		# Deleting entire test file -> BLOCKED
		v_rm = tdd_gate.ratchet_diff_violations('tests/test_math.py', old_py, None)
		self.assertTrue(v_rm, 'Expected ratchet block when deleting test file')

		# Valid RATCHET-OK approval unlocks
		ok_valid, ok_err = tdd_gate.validate_ratchet_reason(
			'User directive in Issue #134 changed tax rounding rule from half-up to half-even.'
		)
		self.assertTrue(ok_valid, ok_err)
		self.assertEqual(
			tdd_gate.ratchet_diff_violations(
				'tests/test_math.py',
				old_py,
				altered_assert,
				approval={'reason': 'User directive in Issue #134 changed tax rounding rule from half-up to half-even.'},
			),
			[],
		)

		# Short or vague test-fitting reasons must be REJECTED
		for bad_reason in (
			'too short',
			'Updated test expectation to match new implementation output.',
			'Adjusting failing test so CI turns green again.',
		):
			ok_b, _ = tdd_gate.validate_ratchet_reason(bad_reason)
			self.assertFalse(ok_b, f'Expected rejection for vague reason: {bad_reason}')

	def test_behavioral_test_guard_catches_source_text_and_wrappers_without_false_positives(self) -> None:
		# Direct Python source-text grep -> REJECTED
		bad_py = (
			'from pathlib import Path\n'
			'def test_has_flag():\n'
			'\tsrc = (Path(__file__).resolve().parents[1] / "scripts/check_stop_gate.py").read_text(encoding="utf-8")\n'
			'\tassert "code_lifecycle_check" in src\n'
		)
		issues_py = tdd_gate.source_text_assertion_issues(
			'tests/test_bad.py',
			bad_py.splitlines(),
			full_content=bad_py,
			added_line_numbers=set(range(1, 5)),
		)
		self.assertTrue(issues_py, 'Expected rejection of Python source-text assertion')

		# inspect.getsource in test -> REJECTED
		bad_inspect = (
			'import inspect\n'
			'def test_source_snippet():\n'
			'\tassert "locked(" in inspect.getsource(target_fn)\n'
		)
		issues_insp = tdd_gate.source_text_assertion_issues(
			'tests/test_bad_inspect.py',
			bad_inspect.splitlines(),
			full_content=bad_inspect,
			added_line_numbers={1, 2, 3},
		)
		self.assertTrue(issues_insp, 'Expected rejection of inspect.getsource test')

		# JS wrapper-obfuscated source-text check (the exact Habr article bypass!) -> REJECTED
		bad_js = (
			"import fs from 'node:fs';\n"
			"function check(cond) { if (!cond) throw new Error('fail'); }\n"
			"const src = fs.readFileSync('src/form.js', 'utf8');\n"
			"check(src.includes('formIsReadOnly'));\n"
		)
		issues_js = tdd_gate.source_text_assertion_issues('tests/form.test.mjs', bad_js.splitlines())
		self.assertTrue(issues_js, 'Expected rejection of JS wrapper source-text assertion')

		# Legitimate test reading generated file inside TemporaryDirectory / self.root -> ALLOWED
		good_py = (
			'import tempfile\n'
			'from pathlib import Path\n'
			'def test_generated_runner_is_ascii(self):\n'
			'\twith tempfile.TemporaryDirectory() as tmp:\n'
			'\t\trunner = Path(tmp) / "harness_hook_runner.py"\n'
			'\t\trunner.write_text("print(1)\\n", encoding="utf-8")\n'
			'\t\tself.assertTrue(runner.read_text(encoding="utf-8").isascii())\n'
		)
		issues_good = tdd_gate.source_text_assertion_issues(
			'tests/test_good.py',
			good_py.splitlines(),
			full_content=good_py,
			added_line_numbers=set(range(1, 8)),
		)
		self.assertEqual(issues_good, [], f'Unexpected false positive: {issues_good}')

		# Reading a Markdown doc file -> ALLOWED (not production code)
		good_md = (
			'from pathlib import Path\n'
			'def test_doc():\n'
			'\ttxt = (Path(__file__).resolve().parents[1] / "rules/08-execution-and-tools.md").read_text(encoding="utf-8")\n'
			'\tassert len(txt) > 0\n'
		)
		self.assertEqual(
			tdd_gate.source_text_assertion_issues(
				'tests/test_doc.py',
				good_md.splitlines(),
				full_content=good_md,
				added_line_numbers={1, 2, 3, 4},
			),
			[],
		)

		# Substantive test check rejects empty / assertionless stub
		ok_empty, _ = tdd_gate.is_substantive_test_content('tests/test_empty.py', '# just a comment\n')
		self.assertFalse(ok_empty)
		ok_stub, _ = tdd_gate.is_substantive_test_content('tests/test_stub.py', 'def test_nothing():\n\tpass\n')
		self.assertFalse(ok_stub)
		ok_real, err_real = tdd_gate.is_substantive_test_content(
			'tests/test_real.py',
			'import unittest\nclass T(unittest.TestCase):\n\tdef test_x(self):\n\t\tself.assertEqual(1, 1)\n',
		)
		self.assertTrue(ok_real, err_real)

	def test_shell_code_write_targets_and_ratchet_issue_evidence(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			# PowerShell / Python / Unix shell writes to production code files
			for cmd, expected_name in (
				(f'Set-Content -Path "{root / "app.py"}" -Value "x = 1"', 'app.py'),
				(f'[System.IO.File]::WriteAllText("{root / "util.js"}", "export default 1;")', 'util.js'),
				(f'python -c "from pathlib import Path; Path(\'{(root / "mod.py").as_posix()}\').write_text(\'x=1\')"', 'mod.py'),
				(f'echo "x=1" > "{root / "run.sh"}"', 'run.sh'),
				(f'sed -i "s/a/b/" "{root / "app.php"}"', 'app.php'),
			):
				targets = tdd_gate.shell_code_write_targets(cmd, cwd=root)
				self.assertTrue(any(p.name == expected_name for p in targets), f'Missed target {expected_name} in {cmd}: {targets}')

			# Non-code scratch write or read-only command must NOT trigger
			self.assertEqual(tdd_gate.shell_code_write_targets('python -m unittest discover -s tests', cwd=root), [])
			self.assertEqual(tdd_gate.shell_code_write_targets(f'Set-Content -Path "{root / "notes.md"}" -Value "hi"', cwd=root), [])

			# GitHub Issue Evidence JSON RATCHET-OK discovery
			ev_dir = root / 'ꘖ/KB/Evidence/GitHub/dmitry-ai__harness'
			ev_dir.mkdir(parents=True)
			issue_url = 'https://github.com/dmitry-ai/harness/issues/135'
			(ev_dir / 'issue-135.json').write_text(
				json.dumps({
					'url': issue_url,
					'issue': {
						'number': 135,
						'state': 'OPEN',
						'body': (
							'## Scope\nUpdate fixture.\n\n'
							'RATCHET-OK: tests/test_legacy.py — User explicitly changed contract in Issue #134 to require TDD tests on code commits.\n'
						),
					},
				}),
				encoding='utf-8',
			)
			found = tdd_gate.find_ratchet_approval(
				'tests/test_legacy.py',
				repo_root=root,
				project_root=root,
				issue_urls=(issue_url,),
			)
			self.assertIsNotNone(found)
			self.assertIn('Issue #134', found['reason'])
			self.assertIsNone(
				tdd_gate.find_ratchet_approval(
					'tests/test_other.py',
					repo_root=root,
					project_root=root,
					issue_urls=(issue_url,),
				)
			)

	def test_extract_antigravity_tdd_events_handles_compact_and_full_transcripts(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			t = Path(tmp).resolve()
			repo = t / 'repo'
			(repo / '.git').mkdir(parents=True)
			test_f = repo / 'tests/test_demo.py'
			prod_f = repo / 'src/demo.py'
			# Compact transcript with double-encoded JSON arg strings
			compact = t / 'transcript.jsonl'
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Add demo feature'},
				{
					'step_index': 1, 'type': 'PLANNER_RESPONSE',
					'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(test_f))}}],
				},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
				{
					'step_index': 3, 'type': 'PLANNER_RESPONSE',
					'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'python -m unittest "{test_f}"')}}],
				},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nImportError: no module demo\n'},
				{
					'step_index': 5, 'type': 'PLANNER_RESPONSE',
					'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(prod_f))}}],
				},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'Created file.'},
			]
			compact.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
			events = tdd_gate.extract_antigravity_tdd_events(compact, cwd=repo)
			res = tdd_gate.evaluate_tdd_events(events, require_final_full_green=False)
			self.assertTrue(res['verified'], res)
			self.assertEqual(res['scopes'][str(repo)]['state'], 'GREEN_IMPLEMENTING')

	def test_hardening_header_exit_code_indirect_source_read_and_index_blob(self) -> None:
		# 1. Header exit code must NOT be overridden by stdout/JSON containing "Command exited with code ..."
		nested_json_pass = (
			'Created At: 2026-11-23T19:20:36+03:00\n'
			'Completed At: 2026-11-23T19:20:42+03:00\n'
			'Command exited with code 0.\n\n'
			'Command output:\n'
			'{"preview": "Command exited with code 1."}\n'
		)
		res_ok = tdd_gate.parse_command_outcome(nested_json_pass)
		self.assertEqual(res_ok['exit_code'], 0)
		self.assertTrue(res_ok['is_pass'])
		self.assertFalse(res_ok['is_failure'])

		spoofed_pass_in_stdout = (
			'Command exited with code 1.\n\n'
			'Command output:\n'
			'Command exited with code 0.\n'
			'FAILED (failures=1)\n'
		)
		res_fail = tdd_gate.parse_command_outcome(spoofed_pass_in_stdout)
		self.assertEqual(res_fail['exit_code'], 1)
		self.assertTrue(res_fail['is_failure'])
		self.assertFalse(res_fail['is_pass'])

		# 2. Variable-indirection & wrapper-function source-text reads must be caught in Python tests
		var_indirect_py = (
			'from pathlib import Path\n'
			'def test_var_indirect():\n'
			'\tsrc_file = Path(__file__).resolve().parents[1] / "scripts/app.py"\n'
			'\ttext = src_file.read_text(encoding="utf-8")\n'
			'\tassert "def run" in text\n'
		)
		issues_var = tdd_gate.source_text_assertion_issues(
			'tests/test_var_indirect.py',
			var_indirect_py.splitlines(),
			full_content=var_indirect_py,
			added_line_numbers=set(range(1, 6)),
		)
		self.assertTrue(issues_var, 'Expected rejection of variable-bound production source read')

		wrapper_py = (
			'from pathlib import Path\n'
			'REPO = Path(__file__).resolve().parents[1]\n'
			'def load_src(rel):\n'
			'\treturn (REPO / rel).read_text(encoding="utf-8")\n'
			'def test_wrapper():\n'
			'\tassert "x" in load_src("scripts/app.py")\n'
		)
		issues_wrap = tdd_gate.source_text_assertion_issues(
			'tests/test_wrapper.py',
			wrapper_py.splitlines(),
			full_content=wrapper_py,
			added_line_numbers=set(range(1, 7)),
		)
		self.assertTrue(issues_wrap, 'Expected rejection of helper-wrapped production source read')

		# Temp variable read-back must still be allowed
		temp_var_py = (
			'import tempfile\n'
			'from pathlib import Path\n'
			'def test_temp_var():\n'
			'\twith tempfile.TemporaryDirectory() as tmp:\n'
			'\t\tf = Path(tmp) / "app.py"\n'
			'\t\tf.write_text("x = 1\\n", encoding="utf-8")\n'
			'\t\tassert "x = 1" in f.read_text(encoding="utf-8")\n'
		)
		self.assertEqual(
			tdd_gate.source_text_assertion_issues(
				'tests/test_temp_var.py',
				temp_var_py.splitlines(),
				full_content=temp_var_py,
				added_line_numbers=set(range(1, 8)),
			),
			[],
		)

		# 3. verify_staged_tdd_diff(use_index=True) inspects staged Git index blob, not unstaged working tree
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve()
			subprocess.run(['git', 'init', str(repo)], check=True, capture_output=True)
			subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'test@example.com'], check=True, capture_output=True)
			subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True, capture_output=True)
			(repo / 'tests').mkdir()
			(repo / 'tests/test_app.py').write_text('def test_ok():\n\tassert 1 == 1\n', encoding='utf-8')
			(repo / 'app.py').write_text('def val(): return 1\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'app.py', 'tests/test_app.py'], check=True, capture_output=True)
			subprocess.run(['git', '-C', str(repo), 'commit', '-m', 'init'], check=True, capture_output=True)
			# Stage an assertion deletion in the index, then restore the working tree without re-staging
			(repo / 'tests/test_app.py').write_text('def test_ok():\n\tpass\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'tests/test_app.py'], check=True, capture_output=True)
			(repo / 'tests/test_app.py').write_text('def test_ok():\n\tassert 1 == 1\n', encoding='utf-8')
			idx_violations = tdd_gate.verify_staged_tdd_diff(repo, ['tests/test_app.py'], use_index=True)
			self.assertTrue(idx_violations, 'Expected index-blob ratchet/substantive rejection even when working tree was restored')


if '__main__' == __name__:
	unittest.main()
