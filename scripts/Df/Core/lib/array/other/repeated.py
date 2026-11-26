# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2016-07-31 Return unique values that appear more than once in `a`, preserving order of first repeat.
# 2020-01-29 dfa_repeated([1, 2, 2, 2, 2, 3, 3, 3, 4]) => [2, 3].
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/repeated.php#L2-L15
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def dfa_repeated(a: list[Any] | dict[Any, Any]) -> list[Any]:
	vals = list(a.values()) if isinstance(a, dict) else a
	seen: list[Any] = []
	r: list[Any] = []
	for v in vals:
		if v not in seen:
			seen.append(v)
		elif v not in r:
			r.append(v)
	return r
