# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/77
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from agent_tools import github_issue, issue_lifecycle
class IssueDecompositionTests(unittest.TestCase):
	def test_gh_api_paginates_concatenated_json_via_shared_decoder(self):
		fake = subprocess.CompletedProcess(['gh'], 0, stdout=b'[{"number": 1}][{"number": 2}]', stderr=b'')
		with mock.patch.object(github_issue.subprocess, 'run', return_value=fake):
			rows = github_issue._gh_api('repos/o/r/issues', paginate=True)
		self.assertEqual([{'number': 1}, {'number': 2}], rows)
	def test_issue_evidence_workspace_uses_locked_atomic_turn_updates(self):
		from agent_tools.issues import IssueEvidenceWorkspace
		with tempfile.TemporaryDirectory() as tmp:
			turns_dir = Path(tmp) / 'turns'
			turns_dir.mkdir()
			tfile = turns_dir / 'abc123.json'
			tfile.write_text(json.dumps({'status': 'open', 'platform': 'antigravity', 'github_issues': {}}), encoding='utf-8')
			ws = IssueEvidenceWorkspace()
			ws.record_issue_in_open_turns(turns_dir, 'o/r', {'kind': 'issue', 'number': 9, 'state': 'open', 'html_url': 'https://github.com/o/r/issues/9'}, 'create')
			self.assertTrue((turns_dir / 'turn-abc123.lock').exists())
			updated = json.loads(tfile.read_text(encoding='utf-8'))
			self.assertIn('https://github.com/o/r/issues/9', updated['github_issues'])
			self.assertEqual('create', updated['github_issues']['https://github.com/o/r/issues/9']['last_action'])
	def test_issue_markdown_linter_and_service_classes_exist(self):
		from agent_tools.issues import GitHubIssueService, IssueEvidenceWorkspace, IssueMarkdownLinter, TurnIssueLifecycleAuditor
		linter = IssueMarkdownLinter()
		errs = linter.lint('Add alpha, beta, and gamma', is_title=True)
		self.assertTrue(any(('ENUMERATED_SLOP_TITLE' == e.get('code') for e in errs)))
		self.assertEqual(errs, github_issue.lint_issue_markdown('Add alpha, beta, and gamma', is_title=True))
		self.assertIsNotNone(GitHubIssueService)
		self.assertIsNotNone(IssueEvidenceWorkspace)
		with tempfile.TemporaryDirectory() as tmp:
			auditor = TurnIssueLifecycleAuditor(Path(tmp), {'touched_files': [], 'issue_actions': []})
			res = auditor.audit()
			self.assertTrue(res['verified'])
			self.assertEqual(res, issue_lifecycle.code_and_issue_lifecycle_status(Path(tmp), {'touched_files': [], 'issue_actions': []}))
	def test_issue_lifecycle_exports_multi_subtask_decomposition_helper(self):
		from agent_tools.issue_lifecycle import _check_multi_subtask_decomposition
		violations = []
		with tempfile.TemporaryDirectory() as tmp:
			_check_multi_subtask_decomposition(Path(tmp), '', {}, {}, {}, {}, [], violations)
		self.assertEqual([], violations)
	def test_service_cmd_close_routes_through_module_gh_api_and_checks_readback(self):
		from agent_tools.issues import GitHubIssueService
		with tempfile.TemporaryDirectory() as tmp:
			cfile = Path(tmp) / 'c.md'
			cfile.write_text('Closing comment verified.\n', encoding='utf-8')
			calls = []
			def fake_api(endpoint, *, method='GET', payload=None, paginate=False):
				calls.append((method, endpoint))
				if 'POST' == method:
					return {'id': 777}
				if 'comments/777' in endpoint:
					return {'id': 777, 'body': 'Mismatched body', 'html_url': 'https://github.com/o/r/issues/5#issuecomment-777'}
				return {'number': 5, 'state': 'closed', 'html_url': 'https://github.com/o/r/issues/5'}
			args = argparse.Namespace(repo='o/r', issue=5, reason='not_planned', comment_file=str(cfile), target_locale='en-US', project_root=tmp, repo_root=None, consume_input=False)
			with mock.patch.object(github_issue, '_gh_api', side_effect=fake_api):
				svc = GitHubIssueService(api_fn=lambda *a, **kw: github_issue._gh_api(*a, **kw))
				rc = svc.cmd_close(args)
			self.assertEqual(2, rc)
			self.assertTrue(any(('POST' == m for m, _ in calls)))
if '__main__' == __name__:
	unittest.main()
