# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
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
	subprocess.run(['git', 'init', '-b', 'main'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
	subprocess.run(['git', 'config', 'user.email', 't@example.com'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
	subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
def _seed_commit(repo: Path, rel: str, text: str) -> None:
	p = repo / rel
	p.parent.mkdir(parents=True, exist_ok=True)
	p.write_text(text, encoding='utf-8')
	subprocess.run(['git', 'add', rel], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
	subprocess.run(['git', 'commit', '--no-verify', '-m', 'seed'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
def _write_red_transcript(repo: Path, test_rel: str) -> Path:
	tr = repo / 'transcript_full.jsonl'
	tpath = (repo / test_rel).as_posix()
	rows = (
		{'step_index': 0, 'type': 'USER_INPUT', 'content': 'fix'},
		{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': tpath, 'Content': 'def test_a():\n\tassert True\n'}}]},
		{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
		{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': f'python -m unittest "{tpath}" -f'}}]},
		{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n\nCommand output:\nFAIL: test_a\nRan 1 test in 0.01s\nFAILED (failures=1)\n'},
	)
	tr.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
	return tr
# 2026-11-26
# "Add PreToolUse and pre-commit gate for issue-comment placement":
# https://github.com/dmitry-ai/harness/issues/273
class IssueCommentGateTests(unittest.TestCase):
	def test_allows_block_adjacent_function_header_trailing_and_new_file_comments(self) -> None:
		from agent_tools.issue_comment_gate import check_issue_comment_violations
		new_py = '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# "Init": https://github.com/o/r/issues/1\nimport os\ndef f(x):\n\treturn x\n'
		self.assertEqual([], check_issue_comment_violations('scripts/m.py', new_py, baseline_source=None))
		base_py = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport os\nimport sys\ndef a():\n\treturn 1\ndef b(x):\n\ty = x + 1\n\treturn y\n'
		block_py = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport os\nimport sys\ndef a():\n\treturn 1\ndef b(x):\n\t# 2026-11-26 "Fix offset": https://github.com/o/r/issues/2\n\ty = x + 2\n\treturn y\n'
		self.assertEqual([], check_issue_comment_violations('scripts/m.py', block_py, baseline_source=base_py))
		fn_py = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport os\nimport sys\ndef a():\n\treturn 1\n# 2026-11-26 "Update b": https://github.com/o/r/issues/2\ndef b(x):\n\ty = x + 2\n\treturn y\n'
		self.assertEqual([], check_issue_comment_violations('scripts/m.py', fn_py, baseline_source=base_py))
		trail_py = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport os\nimport re # 2026-11-26 "Use re": https://github.com/o/r/issues/2\nimport sys\ndef a():\n\treturn 1\ndef b(x):\n\ty = x + 1\n\treturn y\n'
		self.assertEqual([], check_issue_comment_violations('scripts/m.py', trail_py, baseline_source=base_py))
	def test_rejects_duplicate_and_out_of_header_author_lines(self) -> None:
		from agent_tools.issue_comment_gate import check_issue_comment_violations
		dup_new = '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# https://github.com/o/r/issues/1\nx = 1\n'
		errs = check_issue_comment_violations('scripts/m.py', dup_new, baseline_source=None)
		self.assertTrue(any(('DUPLICATE_AUTHOR_HEADER' in e for e in errs)), errs)
		base = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\ndef f():\n\treturn 1\n'
		body_author = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# 2026-11-26 "Fix": https://github.com/o/r/issues/2\ndef f():\n\t# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n\treturn 2\n'
		errs2 = check_issue_comment_violations('scripts/m.py', body_author, baseline_source=base)
		self.assertTrue(any(('DUPLICATE_AUTHOR_HEADER' in e or 'AUTHOR_OUTSIDE_HEADER' in e for e in errs2)), errs2)
	def test_rejects_header_dumped_and_misplaced_issue_comments_across_languages(self) -> None:
		from agent_tools.issue_comment_gate import check_issue_comment_violations
		base_py = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport os\nimport sys\ndef a():\n\treturn 1\ndef b(x):\n\treturn x + 1\n'
		dumped_py = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# 2026-11-26 "Fix b": https://github.com/o/r/issues/2\nimport os\nimport sys\ndef a():\n\treturn 1\ndef b(x):\n\treturn x + 2\n'
		errs = check_issue_comment_violations('scripts/m.py', dumped_py, baseline_source=base_py)
		self.assertTrue(any(('HEADER_DUMPED_ISSUE_COMMENT' in e for e in errs)), errs)
		wrong_fn_py = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport os\nimport sys\n# 2026-11-26 "Fix b": https://github.com/o/r/issues/2\ndef a():\n\treturn 1\ndef b(x):\n\treturn x + 2\n'
		errs_wrong = check_issue_comment_violations('scripts/m.py', wrong_fn_py, baseline_source=base_py)
		self.assertTrue(any(('MISPLACED_ISSUE_COMMENT' in e for e in errs_wrong)), errs_wrong)
		base_js = '// 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nconst fs = require(\'node:fs\');\nconst a = () => 1;\nconst b = x => {\n\treturn x + 1;\n};\n'
		dumped_js = '// 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n// 2026-11-26 "Fix b": https://github.com/o/r/issues/3\nconst fs = require(\'node:fs\');\nconst a = () => 1;\nconst b = x => {\n\treturn x + 2;\n};\n'
		errs_js = check_issue_comment_violations('app/m.js', dumped_js, baseline_source=base_js)
		self.assertTrue(any(('HEADER_DUMPED_ISSUE_COMMENT' in e for e in errs_js)), errs_js)
		good_js = '// 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nconst fs = require(\'node:fs\');\nconst a = () => 1;\n// 2026-11-26 "Fix b": https://github.com/o/r/issues/3\nconst b = x => {\n\treturn x + 2;\n};\n'
		self.assertEqual([], check_issue_comment_violations('app/m.js', good_js, baseline_source=base_js))
	def test_pre_tool_use_and_pre_commit_enforce_issue_comment_gate(self) -> None:
		from agent_tools import git_gate
		from agent_tools.gates import run_pre_tool_gates
		import check_rules_and_server_gate as rg
		self.assertTrue(callable(rg.check_issue_comment_gate))
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			_init_repo(repo)
			base_src = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport os\ndef a():\n\treturn 1\ndef b(v):\n\treturn v + 1\n'
			_seed_commit(repo, 'scripts/mod.py', base_src)
			_seed_commit(repo, 'tests/test_mod.py', '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport unittest\nclass T(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(1, 1)\n')
			dumped_src = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# 2026-11-26 "Fix b": https://github.com/o/r/issues/9\nimport os\ndef a():\n\treturn 1\ndef b(v):\n\treturn v + 2\n'
			good_src = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport os\ndef a():\n\treturn 1\n# 2026-11-26 "Fix b": https://github.com/o/r/issues/9\ndef b(v):\n\treturn v + 2\n'
			tr = _write_red_transcript(repo, 'tests/test_mod.py')
			dec = run_pre_tool_gates('write_file', {'Path': str(repo / 'scripts/mod.py'), 'Content': dumped_src}, {'cwd': str(repo), 'transcriptPath': str(tr)})
			self.assertEqual('deny', dec['decision'])
			self.assertIn('ISSUE-COMMENT-GATE', dec['reason'])
			self.assertIsNone(rg.check_issue_comment_gate('write_file', {'Path': str(repo / 'scripts/mod.py'), 'Content': good_src}, {'cwd': str(repo)}))
			(repo / 'scripts/mod.py').write_text(dumped_src, encoding='utf-8')
			(repo / 'tests/test_mod.py').write_text('# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport unittest\nclass T(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(1, 1)\n\t# 2026-11-26 "Fix b": https://github.com/o/r/issues/9\n\tdef test_b(self):\n\t\tself.assertEqual(3, 3)\n', encoding='utf-8')
			subprocess.run(['git', 'add', 'scripts/mod.py', 'tests/test_mod.py'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
			self.assertNotEqual(0, git_gate.GitRepoGate(repo).run_hook('pre-commit', agent_context=True))
			(repo / 'scripts/mod.py').write_text(good_src, encoding='utf-8')
			subprocess.run(['git', 'add', 'scripts/mod.py'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
			self.assertEqual(0, git_gate.GitRepoGate(repo).run_hook('pre-commit', agent_context=True))
	def test_supports_xml_css_and_rejects_coarse_class_header_for_single_method_edit(self) -> None:
		from agent_tools.issue_comment_gate import check_issue_comment_violations
		base_xml = "<?xml version='1.0'?>\n<!-- 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk -->\n<root>\n\t<a/>\n\t<b/>\n</root>\n"
		good_xml = "<?xml version='1.0'?>\n<!-- 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk -->\n<root>\n\t<a/>\n<!-- 2026-11-26 https://github.com/o/r/issues/4 -->\n\t<b x='1'/>\n</root>\n"
		self.assertEqual([], check_issue_comment_violations('etc/cfg.xml', good_xml, baseline_source=base_xml))
		base_cls = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport os\nclass Box:\n\tdef a(self):\n\t\treturn 1\n\tdef b(self):\n\t\treturn 2\n'
		coarse_cls = '# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport os\n# 2026-11-26 https://github.com/o/r/issues/5\nclass Box:\n\tdef a(self):\n\t\treturn 1\n\tdef b(self):\n\t\treturn 3\n'
		errs = check_issue_comment_violations('scripts/box.py', coarse_cls, baseline_source=base_cls)
		self.assertTrue(any(('MISPLACED_ISSUE_COMMENT' in e for e in errs)), errs)
		base_css = '/* 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk */\n.a { color: red; }\n.b { color: blue; }\n'
		good_css = '/* 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk */\n.a { color: red; }\n/* 2026-11-26 https://github.com/o/r/issues/6 */\n.b { color: green; }\n'
		self.assertEqual([], check_issue_comment_violations('styles/s.css', good_css, baseline_source=base_css))
if '__main__' == __name__:
	unittest.main()
