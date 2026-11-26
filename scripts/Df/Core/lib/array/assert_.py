# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.select import dfa
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2023-07-26 "Implement `dfa_assert_keys()`": https://github.com/mage2pro/core/issues/258
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/assert.php#L2-L14
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_assert_clean_and_filter()`
def dfa_assert_keys(a: dict[Any, Any], kk: list[Any]) -> None:
	for k in kk:
		if k not in a or None is a[k]:
			from Df.Qa.lib.dump import df_dump
			from Df.Qa.lib.validation.error import df_error
			df_error(f'The required key «{k}» is absent.\nThe array:\n{df_dump(a)}')
# 2023-07-26 "Implement `dfa_has_keys()`": https://github.com/mage2pro/core/issues/258
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/assert.php#L16-L19
# @used-by :func:`Df.Qa.lib.bt.entry.df_bt_entry_is_method()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_assert_clean_and_filter()`
def dfa_has_keys(a: dict[Any, Any], kk: list[Any]) -> bool:
	return len(kk) == len(dfa(a, kk))
