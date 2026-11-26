# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2024-09-22 Return True iff `v` is a scalar or an object defining a custom __str__ method (not a list/dict).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/type/stringable.php#L2-L21
# @used-by :func:`Df.Qa.lib.validation.assert_.stringable.df_assert_stringable()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpObject()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_json_and_object_helpers()`
def df_is_stringable(v: Any) -> bool:
	if isinstance(v, (list, dict, tuple, set)):
		r = False
	elif isinstance(v, (str, int, float, bool)) or None is v:
		r = True
	else:
		r = object.__str__ is not type(v).__str__
	return r
