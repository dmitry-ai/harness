# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Iterable
from Df.Core.lib.array.map.kr import df_map_kr
from Df.Core.lib.lang.call import df_call
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2015-02-11 Extract column `fv` from an iterable of dicts or objects, optionally re-keying by `fk` while preserving keys.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/select/column.php#L2-L26
# @used-by :func:`Df.Core.lib.array.other.index.df_index()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def df_column(c: Iterable[Any], fv: Any, fk: Any=None) -> dict[Any, Any]:
	return df_map_kr(c, lambda k, v: [k if not fk else df_call(v, fk), df_call(v, fv)])
