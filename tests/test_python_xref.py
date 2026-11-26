# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
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
# 2026-11-26
# "Implement Python AST cross-reference analyzer and sync CLI":
# https://github.com/dmitry-ai/harness/issues/287
class PythonXrefTests(unittest.TestCase):
	# @used-by :meth:`PythonXrefTests.test_cli_xref_check_and_sync_commands()`
	def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
		return subprocess.run([sys.executable, str(SCRIPTS / 'harness.py'), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=False)
	# @used-by :meth:`PythonXrefTests.test_cli_xref_check_and_sync_commands()`
	# @used-by :meth:`PythonXrefTests.test_override_requires_typing_override_and_see()`
	# @used-by :meth:`PythonXrefTests.test_reexport_through_package_init_and_all_resolves_callers()`
	# @used-by :meth:`PythonXrefTests.test_sync_and_check_python_call_graph_and_uses_propagation()`
	# @used-by :meth:`PythonXrefTests.test_validator_rejects_self_bare_tags_broken_and_stale_used_by()`
	def _write_file(self, root: Path, rel: str, content: str) -> Path:
		target = root / rel
		target.parent.mkdir(parents=True, exist_ok=True)
		target.write_text(content, encoding='utf-8')
		return target
	# @used-by :mod:`unittest`
	def test_cli_xref_check_and_sync_commands(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write_file(repo, 'scripts/pkg/__init__.py', '')
			self._write_file(repo, 'scripts/pkg/a.py', 'def leaf() -> int:\n\treturn 1\n')
			self._write_file(repo, 'scripts/pkg/b.py', 'from .a import leaf\n# @used-by platforms/hooks.json\ndef run() -> int:\n\treturn leaf()\n')
			chk_fail = self._run_cli('xref-check', str(repo), '--lang', 'python')
			self.assertEqual(2, chk_fail.returncode, chk_fail.stdout + chk_fail.stderr)
			syn = self._run_cli('xref-sync', str(repo), '--lang', 'python')
			self.assertEqual(0, syn.returncode, syn.stdout + syn.stderr)
			chk_ok = self._run_cli('xref-check', str(repo), '--lang', 'python')
			self.assertEqual(0, chk_ok.returncode, chk_ok.stdout + chk_ok.stderr)
			self.assertIn('# @used-by :func:`pkg.b.run()`', (repo / 'scripts/pkg/a.py').read_text(encoding='utf-8'))
	# @used-by :mod:`unittest`
	def test_override_requires_typing_override_and_see(self) -> None:
		from agent_tools.xref import check_python_repo, sync_python_repo
		src = (
			'from html.parser import HTMLParser\n'
			'class MyParser(HTMLParser):\n'
			'\tdef handle_starttag(self, tag, attrs):\n\t\tself.last = tag\n'
			'\t@classmethod\n\tdef helper(cls):\n\t\treturn cls()\n'
			'class SubParser(MyParser):\n'
			'\t@classmethod\n\tdef helper(cls):\n\t\treturn super().helper()\n'
			'# @used-by platforms/hooks.json\n'
			'def run() -> object:\n\treturn SubParser.helper()\n'
		)
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write_file(repo, 'scripts/pkg/__init__.py', '')
			self._write_file(repo, 'scripts/pkg/parsers.py', src)
			before = check_python_repo(repo)
			self.assertFalse(before['valid'])
			joined = '\n'.join(before['issues'])
			self.assertIn('@override', joined)
			self.assertIn('@see', joined)
			sync_python_repo(repo, apply=True)
			synced = (repo / 'scripts/pkg/parsers.py').read_text(encoding='utf-8')
			self.assertIn('from typing import override', synced)
			self.assertIn('# @see :meth:`html.parser.HTMLParser.handle_starttag()`\n\t@override\n\tdef handle_starttag', synced)
			self.assertIn('# @see :meth:`MyParser.helper()`\n\t@classmethod\n\t@override\n\tdef helper', synced)
			after = check_python_repo(repo)
			self.assertTrue(after['valid'], after['issues'])
	# @used-by :mod:`unittest`
	def test_reexport_through_package_init_and_all_resolves_callers(self) -> None:
		from agent_tools.xref import check_python_repo, sync_python_repo
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write_file(repo, 'scripts/pkg/__init__.py', "from .impl import exported_fn, public_only\n__all__ = ['exported_fn', 'public_only']\n")
			self._write_file(repo, 'scripts/pkg/impl.py', 'def exported_fn() -> int:\n\treturn 1\ndef public_only() -> int:\n\treturn 2\n')
			self._write_file(repo, 'scripts/pkg/caller.py', 'from pkg import exported_fn\n# @used-by platforms/hooks.json\ndef entry() -> int:\n\treturn exported_fn()\n')
			sync_python_repo(repo, apply=True)
			impl_txt = (repo / 'scripts/pkg/impl.py').read_text(encoding='utf-8')
			self.assertIn('# @used-by :func:`pkg.caller.entry()`', impl_txt)
			self.assertIn('# @used-by :mod:`pkg`', impl_txt)
			res = check_python_repo(repo)
			self.assertTrue(res['valid'], res['issues'])
	# @used-by :mod:`unittest`
	def test_sync_and_check_python_call_graph_and_uses_propagation(self) -> None:
		from agent_tools.xref import check_python_repo, sync_python_repo
		dyn_src = '# 2026-11-26 "Title": https://github.com/dmitry-ai/harness/issues/287\ndef check_plugin() -> bool:\n\treturn True\n'
		core_src = (
			'class Worker:\n\tdef _helper(self) -> int:\n\t\treturn 1\n'
			'\tdef run(self) -> int:\n\t\t# @uses :func:`pkg.dynamic.check_plugin()`\n\t\treturn self._helper()\n'
			'# @used-by platforms/hooks.json\ndef main() -> int:\n'
			'\tdef inner() -> int:\n\t\treturn Worker().run()\n\treturn inner()\n'
		)
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write_file(repo, 'scripts/pkg/__init__.py', '')
			self._write_file(repo, 'scripts/pkg/dynamic.py', dyn_src)
			self._write_file(repo, 'scripts/pkg/core.py', core_src)
			sync_res = sync_python_repo(repo, apply=True)
			self.assertTrue(sync_res['valid'], sync_res)
			dyn_txt = (repo / 'scripts/pkg/dynamic.py').read_text(encoding='utf-8')
			self.assertIn('# 2026-11-26 "Title": https://github.com/dmitry-ai/harness/issues/287\n# @used-by :meth:`pkg.core.Worker.run()`\ndef check_plugin', dyn_txt)
			core_txt = (repo / 'scripts/pkg/core.py').read_text(encoding='utf-8')
			self.assertIn('# @used-by :meth:`Worker.run()`\n\tdef _helper', core_txt)
			self.assertIn('# @used-by :func:`main()`\n\tdef run', core_txt)
			self.assertIn('# @used-by :func:`main()`\n\tdef inner', core_txt)
			check_res = check_python_repo(repo)
			self.assertTrue(check_res['valid'], check_res['issues'])
			self.assertEqual([], sync_python_repo(repo, apply=True)['changed_files'])
	# @used-by :mod:`unittest`
	def test_validator_rejects_self_bare_tags_broken_and_stale_used_by(self) -> None:
		from agent_tools.xref import check_python_repo
		bad_src = (
			'class Box:\n'
			'\t# @used-by :meth:`self.run()`\n'
			'\t# @used-by pkg.bad.missing_fn()\n'
			'\t# @used-by :func:`pkg.bad.ghost()`\n'
			'\tdef helper(self) -> int:\n\t\treturn 1\n'
			'\t# @used-by platforms/hooks.json\n'
			'\tdef run(self) -> int:\n\t\treturn self.helper()\n'
		)
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			self._write_file(repo, 'scripts/pkg/__init__.py', '')
			self._write_file(repo, 'scripts/pkg/bad.py', bad_src)
			res = check_python_repo(repo)
			self.assertFalse(res['valid'])
			joined = '\n'.join(res['issues'])
			self.assertIn('self.', joined)
			self.assertIn('Sphinx', joined)
			self.assertIn('ghost', joined)
if '__main__' == __name__:
	unittest.main()
