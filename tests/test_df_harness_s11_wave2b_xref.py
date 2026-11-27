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
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`unittest`
class DfHarnessS11Wave2bXrefTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_java_xref_classes_tokenize_index_graph_and_sync(self) -> None:
		from Df.Harness.Xref.Java.Graph import Graph as JavaGraph
		from Df.Harness.Xref.Java.Lexer import Lexer as JavaLexer
		from Df.Harness.Xref.Java.Model import Model as JavaModel
		from Df.Harness.Xref.Java.Syncer import Syncer as JavaSyncer
		from Df.Harness.Xref.Java.Tags import Tags as JavaTags
		src = 'package demo;\npublic class Base { public void run() {} }\n'
		child = 'package demo;\npublic class Child extends Base {\n\t@Override\n\tpublic void run() { helper(); }\n\tprivate void helper() {}\n}\n'
		self.assertTrue(JavaLexer(src).tokenize())
		jdoc = ['/**', ' * - @used-by {@link Child#run()}', ' */', 'private void helper() {}']
		self.assertTrue(JavaTags(jdoc, 4, 'Child.java').parse_javadoc_block()['used_by'])
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / 'Base.java').write_text(src, encoding='utf-8')
			(root / 'Child.java').write_text(child, encoding='utf-8')
			idx = JavaModel(root).build_repo_index()
			self.assertIn('demo.Child#helper()', idx['symbols'])
			graph = JavaGraph(idx).build()
			self.assertIn('demo.Child#run()', graph['demo.Child#helper()'])
			sync_res = JavaSyncer(root).sync(apply=True)
			self.assertTrue(sync_res['valid'])
			self.assertGreaterEqual(sync_res['changed_count'], 1)
			chk = JavaSyncer.check_repo(root)
			self.assertIsInstance(chk['issues'], list)
	# @used-by :mod:`unittest`
	def test_js_xref_classes_tokenize_imports_graph_and_sync(self) -> None:
		from Df.Harness.Xref.Js.Graph import Graph as JsGraph
		from Df.Harness.Xref.Js.Imports import Imports as JsImports
		from Df.Harness.Xref.Js.Lexer import Lexer as JsLexer
		from Df.Harness.Xref.Js.Model import Model as JsModel
		from Df.Harness.Xref.Js.Syncer import Syncer as JsSyncer
		from Df.Harness.Xref.Js.Tags import Tags as JsTags
		lib_js = 'export function helper() { return 1; }\n'
		app_js = "import { helper } from './lib.js';\nexport function main() { return helper(); }\n"
		toks = JsLexer(app_js).tokenize()
		imps: dict[str, tuple[str, str]] = {}
		self.assertGreater(JsImports(toks).parse_esm_import(0, imps), 0)
		self.assertIn('helper', imps)
		jlines = ['/**', ' * @used-by CLI', ' */', 'export function helper() { return 1; }']
		self.assertTrue(JsTags(jlines, 4, 'lib.js').parse_jsdoc_block()['has_block'])
		self.assertEqual([], JsSyncer.check_file_local('lib.js', '\n'.join(jlines) + '\n'))
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / 'lib.js').write_text(lib_js, encoding='utf-8')
			(root / 'app.js').write_text(app_js, encoding='utf-8')
			idx = JsModel(root).build_repo_index()
			graph = JsGraph(idx).build()
			self.assertIn('app.js::main', graph['lib.js::helper'])
			sync_res = JsSyncer(root).sync(apply=True)
			self.assertTrue(sync_res['valid'])
			self.assertGreaterEqual(sync_res['changed_count'], 1)
	# @used-by :mod:`unittest`
	def test_python_xref_classes_and_engine_roundtrip(self) -> None:
		from Df.Harness.Xref.Engine import Engine
		from Df.Harness.Xref.Python.Graph import Graph as PyGraph
		from Df.Harness.Xref.Python.Model import Model as PyModel
		from Df.Harness.Xref.Python.Overrides import Overrides as PyOverrides
		from Df.Harness.Xref.Python.Syncer import Syncer as PySyncer
		from Df.Harness.Xref.Python.Tags import Tags as PyTags
		plines = ['# @used-by CLI', '# @see :meth:`Base.ping()`', 'def ping(self) -> int:', '\treturn 2']
		self.assertTrue(PyTags(plines, 3, 'scripts/child.py').parse_header_block()['see'])
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / 'scripts').mkdir()
			(root / 'scripts/base.py').write_text('# @used-by unused\nclass Base:\n\t# @used-by unused\n\tdef ping(self) -> int:\n\t\treturn 1\n', encoding='utf-8')
			(root / 'scripts/child.py').write_text('from base import Base\nclass Child(Base):\n\t# @used-by CLI\n\tdef ping(self) -> int:\n\t\treturn 2\n', encoding='utf-8')
			idx = PyModel(root).build_repo_index()
			cfile = idx['files']['scripts/child.py']
			self.assertEqual('base.Base.ping', PyOverrides(cfile, cfile['classes']['Child'], idx).find_overridden_method('ping'))
			self.assertIsInstance(PyGraph(idx).build(), dict)
			sync_res = PySyncer(root).sync(apply=True)
			self.assertTrue(sync_res['valid'])
			chk = Engine(root).check(lang='python')
			self.assertTrue(chk['valid'], chk['issues'])
			self.assertIn('xref (python):', Engine.format_text(chk))
if '__main__' == __name__:
	unittest.main()
