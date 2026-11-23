# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce TDD test coverage and ratchet in Git pre-commit gate":
# https://github.com/dmitry-ai/harness/issues/137
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))

from agent_tools import git_gate

ISSUE_URL = 'https://github.com/dmitry-ai/harness/issues/137'


def _init_repo(repo: Path) -> None:
	repo.mkdir(parents=True, exist_ok=True)
	subprocess.run(['git', 'init', str(repo)], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'test@example.com'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test User'], check=True, capture_output=True)


class TddGitGateTests(unittest.TestCase):
	def test_agent_commit_requires_behavioral_test_for_production_code(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve() / 'repo'
			_init_repo(repo)
			prod = repo / 'src/calc.py'
			prod.parent.mkdir(parents=True, exist_ok=True)
			prod.write_text(f'# {ISSUE_URL}\ndef add(a, b):\n\treturn a + b\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'src/calc.py'], check=True, capture_output=True)

			# 1. Production code alone -> rejected by check_commit, pre-commit hook, and verify_git_write_invocation
			with self.assertRaisesRegex(ValueError, 'TDD-COMMIT-GATE'):
				git_gate.check_commit(repo, ['src/calc.py'])
			self.assertEqual(git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True), 2)
			with self.assertRaisesRegex(ValueError, 'TDD-COMMIT-GATE'):
				git_gate.verify_git_write_invocation(['-C', str(repo), 'commit', '-m', ISSUE_URL], agent_context=True)

			# Human commit (agent_context=False) remains exempted
			self.assertEqual(git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=False), 0)
			git_gate.verify_git_write_invocation(['-C', str(repo), 'commit', '-m', 'human wip'], agent_context=False)

			# 2. Assertionless stub test -> rejected by TDD-SUBSTANTIVE-TEST-GATE
			test_f = repo / 'tests/test_calc.py'
			test_f.parent.mkdir(parents=True, exist_ok=True)
			test_f.write_text(f'# {ISSUE_URL}\ndef test_empty():\n\tpass\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'tests/test_calc.py'], check=True, capture_output=True)
			with self.assertRaisesRegex(ValueError, 'TDD-SUBSTANTIVE-TEST-GATE'):
				git_gate.check_commit(repo, ['src/calc.py', 'tests/test_calc.py'])
			self.assertEqual(git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True), 2)

			# 3. Source-text grep test -> rejected by TDD-BEHAVIORAL-GATE
			test_f.write_text(
				f'# {ISSUE_URL}\n'
				'from pathlib import Path\n'
				'def test_bad_grep():\n'
				'\ttxt = (Path(__file__).resolve().parents[1] / "src/calc.py").read_text(encoding="utf-8")\n'
				'\tassert "def add" in txt\n',
				encoding='utf-8',
			)
			subprocess.run(['git', '-C', str(repo), 'add', 'tests/test_calc.py'], check=True, capture_output=True)
			with self.assertRaisesRegex(ValueError, 'TDD-BEHAVIORAL-GATE'):
				git_gate.check_commit(repo, ['src/calc.py', 'tests/test_calc.py'])
			self.assertEqual(git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True), 2)

			# 4. Real behavioral test -> ALLOWED and commits cleanly
			test_f.write_text(
				f'# {ISSUE_URL}\n'
				'import unittest\n'
				'class CalcTests(unittest.TestCase):\n'
				'\tdef test_add(self):\n'
				'\t\tself.assertEqual(2 + 3, 5)\n',
				encoding='utf-8',
			)
			subprocess.run(['git', '-C', str(repo), 'add', 'tests/test_calc.py'], check=True, capture_output=True)
			self.assertEqual(git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True), 0)
			committed = git_gate.commit(repo, ['src/calc.py', 'tests/test_calc.py'], ISSUE_URL, execute=True)
			self.assertEqual(committed, ['src/calc.py', 'tests/test_calc.py'])

	def test_ratchet_enforced_on_staged_test_edits_and_unlocked_by_ratchet_ok(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			repo = proj / 'code'
			(proj / 'ꘖ/KB/Evidence/GitHub/dmitry-ai__harness').mkdir(parents=True)
			_init_repo(repo)
			test_f = repo / 'tests/test_core.py'
			test_f.parent.mkdir(parents=True)
			orig = (
				f'# {ISSUE_URL}\n'
				'import unittest\n'
				'class CoreTests(unittest.TestCase):\n'
				'\tdef test_invariant(self):\n'
				'\t\tself.assertEqual(10, 10)\n'
			)
			test_f.write_text(orig, encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'tests/test_core.py'], check=True, capture_output=True)
			git_gate.commit(repo, ['tests/test_core.py'], ISSUE_URL, execute=True)

			# Weakening an existing assertion -> blocked by TDD-RATCHET
			weakened = orig.replace('self.assertEqual(10, 10)', 'self.assertEqual(10, 11)')
			test_f.write_text(weakened, encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'tests/test_core.py'], check=True, capture_output=True)
			with self.assertRaisesRegex(ValueError, 'TDD-RATCHET'):
				git_gate.check_commit(repo, ['tests/test_core.py'])
			self.assertEqual(git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True), 2)

			# Audited RATCHET-OK in GitHub Issue Evidence JSON under project root unlocks commit
			(proj / 'ꘖ/KB/Evidence/GitHub/dmitry-ai__harness/issue-137.json').write_text(
				json.dumps({
					'url': ISSUE_URL,
					'issue': {
						'number': 137,
						'state': 'OPEN',
						'body': 'RATCHET-OK: tests/test_core.py — User explicitly updated expected constant in Issue #137 to match revised contract.\n',
					},
				}),
				encoding='utf-8',
			)
			self.assertEqual(git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True), 0)
			self.assertEqual(git_gate.check_commit(repo, ['tests/test_core.py']), ['tests/test_core.py'])

	def test_doc_only_agent_commit_allowed_without_tests(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve() / 'docs_repo'
			_init_repo(repo)
			readme = repo / 'README.md'
			readme.write_text('# Docs\n\nUpdated guide.\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'README.md'], check=True, capture_output=True)
			self.assertEqual(git_gate.run_git_hook('pre-commit', cwd=repo, agent_context=True), 0)
			self.assertEqual(git_gate.check_commit(repo, ['README.md']), ['README.md'])


if '__main__' == __name__:
	unittest.main()
