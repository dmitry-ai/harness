# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.is_ import array_is_list
from Df.Core.lib.array.map.kr import df_map_kr
from Df.Core.lib.array.other.af import dfaf
from Df.Core.lib.array.other.ita import df_ita
MB_CASE_LOWER = 1
MB_CASE_TITLE = 2
MB_CASE_UPPER = 0
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# @used-by :func:`dfa_key_case()`
def _convert_case(k: Any, c: int) -> Any:
	s = str(k)
	if MB_CASE_UPPER == c:
		r = s.upper()
	elif MB_CASE_LOWER == c:
		r = s.lower()
	else:
		r = s.title()
	return r
# 2015-02-07 Recursively change UTF-8 dict key casing using MB_CASE_UPPER (0), MB_CASE_LOWER (1), or MB_CASE_TITLE (2).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/key/transform.php#L2-L27
# @used-by :func:`dfa_key_uc()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def dfa_key_case(a: dict[Any, Any] | list[Any], c: int) -> dict[Any, Any] | list[Any]:
	return dfak_transform_r(a, lambda k: _convert_case(k, c))
# 2017-09-03 Convert all keys of dict `a` to integers via df_int().
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/key/transform.php#L29-L37
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def dfa_key_int(a: dict[Any, Any]) -> dict[int, Any]:
	from Df.Qa.lib.validation.assert_.int import df_int
	return dfak_transform(a, df_int)
# 2017-02-01 Recursively uppercase all dict keys.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/key/transform.php#L110-L116
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def dfa_key_uc(a: dict[Any, Any] | list[Any]) -> dict[Any, Any] | list[Any]:
	return dfa_key_case(a, MB_CASE_UPPER)
# 2020-01-29 Prefix all associative keys with `p` (optionally recursively).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/key/transform.php#L39-L50
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def dfak_prefix(a: dict[Any, Any] | list[Any], p: str, req: bool=False) -> dict[Any, Any] | list[Any]:
	return dfak_transform(a, lambda k: f'{p}{k}', req)
# 2017-02-01 Transform associative dict keys via `f`; leaves list indexes unchanged while recursing when `req=True`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/key/transform.php#L52-L87
# @used-by :func:`dfa_key_int()`
# @used-by :func:`dfak_prefix()`
# @used-by :func:`dfak_transform_r()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def dfak_transform(a1: Any, a2: Any, req: bool=False) -> dict[Any, Any] | list[Any]:
	a, f = dfaf(a1, a2)
	arr = df_ita(a)
	if array_is_list(arr):
		r: dict[Any, Any] | list[Any] = [dfak_transform(v, f, req) if req and isinstance(v, (dict, list)) else v for v in arr]
	else:
		r = df_map_kr(arr, lambda k, v: [f(k), dfak_transform(v, f, req) if req and isinstance(v, (dict, list)) else v])
	return r
# 2020-01-30 Recursive variant of dfak_transform().
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/key/transform.php#L89-L108
# @used-by :func:`dfa_key_case()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def dfak_transform_r(a1: Any, a2: Any) -> dict[Any, Any] | list[Any]:
	return dfak_transform(a1, a2, True)
