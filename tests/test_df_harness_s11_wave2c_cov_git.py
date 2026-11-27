# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from Df.Harness.Git.GitReadAudit import GitReadAudit
from Df.Harness.Git.IssueCloseVerifier import IssueCloseVerifier
from Df.Harness.Git.IssueWorkflowVerifier import IssueWorkflowVerifier
from Df.Harness.Git.PushValidator import PushValidator
from Df.Harness.Git.TagSelector import TagSelector
from Df.Harness.Git.TransientWaitRunner import TransientWaitRunner
from Df.Harness.Git.VerificationSpecResolver import VerificationSpecResolver
from Df.Harness.Git.WorktreeLockFinder import WorktreeLockFinder
from Df.Harness.Git.WorktreeRebaseVerifier import WorktreeRebaseVerifier
from Df.Harness.Git.WorktreeRemovalGuard import WorktreeRemovalGuard
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DfHarnessS11Wave2CCovGitTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_git_read_audit_unquote_and_tag_selector(self) -> None:
		hits = GitReadAudit('exec_command(cmd: "git status")').detect()
		self.assertTrue(any(('git status' in h for h in hits)))
		self.assertEqual('v1.2.3', TagSelector(['v1.2.3']).pick())
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_issue_close_verifier_parent_children(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			gate = SimpleNamespace(root=root)
			cache = SimpleNamespace(dirty_referencing_issue=lambda *a, **k: [], find_commit_for_issue=lambda _r, u, _fn: 'abcdef123456' if u.endswith('/2') else None)
			children_fn = lambda _self, _repo, num, **_k: [{'number': 2, 'state': 'closed', 'url': 'https://github.com/o/r/issues/2'}] if 1 == num else []
			with patch('Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.find_tracked_child_issues', children_fn), patch('agent_tools.repo_tag_gate.finalize_commit_close_check', return_value={'verified': True, 'commit_sha': 'abcdef123456', 'pushed': True}):
				res = IssueCloseVerifier(gate).verify('o/r', 1, project_root=root, git_cache=cache)
			self.assertTrue(res['verified'])
			self.assertEqual([2], res['child_issues'])
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_issue_workflow_verifier_tracked_evidence(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			ev = root / 'ꘖ/KB/Evidence/GitHub/o__r'
			ev.mkdir(parents=True)
			(ev / 'issue-9.json').write_text(json.dumps({'issue': {'number': 9, 'body': 'parent'}}), encoding='utf-8')
			(ev / 'issue-10.json').write_text(json.dumps({'issue': {'number': 10, 'body': 'Parent: #9'}}), encoding='utf-8')
			gate = SimpleNamespace(root=root, is_issue_tracked=lambda: True, tdd_project_root=lambda: root)
			with patch('Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.origin_repo_slug', return_value='o/r'), patch('agent_tools.tdd.exemption.verify_staged_issue_urls', return_value={'https://github.com/o/r/issues/10'}):
				IssueWorkflowVerifier(gate).verify(['a.py'], 'https://github.com/o/r/issues/10')
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_push_validator_commit_msg_file_and_specs(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / '.git').mkdir()
			(root / 'msg.txt').write_text('https://github.com/o/r/issues/10\n', encoding='utf-8')
			seen: list[tuple] = []
			gate = SimpleNamespace(root=root, ensure_hooks=lambda: None, staged_paths=lambda: ['a.py'], verify_staged_blob_sizes=lambda p: seen.append(('blob', p)), verify_agent_staged=lambda p, **k: seen.append(('agent', p, k.get('message'))))
			PushValidator(gate).validate(['git', 'commit', '-F', 'msg.txt', '--', 'a.py'], subcommand='commit', cwd=root, agent_context=True)
			self.assertEqual(2, len(seen))
			self.assertEqual(['a.py'], seen[0][1])
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_transient_wait_runner_active_turn_and_lease_probe(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			turns_dir = root / 'ꘖ/data/turns'
			turns_dir.mkdir(parents=True)
			repo = root / 'repo'
			(repo / '.git').mkdir(parents=True)
			(turns_dir / 'turn-1.json').write_text(json.dumps({'conversation_id': 'cid-1', 'status': 'open', 'updated_at': '2026-11-27T00:00:00Z', 'touched_files': ['repo/a.py'], 'code_lifecycle_check': {'touched_repos': {'repo': {}}}}), encoding='utf-8')
			pp = SimpleNamespace(turns_dir=turns_dir, code_repos=[repo])
			with patch('Df.Harness.Git.TransientWaitRunner.project_paths', return_value=pp), patch('Df.Harness.Git.LandingLease.LandingLease.status', return_value={'free': True}), patch('Df.Harness.Git.RepoGate.RepoGate.main_repo', return_value=repo):
				res = TransientWaitRunner(root, lambda: {'ok': True}, wait_timeout=0.05, conversation='cid-1').run()
				self.assertTrue(res['ok'])
				self.assertFalse(TransientWaitRunner(root).run(probe_exc=ValueError('uncommitted file')))
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_verification_spec_resolver_expand_and_node_auto(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			reg = SimpleNamespace(raw={'repo_verification': {'o/r': {'test_command': ['${TOOL}', 'run']}}}, resolved_variables={'TOOL': 'pytest'}, env={})
			with patch('Df.Harness.Git.VerificationSpecResolver.load_registry', return_value=reg):
				spec = VerificationSpecResolver(root, slug='o/r').resolve()
			self.assertEqual(['pytest', 'run'], spec['test_command'])
			(root / 'package.json').write_text(json.dumps({'scripts': {'test': 'node app.test.js'}}), encoding='utf-8')
			empty_reg = SimpleNamespace(raw={}, resolved_variables={}, env={})
			with patch('Df.Harness.Git.VerificationSpecResolver.load_registry', return_value=empty_reg):
				auto = VerificationSpecResolver(root, root, slug='other/repo').resolve()
			self.assertEqual('app.test.js', auto['test_command'][1])
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_worktree_lock_finder_rebase_and_removal_guard(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			row = json.dumps({'ProcessId': 999999, 'Name': 'py.exe', 'CommandLine': f'python {root}'})
			with patch('Df.Harness.Git.WorktreeLockFinder.df_is_windows', return_value=True), patch('Df.Harness.Git.WorktreeLockFinder.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=row)):
				holders = WorktreeLockFinder(root).find()
			self.assertEqual(999999, holders[0]['pid'])
			ok_proc = lambda *a, **k: SimpleNamespace(returncode=0, stdout='', stderr='')
			with patch('agent_tools.python_integrity.verify_worktree_python_changes', return_value=[]), patch('agent_tools.xref_gate.verify_worktree_xref_changes', return_value=[]), patch('agent_tools.tdd.diff_executability.resolve_land_test_plan', return_value={'blocked_error': None, 'should_run_tests': True}), patch('agent_tools.tdd.diff_coverage.verify_worktree_diff_coverage', return_value={'valid': False, 'uncovered': ['x.py:f']}):
				err, _, _, _ = WorktreeRebaseVerifier(root, root, 'b', 'main', run_tests=True, workers=1, git_exec_fn=ok_proc, polyglot_test_fn=lambda *a, **k: (True, {'ok': True})).verify()
			self.assertEqual('diff_coverage', err['stage'])
			res_dir = root / 'res'
			(res_dir / 'sub').mkdir(parents=True)
			(res_dir / 'sub/f.txt').write_text('x', encoding='utf-8')
			self.assertTrue(WorktreeRemovalGuard(root, res_dir, force=True, git_exec_fn=ok_proc, lock_finder_fn=lambda _p: []).remove()['ok'])
			res2 = root / 'res2'
			res2.mkdir()
			blocked = WorktreeRemovalGuard(root, res2, force=True, git_exec_fn=ok_proc, lock_finder_fn=lambda _p: [{'pid': 42, 'name': 'x.exe'}]).remove()
			self.assertIn('x.exe(PID 42)', blocked['error'])
if '__main__' == __name__:
	unittest.main()
