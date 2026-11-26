# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# Wrap a non-list/dict value in a single-element list; leave lists and dicts as-is.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/array.php#L2-L13
# @used-by :func:`Df.Core.lib.array.find.df_find()`
# @used-by :func:`Df.Core.lib.array.map.df_map()`
# @used-by :func:`Df.Core.lib.lang.call.a.df_call_a()`
# @used-by :func:`Df.Core.lib.text.explode.df_explode_xpath()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def df_array(v: Any) -> list[Any] | dict[Any, Any]:
	return v if isinstance(v, (list, dict)) else [v]
