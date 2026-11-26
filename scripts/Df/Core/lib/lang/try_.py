# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2017-04-15 Execute `try_fn`; on exception invoke `onE` if callable, re-throw via df_error if True/Exception, else return `onE`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/try.php#L4-L52
# @used-by :func:`Df.Core.lib.date.df_date_from_db()`
# @used-by :func:`Df.Core.lib.text.trim.df_trim()`
# @used-by :meth:`Df.Qa.Trace.Formatter.Formatter.p()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.__resolveMethodR()`
def df_try(try_fn: Callable[[], Any], onE: Any=None) -> Any:
	try:
		r = try_fn()
	except BaseException as t:
		if callable(onE):
			r = onE(t)
		elif True is onE or isinstance(onE, BaseException):
			from Df.Qa.lib.validation.error import df_error
			df_error(t)
			r = None
		else:
			r = onE
	return r
