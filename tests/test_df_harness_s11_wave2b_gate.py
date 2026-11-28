# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# @used-by :func:`_seed_gate_repo()`
def _git_cmd(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True)
	return (proc.stdout or '').strip()
# @used-by :meth:`DfHarnessS11Wave2bGateTests.test_gate_pretool_classes_cover_all_guards()`
def _make_answer_ctx() -> dict:
	return {
		'role': 'primary',
		'doc4_errs': ['d4'],
		'link_errs': [],
		'prob_errs': [],
		'source_errs': [],
		'lang_errs': [],
		'exec5_chk': {'verified': False, 'violations': [{'commands': ['git status']}]},
		'hook_crash_chk': {'verified': False, 'detail': 'crash'},
		'addon_obs_chk': {'verified': False, 'detail': 'addon'},
		'verification_observability_chk': {'verified': False, 'detail': 'shadow'},
		'http_chk': {'verified': False, 'violations': [{'commands': ['curl x']}]},
		'comp_chk': {'verified': False, 'unreread_analysis_sources': ['a.md']},
		'evicted_cited': ['ev.md'],
		'del_chk': {'verified': False, 'aa_partial_read_violations': ['part']},
		'issue_first_chk': {'verified': False, 'violations': ['if']},
		'lifecycle_chk': {'verified': False, 'violations': ['lc']},
		'scope_deferral_chk': {'verified': False, 'violations': ['sd']},
		'tdd_chk': {'verified': False, 'violations': ['tdd']},
		'wf_errs': [],
	}
# @used-by :meth:`DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
def _seed_gate_repo(base: Path) -> tuple[Path, str]:
	repo = base / 'r'
	repo.mkdir()
	_git_cmd(repo, 'init', '-b', 'main')
	_git_cmd(repo, 'config', 'user.email', 't@e.com')
	_git_cmd(repo, 'config', 'user.name', 'T')
	(repo / 'a.py').write_text('# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\ndef ok() -> int:\n\treturn 1\n', encoding='utf-8')
	(repo / 'rules').mkdir()
	(repo / 'rules/00-a.md').write_text('---\ntrigger: always_on\n---\n# A\n', encoding='utf-8')
	_git_cmd(repo, 'add', '.')
	_git_cmd(repo, 'commit', '-m', 'init')
	sha = _git_cmd(repo, 'rev-parse', 'HEAD')
	_git_cmd(repo, 'tag', '2026-11-26', sha)
	return (repo, sha)
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`unittest`
class DfHarnessS11Wave2bGateTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_gate_analyzers_and_checkers(self) -> None:
		from Df.Harness.Gate.AskQuestionGate import AskQuestionGate
		from Df.Harness.Gate.CodeSizeAnalyzer import CodeSizeAnalyzer
		from Df.Harness.Gate.CodeSizeChecker import CodeSizeChecker
		from Df.Harness.Gate.CodeStyleAnalyzer import CodeStyleAnalyzer
		from Df.Harness.Gate.CodeStyleChecker import CodeStyleChecker
		from Df.Harness.Gate.FailfastGate import FailfastGate
		from Df.Harness.Gate.PreToolRegistry import PreToolRegistry
		from Df.Harness.Gate.PythonIntegrity import PythonIntegrity
		bad_ask = AskQuestionGate().check('ask_question', {'questions': [{'question': 'Plan?', 'options': ['(Recommended) Defer phase 2 to next turn']}, {'question': 'Should we bypass Stop Gate?', 'options': ['Yes', 'No']}]}, {})
		self.assertIsNotNone(bad_ask)
		size = CodeSizeAnalyzer('from typing import override\n@override\ndef ok() -> int:\n\treturn 1\n').analyze()
		self.assertIsNone(size['syntax_error'])
		self.assertEqual(2, size['file_sloc'])
		self.assertTrue(CodeSizeChecker('scripts/s.py', 'def f(x):\n\treturn 1; return 2\n').check())
		self.assertFalse(CodeSizeChecker.is_legacy_oversized_baseline('scripts/s.py', 'x = 1\n'))
		self.assertFalse(CodeStyleAnalyzer('def f(x):\n\tif None is x:\n\t\treturn 1\n').analyze()['syntax_error'])
		self.assertTrue(CodeStyleChecker('scripts/demo.py', 'def f(x):\n\tif x == None:\n\t\treturn 1\n\treturn 2\n').check())
		self.assertTrue(any(('UnknownGlobalSym' in e for e in PythonIntegrity.check('scripts/bad.py', 'def boom():\n\treturn UnknownGlobalSym()\n'))))
		self.assertEqual('allow', PreToolRegistry().run('unknown_tool', {}, {})['decision'])
		deny, ow = FailfastGate().evaluate('run_command', {'CommandLine': 'pytest tests/test_a.py'})
		self.assertIsNone(deny)
		self.assertIsNotNone(ow)
	# @used-by :mod:`unittest`
	def test_gate_pretool_classes_cover_all_guards(self) -> None:
		from Df.Harness.Gate.AnswerChecksGate import AnswerChecksGate
		from Df.Harness.Gate.BatchSynthesisGate import BatchSynthesisGate
		from Df.Harness.Gate.BrowserMcpGate import BrowserMcpGate
		from Df.Harness.Gate.BulkSourceReadGate import BulkSourceReadGate
		from Df.Harness.Gate.CdpBypassGate import CdpBypassGate
		from Df.Harness.Gate.ExternalWriteGate import ExternalWriteGate
		from Df.Harness.Gate.GitWriteGate import GitWriteGate
		from Df.Harness.Gate.JournalWriteGate import JournalWriteGate
		from Df.Harness.Gate.RulesBudgetGate import RulesBudgetGate
		from Df.Harness.Gate.ScheduleGate import ScheduleGate
		from Df.Harness.Gate.SendMessageGate import SendMessageGate
		from Df.Harness.Gate.ServerHygieneGate import ServerHygieneGate
		from Df.Harness.Gate.StopChecksGate import StopChecksGate
		issues, checks = AnswerChecksGate().run(_make_answer_ctx())
		self.assertTrue(issues)
		self.assertFalse(checks['exec5'])
		self.assertIsNotNone(StopChecksGate().run({'status': 'open'}))
		self.assertIsNotNone(StopChecksGate().run({'status': 'prepared', 'prepared': {}, 'readiness_check': {'verified': True}, 'issue_first_check': {'verified': False}}))
		self.assertIsNotNone(StopChecksGate().run({'status': 'prepared', 'prepared': {}, 'readiness_check': {'verified': True}, 'code_lifecycle_check': {'verified': False}}))
		self.assertIsNotNone(StopChecksGate().run({'status': 'prepared', 'prepared': {}, 'readiness_check': {'verified': True}, 'tdd_check': {'verified': False}}))
		self.assertIsNotNone(BatchSynthesisGate().check('run_command', {'CommandLine': 'python build_analyses.py'}))
		self.assertIsNotNone(BrowserMcpGate().check('mcp_chrome_new_page', {}))
		self.assertIsNotNone(BrowserMcpGate().check('invoke_subagent', {'TypeName': 'browser', 'Prompt': 'http://127.0.0.1:9222/json/version'}))
		self.assertEqual({}, BulkSourceReadGate.parse_call_args('bad'))
		self.assertIsNotNone(CdpBypassGate().check('read_file', {'Path': 'C:/tmp/DevToolsActivePort'}))
		self.assertIsNotNone(CdpBypassGate().check('write_file', {'Path': 'C:/tmp/x.py', 'Content': 'http://127.0.0.1:9222/devtools/page/1'}))
		self.assertIsNotNone(ExternalWriteGate().check('run_command', {'CommandLine': 'gh issue create --title x'}))
		gw_res = GitWriteGate().check('run_command', {'CommandLine': 'git commit --no-verify -m x'})
		self.assertIsNotNone(gw_res)
		self.assertIsNotNone(JournalWriteGate().check('write_file', {'Path': 'C:/p/\ua66e/\u227a/1.md'}))
		self.assertIsNotNone(RulesBudgetGate().check('write_file', {'Path': 'C:/p/.agents/rules/90-project.md', 'Content': 'a' * 4100}))
		self.assertIsNotNone(SendMessageGate().check('send_message', {'Message': '{"schema_version": 1, "claim_reviews": []}'}))
		self.assertIsNotNone(ServerHygieneGate().check('run_command', {'CommandLine': 'ssh host cp a b.bak'}))
		with tempfile.TemporaryDirectory() as td:
			tp = Path(td) / 'transcript.jsonl'
			tp.write_text(json.dumps({'type': 'USER_INPUT', 'content': 'do work'}) + '\n' + json.dumps({'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'pytest'}}]}) + '\n' + json.dumps({'type': 'GENERIC', 'content': 'Tool is running with task id: conv/task-1'}) + '\n', encoding='utf-8')
			self.assertIsNotNone(ScheduleGate().check('schedule', {'DurationSeconds': 10}, {'transcriptPath': str(tp)}))
	# @used-by :mod:`unittest`
	def test_gate_staged_and_repo_checks(self) -> None:
		from Df.Harness.Gate.CodeSizeStagedGate import CodeSizeStagedGate
		from Df.Harness.Gate.CodeStyleStagedGate import CodeStyleStagedGate
		from Df.Harness.Gate.IssueCommentStagedGate import IssueCommentStagedGate
		from Df.Harness.Gate.PythonIntegrity import PythonIntegrity
		from Df.Harness.Gate.RepoLinkGate import RepoLinkGate
		from Df.Harness.Gate.RepoLinkResolver import RepoLinkResolver
		from Df.Harness.Gate.RepoTagGate import RepoTagGate
		from Df.Harness.Gate.RulesAuditor import RulesAuditor
		from Df.Harness.Gate.RulesManifest import RulesManifest
		from Df.Harness.Gate.StagedGates import StagedGates
		from Df.Harness.Gate.SubprocessHygieneStagedGate import SubprocessHygieneStagedGate
		from Df.Harness.Gate.XrefStagedGate import XrefStagedGate
		from Df.Harness.Gate.XrefWorktreeGate import XrefWorktreeGate
		with tempfile.TemporaryDirectory() as td:
			repo, sha = _seed_gate_repo(Path(td).resolve())
			self.assertEqual([], CodeSizeStagedGate(repo, ['a.py'], use_index=False).verify())
			self.assertEqual([], CodeStyleStagedGate(repo, ['a.py'], use_index=False).verify())
			self.assertEqual([], IssueCommentStagedGate(repo, ['a.py'], use_index=False).verify())
			self.assertEqual([], SubprocessHygieneStagedGate(repo, ['a.py'], use_index=False).verify())
			self.assertEqual([], XrefStagedGate(repo, ['a.py'], use_index=False).verify())
			self.assertEqual([], XrefWorktreeGate(repo, 'main').verify())
			self.assertEqual([], StagedGates(repo, ['a.py'], use_index=False).verify())
			self.assertEqual([], PythonIntegrity.verify_directory(repo))
			self.assertEqual([], PythonIntegrity.verify_touched(repo, ['a.py']))
			self.assertEqual([], PythonIntegrity.verify_worktree(repo, 'main'))
			self.assertEqual('2026-11-26', RepoTagGate(repo, sha, 'https://github.com/o/r/issues/1').verify())
			self.assertTrue(RulesAuditor(repo).audit()['valid'])
			self.assertTrue(RulesManifest.render_codex_loader(repo))
			self.assertTrue(RulesManifest(repo).validate_for_doctor()[0])
			self.assertEqual([], RepoLinkGate.check_chat('see https://example.com', root=repo))
			self.assertEqual([], RepoLinkGate().verify_staged(repo, ['rules/00-a.md'], use_index=False))
			self.assertIsNone(RepoLinkResolver(repo).resolve_blob('https://example.com'))
	# @used-by :mod:`unittest`
	def test_gate_thin_pretool_shims_and_checkers(self) -> None:
		from Df.Harness.Gate.CodeSizePreToolGate import CodeSizePreToolGate
		from Df.Harness.Gate.CodeStylePreToolGate import CodeStylePreToolGate
		from Df.Harness.Gate.IssueCommentChecker import IssueCommentChecker
		from Df.Harness.Gate.IssueCommentPreToolGate import IssueCommentPreToolGate
		from Df.Harness.Gate.IssueFirstPreToolGate import IssueFirstPreToolGate
		from Df.Harness.Gate.SubprocessHygieneChecker import SubprocessHygieneChecker
		from Df.Harness.Gate.SubprocessHygienePreToolGate import SubprocessHygienePreToolGate
		from Df.Harness.Gate.TddPreToolGate import TddPreToolGate
		from Df.Harness.Gate.WorktreeIsolationGate import WorktreeIsolationGate
		from Df.Harness.Gate.XrefChecker import XrefChecker
		from Df.Harness.Gate.XrefPreToolGate import XrefPreToolGate
		self.assertTrue(SubprocessHygieneChecker('tests/test_x.py', 'import subprocess\nsubprocess.run(["echo"])\n').check())
		self.assertTrue(IssueCommentChecker('a.py', '# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\n# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk\nx = 1\n').check())
		self.assertTrue(XrefChecker('scripts/u.py', 'def f():\n\treturn 1\n').check())
		self.assertIsNone(CodeSizePreToolGate().check('read_file', {}, {}))
		self.assertIsNone(CodeStylePreToolGate().check('read_file', {}, {}))
		self.assertIsNone(IssueCommentPreToolGate().check('read_file', {}, {}))
		self.assertIsNone(IssueFirstPreToolGate().check('read_file', {}, {}))
		self.assertIsNone(SubprocessHygienePreToolGate().check('read_file', {}, {}))
		self.assertIsNone(TddPreToolGate().check('read_file', {}, {}))
		self.assertIsNone(WorktreeIsolationGate().check('read_file', {}, {}))
		self.assertIsNone(XrefPreToolGate().check('read_file', {}, {}))
	# @used-by :mod:`unittest`
	def test_gate_v4_arch_audit_and_pipeline_parity(self) -> None:
		from Df.Harness.Gate.AnswerChecksGate import AnswerChecksGate
		from Df.Harness.Gate.ArchAuditGate import ArchAuditGate
		from Df.Harness.Gate.PreToolRegistry import PreToolRegistry
		from Df.Harness.Gate.StopChecksGate import StopChecksGate
		arch_res = ArchAuditGate().check('read_file', {}, {})
		self.assertIsNone(arch_res)
		self.assertIn('arch_audit', PreToolRegistry.BUILTIN_TOOLS_MANIFEST)
		self.assertTrue(any(('architecture' == g[0] for g in AnswerChecksGate.ANSWER_GATES)))
		self.assertTrue(any(((35, 'arch_audit') == (g[0], g[1]) for g in StopChecksGate.STOP_GATES)))
		# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
		self.assertTrue(any(('problem_report' == g[0] for g in AnswerChecksGate.ANSWER_GATES)))
		self.assertTrue(any(((37, 'problem_report') == (g[0], g[1]) for g in StopChecksGate.STOP_GATES)))
		stop_prob = StopChecksGate().run({'status': 'prepared', 'prepared': {}, 'readiness_check': {'verified': True}, 'problem_report_check': {'verified': False}})
		self.assertIsNotNone(stop_prob)
		stop_arch = StopChecksGate().run({'status': 'prepared', 'prepared': {}, 'readiness_check': {'verified': True}, 'arch_audit_check': {'verified': False}})
		self.assertIsNotNone(stop_arch)
if '__main__' == __name__:
	unittest.main()
