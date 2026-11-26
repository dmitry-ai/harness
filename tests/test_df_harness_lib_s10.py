# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import sys
import tempfile
import types
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# @used-by :mod:`unittest`
class DfHarnessLibS10Tests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_trace_and_timesheet_helpers(self) -> None:
		from Df.Harness.lib.platform import dfh_timesheet_add_cat
		from Df.Harness.lib.trace import dfh_cmd_from_call, dfh_read_ag_rows, dfh_row_outputs
		call = {'name': 'run_command', 'args': {'CommandLine': 'python harness.py status'}}
		self.assertEqual('python harness.py status', dfh_cmd_from_call(call))
		self.assertEqual('', dfh_cmd_from_call({'name': 'read_file', 'args': {'Path': 'a.py'}}))
		rows = [
			{'type': 'PLANNER_RESPONSE', 'tool_calls': [call]},
			{'type': 'GENERIC', 'content': 'out-1'},
			{'type': 'GENERIC', 'content': 'out-2'},
			{'type': 'PLANNER_RESPONSE', 'content': 'next'},
			{'type': 'GENERIC', 'content': 'out-3'},
		]
		self.assertEqual(['out-1', 'out-2'], dfh_row_outputs(rows, 0))
		with tempfile.TemporaryDirectory() as tmp:
			tp = Path(tmp) / 'transcript.jsonl'
			tp.write_text('{"type":"USER_INPUT"}\nnot-json\n{"type":"GENERIC"}\n', encoding='utf-8')
			self.assertEqual([{'type': 'USER_INPUT'}, {'type': 'GENERIC'}], dfh_read_ag_rows(tp))
		cats: dict[str, dict] = {}
		dfh_timesheet_add_cat(cats, 'test_runs', 1.2346)
		dfh_timesheet_add_cat(cats, 'test_runs', -2.0)
		self.assertEqual({'test_runs': {'count': 2, 'wall_s': 1.235}}, cats)
	# @used-by :mod:`unittest`
	def test_cli_journal_and_project_helpers(self) -> None:
		from Df.Harness.lib.cli import dfh_collect_urls, dfh_default_workers
		from Df.Harness.lib.journal import dfh_strip_local_file_scheme, dfh_turns_dir
		from Df.Harness.lib.project import dfh_is_skipped_rel, dfh_rewrite_json_file, dfh_rewrite_value
		ns = types.SimpleNamespace(urls_pos=['https://a.example'], url_list=[' https://b.example '], url='https://c.example')
		self.assertEqual(['https://a.example', 'https://b.example', 'https://c.example'], dfh_collect_urls(ns))
		with self.assertRaises(ValueError):
			dfh_collect_urls(types.SimpleNamespace(urls_pos=[], url_list=[], url=None), require_nonempty=True)
		self.assertGreaterEqual(dfh_default_workers(6), 2)
		self.assertLessEqual(dfh_default_workers(6), 6)
		self.assertEqual('C:/work/a.md', dfh_strip_local_file_scheme('file:///C:/work/a.md  \n'))
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			self.assertEqual(root / '\ua616/data/turns', dfh_turns_dir(root))
			jf = root / 'state.json'
			jf.write_text(json.dumps({'path': 'C:/old/a', 'keep': 'C:/old/b'}), encoding='utf-8')
			self.assertTrue(dfh_rewrite_json_file(jf, [('C:/old', 'C:/new')], preserve_keys=('keep',)))
			loaded = json.loads(jf.read_text(encoding='utf-8'))
			self.assertEqual({'path': 'C:/new/a', 'keep': 'C:/old/b'}, loaded)
			self.assertEqual({'C:/new/k': ['C:/new/v']}, dfh_rewrite_value({'C:/old/k': ['C:/old/v']}, [('C:/old', 'C:/new')]))
		self.assertTrue(dfh_is_skipped_rel(Path('\ua616/data/scratch/a.md')))
		self.assertTrue(dfh_is_skipped_rel(Path('dir/x.lock')))
		self.assertFalse(dfh_is_skipped_rel(Path('\ua616/KB/Analysis.json')))
	# @used-by :mod:`unittest`
	def test_harness_callers_delegate_to_df_harness_helpers(self) -> None:
		from agent_tools import cli_command_grounding, cli_domains, doc5_context, project_rename_state, shadow_replay_clone, suite_runner, verification_observability
		from agent_tools.perf import suite_profiler, timesheet_ag, timesheet_codex
		call = {'name': 'exec_command', 'arguments': '{"cmd": "pytest -x"}'}
		self.assertEqual('pytest -x', cli_command_grounding._cmd_from_tool_call(call))
		self.assertEqual('pytest -x', doc5_context._cmd_from_call(call))
		self.assertEqual('pytest -x', verification_observability._cmd_from_call(call))
		rows = [{'type': 'PLANNER_RESPONSE'}, {'type': 'GENERIC', 'content': 'ok'}, {'type': 'USER_INPUT'}]
		self.assertEqual(['ok'], cli_command_grounding._collect_row_outputs(rows, 0))
		self.assertEqual(['ok'], doc5_context._row_outputs(rows, 0))
		self.assertEqual(['ok'], verification_observability._row_outputs(rows, 0))
		self.assertEqual(['https://x.test'], cli_domains._collect_urls(types.SimpleNamespace(urls_pos=['https://x.test'], url_list=[], url=None)))
		self.assertLessEqual(suite_profiler._default_workers(), 6)
		self.assertLessEqual(suite_runner._default_workers(), 8)
		c1, c2 = ({}, {})
		timesheet_ag._add_cat(c1, 'git', 0.5)
		timesheet_codex._add_cat(c2, 'git', 0.5)
		self.assertEqual(c1, c2)
		self.assertEqual({'k': 'B/x'}, project_rename_state._rewrite_value({'k': 'a/x'}, [('A', 'B')]))
		self.assertEqual({'k': 'B/x', 'p': 'a/x'}, shadow_replay_clone._rewrite_value({'k': 'a/x', 'p': 'a/x'}, [('A', 'B')], preserve_keys=('p',)))
		self.assertTrue(shadow_replay_clone._is_skipped_rel(Path('a.lock')))
	# @used-by :mod:`unittest`
	def test_hook_and_transcript_callers_delegate_to_df_harness(self) -> None:
		from Df.Harness.lib import journal as dfh_journal
		from Df.Harness.lib.trace import dfh_read_ag_rows
		from agent_tools.meta import transcripts
		import check_pre_invocation
		import check_stop_gate
		with patch.object(dfh_journal, 'dfh_strip_local_file_scheme', wraps=dfh_journal.dfh_strip_local_file_scheme) as m_strip:
			self.assertEqual('C:/work/a.md', check_stop_gate._strip_local_file_scheme('file:///C:/work/a.md  \n'))
			self.assertGreaterEqual(m_strip.call_count, 1)
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			with patch.object(dfh_journal, 'dfh_turns_dir', wraps=dfh_journal.dfh_turns_dir) as m_turns:
				self.assertEqual(root / '\ua616/data/turns', check_stop_gate._turns_dir(root))
				self.assertEqual(root / '\ua616/data/turns', check_pre_invocation._turns_dir(root))
				self.assertEqual(2, m_turns.call_count)
			tp_bad = root / 'bad.jsonl'
			tp_bad.write_text('{"type":"USER_INPUT"}\nnot-json\n{"type":"GENERIC"}\n', encoding='utf-8')
			with patch.object(transcripts, 'dfh_read_ag_rows', wraps=dfh_read_ag_rows) as m_rows:
				self.assertEqual([{'type': 'USER_INPUT'}, {'type': 'GENERIC'}], transcripts._read_ag_rows(tp_bad))
				self.assertEqual(1, m_rows.call_count)
			tp_ok = root / 'ok.jsonl'
			tp_ok.write_text('{"type":"USER_INPUT"}\n', encoding='utf-8')
			self.assertEqual([{'type': 'USER_INPUT'}], transcripts._read_ag_rows(tp_ok))
if '__main__' == __name__:
	unittest.main()