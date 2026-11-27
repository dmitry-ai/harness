# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.PolyglotTestRunner import PolyglotTestRunner
from Df.Harness.lib.worktree import dfh_fail_land, dfh_git_exec
from agent_tools.path_registry import project_paths
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreeRebaseVerifier:
	# @used-by :func:`agent_tools.worktree_flow._rebase_and_test()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__land_under_lease()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__run_optimistic_loop()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_git.DfHarnessS11Wave2CCovGitTests.test_worktree_lock_finder_rebase_and_removal_guard()`
	def __init__(self, main_repo: Path, wt_path: Path, branch: str, target_branch: str, *, run_tests: bool, workers: int | None, no_tests_reason: str | None=None, git_exec_fn=None, polyglot_test_fn=None) -> None:
		self.__main_repo = main_repo
		self.__wt_path = wt_path
		self.__branch = branch
		self.__target_branch = target_branch
		self.__run_tests = run_tests
		self.__workers = workers
		self.__no_tests_reason = no_tests_reason
		self.__git_exec = git_exec_fn if None is not git_exec_fn else dfh_git_exec
		self.__polyglot_test = polyglot_test_fn
	# @used-by :meth:`WorktreeRebaseVerifier.__run_land_checks()`
	def __check_diff_coverage(self, test_runs: int, test_res: dict | None, plan: dict | None) -> dict | None:
		from agent_tools.doc5_replay_audit import verify_worktree_answer_gate_corpus
		from agent_tools.tdd.diff_coverage import verify_worktree_diff_coverage
		cov = verify_worktree_diff_coverage(self.__wt_path, self.__target_branch)
		if not cov.get('valid'):
			joined = ', '.join(cov.get('uncovered', ())[:8])
			cov_msg = f'Diff coverage timed out with uncovered functions: {joined}' if cov.get('timed_out') else f'Uncovered newly added production functions: {joined}'
			r: dict | None = self.__fail_land('diff_coverage', cov_msg, test_runs=test_runs, test_result=test_res, plan=plan)
		else:
			corpus = verify_worktree_answer_gate_corpus(self.__wt_path, self.__target_branch)
			if corpus.get('valid'):
				r = None
			else:
				bad = ', '.join([*(corpus.get('false_positives') or ()), *(corpus.get('false_negatives') or ())][:8]) or str(corpus.get('error') or 'corpus regression')
				r = self.__fail_land('answer_gate_corpus', f'Answer-gate feature-turn corpus regression: {bad}', test_runs=test_runs, test_result=test_res, plan=plan)
		return r
	# @used-by :meth:`WorktreeRebaseVerifier.__check_diff_coverage()`
	# @used-by :meth:`WorktreeRebaseVerifier.__run_land_checks()`
	# @used-by :meth:`WorktreeRebaseVerifier.verify()`
	def __fail_land(self, stage: str, error: str, *, test_runs: int=0, test_result: dict | None=None, plan: dict | None=None) -> dict:
		return dfh_fail_land(self.__main_repo, self.__wt_path, self.__branch, stage, error, test_runs=test_runs, test_result=test_result, plan=plan)
	# @used-by :meth:`WorktreeRebaseVerifier.verify()`
	def __run_land_checks(self) -> tuple[dict | None, int, dict | None, dict]:
		from agent_tools.tdd.diff_executability import resolve_land_test_plan
		plan = resolve_land_test_plan(self.__wt_path, self.__target_branch, run_tests=self.__run_tests, no_tests_reason=self.__no_tests_reason, project_root=project_paths(self.__main_repo).root)
		if plan['blocked_error']:
			r = (self.__fail_land('no_tests_blocked', str(plan['blocked_error']), plan=plan), 0, None, plan)
		else:
			eff_run = bool(plan['should_run_tests'])
			ok_tests, test_runs, test_res = self.__run_tests_suite(eff_run)
			if not ok_tests:
				stage = str((test_res or {}).get('failure_stage') or 'tests')
				msg = 'Host state mutated during sandboxed tests' if 'host_mutation' == stage else ('Sandboxed land tests timed out' if (test_res or {}).get('timed_out') else 'Full test suite failed on rebased worktree')
				err = self.__fail_land(stage, msg, test_runs=test_runs, test_result=test_res, plan=plan)
			else:
				err = self.__check_diff_coverage(test_runs, test_res, plan) if eff_run else None
			r = (err, test_runs, test_res, plan)
		return r
	# @used-by :meth:`WorktreeRebaseVerifier.__run_land_checks()`
	def __run_tests_suite(self, eff_run: bool) -> tuple[bool, int, dict | None]:
		tests_dir = self.__wt_path / 'tests'
		if not eff_run:
			r: tuple[bool, int, dict | None] = (True, 0, None)
		elif tests_dir.is_dir():
			from agent_tools.parallel_runner import run_parallel_tests
			res = run_parallel_tests(tests_dir, workers=self.__workers, failfast=True)
			r = (bool(res.get('ok')), 1, res)
		else:
			ok, res = self.__polyglot_test(self.__main_repo, self.__wt_path, base_ref=self.__target_branch) if None is not self.__polyglot_test else PolyglotTestRunner(self.__main_repo, self.__wt_path, base_ref=self.__target_branch).run()
			r = (ok, 1 if None is not res else 0, res)
		return r
	# @used-by :func:`agent_tools.worktree_flow._rebase_and_test()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__land_under_lease()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__run_optimistic_loop()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_git.DfHarnessS11Wave2CCovGitTests.test_worktree_lock_finder_rebase_and_removal_guard()`
	def verify(self) -> tuple[dict | None, int, dict | None, dict | None]:
		from agent_tools.python_integrity import verify_worktree_python_changes
		from agent_tools.xref_gate import verify_worktree_xref_changes
		reb = self.__git_exec(self.__wt_path, 'rebase', self.__target_branch)
		if 0 != reb.returncode:
			self.__git_exec(self.__wt_path, 'rebase', '--abort')
			r: tuple[dict | None, int, dict | None, dict | None] = (self.__fail_land('rebase', reb.stderr.strip() or reb.stdout.strip()), 0, None, None)
		else:
			py_errs = verify_worktree_python_changes(self.__wt_path, self.__target_branch)
			if py_errs:
				r = (self.__fail_land('python_integrity', '; '.join(py_errs[:5])), 0, None, None)
			else:
				xref_errs = verify_worktree_xref_changes(self.__wt_path, self.__target_branch)
				r = (self.__fail_land('xref_integrity', '; '.join(xref_errs[:5])), 0, None, None) if xref_errs else self.__run_land_checks()
		return r
