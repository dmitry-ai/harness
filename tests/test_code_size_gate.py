# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = HARNESS_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import links
from agent_tools.git_gate import GitRepoGate
import check_markdown_slop
# 2026-11-23
# "Enforce AST function and file SLOC ratchet gate in PreToolUse and Git pre-commit":
# https://github.com/dmitry-ai/harness/issues/161
class CodeSizeGateTests(unittest.TestCase):
	# @used-by :meth:`CodeSizeGateTests.test_git_pre_commit_blocks_oversized_python_file()`
	# @used-by :meth:`CodeSizeGateTests.test_legacy_ratchet_allows_holding_or_shrinking_blocks_growth()`
	# @used-by :meth:`CodeSizeGateTests.test_new_file_and_function_limits_and_test_soft_limits()`
	# @used-by :meth:`CodeSizeGateTests.test_override_decorator_and_typing_import_excluded_from_sloc()`
	# @used-by :meth:`CodeSizeGateTests.test_pre_tool_use_gate_rejects_oversized_python_write()`
	def _make_func(self, name: str, body_lines: int) -> str:
		lines = [f'def {name}(x):']
		for i in range(max(1, body_lines - 1)):
			lines.append(f'\tx = x + {i}')
		lines.append('\treturn x')
		return '\n'.join(lines) + '\n'
	# @used-by :meth:`CodeSizeGateTests.test_git_pre_commit_blocks_oversized_python_file()`
	# @used-by :meth:`CodeSizeGateTests.test_pre_tool_use_gate_rejects_oversized_python_write()`
	def _make_git_repo(self, root: Path) -> None:
		subprocess.run(['git', '-C', str(root), 'init'], capture_output=True, check=True)
		subprocess.run(['git', '-C', str(root), 'config', 'user.email', 'test@example.com'], capture_output=True, check=True)
		subprocess.run(['git', '-C', str(root), 'config', 'user.name', 'Test'], capture_output=True, check=True)
	# @used-by :mod:`unittest`
	def test_comments_docstrings_and_declarative_tables_excluded_from_sloc(self):
		from agent_tools.code_size_gate import analyze_python_source, check_python_size_violations
		table_lines = '\n'.join([f"\t'k{i}': {i}," for i in range(40)])
		src = (
			'# https://github.com/dmitry-ai/harness/issues/161\n'
			+ ('# comment line\n' * 30)
			+ '"""Module docstring\n' + ('doc line\n' * 30) + '"""\n'
			+ 'TABLE = {\n' + table_lines + '\n}\n'
			+ 'def helper(x):\n\t"""Func doc\n\tline 2\n\t"""\n\treturn TABLE.get(x, 0)\n'
		)
		metrics = analyze_python_source(src)
		self.assertLessEqual(metrics['file_sloc'], 15)
		self.assertLessEqual(metrics['functions']['helper']['sloc'], 5)
		errs = check_python_size_violations(Path('scripts/mod.py'), src)
		self.assertEqual(errs, [])
	# @used-by :mod:`unittest`
	def test_git_pre_commit_blocks_oversized_python_file(self):
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._make_git_repo(repo)
			src_file = repo / 'scripts/huge.py'
			src_file.parent.mkdir(parents=True, exist_ok=True)
			src_file.write_text('# https://github.com/dmitry-ai/harness/issues/161\n' + self._make_func('too_big', 25), encoding='utf-8')
			test_file = repo / 'tests/test_huge.py'
			test_file.parent.mkdir(parents=True, exist_ok=True)
			test_file.write_text('# https://github.com/dmitry-ai/harness/issues/161\nimport unittest\nclass T(unittest.TestCase):\n\tdef test_x(self):\n\t\tself.assertTrue(True)\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', '--', 'scripts/huge.py', 'tests/test_huge.py'], capture_output=True, check=True)
			gate = GitRepoGate(repo)
			with self.assertRaises(ValueError) as ctx:
				gate.verify_code_size_ratchet(['scripts/huge.py', 'tests/test_huge.py'], use_index=True)
			self.assertIn('SLOC', str(ctx.exception))
	# @used-by :mod:`unittest`
	def test_legacy_ratchet_allows_holding_or_shrinking_blocks_growth(self):
		from agent_tools.code_size_gate import check_python_size_violations
		base_src = self._make_func('legacy_fn', 30)
		same_src = base_src + '# extra comment only\n'
		shrunk_src = self._make_func('legacy_fn', 28)
		grown_src = self._make_func('legacy_fn', 31)
		self.assertEqual(check_python_size_violations(Path('scripts/old.py'), same_src, baseline_source=base_src), [])
		self.assertEqual(check_python_size_violations(Path('scripts/old.py'), shrunk_src, baseline_source=base_src), [])
		grown_errs = check_python_size_violations(Path('scripts/old.py'), grown_src, baseline_source=base_src)
		self.assertTrue(any(('ratchet' in e.lower() or 'legacy_fn' in e for e in grown_errs)))
	# @used-by :mod:`unittest`
	def test_mccabe_complexity_and_semicolon_anti_gaming(self):
		from agent_tools.code_size_gate import check_python_size_violations
		branchy = (
			'def complex_fn(a):\n'
			'\tr = 0\n'
			'\tif a == 1: r = 1\n'
			'\tif a == 2: r = 2\n'
			'\tif a == 3: r = 3\n'
			'\tif a == 4: r = 4\n'
			'\tif a == 5: r = 5\n'
			'\tif a == 6: r = 6\n'
			'\tif a == 7: r = 7\n'
			'\tif a == 8: r = 8\n'
			'\treturn r\n'
		)
		errs_c = check_python_size_violations(Path('scripts/comp.py'), branchy)
		self.assertTrue(any(('McCabe' in e or 'complexity' in e.lower() for e in errs_c)))
		semi = 'def cram(a):\n\tx = a + 1; y = x + 2; return y\n'
		errs_s = check_python_size_violations(Path('scripts/cram.py'), semi)
		self.assertTrue(any((';' in e or 'semicolon' in e.lower() for e in errs_s)))
		safe_str = "def ok():\n\treturn 'a; b; c'\n"
		self.assertEqual(check_python_size_violations(Path('scripts/ok.py'), safe_str), [])
	# @used-by :mod:`unittest`
	def test_new_file_and_function_limits_and_test_soft_limits(self):
		from agent_tools.code_size_gate import check_python_size_violations
		big_fn = self._make_func('oversized', 22)
		errs_prod = check_python_size_violations(Path('scripts/mod.py'), big_fn)
		self.assertTrue(any(('oversized' in e for e in errs_prod)))
		self.assertEqual(check_python_size_violations(Path('tests/test_mod.py'), big_fn), [])
		huge_file = ''.join((self._make_func(f'fn_{i}', 10) for i in range(32)))
		errs_file = check_python_size_violations(Path('scripts/big.py'), huge_file)
		self.assertTrue(any(('300' in e for e in errs_file)))
		self.assertEqual(check_python_size_violations(Path('tests/test_big.py'), huge_file), [])
	# 2026-11-26
	# "Codify navigable cross-reference standards and override SLOC exemption":
	# https://github.com/dmitry-ai/harness/issues/286
	# @used-by :mod:`unittest`
	def test_override_decorator_and_typing_import_excluded_from_sloc(self):
		from agent_tools.code_size_gate import analyze_python_source, check_python_size_violations
		base_src = 'class Base:\n\tdef run(self):\n\t\treturn 1\nclass Sub(Base):\n\tdef run(self):\n\t\treturn 2\n'
		ov_src = (
			'from typing import override\n'
			'class Base:\n\tdef run(self):\n\t\treturn 1\n'
			'class Sub(Base):\n'
			'\t# @see :meth:`Base.run()`\n'
			'\t@override\n'
			'\tdef run(self):\n\t\treturn 2\n'
		)
		base_m = analyze_python_source(base_src)
		ov_m = analyze_python_source(ov_src)
		self.assertEqual(base_m['file_sloc'], ov_m['file_sloc'])
		self.assertEqual(base_m['functions']['Sub.run']['sloc'], ov_m['functions']['Sub.run']['sloc'])
		big_base = ''.join((self._make_func(f'fn_{i}', 10) for i in range(32))) + base_src
		big_ov = 'from typing import override\n' + ''.join((self._make_func(f'fn_{i}', 10) for i in range(32))) + ov_src.replace('from typing import override\n', '')
		self.assertEqual(check_python_size_violations(Path('scripts/legacy.py'), big_ov, baseline_source=big_base), [])
	# @used-by :mod:`unittest`
	def test_pre_tool_use_gate_rejects_oversized_python_write(self):
		import check_rules_and_server_gate as gate_mod
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._make_git_repo(repo)
			target = repo / 'scripts/bad.py'
			err = gate_mod.check_code_size_gate('write_file', {'Path': str(target), 'Content': self._make_func('giant', 25)}, {'cwd': str(repo)})
			self.assertIsNotNone(err)
			self.assertIn('giant', err)
			ok_err = gate_mod.check_code_size_gate('write_file', {'Path': str(target), 'Content': self._make_func('tiny', 5)}, {'cwd': str(repo)})
			self.assertIsNone(ok_err)
			self.assertTrue(callable(gate_mod.check_schedule_gate))
	# @used-by :mod:`unittest`
	def test_rules_doc_codifies_code4_size_ratchet(self):
		rule_doc = HARNESS_ROOT / 'rules/11-code-formatting.md'
		text = rule_doc.read_text(encoding='utf-8')
		self.assertEqual(links.validate_file(rule_doc, local_anchors=True, readable_links=True), [])
		self.assertEqual(check_markdown_slop.markdown_slop_issues(text), [])
		for token in ('## CODE-4', '20', '300', 'McCabe', 'ratchet'):
			self.assertIn(token, text)
if '__main__' == __name__:
	unittest.main()
