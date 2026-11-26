# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.map.const import DF_AFTER, DF_BEFORE
from Df.Core.lib.array.other.af import dfaf
from Df.Core.lib.array.other.array import df_array
from Df.Core.lib.array.other.ita import df_ita
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# @used-by :func:`df_map()`
def _map_entry(k: Any, v: Any, f: Any, prep: list[Any], app: list[Any], key_pos: int) -> Any:
	prim = [k, v] if DF_BEFORE == key_pos else ([v, k] if DF_AFTER == key_pos else [v])
	return f(*prep, *prim, *app)
# 2015-02-11 Map callback over any iterable/dict with arbitrary arg order, extra prepend/append args, key position, and custom result keys.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/map/.php#L4-L104
# @used-by :func:`Df.Core.lib.array.clean.main.df_clean_r()`
# @used-by :func:`Df.Core.lib.array.other.chop.dfa_chop()`
# @used-by :func:`Df.Core.lib.lang.call.a.df_call_a()`
# @used-by :func:`Df.Core.lib.text.prepend_append.tab.df_tab()`
# @used-by :func:`Df.Core.lib.text.trim.df_trim()`
# @used-by :func:`Df.Core.lib.text.trim.df_trim_text_left()`
# @used-by :func:`Df.Core.lib.text.trim.df_trim_text_right()`
# @used-by :func:`Df.Qa.lib.validation.assert_.float.df_float()`
# @used-by :func:`Df.Qa.lib.validation.assert_.int.df_int()`
# @used-by :func:`each.df_each()`
# @used-by :func:`k.df_map_k()`
# @used-by :func:`kr.df_map_kr()`
# @used-by :func:`r.df_map_r()`
# @used-by :meth:`Df.Qa.Trace.Trace.__init__()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_key_map_and_merge()`
def df_map(a1: Any, a2: Any, pAppend: Any=None, pPrepend: Any=None, keyPosition: int=0, returnKey: bool=False) -> list[Any] | dict[Any, Any]:
	a, f = dfaf(a1, a2)
	arr = df_ita(a)
	app = [] if None is pAppend else df_array(pAppend)
	prep = [] if None is pPrepend else df_array(pPrepend)
	pairs = list(arr.items()) if isinstance(arr, dict) else list(enumerate(arr))
	if returnKey:
		r: list[Any] | dict[Any, Any] = {}
		for k, v in pairs:
			fr = _map_entry(k, v, f, prep, app, keyPosition)
			r[fr[0]] = fr[1]
	elif isinstance(arr, dict):
		r = {k: _map_entry(k, v, f, prep, app, keyPosition) for k, v in pairs}
	else:
		r = [_map_entry(k, v, f, prep, app, keyPosition) for k, v in pairs]
	return r
