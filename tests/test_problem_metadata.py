# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = WT_ROOT / 'scripts'
TESTS_DIR = WT_ROOT / 'tests'
for _p in (SCRIPT_DIR, TESTS_DIR):
	if str(_p) not in sys.path:
		sys.path.insert(0, str(_p))
from agent_tools import metadata
# 2026-11-26 "Add contract invariants for metadata test env isolation and worktree-land gates": https://github.com/dmitry-ai/harness/issues/366
from agent_tools.env_isolation_contracts import isolated_subprocess_env
from problem_report_fixtures import ProblemReportFixtureBuilder
# 2026-11-28 "Reject invalid or foreign GitHub issues in problem-metadata builder and CLI": https://github.com/dmitry-ai/harness/issues/429
# @used-by :meth:`ProblemMetadataTests.test_build_problem_metadata_with_issue_url_and_distinct_source_project()`
# @used-by :meth:`ProblemMetadataTests.test_cli_problem_metadata_outputs_json_and_markdown_and_enforces_issue_key()`
def _seed_open_parent_issue(proj: Path, num: int=180) -> None:
	ev_dir = proj / '\ua616/KB/Evidence/GitHub/dmitry-ai__harness'
	ev_dir.mkdir(parents=True, exist_ok=True)
	url = f'https://github.com/dmitry-ai/harness/issues/{num}'
	(ev_dir / f'issue-{num}.json').write_text(json.dumps({'url': url, 'html_url': url, 'repo': 'dmitry-ai/harness', 'kind': 'issue', 'number': num, 'state': 'open', 'title': f'Open parent {num}', 'body': 'Observed details.'}), encoding='utf-8')
# 2026-11-24
# "Add structured problem metadata builder and CLI command":
# https://github.com/dmitry-ai/harness/issues/180
class ProblemMetadataTests(unittest.TestCase):
	# 2026-11-28 "Reject invalid or foreign GitHub issues in problem-metadata builder and CLI": https://github.com/dmitry-ai/harness/issues/429
	# @used-by :mod:`unittest`
	def test_build_problem_metadata_and_cli_reject_unverified_closed_child_and_foreign_issues(self) -> None:
		foreign_cid = '99999999-aaaa-4bbb-8ccc-dddddddddddd'
		with tempfile.TemporaryDirectory() as tmp:
			b: ProblemReportFixtureBuilder = ProblemReportFixtureBuilder(Path(tmp)).with_git_repo().add_issue(501).add_issue(502, state='closed').add_issue(503, parent_number=406).add_issue(504, owner_cid=foreign_cid, owner_turn_key='tk-foreign', action=None)
			ctx = b.build_workspace()
			proj, env = (ctx['root'], {'ANTIGRAVITY_CONVERSATION_ID': ctx['cid']})
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=None):
				ok_meta = metadata.build_problem_metadata(issue_url='https://github.com/dmitry-ai/harness/issues/501', project_root=proj, env=env)
				self.assertEqual('https://github.com/dmitry-ai/harness/issues/501', ok_meta['Issue'])
				for num, code in ((502, 'CLOSED_PROBLEM_ISSUE'), (503, 'CHILD_PROBLEM_ISSUE'), (504, 'FOREIGN_PROBLEM_ISSUE'), (99999, 'UNVERIFIED_PROBLEM_ISSUE')):
					with self.subTest(issue=num), self.assertRaisesRegex(ValueError, code):
						metadata.build_problem_metadata(issue_url=f'https://github.com/dmitry-ai/harness/issues/{num}', project_root=proj, env=env)
				with self.assertRaisesRegex(ValueError, 'INJECTED_SPEC_DENY'):
					metadata.build_problem_metadata(issue_url='https://github.com/dmitry-ai/harness/issues/501', project_root=proj, env=env, issue_spec=lambda _u, _r: ['INJECTED_SPEC_DENY'])
			harness_cli = str(SCRIPT_DIR / 'harness.py')
			sub_env = isolated_subprocess_env(ANTIGRAVITY_CONVERSATION_ID=ctx['cid'])
			bad_cli = subprocess.run([sys.executable, harness_cli, 'problem-metadata', str(proj), '--issue', 'https://github.com/dmitry-ai/harness/issues/502'], env=sub_env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=False, timeout=30)
			self.assertNotEqual(0, bad_cli.returncode)
			self.assertIn('CLOSED_PROBLEM_ISSUE', bad_cli.stderr + bad_cli.stdout)
		with tempfile.TemporaryDirectory() as tmp2:
			b2: ProblemReportFixtureBuilder = ProblemReportFixtureBuilder(Path(tmp2)).with_git_repo().add_issue(604, owner_cid=foreign_cid, owner_turn_key='tk-old', action='fetch')
			ctx2 = b2.build_workspace(requests=[{'id': 'r1', 'text': 'Investigate https://github.com/dmitry-ai/harness/issues/604'}])
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=None):
				req_meta = metadata.build_problem_metadata(issue_url='https://github.com/dmitry-ai/harness/issues/604', project_root=ctx2['root'], env={'ANTIGRAVITY_CONVERSATION_ID': ctx2['cid']})
			self.assertEqual('https://github.com/dmitry-ai/harness/issues/604', req_meta['Issue'])
	# @used-by :mod:`unittest`
	def test_build_problem_metadata_rejects_missing_or_invalid_issue_url(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp) / 'demo'
			proj.mkdir()
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=None):
				with self.assertRaises(ValueError):
					metadata.build_problem_metadata(project_root=proj, env={})
				with self.assertRaises(ValueError):
					metadata.build_problem_metadata(issue_url='not-a-github-url', project_root=proj, env={})
				with self.assertRaises(ValueError):
					metadata.build_problem_metadata(issue_url='https://example.com/issues/1', project_root=proj, env={})
	# @used-by :mod:`unittest`
	def test_build_problem_metadata_with_issue_url_and_distinct_source_project(self) -> None:
		tz_plus3 = timezone(timedelta(hours=3))
		now_dt = datetime(2026, 11, 24, 1, 30, 0, tzinfo=timezone.utc)
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'client-proj'
			src_proj = base / 'harness-root'
			proj.mkdir()
			src_proj.mkdir()
			_seed_open_parent_issue(proj, 180)
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=None):
				meta = metadata.build_problem_metadata(
					issue_url='https://github.com/dmitry-ai/harness/issues/180/',
					project_root=proj,
					source_project_root=src_proj,
					env={},
					now=now_dt,
					tz=tz_plus3,
				)
				same_src = metadata.build_problem_metadata(
					issue_url='https://github.com/dmitry-ai/harness/issues/180',
					project_root=proj,
					source_project_root=proj,
					env={},
					now=now_dt,
					tz=tz_plus3,
				)
			self.assertEqual(meta['Time'], '2026-11-24 04:30:00 UTC+3')
			self.assertEqual(meta['Issue'], 'https://github.com/dmitry-ai/harness/issues/180')
			self.assertEqual(meta['Project'], {'Name': 'client-proj', 'Path': proj.as_posix()})
			self.assertEqual(meta['Source Project'], {'Name': 'harness-root', 'Path': src_proj.as_posix()})
			self.assertNotIn('Source Project', same_src)
	# @used-by :mod:`unittest`
	def test_build_problem_metadata_allow_no_issue_keeps_mandatory_issue_key(self) -> None:
		tz_plus3 = timezone(timedelta(hours=3))
		now_dt = datetime(2026, 11, 24, 1, 30, 0, tzinfo=timezone.utc)
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'local-only'
			proj.mkdir()
			with patch('agent_tools.metadata._resolve_ag_paths_safe', return_value=None):
				meta = metadata.build_problem_metadata(project_root=proj, allow_no_issue=True, env={}, now=now_dt, tz=tz_plus3)
			self.assertIn('Issue', meta)
			self.assertIsNone(meta['Issue'])
			self.assertEqual(meta['Project']['Name'], 'local-only')
	# @used-by :mod:`unittest`
	def test_cli_problem_metadata_outputs_json_and_markdown_and_enforces_issue_key(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'cli-proj'
			proj.mkdir()
			_seed_open_parent_issue(proj, 180)
			harness_cli = str(SCRIPT_DIR / 'harness.py')
			# 2026-11-26 "Add contract invariants for metadata test env isolation and worktree-land gates": https://github.com/dmitry-ai/harness/issues/366
			sub_env = isolated_subprocess_env()
			bad = subprocess.run([sys.executable, harness_cli, 'problem-metadata', str(proj)], env=sub_env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=False, timeout=30)
			self.assertNotEqual(0, bad.returncode)
			ok_json = subprocess.run(
				[sys.executable, harness_cli, 'problem-metadata', str(proj), '--issue', 'https://github.com/dmitry-ai/harness/issues/180', '--format', 'json'],
				env=sub_env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=False, timeout=30,
			)
			self.assertEqual(0, ok_json.returncode, ok_json.stderr or ok_json.stdout)
			payload = json.loads(ok_json.stdout)
			self.assertTrue(payload['valid'])
			self.assertEqual(payload['metadata']['Issue'], 'https://github.com/dmitry-ai/harness/issues/180')
			self.assertTrue(payload['markdown'].startswith('```json\n{\n\t"Time":'))
			ok_md = subprocess.run(
				[sys.executable, harness_cli, 'problem-metadata', str(proj), '--no-issue', '--format', 'markdown'],
				env=sub_env, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=False, timeout=30,
			)
			self.assertEqual(0, ok_md.returncode, ok_md.stderr or ok_md.stdout)
			self.assertTrue(ok_md.stdout.startswith('```json\n{\n\t"Time":'))
			self.assertIn('\t"Issue": null', ok_md.stdout)
if '__main__' == __name__:
	unittest.main()
