# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.lang.call.if_ import df_call_if
from Df.Core.lib.object.new import df_new
_SC_CACHE: dict[str, Any] = {}
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2024-06-03 Instantiate `resultClass` with optional expected base class and params dict.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/object/objects.php#L4-L27
# @used-by :func:`df_sc()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cross_module_helpers()`
def df_ic(resultClass: str | type, a2: Any=None, a3: dict[str, Any] | None=None) -> Any:
	from Df.Qa.lib.validation.assert_.class_ import df_ar
	expected_class, params = (None, a2) if isinstance(a2, dict) else (a2, {} if None is a3 else a3)
	inst = df_new(resultClass, params) if params else df_new(resultClass)
	return df_ar(inst, expected_class or '')
# 2015-03-23 Singleton-cached variant of df_ic() keyed by class name and optional suffix.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/object/objects.php#L29-L47
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cross_module_helpers()`
def df_sc(resultClass: str | type, expectedClass: str | type='', params: dict[str, Any] | None=None, cacheKeySuffix: str='') -> Any:
	cls_key = resultClass if isinstance(resultClass, str) else f'{resultClass.__module__}.{resultClass.__qualname__}'
	key = cls_key + cacheKeySuffix
	if key not in _SC_CACHE:
		_SC_CACHE[key] = df_ic(resultClass, expectedClass, {} if None is params else params)
	return _SC_CACHE[key]
# 2016-08-23 Return public non-None attribute `k` of object `o`, or evaluate fallback `d`.
# 2017-10-08 Non-public attributes (leading underscore) are ignored, matching PHP isset($o->{$k}).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/object/objects.php#L49-L74
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_json_and_object_helpers()`
def dfo(o: Any, k: str, d: Any=None) -> Any:
	val = getattr(o, str(k), None) if not str(k).startswith('_') else None
	return val if None is not val else df_call_if(d, k)
