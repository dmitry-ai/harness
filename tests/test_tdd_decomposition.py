# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = HARNESS_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
def _init_temp_git_repo(repo: Path) -> None:
	for args in (
		['git', 'init', '-q'],
		['git', 'config', 'user.email', 'test@example.com'],
		['git', 'config', 'user.name', 'Test User'],
	):
		subprocess.run(args, cwd=repo, check=True, capture_output=True)
# 2026-11-24
# "Decompose tdd_gate.py into modular TDD verification package":
# https://github.com/dmitry-ai/harness/issues/169
class TddDecompositionTests(unittest.TestCase):
	def test_classifier_module_behavior_and_parity(self) -> None:
		from agent_tools import tdd_gate
		from agent_tools.tdd import classifier
		for sym in ('SOFTWARE_CODE_SUFFIXES', 'classify_code_path', 'count_repo_test_files', 'is_software_code_file', 'is_test_file', 'resolve_code_scope'):
			self.assertIs(getattr(tdd_gate, sym), getattr(classifier, sym))
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			(repo / '.git').mkdir()
			(repo / 'src').mkdir()
			(repo / 'tests').mkdir()
			(repo / 'src/service.py').write_text('x = 1\n', encoding='utf-8')
			(repo / 'tests/test_a.py').write_text('assert True\n', encoding='utf-8')
			(repo / 'tests/test_b.py').write_text('assert True\n', encoding='utf-8')
			self.assertEqual('production', classifier.classify_code_path(repo / 'src/service.py'))
			self.assertEqual('test', classifier.classify_code_path(repo / 'tests/test_a.py'))
			self.assertEqual('non_code', classifier.classify_code_path(repo / 'README.md'))
			self.assertEqual('production', classifier.classify_code_path(repo / 'bin/tool', content='#!/usr/bin/env bash\necho ok\n'))
			self.assertEqual(repo, classifier.resolve_code_scope(repo / 'src/service.py'))
			self.assertEqual(repo, classifier.resolve_code_scope(repo / 'tests/test_a.py'))
			self.assertEqual(2, classifier.count_repo_test_files(repo))
	def test_commands_module_behavior_and_parity(self) -> None:
		from agent_tools import tdd_gate
		from agent_tools.tdd import commands
		for sym in ('classify_test_command', 'shell_code_write_targets', 'shell_test_delete_targets', 'shell_write_targets'):
			self.assertIs(getattr(tdd_gate, sym), getattr(commands, sym))
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			(repo / 'tests').mkdir()
			(repo / 'tests/test_a.py').write_text('assert True\n', encoding='utf-8')
			(repo / 'tests/test_b.py').write_text('assert True\n', encoding='utf-8')
			full_rt = commands.classify_test_command('python scripts/harness.py run-tests tests', scope_root=repo)
			self.assertTrue(full_rt['is_test_cmd'] and full_rt['is_full_suite'] and (not full_rt['rigged_failure']))
			mod_rt = commands.classify_test_command('python scripts/harness.py run-tests tests --module test_a', scope_root=repo)
			self.assertTrue(mod_rt['is_test_cmd'] and (not mod_rt['is_full_suite']))
			self.assertTrue(commands.classify_test_command('go test ./...', scope_root=repo)['is_full_suite'])
			self.assertFalse(commands.classify_test_command('pytest -k alpha', scope_root=repo)['is_full_suite'])
			self.assertTrue(commands.classify_test_command('pytest; exit 1', scope_root=repo)['rigged_failure'])
			self.assertFalse(commands.classify_test_command('echo hello', scope_root=repo)['is_test_cmd'])
			self.assertEqual([(repo / 'src/app.py').resolve()], commands.shell_code_write_targets('Set-Content -Path "src/app.py" -Value "x=1"', cwd=repo))
			self.assertEqual([], commands.shell_code_write_targets('Set-Content -Path "tests/test_a.py" -Value "x=1"', cwd=repo))
			self.assertEqual([(repo / 'tests/test_a.py').resolve()], commands.shell_write_targets('Set-Content -Path "tests/test_a.py" -Value "x=1"', cwd=repo))
			self.assertEqual([(repo / 'tests/test_a.py').resolve()], commands.shell_test_delete_targets('rm tests/test_a.py', cwd=repo))
	def test_enforcement_module_behavior_and_parity(self) -> None:
		from agent_tools import tdd_gate
		from agent_tools.tdd import enforcement
		for sym in ('_compute_edited_content', '_git_head_text', '_git_index_text', 'evaluate_pre_tool_use_tdd', 'verify_staged_tdd_diff'):
			self.assertIs(getattr(tdd_gate, sym), getattr(enforcement, sym))
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			_init_temp_git_repo(repo)
			(repo / 'src').mkdir()
			(repo / 'tests').mkdir()
			(repo / 'src/app.py').write_text('def val():\n\treturn 1\n', encoding='utf-8')
			test_orig = 'import unittest\nclass T(unittest.TestCase):\n\tdef test_v(self):\n\t\tself.assertEqual(1, 1)\n'
			(repo / 'tests/test_app.py').write_text(test_orig, encoding='utf-8')
			subprocess.run(['git', 'add', '.'], cwd=repo, check=True, capture_output=True)
			subprocess.run(['git', 'commit', '-m', 'init'], cwd=repo, check=True, capture_output=True)
			self.assertEqual(test_orig, enforcement._git_head_text(repo, 'tests/test_app.py'))
			tx = repo / 'empty_tx.jsonl'
			tx.write_text('', encoding='utf-8')
			blocked = enforcement.evaluate_pre_tool_use_tdd('write_file', {'Path': str(repo / 'src/app.py'), 'Content': 'def val():\n\treturn 2\n'}, {'cwd': str(repo), 'transcriptPath': str(tx)})
			self.assertIsNotNone(blocked)
			self.assertIn('TDD-RED-GATE', blocked)
			ratchet_err = enforcement.evaluate_pre_tool_use_tdd('write_file', {'Path': str(repo / 'tests/test_app.py'), 'Content': 'import unittest\nclass T(unittest.TestCase):\n\tdef test_v(self):\n\t\tself.assertTrue(True)\n'}, {'cwd': str(repo), 'transcriptPath': str(tx)})
			self.assertIsNotNone(ratchet_err)
			self.assertIn('TDD-RATCHET-GATE', ratchet_err)
			(repo / 'src/app.py').write_text('def val():\n\treturn 2\n', encoding='utf-8')
			prod_only_errs = enforcement.verify_staged_tdd_diff(repo, ['src/app.py'])
			self.assertTrue(any('TDD-COMMIT-GATE' in e for e in prod_only_errs))
			(repo / 'tests/test_app.py').write_text(test_orig + '\tdef test_w(self):\n\t\tself.assertEqual(2, 2)\n', encoding='utf-8')
			self.assertEqual([], enforcement.verify_staged_tdd_diff(repo, ['src/app.py', 'tests/test_app.py']))
	def test_evaluator_module_behavior_and_parity(self) -> None:
		from agent_tools import tdd_gate
		from agent_tools.tdd import evaluator, events
		for sym in ('_command_matches_scope', '_git_main_repo_root', 'evaluate_tdd_events'):
			self.assertIs(getattr(tdd_gate, sym), getattr(evaluator, sym))
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			(repo / '.git').mkdir()
			(repo / 'tests').mkdir()
			(repo / 'tests/test_a.py').write_text('assert True\n', encoding='utf-8')
			(repo / 'tests/test_b.py').write_text('assert True\n', encoding='utf-8')
			no_red = [events.build_file_write_tdd_event(1, repo / 'app.py')]
			self.assertFalse(evaluator.evaluate_tdd_events(no_red, require_final_full_green=False)['verified'])
			full_cycle = [
				events.build_file_write_tdd_event(1, repo / 'tests/test_a.py'),
				events.build_command_tdd_event(2, 'python -m unittest tests/test_a.py -f', 'Command exited with code 1.\nFAILED (failures=1)\n', cwd=repo, scope_hint=repo),
				events.build_file_write_tdd_event(3, repo / 'app.py'),
				events.build_command_tdd_event(4, 'python -m unittest discover -s tests -p "test_*.py" -f', 'Command exited with code 0.\nRan 2 tests in 0.01s\nOK\n', cwd=repo, scope_hint=repo),
			]
			self.assertTrue(evaluator.evaluate_tdd_events(full_cycle, require_final_full_green=True)['verified'])
			after_commit = full_cycle + [
				events.build_command_tdd_event(5, 'git commit -m https://github.com/dmitry-ai/harness/issues/169', 'Command exited with code 0.\n[task 111] ok\n', cwd=repo, scope_hint=repo),
				events.build_file_write_tdd_event(6, repo / 'app.py'),
			]
			self.assertFalse(evaluator.evaluate_tdd_events(after_commit, require_final_full_green=False)['verified'])
	def test_events_module_behavior_and_parity(self) -> None:
		from agent_tools import tdd_gate
		from agent_tools.tdd import events
		for sym in ('_antigravity_segment_is_interrupted', '_is_git_commit_command', '_normalize_args_dict', 'build_command_tdd_event', 'build_file_write_tdd_event', 'extract_antigravity_tdd_events'):
			self.assertIs(getattr(tdd_gate, sym), getattr(events, sym))
		self.assertEqual({'Path': 'a.py'}, events._normalize_args_dict('{"Path": "\\"a.py\\""}'))
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			(repo / '.git').mkdir()
			tx = repo / 'transcript_full.jsonl'
			rows = [
				{'step_index': 1, 'type': 'USER_INPUT', 'content': 'Fix bug'},
				{'step_index': 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(repo / 'tests/test_a.py'), 'Content': 'assert False\n'}}]},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python -m unittest tests/test_a.py -f'}}]},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Running in background. Task id: task-bg-1'},
				{'step_index': 5, 'type': 'SYSTEM_MESSAGE', 'content': 'Task id "task-bg-1" finished with result:\nCommand exited with code 1.\nFAILED (failures=1)\n'},
				{'step_index': 6, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(repo / 'app.py'), 'Content': 'x = 1\n'}}]},
			]
			tx.write_text('\n'.join(json.dumps(r) for r in rows) + '\n', encoding='utf-8')
			extracted = events.extract_antigravity_tdd_events(tx, cwd=repo)
			self.assertEqual(3, len(extracted))
			self.assertEqual('test', extracted[0]['classification'])
			self.assertTrue(extracted[1]['outcome']['is_failure'])
			self.assertEqual('production', extracted[2]['classification'])
	def test_facade_and_package_exports_preserve_all_legacy_symbols(self) -> None:
		from agent_tools import tdd, tdd_gate
		required_facade = (
			'SOFTWARE_CODE_SUFFIXES', '_ASSERTION_LINE_RE', '_BG_TASK_FINISHED_RE', '_BG_TASK_ID_RE', '_BG_TASK_LOG_RE',
			'_active_turn_issue_urls', '_antigravity_segment_is_interrupted', '_command_matches_scope', '_compute_edited_content',
			'_git_head_text', '_git_index_text', '_git_main_repo_root', '_is_git_commit_command', '_normalize_args_dict',
			'build_command_tdd_event', 'build_file_write_tdd_event', 'classify_code_path', 'classify_test_command',
			'count_repo_test_files', 'evaluate_pre_tool_use_tdd', 'evaluate_tdd_events', 'extract_antigravity_tdd_events',
			'find_ratchet_approval', 'is_software_code_file', 'is_substantive_test_content', 'is_test_file',
			'parse_command_outcome', 'ratchet_diff_violations', 'resolve_code_scope', 'shell_code_write_targets',
			'shell_test_delete_targets', 'shell_write_targets', 'source_text_assertion_issues',
			'validate_ratchet_reason', 'verify_staged_tdd_diff',
		)
		for sym in required_facade:
			self.assertTrue(hasattr(tdd_gate, sym), f'Missing tdd_gate export: {sym}')
		for pub in tdd.__all__:
			self.assertIs(getattr(tdd, pub), getattr(tdd_gate, pub))
	def test_outcomes_module_behavior_and_parity(self) -> None:
		from agent_tools import tdd_gate
		from agent_tools.tdd import outcomes
		for sym in ('_BG_TASK_FINISHED_RE', '_BG_TASK_ID_RE', '_BG_TASK_LOG_RE', '_infer_exit_code_from_log_text', '_uri_to_local_path', 'parse_command_outcome'):
			self.assertIs(getattr(tdd_gate, sym), getattr(outcomes, sym))
		fail_res = outcomes.parse_command_outcome('Command exited with code 1.\n\nCommand output:\nFAILED (failures=1)\n')
		self.assertTrue(fail_res['is_failure'] and (not fail_res['is_pass']))
		pass_res = outcomes.parse_command_outcome('Command exited with code 0.\n\nCommand output:\nRan 3 tests in 0.02s\nOK\n')
		self.assertTrue(pass_res['is_pass'] and (not pass_res['is_failure']))
		zero_res = outcomes.parse_command_outcome('Command exited with code 0.\n\nCommand output:\nRan 0 tests in 0.00s\nOK\n')
		self.assertTrue(zero_res['ran_zero_tests'] and (not zero_res['is_pass']))
		inv_res = outcomes.parse_command_outcome('Command exited with code 2.\n\nCommand output:\nNo module named pytest\n')
		self.assertTrue(inv_res['is_invocation_error'] and (not inv_res['is_failure']))
		with tempfile.TemporaryDirectory() as td:
			log_p = Path(td).resolve() / 'run.log'
			log_p.write_text('Ran 2 tests in 0.01s\nOK\n', encoding='utf-8')
			bg_res = outcomes.parse_command_outcome(f'Task id: bg-9\nLog: {log_p.as_uri()}\n')
			self.assertEqual('bg-9', bg_res['background_task_id'])
			self.assertTrue(bg_res['is_pass'])
	def test_ratchet_module_behavior_and_parity(self) -> None:
		from agent_tools import tdd_gate
		from agent_tools.tdd import ratchet
		for sym in ('_load_turn_ratchet_receipts', '_match_ratchet_target', '_parse_ratchet_ok_lines', 'find_ratchet_approval', 'ratchet_diff_violations', 'validate_ratchet_reason'):
			self.assertIs(getattr(tdd_gate, sym), getattr(ratchet, sym))
		self.assertFalse(ratchet.validate_ratchet_reason('too short')[0])
		self.assertFalse(ratchet.validate_ratchet_reason('Updated existing tests to match the new implementation output')[0])
		good_reason = 'User changed CLI contract in issue #169 to drop legacy flag format.'
		self.assertTrue(ratchet.validate_ratchet_reason(good_reason)[0])
		old_src = 'def test_a():\n\tassert 1 == 1\n'
		self.assertEqual([], ratchet.ratchet_diff_violations('tests/test_a.py', old_src, old_src + 'def test_b():\n\tassert 2 == 2\n'))
		self.assertTrue(ratchet.ratchet_diff_violations('tests/test_a.py', old_src, 'def test_a():\n\tpass\n'))
		self.assertTrue(ratchet.ratchet_diff_violations('tests/test_a.py', old_src, '@unittest.skip("x")\n' + old_src))
		receipt = [{'file': 'tests/test_a.py', 'reason': good_reason}]
		approval = ratchet.find_ratchet_approval('tests/test_a.py', turn_receipts=receipt)
		self.assertIsNotNone(approval)
		self.assertEqual([], ratchet.ratchet_diff_violations('tests/test_a.py', old_src, 'def test_a():\n\tpass\n', approval=approval))
	def test_substantive_module_behavior_and_parity(self) -> None:
		from agent_tools import tdd_gate
		from agent_tools.tdd import substantive
		for sym in ('is_substantive_test_content', 'source_text_assertion_issues'):
			self.assertIs(getattr(tdd_gate, sym), getattr(substantive, sym))
		self.assertFalse(substantive.is_substantive_test_content('tests/test_x.py', '# only comment\n')[0])
		self.assertFalse(substantive.is_substantive_test_content('tests/test_x.py', 'def test_stub():\n\tpass\n')[0])
		self.assertTrue(substantive.is_substantive_test_content('tests/test_x.py', 'def test_ok():\n\tassert 2 == 1 + 1\n')[0])
		self.assertTrue(substantive.is_substantive_test_content('tests/conftest.py', 'FIXTURE = 1\n')[0])
		bad_py = "from pathlib import Path\ndef test_bad():\n\tassert 'x' in Path('src/app.py').read_text(encoding='utf-8')\n"
		self.assertTrue(substantive.source_text_assertion_issues('tests/test_x.py', bad_py.splitlines(), full_content=bad_py))
		good_py = "def test_good(tmp_path):\n\tp = tmp_path / 'app.py'\n\tassert 'x' in p.read_text(encoding='utf-8')\n"
		self.assertEqual([], substantive.source_text_assertion_issues('tests/test_x.py', good_py.splitlines(), full_content=good_py))
if '__main__' == __name__:
	unittest.main()
