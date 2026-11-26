# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = WT_ROOT / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
_ALPHA_SRC = (
	'import subprocess, sys, time, unittest\n'
	'def _busy_work(n):\n'
	'\treturn sum((i * i for i in range(n)))\n'
	'class AlphaTests(unittest.TestCase):\n'
	'\tdef test_subprocess_sleep_and_cpu(self):\n'
	'\t\tproc = subprocess.run([sys.executable, "-c", "print(42)"], capture_output=True, text=True, check=True)\n'
	'\t\tself.assertEqual("42", proc.stdout.strip())\n'
	'\t\ttime.sleep(0.03)\n'
	'\t\tself.assertGreater(_busy_work(4000), 0)\n'
)
_BETA_SRC = (
	'import unittest\n'
	'class BetaTests(unittest.TestCase):\n'
	'\tdef test_fast_pass(self):\n'
	'\t\tself.assertEqual(2, 1 + 1)\n'
	'\t@unittest.skip("demo skip")\n'
	'\tdef test_skipped(self):\n'
	'\t\tself.fail("unreachable")\n'
)
# @used-by :meth:`PerfProfileTestsSuiteTests.test_cli_perf_profile_tests_help_json_output_and_text_format()`
# @used-by :meth:`PerfProfileTestsSuiteTests.test_profile_test_suite_measures_files_tests_popen_sleep_and_cprofile()`
def _write_demo_suite(base: Path) -> Path:
	tests_dir = base / 'tests'
	tests_dir.mkdir(parents=True, exist_ok=True)
	(tests_dir / 'test_alpha.py').write_text(_ALPHA_SRC, encoding='utf-8')
	(tests_dir / 'test_beta.py').write_text(_BETA_SRC, encoding='utf-8')
	return tests_dir
# 2026-11-24
# "Add harness perf-profile-tests CLI for test suite and subprocess profiling":
# https://github.com/dmitry-ai/harness/issues/192
class PerfProfileTestsSuiteTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_cli_perf_profile_tests_help_json_output_and_text_format(self) -> None:
		p_help = subprocess.run([sys.executable, str(SCRIPT_DIR / 'harness.py'), 'perf-profile-tests', '--help'], capture_output=True, text=True, encoding='utf-8', check=True)
		for flag in ('--workers', '--module', '--cprofile', '--top', '--output', '--format'):
			self.assertIn(flag, p_help.stdout)
		with tempfile.TemporaryDirectory() as td:
			tmp = Path(td)
			tests_dir = _write_demo_suite(tmp)
			out_json = tmp / 'profile.json'
			proc = subprocess.run([sys.executable, str(SCRIPT_DIR / 'harness.py'), 'perf-profile-tests', str(tests_dir), '--workers', '2', '--cprofile', '--output', str(out_json), '--format', 'text'], capture_output=True, text=True, encoding='utf-8', check=True)
			self.assertIn('Parallel wall:', proc.stdout)
			self.assertIn('Popen:', proc.stdout)
			self.assertTrue(out_json.is_file())
			saved = json.loads(out_json.read_text(encoding='utf-8'))
			self.assertEqual(2, saved['total_files'])
			self.assertEqual(3, saved['total_tests'])
	# @used-by :mod:`unittest`
	def test_profile_test_suite_measures_files_tests_popen_sleep_and_cprofile(self) -> None:
		from agent_tools.perf.suite_profiler import profile_test_suite
		with tempfile.TemporaryDirectory() as td:
			tests_dir = _write_demo_suite(Path(td))
			rep = profile_test_suite(tests_dir, workers=2, enable_cprofile=True, top_n=5, cprofile_top=10)
			self.assertTrue(rep['valid'])
			self.assertEqual(2, rep['total_files'])
			self.assertEqual(3, rep['total_tests'])
			self.assertEqual(0, rep['total_failures'])
			self.assertEqual(0, rep['total_errors'])
			self.assertEqual(1, rep['total_skipped'])
			self.assertGreaterEqual(rep['totals']['popen_count'], 1)
			self.assertGreaterEqual(rep['totals']['python_count'], 1)
			self.assertGreater(rep['totals']['popen_s'], 0.0)
			self.assertGreaterEqual(rep['totals']['sleep_count'], 1)
			self.assertGreaterEqual(rep['totals']['sleep_s'], 0.02)
			self.assertEqual('test_alpha.py', rep['top_files'][0]['file'])
			self.assertIn('test_subprocess_sleep_and_cpu', rep['top_tests'][0]['test_id'])
			self.assertTrue(rep['cprofile_top'])
			self.assertIn('cumtime', rep['cprofile_top'][0])
if '__main__' == __name__:
	unittest.main()
