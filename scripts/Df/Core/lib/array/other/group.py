# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.first import df_first
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# @used-by :func:`dfa_group()`
def _group_by_key(a: list[Any] | dict[Any, Any], k: Any) -> dict[Any, list[Any]]:
	r: dict[Any, list[Any]] = {}
	vals = a.values() if isinstance(a, dict) else a
	for item in vals:
		index = item[k]
		if isinstance(item, dict):
			rest: Any = {rk: rv for rk, rv in item.items() if rk != k}
			entry = df_first(rest) if 1 == len(rest) else rest
		else:
			rest_l = [rv for idx, rv in enumerate(item) if idx != k]
			entry = rest_l[0] if 1 == len(rest_l) else rest_l
		r.setdefault(index, []).append(entry)
	return r
# 2018-04-24 Group rows by key/index `k`, or invert mapping keys by values when `k` is None.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/group.php#L2-L32
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def dfa_group(a: dict[Any, Any] | list[Any], k: Any=None) -> dict[Any, list[Any]]:
	if None is not k:
		r = _group_by_key(a, k)
	else:
		r = {}
		pairs = a.items() if isinstance(a, dict) else enumerate(a)
		for key, index in pairs:
			r.setdefault(index, []).append(key)
	return r
