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
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
class JavaXrefTests(unittest.TestCase):
	# @used-by :meth:`JavaXrefTests.test_java_anonymous_class_overloads_and_plugin_xml()`
	# @used-by :meth:`JavaXrefTests.test_java_rejects_bare_used_by_and_uses_block_tags()`
	# @used-by :meth:`JavaXrefTests.test_java_sync_and_check_overrides_records_and_uses()`
	def _write(self, root: Path, rel: str, content: str) -> Path:
		p = root / rel
		p.parent.mkdir(parents=True, exist_ok=True)
		p.write_text(content, encoding='utf-8')
		return p
	# @used-by :mod:`unittest`
	def test_java_anonymous_class_overloads_and_plugin_xml(self) -> None:
		from agent_tools.xref.java_sync import check_java_repo, sync_java_repo
		src = (
			'package demo;\n'
			'import java.lang.Runnable;\n'
			'public final class Service {\n'
			'\t/**\n\t * - @used-by build.ps1\n\t */\n'
			'\tpublic static Runnable create() {\n'
			'\t\twork();\n'
			'\t\treturn new Runnable() {\n'
			'\t\t\t@Override\n'
			'\t\t\tpublic void run() { work("ok"); }\n'
			'\t\t};\n'
			'\t}\n'
			'\tpublic static void work() { work("def"); }\n'
			'\tpublic static void work(String v) {}\n'
			'}\n'
		)
		pxml = '<idea-plugin><extensions><ep implementation="demo.Service"/></extensions></idea-plugin>\n'
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write(repo, 'src/main/java/demo/Service.java', src)
			self._write(repo, 'src/main/resources/META-INF/plugin.xml', pxml)
			sync_java_repo(repo, apply=True)
			txt = (repo / 'src/main/java/demo/Service.java').read_text(encoding='utf-8')
			self.assertIn('* @see Runnable#run()', txt)
			self.assertIn('* - @used-by {@link Service#create()}', txt)
			self.assertIn('* - @used-by {@link Service#work()}', txt)
			res = check_java_repo(repo)
			self.assertTrue(res['valid'], res['issues'])
	# @used-by :mod:`unittest`
	def test_java_rejects_bare_used_by_and_uses_block_tags(self) -> None:
		from agent_tools.xref.java_sync import check_java_repo
		bad_java = (
			'package demo;\n'
			'public final class Bad {\n'
			'\t/**\n\t * @used-by {@link Bad#run()}\n\t * @uses {@link Bad#run()}\n\t */\n'
			'\tpublic void helper() {}\n'
			'\t/**\n\t * - @used-by build.ps1\n\t */\n'
			'\tpublic void run() { helper(); }\n'
			'}\n'
		)
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write(repo, 'src/main/java/demo/Bad.java', bad_java)
			res = check_java_repo(repo)
			self.assertFalse(res['valid'])
			joined = '\n'.join(res['issues'])
			self.assertIn('- @used-by', joined)
			self.assertIn('- @uses', joined)
	# @used-by :mod:`unittest`
	def test_java_sync_and_check_overrides_records_and_uses(self) -> None:
		from agent_tools.xref.java_sync import check_java_repo, sync_java_repo
		iface = 'package demo;\npublic interface Worker {\n\tvoid execute(String name);\n}\n'
		impl = (
			'package demo;\n'
			'public final class Impl implements Worker {\n'
			'\tprivate record Item(String v) {\n'
			'\t\tstatic Item of(String s) { return new Item(s); }\n'
			'\t}\n'
			'\t/**\n\t * - @used-by META-INF/plugin.xml\n\t * - @uses {@link DynamicTarget#ping()}\n\t */\n'
			'\t@Override\n'
			'\tpublic void execute(String name) { Item.of(name); }\n'
			'}\n'
		)
		dyn = 'package demo;\npublic final class DynamicTarget {\n\tprivate DynamicTarget() {}\n\tpublic static void ping() {}\n}\n'
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write(repo, 'src/main/java/demo/Worker.java', iface)
			self._write(repo, 'src/main/java/demo/Impl.java', impl)
			self._write(repo, 'src/main/java/demo/DynamicTarget.java', dyn)
			before = check_java_repo(repo)
			self.assertFalse(before['valid'])
			self.assertIn('@see', '\n'.join(before['issues']))
			sync_java_repo(repo, apply=True)
			impl_txt = (repo / 'src/main/java/demo/Impl.java').read_text(encoding='utf-8')
			dyn_txt = (repo / 'src/main/java/demo/DynamicTarget.java').read_text(encoding='utf-8')
			self.assertIn('* @see Worker#execute(String)', impl_txt)
			self.assertIn('* - @used-by {@link Impl#execute(String)}', impl_txt)
			self.assertIn('* - @used-by {@link Impl#execute(String)}', dyn_txt)
			after = check_java_repo(repo)
			self.assertTrue(after['valid'], after['issues'])
			self.assertEqual([], sync_java_repo(repo, apply=True)['changed_files'])
if '__main__' == __name__:
	unittest.main()
