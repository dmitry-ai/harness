# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2023-08-01 "Implement `df_call_parent()`": https://github.com/mage2pro/core/issues/298
# Invoke method `m` defined on the direct parent class of `o` with arguments `a`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/call/parent.php#L4-L42
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def df_call_parent(o: Any, m: str, a: list[Any] | tuple[Any, ...] | None=None) -> Any:
	cls = type(o)
	bases = [b for b in cls.__mro__[1:] if object is not b]
	if not bases:
		from Df.Qa.lib.validation.error import df_error
		df_error(f'`{cls.__qualname__}` does not have a parent.')
	parent = bases[0]
	fn = getattr(parent, m, None)
	if not callable(fn):
		from Df.Qa.lib.validation.error import df_error
		df_error(f'The `{parent.__qualname__}` class does not have the `{m}` method.')
	return fn(o, *(a or ()))
