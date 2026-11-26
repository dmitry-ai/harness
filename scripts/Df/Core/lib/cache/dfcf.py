# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
import inspect
from Df.Core.lib.cache.o import df_ram
from Df.Core.lib.hash import df_hash_a
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# @used-by :func:`dfcf()`
def _caller_key(offset: int) -> str:
	frame = inspect.currentframe()
	for _ in range(2 + offset):
		frame = frame.f_back if None is not frame else None
	fn = frame.f_code.co_name if None is not frame else '<unknown>'
	mod = frame.f_globals.get('__name__', '') if None is not frame else ''
	cls_obj = frame.f_locals.get('cls') if None is not frame else None
	prefix = cls_obj.__qualname__ if isinstance(cls_obj, type) else mod
	return f'{prefix}::{fn}' if prefix else fn
# 2016-09-04 Function and static-method memoization backed by the process-wide RAM cache.
# 2017-01-01 Pass unique=False when a function has multiple dfcf() calls or receives a dynamic callable.
# 2017-08-11 Supports cache invalidation tags via RAM.clean(tag).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/cache/dfcf.php#L3-L175
# @used-by :func:`Df.Core.lib.array.select.cahed.function.dfac()`
# @used-by :func:`Df.Core.lib.cli.df_cli_user()`
# @used-by :func:`Df.Core.lib.state.df_is_windows()`
# @used-by :func:`Df.Qa.lib.diagnostics.df_webserver()`
# @used-by :func:`Df.Qa.lib.validation.assert_.class_.df_ar()`
# @used-by :meth:`Df.Core.R.ConT.ConT.generic()`
# @used-by :meth:`Df.Qa.Trace.Formatter.Formatter.p()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
def dfcf(f: Callable[..., Any], a: list[Any] | tuple[Any, ...] | None=None, tags: list[str] | None=None, unique: bool=True, offset: int=0) -> Any:
	args = list(a) if None is not a else []
	k = _caller_key(offset) + ('' if not args else f'--{df_hash_a(args)}') + ('' if unique else f'--{id(f):x}')
	ram = df_ram()
	return ram.get(k) if ram.exists(k) else ram.set(k, f(*args), list(tags or ()))
