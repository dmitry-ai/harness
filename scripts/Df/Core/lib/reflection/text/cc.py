# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.clean.main import df_clean
from Df.Core.lib.array.other.flatten import dfa_flatten
from Df.Core.lib.array.select import dfa
from Df.Core.lib.reflection.text.cts import df_cts
from Df.Core.lib.text.concatenate import df_ccc
from Df.Core.lib.text.transform import df_ucfirst
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2016-02-08 Concatenate namespace segments with `\` after flattening and cleaning empty items.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/cc.php#L2-L15
# @used-by :func:`df_cc_class_uc()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_cc_class(*a: Any) -> str:
	return '\\'.join((str(x) for x in df_clean(dfa_flatten(list(a)))))
# 2016-03-25 Concatenate namespace segments with `\` after capitalizing the first letter of each segment.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/cc.php#L17-L30
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_cc_class_uc(*a: Any) -> str:
	return df_cc_class(df_ucfirst(dfa_flatten(list(a))))
# 2016-08-10 Format `Class::method` from (class, method) or a backtrace frame dict.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/cc.php#L32-L46
# @used-by :func:`Df.Core.lib.caller.other.df_caller_m()`
# @used-by :func:`Df.Core.lib.caller.other.df_caller_mf()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.method()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_cc_method(a1: Any, a2: str | None=None) -> str:
	if a2:
		parts: Any = [df_cts(a1), a2]
	elif isinstance(a1, dict) and 'function' in a1:
		parts = [dfa(a1, 'class'), a1['function']]
	else:
		parts = a1
	return df_ccc('::', parts)
