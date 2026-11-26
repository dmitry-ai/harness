# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
from Df.Core.lib.array.is_ import df_is_assoc
from Df.Core.lib.array.other.af import dfaf
from Df.Core.lib.array.other.ita import df_ita
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# @used-by :func:`df_filter()`
def _filter_all(a: list[Any] | dict[Any, Any], f: Callable[[Any], Any]) -> list[Any] | dict[Any, Any]:
	return {k: v for k, v in a.items() if f(v)} if isinstance(a, dict) else [v for v in a if f(v)]
# @used-by :func:`df_filter_head()`
def _filter_head_impl(a: list[Any] | dict[Any, Any], f: Callable[[Any], Any]) -> list[Any] | dict[Any, Any]:
	if isinstance(a, dict):
		r: list[Any] | dict[Any, Any] = {}
		for k, v in a.items():
			if (not r) and f(v):
				continue
			r[k] = v
	else:
		r = []
		for v in a:
			if (not r) and f(v):
				continue
			r.append(v)
	return r
# @used-by :func:`df_filter_tail()`
def _filter_tail_impl(a: list[Any] | dict[Any, Any], f: Callable[[Any], Any]) -> list[Any] | dict[Any, Any]:
	if isinstance(a, dict):
		r: list[Any] | dict[Any, Any] = {}
		for k, v in a.items():
			if f(v):
				break
			r[k] = v
	else:
		r = []
		for v in a:
			if f(v):
				break
			r.append(v)
	return r
# 2016-11-08 Filter any iterable/dict accepting (iterable, predicate) in arbitrary order.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/clean/filter.php#L2-L26
# @used-by :func:`Df.Core.lib.array.clean.main.df_clean_r()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_assert_clean_and_filter()`
def df_filter(a1: Any, a2: Any) -> list[Any] | dict[Any, Any]:
	return df_filter_f(a1, a2, _filter_all)
# 2023-07-26 Apply filter strategy `fA` to iterable/dict and predicate in arbitrary order, re-indexing non-assoc lists.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/clean/filter.php#L28-L69
# @used-by :func:`df_filter()`
# @used-by :func:`df_filter_head()`
# @used-by :func:`df_filter_tail()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_assert_clean_and_filter()`
def df_filter_f(a1: Any, a2: Any, fA: Callable[[Any, Callable[[Any], Any]], Any]) -> list[Any] | dict[Any, Any]:
	a, f_i = dfaf(a1, a2)
	arr = df_ita(a)
	r = fA(arr, f_i)
	return r if df_is_assoc(arr) else (list(r.values()) if isinstance(r, dict) else list(r))
# 2023-07-26 "Implement `df_filter_head()`": https://github.com/mage2pro/core/issues/264
# Drop leading elements matching predicate until the first non-matching element.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/clean/filter.php#L71-L94
# @used-by :func:`Df.Qa.lib.bt.filter.df_bt_filter_head()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_assert_clean_and_filter()`
def df_filter_head(a1: Any, a2: Any) -> list[Any] | dict[Any, Any]:
	return df_filter_f(a1, a2, _filter_head_impl)
# 2023-07-26 "Implement `df_filter_tail()`": https://github.com/mage2pro/core/issues/263
# Keep leading elements until the first element matching predicate is encountered.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/clean/filter.php#L96-L119
# @used-by :meth:`Df.Qa.Trace.Trace.__init__()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_assert_clean_and_filter()`
def df_filter_tail(a1: Any, a2: Any) -> list[Any] | dict[Any, Any]:
	return df_filter_f(a1, a2, _filter_tail_impl)
