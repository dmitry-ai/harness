# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
_NO_WIN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :meth:`DfHarnessS11Wave2bTddCov2Tests.test_enforcement_pretool_and_staged_diff()`
# @used-by :meth:`DfHarnessS11Wave2bTddCov2Tests.test_exemption_mechanical_and_ratchet_guard()`
def _init_sample_repo(repo: Path) -> None:
	for args in (('init',), ('config', 'user.email', 't@example.com'), ('config', 'user.name', 'T')):
		subprocess.run(['git', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False, timeout=30, creationflags=_NO_WIN)
	(repo / 'scripts').mkdir()
	(repo / 'tests').mkdir()
	(repo / 'scripts/a.py').write_text('x = 1\n', encoding='utf-8')
	(repo / 'tests/test_a.py').write_text('import unittest\nclass A(unittest.TestCase):\n\tdef test_x(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
	for args in (('add', '.'), ('commit', '-m', 'init')):
		subprocess.run(['git', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False, timeout=30, creationflags=_NO_WIN)
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`unittest`
class DfHarnessS11Wave2bTddCov2Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_enforcement_pretool_and_staged_diff(self) -> None:
		from Df.Harness.Tdd.Enforcement import Enforcement
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			_init_sample_repo(repo)
			self.assertTrue(Enforcement.active_turn_issue_urls('# https://github.com/o/r/issues/1\nx = 2\n', 'x = 1\n'))
			(repo / 'scripts/a.py').write_text('x = 2\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'scripts/a.py'], stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=30, creationflags=_NO_WIN)
			self.assertTrue(Enforcement.verify_staged_diff(repo, ['scripts/a.py'], use_index=True))
			enf = Enforcement(event_extractor=lambda _p, _c: [])
			self.assertIsNotNone(enf.evaluate_pre_tool_use('write_file', {'Path': str(repo / 'scripts/a.py'), 'Content': 'x = 3\n'}, {'cwd': str(repo)}))
			self.assertIsNotNone(enf.evaluate_pre_tool_use('write_file', {'Path': str(repo / 'tests/test_a.py'), 'Content': 'def test_x():\n\tpass\n'}, {'cwd': str(repo)}))
			self.assertIsNotNone(enf.evaluate_pre_tool_use('run_command', {'CommandLine': f'echo x > "{repo}/scripts/a.py"'}, {'cwd': str(repo)}))
			self.assertIsNotNone(enf.evaluate_pre_tool_use('run_command', {'CommandLine': f'rm "{repo}/tests/test_a.py"'}, {'cwd': str(repo)}))
	# @used-by :mod:`unittest`
	def test_evaluator_and_events_extractor_with_bg_tasks(self) -> None:
		from Df.Harness.Tdd.Evaluator import Evaluator
		from Df.Harness.Tdd.EventsExtractor import EventsExtractor
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			wt = root / '\ua616/data/worktrees/w1'
			(wt / 'scripts').mkdir(parents=True)
			(wt / 'tests').mkdir(parents=True)
			tx = root / 'tx.jsonl'
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Fix bug'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(wt / 'tests/test_x.py'), 'Content': 'def test_a(): assert 1 == 1'}}, {'name': 'run_command', 'args': {'CommandLine': f'python -m pytest -x "{wt}/tests/test_x.py"'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Created file.'},
				{'step_index': 3, 'type': 'GENERIC', 'content': 'Tool is running as a background task with task id: c1/task-3'},
				{'step_index': 4, 'type': 'SYSTEM_MESSAGE', 'content': 'sender=c1/task-3 Task id "c1/task-3" finished with result:\nCommand exited with code 1.\n1 failed in 0.2s'},
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'write_file', 'args': {'Path': str(wt / 'scripts/x.py'), 'Content': 'x = 1\n'}}, {'name': 'run_command', 'args': {'CommandLine': 'git commit -m "https://github.com/o/r/issues/1"'}}]},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'tool call denied by pre-tool hook: REJECTED'},
				{'step_index': 7, 'type': 'GENERIC', 'content': 'Command exited with code 0.'},
				{'step_index': 8, 'type': 'PLANNER_RESPONSE', 'content': 'Done.'},
			]
			tx.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			evs = EventsExtractor(tx, cwd=wt).extract()
			self.assertTrue(evs)
			self.assertFalse(EventsExtractor.antigravity_segment_is_interrupted(rows))
			denied = EventsExtractor.is_denied_write_output(['tool call denied by pre-tool hook: REJECTED'])
			self.assertTrue(denied)
			norm_a = EventsExtractor.normalize_args_dict('{"a": "1"}')
			self.assertEqual({'a': '1'}, norm_a)
			unwrapped = EventsExtractor.unwrap_arg_value('"v"')
			self.assertEqual('v', unwrapped)
			ev_rep = Evaluator(evs, require_final_full_green=True, project_root=root, is_exempt_fn=lambda _p, _s, **_kw: False).evaluate()
			self.assertIn('verified', ev_rep)
			self.assertIsInstance(Evaluator.git_main_repo_root(WT_ROOT), Path)
	# @used-by :mod:`unittest`
	def test_exemption_mechanical_and_ratchet_guard(self) -> None:
		from Df.Harness.Tdd.Exemption import Exemption
		from Df.Harness.Tdd.MechanicalExemption import MechanicalExemption
		from Df.Harness.Tdd.RatchetGuard import RatchetGuard
		with tempfile.TemporaryDirectory() as td:
			repo = Path(td).resolve()
			_init_sample_repo(repo)
			rdir = repo / '\ua616/data/turns'
			rdir.mkdir(parents=True, exist_ok=True)
			(repo / 'scripts/a.py').write_text('x = 2\n', encoding='utf-8')
			subprocess.run(['git', '-C', str(repo), 'add', 'scripts/a.py'], stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=30, creationflags=_NO_WIN)
			rec = MechanicalExemption.record_exemption(repo, repo=repo, issue_url='https://github.com/o/r/issues/1', pattern='x = 1', replacement='x = 2', reason='Mechanical constant migration approved for test coverage', turn_key='tk1')
			self.assertTrue(rec['valid'])
			self.assertTrue(MechanicalExemption.is_mechanical_diff_exempt('x = 1\n', 'x = 2\n', repo_root=repo, message='https://github.com/o/r/issues/1', project_root=repo))
			self.assertTrue(MechanicalExemption.is_git_file_exempt(repo, 'scripts/a.py', use_index=True, message='https://github.com/o/r/issues/1', project_root=repo))
			self.assertTrue(Exemption.is_git_path_exempt(repo, 'scripts/a.py', use_index=True, message='https://github.com/o/r/issues/1', project_root=repo))
			self.assertTrue(Exemption.is_write_event_exempt(repo / 'scripts/a.py', str(repo), project_root=repo))
			self.assertEqual([], Exemption.filter_repo_turn_issue_urls(set(), {}, 'o/r'))
			gate = MagicMock(root=repo)
			gate._extract_added_diff_urls.return_value = {'https://github.com/o/r/issues/1'}
			staged_urls = Exemption.verify_staged_issue_urls(gate, ['scripts/a.py'], 'https://github.com/o/r/issues/1', project_root=repo)
			self.assertIsInstance(staged_urls, set)
			(rdir / 't1-ratchet-ok.json').write_text(json.dumps({'approvals': [{'file': 'tests/test_a.py', 'reason': 'Audited expectation update with full justification text'}]}), encoding='utf-8')
			self.assertTrue(RatchetGuard.load_turn_receipts(repo))
			self.assertIsNotNone(RatchetGuard.find_approval('tests/test_a.py', repo_root=repo, project_root=repo))
			self.assertTrue(RatchetGuard.match_target('tests/test_a.py', repo / 'tests/test_a.py'))
			self.assertTrue(RatchetGuard.parse_ratchet_ok_lines('RATCHET-OK: tests/test_a.py | Audited expectation update for test coverage'))
			r_ok, _ = RatchetGuard.validate_reason('Audited expectation update for test coverage')
			self.assertTrue(r_ok)
	# @used-by :mod:`unittest`
	def test_outcome_service_substantive_and_worktree_scope(self) -> None:
		from Df.Harness.Tdd.OutcomeParser import OutcomeParser
		from Df.Harness.Tdd.ServiceExempt import ServiceExempt
		from Df.Harness.Tdd.SubstantiveTestChecker import SubstantiveTestChecker
		from Df.Harness.Tdd.WorktreeScope import WorktreeScope
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			wt = root / '\ua616/data/worktrees/w1'
			log_f = root / 't.log'
			log_f.write_text('2 passed in 0.1s\n', encoding='utf-8')
			self.assertEqual(0, OutcomeParser([], task_log_paths=[log_f]).parse()['exit_code'])
			self.assertEqual(0, OutcomeParser.infer_exit_code_from_log_text('Ran 2 tests in 0.1s\nOK\n'))
			self.assertIsNotNone(OutcomeParser.uri_to_local_path('file:///C:/demo/a.log'))
			svc_ok = ServiceExempt().is_exempt('run_command', {'CommandLine': 'python harness.py answer-prepare .'}, {})
			self.assertTrue(svc_ok)
			py_bad = 'from pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\ndef _rd(p):\n\treturn (ROOT / p).read_text()\ndef test_src():\n\ttxt = _rd("scripts/a.py")\n\tself.assertIn("def f", txt)\n'
			self.assertTrue(SubstantiveTestChecker.source_text_assertion_issues('tests/test_bad.py', py_bad.splitlines(), full_content=py_bad))
			self.assertTrue(SubstantiveTestChecker.source_text_assertion_issues('tests/bad.test.js', ['const s = fs.readFileSync("src/a.js", "utf8"); expect(s).toContain("x");']))
			self.assertEqual(root, WorktreeScope.canonical_scope_path(f'{root.as_posix()}::wt:w1'))
			self.assertEqual((root, 'w1'), WorktreeScope.split_key(f'{root.as_posix()}::wt:w1'))
			self.assertTrue(WorktreeScope.scope_matches_commit(f'{root.as_posix()}::wt:w1', str(wt)))
			wt_match = WorktreeScope.worktree_command_matches({'cwd': str(wt), 'cmd': f'pytest "{wt}/tests/test_x.py"'}, f'{root.as_posix()}::wt:w1', False)
			self.assertIsNone(wt_match)
if '__main__' == __name__:
	unittest.main()
