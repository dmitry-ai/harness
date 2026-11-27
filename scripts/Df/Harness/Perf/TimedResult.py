# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, override
import time
import unittest
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class TimedResult(unittest.TestResult):
	STAT_KEYS = ('popen_count', 'popen_s', 'git_count', 'git_s', 'python_count', 'python_s', 'other_proc_count', 'other_proc_s', 'sleep_count', 'sleep_s')
	# @used-by :meth:`Df.Harness.Perf.SuiteWorker.SuiteWorker.run()`
	# @see :meth:`unittest.TestResult.__init__()`
	@override
	def __init__(self, stats: dict[str, Any], rel_file: str) -> None:
		super().__init__()
		self.__stats = stats
		self.__rel_file = rel_file
		self.__t0 = 0.0
		self.__snap: dict[str, Any] = {}
		self.__status = 'ok'
		self.records: list[dict[str, Any]] = []
	# @used-by :meth:`Df.Harness.Perf.SuiteWorker.SuiteWorker.run()`
	@staticmethod
	def blank_stats() -> dict[str, Any]:
		return {k: 0 if k.endswith('_count') else 0.0 for k in TimedResult.STAT_KEYS}
	# @used-by :meth:`Df.Harness.Perf.SuiteWorker.SuiteWorker.run()`
	# @used-by :meth:`TimedResult.stopTest()`
	@staticmethod
	def diff_stats(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
		return {k: (after[k] - before[k]) if k.endswith('_count') else round(max(0.0, after[k] - before[k]), 4) for k in TimedResult.STAT_KEYS}
	# @used-by :meth:`unittest.TestResult.addError()`
	# @see :meth:`unittest.TestResult.addError()`
	@override
	def addError(self, test, err) -> None:
		self.__status = 'error'
		super().addError(test, err)
	# @used-by :meth:`unittest.TestResult.addFailure()`
	# @see :meth:`unittest.TestResult.addFailure()`
	@override
	def addFailure(self, test, err) -> None:
		self.__status = 'fail'
		super().addFailure(test, err)
	# @used-by :meth:`unittest.TestResult.addSkip()`
	# @see :meth:`unittest.TestResult.addSkip()`
	@override
	def addSkip(self, test, reason) -> None:
		self.__status = 'skip'
		super().addSkip(test, reason)
	# @used-by :meth:`unittest.TestResult.startTest()`
	# @see :meth:`unittest.TestResult.startTest()`
	@override
	def startTest(self, test) -> None:
		self.__status = 'ok'
		self.__t0 = time.perf_counter()
		self.__snap = dict(self.__stats)
		super().startTest(test)
	# @used-by :meth:`unittest.TestResult.stopTest()`
	# @see :meth:`unittest.TestResult.stopTest()`
	@override
	def stopTest(self, test) -> None:
		super().stopTest(test)
		dt = round(max(0.0, time.perf_counter() - self.__t0), 4)
		delta = TimedResult.diff_stats(self.__snap, self.__stats)
		self.records.append({'test_id': test.id(), 'file': self.__rel_file, 'status': self.__status, 'dur_s': dt, **delta})
