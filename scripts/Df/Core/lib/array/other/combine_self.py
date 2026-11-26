# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.unpack import df_args
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2016-11-25 Build a dict mapping each value in `*a` to itself.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/combine_self.php#L2-L14
# @used-by :func:`Df.Core.lib.option.df_a_to_options()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def dfa_combine_self(*a: Any) -> dict[Any, Any]:
	items = df_args(list(a))
	return {x: x for x in items}
