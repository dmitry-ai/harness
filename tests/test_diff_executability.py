# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement diff executability classifier and automatic test skip":
# https://github.com/dmitry-ai/harness/issues/358
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
_APP_PY = '# comment\nclass Base:\n\tdef run(self) -> int:\n\t\treturn 1\nclass Sub(Base):\n\tdef run(self) -> int:\n\t\treturn 2\n'
_TEST_APP_PY = '# test comment\nimport unittest\nclass AppT(unittest.TestCase):\n\tdef test_ok(self) -> None:\n\t\tself.assertEqual(1, 1)\n'
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_NEW_LANG_CASES = (
	('rust', 'src/lib.rs', '// old\npub fn f(x: &\'a str) -> &\'a str { r#"// str"# }\n', '// new\npub fn f(x: &\'a str) -> &\'a str { r#"// str"# }\n'),
	('go', 'pkg/app.go', '// old\npackage p\nvar s = `// raw`\n', '// new\npackage p\nvar s = `// raw`\n'),
	('zig', 'src/main.zig', '// old\nconst x: i32 = 1;\n', '// new\nconst x: i32 = 1;\n'),
	('swift', 'Sources/App.swift', '/* outer /* old */ */\nlet x = 1\n', '/* outer /* new */ */\nlet x = 1\n'),
	('scala', 'src/App.scala', '/* a /* old */ */\nval x = 1\n', '/* a /* new */ */\nval x = 1\n'),
	('groovy', 'src/App.groovy', '// old\ndef x = 1\n', '// new\ndef x = 1\n'),
	('objc', 'src/App.m', '// old\nint f(void) { return 1; }\n', '// new\nint f(void) { return 1; }\n'),
	('objc', 'src/App.mm', '/* old */\nint f() { return 1; }\n', '/* new */\nint f() { return 1; }\n'),
	('proto', 'api/v1.proto', '// old\nsyntax = "proto3";\n', '// new\nsyntax = "proto3";\n'),
	('hcl', 'infra/main.tf', '# old\n// old2\n/* old3 */\nresource "a" "b" {}\n', '# new\n// new2\n/* new3 */\nresource "a" "b" {}\n'),
	('hcl', 'infra/vars.tfvars', '# old\nx = 1\n', '# new\nx = 1\n'),
	('hcl', 'infra/conf.hcl', '# old\nx = 1\n', '# new\nx = 1\n'),
	('graphql', 'schema/api.graphql', '# old\ntype Query { ok: Boolean }\n', '# new\ntype Query { ok: Boolean }\n'),
	('graphql', 'schema/api.gql', '# old\ntype Query { ok: Boolean }\n', '# new\ntype Query { ok: Boolean }\n'),
	('dockerfile', 'Dockerfile', '# old\nFROM python:3.12\n', '# new\nFROM python:3.12\n'),
	('dockerfile', 'app.dockerfile', '# old\nFROM python:3.12\n', '# new\nFROM python:3.12\n'),
	('lua', 'scripts/init.lua', '-- old\n--[[ block old ]]\nlocal x = 1\n', '-- new\n--[[ block new ]]\nlocal x = 1\n'),
	('fsharp', 'src/App.fs', '// old\n(* nested (* old *) *)\nlet x = 1\n', '// new\n(* nested (* new *) *)\nlet x = 1\n'),
	('vb', 'src/App.vb', '\' old\nREM old\nDim x = 1\n', '\' new\nREM new\nDim x = 1\n'),
	('sed', 'bin/fix.sed', '# old\ns/a/b/g\n', '# new\ns/a/b/g\n'),
	('tcl', 'bin/run.tcl', '# old\nset x 1\n', '# new\nset x 1\n'),
	('sfc', 'ui/App.vue', '<!-- old -->\n<script>// old js\nconst x = 1;</script>\n<style>/* old css */.a{}</style>\n', '<!-- new -->\n<script>// new js\nconst x = 1;</script>\n<style>/* new css */.a{}</style>\n'),
	('sfc', 'ui/App.svelte', '<!-- old -->\n<script>// old\nlet x = 1;</script>\n', '<!-- new -->\n<script>// new\nlet x = 1;</script>\n'),
	('sfc', 'ui/Page.astro', '---\n// old fm\nconst x = 1;\n---\n<!-- old -->\n<div>{x}</div>\n', '---\n// new fm\nconst x = 1;\n---\n<!-- new -->\n<div>{x}</div>\n'),
	('makefile', 'Makefile', '# old\nall:\n\techo ok\n', '# new\nall:\n\techo ok\n'),
	('justfile', 'Justfile', '# old\nbuild:\n\techo ok\n', '# new\nbuild:\n\techo ok\n'),
	('ruby', 'Vagrantfile', '# old\nVagrant.configure("2") {}\n', '# new\nVagrant.configure("2") {}\n'),
	('cmake', 'CMakeLists.txt', '# old\n#[[ block old ]]\nproject(demo)\n', '# new\n#[[ block new ]]\nproject(demo)\n'),
	('sass', 'styles/app.sass', '// old\n.btn\n  color: red\n', '// new\n.btn\n  color: red\n'),
)
# @used-by :func:`_commit_wt()`
# @used-by :func:`_init_node_repo()`
# @used-by :func:`_init_py_repo()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True, creationflags=_NO_WINDOW)
	return (proc.stdout or '').strip()
# @used-by :meth:`DiffExecutabilityTests.test_polyglot_land_skips_tests_and_health_for_comment_only_js()`
# @used-by :meth:`DiffExecutabilityTests.test_worktree_land_blocks_no_tests_on_executable_and_allows_audited_reason()`
# @used-by :meth:`DiffExecutabilityTests.test_worktree_land_skips_tests_for_non_executable_and_runs_for_executable()`
def _commit_wt(wt: Path, rel: str, text: str, msg: str) -> None:
	(wt / rel).write_text(text, encoding='utf-8')
	_git(wt, 'add', rel)
	_git(wt, 'commit', '--no-verify', '-m', msg)
# @used-by :meth:`DiffExecutabilityTests.test_polyglot_land_skips_tests_and_health_for_comment_only_js()`
def _init_node_repo(root: Path) -> Path:
	proj = root / 'proj'
	repo = proj / 'code'
	repo.mkdir(parents=True)
	(proj / '\ua616/data').mkdir(parents=True)
	(repo / 'package.json').write_text(json.dumps({'name': 'demo', 'scripts': {'test': 'node --test demo.test.js'}}), encoding='utf-8')
	(repo / 'demo.test.js').write_text("const test = require('node:test');\nconst assert = require('node:assert/strict');\ntest('ok', () => { assert.equal(1, 1); });\n", encoding='utf-8')
	(repo / 'app.js').write_text('// old\nfunction run() {\n\treturn 1;\n}\nmodule.exports = { run };\n', encoding='utf-8')
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	_git(repo, 'remote', 'add', 'origin', 'https://github.com/owner/node-demo.git')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'init')
	return repo
# @used-by :meth:`DiffExecutabilityTests.test_evaluator_exempts_comment_only_test_edits_in_idle_and_post_green()`
# @used-by :meth:`DiffExecutabilityTests.test_worktree_land_blocks_no_tests_on_executable_and_allows_audited_reason()`
# @used-by :meth:`DiffExecutabilityTests.test_worktree_land_skips_tests_for_non_executable_and_runs_for_executable()`
def _init_py_repo(root: Path) -> Path:
	repo = root / 'repo'
	(repo / 'pkg').mkdir(parents=True)
	(repo / 'tests').mkdir(parents=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	_git(repo, 'remote', 'add', 'origin', 'https://github.com/owner/demo.git')
	(repo / 'README.md').write_text('# Demo\n', encoding='utf-8')
	(repo / 'pkg/app.py').write_text(_APP_PY, encoding='utf-8')
	(repo / 'tests/test_app.py').write_text(_TEST_APP_PY, encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'init')
	return repo
class DiffExecutabilityTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_all_software_code_suffixes_and_basenames_have_lexers(self) -> None:
		from agent_tools.tdd.classifier import SOFTWARE_CODE_SUFFIXES, _EXTENSIONLESS_CODE_NAMES
		from agent_tools.tdd.comment_diff import COMMENT_LEXER_LANGUAGES, _BASENAME_LANG, _EXTENSION_LANG, detect_comment_language, is_comment_only_diff
		self.assertEqual([], sorted(SOFTWARE_CODE_SUFFIXES - set(_EXTENSION_LANG)))
		self.assertEqual([], sorted(_EXTENSIONLESS_CODE_NAMES - set(_BASENAME_LANG)))
		for lang in set(_EXTENSION_LANG.values()) | set(_BASENAME_LANG.values()):
			self.assertIn(lang, COMMENT_LEXER_LANGUAGES)
		for expected_lang, rel, old_t, new_t in _NEW_LANG_CASES:
			self.assertEqual(expected_lang, detect_comment_language(rel, content=old_t), rel)
			self.assertTrue(is_comment_only_diff(rel, old_t, new_t), rel)
	# @used-by :mod:`unittest`
	def test_evaluator_exempts_comment_only_test_edits_in_idle_and_post_green(self) -> None:
		from agent_tools.tdd.evaluator import evaluate_tdd_events
		from agent_tools.tdd.events import build_command_tdd_event, build_file_write_tdd_event
		with tempfile.TemporaryDirectory() as td:
			repo = _init_py_repo(Path(td).resolve())
			test_f = repo / 'tests/test_app.py'
			prod_f = repo / 'pkg/app.py'
			tests_dir = repo / 'tests'
			test_f.write_text(_TEST_APP_PY.replace('# test comment', '# updated test comment'), encoding='utf-8')
			idle_res = evaluate_tdd_events([build_file_write_tdd_event(1, test_f, cwd=repo)], require_final_full_green=True, project_root=repo)
			self.assertTrue(idle_res['verified'], idle_res)
			sc_idle = idle_res['scopes'].get(str(repo))
			if None is not sc_idle:
				self.assertEqual('IDLE', sc_idle['state'])
				self.assertEqual([], sc_idle['written_tests'])
			prod_f.write_text(_APP_PY.replace('return 1', 'return 7'), encoding='utf-8')
			real_test = repo / 'tests/test_extra.py'
			real_test.write_text('import unittest\nclass E(unittest.TestCase):\n\tdef test_e(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
			post_green = [
				build_file_write_tdd_event(1, real_test, cwd=repo),
				build_command_tdd_event(2, f'python -m unittest "{real_test}"', ['Command exited with code 1.\nFAIL\n'], cwd=repo),
				build_file_write_tdd_event(3, prod_f, cwd=repo),
				build_command_tdd_event(4, f'python harness.py run-tests "{tests_dir}"', ['Command exited with code 0.\nOK\n'], cwd=repo),
				build_file_write_tdd_event(5, test_f, cwd=repo),
			]
			self.assertTrue(evaluate_tdd_events(post_green, require_final_full_green=True, project_root=repo)['verified'])
	# @used-by :mod:`unittest`
	def test_polyglot_land_skips_tests_and_health_for_comment_only_js(self) -> None:
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_node_repo(root)
			wt = Path(worktree_begin(repo, 'jsdoc-xref', worktrees_dir=repo.parent / '\ua616/data/worktrees')['worktree'])
			_commit_wt(wt, 'app.js', '/**\n * @used-by unused\n */\nfunction run() {\n\treturn 1;\n}\nmodule.exports = { run };\n', 'jsdoc only')
			with patch('agent_tools.polyglot_land.run_polyglot_land_tests', side_effect=AssertionError('must not run node tests')) as spy_t, patch('agent_tools.polyglot_land.run_repo_health_check', side_effect=AssertionError('must not run health')) as spy_h:
				res = worktree_land(wt, run_tests=True, remove=True, owner='js', leases_dir=root / 'leases', promote_snapshot=False)
			self.assertTrue(res['valid'] and res['landed'], res)
			self.assertEqual(0, res['test_runs'])
			self.assertEqual(0, spy_t.call_count)
			self.assertEqual(0, spy_h.call_count)
	# @used-by :mod:`unittest`
	def test_whitespace_only_and_indentation_sensitive_fail_closed(self) -> None:
		from agent_tools.tdd.diff_executability import classify_text_diff
		self.assertEqual('whitespace_only', classify_text_diff('src/a.py', 'x=1\ny=2\n', 'x = 1\n\ny = 2\n'))
		self.assertEqual('whitespace_only', classify_text_diff('src/a.py', 'def f():\r\n    return (1 + 2)\r\n', 'def f():\n\treturn (\n\t\t1 + 2\n\t)\n'))
		self.assertEqual('whitespace_only', classify_text_diff('src/a.js', 'const a=1;\nconst b=2;\n', 'const a = 1;\n\nconst b = 2;\n'))
		self.assertEqual('whitespace_only', classify_text_diff('src/A.java', 'class A { int x=1; }\n', 'class A {\n\tint x = 1;\n}\n'))
		self.assertEqual('executable', classify_text_diff('src/a.py', 'if a:\n\tx = 1\n\ty = 2\n', 'if a:\n\tx = 1\ny = 2\n'))
		self.assertEqual('executable', classify_text_diff('src/a.py', '"""doc1"""\nx = 1\n', '"""doc2"""\nx = 1\n'))
		self.assertEqual('executable', classify_text_diff('Makefile', 'all:\n\techo ok\n', 'all:\n    echo ok\n'))
		self.assertEqual('executable', classify_text_diff('styles/a.sass', '.a\n  color: red\n', '.a\ncolor: red\n'))
		self.assertEqual('executable', classify_text_diff('Dockerfile', '# syntax=docker/dockerfile:1\nFROM alpine\n', '# syntax=docker/dockerfile:2\nFROM alpine\n'))
		self.assertEqual('executable', classify_text_diff('bin/x.sed', '#n\ns/a/b/\n', '# comment\ns/a/b/\n'))
		self.assertEqual('non_code', classify_text_diff('docs/README.md', None, '# New doc\n'))
		self.assertEqual('executable', classify_text_diff('src/new.py', None, '# comment only new file\n'))
	# @used-by :mod:`unittest`
	def test_worktree_land_blocks_no_tests_on_executable_and_allows_audited_reason(self) -> None:
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_py_repo(root)
			(repo / '.git/info/exclude').write_text('\ua616/\n', encoding='utf-8')
			wt_base, leases = (root / 'wts', root / 'leases')
			wt = Path(worktree_begin(repo, 'exec-no-tests', worktrees_dir=wt_base)['worktree'])
			_commit_wt(wt, 'pkg/app.py', _APP_PY.replace('return 1', 'return 9'), 'exec change')
			blocked = worktree_land(wt, run_tests=False, remove=False, owner='b1', leases_dir=leases, promote_snapshot=False)
			self.assertFalse(blocked['valid'])
			self.assertFalse(blocked['landed'])
			self.assertEqual('no_tests_blocked', blocked['stage'])
			bad_reason = worktree_land(wt, run_tests=False, no_tests_reason='skip tests because hurry', remove=False, owner='b2', leases_dir=leases, promote_snapshot=False)
			self.assertFalse(bad_reason['valid'])
			self.assertEqual('no_tests_blocked', bad_reason['stage'])
			allowed = worktree_land(wt, run_tests=False, no_tests_reason='Audited emergency hotfix verified independently in isolated staging environment.', remove=True, owner='ok', leases_dir=leases, promote_snapshot=False)
			self.assertTrue(allowed['valid'] and allowed['landed'], allowed)
			self.assertEqual(0, allowed['test_runs'])
	# @used-by :mod:`unittest`
	def test_worktree_land_skips_tests_for_non_executable_and_runs_for_executable(self) -> None:
		from agent_tools.tdd.mechanical import record_mechanical_exemption
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_py_repo(root)
			(repo / '.git/info/exclude').write_text('\ua616/\n', encoding='utf-8')
			wt_base, leases = (root / 'wts', root / 'leases')
			iss_url = 'https://github.com/owner/demo/issues/9'
			record_mechanical_exemption(repo, repo=repo, issue_url=iss_url, pattern='return 2', replacement='return 3', reason='Audited mechanical constant update requested under owner/demo issue 9.', turn_key='mech-tk')
			cmt_py = _APP_PY.replace('# comment', '# updated comment')
			ws_py = cmt_py + '\n'
			mech_py = ws_py.replace('return 2', 'return 3')
			ov_py = 'from typing import override\n' + mech_py.replace('class Sub(Base):\n\tdef run', 'class Sub(Base):\n\t@override\n\tdef run')
			cases = (
				('doc-only', 'README.md', '# Demo Updated\n', 'docs', 0),
				('cmt-only', 'pkg/app.py', cmt_py, 'comment', 0),
				('ws-only', 'pkg/app.py', ws_py, 'whitespace', 0),
				('mech-only', 'pkg/app.py', mech_py, iss_url, 0),
				('override-exec', 'pkg/app.py', ov_py, 'add override', 1),
			)
			for task, rel, content, msg, exp_runs in cases:
				wt = Path(worktree_begin(repo, task, worktrees_dir=wt_base)['worktree'])
				_commit_wt(wt, rel, content, msg)
				res = worktree_land(wt, run_tests=True, remove=True, owner=task, leases_dir=leases, promote_snapshot=False)
				self.assertTrue(res['valid'] and res['landed'], f'{task}: {res}')
				self.assertEqual(exp_runs, res['test_runs'], f'{task}: {res}')
if '__main__' == __name__:
	unittest.main()
