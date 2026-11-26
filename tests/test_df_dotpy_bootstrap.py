# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import importlib
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.issue_comment_gate import check_issue_comment_violations
from agent_tools.issues.git_read_cache import RepoReadCache
from agent_tools.shell_audit import extract_issue_urls, is_code_file
from agent_tools.tdd.classifier import classify_code_path
from agent_tools.tdd.comment_diff import detect_comment_language
from agent_tools.tdd.diff_coverage import _prod_match_tokens
from agent_tools.xref.python_model import index_python_file, module_name_for_rel
from agent_tools.xref.python_sync import check_python_repo
from agent_tools.xref_gate import check_file_xref_violations
# 2026-11-26 "Add Df package dot-py bootstrap and dot-py support across Harness gates": https://github.com/dmitry-ai/harness/issues/320
class DfDotPyBootstrapTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_df_bootstrap_loads_dotpy_packages_and_sibling_modules(self) -> None:
		import Df
		with tempfile.TemporaryDirectory() as td:
			pkg_root = Path(td) / 'DfTemp'
			(pkg_root / 'Core/lib/array/select').mkdir(parents=True)
			(pkg_root / 'Qa/Trace').mkdir(parents=True)
			(pkg_root / 'Core/lib/array/select/.py').write_text('def dfa(a, k):\n\treturn a[k]\n', encoding='utf-8')
			(pkg_root / 'Core/lib/array/select/strict.py').write_text('from DfTemp.Core.lib.array.select import dfa\ndef dfa_strict(a, k):\n\treturn dfa(a, k)\n', encoding='utf-8')
			(pkg_root / 'Qa/Trace/.py').write_text('class Trace:\n\tdef count(self):\n\t\treturn 3\n', encoding='utf-8')
			(pkg_root / 'Qa/Trace/Frame.py').write_text('class Frame:\n\tdef line(self):\n\t\treturn 9\n', encoding='utf-8')
			finder = Df.DotPyFinder('DfTemp', pkg_root)
			sys.meta_path.insert(0, finder)
			sys.path.insert(0, td)
			try:
				sel = importlib.import_module('DfTemp.Core.lib.array.select')
				strict = importlib.import_module('DfTemp.Core.lib.array.select.strict')
				trace_mod = importlib.import_module('DfTemp.Qa.Trace')
				frame_mod = importlib.import_module('DfTemp.Qa.Trace.Frame')
				self.assertEqual(11, sel.dfa({'x': 11}, 'x'))
				self.assertEqual(22, strict.dfa_strict({'y': 22}, 'y'))
				self.assertEqual(3, trace_mod.Trace().count())
				self.assertEqual(9, frame_mod.Frame().line())
			finally:
				sys.meta_path.remove(finder)
				sys.path.remove(td)
				for key in [k for k in sys.modules if 'DfTemp' == k or k.startswith('DfTemp.')]:
					del sys.modules[key]
	# @used-by :mod:`unittest`
	def test_gates_and_classifiers_recognize_dotpy_files(self) -> None:
		rel = 'scripts/Df/Core/lib/array/select/.py'
		self.assertEqual('production', classify_code_path(rel))
		self.assertEqual('python', detect_comment_language(rel))
		self.assertTrue(is_code_file(rel))
		tokens = _prod_match_tokens([rel])
		self.assertIn('select', tokens)
		self.assertNotIn('.py', tokens)
		xref_errs = check_file_xref_violations(rel, 'def dfa(a):\n\treturn a\n')
		self.assertTrue(any('missing @used-by' in e for e in xref_errs))
		dup_auth = '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\ndef dfa(a):\n\treturn a\n'
		cmt_errs = check_issue_comment_violations(rel, dup_auth)
		self.assertTrue(any('DUPLICATE_AUTHOR_HEADER' in e for e in cmt_errs))
	# @used-by :mod:`unittest`
	def test_git_read_cache_detects_issue_url_in_untracked_dotpy(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			subprocess.run(['git', 'init', '-q'], cwd=str(repo), stdin=subprocess.DEVNULL, timeout=15, check=True)
			dotpy = repo / 'scripts/Df/Core/lib/array/select/.py'
			dotpy.parent.mkdir(parents=True)
			url = 'https://github.com/dmitry-ai/harness/issues/320'
			dotpy.write_text(f'# 2026-11-26 "Dotpy": {url}\ndef dfa(a):\n\treturn a\n', encoding='utf-8')
			hits = RepoReadCache().dirty_referencing_issue(repo, url, frozenset({'.py'}), extract_issue_urls)
			self.assertEqual(['scripts/Df/Core/lib/array/select/.py'], hits)
	# @used-by :mod:`unittest`
	def test_xref_python_model_and_check_support_dotpy_packages(self) -> None:
		rel = 'scripts/Df/Core/lib/array/select/.py'
		self.assertEqual('Df.Core.lib.array.select', module_name_for_rel(rel, ('scripts',)))
		finfo = index_python_file(rel, 'Df.Core.lib.array.select', 'def dfa(a):\n\treturn a\n')
		self.assertTrue(finfo['is_pkg'])
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'scripts/Df/Core/lib/array/select').mkdir(parents=True)
			(root / rel).write_text('# @used-by :func:`consumer.run()`\ndef dfa(a):\n\treturn a\n', encoding='utf-8')
			(root / 'scripts/consumer.py').write_text('from Df.Core.lib.array.select import dfa\n# @used-by unused\ndef run():\n\treturn dfa(1)\n', encoding='utf-8')
			res = check_python_repo(root)
			self.assertTrue(res['valid'], res)
if '__main__' == __name__:
	unittest.main()
