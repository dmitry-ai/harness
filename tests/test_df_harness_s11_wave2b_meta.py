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
class DfHarnessS11Wave2bMetaTests(unittest.TestCase):
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
			summary = MetricsSummarizer([tr]).summarize()
			self.assertEqual(1, summary['generations'])
			self.assertIn('tokens', summary)
			meta = Builders(root, env={}).build_github_issue(issue_url='https://github.com/dmitry-ai/harness/issues/381')
			self.assertEqual('https://github.com/dmitry-ai/harness/issues/381', meta['Issue'])
	# @used-by :mod:`unittest`
	def test_perf_classes_profile_and_build_timesheets(self) -> None:
		from Df.Harness.Perf.AntigravityTimesheetAnalyzer import AntigravityTimesheetAnalyzer
		from Df.Harness.Perf.CodexTimesheetAnalyzer import CodexTimesheetAnalyzer
		from Df.Harness.Perf.SuiteProfiler import SuiteProfiler
		from Df.Harness.Perf.SuiteWorker import SuiteWorker
		from Df.Harness.Perf.TimedResult import TimedResult
		from Df.Harness.Perf.TimesheetBuilder import TimesheetBuilder
		from Df.Harness.Perf.TimesheetCommon import TimesheetCommon
		from Df.Harness.Perf.TrackedPopen import TrackedPopen
		self.assertTrue(issubclass(TimedResult, unittest.TestResult))
		self.assertEqual('git', TrackedPopen.classify_proc_args(['git', 'status']))
		self.assertEqual('python', TrackedPopen.classify_proc_args(['python.exe', '-V']))
		self.assertEqual('other_proc', TrackedPopen.classify_proc_args(['cmd.exe']))
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
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
if '__main__' == __name__:
	unittest.main()
