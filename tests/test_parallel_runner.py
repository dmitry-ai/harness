# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import time
import unittest
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools.context import assemble, generate
from agent_tools.storage import locked
from agent_tools.tdd_gate import classify_test_command
# 2026-11-23
# "Add parallel fail-fast test runner and worktree-aware TDD support":
# https://github.com/dmitry-ai/harness/issues/159
class ParallelRunnerTests(unittest.TestCase):
	def _write_module(self, root: Path, name: str, body: str) -> Path:
		path = root / name
		path.write_text(body, encoding='utf-8')
		return path
	def test_classify_run_tests_full_and_filtered(self):
		full_cmd = 'python "C:/work/harness/scripts/harness.py" run-tests "C:/work/harness/tests" --workers 4'
		res_full = classify_test_command(full_cmd)
		self.assertTrue(res_full['is_test_cmd'])
		self.assertTrue(res_full['is_full_suite'])
		filt_cmd = 'python "C:/work/harness/scripts/harness.py" run-tests "C:/work/harness/tests" --module test_alpha'
		res_filt = classify_test_command(filt_cmd)
		self.assertTrue(res_filt['is_test_cmd'])
		self.assertFalse(res_filt['is_full_suite'])
		alias_cmd = 'python upwork_project.py run-tests tests'
		res_alias = classify_test_command(alias_cmd)
		self.assertTrue(res_alias['is_test_cmd'])
		self.assertTrue(res_alias['is_full_suite'])
	def test_context_generate_accepts_fixed_now(self):
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			kb = root / '\ua616/KB/Overview.md'
			kb.parent.mkdir(parents=True, exist_ok=True)
			kb.write_text('# Overview\nBody\n', encoding='utf-8')
			fixed = datetime(2026, 11, 23, 19, 30, 0, tzinfo=timezone.utc)
			c_asm, s_asm = assemble(root, now=fixed)
			target, c_gen, s_gen = generate(root, now=fixed)
			self.assertTrue(target.is_file())
			self.assertEqual(c_gen, c_asm)
			self.assertEqual(set(s_gen), set(s_asm))
	def test_discover_orders_heaviest_modules_first(self):
		from agent_tools.parallel_runner import discover_test_modules
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			self._write_module(root, 'test_small.py', 'import unittest\n')
			self._write_module(root, 'test_big.py', 'import unittest\n' + ('# pad\n' * 80))
			ordered = discover_test_modules(root, timings={'test_small': 12.0, 'test_big': 1.0})
			self.assertEqual([p.stem for p in ordered], ['test_small', 'test_big'])
			by_size = discover_test_modules(root)
			self.assertEqual([p.stem for p in by_size], ['test_big', 'test_small'])
	def test_parallel_runner_failfast_kills_slow_siblings(self):
		from agent_tools.parallel_runner import run_parallel_tests
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			self._write_module(root, 'test_a_fast_fail.py', 'import unittest\nclass T(unittest.TestCase):\n\tdef test_fail(self):\n\t\tself.assertEqual(1, 2)\n')
			self._write_module(root, 'test_b_slow.py', 'import time, unittest\nclass T(unittest.TestCase):\n\tdef test_slow(self):\n\t\ttime.sleep(20)\n\t\tself.assertTrue(True)\n')
			started = time.monotonic()
			res = run_parallel_tests(root, workers=2, failfast=True, module_timeout=25.0)
			elapsed = time.monotonic() - started
			self.assertFalse(res['ok'])
			self.assertEqual(res['failed_module'], 'test_a_fast_fail')
			self.assertLess(elapsed, 8.0)
	def test_parallel_runner_module_timeout_terminates_stalled_worker(self):
		from agent_tools.parallel_runner import run_parallel_tests
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			self._write_module(root, 'test_hang.py', 'import time, unittest\nclass T(unittest.TestCase):\n\tdef test_hang(self):\n\t\ttime.sleep(15)\n')
			started = time.monotonic()
			res = run_parallel_tests(root, workers=1, failfast=True, module_timeout=1.0)
			elapsed = time.monotonic() - started
			self.assertFalse(res['ok'])
			self.assertTrue(res['timed_out'])
			self.assertEqual(res['failed_module'], 'test_hang')
			self.assertLess(elapsed, 6.0)
	def test_parallel_runner_passes_all_modules_via_cli(self):
		from agent_tools.upwork_project import main as cli_main
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			self._write_module(root, 'test_one.py', 'import unittest\nclass T1(unittest.TestCase):\n\tdef test_ok(self):\n\t\tself.assertEqual(2 + 2, 4)\n')
			self._write_module(root, 'test_two.py', 'import unittest\nclass T2(unittest.TestCase):\n\tdef test_ok(self):\n\t\tself.assertTrue(True)\n')
			rc = cli_main(['run-tests', str(root), '--workers', '2', '--module-timeout', '15'])
			self.assertEqual(rc, 0)
	def test_storage_locked_concurrent_threads_no_permission_error(self):
		with tempfile.TemporaryDirectory() as td:
			lock_file = Path(td) / 'race.lock'
			counter = {'n': 0}
			def worker(_idx):
				for _ in range(15):
					with locked(lock_file, timeout=10):
						counter['n'] += 1
				return True
			with ThreadPoolExecutor(max_workers=6) as pool:
				results = list(pool.map(worker, range(6)))
			self.assertEqual(results, [True] * 6)
			self.assertEqual(counter['n'], 90)
if '__main__' == __name__:
	unittest.main()
