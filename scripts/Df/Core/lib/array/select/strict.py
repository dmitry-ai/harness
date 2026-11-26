# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.select import dfa
from Df.Core.lib.empty import df_nes
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2022-11-27 Require a non-empty key `k` present in `a`; when missing, raise if `onE is True`, call `onE()` if callable, else return `onE`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/select/strict.php#L4-L35
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def dfa_strict(a: dict[Any, Any] | list[Any], k: Any, onE: Any=True) -> Any:
	if df_nes(k):
		if True is onE:
			from Df.Qa.lib.validation.error import df_error
			df_error('[dfa_strict] The key is required but is not provided.')
		r: Any = None
	else:
		r = dfa(a, k)
		if None is r and True is onE:
			from Df.Qa.lib.validation.error import df_error
			df_error(f'[dfa_strict] The array does not have a value for the key «{k}».')
	return r if None is not r else (onE() if callable(onE) else onE)
