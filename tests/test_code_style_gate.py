# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add CODE-1 Python style ratchet linter gate in PreToolUse and pre-commit":
# https://github.com/dmitry-ai/harness/issues/243
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
def _init_repo(repo: Path) -> None:
	subprocess.run(['git', 'init'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
	subprocess.run(['git', 'config', 'user.email', 't@example.com'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
	subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
def _write_red_transcript(repo: Path) -> Path:
	tr = repo / 'transcript_full.jsonl'
	tpath = (repo / 'tests/test_bad.py').as_posix()
	rows = (
		{'step_index': 0, 'type': 'USER_INPUT', 'content': 'fix'},
		{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': tpath, 'Content': 'def test_a():\n\tassert True\n'}}]},
		{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
		{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest "{tpath}" -f'}}]},
		{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nFAIL: test_a\nRan 1 test in 0.01s\nFAILED (failures=1)\n'},
	)
	tr.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
	return tr
class CodeStyleGateTests(unittest.TestCase):
	def test_clean_code1_python_passes_all_checks(self) -> None:
		from agent_tools.code_style_gate import check_python_style_violations
		clean = "def f(x):\n\t'''Docstring ok'''\n\tif None is x:\n\t\tr = \"don't\"\n\telse:\n\t\tr = 'ok' if 0 <= x <= 10 else 'bad\\nline'\n\treturn r\ndef gen(items):\n\tfor it in items:\n\t\tif 0 == it:\n\t\t\treturn\n\t\tyield it\n"
		self.assertEqual([], check_python_style_violations('scripts/clean.py', clean))
	def test_rejects_blank_lines_spaces_multireturn_non_yoda_and_double_quotes(self) -> None:
		from agent_tools.code_style_gate import check_python_style_violations
		bad = 'def f(x):\n    if x == None:\n        return "bad"\n\n    return 1\n'
		errs = check_python_style_violations('scripts/bad.py', bad)
		joined = '\n'.join(errs)
		self.assertIn('blank line', joined.lower())
		self.assertIn('tab', joined.lower())
		self.assertIn('return', joined.lower())
		self.assertIn('yoda', joined.lower())
		self.assertIn('single quote', joined.lower())
	def test_legacy_ratchet_preserves_existing_violations_but_blocks_new_ones(self) -> None:
		from agent_tools.code_style_gate import check_python_style_violations
		legacy = 'def old(x):\n    if x == None:\n        return "old"\n\n    return 0\n'
		unchanged = legacy + 'def added(y):\n    return 1 if 2 == y else 0\n'
		self.assertEqual([], check_python_style_violations('scripts/legacy.py', unchanged, baseline_source=legacy))
		regressed = legacy + '\ndef bad_new(y):\n    if y == 2:\n        return "nope"\n    return 0\n'
		errs = check_python_style_violations('scripts/legacy.py', regressed, baseline_source=legacy)
		self.assertGreaterEqual(len(errs), 3, errs)
	def test_pre_tool_use_gate_and_pre_commit_enforce_code_style(self) -> None:
		from agent_tools import git_gate
		from agent_tools.gates import run_pre_tool_gates
		import check_rules_and_server_gate as rg
		self.assertTrue(callable(rg.check_code_style_gate))
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			_init_repo(repo)
			bad_p = repo / 'scripts/bad.py'
			bad_p.parent.mkdir(parents=True, exist_ok=True)
			bad_src = 'def demo(v):\n\tif v == 1:\n\t\treturn "x"\n\treturn "y"\n'
			tr = _write_red_transcript(repo)
			dec = run_pre_tool_gates('write_file', {'Path': str(bad_p), 'Content': bad_src}, {'cwd': str(repo), 'transcriptPath': str(tr)})
			self.assertEqual('deny', dec['decision'])
			self.assertIn('CODE-STYLE-GATE', dec['reason'])
			good_src = '# https://github.com/o/r/issues/1\ndef demo(v):\n\treturn 1 if 1 == v else 0\n'
			self.assertIsNone(rg.check_code_style_gate('write_file', {'Path': str(bad_p), 'Content': good_src}, {'cwd': str(repo)}))
			bad_p.write_text('# https://github.com/o/r/issues/1\n' + bad_src, encoding='utf-8')
			(repo / 'tests').mkdir(exist_ok=True)
			tfile = repo / 'tests/test_bad.py'
			tfile.write_text('# https://github.com/o/r/issues/1\nimport unittest\nclass T(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
			subprocess.run(['git', 'add', 'scripts/bad.py', 'tests/test_bad.py'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
			self.assertNotEqual(0, git_gate.GitRepoGate(repo).run_hook('pre-commit', agent_context=True))
			bad_p.write_text(good_src, encoding='utf-8')
			subprocess.run(['git', 'add', 'scripts/bad.py'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
			self.assertEqual(0, git_gate.GitRepoGate(repo).run_hook('pre-commit', agent_context=True))
if '__main__' == __name__:
	unittest.main()