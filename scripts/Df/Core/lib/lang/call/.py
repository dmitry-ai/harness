# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
import inspect
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# @used-by :func:`_invoke_named()`
def _bind_named_param(rp: inspect.Parameter, p: dict[str, Any], fn_name: str, is_method: bool) -> Any:
	from Df.Core.lib.reflection.param.is_.bool import dfr_param_is_bool
	from Df.Qa.lib.validation.assert_.bool import df_bool
	from Df.Qa.lib.validation.error import df_error
	if rp.name in p and None is not p[rp.name]:
		r = df_bool(p[rp.name]) if dfr_param_is_bool(rp) else p[rp.name]
	elif inspect.Parameter.empty is not rp.default:
		r = rp.default
	else:
		kind = 'method' if is_method else 'function'
		df_error(f'`df_call()`: the required argument `{rp.name}` of the `{fn_name}` {kind} is missed.', {'arguments': p})
		r = None
	return r
# 2024-09-07 "Provide an ability to pass named arguments to `df_call()`": https://github.com/mage2pro/core/issues/433
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/call/.php#L58-L89
# @used-by :func:`df_call()`
def _invoke_named(target: Callable[..., Any], p: dict[str, Any], is_method: bool) -> Any:
	sig = inspect.signature(target)
	fn_name = getattr(target, '__name__', str(target))
	bound = [_bind_named_param(rp, p, fn_name, is_method) for rp in sig.parameters.values()]
	return target(*bound)
# @used-by :func:`df_call()`
def _resolve_method(o: Any, f: Any) -> Callable[..., Any] | None:
	r: Callable[..., Any] | None = None
	if isinstance(f, str) and (not f.startswith('_')):
		cand = getattr(o, f, None)
		if callable(cand):
			r = cand
	return r
# 2015-12-30 Unify callback invocation for dicts, callables, and public object methods.
# 2017-07-09 Accepts a dict as `o`.
# 2024-09-06 "Provide an ability to pass named arguments to `df_call()`": https://github.com/mage2pro/core/issues/433
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/call/.php#L6-L99
# @used-by :func:`Df.Core.lib.array.map.each.df_each()`
# @used-by :func:`Df.Core.lib.array.select.column.df_column()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cross_module_helpers()`
def df_call(o: Any, f: Any, p: list[Any] | dict[str, Any] | None=None) -> Any:
	params: list[Any] | dict[str, Any] = [] if None is p else p
	if isinstance(o, dict):
		from Df.Core.lib.array.select import dfa
		r = dfa(o, f)
	elif callable(f):
		r = f(o, **params) if isinstance(params, dict) else f(o, *params)
	else:
		method = _resolve_method(o, f)
		if None is not method:
			r = _invoke_named(method, params, True) if isinstance(params, dict) else method(*params)
		else:
			from Df.Qa.lib.validation.error import df_error
			df_error(f'Unable to call «{f}».')
			r = None
	return r
