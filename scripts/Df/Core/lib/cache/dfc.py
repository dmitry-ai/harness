# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
import inspect
import weakref
from Df.Core.lib.hash import df_hash_a
_FALLBACK_MAP: dict[int, dict[str, Any]] = {}
_WEAK_MAP: weakref.WeakKeyDictionary[Any, dict[str, Any]] = weakref.WeakKeyDictionary()
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# @used-by :func:`dfc()`
def _caller_method_key(offset: int) -> str:
	frame = inspect.currentframe()
	for _ in range(2 + offset):
		frame = frame.f_back if None is not frame else None
	cls = None
	if None is not frame:
		self_obj = frame.f_locals.get('self')
		cls = type(self_obj).__qualname__ if None is not self_obj else None
	if None is frame or None is cls:
		from Df.Qa.lib.validation.error import df_error
		df_error('[dfc] Invalid backtrace frame: caller is not a class method.')
	return f'{cls}::{frame.f_code.co_name}'
# @used-by :func:`dfc()`
def _object_store(o: Any) -> dict[str, Any]:
	try:
		if o not in _WEAK_MAP:
			_WEAK_MAP[o] = {}
		r = _WEAK_MAP[o]
	except TypeError:
		r = _FALLBACK_MAP.setdefault(id(o), {})
	return r
# 2016-08-31 Per-object method result cache bound to the object's lifetime via WeakKeyDictionary.
# 2017-01-01 Pass unique=False when a method has multiple dfc() calls or receives a dynamic callable.
# 2017-01-02 Pass offset > 0 when dfc() is called indirectly through a wrapper such as dfaoc().
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/cache/dfc.php#L3-L95
# @used-by :func:`Df.Core.lib.array.select.cahed.method.dfaoc()`
# @used-by :meth:`Df.Core.Html.Tag.Tag.__contentStr()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.__getSubjectReportPart()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.__getSubjectSplitted()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.__isSubjectMultiline()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.__isSubjectTooLongToReport()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.match()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.test()`
# @used-by :meth:`Df.Qa.Failure.Failure.report()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.file()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.methodParameter()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.methodR()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
def dfc(o: Any, f: Callable[..., Any], a: list[Any] | tuple[Any, ...] | None=None, unique: bool=True, offset: int=0) -> Any:
	args = list(a) if None is not a else []
	k = _caller_method_key(offset) + ('' if not args else df_hash_a(args)) + ('' if unique else f'{id(f):x}')
	store = _object_store(o)
	if k not in store:
		store[k] = f(*args)
	return store[k]
