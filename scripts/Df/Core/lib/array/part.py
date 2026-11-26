# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.empty import df_etn
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2015-03-13 Drop the last element and return the leading slice.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/part.php#L2-L11
# @used-by :func:`Df.Core.lib.reflection.text.other.df_class_replace_last()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def df_head(a: list[Any] | dict[Any, Any]) -> list[Any] | dict[Any, Any]:
	return dict(list(a.items())[:-1]) if isinstance(a, dict) else list(a[:-1])
# 2021-10-05 Slice `a` starting at `offset` with optional `length` (0 returns through the end).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/part.php#L13-L21
# @used-by :func:`Df.Qa.lib.bt.main.df_bt()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def df_slice(a: list[Any] | dict[Any, Any], offset: int, length: int=0) -> list[Any] | dict[Any, Any]:
	lim = df_etn(length)
	end = None if None is lim else (offset + lim if 0 <= offset else (None if 0 <= offset + lim else offset + lim))
	return dict(list(a.items())[offset:end]) if isinstance(a, dict) else list(a[offset:end])
# Drop the first element and return the tail slice (Lisp CDR).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/part.php#L23-L35
# @used-by :func:`Df.Core.lib.text.format.df_sprintf_strict()`
# @used-by :func:`Df.Qa.lib.validation.error._parse_error_args()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.__execMatch()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def df_tail(a: list[Any] | dict[Any, Any]) -> list[Any] | dict[Any, Any]:
	return dict(list(a.items())[1:]) if isinstance(a, dict) else list(a[1:])
