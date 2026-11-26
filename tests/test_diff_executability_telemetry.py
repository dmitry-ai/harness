# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
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
_APP_PY = '# header\nVAL = 1\ndef run() -> int:\n\treturn 1\n'
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_TEST_APP_PY = '# test header\nfrom pathlib import Path\nimport sys\nimport unittest\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\nfrom pkg.app import run\nclass AppT(unittest.TestCase):\n\tdef test_run(self) -> None:\n\t\tself.assertEqual(1, run())\n'
# @used-by :meth:`DiffExecutabilityTelemetryTests.test_worktree_land_attaches_telemetry_on_failed_landings()`
# @used-by :meth:`DiffExecutabilityTelemetryTests.test_worktree_land_emits_telemetry_for_non_executable_executable_and_override()`
def _commit_wt(wt: Path, rel: str, text: str, msg: str) -> None:
	(wt / rel).write_text(text, encoding='utf-8')
	_git(wt, 'add', rel)
	_git(wt, 'commit', '--no-verify', '-m', msg)
# @used-by :func:`_commit_wt()`
# @used-by :func:`_init_py_repo()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True, creationflags=_NO_WINDOW)
	return (proc.stdout or '').strip()
# @used-by :meth:`DiffExecutabilityTelemetryTests.test_evaluate_tdd_events_records_exempt_edits_without_state_transition()`
# @used-by :meth:`DiffExecutabilityTelemetryTests.test_worktree_land_attaches_telemetry_on_failed_landings()`
# @used-by :meth:`DiffExecutabilityTelemetryTests.test_worktree_land_emits_telemetry_for_non_executable_executable_and_override()`
def _init_py_repo(root: Path) -> Path:
	repo = root / 'repo'
	(repo / 'pkg').mkdir(parents=True)
	(repo / 'tests').mkdir(parents=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	_git(repo, 'remote', 'add', 'origin', 'https://github.com/owner/demo.git')
	(repo / '.git/info/exclude').write_text('\ua616/\n', encoding='utf-8')
	(repo / 'README.md').write_text('# Demo\n', encoding='utf-8')
	(repo / 'pkg/__init__.py').write_text('', encoding='utf-8')
	(repo / 'pkg/app.py').write_text(_APP_PY, encoding='utf-8')
	(repo / 'tests/test_app.py').write_text(_TEST_APP_PY, encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '--no-verify', '-m', 'init')
	return repo
class DiffExecutabilityTelemetryTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_evaluate_tdd_events_records_exempt_edits_without_state_transition(self) -> None:
		from agent_tools.tdd.evaluator import evaluate_tdd_events
		from agent_tools.tdd.events import build_command_tdd_event, build_file_write_tdd_event
		with tempfile.TemporaryDirectory() as td:
			repo = _init_py_repo(Path(td).resolve())
			test_f, prod_f, tests_dir, sk = (repo / 'tests/test_app.py', repo / 'pkg/app.py', repo / 'tests', str(repo))
			test_f.write_text(_TEST_APP_PY.replace('# test header', '# test header v2'), encoding='utf-8')
			prod_f.write_text(_APP_PY.replace('# header', '# header v2'), encoding='utf-8')
			res_test = evaluate_tdd_events([build_file_write_tdd_event(1, test_f, cwd=repo)], require_final_full_green=True, project_root=repo)
			self.assertTrue(res_test['verified'], res_test)
			sc_t = res_test['scopes'][sk]
			self.assertEqual('IDLE', sc_t['state'])
			self.assertFalse(sc_t['any_prod_edit'])
			self.assertEqual([], sc_t['written_tests'])
			self.assertEqual([{'classification': 'test', 'path': str(test_f), 'step': 1}], sc_t['exempt_edits'])
			res_prod = evaluate_tdd_events([build_file_write_tdd_event(2, prod_f, cwd=repo)], require_final_full_green=True, project_root=repo)
			self.assertTrue(res_prod['verified'], res_prod)
			sc_p = res_prod['scopes'][sk]
			self.assertEqual('IDLE', sc_p['state'])
			self.assertFalse(sc_p['any_prod_edit'])
			self.assertEqual([], sc_p['touched_prod_files'])
			self.assertEqual([{'classification': 'production', 'path': str(prod_f), 'step': 2}], sc_p['exempt_edits'])
			prod_f.write_text(_APP_PY.replace('VAL = 1', 'VAL = 2'), encoding='utf-8')
			real_test = repo / 'tests/test_extra.py'
			real_test.write_text('import unittest\nclass E(unittest.TestCase):\n\tdef test_e(self) -> None:\n\t\tself.assertEqual(2, 2)\n', encoding='utf-8')
			post_ev = [
				build_file_write_tdd_event(1, real_test, cwd=repo),
				build_command_tdd_event(2, f'python -m unittest "{real_test}"', ['Command exited with code 1.\nFAIL\n'], cwd=repo),
				build_file_write_tdd_event(3, prod_f, cwd=repo),
				build_command_tdd_event(4, f'python harness.py run-tests "{tests_dir}"', ['Command exited with code 0.\nOK\n'], cwd=repo),
				build_file_write_tdd_event(5, test_f, cwd=repo),
			]
			res_post = evaluate_tdd_events(post_ev, require_final_full_green=True, project_root=repo)
			self.assertTrue(res_post['verified'], res_post)
			sc_post = res_post['scopes'][sk]
			self.assertEqual('GREEN_IMPLEMENTING', sc_post['state'])
			self.assertNotIn(str(test_f), sc_post['written_tests'])
			self.assertEqual([{'classification': 'test', 'path': str(test_f), 'step': 5}], sc_post['exempt_edits'])
	# @used-by :mod:`unittest`
	def test_format_land_diff_telemetry_truncates_and_preserves_counts(self) -> None:
		from agent_tools import tdd, tdd_gate
		from agent_tools.tdd.diff_executability import DEFAULT_MAX_REPORTED_FILES, format_land_diff_telemetry
		self.assertEqual(50, DEFAULT_MAX_REPORTED_FILES)
		self.assertIs(format_land_diff_telemetry, tdd.format_land_diff_telemetry)
		self.assertIs(format_land_diff_telemetry, tdd_gate.format_land_diff_telemetry)
		self.assertEqual({}, format_land_diff_telemetry(None))
		plan = {
			'diff_info': {
				'category_counts': {'comment_only': 3, 'executable': 5, 'non_code': 2},
				'classification': 'executable',
				'executable_files': ['src/e5.py', 'src/e1.py', 'src/e4.py', 'src/e2.py', 'src/e3.py'],
				'is_executable': True,
				'non_executable_files': ['docs/n5.md', 'docs/n1.md', 'docs/n4.md', 'docs/n2.md', 'docs/n3.md'],
			},
			'test_skip_reason': None,
		}
		out = format_land_diff_telemetry(plan, max_files=3)
		self.assertEqual('executable', out['diff_classification'])
		self.assertIsNone(out['test_skip_reason'])
		self.assertEqual(['src/e1.py', 'src/e2.py', 'src/e3.py'], out['executable_files'])
		self.assertEqual(5, out['executable_file_count'])
		self.assertEqual(['docs/n1.md', 'docs/n2.md', 'docs/n3.md'], out['non_executable_files'])
		self.assertEqual(5, out['non_executable_file_count'])
		self.assertEqual({'comment_only': 3, 'executable': 5, 'non_code': 2}, out['diff_category_counts'])
	# @used-by :mod:`unittest`
	def test_worktree_land_attaches_telemetry_on_failed_landings(self) -> None:
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_py_repo(root)
			wt_base, leases = (root / 'wts', root / 'leases')
			wt = Path(worktree_begin(repo, 'fail-tel', worktrees_dir=wt_base)['worktree'])
			_commit_wt(wt, 'pkg/app.py', _APP_PY.replace('return 1', 'return 9'), 'break run')
			blocked = worktree_land(wt, run_tests=False, remove=False, owner='b1', leases_dir=leases, promote_snapshot=False)
			self.assertFalse(blocked['valid'])
			self.assertFalse(blocked['landed'])
			self.assertEqual('no_tests_blocked', blocked['stage'])
			self.assertEqual(0, blocked['test_runs'])
			self.assertIsNone(blocked['test_result'])
			self.assertEqual('executable', blocked['diff_classification'])
			self.assertIsNone(blocked['test_skip_reason'])
			self.assertEqual(['pkg/app.py'], blocked['executable_files'])
			self.assertEqual(1, blocked['executable_file_count'])
			self.assertEqual([], blocked['non_executable_files'])
			self.assertEqual(0, blocked['non_executable_file_count'])
			self.assertEqual({'executable': 1}, blocked['diff_category_counts'])
			failed = worktree_land(wt, run_tests=True, remove=False, owner='b2', leases_dir=leases, promote_snapshot=False)
			self.assertFalse(failed['valid'])
			self.assertFalse(failed['landed'])
			self.assertEqual('tests', failed['stage'])
			self.assertEqual(1, failed['test_runs'])
			self.assertIsNotNone(failed['test_result'])
			self.assertEqual('executable', failed['diff_classification'])
			self.assertIsNone(failed['test_skip_reason'])
			self.assertEqual(['pkg/app.py'], failed['executable_files'])
			self.assertEqual(1, failed['executable_file_count'])
			self.assertEqual([], failed['non_executable_files'])
			self.assertEqual(0, failed['non_executable_file_count'])
			self.assertEqual({'executable': 1}, failed['diff_category_counts'])
	# @used-by :mod:`unittest`
	def test_worktree_land_emits_telemetry_for_non_executable_executable_and_override(self) -> None:
		from agent_tools.worktree_flow import worktree_begin, worktree_land
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			repo = _init_py_repo(root)
			wt_base, leases = (root / 'wts', root / 'leases')
			cmt_py = _APP_PY.replace('# header', '# updated header')
			ws_py = cmt_py + '\n'
			exec_py = ws_py.replace('VAL = 1', 'VAL = 2')
			ov_py = exec_py.replace('VAL = 2', 'VAL = 3')
			reason = 'Audited emergency hotfix verified independently in isolated staging environment.'
			cases = (
				('doc-tel', 'README.md', '# Demo v2\n', True, None, 0, 'non_code', 'non_executable_diff:non_code', [], ['README.md'], {'non_code': 1}),
				('cmt-tel', 'pkg/app.py', cmt_py, True, None, 0, 'comment_only', 'non_executable_diff:comment_only', [], ['pkg/app.py'], {'comment_only': 1}),
				('ws-tel', 'pkg/app.py', ws_py, True, None, 0, 'whitespace_only', 'non_executable_diff:whitespace_only', [], ['pkg/app.py'], {'whitespace_only': 1}),
				('exec-tel', 'pkg/app.py', exec_py, True, None, 1, 'executable', None, ['pkg/app.py'], [], {'executable': 1}),
				('ov-tel', 'pkg/app.py', ov_py, False, reason, 0, 'executable', 'audited_no_tests_override', ['pkg/app.py'], [], {'executable': 1}),
			)
			for task, rel, content, run_t, no_r, exp_runs, exp_cls, exp_skip, exp_ef, exp_nef, exp_cnt in cases:
				wt = Path(worktree_begin(repo, task, worktrees_dir=wt_base)['worktree'])
				_commit_wt(wt, rel, content, task)
				res = worktree_land(wt, run_tests=run_t, no_tests_reason=no_r, remove=True, owner=task, leases_dir=leases, promote_snapshot=False)
				self.assertTrue(res['valid'] and res['landed'], f'{task}: {res}')
				self.assertEqual(exp_runs, res['test_runs'], task)
				self.assertEqual(1 == exp_runs, None is not res['test_result'], task)
				self.assertEqual(exp_cls, res['diff_classification'], task)
				self.assertEqual(exp_skip, res['test_skip_reason'], task)
				self.assertEqual(exp_ef, res['executable_files'], task)
				self.assertEqual(len(exp_ef), res['executable_file_count'], task)
				self.assertEqual(exp_nef, res['non_executable_files'], task)
				self.assertEqual(len(exp_nef), res['non_executable_file_count'], task)
				self.assertEqual(exp_cnt, res['diff_category_counts'], task)
if '__main__' == __name__:
	unittest.main()
