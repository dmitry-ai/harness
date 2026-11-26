# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.array.map.k import df_map_k
from Df.Core.lib.cache.dfcf import dfcf
from Df.Core.lib.lang.try_ import df_try
from Df.Core.lib.text.concatenate import df_cc, df_ccc
from Df.Qa.Trace import Trace
from Df.Qa.lib.exception import df_xts
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2020-02-27 Format a Trace into a numbered multi-line stack trace report.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Formatter.php#L6-L39
class Formatter:
	# 2020-02-27 Format each frame entry with 1-based index, method name, and file:line location.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Formatter.php#L13-L18
	# @used-by :meth:`Formatter.p()`
	# @uses :meth:`Df.Qa.Trace.Trace.__iter__()`
	@staticmethod
	def __format(t: Trace) -> str:
		return df_cc('\n\n', df_map_k(list(t), lambda i, f: df_ccc('\n\t', [f'{i + 1}\t{f.method()}', df_ccc(':', f.file(), f.line() or '')])))
	# 2023-08-03 "Treat `\Throwable` similar to `\Exception`": https://github.com/mage2pro/core/issues/311
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Formatter.php#L20-L37
	# @used-by :meth:`Formatter.p()`
	@staticmethod
	def __onError(th: BaseException) -> str:
		# 2026-11-26 "Return error message from Df\Qa\Trace\Formatter::p() catch handler": https://github.com/dmitry-ai/harness/issues/335
		# Upstream defect: https://github.com/mage2pro/core/issues/478
		return df_xts(th)
	# 2020-02-27 Format and memoize a diagnostic string representation of Trace `t`.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace/Formatter.php#L12-L38
	# @used-by :func:`Df.Qa.lib.bt.log.df_bt_s()`
	# @used-by :meth:`Df.Qa.Failure.Failure._postface()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_trace_and_failure()`
	# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_335_formatter_catch_returns_message()`
	@staticmethod
	def p(t: Trace) -> str:
		return str(dfcf(lambda tr: df_try(lambda: Formatter.__format(tr), Formatter.__onError), [t]))