# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# Fast order-preserving deduplication for hashable scalar (str/int) elements, skipping None.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/unique_fast.php#L2-L25
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def dfa_unique_fast(a: list[Any] | dict[Any, Any]) -> list[Any]:
	vals = a.values() if isinstance(a, dict) else a
	return list(dict.fromkeys((v for v in vals if isinstance(v, (str, int)) and (not isinstance(v, bool)))))
