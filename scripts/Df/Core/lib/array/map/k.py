# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.map import df_map
from Df.Core.lib.array.map.const import DF_BEFORE
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2016-08-09 Map callback receiving (key, value); accepts iterable and callback in arbitrary order.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/map/k.php#L2-L29
# @used-by :func:`Df.Core.lib.array.sort.df_ksort_r()`
# @used-by :func:`Df.Qa.lib.dump.kv.df_kv()`
# @used-by :func:`Df.Qa.lib.dump.kv.table.df_kv_table()`
# @used-by :meth:`Df.Core.Html.Tag.Tag.__openTagWithAttributesAsText()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpArrayElements()`
# @used-by :meth:`Df.Qa.Trace.Formatter.Formatter.__format()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def df_map_k(a1: Any, a2: Any) -> list[Any] | dict[Any, Any]:
	return df_map(a1, a2, [], [], DF_BEFORE)
