# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce PreToolUse fail-fast normalization and block redundant schedule timers over run_command":
# https://github.com/dmitry-ai/harness/issues/162
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
HARNESS_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = HARNESS_ROOT / 'scripts'
HOOK_SCRIPT = SCRIPT_DIR / 'check_rules_and_server_gate.py'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools import tdd_gate, upwork_project
def _run_hook(payload: dict) -> dict:
	proc = subprocess.run([sys.executable, str(HOOK_SCRIPT)], input=json.dumps(payload, ensure_ascii=False).encode('utf-8'), capture_output=True, check=True)
	return json.loads(proc.stdout.decode('utf-8'))
def _write_tx(path: Path, rows: list[dict]) -> Path:
	path.write_text(''.join((json.dumps(r, ensure_ascii=False) + '\n' for r in rows)), encoding='utf-8')
	return path
class FailFastAndScheduleGateTests(unittest.TestCase):
	def test_hooks_manifest_and_canonical_hooks_match_schedule(self) -> None:
		hooks = json.loads((HARNESS_ROOT / 'platforms/antigravity/hooks.json').read_text(encoding='utf-8'))
		matcher = hooks['rules-and-server-gate']['PreToolUse'][0]['matcher']
		self.assertIn('|schedule', matcher)
		canon = upwork_project.canonical_global_hooks(HARNESS_ROOT)
		self.assertEqual(canon['rules-and-server-gate']['PreToolUse'][0]['matcher'], matcher)
		legacy = upwork_project.legacy_runner_global_hooks(HARNESS_ROOT)
		self.assertNotIn('|schedule', legacy['rules-and-server-gate']['PreToolUse'][0]['matcher'])
	def test_pre_tool_use_blocks_redundant_schedule_timer_over_run_command(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			tx = base / 'transcript.jsonl'
			_write_tx(tx, [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Fix the test failure'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python -m unittest discover -f -s tests'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Tool is running as a background task with task id: cid-1/task-464\nTask logs are available at: file:///tmp/task-464.log'},
			])
			d_bound = _run_hook({'cwd': str(base), 'transcriptPath': str(tx), 'toolCall': {'name': 'schedule', 'args': {'DurationSeconds': 900, 'TimerCondition': 'cid-1/task-464', 'Prompt': 'Check tests'}}})
			self.assertEqual(d_bound['decision'], 'deny', d_bound)
			self.assertIn('EXEC-4-SCHEDULE-GATE', d_bound.get('reason', ''))
			d_any = _run_hook({'cwd': str(base), 'transcriptPath': str(tx), 'toolCall': {'name': 'schedule', 'args': {'DurationSeconds': 300, 'TimerCondition': 'any', 'Prompt': 'Wait'}}})
			self.assertEqual(d_any['decision'], 'deny', d_any)
			d_cron = _run_hook({'cwd': str(base), 'transcriptPath': str(tx), 'toolCall': {'name': 'schedule', 'args': {'CronExpression': '*/5 * * * *', 'Prompt': 'Periodic monitor'}}})
			self.assertEqual(d_cron['decision'], 'allow', d_cron)
			_write_tx(tx, [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Fix the test failure'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python -m unittest discover -f -s tests'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Tool is running as a background task with task id: cid-1/task-464'},
				{'step_index': 3, 'type': 'SYSTEM_MESSAGE', 'content': 'Task id "cid-1/task-464" finished with result:\nCommand exited with code 0.'},
			])
			d_after_done = _run_hook({'cwd': str(base), 'transcriptPath': str(tx), 'toolCall': {'name': 'schedule', 'args': {'DurationSeconds': 180, 'Prompt': 'Check external job'}}})
			self.assertEqual(d_after_done['decision'], 'allow', d_after_done)
			d_stale_ref = _run_hook({'cwd': str(base), 'transcriptPath': str(tx), 'toolCall': {'name': 'schedule', 'args': {'DurationSeconds': 180, 'TimerCondition': 'cid-1/task-464', 'Prompt': 'Watch finished cmd'}}})
			self.assertEqual(d_stale_ref['decision'], 'deny', d_stale_ref)
			_write_tx(tx, [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': '/schedule remind me in 10 minutes'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python -m unittest discover -f -s tests'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': 'Tool is running as a background task with task id: cid-1/task-999'},
			])
			d_explicit = _run_hook({'cwd': str(base), 'transcriptPath': str(tx), 'toolCall': {'name': 'schedule', 'args': {'DurationSeconds': 600, 'Prompt': 'Reminder'}}})
			self.assertEqual(d_explicit['decision'], 'allow', d_explicit)
	def test_pre_tool_use_denies_multi_segment_test_command_without_failfast(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			d_bad = _run_hook({'cwd': tmp, 'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'Set-Location tests; python -m unittest discover -s . -p test_*.py', 'WaitMsBeforeAsync': 500}}})
			self.assertEqual(d_bad['decision'], 'deny', d_bad)
			self.assertIn('EXEC-2-TEST-FAILFAST-GATE', d_bad.get('reason', ''))
			d_ok = _run_hook({'cwd': tmp, 'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'Set-Location tests; python -m unittest discover -f -s . -p test_*.py', 'WaitMsBeforeAsync': 10000}}})
			self.assertEqual(d_ok['decision'], 'allow', d_ok)
			self.assertNotIn('overwrite', d_ok)
	def test_pre_tool_use_overwrites_single_segment_test_commands_and_low_wait_ms(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			cases = (
				('python -m unittest discover -s tests -p "test_*.py"', '-f'),
				('pytest tests/', '-x'),
				('go test ./...', '-failfast'),
				('npx vitest run', '--bail'),
				('phpunit tests', '--stop-on-failure'),
				('rspec spec', '--fail-fast'),
			)
			for cmd, expected_flag in cases:
				dec = _run_hook({'cwd': tmp, 'toolCall': {'name': 'run_command', 'args': {'CommandLine': cmd, 'WaitMsBeforeAsync': 500}}})
				self.assertEqual(dec['decision'], 'allow', (cmd, dec))
				ov = dec.get('overwrite') or {}
				self.assertIn(expected_flag, ov.get('CommandLine', ''), (cmd, dec))
				self.assertEqual(ov.get('WaitMsBeforeAsync'), 10000, (cmd, dec))
			clean = _run_hook({'cwd': tmp, 'toolCall': {'name': 'run_command', 'args': {'CommandLine': 'python -m unittest discover -f -s tests -p "test_*.py"', 'WaitMsBeforeAsync': 10000}}})
			self.assertEqual(clean['decision'], 'allow', clean)
			self.assertNotIn('overwrite', clean)
			opt_out = _run_hook({'cwd': tmp, 'toolCall': {'name': 'run_command', 'args': {'CommandLine': f'python "{SCRIPT_DIR / "harness.py"}" run-tests tests --no-failfast', 'WaitMsBeforeAsync': 500}}})
			self.assertEqual(opt_out['decision'], 'allow', opt_out)
			self.assertEqual(opt_out.get('overwrite'), {'WaitMsBeforeAsync': 10000})
	def test_tdd_gate_records_non_failfast_full_suite_warning_without_breaking_verified(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			repo = Path(tmp).resolve()
			(repo / 'tests').mkdir()
			(repo / 'tests/test_a.py').write_text('import unittest\n', encoding='utf-8')
			(repo / 'tests/test_b.py').write_text('import unittest\n', encoding='utf-8')
			(repo / 'app.py').write_text('x = 1\n', encoding='utf-8')
			events = [
				tdd_gate.build_file_write_tdd_event(1, repo / 'tests/test_a.py'),
				tdd_gate.build_command_tdd_event(2, f'python -m unittest "{repo / "tests/test_a.py"}" -f', 'Command exited with code 1.\n\nCommand output:\nFAILED (failures=1)\n', cwd=repo),
				tdd_gate.build_file_write_tdd_event(3, repo / 'app.py'),
				tdd_gate.build_command_tdd_event(4, f'python -m unittest discover -s "{repo / "tests"}" -p test_*.py', 'Command exited with code 0.\n\nCommand output:\nRan 2 tests in 0.1s\n\nOK\n', cwd=repo),
			]
			res = tdd_gate.evaluate_tdd_events(events, require_final_full_green=True)
			self.assertTrue(res['verified'], res)
			self.assertTrue(res.get('failfast_warnings'), res)
if '__main__' == __name__:
	unittest.main()
