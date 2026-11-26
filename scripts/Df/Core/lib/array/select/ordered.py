# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.clean.main import df_clean_null
from Df.Core.lib.array.merge import dfa_merge_numeric
from Df.Core.lib.array.other.ita import df_ita
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2015-02-08 Return a subset of `a` containing only keys in `k` in the exact order of `k`, omitting None/missing entries.
# 2023-07-20 Uses df_clean_null() to drop missing keys: https://github.com/mage2pro/core/issues/238
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/select/ordered.php#L2-L49
# @used-by :func:`Df.Core.lib.array.select.dfa()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def dfa_select_ordered(a: Any, k: list[Any]) -> dict[Any, Any]:
	result_keys = {key: None for key in k}
	arr = df_ita(a)
	src = arr if isinstance(arr, dict) else dict(enumerate(arr))
	merged = dfa_merge_numeric(result_keys, src)
	return df_clean_null({key: merged[key] for key in result_keys})
