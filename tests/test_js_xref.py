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
class JsXrefTests(unittest.TestCase):
	# @used-by :meth:`JsXrefTests.test_js_global_assignment_and_top_level_listener_edges()`
	# @used-by :meth:`JsXrefTests.test_js_override_and_ts_override_require_see_and_modifier()`
	# @used-by :meth:`JsXrefTests.test_js_sync_and_check_commonjs_esm_classes_and_uses()`
	# @used-by :meth:`JsXrefTests.test_js_validator_rejects_broken_and_missing_used_by()`
	def _write(self, root: Path, rel: str, content: str) -> Path:
		p = root / rel
		p.parent.mkdir(parents=True, exist_ok=True)
		p.write_text(content, encoding='utf-8')
		return p
	# @used-by :mod:`unittest`
	def test_js_global_assignment_and_top_level_listener_edges(self) -> None:
		from agent_tools.xref.js_sync import check_js_repo, sync_js_repo
		sw_src = (
			'async function setup() { return 1; }\n'
			'async function handle(m) { return m; }\n'
			'chrome.runtime.onMessage.addListener(m => { setup(); return handle(m); });\n'
		)
		off_src = (
			'/**\n * @used-by browser_extension/offscreen.html\n'
			" * @uses {@link import('./sw.js')} (handle)\n */\n"
			'globalThis.__broker = async p => chrome.runtime.sendMessage(p);\n'
		)
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write(repo, 'browser_extension/sw.js', sw_src)
			self._write(repo, 'browser_extension/offscreen.js', off_src)
			sync_js_repo(repo, apply=True)
			sw_txt = (repo / 'browser_extension/sw.js').read_text(encoding='utf-8')
			self.assertIn("* @used-by {@link import('./sw.js')}", sw_txt)
			self.assertIn("* @used-by {@link import('./offscreen.js')} (globalThis.__broker)", sw_txt)
			after = check_js_repo(repo)
			self.assertTrue(after['valid'], after['issues'])
	# @used-by :mod:`unittest`
	def test_js_override_and_ts_override_require_see_and_modifier(self) -> None:
		from agent_tools.xref.js_sync import check_js_repo, sync_js_repo
		js_src = (
			'class Base {\n\trun() { return 1; }\n}\n'
			'class Child extends Base {\n\trun() { return super.run() + 1; }\n}\n'
			'/**\n * @used-by Upgrade/package.json\n */\n'
			'const main = () => new Child().run();\n'
		)
		ts_src = (
			'class Alpha {\n\tcompute(x: number): number { return x; }\n}\n'
			'class Beta extends Alpha {\n\toverride compute(x: number): number { return x + 1; }\n}\n'
			'/**\n * @used-by CLI\n */\n'
			'export const entry = () => new Beta().compute(1);\n'
		)
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write(repo, 'app.js', js_src)
			self._write(repo, 'typed.ts', ts_src)
			before = check_js_repo(repo)
			self.assertFalse(before['valid'])
			joined = '\n'.join(before['issues'])
			self.assertIn('@override', joined)
			self.assertIn('@see', joined)
			sync_js_repo(repo, apply=True)
			js_after = (repo / 'app.js').read_text(encoding='utf-8')
			self.assertIn('* @override', js_after)
			self.assertIn('* @see {@link Base#run}', js_after)
			ts_after = (repo / 'typed.ts').read_text(encoding='utf-8')
			self.assertIn('* @see {@link Alpha#compute}', ts_after)
			self.assertNotIn('* @override', ts_after)
			after = check_js_repo(repo)
			self.assertTrue(after['valid'], after['issues'])
	# @used-by :mod:`unittest`
	def test_js_sync_and_check_commonjs_esm_classes_and_uses(self) -> None:
		from agent_tools.xref.js_sync import check_js_repo, sync_js_repo
		model_src = (
			'// 2026-11-26 "Title": https://github.com/dmitry-ai/harness/issues/301\n'
			'const leaf = x => x + 1;\n'
			'class Store {\n\tconstructor(n) { this.n = n; }\n\tget() { return leaf(this.n); }\n}\n'
			'module.exports = {Store, leaf};\n'
		)
		dyn_src = 'function broker(msg) { return msg; }\nmodule.exports = {broker};\n'
		app_src = (
			"const {Store} = require('./model');\n"
			'/**\n * @used-by Upgrade/package.json\n * @uses {@link import(\'./dyn.js\').broker}\n */\n'
			'const start = () => new Store(1).get();\n'
		)
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write(repo, 'lib/model.js', model_src)
			self._write(repo, 'lib/dyn.js', dyn_src)
			self._write(repo, 'lib/app.js', app_src)
			sync_js_repo(repo, apply=True)
			model_txt = (repo / 'lib/model.js').read_text(encoding='utf-8')
			dyn_txt = (repo / 'lib/dyn.js').read_text(encoding='utf-8')
			self.assertIn('* @used-by {@link Store#get}', model_txt)
			self.assertIn("* @used-by {@link import('./app.js')} (start)", model_txt)
			self.assertIn("* @used-by {@link import('./app.js')} (start)", dyn_txt)
			self.assertTrue(check_js_repo(repo)['valid'])
			self.assertEqual([], sync_js_repo(repo, apply=True)['changed_files'])
	# @used-by :mod:`unittest`
	def test_js_validator_rejects_broken_and_missing_used_by(self) -> None:
		from agent_tools.xref.js_sync import check_js_repo
		bad_src = (
			'/**\n * @used-by {@link ghostFn}\n */\n'
			'function helper() { return 1; }\n'
			'function orphan() { return helper(); }\n'
		)
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write(repo, 'bad.js', bad_src)
			res = check_js_repo(repo)
			self.assertFalse(res['valid'])
			joined = '\n'.join(res['issues'])
			self.assertIn('ghostFn', joined)
			self.assertIn('orphan', joined)
if '__main__' == __name__:
	unittest.main()
