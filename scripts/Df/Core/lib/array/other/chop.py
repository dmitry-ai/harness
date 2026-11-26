# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.array.map import df_map
from Df.Core.lib.empty import df_etn
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2016-09-07 Truncate every string element of `a` to at most `length` characters (0 = unchanged).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/chop.php#L2-L14
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def dfa_chop(a: list[str] | dict[str, str], length: int=0) -> list[str] | dict[str, str]:
	limit = df_etn(length)
	return df_map(lambda s: s[:limit] if None is not limit else s, a)
