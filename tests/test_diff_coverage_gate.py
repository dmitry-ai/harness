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
# @used-by :func:`_init_demo_repo()`
# @used-by :meth:`DiffCoverageGateTests.test_select_targeted_narrows_large_cross_cutting_test_diffs_to_prod_stems_and_packages()`
# @used-by :meth:`DiffCoverageGateTests.test_select_targeted_prefers_changed_tests_over_unrelated_stem_matches()`
# @used-by :meth:`DiffCoverageGateTests.test_worktree_land_blocks_uncovered_new_function_and_passes_when_covered()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=True, timeout=30)
	return (proc.stdout or '').strip()
# @used-by :meth:`DiffCoverageGateTests.test_run_trace_diff_coverage_handles_timeout_gracefully()`
# @used-by :meth:`DiffCoverageGateTests.test_select_targeted_narrows_large_cross_cutting_test_diffs_to_prod_stems_and_packages()`
# @used-by :meth:`DiffCoverageGateTests.test_select_targeted_prefers_changed_tests_over_unrelated_stem_matches()`
# @used-by :meth:`DiffCoverageGateTests.test_tdd_check_reports_uncovered_added_function()`
# @used-by :meth:`DiffCoverageGateTests.test_worktree_land_blocks_uncovered_new_function_and_passes_when_covered()`
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
	# 2026-11-26 "Narrow diff-coverage test selection to production module stems on cross-cutting commits": https://github.com/dmitry-ai/harness/issues/315
	# @used-by :mod:`unittest`
	def test_select_targeted_narrows_large_cross_cutting_test_diffs_to_prod_stems_and_packages(self) -> None:
		from agent_tools.tdd.diff_coverage import select_targeted_test_modules
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_demo_repo(root)
			(repo / 'pkg/xref').mkdir(parents=True)
			(repo / 'pkg/xref/__init__.py').write_text('', encoding='utf-8')
			(repo / 'pkg/xref/calc.py').write_text('def x_base() -> int:\n\treturn 1\n', encoding='utf-8')
			(repo / 'tests/test_xref_mod.py').write_text('# covers pkg/xref/calc.py\nimport unittest\nclass X(unittest.TestCase):\n\tdef test_ok(self) -> None:\n\t\tself.assertTrue(True)\n', encoding='utf-8')
			for idx in range(7):
				(repo / f'tests/test_other_{idx}.py').write_text(f'import unittest\nclass O{idx}(unittest.TestCase):\n\tdef test_ok(self) -> None:\n\t\tself.assertTrue(True)\n', encoding='utf-8')
			_git(repo, 'add', '.')
			_git(repo, 'commit', '--no-verify', '-m', 'add xref and unrelated tests')
			(repo / 'pkg/xref/calc.py').write_text('def x_base() -> int:\n\treturn 1\ndef x_new() -> int:\n\treturn 2\n', encoding='utf-8')
			by_pkg = select_targeted_test_modules(repo, ['pkg/xref/calc.py'], base_ref='HEAD', include_working_tree=True)
			self.assertIn('test_xref_mod.py', [m.name for m in by_pkg])
			(repo / 'tests/test_xref_mod.py').write_text('# updated pkg/xref/calc.py\nimport unittest\nclass X(unittest.TestCase):\n\tdef test_ok(self) -> None:\n\t\tself.assertTrue(True)\n', encoding='utf-8')
			for idx in range(7):
				(repo / f'tests/test_other_{idx}.py').write_text(f'# touched {idx}\nimport unittest\nclass O{idx}(unittest.TestCase):\n\tdef test_ok(self) -> None:\n\t\tself.assertTrue(True)\n', encoding='utf-8')
			selected = select_targeted_test_modules(repo, ['pkg/xref/calc.py'], base_ref='HEAD', include_working_tree=True)
			self.assertEqual(['test_xref_mod.py'], [m.name for m in selected])
	# 2026-11-26 "Narrow diff-coverage test selection to production module stems on cross-cutting commits": https://github.com/dmitry-ai/harness/issues/315
	# @used-by :mod:`unittest`
	def test_run_trace_diff_coverage_handles_timeout_gracefully(self) -> None:
		from agent_tools.tdd import diff_coverage
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_demo_repo(root)
			added = {'pkg/calc.py': [{'name': 'base_val', 'start_line': 1, 'end_line': 2}]}
			with patch.object(diff_coverage.subprocess, 'run', side_effect=subprocess.TimeoutExpired(cmd=['pytest'], timeout=1.0)):
				res = diff_coverage.run_trace_diff_coverage(repo, added, [repo / 'tests/test_calc.py'], timeout=1.0)
			self.assertFalse(res['valid'], res)
			self.assertTrue(res.get('timed_out'), res)
			self.assertEqual(-1, res['exit_code'])
			self.assertEqual(1, res['checked_functions'])
			self.assertEqual(['pkg/calc.py:base_val (L1)'], res['uncovered'])
			self.assertEqual(['test_calc.py'], res['targeted_modules'])
if '__main__' == __name__:
	unittest.main()