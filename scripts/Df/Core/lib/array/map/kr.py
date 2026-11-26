# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.map import df_map
from Df.Core.lib.array.map.const import DF_BEFORE
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2016-11-08 Map callback receiving (key, value) and returning [new_key, new_value]; arbitrary arg order.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/map/kr.php#L4-L25
# @used-by :func:`Df.Core.lib.array.key.transform.dfak_transform()`
# @used-by :func:`Df.Core.lib.array.select.column.df_column()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def df_map_kr(a1: Any, a2: Any) -> dict[Any, Any]:
	return df_map(a1, a2, [], [], DF_BEFORE, True)
