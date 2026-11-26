# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
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
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.tdd import enforcement, evaluator, exemption
from agent_tools.tdd.events import build_command_tdd_event, build_file_write_tdd_event
from agent_tools.tdd.mechanical import find_matching_mechanical_recipes, is_git_file_mechanical_exempt
# @used-by :func:`_init_repo()`
# @used-by :func:`_seed_committed_files()`
# @used-by :meth:`TddFastPathTests.test_evaluator_memoizes_exemption_and_allows_exempt_only_edits()`
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], check=True, stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
# @used-by :meth:`TddFastPathTests.test_evaluator_lazy_exemption_and_full_green_edge_cases()`
# @used-by :meth:`TddFastPathTests.test_evaluator_memoizes_exemption_and_allows_exempt_only_edits()`
# @used-by :meth:`TddFastPathTests.test_mechanical_exemption_spawns_zero_git_without_recipes()`
# @used-by :meth:`TddFastPathTests.test_pre_tool_use_short_circuits_non_code_and_non_writing_commands()`
def _init_repo(repo: Path) -> None:
	repo.mkdir(parents=True, exist_ok=True)
	_git(repo, 'init', '-b', 'main')
	cfg = repo / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + '[user]\n\temail = test@example.com\n\tname = Test\n', encoding='utf-8')
# @used-by :meth:`TddFastPathTests.test_evaluator_lazy_exemption_and_full_green_edge_cases()`
# @used-by :meth:`TddFastPathTests.test_evaluator_memoizes_exemption_and_allows_exempt_only_edits()`
# @used-by :meth:`TddFastPathTests.test_mechanical_exemption_spawns_zero_git_without_recipes()`
# @used-by :meth:`TddFastPathTests.test_pre_tool_use_short_circuits_non_code_and_non_writing_commands()`
def _seed_committed_files(repo: Path, count: int) -> list[Path]:
	files: list[Path] = []
	for idx in range(count):
		fp = repo / f'src/mod_{idx:02d}.py'
		fp.parent.mkdir(parents=True, exist_ok=True)
		fp.write_text(f'# header\nVAL = {idx}\n', encoding='utf-8')
		files.append(fp)
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'seed')
	return files
# @used-by :meth:`TddFastPathTests.test_pre_tool_use_short_circuits_non_code_and_non_writing_commands()`
def _write_multi_commit_transcript(tx: Path, repo: Path, prod_files: list[Path]) -> None:
	test_f = repo / 'tests/test_app.py'
	rows: list[dict] = [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Implement modules'}]
	step = 1
	rows.append({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(test_f))}}]})
	rows.append({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Created file.'})
	rows.append({'step_index': step + 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'python -m unittest "{test_f}"')}}]})
	rows.append({'step_index': step + 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nFAIL\n'})
	step += 4
	for fp in prod_files:
		rows.append({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(fp))}}]})
		rows.append({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Updated file.'})
		step += 2
	rows.append({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'git -C "{repo}" commit -m https://github.com/dmitry-ai/harness/issues/250')}}]})
	rows.append({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n\nCommand output:\n[main 1234567] ok\n'})
	tx.write_text(''.join((json.dumps(row, ensure_ascii=False) + '\n' for row in rows)), encoding='utf-8')
# 2026-11-25
# "Short-circuit non-code PreToolUse TDD checks and lazily memoize exemptions":
# https://github.com/dmitry-ai/harness/issues/250
class TddFastPathTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_evaluator_lazy_exemption_and_full_green_edge_cases(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve() / 'repo'
			_init_repo(repo)
			prod_files = _seed_committed_files(repo, 6)
			test_f = repo / 'tests/test_mod.py'
			events = [
				build_file_write_tdd_event(1, test_f, cwd=repo),
				build_command_tdd_event(2, f'python -m unittest "{test_f}"', ['Command exited with code 1.\nFAIL\n'], cwd=repo),
				*(build_file_write_tdd_event(3 + idx, fp, cwd=repo) for idx, fp in enumerate(prod_files)),
			]
			with patch.object(subprocess, 'run', wraps=subprocess.run) as spy:
				res_pre = evaluator.evaluate_tdd_events(events, require_final_full_green=False, project_root=repo)
				self.assertTrue(res_pre['verified'], res_pre)
				self.assertEqual(0, spy.call_count)
			full_pass = build_command_tdd_event(20, f'python harness.py run-tests "{repo / "tests"}"', ['Command exited with code 0.\nOK\n'], cwd=repo)
			with patch.object(subprocess, 'run', wraps=subprocess.run) as spy:
				res_green = evaluator.evaluate_tdd_events([*events, full_pass], require_final_full_green=True, project_root=repo)
				self.assertTrue(res_green['verified'], res_green)
				self.assertEqual(0, spy.call_count)
			res_missing_full = evaluator.evaluate_tdd_events(events, require_final_full_green=True, project_root=repo)
			self.assertFalse(res_missing_full['verified'], res_missing_full)
			self.assertTrue(any(('TDD-FULL-GATE' in v for v in res_missing_full['violations'])))
	# @used-by :mod:`unittest`
	def test_evaluator_memoizes_exemption_and_allows_exempt_only_edits(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve() / 'repo'
			_init_repo(repo)
			prod_f = _seed_committed_files(repo, 1)[0]
			prod_f.write_text('# updated comment\nVAL = 0\n', encoding='utf-8')
			test_f = repo / 'tests/test_mod.py'
			dup_idle_events = [build_file_write_tdd_event(1, prod_f, cwd=repo), build_file_write_tdd_event(2, prod_f, cwd=repo), build_file_write_tdd_event(3, prod_f, cwd=repo)]
			with patch.object(evaluator, 'is_write_event_exempt', wraps=exemption.is_write_event_exempt) as spy:
				res_idle = evaluator.evaluate_tdd_events(dup_idle_events, require_final_full_green=True, project_root=repo)
				self.assertTrue(res_idle['verified'], res_idle)
				self.assertEqual(1, spy.call_count)
			red_exempt_events = [
				build_file_write_tdd_event(1, test_f, cwd=repo),
				build_command_tdd_event(2, f'python -m unittest "{test_f}"', ['Command exited with code 1.\nFAIL\n'], cwd=repo),
				build_file_write_tdd_event(3, prod_f, cwd=repo),
			]
			res_red_exempt = evaluator.evaluate_tdd_events(red_exempt_events, require_final_full_green=True, project_root=repo)
			self.assertTrue(res_red_exempt['verified'], res_red_exempt)
			real_f = repo / 'src/real.py'
			real_f.write_text('X = 1\n', encoding='utf-8')
			_git(repo, 'add', 'src/real.py')
			_git(repo, 'commit', '--no-verify', '-m', 'add real')
			real_f.write_text('X = 2\n', encoding='utf-8')
			post_green_comment = [
				build_file_write_tdd_event(1, test_f, cwd=repo),
				build_command_tdd_event(2, f'python -m unittest "{test_f}"', ['Command exited with code 1.\nFAIL\n'], cwd=repo),
				build_file_write_tdd_event(3, real_f, cwd=repo),
				build_command_tdd_event(4, f'python harness.py run-tests "{repo / "tests"}"', ['Command exited with code 0.\nOK\n'], cwd=repo),
				build_file_write_tdd_event(5, prod_f, cwd=repo),
			]
			res_post_green = evaluator.evaluate_tdd_events(post_green_comment, require_final_full_green=True, project_root=repo)
			self.assertTrue(res_post_green['verified'], res_post_green)
	# @used-by :mod:`unittest`
	def test_mechanical_exemption_spawns_zero_git_without_recipes(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve() / 'repo'
			_init_repo(repo)
			_seed_committed_files(repo, 2)
			with patch.object(subprocess, 'run', wraps=subprocess.run) as spy:
				self.assertEqual([], find_matching_mechanical_recipes(repo, project_root=repo))
				self.assertFalse(is_git_file_mechanical_exempt(repo, 'src/mod_00.py', project_root=repo))
				self.assertEqual(0, spy.call_count)
	# @used-by :mod:`unittest`
	def test_pre_tool_use_short_circuits_non_code_and_non_writing_commands(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			repo = base / 'repo'
			_init_repo(repo)
			prod_files = _seed_committed_files(repo, 6)
			tx = base / 'transcript_full.jsonl'
			_write_multi_commit_transcript(tx, repo, prod_files)
			payload = {'cwd': str(repo), 'transcriptPath': str(tx)}
			with patch.object(enforcement, 'extract_antigravity_tdd_events', side_effect=AssertionError('must not parse transcript')), patch.object(subprocess, 'run', wraps=subprocess.run) as spy:
				self.assertIsNone(enforcement.evaluate_pre_tool_use_tdd('write_file', {'Path': str(repo / '\ua616/data/scratch/answer-abc.md'), 'Content': 'Answer text\n'}, payload))
				self.assertIsNone(enforcement.evaluate_pre_tool_use_tdd('edit_file', {'Path': str(repo / 'README.md'), 'Target': 'a', 'Replacement': 'b'}, payload))
				self.assertIsNone(enforcement.evaluate_pre_tool_use_tdd('run_command', {'CommandLine': 'python scripts/harness.py answer-prepare . --response-file x.md'}, payload))
				self.assertIsNone(enforcement.evaluate_pre_tool_use_tdd('run_command', {'CommandLine': 'git --no-optional-locks status'}, payload))
				self.assertEqual(0, spy.call_count)
if '__main__' == __name__:
	unittest.main()
