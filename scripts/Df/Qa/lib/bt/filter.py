# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
from Df.Core.lib.array.clean.filter import df_filter_head
from Df.Core.lib.text.contains import df_contains
from Df.Qa.lib.bt.entry import df_bt_entry_func
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2024-03-04 "Implement `df_bt_filter_head()`": https://github.com/mage2pro/core/issues/356
# 2023-07-26 "Add the `$skip` optional parameter to `df_caller_entry()`": https://github.com/mage2pro/core/issues/281
# 2020-09-24 Includes "unknown" for debugger expression evaluation frames.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/filter.php#L11-L26
# @used-by :func:`Df.Core.lib.caller.entry.df_caller_entry()`
# @used-by :meth:`Df.Qa.Trace.Trace.__init__()`
# @used-by :meth:`test_df_qa.TestDfQa.test_bt_helpers()`
def df_bt_filter_head(bt: list[dict[str, Any]], skip: list[str] | None=None, f: Callable[[dict[str, Any]], bool] | None=None) -> list[dict[str, Any]]:
	skip_all = [*(skip or ()), 'dfc', 'dfcf', 'unknown']
	return list(df_filter_head(bt, lambda e: df_contains(df_bt_entry_func(e), '{closure}') or '<lambda>' == df_bt_entry_func(e) or df_bt_entry_func(e) in skip_all or (None is not f and (not f(e)))))