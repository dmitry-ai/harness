# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add host test-worker semaphore and worksteal pytest mode":
# https://github.com/dmitry-ai/harness/issues/354
from __future__ import annotations
from pathlib import Path
import inspect
import json
import os
import sys
import tempfile
import time
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import cli_registry, parallel_runner, suite_runner
# @used-by :mod:`unittest`
class WorkerSemaphoreAndXdistTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_worker_semaphore_bounds_total_slots_and_reclaims_dead_and_expired(self) -> None:
		from agent_tools import worker_semaphore
		with tempfile.TemporaryDirectory() as td:
			sdir = Path(td).resolve() / 'test-worker-slots'
			sdir.mkdir(parents=True)
			now = time.time()
			(sdir / 'dead-slot.json').write_text(json.dumps({'owner': 'dead', 'pid': 99999999, 'slots': 3, 'acquired_at': now, 'expires_at': now + 300.0}), encoding='utf-8')
			(sdir / 'expired-slot.json').write_text(json.dumps({'owner': 'exp', 'pid': os.getpid(), 'slots': 2, 'acquired_at': now - 400.0, 'expires_at': now - 5.0}), encoding='utf-8')
			lease1 = worker_semaphore.acquire_worker_slots(3, max_slots=4, slots_dir=sdir, ttl_s=60.0)
			try:
				self.assertEqual(3, lease1['granted'])
				self.assertFalse((sdir / 'dead-slot.json').exists())
				self.assertFalse((sdir / 'expired-slot.json').exists())
				lease2 = worker_semaphore.acquire_worker_slots(4, max_slots=4, slots_dir=sdir, ttl_s=60.0, wait_timeout=0.05)
				try:
					self.assertEqual(1, lease2['granted'])
					lease_fb = worker_semaphore.acquire_worker_slots(2, max_slots=4, slots_dir=sdir, ttl_s=60.0, wait_timeout=0.05, poll_interval=0.02)
					self.assertEqual(1, lease_fb['granted'])
					self.assertFalse(lease_fb['reserved'])
				finally:
					worker_semaphore.release_worker_slots(lease2)
			finally:
				worker_semaphore.release_worker_slots(lease1)
			lease3 = worker_semaphore.acquire_worker_slots(3, max_slots=4, slots_dir=sdir, ttl_s=60.0)
			try:
				self.assertEqual(3, lease3['granted'])
			finally:
				worker_semaphore.release_worker_slots(lease3)
			default_dir = worker_semaphore.default_slots_dir()
			self.assertEqual('test-worker-slots', default_dir.name)
			self.assertEqual('data', default_dir.parent.name)
	# @used-by :mod:`unittest`
	def test_pytest_worksteal_runner_and_cli_runner_option(self) -> None:
		sig = inspect.signature(parallel_runner.run_parallel_tests)
		self.assertGreaterEqual(float(sig.parameters['module_timeout'].default), 300.0)
		with tempfile.TemporaryDirectory() as td:
			tdir = Path(td).resolve() / 'tests'
			tdir.mkdir(parents=True)
			for idx in range(3):
				(tdir / f'test_mod_{idx}.py').write_text(f'import unittest\nclass T{idx}(unittest.TestCase):\n\tdef test_ok(self) -> None:\n\t\tself.assertEqual({idx}, {idx})\n', encoding='utf-8')
			res = suite_runner.run_test_suite(tdir, workers=2, runner='pytest', failfast=True, module_timeout=60.0)
			self.assertTrue(res['ok'], res)
			self.assertEqual('pytest', res.get('runner'))
			self.assertEqual(3, res['total_tests'])
			par = parallel_runner.run_parallel_tests(tdir, workers=2, runner='pytest', failfast=True)
			self.assertTrue(par['ok'], par)
			self.assertEqual('pytest', par.get('runner'))
			self.assertEqual(3, par['total_tests'])
			u_suite = suite_runner.run_test_suite(tdir, workers=2, runner='auto', failfast=True, module_timeout=60.0)
			self.assertTrue(u_suite['ok'], u_suite)
			self.assertEqual('unittest', u_suite.get('runner'))
			u_par = parallel_runner.run_parallel_tests(tdir, workers=2, runner='auto', failfast=True)
			self.assertTrue(u_par['ok'], u_par)
			self.assertEqual('unittest', u_par.get('runner'))
			(tdir / 'test_mod_1.py').write_text('import unittest\nclass T1(unittest.TestCase):\n\tdef test_bad(self) -> None:\n\t\tself.assertEqual(1, 2)\n', encoding='utf-8')
			bad = suite_runner.run_test_suite(tdir, workers=2, runner='pytest', failfast=True, module_timeout=60.0)
			self.assertFalse(bad['ok'])
			self.assertNotEqual(0, bad['exit_code'])
		cli_registry._ensure_builtin_plugins()
		specs = cli_registry._REGISTRY['run-tests']['specs']
		flags = [sp[0] for sp in specs]
		self.assertIn('--runner', flags)
if '__main__' == __name__:
	unittest.main()
