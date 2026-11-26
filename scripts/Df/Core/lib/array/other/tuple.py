# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.select import dfa
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2020-02-12 Transpose a dict/list of sequences into a list of position-aligned dicts/lists padded with None.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/tuple.php#L2-L20
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def df_tuple(arrays: dict[Any, list[Any]] | list[list[Any]]) -> list[Any]:
	vals = list(arrays.values()) if isinstance(arrays, dict) else arrays
	count_items = max((len(x) for x in vals), default=0)
	if isinstance(arrays, dict):
		r: list[Any] = [{k: dfa(arr, i) for k, arr in arrays.items()} for i in range(count_items)]
	else:
		r = [[dfa(arr, i) for arr in arrays] for i in range(count_items)]
	return r
