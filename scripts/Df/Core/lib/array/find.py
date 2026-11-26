# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Iterable
from Df.Core.lib.array.map.const import DF_AFTER, DF_BEFORE
from Df.Core.lib.array.other.af import dfaf
from Df.Core.lib.array.other.array import df_array
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# @used-by :func:`df_find()`
def _find_direct(a: Any, f: Any, app: list[Any], prep: list[Any], key_pos: int) -> Any:
	pairs = a.items() if isinstance(a, dict) else enumerate(a)
	r: Any = None
	for k, v in pairs:
		prim = [k, v] if DF_BEFORE == key_pos else ([v, k] if DF_AFTER == key_pos else [v])
		fr = f(*prep, *prim, *app)
		if fr:
			r = v if isinstance(fr, bool) else fr
			break
	return r
# 2016-10-25 Find the first matching element (or truthy callback result) in an iterable/dict, with optional nested search.
# 2023-07-25 "Adapt `df_find` to the nested search": https://github.com/mage2pro/core/issues/251
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/find.php#L4-L92
# @used-by :func:`Df.Core.lib.array.is_.dfa_has_objects()`
# @used-by :func:`Df.Core.lib.text.starts_ends.df_ends_with()`
# @used-by :func:`Df.Core.lib.text.starts_ends.df_starts_with()`
# @used-by :func:`Df.Qa.lib.bt.main.df_bt_has()`
# @used-by :func:`Df.Qa.lib.validation.assert_.class_.df_is()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def df_find(a1: Any, a2: Any, pAppend: Any=None, pPrepend: Any=None, keyPosition: int=0, nested: bool=False) -> Any:
	a, f = dfaf(a1, a2)
	app = [] if None is pAppend else df_array(pAppend)
	prep = [] if None is pPrepend else df_array(pPrepend)
	r = _find_direct(a, f, app, prep, keyPosition)
	if None is r and nested:
		vals = a.values() if isinstance(a, dict) else a
		for v in vals:
			if isinstance(v, Iterable) and (not isinstance(v, (str, bytes))):
				cand = df_find(v, f, app, prep, keyPosition, True)
				if cand:
					r = cand
					break
	return r
# 2020-04-25 Recursively search nested dicts for key `k`, returning `d` if absent.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/find.php#L94-L111
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def dfa_r(a: dict[Any, Any], k: str, d: Any=None) -> Any:
	r: Any = None
	if k in a and None is not a[k]:
		r = a[k]
	else:
		for av in a.values():
			if isinstance(av, dict):
				cand = dfa_r(av, k)
				if None is not cand:
					r = cand
					break
	return d if None is r else r
