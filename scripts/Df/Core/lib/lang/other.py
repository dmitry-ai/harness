# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
_IN_PROCESS: set[str] = set()
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2017-02-07 If `args` is empty return `r`; otherwise return args[0] when `r` is truthy or args[1] when falsy.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/other.php#L2-L18
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def df_b(args: list[Any] | tuple[Any, ...], r: bool) -> Any:
	return r if not args else args[int(not r)]
# 2024-03-03 "Refactor `static $inProcess` to a function": https://github.com/mage2pro/core/issues/354
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/other.php#L20-L36
# @used-by :func:`Df.Core.lib.text.format.df_sprintf_strict()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cross_module_helpers()`
def df_no_rec(f: Callable[[], Any]) -> None:
	from Df.Core.lib.caller.other import df_caller_mf
	k = df_caller_mf()
	if k not in _IN_PROCESS:
		_IN_PROCESS.add(k)
		try:
			f()
		finally:
			_IN_PROCESS.discard(k)
# Return the argument unchanged.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/other.php#L38-L43
# @used-by :meth:`Df.Core.Html.Tag.Tag.__openTagWithAttributesAsText()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def df_nop(v: Any) -> Any:
	return v
