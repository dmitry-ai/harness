# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
from Df.Core.lib.array.select import dfa
from Df.Core.lib.cache.dfc import dfc
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2020-01-29 Cache a dict-returning method on object `o` via dfc() and select key/path `k` with default `d`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/select/cahed/method.php#L4-L22
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def dfaoc(o: Any, f: Callable[[], Any], k: Any='', d: Any=None) -> Any:
	return dfa(dfc(o, f, [], False, 1), k, d)
