# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion, links
from agent_tools.cli_registry import registered_commands
from agent_tools.landing_lease import acquire_lease, release_lease
from agent_tools.upwork_project import main as cli_main
import check_markdown_slop
# @used-by :meth:`RepoWaitAndRetryTests.test_wait_repo_cli_and_registry_expose_wait_repo()`
# @used-by :meth:`RepoWaitAndRetryTests.test_wait_repo_reacts_to_lease_release_dead_pid_and_clean_tree()`
def _init_repo(base: Path) -> Path:
	repo = base / 'repo'
	repo.mkdir(parents=True)
	subprocess.run(['git', 'init', '-b', 'main', str(repo)], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'test@example.com'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True, capture_output=True)
	(repo / 'a.py').write_text('X = 1\n', encoding='utf-8')
	subprocess.run(['git', '-C', str(repo), 'add', 'a.py'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(repo), 'commit', '-m', 'init'], check=True, capture_output=True)
	return repo
# 2026-11-24
# "Add deterministic reactive wait primitive for transient repository and journal contention":
# https://github.com/dmitry-ai/harness/issues/199
class RepoWaitAndRetryTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_answer_prepare_cli_reports_retryable_false_fast_and_true_on_transient_timeout(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			(proj / '\ua616/data/scratch').mkdir(parents=True)
			ans = proj / '\ua616/data/scratch/answer-test.md'
			ans.write_text('Equal probability 50/50 solely because there is no data.\n', encoding='utf-8')
			t0 = time.monotonic()
			buf_perm = StringIO()
			with redirect_stdout(buf_perm):
				rc_perm = cli_main(['answer-prepare', str(proj), '--response-file', str(ans), '--wait-timeout', '30'])
			elapsed_perm = time.monotonic() - t0
			data_perm = json.loads(buf_perm.getvalue())
			self.assertEqual(1, rc_perm)
			self.assertFalse(data_perm['valid'])
			self.assertIs(False, data_perm['retryable'])
			self.assertLess(elapsed_perm, 3.0)
			buf_trans = StringIO()
			with patch.object(completion, '_prepare_once', side_effect=TimeoutError('Lock busy: journal.lock')):
				with redirect_stdout(buf_trans):
					rc_trans = cli_main(['answer-prepare', str(proj), '--response-file', str(ans), '--wait-timeout', '0.15'])
			data_trans = json.loads(buf_trans.getvalue())
			self.assertEqual(1, rc_trans)
			self.assertFalse(data_trans['valid'])
			self.assertIs(True, data_trans['retryable'])
	# @used-by :mod:`unittest`
	def test_answer_prepare_wait_timeout_retries_transient_lock_and_recovers(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			proj.mkdir(parents=True)
			calls = {'n': 0}
			# @used-by :meth:`RepoWaitAndRetryTests.test_answer_prepare_wait_timeout_retries_transient_lock_and_recovers()`
			def flaky_prepare(*_args, **_kwargs):
				calls['n'] += 1
				if 3 > calls['n']:
					raise TimeoutError('Lock busy: turn.lock')
				return {'ready': True, 'status': 'prepared'}
			with patch.object(completion, '_prepare_once', side_effect=flaky_prepare):
				res = completion.prepare(proj, 'Valid response text.', '11111111-2222-3333-4444-555555555555', wait_timeout=5.0, wait_poll=0.05)
			self.assertTrue(res['ready'])
			self.assertIs(False, res['retryable'])
			self.assertEqual(3, calls['n'])
			self.assertGreaterEqual(res['waited_seconds'], 0.05)
	# @used-by :mod:`unittest`
	def test_exec4_documents_wait_repo_wait_timeout_and_no_premature_user_escalation(self) -> None:
		rule_doc = WT_ROOT / 'rules/08-execution-and-tools.md'
		text = rule_doc.read_text(encoding='utf-8')
		self.assertEqual([], links.validate_file(rule_doc, local_anchors=True, readable_links=True))
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(text))
		for token in ('wait-repo', '--wait-timeout', 'land-acquire --wait'):
			self.assertIn(token, text)
	# @used-by :mod:`unittest`
	def test_wait_repo_cli_and_registry_expose_wait_repo(self) -> None:
		self.assertIn('wait-repo', registered_commands())
		with tempfile.TemporaryDirectory() as tmp:
			repo = _init_repo(Path(tmp).resolve())
			buf_ok = StringIO()
			with redirect_stdout(buf_ok):
				rc_ok = cli_main(['wait-repo', str(repo), '--clean', '--timeout', '2', '--poll', '0.05'])
			self.assertEqual(0, rc_ok)
			self.assertTrue(json.loads(buf_ok.getvalue())['ready'])
			(repo / 'dirty.py').write_text('Y = 2\n', encoding='utf-8')
			buf_fail = StringIO()
			with redirect_stdout(buf_fail):
				rc_fail = cli_main(['wait-repo', str(repo), '--clean', '--timeout', '0.15', '--poll', '0.05'])
			fail_out = json.loads(buf_fail.getvalue())
			self.assertNotEqual(0, rc_fail)
			self.assertTrue(fail_out['timed_out'])
			self.assertTrue(fail_out['retryable'])
			self.assertEqual(['dirty.py'], fail_out['dirty_files'])
	# @used-by :mod:`unittest`
	def test_wait_repo_reacts_to_lease_release_dead_pid_and_clean_tree(self) -> None:
		from agent_tools.repo_wait import wait_for_repo
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			repo = _init_repo(base)
			leases = base / 'leases'
			acquire_lease(repo, 'dead-holder', pid=99999999, leases_dir=leases)
			dead_res = wait_for_repo(repo, lease_free=True, timeout=2.0, poll_interval=0.05, leases_dir=leases)
			self.assertTrue(dead_res['ready'])
			self.assertTrue(dead_res['lease_free'])
			acquire_lease(repo, 'live-holder', leases_dir=leases)
			(repo / 'wip.py').write_text('Z = 3\n', encoding='utf-8')
			# @used-by :meth:`RepoWaitAndRetryTests.test_wait_repo_reacts_to_lease_release_dead_pid_and_clean_tree()`
			def release_soon() -> None:
				time.sleep(0.2)
				(repo / 'wip.py').unlink()
				release_lease(repo, 'live-holder', leases_dir=leases)
			worker = threading.Thread(target=release_soon)
			worker.start()
			res = wait_for_repo(repo, timeout=5.0, poll_interval=0.05, leases_dir=leases)
			worker.join(timeout=3.0)
			self.assertTrue(res['valid'])
			self.assertTrue(res['ready'])
			self.assertFalse(res['timed_out'])
			self.assertFalse(res['retryable'])
			self.assertTrue(res['clean'])
			self.assertTrue(res['lease_free'])
			self.assertLess(res['elapsed_seconds'], 2.5)
if '__main__' == __name__:
	unittest.main()