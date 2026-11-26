# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.other.flatten import dfa_flatten
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2022-11-26 Unwrap a single-element list [v] to v without flattening multi-element lists.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/unpack.php#L2-L20
# @used-by :func:`Df.Core.lib.text.contains.df_contains()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def df_arg(a: list[Any]) -> Any:
	return a[0] if 1 == len(a) and None is not a[0] else a
# 2015-12-25 Normalize variadic arguments: if the first element is already a list, unwrap it.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/unpack.php#L22-L38
# @used-by :func:`Df.Core.lib.array.clean.main.df_clean()`
# @used-by :func:`Df.Core.lib.array.clean.main.df_clean_keys()`
# @used-by :func:`Df.Core.lib.array.other.combine_self.dfa_combine_self()`
# @used-by :func:`Df.Core.lib.array.other.unset.dfa_unset()`
# @used-by :func:`Df.Core.lib.text.csv.df_csv()`
# @used-by :func:`Df.Core.lib.text.csv.df_csv_pretty_quote()`
# @used-by :func:`Df.Core.lib.text.format.df_format()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def df_args(a: list[Any]) -> list[Any]:
	return a[0] if a and isinstance(a[0], list) else a
# 2020-01-29 Return None for empty list, a[0] for single element, or recursively flattened list otherwise.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/unpack.php#L40-L53
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def dfa_unpack(a: list[Any]) -> Any:
	c = len(a)
	return None if 0 == c else (a[0] if 1 == c else dfa_flatten(a))
