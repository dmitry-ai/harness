# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Iterable
from Df.Core.lib.array.map import df_map
from Df.Core.lib.lang.call import df_call
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2015-02-07 Invoke method/callback/key `f` on every element of iterable `c`, preserving dict keys.
# 2017-07-09 Accepts dict elements as well as object instances.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/map/each.php#L2-L27
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def df_each(c: Iterable[Any], f: Any, *p: Any) -> list[Any] | dict[Any, Any]:
	return df_map(c, lambda v: df_call(v, f, list(p)))
