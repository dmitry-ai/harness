# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import inspect
import weakref
# 2019-09-08 Sentinel distinguishing an omitted property setter value from an explicit None.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/prop/custom.php#L2-L35
DF_N = 'df-null'
_FALLBACK_PROPS: dict[int, dict[str, Any]] = {}
_STATIC_PROPS: dict[str, Any] = {}
_WEAK_PROPS: weakref.WeakKeyDictionary[Any, dict[str, Any]] = weakref.WeakKeyDictionary()
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# @used-by :func:`df_prop()`
def _caller_prop_key(is_static: bool) -> str:
	stack = inspect.stack()
	frame = stack[2].frame if 2 < len(stack) else None
	if None is frame:
		r = '<unknown>'
	elif not is_static:
		r = frame.f_code.co_name
	else:
		cls_obj = frame.f_locals.get('cls')
		prefix = cls_obj.__qualname__ if isinstance(cls_obj, type) else str(frame.f_globals.get('__name__', ''))
		r = f'{prefix}::{frame.f_code.co_name}' if prefix else frame.f_code.co_name
	return r
# @used-by :func:`df_prop_k()`
def _obj_prop_bag(o: Any) -> dict[str, Any]:
	try:
		if o not in _WEAK_PROPS:
			_WEAK_PROPS[o] = {}
		r = _WEAK_PROPS[o]
	except TypeError:
		r = _FALLBACK_PROPS.setdefault(id(o), {})
	return r
# Convert sentinel DF_N back to None.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/prop/custom.php#L37-L42
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def df_n_get(v: Any) -> Any:
	return None if DF_N == v else v
# Convert None to sentinel DF_N.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/prop/custom.php#L44-L49
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def df_n_set(v: Any) -> Any:
	return DF_N if None is v else v
# 2019-04-05 Combined getter/setter property helper; pass o=None for static class/module properties.
# 2019-09-08 Supports static properties.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/prop/custom.php#L51-L129
# @used-by :meth:`Df.Core.Exception.Exception.context()`
# @used-by :meth:`Df.Core.Json.Json.bSort()`
# @used-by :meth:`Df.Zf.Validate.Validate._v()`
def df_prop(o: Any, v: Any=DF_N, d: Any=None, type_: str='') -> Any:
	is_get = DF_N == v
	eff_type, eff_d = (d, None) if 'int' == d else (type_, d)
	if None is not o:
		r = df_prop_k(o, _caller_prop_key(False), v, eff_d)
	else:
		k = _caller_prop_key(True)
		if is_get:
			r = _STATIC_PROPS.get(k, eff_d)
		else:
			_STATIC_PROPS[k] = v
			r = None
	return int(r or 0) if is_get and 'int' == eff_type else r
# 2022-10-28 Store or retrieve a keyed dynamic property on object `o` via WeakKeyDictionary.
# 2024-05-20 "Remove the special `ArrayAccess` case's handling from `df_prop_k()`": https://github.com/mage2pro/core/issues/377
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/prop/custom.php#L131-L232
# @used-by :func:`df_prop()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def df_prop_k(o: Any, k: str, v: Any=DF_N, d: Any=None) -> Any:
	bag = _obj_prop_bag(o)
	if DF_N == v:
		r = bag.get(k, d)
	else:
		bag[k] = v
		r = o
	return r
