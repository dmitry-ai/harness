# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26
# "Enforce cross-reference compliance in PreToolUse and Git gates":
# https://github.com/dmitry-ai/harness/issues/306
_A_UNUSED = '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# https://github.com/o/r/issues/1\n# @used-by unused\ndef helper() -> int:\n\treturn 1\n'
_B_DROPPED = '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# https://github.com/o/r/issues/2\n# @used-by :meth:`test_ab.AbTests.test_run()`\ndef run() -> int:\n\treturn 2\n'
# @used-by :func:`_init_repo()`
# @used-by :func:`_seed_commit()`
# @used-by :meth:`XrefGateTests._assert_staged_js_java_and_legacy()`
# @used-by :meth:`XrefGateTests.test_pre_commit_blocks_stale_cross_file_xref_and_passes_after_sync()`
# @used-by :meth:`XrefGateTests.test_worktree_land_blocks_stale_xref_and_passes_when_synced()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True)
	return (proc.stdout or '').strip()
# @used-by :meth:`XrefGateTests._assert_staged_js_java_and_legacy()`
# @used-by :meth:`XrefGateTests.test_pre_commit_blocks_stale_cross_file_xref_and_passes_after_sync()`
# @used-by :meth:`XrefGateTests.test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax()`
# @used-by :meth:`XrefGateTests.test_worktree_land_blocks_stale_xref_and_passes_when_synced()`
def _init_repo(repo: Path) -> Path:
	repo.mkdir(parents=True, exist_ok=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 't@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	return repo
# @used-by :meth:`XrefGateTests.test_pre_commit_blocks_stale_cross_file_xref_and_passes_after_sync()`
# @used-by :meth:`XrefGateTests.test_worktree_land_blocks_stale_xref_and_passes_when_synced()`
def _seed_annotated_ab(repo: Path) -> None:
	a_src = '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# https://github.com/o/r/issues/1\n# @used-by :func:`b.run()`\ndef helper() -> int:\n\treturn 1\n'
	b_src = '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# https://github.com/o/r/issues/1\nfrom a import helper\n# @used-by :meth:`test_ab.AbTests.test_run()`\ndef run() -> int:\n\treturn helper()\n'
	t_src = '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# https://github.com/o/r/issues/1\nimport unittest\nfrom b import run\nclass AbTests(unittest.TestCase):\n\t# @used-by :mod:`unittest`\n\tdef test_run(self) -> None:\n\t\tself.assertEqual(1, run())\n'
	_seed_commit(repo, {'scripts/a.py': a_src, 'scripts/b.py': b_src, 'tests/test_ab.py': t_src})
# @used-by :func:`_seed_annotated_ab()`
# @used-by :meth:`XrefGateTests._assert_staged_js_java_and_legacy()`
# @used-by :meth:`XrefGateTests.test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax()`
# @used-by :meth:`XrefGateTests.test_worktree_land_blocks_stale_xref_and_passes_when_synced()`
def _seed_commit(repo: Path, files: dict[str, str], message: str='seed') -> None:
	for rel, text in files.items():
		fp = repo / rel
		fp.parent.mkdir(parents=True, exist_ok=True)
		fp.write_text(text, encoding='utf-8', newline='\n')
	_git(repo, 'add', *sorted(files))
	_git(repo, 'commit', '--no-verify', '-m', message)
# @used-by :meth:`XrefGateTests.test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax()`
def _write_red_transcript(repo: Path) -> Path:
	tr = repo / 'transcript_full.jsonl'
	tpath = (repo / 'tests/test_demo.py').as_posix()
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
# "Enforce cross-reference compliance in PreToolUse and Git gates":
# https://github.com/dmitry-ai/harness/issues/306
class XrefGateTests(unittest.TestCase):
	# @used-by :meth:`XrefGateTests.test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax()`
	def _assert_pre_tool_allows_valid_and_legacy_ratchet(self, repo: Path, tr: Path) -> None:
		from agent_tools.gates import run_pre_tool_gates
		import check_rules_and_server_gate as rg
		pay = {'cwd': str(repo), 'transcriptPath': str(tr)}
		valid_cases = (
			('scripts/ok.py', '# @used-by unused\ndef ok() -> int:\n\treturn 1\n'),
			('app/ok.js', '/**\n * @used-by unused\n */\nfunction ok() {\n\treturn 1;\n}\n'),
			('src/Ok.java', 'public class Ok {\n\t/**\n\t * - @used-by unused\n\t */\n\tpublic int ok() {\n\t\treturn 1;\n\t}\n}\n'),
		)
		for rel, src in valid_cases:
			self.assertIsNone(rg.check_xref_gate('write_file', {'Path': str(repo / rel), 'Content': src}, pay), rel)
			self.assertEqual('allow', run_pre_tool_gates('write_file', {'Path': str(repo / rel), 'Content': src}, pay)['decision'], rel)
		legacy_p = repo / 'scripts/legacy.py'
		mod_ok = run_pre_tool_gates('edit_file', {'Path': str(legacy_p), 'Target': 'return 1', 'Replacement': 'return 2'}, pay)
		self.assertEqual('allow', mod_ok['decision'], mod_ok)
		add_bad = run_pre_tool_gates('edit_file', {'Path': str(legacy_p), 'Target': 'return 1\n', 'Replacement': 'return 1\ndef brand_new() -> int:\n\treturn 3\n'}, pay)
		self.assertEqual('deny', add_bad['decision'], add_bad)
		self.assertIn('XREF-GATE', add_bad['reason'])
		syn_bad = run_pre_tool_gates('write_file', {'Path': str(legacy_p), 'Content': '# @used-by :meth:`self.x()`\ndef old_fn() -> int:\n\treturn 1\n'}, pay)
		self.assertEqual('deny', syn_bad['decision'], syn_bad)
		self.assertIn('XREF-GATE', syn_bad['reason'])
	# @used-by :meth:`XrefGateTests.test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax()`
	def _assert_pre_tool_denies_bad_samples(self, repo: Path, tr: Path) -> None:
		from agent_tools.gates import run_pre_tool_gates
		pay = {'cwd': str(repo), 'transcriptPath': str(tr)}
		bad_cases = (
			('scripts/no_tag.py', 'def missing_tag() -> int:\n\treturn 1\n'),
			('scripts/ov.py', 'from typing import override\nclass Sub:\n\t# @used-by unused\n\t@override\n\tdef run(self) -> int:\n\t\treturn 1\n'),
			('scripts/self_ref.py', 'class Box:\n\t# @used-by :meth:`self.run()`\n\tdef helper(self) -> int:\n\t\treturn 1\n'),
			('scripts/bare.py', '# @used-by caller_fn\ndef target() -> int:\n\treturn 1\n'),
			('app/no_tag.js', 'function compute(x) {\n\treturn x + 1;\n}\n'),
			('src/NoTag.java', 'public class NoTag {\n\tpublic int run() {\n\t\treturn 1;\n\t}\n}\n'),
			('src/BareTag.java', 'public class BareTag {\n\t/**\n\t * @used-by unused\n\t */\n\tpublic int run() {\n\t\treturn 1;\n\t}\n}\n'),
		)
		for rel, src in bad_cases:
			dec = run_pre_tool_gates('write_file', {'Path': str(repo / rel), 'Content': src}, pay)
			self.assertEqual('deny', dec['decision'], f'{rel}: {dec}')
			self.assertIn('XREF-GATE', dec['reason'], f'{rel}: {dec}')
	# @used-by :meth:`XrefGateTests.test_pre_commit_blocks_stale_cross_file_xref_and_passes_after_sync()`
	def _assert_staged_js_java_and_legacy(self, root: Path) -> None:
		from agent_tools.xref_gate import verify_staged_xref
		js_repo = _init_repo(root / 'js_java')
		good_js = '/**\n * @used-by unused\n */\nfunction a() {\n\treturn 1;\n}\n'
		good_java = 'public class A {\n\t/**\n\t * - @used-by unused\n\t */\n\tpublic int a() {\n\t\treturn 1;\n\t}\n}\n'
		_seed_commit(js_repo, {'app/a.js': good_js, 'src/A.java': good_java})
		(js_repo / 'app/a.js').write_text('function a() {\n\treturn 2;\n}\n', encoding='utf-8')
		(js_repo / 'src/A.java').write_text('public class A {\n\tpublic int a() {\n\t\treturn 2;\n\t}\n}\n', encoding='utf-8')
		_git(js_repo, 'add', 'app/a.js', 'src/A.java')
		viols = verify_staged_xref(js_repo, ['app/a.js', 'src/A.java'], use_index=True, strict=True)
		self.assertTrue(any(('app/a.js' in v for v in viols)), viols)
		self.assertTrue(any(('src/A.java' in v for v in viols)), viols)
		(js_repo / 'app/a.js').write_text(good_js, encoding='utf-8')
		(js_repo / 'src/A.java').write_text(good_java, encoding='utf-8')
		_git(js_repo, 'add', 'app/a.js', 'src/A.java')
		self.assertEqual([], verify_staged_xref(js_repo, ['app/a.js', 'src/A.java'], use_index=True, strict=True))
		leg = _init_repo(root / 'legacy_staged')
		_seed_commit(leg, {'scripts/an.py': '# @used-by unused\ndef an():\n\treturn 1\n', 'scripts/old1.py': 'def old1():\n\treturn 1\n', 'scripts/old2.py': 'def old2():\n\treturn 2\n'})
		(leg / 'scripts/old1.py').write_text('def old1():\n\treturn 9\n', encoding='utf-8')
		_git(leg, 'add', 'scripts/old1.py')
		self.assertEqual([], verify_staged_xref(leg, ['scripts/old1.py'], use_index=True))
		(leg / 'scripts/old1.py').write_text('def old1():\n\treturn 9\ndef added_bad():\n\treturn 0\n', encoding='utf-8')
		_git(leg, 'add', 'scripts/old1.py')
		self.assertTrue(verify_staged_xref(leg, ['scripts/old1.py'], use_index=True))
	# @used-by :mod:`unittest`
	def test_pre_commit_blocks_stale_cross_file_xref_and_passes_after_sync(self) -> None:
		from agent_tools import git_gate
		from agent_tools.xref import run_xref_sync
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_repo(root / 'py_repo')
			_seed_annotated_ab(repo)
			(repo / 'scripts/b.py').write_text(_B_DROPPED, encoding='utf-8', newline='\n')
			(repo / 'tests/test_ab.py').write_text('# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# https://github.com/o/r/issues/1\nimport unittest\nfrom b import run\nclass AbTests(unittest.TestCase):\n\t# @used-by :mod:`unittest`\n\tdef test_run(self) -> None:\n\t\tself.assertEqual(1, run())\n\t# 2026-11-26 "Drop helper call": https://github.com/o/r/issues/2\n\t# @used-by :mod:`unittest`\n\tdef test_two(self) -> None:\n\t\tself.assertEqual(2, run())\n', encoding='utf-8', newline='\n')
			_git(repo, 'add', 'scripts/b.py', 'tests/test_ab.py')
			err_buf = io.StringIO()
			with redirect_stderr(err_buf):
				rc_bad = git_gate.GitRepoGate(repo).run_hook('pre-commit', agent_context=True)
			self.assertEqual(2, rc_bad)
			self.assertIn('XREF-GATE', err_buf.getvalue())
			run_xref_sync(repo, lang='python')
			(repo / 'scripts/a.py').write_text(_A_UNUSED, encoding='utf-8', newline='\n')
			_git(repo, 'add', 'scripts/a.py', 'scripts/b.py', 'tests/test_ab.py')
			self.assertEqual(0, git_gate.GitRepoGate(repo).run_hook('pre-commit', agent_context=True))
			self._assert_staged_js_java_and_legacy(root)
	# @used-by :mod:`unittest`
	def test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax(self) -> None:
		from agent_tools.gates import discover_pre_tool_gates
		from agent_tools.xref_gate import check_file_xref_violations, is_xref_governed_repo
		import check_rules_and_server_gate as rg
		self.assertTrue(callable(rg.check_xref_gate))
		gates = discover_pre_tool_gates()
		by_name = {g['name']: g['priority'] for g in gates}
		self.assertEqual(127, by_name.get('XREF-GATE'))
		self.assertGreater(by_name['XREF-GATE'], by_name['ISSUE-COMMENT-GATE'])
		self.assertGreater(by_name['ISSUE-COMMENT-GATE'], by_name['CODE-STYLE-GATE'])
		self.assertTrue(is_xref_governed_repo(WT_ROOT))
		self.assertEqual([], check_file_xref_violations('README.md', '# doc\n'))
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_repo(root / 'repo')
			self.assertFalse(is_xref_governed_repo(repo))
			_seed_commit(repo, {'scripts/anchor.py': '# @used-by unused\ndef anchor() -> int:\n\treturn 0\n', 'scripts/legacy.py': 'def old_fn() -> int:\n\treturn 1\n'})
			self.assertTrue(is_xref_governed_repo(repo))
			tr = _write_red_transcript(repo)
			self._assert_pre_tool_denies_bad_samples(repo, tr)
			self._assert_pre_tool_allows_valid_and_legacy_ratchet(repo, tr)
			standalone = root / 'solo.py'
			self.assertIsNone(rg.check_xref_gate('write_file', {'Path': str(standalone), 'Content': 'def x():\n\treturn 1\n'}, {}))
	# @used-by :mod:`unittest`
	def test_worktree_land_blocks_stale_xref_and_passes_when_synced(self) -> None:
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		from agent_tools.xref import run_xref_sync
		from agent_tools.xref_gate import verify_worktree_xref_changes
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_repo(root / 'repo')
			_seed_annotated_ab(repo)
			wt = Path(worktree_begin(repo, 'xref-wt', worktrees_dir=root / 'wts')['worktree'])
			(wt / 'scripts/b.py').write_text(_B_DROPPED, encoding='utf-8', newline='\n')
			_git(wt, 'add', 'scripts/b.py')
			_git(wt, 'commit', '--no-verify', '-m', 'stale xref')
			blocked = worktree_land(wt, run_tests=False, remove=False, leases_dir=root / 'leases', promote_snapshot=False)
			self.assertFalse(blocked['landed'], blocked)
			self.assertEqual('xref_integrity', blocked['stage'])
			self.assertIn('XREF-GATE', blocked['error'])
			run_xref_sync(wt, lang='python')
			(wt / 'scripts/a.py').write_text(_A_UNUSED, encoding='utf-8', newline='\n')
			_git(wt, 'add', 'scripts/a.py')
			_git(wt, 'commit', '--no-verify', '-m', 'sync xref')
			landed = worktree_land(wt, run_tests=False, remove=True, leases_dir=root / 'leases', promote_snapshot=False)
			self.assertTrue(landed['valid'], landed)
			self.assertTrue(landed['landed'], landed)
			leg = _init_repo(root / 'leg_wt')
			_seed_commit(leg, {'scripts/an.py': '# @used-by unused\ndef an():\n\treturn 1\n', 'scripts/u1.py': 'def u1():\n\treturn 1\n', 'scripts/u2.py': 'def u2():\n\treturn 2\n'})
			wt2 = Path(worktree_begin(leg, 'leg-ok', worktrees_dir=root / 'wts2')['worktree'])
			(wt2 / 'scripts/u1.py').write_text('def u1():\n\treturn 3\n', encoding='utf-8')
			_git(wt2, 'add', 'scripts/u1.py')
			_git(wt2, 'commit', '--no-verify', '-m', 'edit legacy')
			self.assertEqual([], verify_worktree_xref_changes(wt2, 'main'))
if '__main__' == __name__:
	unittest.main()
