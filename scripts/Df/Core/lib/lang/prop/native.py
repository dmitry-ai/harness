# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# ReflectionProperty-compatible accessor returned by dfr_prop().
class _PropertyHandle:
	# @used-by :func:`dfr_prop()`
	def __init__(self, name: str) -> None:
		self.__name = name
	# @used-by :func:`dfr_prop_get()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
	def getValue(self, o: Any) -> Any:
		return getattr(o, self.__name)
	# @used-by :func:`dfr_prop_set()`
	def setValue(self, o: Any, v: Any) -> None:
		setattr(o, self.__name, v)
# 2023-08-01 Resolve a named attribute (including private/mangled attributes) on `o`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/prop/native.php#L4-L26
# @used-by :func:`dfr_prop_get()`
# @used-by :func:`dfr_prop_set()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def dfr_prop(o: Any, n: str) -> _PropertyHandle:
	if not hasattr(o, n):
		from Df.Qa.lib.validation.error import df_error
		df_error(f'The `{type(o).__qualname__}` class does not have the `{n}` property.')
	return _PropertyHandle(n)
# 2023-08-01 "Implement `dfr_prop_get()`": https://github.com/mage2pro/core/issues/299
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/prop/native.php#L28-L41
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def dfr_prop_get(o: Any, n: str) -> Any:
	return dfr_prop(o, n).getValue(o)
# 2023-08-01 "Implement `dfr_prop_set()`": https://github.com/mage2pro/core/issues/300
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/prop/native.php#L43-L54
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def dfr_prop_set(o: Any, n: str, v: Any) -> None:
	dfr_prop(o, n).setValue(o, v)
