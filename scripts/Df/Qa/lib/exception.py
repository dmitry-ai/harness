# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import builtins
from Df.Core.Exception import Exception as DFE
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2023-08-02 "Treat `\Throwable` similar to `\Exception`": https://github.com/mage2pro/core/issues/311
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/exception.php#L24
# @used-by :func:`Df.Qa.lib.bt.main.df_bt()`
# @used-by :func:`Df.Qa.lib.bt.main.df_bt_inc()`
# @used-by :func:`Df.Qa.lib.validation.error.df_error_create()`
# @used-by :func:`df_xts()`
# @used-by :func:`df_xtsd()`
# @used-by :meth:`test_df_qa.TestDfQa.test_diagnostics_and_exceptions()`
def df_is_th(v: Any) -> bool:
	return isinstance(v, BaseException)
# 2023-08-02 Return True iff `v` is an Exception instance (excluding BaseException subclasses like KeyboardInterrupt).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/exception.php#L32
# @used-by :func:`df_th2x()`
# @used-by :meth:`test_df_qa.TestDfQa.test_diagnostics_and_exceptions()`
def df_is_x(v: Any) -> bool:
	return isinstance(v, builtins.Exception)
# 2023-08-03 Convert any BaseException into an Exception, preserving cause chaining.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/exception.php#L70
# @used-by :meth:`test_df_qa.TestDfQa.test_diagnostics_and_exceptions()`
def df_th2x(t: BaseException) -> builtins.Exception:
	if df_is_x(t):
		r: builtins.Exception = t
	else:
		r = builtins.Exception(df_xts(t))
		r.__cause__ = t
	return r
# 2016-07-18 Unwrap chained exceptions to return the innermost root-cause BaseException.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/exception.php#L78
# @used-by :meth:`Df.Qa.Failure.Exception.Exception._trace()`
# @used-by :meth:`test_df_qa.TestDfQa.test_diagnostics_and_exceptions()`
def df_xf(t: BaseException) -> BaseException:
	r = t
	while None is not (r.__cause__ or r.__context__):
		r = r.__cause__ or r.__context__
	return r
# Convert an exception or string into its diagnostic message.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/exception.php#L112-L114
# @used-by :func:`Df.Core.lib.text.format.df_sprintf_strict()`
# @used-by :func:`df_th2x()`
# @used-by :meth:`Df.Core.Exception.Exception.__init__()`
# @used-by :meth:`Df.Qa.Trace.Formatter.Formatter.__onError()`
# @used-by :meth:`test_df_qa.TestDfQa.test_diagnostics_and_exceptions()`
def df_xts(t: Any) -> str:
	if not df_is_th(t):
		r = str(t)
	elif isinstance(t, DFE):
		r = t.message()
	else:
		r = str(t)
	return r
# 2016-10-24 Convert an exception or string into its developer message.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/exception.php#L124-L126
# @used-by :meth:`test_df_qa.TestDfQa.test_diagnostics_and_exceptions()`
def df_xtsd(t: Any) -> str:
	if not df_is_th(t):
		r = str(t)
	elif isinstance(t, DFE):
		r = t.messageD()
	else:
		r = str(t)
	return r