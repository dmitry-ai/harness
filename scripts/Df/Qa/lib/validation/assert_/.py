# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Qa.lib.validation.error import df_error
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2019-12-14 Return `cond` when truthy, otherwise raise a Df\Core\Exception via df_error(*a).
# 2024-06-02 "Improve `df_assert()`": https://github.com/mage2pro/core/issues/401
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/.php#L77
# @used-by :func:`Df.Core.lib.caller.other.df_caller_m()`
# @used-by :func:`Df.Core.lib.caller.other.df_caller_mf()`
# @used-by :func:`Df.Core.lib.date.df_date_from_timestamp_14()`
# @used-by :func:`Df.Core.lib.date.df_dtss()`
# @used-by :func:`Df.Core.lib.empty.df_eta()`
# @used-by :func:`Df.Qa.lib.validation.error.df_error_create()`
# @used-by :func:`float._float_str()`
# @used-by :func:`stringable.df_assert_stringable()`
# @used-by :meth:`Df.Core.Html.Tag.Tag.__formatAttr()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.__getParam()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_array_and_bool()`
def df_assert(cond: Any, *a: Any) -> Any:
	if not cond:
		df_error(*a)
	return cond