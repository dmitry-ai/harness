# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Iterable
from Df.Core.lib.array.other.ita import df_ita
from Df.Core.lib.array.select.column import df_column
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2015-12-30 Index an iterable of dicts or objects into a map keyed by field/method/callable `k`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/index.php#L3-L15
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def df_index(k: Any, a: Iterable[Any]) -> dict[Any, Any]:
	arr = df_ita(a)
	vals = list(arr.values()) if isinstance(arr, dict) else arr
	keys_col = df_column(arr, k)
	keys = list(keys_col.values()) if isinstance(keys_col, dict) else keys_col
	return dict(zip(keys, vals))
