# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.is_ import array_is_list
from Df.Core.lib.array.select import dfa
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2016-08-26 Insert element(s) into a list or associative dict at position `pos` without mutating the caller's reference.
# 2016-11-24 Handles associative dicts by slicing and merging preserving insertion order.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/insert.php#L3-L24
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def dfa_insert(a: list[Any] | dict[Any, Any], pos: int, add: Any) -> list[Any] | dict[Any, Any]:
	if isinstance(a, dict):
		items = list(a.items())
		add_items = list(add.items()) if isinstance(add, dict) else [(i, v) for i, v in enumerate(add if isinstance(add, list) else [add])]
		r: list[Any] | dict[Any, Any] = dict(items[:pos] + add_items + items[pos:])
	else:
		res = list(a)
		ins = list(add) if array_is_list(add) else [add]
		res[pos:pos] = ins
		r = res
	return r
# 2015-02-07 Move entries with keys listed in `k` to the front of associative dict `a`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/insert.php#L26-L53
# @used-by :func:`dfa_prepend_by_values()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def dfa_prepend_by_keys(a: dict[Any, Any], k: list[Any]) -> dict[Any, Any]:
	r = dict(dfa(a, k))
	for ak, av in a.items():
		if ak not in r:
			r[ak] = av
	return r
# 2015-02-07 Move entries whose values appear in `v` to the front of associative dict `a`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/insert.php#L55-L85
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def dfa_prepend_by_values(a: dict[Any, Any], v: list[Any]) -> dict[Any, Any]:
	flipped = {val: key for key, val in a.items()}
	ordered = dfa_prepend_by_keys(flipped, v)
	return {key: val for val, key in ordered.items()}
