# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.map import df_map
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2016-11-08 Map callback receiving value and returning [new_key, new_value]; arbitrary arg order.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/map/r.php#L2-L31
# @used-by :func:`Df.Core.lib.text.parse.df_parse_colon()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def df_map_r(a1: Any, a2: Any) -> dict[Any, Any]:
	return df_map(a1, a2, [], [], 0, True)
