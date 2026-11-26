# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix shadow-replay CLI matching and observability timing diagnostics":
# https://github.com/dmitry-ai/harness/issues/342
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import sys
import tempfile
import time
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import repo_wait, runtime, verification_observability as vo
from agent_tools.perf import timesheet_common
# @used-by :mod:`unittest`
class ObservabilityDiagnosticsTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_detect_shadow_replay_ignores_cli_arguments_and_matches_real_invocations(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			tx = base / 'tx.jsonl'
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Audit commands.'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python df_github_issue.py comment dmitry-ai/harness 279 --body "shadow-replay failed"'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Command exited with code 1.\n{"valid": false}'},
				{'step_index': 3, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python -c "print(\'shadow-replay\')"'}}]},
				{'step_index': 4, 'type': 'GENERIC', 'content': 'Command exited with code 1.'},
			]
			tx.write_text(''.join((json.dumps(r) + '\n' for r in rows)), encoding='utf-8')
			turn = {'start_step': 0, 'issue_actions': []}
			native = {'source_file': str(tx), 'turns': [turn]}
			self.assertEqual([], vo.detect_shadow_replay_runs(native, turn))
			self.assertTrue(vo.evaluate_verification_observability(base, native, turn, {}, 'Clean summary.  \n')['verified'])
			rows.extend([
				{'step_index': 5, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python "C:/tool/harness.py" shadow-replay "C:/proj" --exec-rename-domain ex.com'}}]},
				{'step_index': 6, 'type': 'GENERIC', 'content': 'Command exited with code 2.\n{"valid": false}'},
				{'step_index': 7, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python upwork_project.py shadow-replay "C:/proj"'}}]},
				{'step_index': 8, 'type': 'GENERIC', 'content': 'Command exited with code 0.\n{"valid": true}'},
			])
			tx.write_text(''.join((json.dumps(r) + '\n' for r in rows)), encoding='utf-8')
			runs = vo.detect_shadow_replay_runs(native, turn)
			self.assertEqual(2, len(runs), runs)
			self.assertTrue(runs[0]['failed'])
			self.assertTrue(runs[1]['passed'])
	# @used-by :mod:`unittest`
	def test_resolve_trace_source_populates_summary_db_from_journal_step(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			proj = base / 'proj'
			jfile = proj / '\ua66e/\u227a/1\u201320/1.md'
			jfile.parent.mkdir(parents=True)
			tx = base / 'transcript.jsonl'
			tx.write_text('{}\n', encoding='utf-8')
			db_path = base / 'conversation_summaries.db'
			db_path.write_bytes(b'')
			cid = '12345678-1234-4234-8234-123456789abc'
			meta = {'Trace': {'Conversation ID': cid, 'Transcript': str(tx), 'Turn': {'Start Step': 0}}}
			jfile.write_text(f'```json\n{json.dumps(meta)}\n```\nBody.\n', encoding='utf-8')
			fake = [{'id': 'ag-a6', 'trace_file': str(tx), 'system_paths': {'conversations_db': str(db_path)}}]
			with patch.object(runtime, 'find_conversation_instance', return_value=fake):
				res = timesheet_common.resolve_trace_source(project=proj, journal_step=1)
			self.assertEqual(db_path.resolve(), res['summary_db'])
			with patch.object(runtime, 'find_conversation_instance', return_value=[]):
				res_missing = timesheet_common.resolve_trace_source(project=proj, journal_step=1)
			self.assertIsNone(res_missing['summary_db'])
	# @used-by :mod:`unittest`
	def test_run_with_transient_wait_separates_lease_retry_and_execution_seconds(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			proj = Path(td).resolve() / 'proj'
			proj.mkdir(parents=True)
			# @used-by :meth:`ObservabilityDiagnosticsTests.test_run_with_transient_wait_separates_lease_retry_and_execution_seconds()`
			def _slow_clean() -> dict:
				time.sleep(0.1)
				return {'ready': True}
			res = repo_wait.run_with_transient_wait(proj, _slow_clean, wait_timeout=5.0, poll_interval=0.05)
			self.assertEqual(0.0, res['lease_wait_seconds'])
			self.assertEqual(0.0, res['retry_wait_seconds'])
			self.assertEqual(0.0, res['waited_seconds'])
			self.assertGreaterEqual(res['execution_seconds'], 0.08)
			self.assertGreaterEqual(res['total_seconds'], res['execution_seconds'])
			calls = {'n': 0}
			# @used-by :meth:`ObservabilityDiagnosticsTests.test_run_with_transient_wait_separates_lease_retry_and_execution_seconds()`
			def _flaky() -> dict:
				calls['n'] += 1
				if 1 == calls['n']:
					raise TimeoutError('Lock busy: turn.lock')
				time.sleep(0.05)
				return {'ready': True}
			res2 = repo_wait.run_with_transient_wait(proj, _flaky, wait_timeout=5.0, poll_interval=0.05)
			self.assertGreaterEqual(res2['retry_wait_seconds'], 0.04)
			self.assertEqual(round(res2['lease_wait_seconds'] + res2['retry_wait_seconds'], 3), res2['waited_seconds'])
			self.assertGreaterEqual(res2['execution_seconds'], 0.04)
if '__main__' == __name__:
	unittest.main()
