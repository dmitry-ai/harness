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
_JAVA_BASE = 'package demo;\npublic class Base {\n\t/** @used-by unused */\n\tpublic void work(final String a, int b) {}\n\t/** @used-by unused */\n\tpublic static void util() {}\n}\n'
_JAVA_SUB = 'package demo;\npublic enum Kind {\n\tALPHA(1), BETA(2);\n\tprivate final int code;\n\tKind(int code) { this.code = code; }\n\t/** @used-by unused */\n\tpublic int getCode() { return code; }\n}\npublic class Sub extends Base {\n\t/** @used-by unused\n\t * @override\n\t * @see Base#work(String, int) */\n\t@Override\n\tpublic void work(String a, int b) {\n\t\tsuper.work(a, b);\n\t\tBase.util();\n\t\tKind.ALPHA.getCode();\n\t\tRunnable r = new Runnable() {\n\t\t\t/** @used-by unused\n\t\t\t * @override\n\t\t\t * @see java.lang.Runnable#run() */\n\t\t\t@Override\n\t\t\tpublic void run() { Base.util(); }\n\t\t};\n\t\tr.run();\n\t}\n}\n'
_JS_LIB = '/** @used-by unused */\nexport class Base {\n\t/** @used-by unused */\n\tping(v) { return `ok:${v + 1}`; }\n}\n/** @used-by unused */\nexport const helper = (x) => `val:${x}`;\nconst fnExpr = function(y) { return helper(y); };\nmodule.exports = { Base, helper, fnExpr };\nexport { fnExpr };\n'
_JS_APP = "const { Base, helper } = require('./lib');\nimport * as ns from './lib.js';\n/** @used-by unused */\nclass Sub extends Base {\n\t/** @used-by unused\n\t * @override\n\t * @see {@link import('./lib').Base#ping} */\n\tping(v) {\n\t\tconst a = new ns.Base().ping(v);\n\t\tconst b = new Base().ping(v);\n\t\tconst c = require('./lib').helper(a);\n\t\treturn helper(b + c);\n\t}\n}\nconst run = () => { const s = new Sub(); return s.ping(1); };\nrun();\n"
_PY_LIB = 'from contextlib import nullcontext\nfrom typing import override\nimport unittest\nclass Helper:\n\t# @used-by unused\n\tdef work(self):\n\t\treturn 1\nclass Base:\n\t# @used-by unused\n\tdef step(self):\n\t\treturn 2\nclass Child(Base):\n\t# @used-by unused\n\tdef __init__(self):\n\t\tself.h = Helper()\n\t# @used-by unused\n\t# @see :meth:`Base.step()`\n\t@override\n\tdef step(self):\n\t\twith nullcontext():\n\t\t\tval = super().step() + self.h.work()\n\t\treturn val\nclass Case(unittest.TestCase):\n\t# @used-by unused\n\t# @see :meth:`unittest.TestCase.setUp()`\n\t@override\n\tdef setUp(self):\n\t\tsuper().setUp()\nALIAS = Helper\nif True:\n\timport json\n__all__ = ["Helper", "Base", "Child", "Case", "ALIAS"]\n'
_PY_CALLER = 'import lib\n# @used-by unused\ndef main():\n\tc = lib.Child()\n\treturn c.step()\n'
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`unittest`
class DfHarnessS11Wave2bXrefCovTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_java_xref_covers_enums_anon_classes_overrides_and_external_tags(self) -> None:
		from Df.Harness.Xref.Engine import Engine
		from Df.Harness.Xref.Java.Syncer import Syncer as JavaSyncer
		from Df.Harness.Xref.Java.Tags import Tags as JavaTags
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			src = root / 'src/demo'
			src.mkdir(parents=True)
			(src / 'Base.java').write_text(_JAVA_BASE, encoding='utf-8')
			(src / 'Sub.java').write_text(_JAVA_SUB, encoding='utf-8')
			sync_res = Engine.sync_repo(root, lang='java', apply=True)
			self.assertTrue(sync_res['valid'])
			chk = JavaSyncer.check_repo(root)
			self.assertIn('issues', chk)
			loc = JavaSyncer.check_file_local('src/demo/Base.java', _JAVA_BASE)
			self.assertIsInstance(loc, list)
			ext_ok = JavaTags.is_valid_external('src/demo/Base.java', root)
			ext_bad = JavaTags.is_valid_external('unknown.pkg.Missing#nope()', root)
			self.assertTrue(ext_ok)
			self.assertFalse(ext_bad)
	# @used-by :mod:`unittest`
	def test_js_xref_covers_classes_arrows_templates_imports_and_sync(self) -> None:
		from Df.Harness.Xref.Engine import Engine
		from Df.Harness.Xref.Js.Model import Model as JsModel
		from Df.Harness.Xref.Js.Syncer import Syncer as JsSyncer
		from Df.Harness.Xref.Js.Tags import Tags as JsTags
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			(root / 'lib.js').write_text(_JS_LIB, encoding='utf-8')
			(root / 'app.js').write_text(_JS_APP, encoding='utf-8')
			sync_res = Engine.sync_repo(root, lang='js', apply=True)
			self.assertTrue(sync_res['valid'])
			chk = JsSyncer.check_repo(root)
			self.assertTrue(chk['valid'], chk)
			idx = JsModel(root).build_repo_index()
			ext_ok = JsTags.is_valid_external('https://nodejs.org/api/fs.html', root)
			res = JsTags.resolve_link("import('./lib').Base#ping", '', 'app.js', idx)
			self.assertTrue(ext_ok)
			self.assertTrue(res[0])
	# @used-by :mod:`unittest`
	def test_python_xref_covers_all_exports_with_overrides_and_stdlib_tags(self) -> None:
		from Df.Harness.Xref.Engine import Engine
		from Df.Harness.Xref.Python.Syncer import Syncer as PySyncer
		from Df.Harness.Xref.Python.Tags import Tags as PyTags
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			pkg = root / 'scripts'
			pkg.mkdir(parents=True)
			(pkg / 'lib.py').write_text(_PY_LIB, encoding='utf-8')
			(pkg / 'caller.py').write_text(_PY_CALLER, encoding='utf-8')
			sync_res = Engine.sync_repo(root, lang='python', apply=True)
			self.assertTrue(sync_res['valid'])
			chk = PySyncer.check_repo(root)
			self.assertTrue(chk['valid'], chk)
			std_ok = PyTags.resolve_stdlib_symbol('unittest.TestCase.setUp')
			std_bad = PyTags.resolve_stdlib_symbol('nonexistent_mod_xyz.Missing.fn')
			self.assertTrue(std_ok)
			self.assertFalse(std_bad)
if '__main__' == __name__:
	unittest.main()
