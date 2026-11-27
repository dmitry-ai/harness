# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`unittest`
class DfHarnessS11Wave2bTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_gate_classes_enforce_python_and_pretool_checks(self) -> None:
		from Df.Harness.Gate.AskQuestionGate import AskQuestionGate
		from Df.Harness.Gate.CodeSizeAnalyzer import CodeSizeAnalyzer
		from Df.Harness.Gate.CodeStyleChecker import CodeStyleChecker
		from Df.Harness.Gate.PreToolRegistry import PreToolRegistry
		from Df.Harness.Gate.PythonIntegrity import PythonIntegrity
		bad_ask = AskQuestionGate().check('ask_question', {'questions': [{'question': 'Should we bypass Stop Gate?', 'options': ['Yes', 'No']}]}, {})
		self.assertIsNotNone(bad_ask)
		size = CodeSizeAnalyzer('def ok() -> int:\n\treturn 1\n').analyze()
		self.assertIsNone(size['syntax_error'])
		self.assertEqual(2, size['file_sloc'])
		style_errs = CodeStyleChecker('scripts/demo.py', 'def f(x):\n\tif x == None:\n\t\treturn 1\n\treturn 2\n').check()
		self.assertTrue(style_errs)
		int_errs = PythonIntegrity.check('scripts/bad.py', 'def boom():\n\treturn UnknownGlobalSym()\n')
		self.assertTrue(any(('UnknownGlobalSym' in e for e in int_errs)))
		self.assertEqual('allow', PreToolRegistry().run('unknown_tool', {}, {})['decision'])
	# @used-by :mod:`unittest`
	def test_meta_classes_render_headers_identity_transcripts_and_metrics(self) -> None:
		from Df.Harness.Meta.Blocks import Blocks
		from Df.Harness.Meta.Builders import Builders
		from Df.Harness.Meta.HeaderRenderer import HeaderRenderer
		from Df.Harness.Meta.MetricsSummarizer import MetricsSummarizer
		from Df.Harness.Meta.ProjectIdentity import ProjectIdentity
		from Df.Harness.Meta.TimestampFormatter import TimestampFormatter
		from Df.Harness.Meta.TranscriptReader import TranscriptReader
		rendered = HeaderRenderer({'Time': '2026-11-26 00:00:00 UTC+0', 'Project': {'Path': 'C:/demo'}}).render()
		self.assertIn('```json', rendered)
		self.assertEqual('00:01:05', TimestampFormatter.format_duration(65.0))
		self.assertIn('UTC', TimestampFormatter('2026-11-26T00:00:00+00:00').format_local())
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			self.assertEqual(root.name, ProjectIdentity(root).resolve()['Name'])
			req_p, res_p = Blocks(root / '\ua66e', [1]).step_paths()
			self.assertTrue(str(req_p).endswith('1.md') and str(res_p).endswith('1.md'))
			tr = root / 'transcript.jsonl'
			tr.write_text(json.dumps({'step_index': 1, 'type': 'USER_INPUT', 'created_at': '2026-11-26T00:00:00Z'}) + '\n' + json.dumps({'step_index': 2, 'type': 'PLANNER_RESPONSE', 'model': 'gemini-2.5-pro'}) + '\n', encoding='utf-8')
			self.assertEqual(1, TranscriptReader(tr).extract_ag_info(start_step=1)['turn_index'])
			self.assertEqual(1, MetricsSummarizer([tr]).summarize()['generations'])
			meta = Builders(root, env={}).build_github_issue(issue_url='https://github.com/dmitry-ai/harness/issues/381')
			self.assertEqual('https://github.com/dmitry-ai/harness/issues/381', meta['Issue'])
	# @used-by :mod:`unittest`
	def test_perf_and_test_runner_classes(self) -> None:
		from Df.Harness.Perf.AntigravityTimesheetAnalyzer import AntigravityTimesheetAnalyzer
		from Df.Harness.Perf.CodexTimesheetAnalyzer import CodexTimesheetAnalyzer
		from Df.Harness.Perf.SuiteProfiler import SuiteProfiler
		from Df.Harness.Perf.SuiteWorker import SuiteWorker
		from Df.Harness.Perf.TimedResult import TimedResult
		from Df.Harness.Perf.TimesheetBuilder import TimesheetBuilder
		from Df.Harness.Perf.TimesheetCommon import TimesheetCommon
		from Df.Harness.Perf.TrackedPopen import TrackedPopen
		from Df.Harness.TestRunner.ParallelRunner import ParallelRunner
		from Df.Harness.TestRunner.ProcessTree import ProcessTree
		from Df.Harness.TestRunner.PytestWorkstealRunner import PytestWorkstealRunner
		from Df.Harness.TestRunner.SuiteRunner import SuiteRunner
		from Df.Harness.TestRunner.WatchdogRunner import WatchdogRunner
		from Df.Harness.TestRunner.WorkerSemaphore import WorkerSemaphore
		self.assertTrue(issubclass(TimedResult, unittest.TestResult))
		self.assertTrue(hasattr(TrackedPopen, 'install'))
		self.assertTrue(hasattr(ProcessTree, 'POPEN_TREE_KWARGS'))
		self.assertEqual('unittest', PytestWorkstealRunner.resolve_runner_mode('unittest'))
		res = WatchdogRunner([sys.executable, '-c', 'print("ok")'], timeout_sec=15).run()
		self.assertEqual(0, res['returncode'])
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			lease = WorkerSemaphore(1, max_slots=2, slots_dir=root / 'slots').acquire()
			self.assertTrue(WorkerSemaphore.release(lease))
			tr = root / 'trace.jsonl'
			tr.write_text(json.dumps({'step_index': 0, 'type': 'USER_INPUT', 'created_at': '2026-11-26T00:00:00Z'}) + '\n', encoding='utf-8')
			_, rows = TimesheetCommon(tr).load_jsonl_rows()
			self.assertEqual(1, len(rows))
			self.assertIn('timestamps', AntigravityTimesheetAnalyzer(rows).analyze())
			self.assertIn('timestamps', CodexTimesheetAnalyzer([]).analyze())
			self.assertTrue(TimesheetBuilder(tr).build()['valid'])
			tmod = root / 'test_mini.py'
			tmod.write_text('import unittest\nclass M(unittest.TestCase):\n\tdef test_ok(self):\n\t\tself.assertEqual(1, 1)\n', encoding='utf-8')
			self.assertEqual(1, SuiteWorker(tmod, root).run()['tests_run'])
			self.assertTrue(SuiteProfiler(root, workers=1).profile()['valid'])
			self.assertTrue(ParallelRunner(root, workers=1, runner='unittest').run()['ok'])
			self.assertTrue(SuiteRunner(root, workers=1, runner='unittest').run()['ok'])
	# @used-by :mod:`unittest`
	def test_tdd_and_xref_classes(self) -> None:
		from Df.Harness.Tdd.DiffExecutability import DiffExecutability
		from Df.Harness.Xref.Engine import Engine
		from Df.Harness.Xref.Java.Lexer import Lexer as JavaLexer
		from Df.Harness.Xref.Js.Lexer import Lexer as JsLexer
		from Df.Harness.Xref.Python.Model import Model as PythonModel
		res = DiffExecutability().classify('scripts/demo.py', 'x = 1\n', '# comment\nx = 1\n')
		self.assertFalse(res['executable'])
		pinfo = PythonModel.index_file('scripts/demo.py', 'demo', 'def f():\n\treturn 1\n')
		self.assertEqual(1, len(pinfo['defs']))
		self.assertTrue(JavaLexer('class A {}').tokenize())
		self.assertTrue(JsLexer('export function f() { return 1; }').tokenize())
		with tempfile.TemporaryDirectory() as td:
			chk = Engine(Path(td)).check(lang='python')
			self.assertTrue(chk['valid'])
if '__main__' == __name__:
	unittest.main()
