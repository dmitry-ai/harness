# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# Prepend key `k` with value `v` to the front of dict `a` in place.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/unshift_assoc.php#L2-L12
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def dfa_unshift_assoc(a: dict[Any, Any], k: str, v: Any) -> None:
	items = [(k, v)] + [(ak, av) for ak, av in a.items() if ak != k]
	a.clear()
	a.update(items)
