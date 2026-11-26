# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2016-02-09 Invoke `v` with `*a` if `v` is callable; otherwise return `v` directly.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/call/if.php#L2-L17
# @used-by :func:`Df.Core.lib.array.select.dfa()`
# @used-by :func:`Df.Core.lib.lang.if_.df_if()`
# @used-by :func:`Df.Core.lib.lang.if_.df_if1()`
# @used-by :func:`Df.Core.lib.lang.if_.df_if2()`
# @used-by :func:`Df.Core.lib.object.objects.dfo()`
# @used-by :func:`Df.Core.lib.reflection.text.other.df_const()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def df_call_if(v: Any, *a: Any) -> Any:
	return v(*a) if callable(v) else v
