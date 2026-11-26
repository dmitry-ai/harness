# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
from Df.Core.lib.array.first import df_first
from Df.Core.lib.empty import df_eta
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2017-03-28 Inspect the backtrace and return the first non-closure caller entry matching optional predicate `f`.
# 2023-07-26 "Add the `$skip` optional parameter to `df_caller_entry()`": https://github.com/mage2pro/core/issues/281
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/caller/entry.php#L4-L45
# @used-by :func:`Df.Core.lib.caller.other.df_caller_f()`
# @used-by :func:`Df.Core.lib.caller.other.df_caller_m()`
# @used-by :func:`Df.Core.lib.caller.other.df_caller_mf()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_caller_entry(p: Any=0, f: Callable[[dict[str, Any]], bool] | None=None, skip: list[str] | None=None) -> dict[str, Any]:
	from Df.Qa.lib.bt.filter import df_bt_filter_head
	from Df.Qa.lib.bt.main import df_bt, df_bt_inc
	bt = df_bt(df_bt_inc(p, 2))
	res = df_eta(df_first(df_bt_filter_head(bt, list(skip or ()), f)))
	return res if isinstance(res, dict) else {}
