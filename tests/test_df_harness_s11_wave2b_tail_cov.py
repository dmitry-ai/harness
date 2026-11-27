# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import cProfile
import json
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from Df.Harness.Gate.BulkSourceReadGate import BulkSourceReadGate
from Df.Harness.Gate.CodeSizeAnalyzer import CodeSizeAnalyzer
from Df.Harness.Gate.ExternalWriteGate import ExternalWriteGate
from Df.Harness.Gate.IssueCommentChecker import IssueCommentChecker
from Df.Harness.Gate.PreToolRegistry import PreToolRegistry
from Df.Harness.Gate.RepoTagGate import RepoTagGate
from Df.Harness.Gate.RulesAuditor import RulesAuditor
from Df.Harness.Gate.SubprocessHygieneChecker import SubprocessHygieneChecker
from Df.Harness.Perf.AntigravityTimesheetAnalyzer import AntigravityTimesheetAnalyzer
from Df.Harness.Perf.SuiteWorker import SuiteWorker
from Df.Harness.Tdd.CommentDiff import CommentDiff
from Df.Harness.Tdd.DiffContract import DiffContract
from Df.Harness.Tdd.DiffCoverage import DiffCoverage
from Df.Harness.Tdd.DiffExecutability import DiffExecutability
from Df.Harness.Tdd.Enforcement import Enforcement
from Df.Harness.Tdd.Evaluator import Evaluator
from Df.Harness.Tdd.EventsExtractor import EventsExtractor
from Df.Harness.Tdd.Exemption import Exemption
from Df.Harness.Tdd.MechanicalExemption import MechanicalExemption
from Df.Harness.Tdd.RatchetGuard import RatchetGuard
from Df.Harness.Tdd.SubstantiveTestChecker import SubstantiveTestChecker
from Df.Harness.Tdd.WorktreeScope import WorktreeScope
from Df.Harness.TestRunner.ParallelRunner import ParallelRunner
from Df.Harness.Xref.Java.Graph import Graph as JavaGraph
from Df.Harness.Xref.Java.Model import Model as JavaModel
from Df.Harness.Xref.Python.Graph import Graph as PyGraph
from Df.Harness.Xref.Python.Model import Model as PyModel
# 2026-11-27 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :func:`_init_repo()`
# @used-by :meth:`DfHarnessS11Wave2bTailCovTests.test_gate_registry_repo_tag_and_rules_auditor()`
# @used-by :meth:`DfHarnessS11Wave2bTailCovTests.test_mechanical_exemption_clean_disk_and_last_commit()`
# @used-by :meth:`DfHarnessS11Wave2bTailCovTests.test_tdd_diff_contract_coverage_and_executability()`
# @used-by :meth:`DfHarnessS11Wave2bTailCovTests.test_tdd_enforcement_evaluator_events_and_worktree()`
# @used-by :meth:`DfHarnessS11Wave2bTailCovTests.test_tdd_exemption_mechanical_ratchet_and_substantive()`
def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(['git', '--no-optional-locks', *args], cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=15, check=True)
# @used-by :meth:`DfHarnessS11Wave2bTailCovTests.test_gate_registry_repo_tag_and_rules_auditor()`
# @used-by :meth:`DfHarnessS11Wave2bTailCovTests.test_mechanical_exemption_clean_disk_and_last_commit()`
# @used-by :meth:`DfHarnessS11Wave2bTailCovTests.test_tdd_diff_contract_coverage_and_executability()`
# @used-by :meth:`DfHarnessS11Wave2bTailCovTests.test_tdd_enforcement_evaluator_events_and_worktree()`
# @used-by :meth:`DfHarnessS11Wave2bTailCovTests.test_tdd_exemption_mechanical_ratchet_and_substantive()`
def _init_repo(repo: Path) -> None:
	repo.mkdir(parents=True, exist_ok=True)
	_git(repo, 'init')
	_git(repo, 'branch', '-M', 'main')
	_git(repo, 'config', 'user.email', 't@example.com')
	_git(repo, 'config', 'user.name', 'T')
	(repo / 'a.py').write_text('x = 1\n', encoding='utf-8')
	(repo / 'b.py').write_text('y = 1\n', encoding='utf-8')
	(repo / 'tests').mkdir(exist_ok=True)
	(repo / 'tests/test_a.py').write_text('def test_a():\n\tassert 1 == 1\n', encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '-m', 'init')
class DfHarnessS11Wave2bTailCovTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_gate_bulk_size_external_issue_and_subproc(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			tmp = Path(td)
			tx = tmp / 'tx.jsonl'
			rows = [{'type': 'USER_INPUT', 'content': 'go'}, {'type': 'PLANNER', 'tool_calls': [{'name': 'read_file', 'args': {'Path': 'C:/a/KB/source.md'}}, {'name': 'write_file', 'args': {'Path': 'C:/a/\ua616/KB/analysis.md'}}, {'name': 'invoke_subagent', 'args': {}}]}]
			tx.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			bulk_res = BulkSourceReadGate().check('read_file', {'Path': 'C:/b/KB/source.md'}, {'transcriptPath': str(tx)})
			self.assertIsNone(bulk_res)
			size_res = CodeSizeAnalyzer("DATA = {\n\t'a': [1, -2],\n\t'b': (3, {4}),\n}\n").analyze()
			self.assertEqual(1, size_res['file_sloc'])
			upw = tmp / 'upw'
			(upw / '\ua616/data/turns').mkdir(parents=True)
			(upw / '\ua616/project.json').write_text('{}', encoding='utf-8')
			(upw / '\ua616/data/turns/t1.json').write_text(json.dumps({'status': 'open', 'requests': [{'text': 'Read only analysis'}]}), encoding='utf-8')
			ext_res = ExternalWriteGate().check('run_command', {'CommandLine': f'python df_github_issue.py create --repo o/r --body-file "{upw.as_posix()}/b.md"'})
			self.assertIsNotNone(ext_res)
			base_cls = 'A = 1\nB = 2\nC = 3\nD = 4\nclass Foo:\n\tdef a(self):\n\t\treturn 1\n\tdef b(self):\n\t\treturn 2\n'
			new_cls = 'A = 1\nB = 2\nC = 3\nD = 4\n# 2026-11-27 "t": https://github.com/o/r/issues/1\nclass Foo:\n\tdef a(self):\n\t\treturn 9\n\tdef b(self):\n\t\treturn 2\n'
			ic_errs = IssueCommentChecker('foo.py', new_cls, baseline_source=base_cls).check()
			self.assertTrue(any(('MISPLACED_ISSUE_COMMENT' in e for e in ic_errs)))
			sub_errs = SubprocessHygieneChecker(Path('tests/test_s.py'), "import subprocess\nsubprocess.run(['echo'], **{'stdin': subprocess.DEVNULL, 'timeout': 5})\n").check()
			self.assertEqual([], sub_errs)
	# @used-by :mod:`unittest`
	def test_gate_registry_repo_tag_and_rules_auditor(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			tmp = Path(td)
			disc = PreToolRegistry().discover(tool_name='ask_question')
			self.assertTrue(bool(disc))
			repo = tmp / 'repo'
			_init_repo(repo)
			_git(repo, 'remote', 'add', 'origin', 'https://github.com/o/r.git')
			_git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
			_git(repo, 'branch', '--set-upstream-to=origin/main', 'main')
			_git(repo, 'tag', '2026-11-27')
			sha = _git(repo, 'rev-parse', 'HEAD').stdout.strip()
			orig_run = subprocess.run
			fake_ls = subprocess.CompletedProcess(['git'], 0, stdout=b'abc\trefs/tags/2026-11-27\nabc\trefs/tags/2026-11-27^{}\n', stderr=b'')
			with patch('subprocess.run', side_effect=lambda cmd, *a, **kw: fake_ls if 'ls-remote' in cmd else orig_run(cmd, *a, **kw)):
				tag_rep = {'ok': '2026-11-27' == RepoTagGate(repo, sha, 'https://github.com/o/r/issues/1').verify()}
			self.assertTrue(tag_rep['ok'])
			prim = tmp / 'prim'
			_init_repo(prim)
			(prim / 'paths.json').write_text('{}', encoding='utf-8')
			(prim / 'rules').mkdir()
			(prim / 'rules/00-a.md').write_text('---\ntrigger: always_on\n---\n# A\n', encoding='utf-8')
			(prim / 'rules/01-b.md').write_text('---\ntrigger: always_on\n---\n# B\n', encoding='utf-8')
			_git(prim, 'add', 'rules/00-a.md', 'rules/01-b.md')
			w_err = RulesAuditor.check_shared_rule_edit('write_file', {'Path': str(prim / 'rules/00-a.md'), 'Content': '---\ntrigger: always_on\n---\n# A2\n'})
			e_err = RulesAuditor.check_shared_rule_edit('edit_file', {'Path': str(prim / 'rules/00-a.md'), 'Target': '# A', 'Replacement': '# A3'})
			s_errs = RulesAuditor.verify_staged(prim, ['rules/00-a.md'], use_index=True)
			self.assertIsNone(w_err)
			self.assertIsNone(e_err)
			self.assertIsInstance(s_errs, list)
	# 2026-11-27 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
	# @used-by :mod:`unittest`
	def test_mechanical_exemption_clean_disk_and_last_commit(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve() / 'repo'
			_init_repo(repo)
			_git(repo, 'remote', 'add', 'origin', 'https://github.com/o/r.git')
			(repo / '\ua616/data/turns').mkdir(parents=True, exist_ok=True)
			iss = 'https://github.com/o/r/issues/1'
			(repo / 'a.py').write_text('x = 2\n', encoding='utf-8')
			_git(repo, 'add', 'a.py')
			_git(repo, 'commit', '-m', iss)
			rec = MechanicalExemption.record_exemption(repo, repo=repo, issue_url=iss, pattern='x = 1', replacement='x = 2', reason='Mechanical constant migration approved for last-commit coverage', turn_key='tk2')
			self.assertTrue(rec['valid'])
			self.assertTrue(MechanicalExemption.is_git_file_exempt(repo, 'a.py', use_index=False, project_root=repo))
	# @used-by :mod:`unittest`
	def test_perf_ag_timesheet_and_parallel_runner_timeout(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			tmp = Path(td)
			rows = [
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'model': 'm1', 'input_tokens': 10, 'cache_read_tokens': 10, 'output_tokens': 5, 'created_at': '2026-11-27T10:00:00Z', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'pytest -x'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'created_at': '2026-11-27T10:00:01Z', 'content': 'Tool is running as a background task with task id: bg-99'},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'model': 'm1', 'input_tokens': 12, 'cache_read_tokens': 10, 'output_tokens': 5, 'created_at': '2026-11-27T10:00:03Z', 'content': 'Completed At: 2026-11-27T10:00:04Z'},
				{'step_index': 4, 'type': 'SYSTEM_MESSAGE', 'created_at': '2026-11-27T10:00:06Z', 'content': 'sender=bg-99 Task id "bg-99" finished with result:\n1 passed in 0.2s'},
			]
			ag_res = AntigravityTimesheetAnalyzer(rows).analyze()
			self.assertEqual(1, len(ag_res['commands']['bg_test_waits']))
			tmod = tmp / 'test_ok.py'
			tmod.write_text('import unittest\nclass T(unittest.TestCase):\n\tdef test_a(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
			with patch('subprocess.Popen.communicate', side_effect=subprocess.TimeoutExpired(['py'], 2.0)):
				pr_raw = ParallelRunner(tmp, modules=['test_ok'], workers=1, module_timeout=5.0, runner='unittest').run()
			pr_res = {'modules_run': pr_raw['total_modules']}
			self.assertEqual(1, pr_res['modules_run'])
	# @used-by :mod:`unittest`
	def test_perf_suite_worker_falls_back_when_cprofile_busy(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'tests').mkdir()
			tmod = root / 'tests/test_fb.py'
			tmod.write_text('import unittest\nclass T(unittest.TestCase):\n\tdef test_ok(self):\n\t\tself.assertEqual(2, 1 + 1)\n', encoding='utf-8')
			with patch.object(cProfile.Profile, 'runcall', side_effect=ValueError('Another profiling tool is already active')):
				wrep = SuiteWorker(tmod, tmod.parent, cprofile_top=5).run()
			self.assertEqual(1, wrep['tests_run'])
			self.assertTrue(bool(wrep['cprofile']))
	# @used-by :mod:`unittest`
	def test_tdd_diff_contract_coverage_and_executability(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td) / 'repo'
			_init_repo(repo)
			js_lex = CommentDiff.lex_language('javascript', 'const s = `a${1 + 2}b`;\nconst r = /x/g;\n')
			self.assertIsNotNone(js_lex)
			(repo / 'a.py').write_text('x = 2\n', encoding='utf-8')
			(repo / 'b.py').write_text('y = 2\n', encoding='utf-8')
			_git(repo, 'add', 'a.py', 'b.py')
			w_staged = DiffContract.check_staged_mixed_commit_warning(repo, ['a.py', 'b.py'], threshold=1)
			w_touched = DiffContract.check_touched_mixed_commit_warning(repo, ['a.py', 'b.py'], threshold=1)
			self.assertIsNone(w_staged)
			self.assertIsNone(w_touched)
			_git(repo, 'commit', '-m', 'c2')
			(repo / 'added.py').write_text('z = 3\n', encoding='utf-8')
			_git(repo, 'add', 'added.py')
			_git(repo, 'commit', '-m', 'c3')
			cat_clean = DiffExecutability.classify_git_path(repo, 'a.py')
			rng_raw = DiffExecutability.classify_git_range(repo, 'HEAD~1', 'HEAD')
			rng = {'files': rng_raw['executable_files']}
			self.assertEqual('executable', cat_clean)
			self.assertIn('added.py', rng['files'])
			(repo / 'scripts').mkdir()
			(repo / 'scripts/alpha_mod.py').write_text('def fn():\n\treturn 1\n', encoding='utf-8')
			for idx in range(1, 7):
				body = 'import alpha_mod\ndef test_k():\n\tassert 1 == 1\n' if 1 == idx else 'def test_k():\n\tassert 1 == 1\n'
				(repo / f'tests/test_{idx}.py').write_text(body, encoding='utf-8')
			sel = DiffCoverage.select_targeted_test_modules(repo, {'scripts/alpha_mod.py': [{'name': 'fn', 'start_line': 1, 'end_line': 2}]}, base_ref='HEAD')
			self.assertTrue(bool(sel))
	# @used-by :mod:`unittest`
	def test_tdd_enforcement_evaluator_events_and_worktree(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			tmp = Path(td)
			repo = tmp / 'repo'
			_init_repo(repo)
			enf_err = Enforcement().evaluate_pre_tool_use('write_file', {'Path': str(repo / 'tests/test_a.py'), 'Content': 'def test_a():\n\tassert 2 == 2\n'}, {'cwd': str(repo)})
			self.assertIsNotNone(enf_err)
			wt = tmp / 'wt'
			wt.mkdir()
			dot_git = (repo / '.git').as_posix()
			(wt / '.git').write_text(f'gitdir: {dot_git}\n', encoding='utf-8')
			wt_head = Enforcement.git_head_text(wt, 'a.py')
			self.assertEqual('x = 1\n', wt_head)
			(repo / 'tests/test_a.py').write_text('def test_a():\n\tassert 2 == 2\n', encoding='utf-8')
			_git(repo, 'add', 'tests/test_a.py')
			st_errs = Enforcement.verify_staged_diff(repo, ['tests/test_a.py'], use_index=True)
			self.assertTrue(bool(st_errs))
			evs = [
				{'kind': 'file_write', 'classification': 'production', 'path': str(repo / 'ex.py'), 'scope': str(repo), 'step': 1},
				{'kind': 'file_write', 'classification': 'production', 'path': str(repo / 'prod.py'), 'scope': str(repo), 'step': 2},
				{'kind': 'command', 'cmd': 'pytest', 'cwd': str(repo), 'step': 3, 'test_info': {'is_test_cmd': True, 'is_full_suite': True, 'targets': []}, 'outcome': {'is_failure': False, 'is_pass': False, 'exit_code': 1}},
			]
			ev_res = Evaluator(evs, require_final_full_green=True, project_root=repo, is_exempt_fn=lambda p, *a, **k: str(p).endswith('ex.py')).evaluate()
			self.assertFalse(ev_res['verified'])
			self.assertTrue(bool(ev_res.get('failfast_warnings')))
			acc: dict = {'tdd_events': []}
			wev = EventsExtractor.record_tool_write_event(acc, 1, str(repo / 'a.py'), cwd=repo, content='x = 1\n')
			ws_match = WorktreeScope.scope_matches_commit(str(repo), str(repo))
			self.assertIsNotNone(wev)
			self.assertTrue(ws_match)
	# @used-by :mod:`unittest`
	def test_tdd_exemption_mechanical_ratchet_and_substantive(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td) / 'repo'
			_init_repo(repo)
			_git(repo, 'remote', 'add', 'origin', 'https://github.com/o/r.git')
			iss = 'https://github.com/o/r/issues/1'
			(repo / 'a.py').write_text(f'# 2026-11-27 "t": {iss}\nx = 2\n', encoding='utf-8')
			_git(repo, 'add', 'a.py')
			gate = SimpleNamespace(root=repo, _extract_added_diff_urls=lambda _n: ({iss}, set()))
			ex_urls = Exemption.verify_staged_issue_urls(gate, ['a.py'], iss, project_root=repo)
			self.assertEqual({iss}, ex_urls)
			_git(repo, 'commit', '-m', iss)
			mech_part = MechanicalExemption.matches_any_recipes('a = foo + foo\n', 'a = bar + foo\n', [{'pattern': 'foo', 'replacement': 'bar'}])
			mech_clean = MechanicalExemption.is_git_file_exempt(repo, 'a.py', use_index=False)
			self.assertTrue(mech_part)
			self.assertFalse(mech_clean)
			ev_file = repo / '\ua616/KB/Evidence/GitHub/o__r/issue-1.json'
			ev_file.parent.mkdir(parents=True, exist_ok=True)
			ev_file.write_text(json.dumps({'body': 'RATCHET-OK: tests/test_a.py | Replacing obsolete signature assertion with updated behavior check.'}), encoding='utf-8')
			appr = RatchetGuard.find_approval('tests/test_a.py', repo_root=repo, project_root=repo, issue_urls=[iss])
			self.assertIsNotNone(appr)
			src_line = "(REPO_ROOT / 'tmp' / 'app.py').read_text()"
			sub_errs = SubstantiveTestChecker.source_text_assertion_issues(Path('tests/test_x.py'), [src_line], full_content=f'from pathlib import Path\nREPO_ROOT = Path(__file__).parent\n{src_line}\n', added_line_numbers={3})
			self.assertTrue(bool(sub_errs))
	# @used-by :mod:`unittest`
	def test_xref_java_and_python_tail_branches(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			tmp = Path(td)
			jrepo = tmp / 'jrepo'
			(jrepo / 'p').mkdir(parents=True)
			(jrepo / 'p/C.java').write_text('package p;\npublic class C implements UnknownA, UnknownB {\n\t/**\n\t * @see java.lang.Runnable#run()\n\t */\n\t@Override\n\tpublic void customWork() {}\n}\n', encoding='utf-8')
			(jrepo / 'p/E.java').write_text('package p;\npublic enum E {\n\tA, B;\n\tpublic void f() {}\n}\n', encoding='utf-8')
			jidx = JavaModel(jrepo).build_repo_index()
			jgraph = JavaGraph(jidx).build()
			self.assertIn('p.C#customWork()', jgraph)
			prepo = tmp / 'prepo'
			prepo.mkdir()
			(prepo / 'm.py').write_text('class MyErr(UnknownBase, Exception):\n\tdef work(self):\n\t\t# @uses :func:`m.helper()`\n\t\treturn 1\ndef helper():\n\treturn 2\n', encoding='utf-8')
			pidx = PyModel(prepo).build_repo_index()
			pgraph = PyGraph(pidx).build()
			self.assertIn('m.helper', pgraph)
if '__main__' == __name__:
	unittest.main()
