# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :mod:`unittest`
class DfCoreQaS10Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_sha256_json_io_and_time_helpers(self) -> None:
		from Df.Core.lib.json_io import df_json_bytes, df_json_dict_load
		from Df.Core.lib.sha256 import df_sha256, df_sha256_file, df_sha256_text
		from Df.Core.lib.time import df_utc_iso
		with tempfile.TemporaryDirectory() as tmp:
			p = Path(tmp) / 'data.json'
			raw = df_json_bytes({'b': 1, 'a': 2})
			self.assertEqual(b'{"a":2,"b":1}\n', raw)
			pretty = df_json_bytes({'a': 1}, indent=2)
			self.assertIn(b'\n  "a": 1\n', pretty)
			p.write_bytes(raw)
			self.assertEqual(df_sha256(raw), df_sha256_file(p))
			self.assertEqual(df_sha256(b'hello'), df_sha256_text('hello'))
			self.assertEqual({'a': 2, 'b': 1}, df_json_dict_load(p))
			bad = Path(tmp) / 'bad.json'
			bad.write_text('[1, 2]', encoding='utf-8')
			self.assertIsNone(df_json_dict_load(bad))
			self.assertIsNone(df_json_dict_load(Path(tmp) / 'missing.json'))
		iso = df_utc_iso()
		self.assertTrue(iso.endswith('+00:00'))
	# @used-by :mod:`unittest`
	def test_fs_and_git_helpers(self) -> None:
		from Df.Core.lib.fs import df_path_inside, df_path_posix, df_path_suffix, df_stat_sig, df_uri_file_decode
		from Df.Core.lib.git import df_git_read_text, df_git_root
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			child = base / 'sub' / '.py'
			child.parent.mkdir(parents=True)
			child.write_bytes(b'x = 1\n')
			self.assertTrue(df_path_inside(child, base))
			self.assertFalse(df_path_inside(base.parent, child))
			self.assertEqual('a/b/c.py', df_path_posix('a\\b\\c.py'))
			self.assertEqual('.py', df_path_suffix(child))
			self.assertEqual('.md', df_path_suffix('README.MD'))
			sig = df_stat_sig(child)
			self.assertIsNotNone(sig)
			self.assertEqual(6, sig[1])
			self.assertIsNone(df_stat_sig(base / 'absent.txt'))
			self.assertEqual('C:/work/test file.md', df_uri_file_decode('file:///C:/work/test%20file.md'))
			self.assertIsNone(df_git_root(base))
		self.assertEqual(WT_ROOT, df_git_root(WT_ROOT / 'scripts'))
		self.assertEqual('true', (df_git_read_text(WT_ROOT, 'rev-parse', '--is-inside-work-tree') or '').strip())
	# @used-by :mod:`unittest`
	def test_text_source_and_strict_validation_helpers(self) -> None:
		from Df.Core.lib.text.source import df_line_indent, df_match_delim, df_text_rewrite_pairs
		from Df.Qa.lib.validation.check_strict import df_is_int_strict, df_is_sne
		self.assertEqual('\t  ', df_line_indent('\t  def f():'))
		toks = [('punct', '(', 1), ('word', 'a', 1), ('punct', '(', 1), ('punct', ')', 1), ('punct', ')', 1)]
		self.assertEqual(4, df_match_delim(toks, 0, '(', ')'))
		self.assertEqual('NEW/path/NEW', df_text_rewrite_pairs('old/path/OLD', [('old', 'NEW')]))
		self.assertTrue(df_is_sne('ok'))
		self.assertFalse(df_is_sne('   '))
		self.assertFalse(df_is_sne(None))
		self.assertTrue(df_is_int_strict(7))
		self.assertFalse(df_is_int_strict(True))
		self.assertFalse(df_is_int_strict('7'))
	# @used-by :mod:`unittest`
	def test_harness_callers_delegate_to_new_core_and_qa_helpers(self) -> None:
		from agent_tools import admission, code_size_gate, project_card, project_drift, project_rename_state, python_integrity, review_alignment, shadow_replay_clone, xref_gate
		from agent_tools.xref import java_lex, java_model, js_lex, js_model
		self.assertEqual(admission._digest(b'abc'), project_card._digest(b'abc'))
		self.assertEqual(b'{"a":1}\n', admission._bytes({'a': 1}))
		self.assertTrue(review_alignment._nonempty('hi'))
		self.assertFalse(review_alignment._nonempty('  '))
		self.assertEqual(WT_ROOT, code_size_gate._find_git_root(WT_ROOT / 'scripts'))
		self.assertEqual('.py', xref_gate._path_suffix(Path('.py')))
		self.assertEqual('true', (python_integrity._git_read_text(WT_ROOT, 'rev-parse', '--is-inside-work-tree') or '').strip())
		self.assertEqual('\t', java_model._line_indent(['\tvoid f()'], 1))
		self.assertEqual('\t', js_model._line_indent(['\tfunction f()'], 1))
		toks = [('punct', '{', 1), ('punct', '}', 1)]
		self.assertEqual(1, java_lex.match_delim(toks, 0, '{', '}'))
		self.assertEqual(1, js_lex.match_delim(toks, 0, '{', '}'))
		self.assertEqual('B/x', project_rename_state._rewrite_text('a/x', [('A', 'B')]))
		self.assertEqual('B/x', shadow_replay_clone._rewrite_path_text('a/x', [('A', 'B')]))
		self.assertIsNone(project_drift._load_json_dict(WT_ROOT / 'nonexistent_x.json'))
if '__main__' == __name__:
	unittest.main()