# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add structured problem metadata builder and CLI command":
# https://github.com/dmitry-ai/harness/issues/180
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
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools import metadata
class ProblemMetadataTests(unittest.TestCase):
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
	def test_build_problem_metadata_with_issue_url_and_distinct_source_project(self) -> None:
		tz_plus3 = timezone(timedelta(hours=3))
		now_dt = datetime(2026, 11, 24, 1, 30, 0, tzinfo=timezone.utc)
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'client-proj'
			src_proj = base / 'harness-root'
			proj.mkdir()
			src_proj.mkdir()
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
	def test_cli_problem_metadata_outputs_json_and_markdown_and_enforces_issue_key(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'cli-proj'
			proj.mkdir()
			harness_cli = str(SCRIPT_DIR / 'harness.py')
			bad = subprocess.run([sys.executable, harness_cli, 'problem-metadata', str(proj)], capture_output=True, text=True, encoding='utf-8', check=False)
			self.assertNotEqual(0, bad.returncode)
			ok_json = subprocess.run(
				[sys.executable, harness_cli, 'problem-metadata', str(proj), '--issue', 'https://github.com/dmitry-ai/harness/issues/180', '--format', 'json'],
				capture_output=True, text=True, encoding='utf-8', check=False,
			)
			self.assertEqual(0, ok_json.returncode, ok_json.stderr or ok_json.stdout)
			payload = json.loads(ok_json.stdout)
			self.assertTrue(payload['valid'])
			self.assertEqual(payload['metadata']['Issue'], 'https://github.com/dmitry-ai/harness/issues/180')
			self.assertTrue(payload['markdown'].startswith('```json\n{\n\t"Time":'))
			ok_md = subprocess.run(
				[sys.executable, harness_cli, 'problem-metadata', str(proj), '--no-issue', '--format', 'markdown'],
				capture_output=True, text=True, encoding='utf-8', check=False,
			)
			self.assertEqual(0, ok_md.returncode, ok_md.stderr or ok_md.stdout)
			self.assertTrue(ok_md.stdout.startswith('```json\n{\n\t"Time":'))
			self.assertIn('\t"Issue": null', ok_md.stdout)
if '__main__' == __name__:
	unittest.main()
