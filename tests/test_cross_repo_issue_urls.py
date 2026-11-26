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
from agent_tools.git_gate import GitRepoGate
from agent_tools.issues.auditor import TurnIssueLifecycleAuditor
from agent_tools.tdd.exemption import verify_staged_issue_urls
# @used-by :meth:`CrossRepoIssueUrlsTests.test_auditor_ignores_foreign_repo_turn_issue_urls_in_touched_file()`
# @used-by :meth:`CrossRepoIssueUrlsTests.test_staged_issue_urls_ignore_foreign_repo_urls_and_check_dotpy()`
def _git(repo: Path, *args: str) -> None:
	subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=15, check=True)
# 2026-11-26 "Scope issue-URL lifecycle gates to target repository": https://github.com/dmitry-ai/harness/issues/321
class CrossRepoIssueUrlsTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_auditor_ignores_foreign_repo_turn_issue_urls_in_touched_file(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			repo = root / 'repo'
			(repo / 'scripts/Df/Core').mkdir(parents=True)
			_git(repo, 'init', '-b', 'main')
			_git(repo, 'remote', 'add', 'origin', 'https://github.com/dmitry-ai/harness.git')
			f = repo / 'scripts/Df/Core/Exception.py'
			local_url = 'https://github.com/dmitry-ai/harness/issues/321'
			foreign_url = 'https://github.com/mage2pro/core/issues/459'
			f.write_text(f'# {local_url}\n# {foreign_url}\ndef f() -> int:\n\treturn 1\n', encoding='utf-8')
			auditor = TurnIssueLifecycleAuditor(root, {}, None, None)
			auditor.turn_issues = {local_url: {'repo': 'dmitry-ai/harness', 'number': 321}, foreign_url: {'repo': 'mage2pro/core', 'number': 459}}
			req, committed = (set(), set())
			auditor._inspect_touched_code_file(repo, 'scripts/Df/Core/Exception.py', req, committed)
			self.assertEqual({local_url}, req)
			self.assertEqual({local_url}, committed)
	# @used-by :mod:`unittest`
	def test_staged_issue_urls_ignore_foreign_repo_urls_and_check_dotpy(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td)
			(repo / 'scripts/Df/Core/lib/array/select').mkdir(parents=True)
			_git(repo, 'init', '-b', 'main')
			_git(repo, 'config', 'user.email', 't@example.com')
			_git(repo, 'config', 'user.name', 'Test')
			_git(repo, 'remote', 'add', 'origin', 'https://github.com/dmitry-ai/harness.git')
			local_url = 'https://github.com/dmitry-ai/harness/issues/321'
			foreign_url = 'https://github.com/mage2pro/core/issues/375'
			dotpy = repo / 'scripts/Df/Core/lib/array/select/.py'
			dotpy.write_text(f'# {local_url}\n# {foreign_url}\ndef dfa(a):\n\treturn a\n', encoding='utf-8')
			_git(repo, 'add', 'scripts/Df/Core/lib/array/select/.py')
			gate = GitRepoGate(repo)
			urls = verify_staged_issue_urls(gate, ['scripts/Df/Core/lib/array/select/.py'], local_url)
			self.assertEqual({local_url}, urls)
			dotpy.write_text(f'# {foreign_url}\ndef dfa(a):\n\treturn a\n', encoding='utf-8')
			_git(repo, 'add', 'scripts/Df/Core/lib/array/select/.py')
			with self.assertRaises(ValueError):
				verify_staged_issue_urls(gate, ['scripts/Df/Core/lib/array/select/.py'], local_url)
			with self.assertRaisesRegex(ValueError, 'ISSUE-FIRST-GATE'):
				verify_staged_issue_urls(gate, ['scripts/Df/Core/lib/array/select/.py'], None)
			dotpy.write_text(f'# {local_url}\n# https://github.com/dmitry-ai/harness/issues/322\ndef dfa(a):\n\treturn a\n', encoding='utf-8')
			_git(repo, 'add', 'scripts/Df/Core/lib/array/select/.py')
			with self.assertRaises(ValueError):
				verify_staged_issue_urls(gate, ['scripts/Df/Core/lib/array/select/.py'], local_url)
if '__main__' == __name__:
	unittest.main()
