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
def _seed(repo: Path, rel: str, text: str) -> None:
	p = repo / rel
	p.parent.mkdir(parents=True, exist_ok=True)
	p.write_text(text, encoding='utf-8')
	subprocess.run(['git', 'add', rel], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
	subprocess.run(['git', 'commit', '--no-verify', '-m', 'seed'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
# 2026-11-26
# "Fix comment-only diff and denied-write gate false positives":
# https://github.com/dmitry-ai/harness/issues/276
class CommentExemptionAndDeniedWritesTests(unittest.TestCase):
	def test_issue_comment_gate_skips_body_misalignment_on_comment_only_diff(self) -> None:
		from agent_tools import native_profiles
		from agent_tools.issue_comment_gate import check_issue_comment_violations
		base_css = '/* 2026-10-12 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n\thttps://github.com/o/r/issues/4 */\n.a {\n\tcolor: red;\n}\n.b {\n\tcolor: blue;\n}\n'
		cur_css = '/* 2026-10-12 Dmitrii Fediuk https://github.com/dmitrii-fediuk */\n/* 2026-10-20 https://github.com/o/r/issues/12 */\n.a {\n\tcolor: red;\n}\n/* 2026-10-12 https://github.com/o/r/issues/4 */\n/* 2026-11-01 https://github.com/o/r/issues/24 */\n.b {\n\tcolor: blue;\n}\n'
		self.assertEqual([], check_issue_comment_violations('CSS/folders.css', cur_css, baseline_source=base_css))
		base_py = '# 2026-10-12 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nimport os\ndef f():\n\treturn 1\n'
		bad_py = '# 2026-10-12 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# 2026-11-26 https://github.com/o/r/issues/99\nimport os\ndef f():\n\treturn 1\n'
		self.assertTrue(any(('HEADER_DUMPED_ISSUE_COMMENT' in e for e in check_issue_comment_violations('a.py', bad_py, baseline_source=base_py))))
		af_path = WT_ROOT / 'agents/af-worker.md'
		self.assertEqual(native_profiles.shared_native_outputs(WT_ROOT)[af_path], af_path.read_text(encoding='utf-8'))
	def test_tdd_exempts_comment_only_test_edits_and_recognizes_java_assertions(self) -> None:
		from agent_tools.tdd.enforcement import evaluate_pre_tool_use_tdd, verify_staged_tdd_diff
		from agent_tools.tdd.substantive import is_substantive_test_content
		java_test = '// 2026-11-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nclass SampleTest {\n\tstatic void run() {\n\t\tA.assertEquals("ok", 1, 1);\n\t}\n}\n'
		self.assertEqual((True, None), is_substantive_test_content('src/test/java/SampleTest.java', java_test))
		java_helper = '// 2026-11-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk\npublic final class Assertions {\n\tpublic void assertTrue(String m, boolean ok) {\n\t\tif (!ok) throw new AssertionError(m);\n\t}\n}\n'
		self.assertEqual((True, None), is_substantive_test_content('src/test/java/df/idea/support/Assertions.java', java_helper))
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			_init_repo(repo)
			orig = '// 2026-11-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n// https://github.com/o/r/issues/1\nclass PlainHelper {\n\tstatic int x() { return 1; }\n}\n'
			_seed(repo, 'src/test/java/PlainHelper.java', orig)
			edited = '// 2026-11-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n// 2026-11-22 "Init": https://github.com/o/r/issues/1\nclass PlainHelper {\n\tstatic int x() { return 1; }\n}\n'
			self.assertIsNone(evaluate_pre_tool_use_tdd('write_file', {'Path': str(repo / 'src/test/java/PlainHelper.java'), 'Content': edited}, {'cwd': str(repo)}))
			(repo / 'src/test/java/PlainHelper.java').write_text(edited, encoding='utf-8')
			subprocess.run(['git', 'add', 'src/test/java/PlainHelper.java'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
			self.assertEqual([], verify_staged_tdd_diff(repo, ['src/test/java/PlainHelper.java'], use_index=True))
	def test_issue_first_skips_denied_writes_and_reads_background_task_issue_actions(self) -> None:
		from agent_tools.issue_first_gate import evaluate_issue_first_events, extract_antigravity_issue_first_events
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = root / 'code'
			repo.mkdir()
			_init_repo(repo)
			subprocess.run(['git', 'remote', 'add', 'origin', 'https://github.com/o/r.git'], cwd=str(repo), stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=True)
			tr = root / 'transcript_full.jsonl'
			mod_p = (repo / 'tests/test_a.py').as_posix()
			bg_msg = 'Task id "t1" finished with result:\nCommand exited with code 0.\n\nCommand output:\n{"ok": true, "action": "create", "repo": "o/r", "number": 7, "state": "open"}\n'
			rows = (
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'fix'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': '$cli = "scripts/df_github_issue.py"\npython $cli create --repo o/r'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Tool is running as a background task with task id: t1'},
				{'step_index': 3, 'type': 'SYSTEM_MESSAGE', 'content': bg_msg},
				{'step_index': 4, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'edit_file', 'args': {'Path': mod_p, 'Target': 'a', 'Replacement': 'b'}}]},
				{'step_index': 5, 'type': 'GENERIC', 'content': 'Encountered error in tool execution: tool call denied by pre-tool hook: REJECTED'},
				{'step_index': 6, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'edit_file', 'args': {'Path': mod_p, 'Target': 'a', 'Replacement': 'b'}}]},
				{'step_index': 7, 'type': 'GENERIC', 'content': 'Made 1 replacement.'},
			)
			tr.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			events, reqs = extract_antigravity_issue_first_events(tr, cwd=root)
			res = evaluate_issue_first_events(events, requests=reqs, project_root=root)
			self.assertTrue(res['verified'], res)
			self.assertEqual([7], res['repos']['o/r']['established_parents'])
			self.assertEqual(1, res['repos']['o/r']['code_write_count'])
if '__main__' == __name__:
	unittest.main()
