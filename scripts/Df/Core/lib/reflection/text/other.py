# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import inspect
from Df.Core.lib.array.other.flatten import dfa_flatten
from Df.Core.lib.array.part import df_head
from Df.Core.lib.lang.call.if_ import df_call_if
from Df.Core.lib.reflection.text.check import _load_class
from Df.Core.lib.reflection.text.cts import df_cts
from Df.Core.lib.reflection.text.explode import df_explode_class
from Df.Core.lib.text.contains import df_contains
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2017-01-10 Return the normalized forward-slash source file path defining class `c`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/other.php#L4-L13
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_class_file(c: Any) -> str:
	cls = c if isinstance(c, type) else (_load_class(c) if isinstance(c, str) else type(c))
	raw = inspect.getsourcefile(cls) or '' if None is not cls else ''
	return raw.replace('\\', '/')
# 2016-07-10 Replace the last segment of class name `c` with `newSuffix`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/other.php#L15-L25
# @used-by :func:`Df.Core.lib.reflection.text.con_.df_con_sibling()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_class_replace_last(c: Any, *newSuffix: Any) -> str:
	return df_cld(c).join(df_head(df_explode_class(c)) + [str(x) for x in dfa_flatten(list(newSuffix))])
# 2016-10-15 Detect the namespace delimiter (`\`, `.`, or `_`) used in class name `c`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/other.php#L27-L37
# @used-by :func:`Df.Core.lib.reflection.text.con_.df_con_child()`
# @used-by :func:`Df.Core.lib.reflection.text.part.df_class_suffix()`
# @used-by :func:`df_class_replace_last()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_cld(c: Any) -> str:
	s = df_cts(c)
	return '\\' if df_contains(s, '\\') else ('.' if df_contains(s, '.') else '_')
# 2016-08-04 Read a non-callable class constant/attribute `name` from `c`, or evaluate `df_def`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/other.php#L39-L52
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_const(c: Any, name: str, df_def: Any=None) -> Any:
	cls = c if isinstance(c, type) else (_load_class(c) if isinstance(c, str) else type(c))
	if None is not cls and hasattr(cls, name) and (not callable(getattr(cls, name))):
		r = getattr(cls, name)
	else:
		r = df_call_if(df_def)
	return r
