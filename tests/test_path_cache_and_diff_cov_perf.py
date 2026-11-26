# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add RLock to path_cache and migrate diff_coverage to sys.monitoring":
# https://github.com/dmitry-ai/harness/issues/352
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import subprocess
import sys
import tempfile
import threading
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import path_cache
from agent_tools.tdd import diff_coverage
# @used-by :meth:`PathCacheAndDiffCovPerfTests.test_diff_coverage_sys_monitoring_matches_settrace_and_supports_single_pass()`
def _seed_cov_repo(base: Path) -> Path:
	repo = base / 'repo'
	(repo / 'pkg').mkdir(parents=True)
	(repo / 'tests').mkdir(parents=True)
	subprocess.run(['git', 'init', '-b', 'main', str(repo)], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30)
	cfg = repo / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + '[user]\n\temail = t@example.com\n\tname = T\n', encoding='utf-8')
	(repo / 'pkg/__init__.py').write_text('', encoding='utf-8')
	(repo / 'pkg/math_ops.py').write_text('def base_fn() -> int:\n\treturn 0\n', encoding='utf-8')
	(repo / 'tests/test_math_ops.py').write_text('import sys, unittest\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\nfrom pkg import math_ops\nclass M(unittest.TestCase):\n\tdef test_base(self) -> None:\n\t\tself.assertEqual(0, math_ops.base_fn())\n', encoding='utf-8')
	subprocess.run(['git', '-C', str(repo), 'add', '.'], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30)
	subprocess.run(['git', '-C', str(repo), 'commit', '--no-verify', '-m', 'init'], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30)
	return repo
# @used-by :mod:`unittest`
class PathCacheAndDiffCovPerfTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_path_cache_rlock_handles_concurrent_eviction_and_clear(self) -> None:
		lock = getattr(path_cache, '_CACHE_LOCK', None)
		self.assertIsNotNone(lock)
		with lock:
			with lock:
				self.assertTrue(True)
		barrier = threading.Barrier(8)
		errors: list[BaseException] = []
		local_lru: OrderedDict = OrderedDict()
		# @used-by :meth:`PathCacheAndDiffCovPerfTests.test_path_cache_rlock_handles_concurrent_eviction_and_clear()`
		def _worker(tid: int) -> None:
			try:
				barrier.wait(timeout=5.0)
				for idx in range(60):
					key = (tid, idx % 24)
					path_cache.lru_put(local_lru, key, idx)
					path_cache.lru_get(local_lru, key)
					if 0 == idx % 15:
						path_cache.clear_path_cache()
			except BaseException as exc:
				errors.append(exc)
		with patch.object(path_cache, 'CACHE_LIMIT', 12):
			threads = [threading.Thread(target=_worker, args=(i,)) for i in range(8)]
			for th in threads:
				th.start()
			for th in threads:
				th.join(timeout=15.0)
		self.assertEqual([], errors, errors)
	# @used-by :mod:`unittest`
	def test_diff_coverage_sys_monitoring_matches_settrace_and_supports_single_pass(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			repo = _seed_cov_repo(base)
			(repo / 'pkg/math_ops.py').write_text('def base_fn() -> int:\n\treturn 0\ndef used_a(x: int) -> int:\n\treturn x + 1\ndef dead_c(x: int) -> int:\n\treturn x * 2\n', encoding='utf-8')
			(repo / 'tests/test_math_ops.py').write_text('import sys, unittest\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\nfrom pkg import math_ops\nclass M(unittest.TestCase):\n\tdef test_ops(self) -> None:\n\t\tself.assertEqual(0, math_ops.base_fn())\n\t\tself.assertEqual(2, math_ops.used_a(1))\n', encoding='utf-8')
			added = diff_coverage.find_added_production_functions(repo, base_ref='HEAD', include_working_tree=True)
			mods = [repo / 'tests/test_math_ops.py']
			res_mon = diff_coverage.run_trace_diff_coverage(repo, added, mods)
			res_tr = diff_coverage.run_trace_diff_coverage(repo, added, mods, trace_backend='settrace')
			expected_backend = 'sys.monitoring' if hasattr(sys, 'monitoring') else 'sys.settrace'
			self.assertEqual(expected_backend, res_mon.get('backend'))
			self.assertEqual('sys.settrace', res_tr.get('backend'))
			self.assertFalse(res_mon['valid'], res_mon)
			self.assertEqual(res_tr['uncovered'], res_mon['uncovered'])
			self.assertEqual(1, len(res_mon['uncovered']))
			self.assertIn('dead_c', res_mon['uncovered'][0])
			(repo / 'tests/test_math_ops.py').write_text('import sys, unittest\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\nfrom pkg import math_ops\nclass M(unittest.TestCase):\n\tdef test_ops(self) -> None:\n\t\tself.assertEqual(0, math_ops.base_fn())\n\t\tself.assertEqual(2, math_ops.used_a(1))\n\t\tself.assertEqual(6, math_ops.dead_c(3))\n', encoding='utf-8')
			res_ok = diff_coverage.run_trace_diff_coverage(repo, added, mods)
			self.assertTrue(res_ok['valid'], res_ok)
			self.assertEqual([], res_ok['uncovered'])
			with tempfile.TemporaryDirectory() as s_td:
				sp_env, cov_dir = diff_coverage.prepare_single_pass_coverage_env(repo, added, Path(s_td))
				self.assertIn('HARNESS_DIFF_COV_TARGETS', sp_env)
				self.assertEqual(str(cov_dir), sp_env['HARNESS_DIFF_COV_DIR'])
if '__main__' == __name__:
	unittest.main()
