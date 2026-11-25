# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add deterministic PreToolUse subprocess budget and scaling regression tests":
# https://github.com/dmitry-ai/harness/issues/253
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import subprocess
import sys
import tempfile
import time
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.tdd.mechanical import is_git_file_mechanical_exempt
import check_rules_and_server_gate as rg
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
def _seed_multicommit_transcript(base: Path, file_count: int) -> tuple[Path, Path]:
	repo = base / f'repo_{file_count}'
	repo.mkdir(parents=True)
	_git(repo, 'init', '-b', 'main')
	cfg = repo / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + '[user]\n\temail = perf@example.com\n\tname = Perf\n', encoding='utf-8')
	test_f = repo / 'tests/test_suite.py'
	test_f.parent.mkdir(parents=True, exist_ok=True)
	test_f.write_text('import unittest\nclass T(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
	rows: list[dict] = [{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Multi-commit turn'}]
	step = 1
	batch = max(1, (file_count + 2) // 3)
	for c_idx in range(3):
		s_i, e_i = (c_idx * batch, min(file_count, (c_idx + 1) * batch))
		if s_i >= e_i:
			break
		rows.append({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(test_f))}}]})
		rows.append({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Updated file.'})
		rows.append({'step_index': step + 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'python -m unittest "{test_f}"')}}]})
		rows.append({'step_index': step + 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\nFAIL\n'})
		step += 4
		for idx in range(s_i, e_i):
			fp = repo / f'src/mod_{idx:02d}.py'
			fp.parent.mkdir(parents=True, exist_ok=True)
			fp.write_text(f'VALUE = {idx}\n', encoding='utf-8')
			rows.append({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(fp))}}]})
			rows.append({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Created file.'})
			step += 2
		_git(repo, 'add', '.')
		_git(repo, 'commit', '--no-verify', '-m', f'commit-{c_idx}')
		rows.append({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'git -C "{repo}" commit -m commit-{c_idx}')}}]})
		rows.append({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n[main 1234567] ok\n'})
		step += 2
	rows.append({'step_index': step, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': json.dumps(str(test_f))}}]})
	rows.append({'step_index': step + 1, 'type': 'GENERIC', 'content': 'Updated file.'})
	rows.append({'step_index': step + 2, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': json.dumps(f'python -m unittest "{test_f}"')}}]})
	rows.append({'step_index': step + 3, 'type': 'GENERIC', 'content': 'Command exited with code 1.\nFAIL\n'})
	tx = base / f'tx_{file_count}.jsonl'
	tx.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
	return (repo, tx)
class TddPreToolUsePerfTests(unittest.TestCase):
	def test_code_and_test_writes_stay_o1_subprocesses_across_25_committed_files(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			repo5, tx5 = _seed_multicommit_transcript(base, 5)
			repo25, tx25 = _seed_multicommit_transcript(base, 25)
			rg._evaluate_payload({'cwd': str(repo5), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo5 / 'warm.md'), 'Content': 'x\n'}}})
			test_body = 'import unittest\nclass T(unittest.TestCase):\n\tdef test_new(self):\n\t\tself.assertEqual(2, 1 + 1)\n'
			with patch.object(subprocess, 'run', wraps=subprocess.run) as spy5:
				dec5 = rg._evaluate_payload({'cwd': str(repo5), 'transcriptPath': str(tx5), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo5 / 'src/prod_next.py'), 'Content': 'X = 1\n'}}})
				calls5 = spy5.call_count
			self.assertEqual('allow', dec5['decision'], dec5)
			self.assertLessEqual(calls5, 2)
			with patch.object(subprocess, 'run', wraps=subprocess.run) as spy25_test:
				t0 = time.perf_counter()
				dec_t = rg._evaluate_payload({'cwd': str(repo25), 'transcriptPath': str(tx25), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo25 / 'tests/test_new.py'), 'Content': test_body}}})
				dt_t = time.perf_counter() - t0
				calls_t = spy25_test.call_count
			self.assertEqual('allow', dec_t['decision'], dec_t)
			self.assertLessEqual(calls_t, 2)
			self.assertLess(dt_t, 1.0)
			with patch.object(subprocess, 'run', wraps=subprocess.run) as spy25_prod:
				t1 = time.perf_counter()
				dec_p = rg._evaluate_payload({'cwd': str(repo25), 'transcriptPath': str(tx25), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo25 / 'src/prod_next.py'), 'Content': 'X = 1\n'}}})
				dt_p = time.perf_counter() - t1
				calls_p = spy25_prod.call_count
			self.assertEqual('allow', dec_p['decision'], dec_p)
			self.assertLessEqual(calls_p, 2)
			self.assertEqual(calls5, calls_p)
			self.assertLess(dt_p, 1.0)
	def test_mechanical_exemption_spawns_zero_subprocesses_without_recipes(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo, _ = _seed_multicommit_transcript(Path(td).resolve(), 5)
			with patch.object(subprocess, 'run', wraps=subprocess.run) as spy:
				self.assertFalse(is_git_file_mechanical_exempt(repo, 'src/mod_00.py', project_root=repo))
				self.assertEqual(0, spy.call_count)
	def test_non_code_write_and_non_writing_command_spawn_zero_subprocesses(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo, tx = _seed_multicommit_transcript(Path(td).resolve(), 25)
			rg._evaluate_payload({'cwd': str(repo), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo / 'warm.md'), 'Content': 'x\n'}}})
			with patch.object(subprocess, 'run', wraps=subprocess.run) as spy_md:
				t0 = time.perf_counter()
				dec_md = rg._evaluate_payload({'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'write_file', 'args': {'Path': str(repo / '\ua616/data/scratch/answer.md'), 'Content': 'Final answer.\n'}}})
				dt_md = time.perf_counter() - t0
				self.assertEqual('allow', dec_md['decision'], dec_md)
				self.assertEqual(0, spy_md.call_count)
				self.assertLess(dt_md, 0.5)
			with patch.object(subprocess, 'run', wraps=subprocess.run) as spy_cmd:
				t1 = time.perf_counter()
				dec_cmd = rg._evaluate_payload({'cwd': str(repo), 'transcriptPath': str(tx), 'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'python scripts/harness.py answer-prepare . --response-file x.md --consume-input'}}})
				dt_cmd = time.perf_counter() - t1
				self.assertEqual('allow', dec_cmd['decision'], dec_cmd)
				self.assertEqual(0, spy_cmd.call_count)
				self.assertLess(dt_cmd, 0.5)
if '__main__' == __name__:
	unittest.main()
