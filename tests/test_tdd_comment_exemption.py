# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools import git_gate
from agent_tools.issues.auditor import TurnIssueLifecycleAuditor
from agent_tools.tdd.comment_diff import COMMENT_LEXER_LANGUAGES, detect_comment_language, is_comment_only_diff
from agent_tools.tdd.enforcement import evaluate_pre_tool_use_tdd
from agent_tools.tdd.evaluator import evaluate_tdd_events
from agent_tools.tdd.events import build_file_write_tdd_event
ISSUE_URL = 'https://github.com/dmitry-ai/harness/issues/238'
OLD_URL = 'https://upwork.com/fl/mage2pro'
NEW_URL = 'https://github.com/dmitrii-fediuk'
_LANG_CASES = (
	('php', 'app/Model.php', f'<?php\n// {OLD_URL}\nreturn 1;\n', f'<?php\n// {NEW_URL}\nreturn 1;\n'),
	('php', 'view/page.phtml', f'<!-- {OLD_URL} -->\n<div><?php /* {OLD_URL} */ echo 1; ?></div>\n', f'<!-- {NEW_URL} -->\n<div><?php /* {NEW_URL} */ echo 1; ?></div>\n'),
	('javascript', 'scripts/site.js', f'// @homepageURL {OLD_URL}\nconst x = 1;\n', f'// @homepageURL {NEW_URL}\nconst x = 1;\n'),
	('less', 'styles/app.less', f'// {OLD_URL}\n.btn {{ color: red; }}\n', f'// {NEW_URL}\n.btn {{ color: red; }}\n'),
	('css', 'styles/app.css', f'/* {OLD_URL} */\n.btn {{ color: red; }}\n', f'/* {NEW_URL} */\n.btn {{ color: red; }}\n'),
	('shell', 'bin/deploy.sh', f'#!/usr/bin/env bash\n# {OLD_URL}\necho ok\n', f'#!/usr/bin/env bash\n# {NEW_URL}\necho ok\n'),
	('scss', 'styles/app.scss', f'// {OLD_URL}\n$c: #fff;\n', f'// {NEW_URL}\n$c: #fff;\n'),
	('ruby', 'lib/app.rb', f'# {OLD_URL}\n=begin\n{OLD_URL}\n=end\nputs 1\n', f'# {NEW_URL}\n=begin\n{NEW_URL}\n=end\nputs 1\n'),
	('python', 'src/app.py', f'#!/usr/bin/env python3\n# {OLD_URL}\nx = 1\n', f'#!/usr/bin/env python3\n# {NEW_URL}\nx = 1\n'),
	('batch', 'bin/run.bat', f'@echo off\nREM {OLD_URL}\n:: {OLD_URL}\necho ok\n', f'@echo off\nREM {NEW_URL}\n:: {NEW_URL}\necho ok\n'),
	('powershell', 'bin/run.ps1', f'# {OLD_URL}\n<# {OLD_URL} #>\nWrite-Output 1\n', f'# {NEW_URL}\n<# {NEW_URL} #>\nWrite-Output 1\n'),
	('perl', 'bin/run.pl', f'# {OLD_URL}\n=pod\n{OLD_URL}\n=cut\nprint 1;\n', f'# {NEW_URL}\n=pod\n{NEW_URL}\n=cut\nprint 1;\n'),
	('sql', 'db/init.sql', f'-- {OLD_URL}\n/* {OLD_URL} */\nSELECT 1;\n', f'-- {NEW_URL}\n/* {NEW_URL} */\nSELECT 1;\n'),
	('java', 'src/App.java', f'// {OLD_URL}\nclass App {{ int x = 1; }}\n', f'// {NEW_URL}\nclass App {{ int x = 1; }}\n'),
	('c', 'src/app.c', f'/* {OLD_URL} */\nint main(void) {{ return 0; }}\n', f'/* {NEW_URL} */\nint main(void) {{ return 0; }}\n'),
	('cpp', 'src/app.cpp', f'// {OLD_URL}\nint main() {{ return 0; }}\n', f'// {NEW_URL}\nint main() {{ return 0; }}\n'),
	('vbscript', 'bin/run.vbs', f"' {OLD_URL}\nREM {OLD_URL}\nWScript.Echo 1\n", f"' {NEW_URL}\nREM {NEW_URL}\nWScript.Echo 1\n"),
	('typescript', 'src/app.ts', f'// {OLD_URL}\nconst n: number = 1;\n', f'// {NEW_URL}\nconst n: number = 1;\n'),
	('kotlin', 'src/App.kt', f'/* outer /* {OLD_URL} */ */\nfun main() {{}}\n', f'/* outer /* {NEW_URL} */ */\nfun main() {{}}\n'),
	('awk', 'bin/run.awk', f'# {OLD_URL}\nBEGIN {{ print 1 }}\n', f'# {NEW_URL}\nBEGIN {{ print 1 }}\n'),
	('csharp', 'src/App.cs', f'// {OLD_URL}\nclass App {{ int X = 1; }}\n', f'// {NEW_URL}\nclass App {{ int X = 1; }}\n'),
)
_NEGATIVE_CASES = (
	('php_string', 'app/Model.php', f"<?php\nreturn '{OLD_URL}';\n", f"<?php\nreturn '{NEW_URL}';\n"),
	('php_attr', 'app/Model.php', f"<?php\n#[Attr('{OLD_URL}')]\nclass A {{}}\n", f"<?php\n#[Attr('{NEW_URL}')]\nclass A {{}}\n"),
	('py_string', 'src/app.py', f"URL = '{OLD_URL}'\n", f"URL = '{NEW_URL}'\n"),
	('py_docstring', 'src/app.py', f'"""{OLD_URL}"""\nx = 1\n', f'"""{NEW_URL}"""\nx = 1\n'),
	('py_shebang', 'src/app.py', '#!/usr/bin/env python3\nx = 1\n', '#!/usr/bin/env python\nx = 1\n'),
	('py_coding', 'src/app.py', '# coding: utf-8\nx = 1\n', '# coding: latin-1\nx = 1\n'),
	('js_string', 'src/app.js', f"const u = '{OLD_URL}';\n", f"const u = '{NEW_URL}';\n"),
	('js_template', 'src/app.js', f'const u = `{OLD_URL}/${{id}}`;\n', f'const u = `{NEW_URL}/${{id}}`;\n'),
	('js_regex', 'src/app.js', 'const r = /https:\\/\\/upwork\\.com/;\n', 'const r = /https:\\/\\/github\\.com/;\n'),
	('js_asi', 'src/app.js', '// c\nreturn x;\n', '// c2\nreturn\nx;\n'),
	('css_line_slash', 'styles/app.css', f'// {OLD_URL}\n.a {{ color: red; }}\n', f'// {NEW_URL}\n.a {{ color: red; }}\n'),
	('less_url_unquoted', 'styles/app.less', f'.a {{ background: url({OLD_URL}/a.png); }}\n', f'.a {{ background: url({NEW_URL}/a.png); }}\n'),
	('sql_string', 'db/init.sql', f"SELECT '{OLD_URL}';\n", f"SELECT '{NEW_URL}';\n"),
	('sh_param_hash', 'bin/run.sh', 'echo ${#var}\n', 'echo ${#other}\n'),
	('ps_string', 'bin/run.ps1', f'Write-Output "{OLD_URL}"\n', f'Write-Output "{NEW_URL}"\n'),
	('c_preproc', 'src/app.c', f'#define URL "{OLD_URL}"\n', f'#define URL "{NEW_URL}"\n'),
	('c_token_merge', 'src/app.c', 'int/*c*/x;\n', 'intx;\n'),
	('mixed_comment_and_code', 'src/app.js', f'// {OLD_URL}\nconst a = 1;\n', f'// {NEW_URL}\nconst a = 2;\n'),
	('unsupported_rust', 'src/lib.rs', f'// {OLD_URL}\nfn f() {{}}\n', f'// {NEW_URL}\nfn f() {{}}\n'),
	('unterminated_block', 'src/app.js', f'/* {OLD_URL}\nconst a = 1;\n', f'/* {NEW_URL}\nconst a = 1;\n'),
	('invalid_python_syntax', 'src/app.py', f'# {OLD_URL}\n"unterminated\n', f'# {NEW_URL}\n"unterminated\n'),
)
# @used-by :func:`_init_repo()`
# @used-by :func:`_seed_commit()`
# @used-by :meth:`CommentOnlyExemptionTests.test_auditor_exempts_committed_comment_only_js_from_per_file_issue_url()`
# @used-by :meth:`CommentOnlyExemptionTests.test_git_gate_allows_comment_only_commit_and_blocks_code_change()`
def _git(*args: str) -> None:
	subprocess.run(['git', *args], check=True, stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
# @used-by :meth:`CommentOnlyExemptionTests.test_auditor_exempts_committed_comment_only_js_from_per_file_issue_url()`
# @used-by :meth:`CommentOnlyExemptionTests.test_evaluator_skips_tdd_red_and_full_gates_for_comment_only_write()`
# @used-by :meth:`CommentOnlyExemptionTests.test_git_gate_allows_comment_only_commit_and_blocks_code_change()`
# @used-by :meth:`CommentOnlyExemptionTests.test_pre_tool_use_allows_comment_only_edit_and_denies_code_edit()`
def _init_repo(repo: Path, remote_url: str | None=None) -> None:
	repo.mkdir(parents=True, exist_ok=True)
	_git('init', '-b', 'main', str(repo))
	cfg = repo / '.git/config'
	extra = '[user]\n\temail = test@example.com\n\tname = Test User\n'
	if None is not remote_url:
		extra += f'[remote "origin"]\n\turl = {remote_url}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n'
	cfg.write_text(cfg.read_text(encoding='utf-8') + extra, encoding='utf-8')
# @used-by :meth:`CommentOnlyExemptionTests.test_auditor_exempts_committed_comment_only_js_from_per_file_issue_url()`
# @used-by :meth:`CommentOnlyExemptionTests.test_evaluator_skips_tdd_red_and_full_gates_for_comment_only_write()`
# @used-by :meth:`CommentOnlyExemptionTests.test_git_gate_allows_comment_only_commit_and_blocks_code_change()`
# @used-by :meth:`CommentOnlyExemptionTests.test_pre_tool_use_allows_comment_only_edit_and_denies_code_edit()`
def _seed_commit(repo: Path, rel: str, content: str) -> None:
	target = repo / rel
	target.parent.mkdir(parents=True, exist_ok=True)
	target.write_text(content, encoding='utf-8')
	_git('-C', str(repo), 'add', rel)
	_git('-C', str(repo), 'commit', '--no-verify', '-m', 'seed')
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
class CommentOnlyExemptionTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_auditor_exempts_committed_comment_only_js_from_per_file_issue_url(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve() / 'proj'
			repo = root / 'code'
			(root / '_').mkdir(parents=True)
			_init_repo(repo, remote_url='https://github.com/dmitrii-fediuk/vm.git')
			_seed_commit(repo, 'site.js', f'// @homepageURL {OLD_URL}\nconsole.log(1);\n')
			(repo / 'site.js').write_text(f'// @homepageURL {NEW_URL}\nconsole.log(1);\n', encoding='utf-8')
			_git('-C', str(repo), 'add', 'site.js')
			issue_url = 'https://github.com/dmitrii-fediuk/vm/issues/1'
			_git('-C', str(repo), 'commit', '--no-verify', '-m', issue_url)
			aud = TurnIssueLifecycleAuditor(root, {'touched_files': [str(repo / 'site.js')]}, None)
			req_set: set[str] = set()
			comm_set: set[str] = set()
			aud._inspect_touched_code_file(repo, 'site.js', req_set, comm_set)
			self.assertEqual([], aud.violations)
	# @used-by :mod:`unittest`
	def test_comment_only_diffs_accepted_for_all_20_languages(self) -> None:
		self.assertEqual(20, len(COMMENT_LEXER_LANGUAGES))
		seen: set[str] = set()
		for expected_lang, rel, old_txt, new_txt in _LANG_CASES:
			self.assertEqual(expected_lang, detect_comment_language(rel, content=old_txt), rel)
			self.assertTrue(is_comment_only_diff(rel, old_txt, new_txt), f'Expected comment-only for {rel}')
			seen.add(expected_lang)
		self.assertEqual(set(COMMENT_LEXER_LANGUAGES), seen)
	# @used-by :mod:`unittest`
	def test_evaluator_skips_tdd_red_and_full_gates_for_comment_only_write(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve() / 'repo'
			_init_repo(repo)
			_seed_commit(repo, 'src/app.php', f'<?php\n// {OLD_URL}\nreturn 1;\n')
			(repo / 'src/app.php').write_text(f'<?php\n// {NEW_URL}\nreturn 1;\n', encoding='utf-8')
			ev = build_file_write_tdd_event(1, repo / 'src/app.php', cwd=repo)
			res = evaluate_tdd_events([ev], require_final_full_green=True)
			self.assertTrue(res['verified'], res)
			(repo / 'src/app.php').write_text(f"<?php\nreturn '{NEW_URL}';\n", encoding='utf-8')
			res_code = evaluate_tdd_events([ev], require_final_full_green=True)
			self.assertFalse(res_code['verified'], res_code)
	# @used-by :mod:`unittest`
	def test_git_gate_allows_comment_only_commit_and_blocks_code_change(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve() / 'ext_repo'
			_init_repo(repo)
			_seed_commit(repo, 'site.js', f'// @homepageURL {OLD_URL}\nconst a = 1;\n')
			_seed_commit(repo, 'app.php', f'<?php\n// {OLD_URL}\necho 1;\n')
			(repo / 'site.js').write_text(f'// @homepageURL {NEW_URL}\nconst a = 1;\n', encoding='utf-8')
			(repo / 'app.php').write_text(f'<?php\n// {NEW_URL}\necho 1;\n', encoding='utf-8')
			_git('-C', str(repo), 'add', 'site.js', 'app.php')
			self.assertEqual(0, git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True))
			git_gate.verify_git_write_invocation(['-C', str(repo), 'commit', '-m', ISSUE_URL], agent_context=True)
			self.assertEqual(['app.php', 'site.js'], sorted(git_gate.check_commit(repo, ['site.js', 'app.php'], message=ISSUE_URL)))
			(repo / 'site.js').write_text(f'// @homepageURL {NEW_URL}\nconst a = 2;\n', encoding='utf-8')
			_git('-C', str(repo), 'add', 'site.js')
			self.assertEqual(2, git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True))
			with self.assertRaisesRegex(ValueError, 'TDD-COMMIT-GATE|Issue URL'):
				git_gate.check_commit(repo, ['site.js', 'app.php'], message=ISSUE_URL)
	# @used-by :mod:`unittest`
	def test_non_comment_and_edge_cases_fail_closed(self) -> None:
		self.assertFalse(is_comment_only_diff('src/app.py', None, '# new file\n'))
		self.assertFalse(is_comment_only_diff('src/app.py', '# old\n', None))
		for label, rel, old_txt, new_txt in _NEGATIVE_CASES:
			self.assertFalse(is_comment_only_diff(rel, old_txt, new_txt), f'Expected fail-closed for {label} ({rel})')
	# @used-by :mod:`unittest`
	def test_pre_tool_use_allows_comment_only_edit_and_denies_code_edit(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve() / 'repo'
			_init_repo(repo)
			_seed_commit(repo, 'src/app.php', f'<?php\n// {OLD_URL}\nreturn 1;\n')
			allow_err = evaluate_pre_tool_use_tdd(
				'edit_file',
				{'Path': str(repo / 'src/app.php'), 'Target': f'// {OLD_URL}', 'Replacement': f'// {NEW_URL}'},
				{'cwd': str(repo)},
			)
			self.assertIsNone(allow_err)
			deny_err = evaluate_pre_tool_use_tdd(
				'edit_file',
				{'Path': str(repo / 'src/app.php'), 'Target': 'return 1;', 'Replacement': 'return 2;'},
				{'cwd': str(repo)},
			)
			self.assertIsNotNone(deny_err)
			self.assertIn('TDD-RED-GATE', str(deny_err))
if '__main__' == __name__:
	unittest.main()
