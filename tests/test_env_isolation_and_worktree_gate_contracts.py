# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add contract invariants for metadata test env isolation and worktree-land gates":
# https://github.com/dmitry-ai/harness/issues/366
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import os
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for _p in (SCRIPTS, TESTS):
	if str(_p) not in sys.path:
		sys.path.insert(0, str(_p))
# @used-by :meth:`EnvIsolationAndWorktreeGateContractsTests.test_cleanup_audit_and_diff_coverage_pass_under_conflicting_a0_host_env()`
def _run_test_case(case_cls: type[unittest.TestCase], method_name: str) -> unittest.TestResult:
	suite = unittest.TestSuite([case_cls(method_name)])
	result = unittest.TestResult()
	suite.run(result)
	return result
# @used-by :mod:`unittest`
class EnvIsolationAndWorktreeGateContractsTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_cleanup_audit_and_diff_coverage_pass_under_conflicting_a0_host_env(self) -> None:
		from test_cleanup_audit import CleanupAuditTests
		from test_diff_coverage_gate import DiffCoverageGateTests
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			poison = {
				'ANTIGRAVITY_ACCOUNT': 'A0',
				'ANTIGRAVITY_APP_DATA_DIR': str(root / 'host_a0/.gemini/antigravity'),
				'CODEX_HOME': str(root / 'host_codex/C1'),
			}
			with patch.dict(os.environ, poison, clear=False):
				r_clean = _run_test_case(CleanupAuditTests, 'test_cleanup_report_writes_metadata_header_links_manifest_and_consumes_scratch_file')
				r_cov = _run_test_case(DiffCoverageGateTests, 'test_select_targeted_narrows_large_cross_cutting_test_diffs_to_prod_stems_and_packages')
			self.assertEqual([], r_clean.failures, r_clean.failures)
			self.assertEqual([], r_clean.errors, r_clean.errors)
			self.assertEqual([], r_cov.failures, r_cov.failures)
			self.assertEqual([], r_cov.errors, r_cov.errors)
	# @used-by :mod:`unittest`
	def test_harness_metadata_tests_pass_host_env_isolation_contract_and_negative_detection(self) -> None:
		from agent_tools.env_isolation_contracts import HOST_PROFILE_ENV_VARS, audit_metadata_test_env_isolation, isolated_host_env, isolated_subprocess_env
		self.assertEqual(('ANTIGRAVITY_ACCOUNT', 'ANTIGRAVITY_APP_DATA_DIR', 'CODEX_HOME'), HOST_PROFILE_ENV_VARS)
		self.assertTrue(all(('' == isolated_host_env()[k] for k in HOST_PROFILE_ENV_VARS)))
		sub = isolated_subprocess_env({'PATH': '/bin', 'ANTIGRAVITY_APP_DATA_DIR': 'C:/A0', 'CODEX_HOME': 'C:/C1'}, ANTIGRAVITY_ACCOUNT='A6')
		self.assertEqual('A6', sub['ANTIGRAVITY_ACCOUNT'])
		self.assertEqual('', sub['ANTIGRAVITY_APP_DATA_DIR'])
		self.assertEqual('', sub['CODEX_HOME'])
		self.assertEqual([], audit_metadata_test_env_isolation(TESTS))
		with tempfile.TemporaryDirectory() as td:
			fake_tests = Path(td).resolve()
			(fake_tests / 'test_bad_meta.py').write_text(
				'from unittest.mock import patch\nimport subprocess, unittest\n'
				'class Bad(unittest.TestCase):\n'
				'\tdef test_partial_patch(self):\n'
				'\t\tfake_env = {"ANTIGRAVITY_ACCOUNT": "A6"}\n'
				'\t\twith patch.dict("os.environ", fake_env, clear=False):\n'
				'\t\t\trecord_cleanup_answer("ok")\n'
				'\tdef test_unisolated_cli(self):\n'
				'\t\tsubprocess.run(["python", "harness.py", "problem-metadata", "."], stdin=subprocess.DEVNULL, timeout=10)\n',
				encoding='utf-8',
			)
			errs = audit_metadata_test_env_isolation(fake_tests)
			self.assertGreaterEqual(len(errs), 2, errs)
			self.assertTrue(any(('ANTIGRAVITY_APP_DATA_DIR' in e and 'CODEX_HOME' in e for e in errs)), errs)
			self.assertTrue(any(('test_unisolated_cli' in e for e in errs)), errs)
			(fake_tests / 'test_bad_meta.py').unlink()
			(fake_tests / 'test_good_meta.py').write_text(
				'from agent_tools.env_isolation_contracts import isolated_host_env, isolated_subprocess_env\n'
				'from unittest.mock import patch\nimport subprocess, unittest\n'
				'class Good(unittest.TestCase):\n'
				'\tdef test_clean(self):\n'
				'\t\twith patch.dict("os.environ", isolated_host_env(ANTIGRAVITY_ACCOUNT="A6"), clear=False):\n'
				'\t\t\trecord_cleanup_answer("ok")\n'
				'\tdef test_clean_cli(self):\n'
				'\t\tsubprocess.run(["python", "harness.py", "problem-metadata", "."], env=isolated_subprocess_env(), stdin=subprocess.DEVNULL, timeout=10)\n',
				encoding='utf-8',
			)
			self.assertEqual([], audit_metadata_test_env_isolation(fake_tests))
	# @used-by :mod:`unittest`
	def test_harness_worktree_land_gates_pass_scaling_and_timeout_contract_and_negative_detection(self) -> None:
		from agent_tools.env_isolation_contracts import audit_worktree_land_gate_contracts
		self.assertEqual([], audit_worktree_land_gate_contracts(SCRIPTS, TESTS))
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			sdir = base / 'scripts/agent_tools'
			tdir = base / 'tests'
			sdir.mkdir(parents=True)
			tdir.mkdir(parents=True)
			(sdir / 'worktree_flow.py').write_text(
				'def _rebase_and_test():\n\tverify_worktree_extra_gate()\n'
				'def _run_land_checks():\n\tverify_worktree_diff_coverage()\n'
				'def _run_land_tests():\n\tpass\n'
				'def _post_merge_checks():\n\tpass\n',
				encoding='utf-8',
			)
			(tdir / 'test_stub.py').write_text('import unittest\nclass S(unittest.TestCase):\n\tdef test_empty(self):\n\t\tpass\n', encoding='utf-8')
			reg = {'verify_worktree_diff_coverage': {'timeout_tests': (('test_stub.py', 'S.test_empty'),)}}
			errs = audit_worktree_land_gate_contracts(base / 'scripts', tdir, registry=reg)
			self.assertTrue(any(('verify_worktree_extra_gate' in e for e in errs)), errs)
			self.assertTrue(any(('S.test_empty' in e for e in errs)), errs)
if '__main__' == __name__:
	unittest.main()
