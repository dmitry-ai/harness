# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.select import dfa
from Df.Core.lib.empty import df_nes
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2016-09-05 Map scalar `v` via `map_`; return `v` unchanged if empty/None or absent from `map_`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/tr.php#L2-L34
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def dftr(v: Any, map_: dict[Any, Any]) -> Any:
	return v if df_nes(v) else dfa(map_, v, v)
