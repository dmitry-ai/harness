# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
# https://github.com/dmitry-ai/harness/issues/41
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion, journal_watch
class ForegroundJournalCase(unittest.TestCase):
	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp.cleanup)
		self.root = Path(self.temp.name)
		self.directory = self.root / 'legacy verifier'
		self.project = self.root / 'project'
		self.project.mkdir()
		self.source = self.root / 'native.jsonl'
		self.source.write_text('native input\n', encoding='utf-8')
		self.native = {'platform': 'codex', 'native_backend': str(self.root), 'conversation_id': str(uuid.uuid4()), 'source_file': str(self.source)}
	def binding(self):
		return Path(journal_watch.register(self.project, self.native, 0, state_dir=self.directory)['binding'])
	def snapshot(self):
		return {str(p.relative_to(self.directory)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in self.directory.rglob('*') if p.is_file()}
	def test_legacy_daemon_entry_points_refuse_without_writes_or_processes(self):
		with patch('subprocess.Popen', side_effect=AssertionError('No process may be spawned')):
			for operation, options in ((journal_watch.start, {}), (journal_watch.run, {'token': 'a' * 32, 'interval': 0.1})):
				with self.subTest(operation=operation.__name__):
					with self.assertRaisesRegex(ValueError, 'Persistent journal watchers are not supported'):
						operation(state_dir=self.directory, **options)
		self.assertFalse(self.directory.exists())
	def test_legacy_cli_entry_points_finish_with_an_actionable_error(self):
		for action in ('start', 'run'):
			with self.subTest(action=action):
				result = subprocess.run([sys.executable, str(SCRIPTS / 'harness.py'), 'journal-watch', '--action', action, '--state-dir', str(self.directory), '--token', 'a' * 32, '--interval', '0.1', '--platform', 'codex'], capture_output=True, timeout=8, text=True, encoding='utf-8')
				self.assertNotEqual(result.returncode, 0)
				self.assertIn('Persistent journal watchers are not supported', result.stdout + result.stderr)
		self.assertFalse(self.directory.exists())
	def test_status_and_empty_foreground_pass_do_not_create_state(self):
		result = journal_watch.status(state_dir=self.directory)
		self.assertEqual(result['status'], 'stopped')
		self.assertEqual(result['execution_mode'], 'foreground-only')
		self.assertFalse(result['background_supported'])
		for dry_run in (False, True):
			self.assertEqual(journal_watch.once(state_dir=self.directory, dry_run=dry_run)['bindings_checked'], 0)
		self.assertFalse(journal_watch.stop(state_dir=self.directory)['stop_requested'])
		self.assertFalse(self.directory.exists())
	def test_repeated_registration_preserves_bytes_and_mtime(self):
		binding = self.binding()
		before = self.snapshot()
		with patch.object(journal_watch, '_now', return_value='2099-01-01T00:00:00+00:00'):
			self.assertEqual(Path(journal_watch.register(self.project, self.native, 0, state_dir=self.directory)['binding']), binding)
		self.assertEqual(self.snapshot(), before)
	def test_status_does_not_initialize_an_empty_legacy_lock(self):
		self.directory.mkdir()
		(self.directory / 'daemon.lock').touch()
		before = self.snapshot()
		self.assertEqual(journal_watch.status(state_dir=self.directory)['status'], 'stopped')
		self.assertEqual(self.snapshot(), before)
	def test_dry_run_reads_bindings_without_locks_writes_or_reconciliation(self):
		self.binding()
		before = self.snapshot()
		with patch.object(completion, 'sync', side_effect=AssertionError('Dry run must not reconcile')):
			result = journal_watch.once(state_dir=self.directory, dry_run=True)
		self.assertTrue(result['valid'])
		self.assertTrue(result['results'][0]['would_sync'])
		self.assertEqual(self.snapshot(), before)
		self.assertFalse((self.directory / 'scan.lock').exists())
	def test_every_foreground_pass_audits_and_unchanged_results_do_not_write(self):
		self.binding()
		outcome = {'valid': True, 'turns': [{'turn_key': 'completed', 'status': 'delivered', 'journal_steps': [1], 'recovered_after_delivery': True}]}
		with patch.object(completion, 'sync', return_value=outcome) as sync:
			first = journal_watch.once(state_dir=self.directory)
			before = self.snapshot()
			with patch.object(journal_watch, '_now', return_value='2099-01-01T00:00:00+00:00'):
				second = journal_watch.once(state_dir=self.directory)
		self.assertEqual(sync.call_count, 2)
		self.assertEqual(first['bindings_checked'], 1)
		self.assertEqual(second['bindings_checked'], 1)
		self.assertEqual(second['results'], first['results'])
		self.assertEqual(self.snapshot(), before)
	def test_changed_result_is_recorded_once_without_waiting_for_a_timer(self):
		self.binding()
		good = {'valid': True, 'turns': []}
		bad = {'valid': False, 'turns': [{'turn_key': 'same turn', 'status': 'conflict', 'detail': 'Journal changed'}]}
		with patch.object(completion, 'sync', side_effect=[good, bad, bad]) as sync:
			self.assertTrue(journal_watch.once(state_dir=self.directory)['valid'])
			first = self.snapshot()
			self.assertFalse(journal_watch.once(state_dir=self.directory)['valid'])
			changed = self.snapshot()
			self.assertNotEqual(changed, first)
			self.assertFalse(journal_watch.once(state_dir=self.directory)['valid'])
		self.assertEqual(sync.call_count, 3)
		self.assertEqual(self.snapshot(), changed)
	def test_identical_errors_are_retried_without_rewriting_error_evidence(self):
		self.binding()
		with patch.object(completion, 'sync', side_effect=PermissionError('Temporarily locked')) as sync:
			self.assertFalse(journal_watch.once(state_dir=self.directory)['valid'])
			before = self.snapshot()
			self.assertFalse(journal_watch.once(state_dir=self.directory)['valid'])
		self.assertEqual(sync.call_count, 2)
		self.assertEqual(self.snapshot(), before)
	def test_legacy_stop_is_cooperative_and_does_not_repeat_its_request(self):
		marker = {'status': 'running', 'token': 'a' * 32, 'pid': 123}
		with patch.object(journal_watch, 'status', return_value=marker):
			self.assertTrue(journal_watch.stop(state_dir=self.directory)['stop_requested'])
			before = self.snapshot()
			self.assertTrue(journal_watch.stop(state_dir=self.directory)['stop_requested'])
		self.assertEqual(self.snapshot(), before)
		request = json.loads((self.directory / 'stop.json').read_text(encoding='utf-8'))
		self.assertEqual(request['token'], marker['token'])
if __name__ == '__main__':
	unittest.main()
