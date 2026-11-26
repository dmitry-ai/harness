# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# Merge two associative dicts where truthy entries from `a2` override `a1`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/merge.php#L4-L11
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def df_merge_not_empty(a1: dict[Any, Any], a2: dict[Any, Any]) -> dict[Any, Any]:
	r = dict(a1)
	for k, v in a2.items():
		if v:
			r[k] = v
	return r
# 2017-10-28 Merge dict `b` into `r` preserving numeric-string and integer keys without renumbering.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/merge.php#L13-L28
# @used-by :func:`Df.Core.lib.array.select.ordered.dfa_select_ordered()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def dfa_merge_numeric(r: dict[Any, Any], b: dict[Any, Any]) -> dict[Any, Any]:
	out = dict(r)
	for k, v in b.items():
		out[k] = v
	return out
# 2015-02-18 Recursively merge associative dicts; `None` values in `new` unset the key, scalar overrides dict.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/merge.php#L30-L90
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def dfa_merge_r(old: dict[Any, Any], new: dict[Any, Any]) -> dict[Any, Any]:
	r = dict(old)
	for k, new_v in new.items():
		if None is new_v:
			r.pop(k, None)
		else:
			old_v = old.get(k)
			r[k] = dfa_merge_r(old_v, new_v) if isinstance(old_v, dict) and isinstance(new_v, dict) else new_v
	return r
