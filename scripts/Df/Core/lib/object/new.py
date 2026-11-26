# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import importlib
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# @used-by :func:`df_new()`
def _resolve_class(c: str | type) -> type:
	if isinstance(c, type):
		r = c
	else:
		dotted = c.replace('\\', '.').lstrip('.')
		mod_name, _, attr = dotted.rpartition('.')
		mod = importlib.import_module(mod_name)
		r = getattr(mod, attr)
	return r
# 2017-01-12 Instantiate a class (by class object or dotted/backslash name) with unpacked arguments.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/object/new.php#L4-L31
# @used-by :func:`Df.Core.lib.object.objects.df_ic()`
# @used-by :func:`df_newa()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_json_and_object_helpers()`
def df_new(c: str | type, *a: Any) -> Any:
	return _resolve_class(c)(*a)
# 2017-01-12 Instantiate `c` with `*a` and verify the resulting instance against `expected`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/object/new.php#L33-L46
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cross_module_helpers()`
def df_newa(c: str | type, expected: str | type='', *a: Any) -> Any:
	from Df.Qa.lib.validation.assert_.class_ import df_ar
	return df_ar(df_new(c, *a), expected)
