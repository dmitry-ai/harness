# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.first import df_first
from Df.Core.lib.array.select import dfa
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2019-01-28 Return the first non-None value in `a` among candidate keys `*k`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/select/try.php#L2-L11
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def dfa_try(a: dict[Any, Any], *k: str) -> Any:
	return df_first(dfa(a, list(k)))
