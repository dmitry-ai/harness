# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# @used-by :func:`df_hash_a()`
def _hash_item(v: Any) -> str:
	if isinstance(v, (dict, list, tuple)):
		r = df_hash_a(v)
	elif isinstance(v, (str, int, float, bool)) or None is v:
		r = '' if None is v else str(v)
	else:
		r = df_hash_o(v)
	return r
# 2016-08-31 Recursively hash a list, tuple, or dict including keys.
# 2016-10-29 Accounts for array/dict keys (unlike array_reduce).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/hash.php#L5-L22
# @used-by :func:`Df.Core.lib.cache.dfc.dfc()`
# @used-by :func:`Df.Core.lib.cache.dfcf.dfcf()`
# @used-by :func:`_hash_item()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cli_state_and_hash()`
def df_hash_a(a: dict[Any, Any] | list[Any] | tuple[Any, ...]) -> str:
	pairs = a.items() if isinstance(a, dict) else enumerate(a)
	return '::'.join((f'{k}=>{_hash_item(v)}' for k, v in pairs))
# 2016-09-04 Hash an object using getId() / id() when available, falling back to object identity.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/hash.php#L24-L45
# @used-by :func:`_hash_item()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cli_state_and_hash()`
def df_hash_o(o: Any) -> str:
	oid = o.getId() if callable(getattr(o, 'getId', None)) else (o.id() if callable(getattr(o, 'id', None)) else None)
	return f'{type(o).__module__}.{type(o).__qualname__}::{oid}' if oid else f'{id(o):x}'
