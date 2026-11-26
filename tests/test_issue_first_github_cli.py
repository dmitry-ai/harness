# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))

from agent_tools import github_issue
import check_rules_and_server_gate as hook_gate


# @used-by :meth:`IssueFirstGitHubCliTests.test_create_parent_issue_blocked_on_dirty_tree_while_open_parent_child_create_allowed()`
# @used-by :meth:`IssueFirstGitHubCliTests.test_fetch_persists_open_issue_and_parent_evidence_and_rejects_pull_requests()`
def _init_github_code_repo(proj: Path, slug: str) -> Path:
	(proj / '_/ꘖ/data/scratch').mkdir(parents=True, exist_ok=True)
	code = proj / 'code'
	code.mkdir(parents=True, exist_ok=True)
	subprocess.run(['git', 'init', str(code)], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(code), 'config', 'user.email', 'test@example.com'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(code), 'config', 'user.name', 'Test User'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(code), 'remote', 'add', 'origin', f'https://github.com/{slug}.git'], check=True, capture_output=True)
	(code / 'app.py').write_text(f'# https://github.com/{slug}/issues/1\nx = 1\n', encoding='utf-8')
	subprocess.run(['git', '-C', str(code), 'add', 'app.py'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(code), 'commit', '-m', f'https://github.com/{slug}/issues/1'], check=True, capture_output=True)
	return code


# 2026-11-23
# "Add fetch subcommand and Issue-First pre-flight guards to df_github_issue.py":
# https://github.com/dmitry-ai/harness/issues/144
class IssueFirstGitHubCliTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_fetch_persists_open_issue_and_parent_evidence_and_rejects_pull_requests(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			_init_github_code_repo(proj, 'acme/demo')
			issues_db = {
				50: {
					'number': 50,
					'id': 5000,
					'title': 'Parent problem report',
					'body': '## Problem\nRoot causes.\n',
					'state': 'open',
					'state_reason': None,
					'created_at': '2026-11-23T10:00:00Z',
					'updated_at': '2026-11-23T10:05:00Z',
					'html_url': 'https://github.com/acme/demo/issues/50',
				},
				51: {
					'number': 51,
					'id': 5001,
					'title': 'Implement first subtask',
					'body': 'Parent: #50\n\n## Scope\nDetails.\n',
					'state': 'open',
					'state_reason': None,
					'created_at': '2026-11-23T10:10:00Z',
					'updated_at': '2026-11-23T10:11:00Z',
					'html_url': 'https://github.com/acme/demo/issues/51',
				},
				52: {
					'number': 52,
					'id': 5002,
					'title': 'Pull request',
					'body': 'PR body',
					'state': 'open',
					'pull_request': {'url': 'https://api.github.com/repos/acme/demo/pulls/52'},
					'html_url': 'https://github.com/acme/demo/pull/52',
				},
			}

			# @used-by :meth:`IssueFirstGitHubCliTests.test_fetch_persists_open_issue_and_parent_evidence_and_rejects_pull_requests()`
			def fake_gh(endpoint, *, method='GET', payload=None, paginate=False):
				self.assertEqual(method, 'GET')
				num = int(endpoint.rsplit('/', 1)[-1])
				return issues_db[num]

			with patch('agent_tools.github_issue._gh_api', side_effect=fake_gh):
				buf50 = io.StringIO()
				with patch('sys.stdout', buf50):
					rc50 = github_issue.main(['fetch', '--repo', 'acme/demo', '--issue', '50', '--project-root', str(proj)])
				self.assertEqual(rc50, 0, buf50.getvalue())
				out50 = json.loads(buf50.getvalue())
				self.assertTrue(out50['ok'])
				self.assertEqual(out50['action'], 'fetch')
				self.assertEqual(out50['number'], 50)
				self.assertEqual(out50['state'], 'open')
				self.assertTrue(out50['verified'])
				ev50_path = proj / '_/ꘖ/KB/Evidence/GitHub/acme__demo/issue-50.json'
				self.assertTrue(ev50_path.is_file())
				ev50 = json.loads(ev50_path.read_text(encoding='utf-8'))
				self.assertEqual(ev50['created_at'], '2026-11-23T10:00:00Z')
				self.assertEqual(ev50['updated_at'], '2026-11-23T10:05:00Z')

				# Remove issue-50.json and verify fetching child #51 also fetches and persists parent #50
				ev50_path.unlink()
				buf51 = io.StringIO()
				with patch('sys.stdout', buf51):
					rc51 = github_issue.main(['fetch', '--repo', 'acme/demo', '--issue', '51', '--project-root', str(proj)])
				self.assertEqual(rc51, 0, buf51.getvalue())
				out51 = json.loads(buf51.getvalue())
				self.assertEqual(out51['parent_number'], 50)
				self.assertTrue(ev50_path.is_file())
				self.assertTrue((proj / '_/ꘖ/KB/Evidence/GitHub/acme__demo/issue-51.json').is_file())

				# Pull request must be rejected
				buf52 = io.StringIO()
				with patch('sys.stderr', buf52):
					rc52 = github_issue.main(['fetch', '--repo', 'acme/demo', '--issue', '52', '--project-root', str(proj)])
				self.assertNotEqual(rc52, 0)

			# PreToolUse external write gate allows read-only fetch
			self.assertIsNone(
				hook_gate.check_external_write_gate(
					'run_command',
					{'CommandLine': 'python scripts/df_github_issue.py fetch --repo acme/demo --issue 50'},
				)
			)

	# @used-by :mod:`unittest`
	def test_create_parent_issue_blocked_on_dirty_tree_while_open_parent_child_create_allowed(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			code = _init_github_code_repo(proj, 'acme/demo')
			scratch = proj / '_/ꘖ/data/scratch'
			parent_body = scratch / 'parent.md'
			parent_body.write_text('## Problem\nDescribe the defect before coding.\n', encoding='utf-8')
			child_open_body = scratch / 'child_open.md'
			child_open_body.write_text('Parent: #60\n\n## Scope\nSubtask under open parent.\n', encoding='utf-8')
			child_closed_body = scratch / 'child_closed.md'
			child_closed_body.write_text('Parent: #61\n\n## Scope\nSubtask under closed parent.\n', encoding='utf-8')

			next_num = [62]
			issues_db = {
				60: {
					'number': 60, 'id': 6000, 'title': 'Open parent', 'body': '## Problem\nOpen.\n',
					'state': 'open', 'state_reason': None, 'created_at': '2026-11-23T09:00:00Z', 'updated_at': '2026-11-23T09:00:00Z',
					'html_url': 'https://github.com/acme/demo/issues/60',
				},
				61: {
					'number': 61, 'id': 6001, 'title': 'Closed parent', 'body': '## Problem\nClosed.\n',
					'state': 'closed', 'state_reason': 'completed', 'created_at': '2026-11-22T09:00:00Z', 'updated_at': '2026-11-22T10:00:00Z',
					'html_url': 'https://github.com/acme/demo/issues/61',
				},
			}
			api_calls: list[tuple[str, str]] = []

			# @used-by :meth:`IssueFirstGitHubCliTests.test_create_parent_issue_blocked_on_dirty_tree_while_open_parent_child_create_allowed()`
			def fake_gh(endpoint, *, method='GET', payload=None, paginate=False):
				api_calls.append((method, endpoint))
				if 'POST' == method and endpoint.endswith('/issues'):
					num = next_num[0]
					next_num[0] += 1
					issues_db[num] = {
						'number': num, 'id': 6000 + num, 'title': payload['title'], 'body': payload['body'],
						'state': 'open', 'state_reason': None,
						'created_at': '2026-11-23T11:00:00Z', 'updated_at': '2026-11-23T11:00:00Z',
						'html_url': f'https://github.com/acme/demo/issues/{num}',
					}
					return issues_db[num]
				if 'POST' == method and endpoint.endswith('/sub_issues'):
					return {'linked': True}
				# 2026-11-23
				# "Prepend structured JSON metadata header to new GitHub issues in df_github_issue.py":
				# https://github.com/dmitry-ai/harness/issues/150
				if 'PATCH' == method and '/issues/' in endpoint:
					num = int(endpoint.rsplit('/', 1)[-1])
					issues_db[num].update(payload)
					return issues_db[num]
				if 'GET' == method and '/issues/' in endpoint:
					return issues_db[int(endpoint.rsplit('/', 1)[-1])]
				raise AssertionError(f'Unexpected {method} {endpoint}')

			# Make working tree dirty with an untracked test file written before any issue
			(code / 'tests').mkdir()
			dirty_test = code / 'tests/test_early.py'
			dirty_test.write_text('def test_early(): assert True\n', encoding='utf-8')

			with patch('agent_tools.github_issue._gh_api', side_effect=fake_gh):
				# 1. Retroactive parent create with dirty test file -> BLOCKED (exit 2), zero API calls, input preserved
				buf_dirty = io.StringIO()
				with patch('sys.stdout', buf_dirty):
					rc_dirty = github_issue.main([
						'create', '--repo', 'acme/demo', '--title', 'Retroactive problem report',
						'--body-file', str(parent_body), '--project-root', str(proj), '--consume-input',
					])
				self.assertEqual(rc_dirty, 2, buf_dirty.getvalue())
				out_dirty = json.loads(buf_dirty.getvalue())
				self.assertFalse(out_dirty['ok'])
				self.assertEqual(out_dirty['stage'], 'pre_flight_issue_first')
				self.assertIn('ISSUE-FIRST-GATE', out_dirty['error'])
				self.assertIn('tests/test_early.py', out_dirty['dirty_files'])
				self.assertEqual(api_calls, [])
				self.assertTrue(parent_body.is_file())

				# 2. Creating a child subtask under an OPEN parent #60 during ongoing work -> ALLOWED
				buf_child = io.StringIO()
				with patch('sys.stdout', buf_child):
					rc_child = github_issue.main([
						'create', '--repo', 'acme/demo', '--parent', '60', '--title', 'Subtask under open parent',
						'--body-file', str(child_open_body), '--project-root', str(proj), '--consume-input',
					])
				self.assertEqual(rc_child, 0, buf_child.getvalue())
				out_child = json.loads(buf_child.getvalue())
				self.assertTrue(out_child['ok'])
				self.assertEqual(out_child['state'], 'open')
				self.assertEqual(out_child['parent_number'], 60)

				# 3. Creating a child subtask under a CLOSED parent #61 -> REJECTED
				buf_closed_parent = io.StringIO()
				with patch('sys.stdout', buf_closed_parent), patch('sys.stderr', io.StringIO()):
					rc_closed_parent = github_issue.main([
						'create', '--repo', 'acme/demo', '--parent', '61', '--title', 'Subtask under closed parent',
						'--body-file', str(child_closed_body), '--project-root', str(proj),
					])
				self.assertNotEqual(rc_closed_parent, 0)

				# 4. Clean working tree -> parent issue create succeeds and persists state/timestamps
				dirty_test.unlink()
				buf_clean = io.StringIO()
				with patch('sys.stdout', buf_clean):
					rc_clean = github_issue.main([
						'create', '--repo', 'acme/demo', '--title', 'Clean strategic problem report',
						'--body-file', str(parent_body), '--project-root', str(proj), '--consume-input',
					])
				self.assertEqual(rc_clean, 0, buf_clean.getvalue())
				out_clean = json.loads(buf_clean.getvalue())
				self.assertTrue(out_clean['ok'])
				self.assertEqual(out_clean['state'], 'open')
				self.assertFalse(parent_body.is_file())
				ev_new = json.loads((proj / f'_/ꘖ/KB/Evidence/GitHub/acme__demo/issue-{out_clean["number"]}.json').read_text(encoding='utf-8'))
				self.assertEqual(ev_new['created_at'], '2026-11-23T11:00:00Z')


if '__main__' == __name__:
	unittest.main()
