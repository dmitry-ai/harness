# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
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
from agent_tools import links
from agent_tools.github_issue import _dirty_issue_first_files, _find_local_code_repo
from agent_tools.issue_lifecycle import origin_repo_slug
from git_fixture_cache import clone_template_git_repo
import check_markdown_slop
# 2026-11-23
# "Add isolated git worktree task workflow and worktree-scoped issue gates":
# https://github.com/dmitry-ai/harness/issues/165
class WorktreeFlowTests(unittest.TestCase):
	# @used-by :meth:`WorktreeFlowTests._init_repo()`
	# @used-by :meth:`WorktreeFlowTests.test_isolated_temp_project_ignores_unrelated_host_worktree_cwd()`
	# @used-by :meth:`WorktreeFlowTests.test_resolve_code_scope_keeps_active_worktree_for_new_files_and_falls_back_after_cleanup()`
	# @used-by :meth:`WorktreeFlowTests.test_two_parallel_worktrees_commit_and_land_with_single_test_run()`
	# @used-by :meth:`WorktreeFlowTests.test_worktree_land_aborts_when_tests_fail()`
	def _git(self, repo: Path, *args: str) -> str:
		proc = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True)
		return (proc.stdout or '').strip()
	# @used-by :meth:`WorktreeFlowTests.test_cli_worktree_begin_status_cleanup()`
	# @used-by :meth:`WorktreeFlowTests.test_origin_repo_slug_and_linked_worktree_detection()`
	# @used-by :meth:`WorktreeFlowTests.test_resolve_code_anchor_maps_linked_worktree_to_canonical_main_repo()`
	# @used-by :meth:`WorktreeFlowTests.test_two_parallel_worktrees_commit_and_land_with_single_test_run()`
	# @used-by :meth:`WorktreeFlowTests.test_worktree_land_aborts_when_tests_fail()`
	# @used-by :meth:`WorktreeFlowTests.test_worktree_scoped_issue_first_ignores_dirty_main_checkout()`
	def _init_repo(self, root: Path, *, with_tests: bool=True) -> Path:
		repo = root / 'repo'
		# 2026-11-26 "Cache template Git repositories and in-process CLI helpers in slow test fixtures": https://github.com/dmitry-ai/harness/issues/355
		clone_template_git_repo(repo, remote_url='https://github.com/owner/demo.git')
		(repo / 'README.md').write_text('# Demo\n', encoding='utf-8')
		if with_tests:
			tdir = repo / 'tests'
			tdir.mkdir()
			(tdir / 'test_base.py').write_text('import unittest\nclass BaseT(unittest.TestCase):\n\tdef test_ok(self):\n\t\tself.assertTrue(True)\n', encoding='utf-8')
		self._git(repo, 'add', '.')
		self._git(repo, 'commit', '-m', 'init')
		return repo
	# @used-by :mod:`unittest`
	def test_cli_worktree_begin_status_cleanup(self):
		from agent_tools.upwork_project import main as cli_main
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			repo = self._init_repo(root, with_tests=False)
			wt_dir = root / 'wts'
			self.assertEqual(cli_main(['worktree-begin', str(repo), '--task', 'demo-1', '--worktrees-dir', str(wt_dir)]), 0)
			self.assertTrue((wt_dir / 'demo-1').is_dir())
			self.assertEqual(cli_main(['worktree-status', str(repo)]), 0)
			self.assertEqual(cli_main(['worktree-cleanup', str(repo), str(wt_dir / 'demo-1')]), 0)
			self.assertFalse((wt_dir / 'demo-1').exists())
	# @used-by :mod:`unittest`
	def test_exec5_documents_worktree_and_landing_only_host_mutations(self):
		rule_doc = HARNESS_ROOT / 'rules/08-execution-and-tools.md'
		text = rule_doc.read_text(encoding='utf-8')
		self.assertEqual(links.validate_file(rule_doc, local_anchors=True, readable_links=True), [])
		self.assertEqual(check_markdown_slop.markdown_slop_issues(text), [])
		for token in ('worktree-begin', 'worktree-land', 'build-native', 'install-global'):
			self.assertIn(token, text)
	# @used-by :mod:`unittest`
	def test_origin_repo_slug_and_linked_worktree_detection(self):
		from agent_tools.worktree_flow import is_linked_worktree, worktree_begin, worktree_cleanup
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			repo = self._init_repo(root, with_tests=False)
			res = worktree_begin(repo, 'slug-check', worktrees_dir=root / 'wts')
			wt = Path(res['worktree'])
			self.assertFalse(is_linked_worktree(repo))
			self.assertTrue(is_linked_worktree(wt))
			self.assertEqual(origin_repo_slug(wt), 'owner/demo')
			worktree_cleanup(repo, wt)
	# @used-by :mod:`unittest`
	def test_two_parallel_worktrees_commit_and_land_with_single_test_run(self):
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			repo = self._init_repo(root, with_tests=True)
			wt_base = root / 'wts'
			leases = root / 'leases'
			wt_a = Path(worktree_begin(repo, 'task-a', worktrees_dir=wt_base)['worktree'])
			wt_b = Path(worktree_begin(repo, 'task-b', worktrees_dir=wt_base)['worktree'])
			# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
			(wt_a / 'a.py').write_text('VAL_A = 1\n', encoding='utf-8')
			self._git(wt_a, 'add', 'a.py')
			self._git(wt_a, 'commit', '-m', 'add a')
			(wt_b / 'b.py').write_text('VAL_B = 2\n', encoding='utf-8')
			self._git(wt_b, 'add', 'b.py')
			self._git(wt_b, 'commit', '-m', 'add b')
			land_a = worktree_land(wt_a, run_tests=True, remove=True, owner='a', leases_dir=leases)
			self.assertTrue(land_a['landed'])
			self.assertEqual(land_a['test_runs'], 1)
			land_b = worktree_land(wt_b, run_tests=True, remove=True, owner='b', leases_dir=leases)
			self.assertTrue(land_b['landed'])
			self.assertEqual(land_b['test_runs'], 1)
			self.assertTrue((repo / 'a.py').is_file())
			self.assertTrue((repo / 'b.py').is_file())
			self.assertFalse(wt_a.exists())
			self.assertFalse(wt_b.exists())
	# @used-by :mod:`unittest`
	def test_worktree_land_aborts_when_tests_fail(self):
		from agent_tools.landing_lease import lease_status
		from agent_tools.worktree_flow import worktree_begin, worktree_cleanup, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			repo = self._init_repo(root, with_tests=True)
			leases = root / 'leases'
			main_before = self._git(repo, 'rev-parse', 'main')
			wt = Path(worktree_begin(repo, 'bad-task', worktrees_dir=root / 'wts')['worktree'])
			(wt / 'tests/test_fail.py').write_text('import unittest\nclass Bad(unittest.TestCase):\n\tdef test_bad(self):\n\t\tself.assertEqual(1, 2)\n', encoding='utf-8')
			self._git(wt, 'add', 'tests/test_fail.py')
			self._git(wt, 'commit', '-m', 'add failing test')
			res = worktree_land(wt, run_tests=True, owner='bad', leases_dir=leases)
			self.assertFalse(res['landed'])
			self.assertEqual(self._git(repo, 'rev-parse', 'main'), main_before)
			self.assertTrue(lease_status(repo, leases_dir=leases)['free'])
			worktree_cleanup(repo, wt, force=True)
	# @used-by :mod:`unittest`
	def test_worktree_scoped_issue_first_ignores_dirty_main_checkout(self):
		from agent_tools.worktree_flow import worktree_begin, worktree_cleanup
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			repo = self._init_repo(root, with_tests=False)
			(repo / 'dirty.py').write_text('x = 1\n', encoding='utf-8')
			wt = Path(worktree_begin(repo, 'clean-wt', worktrees_dir=root / 'wts')['worktree'])
			self.assertEqual(_find_local_code_repo('owner/demo', repo_root=wt), wt.resolve())
			self.assertEqual(_dirty_issue_first_files('owner/demo', repo_root=wt), [])
			self.assertEqual(_dirty_issue_first_files('owner/demo', project_root=repo), ['dirty.py'])
			prev_cwd = os.getcwd()
			try:
				os.chdir(wt)
				self.assertEqual(_find_local_code_repo('owner/demo', project_root=repo), wt.resolve())
				self.assertEqual(_dirty_issue_first_files('owner/demo', project_root=repo), [])
			finally:
				os.chdir(prev_cwd)
			worktree_cleanup(repo, wt)
	# 2026-11-24
	# "Fix worktree scope resolution for new files in TDD classifier":
	# https://github.com/dmitry-ai/harness/issues/188
	# @used-by :mod:`unittest`
	def test_resolve_code_scope_keeps_active_worktree_for_new_files_and_falls_back_after_cleanup(self):
		from agent_tools.tdd.classifier import resolve_code_scope
		from agent_tools.worktree_flow import worktree_begin, worktree_cleanup
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			proj = root / 'proj'
			code_repo = proj / 'code'
			# 2026-11-26 "Cache template Git repositories and in-process CLI helpers in slow test fixtures": https://github.com/dmitry-ai/harness/issues/355
			clone_template_git_repo(code_repo)
			(code_repo / 'README.md').write_text('# Demo\n', encoding='utf-8')
			self._git(code_repo, 'add', '.')
			self._git(code_repo, 'commit', '-m', 'init')
			wt_base = proj / '\ua616/data/worktrees'
			wt = Path(worktree_begin(code_repo, 'new-file-scope', worktrees_dir=wt_base)['worktree'])
			new_prod = wt / 'scripts/brand_new_module.py'
			self.assertFalse(new_prod.exists())
			self.assertEqual(resolve_code_scope(new_prod), wt.resolve())
			worktree_cleanup(code_repo, wt, force=True)
			self.assertEqual(resolve_code_scope(new_prod), code_repo.resolve())
	# 2026-11-24
	# "Fix worktree scope resolution for new files in TDD classifier":
	# https://github.com/dmitry-ai/harness/issues/188
	# @used-by :mod:`unittest`
	def test_isolated_temp_project_ignores_unrelated_host_worktree_cwd(self):
		from agent_tools.issues.repo_locator import find_local_code_repo
		from agent_tools.worktree_flow import worktree_begin, worktree_cleanup
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			proj = root / 'isolated_proj'
			code_dir = proj / 'code'
			# 2026-11-26 "Cache template Git repositories and in-process CLI helpers in slow test fixtures": https://github.com/dmitry-ai/harness/issues/355
			clone_template_git_repo(code_dir, remote_url='https://github.com/dmitry-ai/harness.git')
			(code_dir / 'README.md').write_text('# Demo\n', encoding='utf-8')
			self._git(code_dir, 'add', '.')
			self._git(code_dir, 'commit', '-m', 'init')
			prev_cwd = os.getcwd()
			try:
				os.chdir(HARNESS_ROOT / 'tests')
				self.assertEqual(find_local_code_repo('dmitry-ai/harness', project_root=proj), code_dir.resolve())
			finally:
				os.chdir(prev_cwd)
	# 2026-11-24
	# "Fix worktree scope resolution for new files in TDD classifier":
	# https://github.com/dmitry-ai/harness/issues/188
	# @used-by :mod:`unittest`
	def test_resolve_code_anchor_maps_linked_worktree_to_canonical_main_repo(self):
		from agent_tools.path_cache import resolve_code_anchor
		from agent_tools.worktree_flow import worktree_begin, worktree_cleanup
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = self._init_repo(root, with_tests=False)
			wt = Path(worktree_begin(repo, 'anchor-wt', worktrees_dir=root / 'wts')['worktree'])
			self.assertEqual(resolve_code_anchor(wt), repo.resolve())
			self.assertEqual(resolve_code_anchor(repo), repo.resolve())
			worktree_cleanup(repo, wt, force=True)
if '__main__' == __name__:
	unittest.main()
