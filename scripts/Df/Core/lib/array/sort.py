# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from functools import cmp_to_key
from typing import Any, Callable
import locale
from Df.Core.lib.array.is_ import array_is_list, df_is_assoc
from Df.Core.lib.array.map.k import df_map_k
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# @used-by :func:`df_sort()`
def _sort_key(f: Any, is_get: bool, posix: bool) -> Callable[[Any], Any]:
	if None is f:
		r: Callable[[Any], Any] = (lambda v: v if posix or (not isinstance(v, str)) else locale.strxfrm(v))
	elif is_get:
		r = (lambda v: f(v) if posix or (not isinstance(f(v), str)) else locale.strxfrm(f(v)))
	elif callable(f):
		r = cmp_to_key(f)
	else:
		r = (lambda v: getattr(v, str(f))() if not isinstance(v, (int, float, str)) else v)
	return r
# 2016-01-29 Sort associative dict by key (optionally with comparator `f`), leaving lists unchanged.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/sort.php#L2-L25
# @used-by :func:`df_ksort_r()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpArrayElements()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def df_ksort(a: dict[Any, Any] | list[Any], f: Callable[[Any, Any], int] | None=None) -> dict[Any, Any] | list[Any]:
	if not df_is_assoc(a) or (not isinstance(a, dict)):
		r: dict[Any, Any] | list[Any] = a
	else:
		keys = sorted(a.keys(), key=cmp_to_key(f)) if None is not f else sorted(a.keys())
		r = {k: a[k] for k in keys}
	return r
# 2017-08-22 Case-insensitive key sort on a dict.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/sort.php#L27-L39
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def df_ksort_ci(a: dict[Any, Any]) -> dict[Any, Any]:
	return {k: a[k] for k in sorted(a.keys(), key=lambda x: str(x).lower())}
# 2017-07-05 Recursively sort associative dict keys at all nesting levels.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/sort.php#L41-L52
# @used-by :func:`df_ksort_r_ci()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def df_ksort_r(a: dict[Any, Any] | list[Any], f: Callable[[Any, Any], int] | None=None) -> dict[Any, Any] | list[Any]:
	mapped = df_map_k(lambda _k, v: df_ksort_r(v, f) if isinstance(v, (dict, list)) else v, a)
	return df_ksort(mapped, f)
# 2017-08-22 Recursively case-insensitive key sort on associative dicts, preserving list ordering.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/sort.php#L54-L75
# @used-by :func:`Df.Core.lib.json.df_json_sort()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def df_ksort_r_ci(a: dict[Any, Any] | list[Any]) -> dict[Any, Any] | list[Any]:
	# @used-by :func:`df_ksort_r_ci()`
	def _ci_cmp(x: Any, y: Any) -> int:
		lx, ly = (str(x).lower(), str(y).lower())
		return -1 if lx < ly else (1 if lx > ly else 0)
	return a if array_is_list(a) else df_ksort_r(a, _ci_cmp)
# 2016-07-18 Sort a list or dict by values with optional comparator/getter/method name and locale.
# 2024-04-08 Supports locale-aware sorting and getter mode via `isGet=True`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/sort.php#L77-L184
# @used-by :func:`df_sort_posix()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def df_sort(a: list[Any] | dict[Any, Any], f: Any=None, isGet: bool=False, l: str='') -> list[Any] | dict[Any, Any]:
	key_fn = _sort_key(f, isGet, 'en_US_POSIX' == l or '' == l)
	if isinstance(a, dict):
		r: list[Any] | dict[Any, Any] = dict(sorted(a.items(), key=lambda kv: key_fn(kv[1])))
	else:
		r = sorted(a, key=key_fn)
	return r
# 2018-05-21 Sort dict values in ascending order while preserving key association.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/sort.php#L186-L192
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def df_sort_a(a: dict[Any, Any]) -> dict[Any, Any]:
	return dict(sorted(a.items(), key=lambda kv: kv[1]))
# 2025-06-10 "Implement `df_sort_posix()`": https://github.com/mage2pro/core/issues/419
# Sort deterministically using POSIX byte/codepoint order.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/sort.php#L194-L238
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def df_sort_posix(a: list[Any] | dict[Any, Any], f: Any=None, isGet: bool=False) -> list[Any] | dict[Any, Any]:
	return df_sort(a, f, isGet, 'en_US_POSIX')
