# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from unittest import mock
import os
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :mod:`unittest`
class DfHarnessS11Wave2CGitTests(unittest.TestCase):
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.__init_repo_with_origin()`
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def __git(self, repo: Path, *args: str) -> subprocess.CompletedProcess:
		return subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=True)
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_lease_and_fifo()`
	def __init_repo_with_origin(self, base: Path) -> tuple[Path, Path]:
		origin = base / 'origin.git'
		repo = base / 'repo'
		origin.mkdir(parents=True)
		repo.mkdir(parents=True)
		self.__git(origin, 'init', '--bare')
		self.__git(repo, 'init', '-b', 'main')
		self.__git(repo, 'config', 'user.email', 'test@example.com')
		self.__git(repo, 'config', 'user.name', 'Test User')
		self.__git(repo, 'remote', 'add', 'origin', str(origin))
		(repo / 'README.md').write_text('hello\n', encoding='utf-8')
		self.__git(repo, 'add', 'README.md')
		self.__git(repo, 'commit', '-m', 'init')
		self.__git(repo, 'push', '-u', 'origin', 'main')
		return (repo, origin)
	# @used-by :mod:`unittest`
	def test_git_gate_commit_and_hooks(self) -> None:
		from Df.Harness.Git.BlobSizeValidator import BlobSizeValidator
		from Df.Harness.Git.RepoGate import RepoGate
		from Df.Harness.Git.RepoResolver import RepoResolver
		from Df.Harness.Git.WorktreeTransaction import WorktreeTransaction
		from agent_tools import git_gate
		self.assertIs(RepoGate, git_gate.GitRepoGate)
		self.assertIs(WorktreeTransaction, git_gate.WorktreeCommitTransaction)
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			repo, _ = self.__init_repo_with_origin(base)
			gate = RepoGate(repo)
			self.assertEqual(repo.resolve(), gate.assert_toplevel())
			self.assertEqual(repo.resolve(), RepoResolver(['-C', str(repo), 'status']).resolve())
			self.assertTrue(gate.read_git('status', ['--short'])['valid'])
			gate.ensure_hooks()
			(repo / 'note.txt').write_text('# https://github.com/dmitry-ai/harness/issues/382\n', encoding='utf-8')
			self.__git(repo, 'add', 'note.txt')
			self.assertEqual(['note.txt'], gate.staged_paths())
			self.assertEqual(['note.txt'], gate.normalize_paths(['note.txt']))
			self.assertEqual(0, gate.run_hook('pre-commit', agent_context=False))
			self.assertEqual(0, gate.run_hook('pre-commit', agent_context=True))
			msg_f = base / 'msg.txt'
			msg_f.write_text('https://github.com/dmitry-ai/harness/issues/382\n', encoding='utf-8')
			self.assertEqual(0, gate.run_hook('commit-msg', [str(msg_f)], agent_context=True))
			added_u, head_u = gate.extract_added_diff_urls('note.txt')
			self.assertTrue(added_u and (not head_u))
			self.assertEqual((added_u, head_u), gate._extract_added_diff_urls('note.txt'))
			self.assertFalse(hasattr(gate, 'nonexistent_gate_attr'))
			gate.verify_staged_blob_sizes(['note.txt'])
			gate.verify_code_size_ratchet(['note.txt'], agent_context=False)
			gate.verify_subprocess_hygiene(['note.txt'], agent_context=False)
			gate.verify_tdd_commit(['note.txt'], agent_context=False)
			gate.verify_write_invocation(['git', 'status'], agent_context=False)
			self.assertEqual(['note.txt'], gate.commit(['note.txt'], 'https://github.com/dmitry-ai/harness/issues/382', execute=True))
			head_sha = self.__git(repo, 'rev-parse', 'HEAD').stdout.strip()
			zero = '0' * 40
			stdin_txt = f'refs/heads/main {head_sha} refs/heads/main {zero}\n'
			self.assertEqual(0, gate.run_hook('pre-push', ['origin', 'url'], stdin_text=stdin_txt, agent_context=True))
			BlobSizeValidator(gate).validate(mode='push', stdin_lines=[stdin_txt.strip()])
	# @used-by :mod:`unittest`
	def test_git_gate_worktree_locks_and_issues(self) -> None:
		from Df.Harness.Git.AgentContextDetector import AgentContextDetector
		from Df.Harness.Git.CredentialLockCleaner import CredentialLockCleaner
		from Df.Harness.Git.IssueCloseVerifier import IssueCloseVerifier
		from Df.Harness.Git.IssueWorkflowVerifier import IssueWorkflowVerifier
		from Df.Harness.Git.RepoGate import RepoGate
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			repo, _ = self.__init_repo_with_origin(base)
			gate = RepoGate(repo)
			self.assertIsInstance(gate.is_issue_tracked(), bool)
			self.assertIsInstance(gate.tdd_project_root(), Path)
			(repo / 'wt_file.txt').write_text('# https://github.com/dmitry-ai/harness/issues/382\n', encoding='utf-8')
			self.assertEqual(['wt_file.txt'], gate.commit(['wt_file.txt'], 'https://github.com/dmitry-ai/harness/issues/382', execute=True, worktree=True))
			self.assertIsInstance(AgentContextDetector().detect(), bool)
			lock_f = base / '.git-credentials.lock'
			lock_f.write_text('stale', encoding='utf-8')
			old = lock_f.stat().st_mtime - 600
			os.utime(lock_f, (old, old))
			cleaned = CredentialLockCleaner(max_age_seconds=60.0, candidates=[lock_f], check_running=False).clean()
			self.assertEqual([str(lock_f)], cleaned)
			IssueWorkflowVerifier(gate).verify(['wt_file.txt'], agent_context=False)
			with mock.patch('Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.find_tracked_child_issues', return_value=[]), mock.patch('agent_tools.repo_tag_gate.finalize_commit_close_check', return_value={'verified': True, 'commit_sha': 'abc'}):
				res = IssueCloseVerifier(gate).verify('dmitry-ai/harness', 382)
			self.assertTrue(res['verified'])
	# @used-by :mod:`unittest`
	def test_git_ignore_tags_and_repo_wait(self) -> None:
		from Df.Harness.Git.BlobUrlBuilder import BlobUrlBuilder
		from Df.Harness.Git.CommitTagger import CommitTagger
		from Df.Harness.Git.DateTagAllocator import DateTagAllocator
		from Df.Harness.Git.GlobalIgnoreSyncer import GlobalIgnoreSyncer
		from Df.Harness.Git.RepoWaiter import RepoWaiter
		from Df.Harness.Git.RetroTagger import RetroTagger
		from Df.Harness.Git.RetryableError import RetryableError
		from Df.Harness.Git.TagSelector import TagSelector
		from Df.Harness.Git.TransientWaitRunner import TransientWaitRunner
		from Df.Harness.Git.WorktreeExcludeManager import WorktreeExcludeManager
		from agent_tools import repo_wait
		self.assertIs(RetryableError, repo_wait.RetryableOperationError)
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			repo, _ = self.__init_repo_with_origin(base)
			gignore = base / 'global.ignore'
			self.assertTrue(GlobalIgnoreSyncer(check=False, ignore_path=gignore).sync()['valid'])
			self.assertTrue(WorktreeExcludeManager(repo / 'sub_wts').ensure()['excluded'])
			self.assertEqual('2026-11-26', DateTagAllocator(set(), '2026-11-26').allocate())
			self.assertEqual('2026-11-26--2', DateTagAllocator({'2026-11-26'}, '2026-11-26').allocate())
			tag_res = CommitTagger(repo, push=True).ensure()
			self.assertTrue(tag_res['valid'])
			self.assertEqual(tag_res['tag'], TagSelector([tag_res['tag']]).pick())
			self.__git(repo, 'remote', 'set-url', 'origin', 'https://github.com/dmitry-ai/harness.git')
			url_res = BlobUrlBuilder(repo / 'README.md', lines='L1-L1', push=False).build()
			self.assertIn('#L1', url_res)
			self.assertTrue(RetroTagger(repo, apply=False, push=False).run()['valid'])
			self.assertTrue(RepoWaiter(repo, timeout=1.0, poll_interval=0.05).wait()['valid'])
			attempts = {'n': 0}
			# @used-by :meth:`DfHarnessS11Wave2CGitTests.test_git_ignore_tags_and_repo_wait()`
			def flaky():
				attempts['n'] += 1
				if 1 == attempts['n']:
					raise RetryableError('busy')
				return {'ok': True}
			ran = TransientWaitRunner(repo, flaky, wait_timeout=2.0, poll_interval=0.01, wait_repos=[repo]).run()
			self.assertTrue(ran['ok'] and 2 == attempts['n'])
	# @used-by :mod:`unittest`
	def test_landing_lease_and_polyglot_land(self) -> None:
		from Df.Harness.Git.DirtyMainChecker import DirtyMainChecker
		from Df.Harness.Git.LandingLease import LandingLease
		from Df.Harness.Git.PolyglotTestRunner import PolyglotTestRunner
		from Df.Harness.Git.RepoHealthChecker import RepoHealthChecker
		from Df.Harness.Git.VerificationSpecResolver import VerificationSpecResolver
		from Df.Harness.lib.process import dfh_pid_is_alive
		from Df.Harness.lib.shell import dfh_extract_comment_issue_urls, dfh_extract_issue_urls, dfh_normalize_commit_message, dfh_parse_issue_url, dfh_protected_browser_perimeter
		self.assertTrue(dfh_pid_is_alive(os.getpid()))
		self.assertFalse(dfh_pid_is_alive(-1))
		self.assertEqual({'https://github.com/a/b/issues/1'}, dfh_extract_comment_issue_urls('# https://github.com/a/b/issues/1'))
		self.assertEqual(['https://github.com/a/b/issues/1'], dfh_extract_issue_urls('https://github.com/a/b/issues/1'))
		self.assertEqual('x', dfh_normalize_commit_message('# c\nx\n'))
		self.assertEqual(('a/b', 1), dfh_parse_issue_url('https://github.com/a/b/issues/1'))
		self.assertIsInstance(dfh_protected_browser_perimeter(), dict)
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			repo, _ = self.__init_repo_with_origin(base)
			leases = base / 'leases'
			lease = LandingLease(repo, 'h1', leases_dir=leases)
			self.assertTrue(lease.acquire(wait=False)['acquired'])
			self.assertFalse(lease.status()['free'])
			self.assertTrue(lease.release()['released'])
			self.assertEqual([], DirtyMainChecker(repo, 'main').find_blocking())
			spec = {'test_command': [sys.executable, '-c', 'print(1)'], 'watch_host_files': [str(repo / 'README.md')]}
			self.assertIsNone(VerificationSpecResolver(repo, repo).resolve())
			self.assertTrue(PolyglotTestRunner(repo, repo, spec=spec).run()[0])
			health_cfg = {'health_command': [sys.executable, '-c', 'import json; print(json.dumps({"state": "ok"}))']}
			self.assertTrue(RepoHealthChecker(repo, spec=health_cfg, force=True).check()['ok'])
	# @used-by :mod:`unittest`
	def test_shell_audit_single_class_modules_and_facade(self) -> None:
		from Df.Harness.Git.CdpBypassAudit import CdpBypassAudit
		from Df.Harness.Git.CommitArgsParser import CommitArgsParser
		from Df.Harness.Git.GitGlobalOptsScanner import GitGlobalOptsScanner
		from Df.Harness.Git.GitReadAudit import GitReadAudit
		from Df.Harness.Git.GitSegmentExtractor import GitSegmentExtractor
		from Df.Harness.Git.GitWriteAudit import GitWriteAudit
		from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
		from Df.Harness.Git.IssueActionExtractor import IssueActionExtractor
		from Df.Harness.Git.ShellInspector import ShellInspector
		from Df.Harness.Git.ShellSegmenter import ShellSegmenter
		from agent_tools import shell_audit
		self.assertIs(ShellInspector, shell_audit.ShellCommandInspector)
		self.assertEqual(Path('C:/work/test'), HostPathNormalizer('/cygdrive/c/work/test').normalize())
		self.assertEqual(['git status', 'git log'], ShellSegmenter('git status && git log').split())
		self.assertEqual([('git status', ['status'])], GitSegmentExtractor('git status').extract())
		self.assertEqual(2, GitGlobalOptsScanner(['-C', '.', 'status']).scan()[0])
		self.assertEqual('hi', CommitArgsParser(['commit', '-am', 'hi', '--', 'a.py']).parse()[1])
		self.assertTrue(GitWriteAudit('git commit -m "bad"').detect())
		self.assertTrue(GitReadAudit('git status').detect())
		self.assertTrue(CdpBypassAudit('python -c "ws://127.0.0.1:9222/json"').detect())
		self.assertEqual([], IssueActionExtractor(['echo hi']).extract())
		ins = ShellInspector()
		self.assertEqual(('status', False), ins.classify_git_argv(['status']))
		self.assertTrue(ins.unpersisted_http_fetch_commands('curl https://example.com'))
		self.assertTrue(ins.prohibited_git_write_commands('git commit -m "bad"'))
		self.assertTrue(ins.unflagged_git_read_commands('git diff'))
		self.assertTrue(ins.prohibited_cdp_bypass_commands('curl http://127.0.0.1:9222/json/list'))
		self.assertEqual(0, ins.scan_git_global_opts(['log'])[0])
		self.assertEqual(['a.py'], ins.parse_commit_subcommand_args(['commit', '-m', 'x', '--', 'a.py'])[5])
		self.assertEqual([], ins.extract_issue_actions(['echo ok']))
	# @used-by :mod:`unittest`
	def test_worktree_flow_guard_and_land(self) -> None:
		from Df.Harness.Git.WorktreeCleaner import WorktreeCleaner
		from Df.Harness.Git.WorktreeCommandGuard import WorktreeCommandGuard
		from Df.Harness.Git.WorktreeCreator import WorktreeCreator
		from Df.Harness.Git.WorktreeLander import WorktreeLander
		from Df.Harness.Git.WorktreeLockFinder import WorktreeLockFinder
		from Df.Harness.Git.WorktreePathResolver import WorktreePathResolver
		from Df.Harness.Git.WorktreeRemovalGuard import WorktreeRemovalGuard
		from Df.Harness.Git.WorktreeStatusInspector import WorktreeStatusInspector
		from Df.Harness.lib.worktree import dfh_fail_land, dfh_git_config_file, dfh_git_exec, dfh_has_origin_remote
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			repo, _ = self.__init_repo_with_origin(base)
			self.assertTrue(dfh_git_config_file(repo).is_file())
			self.assertTrue(dfh_has_origin_remote(repo))
			self.assertFalse(dfh_fail_land(repo, repo, 'main', 'err', 'boom')['valid'])
			wt_dir = base / 'wts'
			wt_info = WorktreeCreator(repo, 'demo-task', base_ref='main', worktrees_dir=wt_dir).begin()
			wt_path = Path(wt_info['worktree'])
			self.assertTrue(wt_path.is_dir())
			self.assertTrue(WorktreeStatusInspector(repo).inspect()['worktrees'])
			(wt_path / 'change.txt').write_text('ok\n', encoding='utf-8')
			self.__git(wt_path, 'add', 'change.txt')
			self.__git(wt_path, 'commit', '-m', 'wt change')
			self.assertIsNotNone(WorktreePathResolver(wt_path / 'change.txt', lambda p: (p / '.git').exists()).resolve())
			self.assertIsNone(WorktreePathResolver(wt_path / 'missing_dir' / 'gone.txt', lambda _: False).resolve())
			self.assertEqual([], WorktreeCommandGuard('git status').check())
			self.assertTrue(WorktreeCommandGuard('rm -rf \ua616/data/worktrees/demo-task').check(mode='delete'))
			self.assertTrue(WorktreeCommandGuard('git worktree remove demo-task').check())
			self.assertIsInstance(WorktreeLockFinder(wt_path, process_rows=[]).find(), list)
			cfg = {'target_branch': 'main', 'run_tests': False, 'push': True, 'remove': True, 'wait': True, 'wait_timeout': 5.0, 'ttl': 60.0, 'poll_interval': 0.05, 'workers': None, 'no_tests_reason': 'doc', 'owner': 'o1', 'leases_dir': base / 'leases', 'tag': False, 'post_merge_fn': None, 'promote_snapshot': False, 'snapshot_store': None, 'plan': None}
			land_res = WorktreeLander(repo, wt_path, wt_info['branch'], cfg).land()
			self.assertTrue(land_res['valid'])
			wt2 = WorktreeCreator(repo, 'cleanup-task', base_ref='main', worktrees_dir=wt_dir).begin()
			self.assertTrue(WorktreeCleaner(repo, wt2['worktree']).cleanup()['valid'])
			wt3 = WorktreeCreator(repo, 'remove-task', base_ref='main', worktrees_dir=wt_dir).begin()
			WorktreeRemovalGuard(repo, Path(wt3['worktree']), force=True, git_exec_fn=dfh_git_exec).remove()
			self.assertFalse(Path(wt3['worktree']).exists())
	# @used-by :mod:`unittest`
	def test_worktree_helper_branches_audit_and_tags(self) -> None:
		from Df.Harness.Git.AgentContextDetector import AgentContextDetector
		from Df.Harness.Git.CredentialLockCleaner import CredentialLockCleaner
		from Df.Harness.Git.DirtyMainChecker import DirtyMainChecker
		from Df.Harness.Git.GitReadAudit import GitReadAudit
		from Df.Harness.Git.GlobalIgnoreSyncer import GlobalIgnoreSyncer
		from Df.Harness.Git.IssueActionExtractor import IssueActionExtractor
		from Df.Harness.Git.PushValidator import PushValidator
		from Df.Harness.Git.RepoGate import RepoGate
		from Df.Harness.Git.RetroTagger import RetroTagger
		from Df.Harness.Git.TagSelector import TagSelector
		self.assertIsInstance(AgentContextDetector(env={}).detect(), bool)
		self.assertIsInstance(CredentialLockCleaner(max_age_seconds=99999.0, check_running=False).clean(), list)
		self.assertTrue(GitReadAudit('git "status"').detect())
		self.assertIsInstance(IssueActionExtractor(['{"action":"create","issue":{"number":1}}']).extract(), list)
		self.assertEqual('2026-11-26', TagSelector(['2026-11-26', 'bad-tag']).pick())
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			repo, _ = self.__init_repo_with_origin(base)
			self.assertIn(GlobalIgnoreSyncer(check=True, env={'HOME': str(base), 'USERPROFILE': str(base)}).sync()['valid'], (True, False))
			(repo / 'README.md').write_text('dirty\n', encoding='utf-8')
			self.assertEqual(['README.md'], DirtyMainChecker(repo, 'main').find_blocking())
			self.__git(repo, 'checkout', '--', 'README.md')
			gate = RepoGate(repo)
			PushValidator(gate).validate(['push', 'origin', 'main'], agent_context=False)
			with mock.patch('Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.find_tracked_child_issues', return_value=[]):
				self.assertRaises(ValueError, gate.verify_issue_ready_for_close, 'dmitry-ai/harness', 999)
			self.assertTrue(RetroTagger(repo, apply=True, push=False, extra_commits=['HEAD']).run()['valid'])
	# @used-by :mod:`unittest`
	def test_worktree_helper_branches_lease_and_fifo(self) -> None:
		from Df.Harness.Git.LandingLease import LandingLease
		from Df.Harness.Git.VerificationSpecResolver import VerificationSpecResolver
		from Df.Harness.Git.WorktreeCreator import WorktreeCreator
		from Df.Harness.Git.WorktreeLander import WorktreeLander
		from Df.Harness.Git.WorktreeLockFinder import WorktreeLockFinder
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			repo, _ = self.__init_repo_with_origin(base)
			(repo / 'package.json').write_text('{"scripts":{"test":"echo ok"}}', encoding='utf-8')
			self.assertIsNotNone(VerificationSpecResolver(repo, repo).resolve())
			(repo / 'package.json').unlink()
			leases = base / 'leases'
			self.assertTrue(LandingLease(repo, 'h1', leases_dir=leases).acquire(wait=False)['acquired'])
			self.assertFalse(LandingLease(repo, 'h2', leases_dir=leases).acquire(wait=True, timeout=0.05, poll_interval=0.02)['acquired'])
			wt_info = WorktreeCreator(repo, 'fifo-task', base_ref='main', worktrees_dir=base / 'wts').begin()
			wt_p = Path(wt_info['worktree'])
			(wt_p / 'f.txt').write_text('x\n', encoding='utf-8')
			self.__git(wt_p, 'add', 'f.txt')
			self.__git(wt_p, 'commit', '-m', 'f')
			rows = [{'pid': 999999, 'name': 'python.exe', 'command_line': str(wt_p)}]
			self.assertTrue(WorktreeLockFinder(wt_p, process_rows=rows).find())
			cfg = {'target_branch': 'main', 'run_tests': False, 'push': False, 'remove': True, 'wait': True, 'wait_timeout': 5.0, 'ttl': 60.0, 'poll_interval': 0.05, 'workers': None, 'no_tests_reason': 'doc', 'owner': 'o2', 'leases_dir': base / 'leases2', 'tag': False, 'post_merge_fn': None, 'promote_snapshot': False, 'snapshot_store': None, 'plan': None}
			self.assertTrue(WorktreeLander(repo, wt_p, wt_info['branch'], cfg, max_optimistic_retries=0).land()['valid'])
if '__main__' == __name__:
	unittest.main()
