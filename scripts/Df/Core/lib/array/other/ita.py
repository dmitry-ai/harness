# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Iterable
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2015-02-11 Materialize any iterable to a list while leaving lists and dicts unchanged.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/ita.php#L2-L23
# @used-by :func:`Df.Core.lib.array.clean.filter.df_filter_f()`
# @used-by :func:`Df.Core.lib.array.first.df_first()`
# @used-by :func:`Df.Core.lib.array.first.df_last()`
# @used-by :func:`Df.Core.lib.array.key.transform.dfak_transform()`
# @used-by :func:`Df.Core.lib.array.map.df_map()`
# @used-by :func:`Df.Core.lib.array.other.index.df_index()`
# @used-by :func:`Df.Core.lib.array.select.ordered.dfa_select_ordered()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpObject()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def df_ita(i: Iterable[Any]) -> list[Any] | dict[Any, Any]:
	return i if isinstance(i, (list, dict)) else list(i)
