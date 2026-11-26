# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = HARNESS_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# @used-by :func:`_init_repo()`
def _copy_fixture_modules(repo: Path, rels: tuple[str, ...]) -> None:
	for rel in rels:
		src = HARNESS_ROOT / rel
		if src.is_file():
			dst = repo / rel
			dst.parent.mkdir(parents=True, exist_ok=True)
			shutil.copy2(src, dst)
# @used-by :func:`_init_repo()`
# @used-by :meth:`PythonIntegrityGateTests.test_pre_commit_and_worktree_land_enforce_integrity_and_ratchet()`
# @used-by :meth:`PythonIntegrityGateTests.test_worktree_land_python_integrity_handles_cross_cutting_multi_file_commit()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True)
	return (proc.stdout or '').strip()
# @used-by :meth:`PythonIntegrityGateTests.test_legacy_oversized_edit_deferred_in_pre_tool_use_while_write_file_enforced()`
# @used-by :meth:`PythonIntegrityGateTests.test_pre_commit_and_worktree_land_enforce_integrity_and_ratchet()`
# @used-by :meth:`PythonIntegrityGateTests.test_snapshot_promotion_and_auditor_reject_undefined_global()`
# @used-by :meth:`PythonIntegrityGateTests.test_worktree_land_python_integrity_handles_cross_cutting_multi_file_commit()`
def _init_repo(repo: Path, files: dict[str, str], *, copy_rels: tuple[str, ...]=()) -> Path:
	repo.mkdir(parents=True, exist_ok=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	_copy_fixture_modules(repo, copy_rels)
	for rel, body in files.items():
		fp = repo / rel
		fp.parent.mkdir(parents=True, exist_ok=True)
		fp.write_text(body, encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '-m', 'init')
	return repo
# @used-by :meth:`PythonIntegrityGateTests.test_legacy_oversized_edit_deferred_in_pre_tool_use_while_write_file_enforced()`
# @used-by :meth:`PythonIntegrityGateTests.test_pre_commit_and_worktree_land_enforce_integrity_and_ratchet()`
def _make_legacy_file(lines_count: int=310) -> str:
	return ''.join((f'CONST_{i} = {i}\n' for i in range(lines_count)))
# 2026-11-24
# "Enforce transaction-boundary Python size ratchet and symbol integrity checks":
# https://github.com/dmitry-ai/harness/issues/186
class PythonIntegrityGateTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_check_python_size_violations_rejects_syntax_error(self) -> None:
		from agent_tools.code_size_gate import check_python_size_violations
		errs = check_python_size_violations('scripts/bad.py', 'def broken(:\n\tpass\n')
		self.assertTrue(errs, 'SyntaxError must not silently return []')
		self.assertTrue(any(('syntax' in e.lower() for e in errs)), errs)
	# @used-by :mod:`unittest`
	def test_legacy_oversized_edit_deferred_in_pre_tool_use_while_write_file_enforced(self) -> None:
		from agent_tools.code_size_gate import evaluate_pre_tool_use_code_size
		with tempfile.TemporaryDirectory() as td:
			repo = _init_repo(Path(td).resolve() / 'repo', {'scripts/legacy_big.py': _make_legacy_file(310)})
			target = repo / 'scripts/legacy_big.py'
			edit_err = evaluate_pre_tool_use_code_size('edit_file', {'Path': str(target), 'Target': 'CONST_0 = 0\n', 'Replacement': 'from collections import OrderedDict\nEXTRA_VAR = 1\nCONST_0 = 0\n'}, {'cwd': str(repo)})
			self.assertIsNone(edit_err, f'Incremental edit on legacy >300 SLOC file must defer to commit boundary: {edit_err}')
			grown = 'from collections import OrderedDict\nEXTRA_VAR = 1\n' + target.read_text(encoding='utf-8')
			write_err = evaluate_pre_tool_use_code_size('write_file', {'Path': str(target), 'Content': grown}, {'cwd': str(repo)})
			self.assertIsNotNone(write_err)
			self.assertIn('CODE-4', write_err or '')
			undef_err = evaluate_pre_tool_use_code_size('write_file', {'Path': str(repo / 'scripts/undef.py'), 'Content': '_CACHE = OrderedDict()\n'}, {'cwd': str(repo)})
			self.assertIsNotNone(undef_err)
			self.assertIn('OrderedDict', undef_err or '')
			syn_err = evaluate_pre_tool_use_code_size('write_file', {'Path': str(repo / 'scripts/syn.py'), 'Content': 'def bad(:\n\tpass\n'}, {'cwd': str(repo)})
			self.assertIsNotNone(syn_err)
			self.assertIn('syntax', (syn_err or '').lower())
	# @used-by :mod:`unittest`
	def test_pre_commit_and_worktree_land_enforce_integrity_and_ratchet(self) -> None:
		from agent_tools.code_size_gate import verify_staged_code_size_ratchet
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_repo(root / 'repo', {'scripts/legacy_big.py': _make_legacy_file(310)})
			(repo / 'scripts/legacy_big.py').write_text('EXTRA_A = 1\nEXTRA_B = 2\n' + _make_legacy_file(310), encoding='utf-8')
			(repo / 'scripts/bad_sym.py').write_text('_CACHE = OrderedDict()\n', encoding='utf-8')
			_git(repo, 'add', 'scripts/legacy_big.py', 'scripts/bad_sym.py')
			viols = verify_staged_code_size_ratchet(repo, ['scripts/legacy_big.py', 'scripts/bad_sym.py'], use_index=True)
			self.assertTrue(any(('legacy_big.py' in v for v in viols)), viols)
			self.assertTrue(any(('OrderedDict' in v for v in viols)), viols)
			_git(repo, 'reset', '--hard', 'HEAD')
			wt = Path(worktree_begin(repo, 'bad-py', worktrees_dir=root / 'wts')['worktree'])
			(wt / 'scripts/bad_wt.py').write_text('def boom():\n\treturn MissingWtSym()\n', encoding='utf-8')
			_git(wt, 'add', 'scripts/bad_wt.py')
			_git(wt, 'commit', '-m', 'add broken symbol')
			land = worktree_land(wt, run_tests=False, remove=False, leases_dir=root / 'leases')
			self.assertFalse(land['landed'])
			self.assertEqual('python_integrity', land['stage'])
			self.assertIn('MissingWtSym', land['error'])
	# @used-by :mod:`unittest`
	def test_python_integrity_catches_syntax_and_undefined_globals_zero_fp_on_harness(self) -> None:
		from agent_tools.python_integrity import check_python_integrity, verify_directory_python_integrity
		e1 = check_python_integrity('scripts/a.py', '_CACHE: OrderedDict = OrderedDict()\n')
		self.assertTrue(any(('OrderedDict' in e for e in e1)), e1)
		e2 = check_python_integrity('scripts/b.py', 'def f():\n\treturn MissingGlobal()\n')
		self.assertTrue(any(('MissingGlobal' in e for e in e2)), e2)
		e3 = check_python_integrity('scripts/c.py', 'def bad(:\n\tpass\n')
		self.assertTrue(any(('syntax' in e.lower() for e in e3)), e3)
		valid_src = (
			'from __future__ import annotations\n'
			'class Box:\n'
			'\tVAL = 1\n'
			'\tDUP = VAL\n'
			'\tdef get(self) -> Box:\n'
			'\t\treturn self\n'
			'def outer(p: int):\n'
			'\tdef inner():\n'
			'\t\treturn [p + i for i in range(3)]\n'
			'\treturn inner\n'
			'def set_g():\n'
			'\tglobal LATER\n'
			'\tLATER = 5\n'
		)
		self.assertEqual([], check_python_integrity('scripts/ok.py', valid_src))
		self.assertEqual([], check_python_integrity('scripts/star.py', 'from math import *\nX = sin(1)\n'))
		self.assertEqual([], verify_directory_python_integrity(HARNESS_ROOT / 'scripts'))
	# @used-by :mod:`unittest`
	def test_snapshot_promotion_and_auditor_reject_undefined_global(self) -> None:
		from agent_tools.python_integrity import verify_touched_python_files
		from agent_tools.runtime_snapshot import promote_runtime_snapshot
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_repo(
				root / 'proj/\u2c0f/\u227b/\u2655/\u26ef',
				{
					'scripts/agent_tools/__init__.py': '',
					'scripts/agent_tools/gates/__init__.py': 'def discover_pre_tool_gates():\n\treturn []\n',
					'scripts/agent_tools/lazy_bug.py': 'def lazy_fn():\n\treturn MissingLazySym()\n',
					'scripts/check_markdown_slop.py': 'import sys\n',
					'scripts/check_rules_and_server_gate.py': 'import sys\n',
					'scripts/check_pre_invocation.py': 'import sys\n',
					'scripts/check_stop_gate.py': 'import sys\n',
					'scripts/git_shim.py': 'import sys\n',
				},
				# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
				# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
				copy_rels=('paths.json', 'runtime.json', 'scripts/Df/__init__.py', 'scripts/Df/Core/lib/fs/.py', 'scripts/Df/Core/lib/git.py', 'scripts/Df/Harness/Gate/PythonIntegrity.py', 'scripts/agent_tools/path_cache.py', 'scripts/agent_tools/path_registry.py', 'scripts/agent_tools/python_integrity.py'),
			)
			snap = promote_runtime_snapshot(repo, store_dir=root / 'store')
			self.assertFalse(snap['valid'])
			self.assertFalse(snap['promoted'])
			self.assertIn('MissingLazySym', snap.get('error', ''))
			t_viols = verify_touched_python_files(repo, ['scripts/agent_tools/lazy_bug.py'])
			self.assertTrue(any(('MissingLazySym' in v for v in t_viols)), t_viols)
	# 2026-11-26 "Handle worktree-land gate timeouts cleanly and add cross-cutting boundary regressions": https://github.com/dmitry-ai/harness/issues/365
	# @used-by :mod:`unittest`
	def test_worktree_land_python_integrity_handles_cross_cutting_multi_file_commit(self) -> None:
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			seed = {f'scripts/mod_{idx}.py': f'def fn_{idx}() -> int:\n\treturn {idx}\n' for idx in range(7)}
			repo = _init_repo(root / 'repo', seed)
			wt = Path(worktree_begin(repo, 'cross-py', worktrees_dir=root / 'wts')['worktree'])
			for idx in range(7):
				body = f'def fn_{idx}() -> int:\n\treturn BrokenCrossSym()\n' if 5 == idx else f'def fn_{idx}() -> int:\n\treturn {idx + 10}\n'
				(wt / f'scripts/mod_{idx}.py').write_text(body, encoding='utf-8')
			_git(wt, 'add', '.')
			_git(wt, 'commit', '-m', 'cross cutting with broken symbol')
			blocked = worktree_land(wt, run_tests=False, remove=False, leases_dir=root / 'leases', promote_snapshot=False)
			self.assertFalse(blocked['landed'], blocked)
			self.assertEqual('python_integrity', blocked['stage'])
			self.assertIn('BrokenCrossSym', blocked['error'])
			(wt / 'scripts/mod_5.py').write_text('def fn_5() -> int:\n\treturn 15\n', encoding='utf-8')
			_git(wt, 'add', 'scripts/mod_5.py')
			_git(wt, 'commit', '-m', 'fix broken symbol')
			# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
			landed = worktree_land(wt, run_tests=False, no_tests_reason='Isolated cross-cutting python-integrity fixture validates static checks only.', remove=True, leases_dir=root / 'leases', promote_snapshot=False)
			self.assertTrue(landed['valid'], landed)
			self.assertTrue(landed['landed'], landed)
if '__main__' == __name__:
	unittest.main()
