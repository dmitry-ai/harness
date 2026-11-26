# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.empty import df_nes
from Df.Core.lib.lang.call.if_ import df_call_if
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# @used-by :func:`dfa()`
def _lookup_direct(a: dict[Any, Any] | list[Any], k: Any) -> tuple[bool, Any]:
	if isinstance(a, dict):
		r = (True, a[k]) if k in a and None is not a[k] else (False, None)
	elif isinstance(k, int) and (not isinstance(k, bool)) and 0 <= k < len(a) and None is not a[k]:
		r = (True, a[k])
	elif isinstance(k, str) and k.isdigit() and int(k) < len(a) and None is not a[int(k)]:
		r = (True, a[int(k)])
	else:
		r = (False, None)
	return r
# Safe array/dict lookup supporting key lists (preserving order), slash paths via dfa_deep(), and lazy defaults.
# 2020-01-29 If `k` is a list, returns a subset of `a` with keys in the order of `k`.
# 2022-11-26 Returns `a` unchanged when `k` is an empty list.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/select/.php#L2-L109
# @used-by :func:`Df.Core.lib.array.assert_.dfa_has_keys()`
# @used-by :func:`Df.Core.lib.array.deep._walk_deep()`
# @used-by :func:`Df.Core.lib.array.insert.dfa_prepend_by_keys()`
# @used-by :func:`Df.Core.lib.array.other.tr.dftr()`
# @used-by :func:`Df.Core.lib.array.other.tuple.df_tuple()`
# @used-by :func:`Df.Core.lib.lang.call.df_call()`
# @used-by :func:`Df.Core.lib.option.df_option_v()`
# @used-by :func:`Df.Core.lib.reflection.text.cc.df_cc_method()`
# @used-by :func:`Df.Core.lib.text.format.df_var()`
# @used-by :func:`Df.Qa.lib.bt.entry.df_bt_entry_class()`
# @used-by :func:`Df.Qa.lib.bt.entry.df_bt_entry_file()`
# @used-by :func:`Df.Qa.lib.bt.entry.df_bt_entry_func()`
# @used-by :func:`Df.Qa.lib.bt.entry.df_bt_entry_line()`
# @used-by :func:`Df.Qa.lib.bt.main.df_bt_has()`
# @used-by :func:`Df.Qa.lib.validation.error._parse_error_args()`
# @used-by :func:`cahed.function.dfac()`
# @used-by :func:`cahed.method.dfaoc()`
# @used-by :func:`strict.dfa_strict()`
# @used-by :func:`try_.dfa_try()`
# @used-by :meth:`Df.Core.Helper.Text.Text.quote()`
# @used-by :meth:`Df.Core.O.O.a()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.__getParam()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_select_sort_and_unpack()`
def dfa(a: dict[Any, Any] | list[Any], k: Any, d: Any=None) -> Any:
	if df_nes(k):
		r: Any = a
	elif isinstance(k, list):
		from Df.Core.lib.array.select.ordered import dfa_select_ordered
		r = a if not k else dfa_select_ordered(a, k)
	else:
		found, val = _lookup_direct(a, k)
		if found:
			r = val
		elif isinstance(k, str) and '/' in k:
			from Df.Core.lib.array.deep import dfa_deep
			r = dfa_deep(a, k, d)
		else:
			r = df_call_if(d, k)
	return r
