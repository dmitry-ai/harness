# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Perf.TimedResult import TimedResult
from Df.Harness.Perf.TrackedPopen import TrackedPopen
import cProfile
import json
import os
import profile
import pstats
import sys
import time
import unittest
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class SuiteWorker:
	# @used-by :func:`agent_tools.perf.suite_worker.run_module_profile()`
	# @used-by :meth:`SuiteWorker.main()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_perf_classes_profile_and_build_timesheets()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_perf_profiler_worker_timed_result_and_tracked_popen()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_perf_suite_worker_falls_back_when_cprofile_busy()`
	def __init__(self, mod_path: Path, top_dir: Path, *, cprofile_top: int=0) -> None:
		self.__mod_path = Path(mod_path)
		self.__top_dir = Path(top_dir)
		self.__cprofile_top = cprofile_top
	# @used-by :func:`agent_tools.perf.suite_worker.run_module_profile()`
	# @used-by :meth:`SuiteWorker.main()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_perf_classes_profile_and_build_timesheets()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_perf_profiler_worker_timed_result_and_tracked_popen()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_perf_suite_worker_falls_back_when_cprofile_busy()`
	def run(self) -> dict[str, Any]:
		rel = self.__mod_path.relative_to(self.__top_dir).as_posix()
		stats = TimedResult.blank_stats()
		orig_popen, orig_sleep = TrackedPopen.install(stats)
		try:
			t_load0 = time.perf_counter()
			suite = SuiteWorker.__discover_suite(self.__mod_path, self.__top_dir)
			load_s = round(max(0.0, time.perf_counter() - t_load0), 4)
			import_stats = TimedResult.diff_stats(TimedResult.blank_stats(), stats)
			result = TimedResult(stats, rel)
			t_run0 = time.perf_counter()
			prof = SuiteWorker.__run_profiled(suite, result, self.__cprofile_top)
			run_s = round(max(0.0, time.perf_counter() - t_run0), 4)
		finally:
			TrackedPopen.restore(orig_popen, orig_sleep)
		cp_rows = SuiteWorker.__extract_cprofile(prof, self.__cprofile_top) if None is not prof else []
		return {'file': rel, 'load_s': load_s, 'run_s': run_s, 'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped), 'import_stats': import_stats, 'tests': result.records, 'cprofile': cp_rows}
	# @used-by :meth:`SuiteWorker.run()`
	@staticmethod
	def __discover_suite(mod_path: Path, top_dir: Path) -> unittest.TestSuite:
		mod_name = mod_path.stem
		cached = sys.modules.get(mod_name)
		cached_file = getattr(cached, '__file__', None) if None is not cached else None
		if cached_file and Path(str(cached_file)).resolve() != mod_path.resolve():
			sys.modules.pop(mod_name, None)
		return unittest.TestLoader().discover(str(mod_path.parent), pattern=mod_path.name, top_level_dir=str(top_dir))
	# @used-by :meth:`SuiteWorker.run()`
	@staticmethod
	def __extract_cprofile(prof: Any, top_n: int) -> list[dict[str, Any]]:
		st = pstats.Stats(prof)
		rows = [{'file': Path(fname).as_posix() if fname else '', 'line': int(lineno), 'func': str(func), 'ncalls': int(nc), 'tottime': round(float(tt), 5), 'cumtime': round(float(ct), 5)} for (fname, lineno, func), (_cc, nc, tt, ct, _callers) in st.stats.items()]
		rows.sort(key=lambda item: (-item['cumtime'], -item['tottime']))
		return rows[:max(1, int(top_n))]
	# @used-by :meth:`SuiteWorker.run()`
	@staticmethod
	def __run_profiled(suite: unittest.TestSuite, result: TimedResult, cprofile_top: int) -> Any:
		prof: Any = None
		if 0 >= cprofile_top:
			suite.run(result)
		else:
			try:
				prof = cProfile.Profile()
				prof.runcall(suite.run, result)
			except ValueError:
				prof = profile.Profile()
				prof.runcall(suite.run, result)
		return prof
	# @used-by :func:`agent_tools.perf.suite_worker.main()`
	@staticmethod
	def main(argv: list[str] | None=None) -> int:
		args = list(sys.argv[1:] if None is argv else argv)
		mod_p, top_p, out_p = (Path(args[0]).resolve(), Path(args[1]).resolve(), Path(args[2]).resolve())
		cp_top = int(args[3]) if 3 < len(args) else 0
		if str(top_p) not in sys.path:
			sys.path.insert(0, str(top_p))
		os.environ.setdefault('HARNESS_TEST_NO_FSYNC', '1')
		data = SuiteWorker(mod_p, top_p, cprofile_top=cp_top).run()
		out_p.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
		return 0
