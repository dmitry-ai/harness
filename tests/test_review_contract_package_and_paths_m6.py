# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import cli_domains, review
# 2026-11-24
# "Include required package keys in REPORT_CONTRACT and resolve record-review paths":
# https://github.com/dmitry-ai/harness/issues/223
class ReviewContractPackageAndPathsM6Tests(unittest.TestCase):
	def test_report_contract_and_validator_require_package_envelope_keys(self) -> None:
		req_fields = review.REPORT_CONTRACT.get('required_top_level_fields') or []
		self.assertIn('package', req_fields)
		self.assertIn('package_sha256', req_fields)
		pkg = {
			'project_root': str(WT_ROOT),
			'risk': 'significant',
			'scope': list(review.SCOPES),
			'claims': [{'claim_id': 'F-1', 'essence': 'Claim text', 'response_excerpt': 'Claim text'}],
			'package': 'ꘖ/KB/Evidence/Reviews/abc-inputs.json',
			'package_sha256': 'a' * 64,
		}
		report_missing_both = {
			'schema_version': review.REVIEW_SCHEMA,
			'review_mode': 'falsifier',
			'result': 'approved',
			'scope': list(review.SCOPES),
			'disproved_claims': [],
			'findings': [],
		}
		env_issues = review.report_issues(report_missing_both, pkg, require_envelope=True)
		self.assertTrue(any(('package' in item for item in env_issues)), env_issues)
		report_missing_path = {**report_missing_both, 'package_sha256': 'a' * 64}
		partial_issues = review.report_issues(report_missing_path, pkg)
		self.assertTrue(any(('package' in item for item in partial_issues)), partial_issues)
	def test_record_review_resolves_project_relative_report_from_foreign_cwd(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj = base / 'daily_project'
			foreign_cwd = base / 'launcher_init'
			foreign_cwd.mkdir(parents=True)
			rel_report = 'ꘖ/KB/Evidence/Reviews/rev-authored.txt'
			abs_report = proj / rel_report
			abs_report.parent.mkdir(parents=True)
			abs_report.write_text('{"schema_version": 2}', encoding='utf-8')
			args = argparse.Namespace(project=str(proj), parent='p-1', reviewer='r-1', report=rel_report, native_evidence='ꘖ/KB/Evidence/Reviews/rev-native.json', consume_input=False, expected_sha256=None)
			old_cwd = os.getcwd()
			captured = {}
			def _fake_record(project, payload, **kwargs):
				captured['project'] = project
				captured['payload'] = payload
				captured['kwargs'] = kwargs
				return {'recorded': True}
			try:
				os.chdir(foreign_cwd)
				with patch('agent_tools.workflow.record_review', side_effect=_fake_record):
					res = cli_domains._op_record_review(args)
			finally:
				os.chdir(old_cwd)
			self.assertEqual({'recorded': True}, res)
			self.assertEqual(b'{"schema_version": 2}', captured['payload'])
if '__main__' == __name__:
	unittest.main()
