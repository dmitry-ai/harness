# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce diff-coverage check for newly added functions in tdd-check and worktree-land":
# https://github.com/dmitry-ai/harness/issues/292
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
for p in (SCRIPTS,):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
# @used-by :func:`_init_demo_repo()`, :meth:`DiffCoverageGateTests.test_worktree_land_blocks_uncovered_new_function_and_passes_when_covered()`, :meth:`DiffCoverageGateTests.test_tdd_check_reports_uncovered_added_function()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=True, timeout=30)
	return (proc.stdout or '').strip()
# @used-by :meth:`DiffCoverageGateTests.test_worktree_land_blocks_uncovered_new_function_and_passes_when_covered()`, :meth:`DiffCoverageGateTests.test_tdd_check_reports_uncovered_added_function()`
def _init_demo_repo(root: Path) -> Path:
	repo = root / 'repo'
	(repo / 'pkg').mkdir(parents=True)
	(repo / 'tests').mkdir(parents=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	_git(repo, 'remote', 'add', 'origin', 'https://github.com/owner/demo.git')
	(repo / '.gitignore').write_text('__pycache__/\n*.pyc\n', encoding='utf-8')
	(repo / 'pkg/__init__.py').write_text('', encoding='utf-8')
	(repo / 'pkg/calc.py').write_text('def base_val() -> int:\n\treturn 1\n', encoding='utf-8')
	(repo / 'tests/test_calc.py').write_text('import sys, unittest\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\nfrom pkg import calc\nclass CalcTests(unittest.TestCase):\n\tdef test_base(self) -> None:\n\t\tself.assertEqual(1, calc.base_val())\n', encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'init')
	return repo
# @used-by :mod:`unittest`
class DiffCoverageGateTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_worktree_land_blocks_uncovered_new_function_and_passes_when_covered(self) -> None:
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_demo_repo(root)
			wt = Path(worktree_begin(repo, 'cov-demo', worktrees_dir=root / 'wts')['worktree'])
			(wt / 'pkg/calc.py').write_text('def base_val() -> int:\n\treturn 1\ndef dead_untested_helper() -> int:\n\treturn 42\n', encoding='utf-8')
			_git(wt, 'add', 'pkg/calc.py')
			_git(wt, 'commit', '--no-verify', '-m', 'add dead helper')
			blocked = worktree_land(wt, run_tests=True, remove=False, leases_dir=root / 'leases', promote_snapshot=False)
			self.assertFalse(blocked['valid'], blocked)
			self.assertEqual('diff_coverage', blocked['stage'])
			self.assertIn('dead_untested_helper', blocked['error'])
			(wt / 'tests/test_calc.py').write_text('import sys, unittest\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\nfrom pkg import calc\nclass CalcTests(unittest.TestCase):\n\tdef test_base(self) -> None:\n\t\tself.assertEqual(1, calc.base_val())\n\t\tself.assertEqual(42, calc.dead_untested_helper())\n', encoding='utf-8')
			_git(wt, 'add', 'tests/test_calc.py')
			_git(wt, 'commit', '--no-verify', '-m', 'cover helper')
			passed = worktree_land(wt, run_tests=True, remove=True, leases_dir=root / 'leases', promote_snapshot=False)
			self.assertTrue(passed['valid'], passed)
			self.assertTrue(passed['landed'])
	# @used-by :mod:`unittest`
	def test_tdd_check_reports_uncovered_added_function(self) -> None:
		from agent_tools import completion
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_demo_repo(root)
			(repo / 'pkg/calc.py').write_text('def base_val() -> int:\n\treturn 1\ndef untested_extra() -> int:\n\treturn 99\n', encoding='utf-8')
			cid = '22222222-2222-2222-2222-222222222222'
			turn = {'turn_id': f'ag-{cid}-0', 'start_step': 0, 'requests': [{'id': f'{cid}-0', 'text': 'Check tdd'}], 'owned': True, 'completed': False, 'aborted': False, 'touched_files': [str(repo / 'pkg/calc.py')], 'tdd_events': []}
			native = {'platform': 'antigravity', 'conversation_id': cid, 'native_backend': str(root), 'source_file': str(root / 'tx.jsonl'), 'primary': True, 'turns': [turn], 'active_turn_id': turn['turn_id']}
			with patch.object(completion, '_native', return_value=native):
				rep = completion.tdd_check_turn(repo, conversation=cid, platform='antigravity')
			self.assertIn('diff_coverage', rep)
			self.assertFalse(rep['diff_coverage']['valid'], rep['diff_coverage'])
			self.assertTrue(any(('untested_extra' in u for u in rep['diff_coverage']['uncovered'])), rep['diff_coverage'])
	# @used-by :mod:`unittest`
	def test_select_targeted_prefers_changed_tests_over_unrelated_stem_matches(self) -> None:
		from agent_tools.tdd.diff_coverage import select_targeted_test_modules
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_demo_repo(root)
			for idx in range(6):
				(repo / f'tests/test_extra_{idx}.py').write_text(f'# mentions calc\nimport unittest\nclass E{idx}(unittest.TestCase):\n\tdef test_ok(self) -> None:\n\t\tself.assertTrue(True)\n', encoding='utf-8')
			_git(repo, 'add', '.')
			_git(repo, 'commit', '--no-verify', '-m', 'add extra tests')
			(repo / 'pkg/calc.py').write_text('def base_val() -> int:\n\treturn 1\ndef new_fn() -> int:\n\treturn 2\n', encoding='utf-8')
			(repo / 'tests/test_calc.py').write_text('import unittest\nclass CalcTests(unittest.TestCase):\n\tdef test_ok(self) -> None:\n\t\tself.assertTrue(True)\n', encoding='utf-8')
			selected = select_targeted_test_modules(repo, ['pkg/calc.py'], base_ref='HEAD', include_working_tree=True)
			self.assertEqual(['test_calc.py'], [m.name for m in selected])
if '__main__' == __name__:
	unittest.main()