# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = HARNESS_ROOT / 'scripts'
TESTS = HARNESS_ROOT / 'tests'
for _p in (SCRIPTS, TESTS):
	if str(_p) not in sys.path:
		sys.path.insert(0, str(_p))
from git_fixture_cache import clone_template_git_repo
# @used-by :func:`_seed_harness_git_repo()`
# @used-by :meth:`RuntimeSnapshotTests.test_broken_head_rejected_by_validation_preserving_current()`
# @used-by :meth:`RuntimeSnapshotTests.test_ensure_hooks_uses_deployed_immutable_git_hooks_dir()`
# @used-by :meth:`RuntimeSnapshotTests.test_lkg_fallback_runs_previous_release_when_current_crashes()`
# @used-by :meth:`RuntimeSnapshotTests.test_release_rotation_keeps_latest_five_and_retains_lkg()`
# @used-by :meth:`RuntimeSnapshotTests.test_worktree_land_promotes_runtime_snapshot_after_merge()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True)
	return (proc.stdout or '').strip()
# @used-by :meth:`RuntimeSnapshotTests.test_broken_head_rejected_by_validation_preserving_current()`
# @used-by :meth:`RuntimeSnapshotTests.test_ensure_hooks_uses_deployed_immutable_git_hooks_dir()`
# @used-by :meth:`RuntimeSnapshotTests.test_lkg_fallback_runs_previous_release_when_current_crashes()`
# @used-by :meth:`RuntimeSnapshotTests.test_promote_exports_snapshot_surviving_live_tree_corruption_and_preserving_anchor()`
# @used-by :meth:`RuntimeSnapshotTests.test_release_rotation_keeps_latest_five_and_retains_lkg()`
# @used-by :meth:`RuntimeSnapshotTests.test_worktree_land_promotes_runtime_snapshot_after_merge()`
def _seed_harness_git_repo(base: Path) -> Path:
	repo = base / 'proj/\u2c0f/\u227b/\u2655/\u26ef'
	# 2026-11-26 "Cache template Git repositories and in-process CLI helpers in slow test fixtures": https://github.com/dmitry-ai/harness/issues/355
	clone_template_git_repo(repo)
	(repo / 'scripts/agent_tools/gates').mkdir(parents=True, exist_ok=True)
	(repo / 'paths.json').write_text((HARNESS_ROOT / 'paths.json').read_text(encoding='utf-8'), encoding='utf-8')
	(repo / 'runtime.json').write_text((HARNESS_ROOT / 'runtime.json').read_text(encoding='utf-8'), encoding='utf-8')
	(repo / 'scripts/agent_tools/__init__.py').write_text('', encoding='utf-8')
	(repo / 'scripts/agent_tools/gates/__init__.py').write_text('def discover_pre_tool_gates():\n\treturn []\n', encoding='utf-8')
	for rel in ('scripts/agent_tools/path_cache.py', 'scripts/agent_tools/path_registry.py', 'scripts/agent_tools/runtime_snapshot.py'):
		src = HARNESS_ROOT / rel
		if src.is_file():
			(repo / rel).write_text(src.read_text(encoding='utf-8'), encoding='utf-8')
	slop_src = (
		'import json\nimport sys\n'
		'def main():\n'
		'\traw = sys.stdin.read()\n'
		'\tdata = json.loads(raw) if raw.strip() else {}\n'
		'\tcontent = (data.get("toolCall") or {}).get("args", {}).get("Content", "")\n'
		'\tdec = {"decision": "deny", "reason": "SNAP-SLOP-DENY"} if "BAD_SLOP" in content else {"decision": "allow"}\n'
		'\tsys.stdout.write(json.dumps(dec))\n'
		'if "__main__" == __name__:\n\tmain()\n'
	)
	allow_src = 'import json\nimport sys\nif "__main__" == __name__:\n\tsys.stdout.write(json.dumps({"decision": "allow"}))\n'
	shim_src = 'import sys\nif "__main__" == __name__:\n\traise SystemExit(0)\n'
	(repo / 'scripts/check_markdown_slop.py').write_text(slop_src, encoding='utf-8')
	(repo / 'scripts/check_rules_and_server_gate.py').write_text(allow_src, encoding='utf-8')
	(repo / 'scripts/check_pre_invocation.py').write_text(allow_src, encoding='utf-8')
	(repo / 'scripts/check_stop_gate.py').write_text(allow_src, encoding='utf-8')
	(repo / 'scripts/git_shim.py').write_text(shim_src, encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '-m', 'init')
	return repo
# 2026-11-24
# "Deploy immutable Harness runtime snapshots with LKG fallback":
# https://github.com/dmitry-ai/harness/issues/184
class RuntimeSnapshotTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_broken_head_rejected_by_validation_preserving_current(self) -> None:
		from agent_tools.runtime_snapshot import promote_runtime_snapshot
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _seed_harness_git_repo(root)
			store = root / 'store'
			ok1 = promote_runtime_snapshot(repo, store_dir=store)
			self.assertTrue(ok1['valid'], ok1)
			sha1 = ok1['commit_sha']
			(repo / 'scripts/check_markdown_slop.py').write_text('def broken(:\n\tpass\n', encoding='utf-8')
			_git(repo, 'add', 'scripts/check_markdown_slop.py')
			_git(repo, 'commit', '-m', 'broken syntax')
			bad_syntax = promote_runtime_snapshot(repo, store_dir=store)
			self.assertFalse(bad_syntax['valid'])
			self.assertFalse(bad_syntax['promoted'])
			ptr = json.loads((store / 'current.json').read_text(encoding='utf-8'))
			self.assertEqual(ptr['current'], sha1)
			(repo / 'scripts/check_rules_and_server_gate.py').write_text('import nonexistent_pkg_for_smoke_test_999\n', encoding='utf-8')
			(repo / 'scripts/check_markdown_slop.py').write_text('import sys\n', encoding='utf-8')
			_git(repo, 'add', '.')
			_git(repo, 'commit', '-m', 'broken import')
			bad_imp = promote_runtime_snapshot(repo, store_dir=store)
			self.assertFalse(bad_imp['valid'])
			self.assertFalse(bad_imp['promoted'])
			ptr2 = json.loads((store / 'current.json').read_text(encoding='utf-8'))
			self.assertEqual(ptr2['current'], sha1)
	# @used-by :mod:`unittest`
	def test_ensure_hooks_uses_deployed_immutable_git_hooks_dir(self) -> None:
		from agent_tools.git_gate import GitRepoGate
		from agent_tools.runtime_snapshot import effective_git_hooks_dir, promote_runtime_snapshot
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _seed_harness_git_repo(root)
			store = root / 'store'
			res = promote_runtime_snapshot(repo, store_dir=store)
			self.assertTrue(res['valid'], res)
			gh_dir = effective_git_hooks_dir(store_dir=store)
			self.assertEqual(gh_dir, (store / 'git_hooks').resolve())
			self.assertTrue((gh_dir / 'harness_git_hook_launcher.py').is_file())
			self.assertTrue((gh_dir / 'pre-commit').is_file())
			prev_env = os.environ.get('HARNESS_RUNTIME_STORE')
			os.environ['HARNESS_RUNTIME_STORE'] = str(store)
			try:
				installed = GitRepoGate(repo).ensure_hooks()
				self.assertEqual(installed.resolve(), gh_dir)
				configured = _git(repo, 'config', '--local', '--get', 'core.hooksPath')
				self.assertEqual(Path(configured).resolve(), gh_dir)
			finally:
				if None is prev_env:
					os.environ.pop('HARNESS_RUNTIME_STORE', None)
				else:
					os.environ['HARNESS_RUNTIME_STORE'] = prev_env
	# @used-by :mod:`unittest`
	def test_lkg_fallback_runs_previous_release_when_current_crashes(self) -> None:
		from agent_tools.runtime_snapshot import harness_hook_runner_source, promote_runtime_snapshot
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _seed_harness_git_repo(root)
			store = root / 'store'
			r1 = promote_runtime_snapshot(repo, store_dir=store)
			sha1 = r1['commit_sha']
			(repo / 'scripts/extra.py').write_text('VAL = 2\n', encoding='utf-8')
			_git(repo, 'add', 'scripts/extra.py')
			_git(repo, 'commit', '-m', 'second release')
			r2 = promote_runtime_snapshot(repo, store_dir=store)
			sha2 = r2['commit_sha']
			self.assertNotEqual(sha1, sha2)
			r2_again = promote_runtime_snapshot(repo, store_dir=store)
			self.assertEqual(r2_again['previous'], sha1)
			(store / 'releases' / sha2 / 'scripts/check_markdown_slop.py').write_text('raise NameError("broken current release")\n', encoding='utf-8')
			runner = root / 'harness_hook_runner.py'
			runner.write_text(harness_hook_runner_source(repo, store_dir=store), encoding='utf-8')
			payload = json.dumps({'toolCall': {'name': 'write_file', 'args': {'Path': 'x.md', 'Content': 'BAD_SLOP'}}})
			proc = subprocess.run([sys.executable, str(runner), 'check_markdown_slop.py'], input=payload, text=True, encoding='utf-8', capture_output=True, timeout=30, check=False)
			self.assertEqual(0, proc.returncode, proc.stderr)
			self.assertEqual('deny', json.loads(proc.stdout)['decision'])
			self.assertTrue((store / 'fallback.log').is_file())
			self.assertIn(sha1, (store / 'fallback.log').read_text(encoding='utf-8'))
			(store / 'releases' / sha2 / 'scripts/git_shim.py').write_text('raise ImportError("broken git shim")\n', encoding='utf-8')
			gl = store / 'git_hooks/harness_git_hook_launcher.py'
			gproc = subprocess.run([sys.executable, str(gl), '--hook', 'pre-commit'], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=False)
			self.assertEqual(0, gproc.returncode, gproc.stderr)
			r_fd, w_fd = os.pipe()
			try:
				p_open = subprocess.run([sys.executable, str(gl), '--hook', 'pre-commit'], stdin=r_fd, capture_output=True, text=True, timeout=15, check=False)
				self.assertEqual(0, p_open.returncode, p_open.stderr)
			finally:
				os.close(r_fd)
				os.close(w_fd)
	# @used-by :mod:`unittest`
	def test_promote_exports_snapshot_surviving_live_tree_corruption_and_preserving_anchor(self) -> None:
		from agent_tools.runtime_snapshot import harness_hook_runner_source, promote_runtime_snapshot
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _seed_harness_git_repo(root)
			store = root / 'store'
			res = promote_runtime_snapshot(repo, store_dir=store)
			self.assertTrue(res['valid'], res)
			self.assertTrue(res['promoted'])
			sha = res['commit_sha']
			snap_meta = json.loads((store / 'releases' / sha / 'snapshot.json').read_text(encoding='utf-8'))
			self.assertEqual(snap_meta['canonical_primary'], repo.resolve().as_posix())
			runner_src = harness_hook_runner_source(repo, store_dir=store)
			self.assertTrue(runner_src.isascii())
			runner = root / 'harness_hook_runner.py'
			runner.write_text(runner_src, encoding='utf-8')
			(repo / 'scripts/agent_tools/path_registry.py').write_text('_BROKEN = OrderedDict()\n', encoding='utf-8')
			(repo / 'scripts/check_markdown_slop.py').write_text('def broken(:\n', encoding='utf-8')
			payload = json.dumps({'toolCall': {'name': 'write_file', 'args': {'Path': 'x.md', 'Content': 'BAD_SLOP'}}})
			proc = subprocess.run([sys.executable, str(runner), 'check_markdown_slop.py'], input=payload, text=True, encoding='utf-8', capture_output=True, timeout=30, check=False)
			self.assertEqual(0, proc.returncode, proc.stderr)
			self.assertEqual('deny', json.loads(proc.stdout)['decision'])
			probe_code = 'import json, sys; sys.path.insert(0, sys.argv[1]); import agent_tools.path_registry as pr; print(json.dumps([pr._CODE_ANCHOR.as_posix(), pr.DEFAULT_REGISTRY_FILE.as_posix()]))'
			aproc = subprocess.run([sys.executable, '-I', '-c', probe_code, str((store / 'releases' / sha / 'scripts').resolve())], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=30, check=True)
			lines = json.loads(aproc.stdout)
			self.assertEqual(lines[0], repo.resolve().as_posix())
			self.assertEqual(Path(lines[1]).resolve(), (store / 'releases' / sha / 'paths.json').resolve())
	# @used-by :mod:`unittest`
	def test_release_rotation_keeps_latest_five_and_retains_lkg(self) -> None:
		from agent_tools.runtime_snapshot import promote_runtime_snapshot
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _seed_harness_git_repo(root)
			store = root / 'store'
			shas = []
			for i in range(7):
				(repo / f'scripts/step_{i}.py').write_text(f'N = {i}\n', encoding='utf-8')
				_git(repo, 'add', f'scripts/step_{i}.py')
				_git(repo, 'commit', '-m', f'step {i}')
				res = promote_runtime_snapshot(repo, store_dir=store, keep=5)
				self.assertTrue(res['valid'], res)
				shas.append(res['commit_sha'])
			remaining = {p.name for p in (store / 'releases').iterdir() if p.is_dir()}
			self.assertLessEqual(len(remaining), 5)
			self.assertIn(shas[-1], remaining)
			self.assertIn(shas[-2], remaining)
	# @used-by :mod:`unittest`
	def test_worktree_land_promotes_runtime_snapshot_after_merge(self) -> None:
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _seed_harness_git_repo(root)
			store = root / 'store'
			wt = Path(worktree_begin(repo, 'snap-land', worktrees_dir=root / 'wts')['worktree'])
			(wt / 'scripts/landed.py').write_text('LANDED = True\n', encoding='utf-8')
			_git(wt, 'add', 'scripts/landed.py')
			_git(wt, 'commit', '-m', 'landed change')
			land = worktree_land(wt, run_tests=False, remove=True, leases_dir=root / 'leases', promote_snapshot=True, snapshot_store=store)
			self.assertTrue(land['landed'], land)
			self.assertTrue(land['runtime_snapshot']['promoted'], land)
			ptr = json.loads((store / 'current.json').read_text(encoding='utf-8'))
			self.assertEqual(ptr['current'], land['head'])
if '__main__' == __name__:
	unittest.main()
