# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.unpack import df_args
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2016-09-02 Return a copy of dict `a` excluding all keys listed in `*k`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/unset.php#L2-L21
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def dfa_unset(a: dict[Any, Any], *k: Any) -> dict[Any, Any]:
	drop = set(df_args(list(k)))
	return {ak: av for ak, av in a.items() if ak not in drop}
