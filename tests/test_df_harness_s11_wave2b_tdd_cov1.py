# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
_NO_WIN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :meth:`DfHarnessS11Wave2bTddCov1Tests.test_diff_contract_executability_and_coverage_end_to_end()`
def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(['git', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=False, timeout=30, creationflags=_NO_WIN)
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`unittest`
class DfHarnessS11Wave2bTddCov1Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_classifier_command_inspector_and_lexers(self) -> None:
		from Df.Harness.Tdd.CLikeCommentLexer import CLikeCommentLexer
		from Df.Harness.Tdd.CodeClassifier import CodeClassifier
		from Df.Harness.Tdd.CommandInspector import CommandInspector
		from Df.Harness.Tdd.CommentDiff import CommentDiff
		from Df.Harness.Tdd.CommentScanners import CommentScanners
		from Df.Harness.Tdd.ExtCommentLexer import ExtCommentLexer
		js_lex = CLikeCommentLexer('const x = `a${1 + 2}b`; const r = /ab/gi; // c', {'line_slash': True, 'template_lit': True, 'regex_lit': True, 'nl_significant': True}).lex()
		rs_lex = ExtCommentLexer.lex_rust("fn f<'a>(c: char) { let s = r#\"raw\"#; }")
		self.assertTrue(js_lex)
		self.assertTrue(rs_lex)
		self.assertGreater(CommentScanners.scan_cpp_raw('R"(hi)"', 0), 0)
		self.assertGreater(CommentScanners.scan_css_url('url(a.png)', 0), 0)
		self.assertGreater(CommentScanners.scan_heredoc('cat <<EOF\nhi\nEOF\n', 4), 4)
		self.assertGreater(CommentScanners.scan_js_regex('/abc/gi', 0), 0)
		self.assertGreater(CommentScanners.scan_line_block('=begin\nhi\n=end\n', 0, '=end'), 0)
		self.assertGreater(CommentScanners.scan_ps_herestring('@"\nhi\n"@\n', 0, '"'), 0)
		self.assertGreater(CommentScanners.scan_triple_quote('"""hi"""', 0, '"'), 0)
		self.assertTrue(CommentDiff.is_whitespace_only('a.py', 'a = 1\n', 'a = 1  \n'))
		lang = CommentDiff.detect_language('bin/run', content='#!/usr/bin/env python3\nx = 1\n')
		self.assertEqual('python', lang)
		self.assertTrue(CodeClassifier.has_shebang('script', '#!/usr/bin/env python3\n'))
		self.assertEqual('a/b', CodeClassifier.norm_posix('a\\b'))
		self.assertTrue(CommandInspector('go test ./...').classify_test_command()['is_test_cmd'])
		self.assertTrue(CommandInspector('cargo test --workspace').classify_test_command()['is_test_cmd'])
		self.assertTrue(CommandInspector('gradle test --tests Foo').classify_test_command()['is_test_cmd'])
		self.assertTrue(CommandInspector('python -m unittest discover -p test_a.py').classify_test_command()['is_test_cmd'])
		self.assertTrue(CommandInspector('python tests/test_a.py').classify_test_command()['is_test_cmd'])
		self.assertTrue(CommandInspector.shell_write_targets('Set-Content -Path a.py -Value @"\nx = 1\n"@'))
		self.assertTrue(CommandInspector.shell_code_write_targets('echo "x" > a.py'))
		self.assertTrue(CommandInspector.shell_test_delete_targets('rm tests/test_a.py'))
	# @used-by :mod:`unittest`
	def test_diff_contract_executability_and_coverage_end_to_end(self) -> None:
		from Df.Harness.Tdd.CodeClassifier import CodeClassifier
		from Df.Harness.Tdd.CommentDiff import CommentDiff
		from Df.Harness.Tdd.DiffContract import DiffContract
		from Df.Harness.Tdd.DiffCoverage import DiffCoverage
		from Df.Harness.Tdd.DiffExecutability import DiffExecutability
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			_git(repo, 'init')
			_git(repo, 'config', 'user.email', 't@example.com')
			_git(repo, 'config', 'user.name', 'T')
			(repo / 'scripts').mkdir()
			(repo / 'tests').mkdir()
			(repo / 'scripts/mod.py').write_text('def base_fn():\n\treturn 1\n', encoding='utf-8')
			(repo / 'tests/test_mod.py').write_text('import sys, unittest\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))\nimport mod\nclass T(unittest.TestCase):\n\tdef test_base(self):\n\t\tself.assertEqual(1, mod.base_fn())\n', encoding='utf-8')
			_git(repo, 'add', '.')
			_git(repo, 'commit', '-m', 'init')
			self.assertEqual(1, CodeClassifier.count_repo_test_files(repo))
			self.assertEqual(repo, CodeClassifier.resolve_code_scope(repo / 'scripts/mod.py'))
			self.assertIsNotNone(CodeClassifier.resolve_code_scope(repo / '\ua616/data/worktrees/gone/scripts/mod.py'))
			head_txt = CommentDiff.git_read_text(repo, ['show', 'HEAD:scripts/mod.py']) or ''
			self.assertIn('base_fn', head_txt)
			(repo / 'scripts/mod.py').write_text('def base_fn():\n\treturn 1\ndef added_fn():\n\treturn 2\n', encoding='utf-8')
			(repo / 'tests/test_mod.py').write_text('import sys, unittest\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))\nimport mod\nclass T(unittest.TestCase):\n\tdef test_added(self):\n\t\tself.assertEqual(2, mod.added_fn())\n', encoding='utf-8')
			self.assertFalse(DiffExecutability.is_git_path_non_executable(repo, 'scripts/mod.py'))
			self.assertIsNone(DiffContract.check_touched_mixed_commit_warning(repo, ['scripts/mod.py']))
			self.assertTrue(DiffCoverage.verify_repo(repo)['valid'])
			self.assertTrue(DiffCoverage.enrich_tdd_check_report(repo, 'primary', 'tk', {'touched_files': [str(repo / 'scripts/mod.py')], 'tdd_events': []}, {'verified': True})['valid'])
			_git(repo, 'checkout', '-b', 'feat')
			_git(repo, 'add', '.')
			_git(repo, 'commit', '-m', 'feat')
			self.assertTrue(DiffCoverage.verify_worktree(repo, 'master' if 0 == _git(repo, 'rev-parse', '--verify', 'master').returncode else 'main')['valid'])
if '__main__' == __name__:
	unittest.main()
