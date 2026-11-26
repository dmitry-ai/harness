# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.other.flatten import dfa_flatten
from Df.Core.lib.text.camel import df_explode_camel
from Df.Core.lib.text.explode import df_explode_multiple
from Df.Core.lib.text.transform import df_lcfirst
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# Split a class name into namespace/module segments by `\`, `.`, and `_`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/explode.php#L2-L13
# @used-by :func:`Df.Core.lib.reflection.text.other.df_class_replace_last()`
# @used-by :func:`Df.Core.lib.reflection.text.part.df_class_f()`
# @used-by :func:`Df.Core.lib.reflection.text.part.df_class_l()`
# @used-by :func:`Df.Core.lib.reflection.text.part.df_class_second()`
# @used-by :func:`Df.Core.lib.reflection.text.part.df_class_suffix()`
# @used-by :func:`df_explode_class_lc()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_explode_class(c: Any) -> list[str]:
	from Df.Core.lib.reflection.text.cts import df_cts
	return df_explode_multiple(['\\', '.', '_'], df_cts(c))
# 2016-04-11 Split class namespace segments and split each segment along CamelCase boundaries.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/explode.php#L15-L23
# @used-by :func:`df_explode_class_lc_camel()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_explode_class_camel(c: Any) -> list[str]:
	from Df.Core.lib.reflection.text.cts import df_cts
	parts = df_explode_multiple(['\\', '.'], df_cts(c))
	return dfa_flatten(df_explode_camel(parts))
# 2016-01-14 Split a class name into segments with lowercased initial letters.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/explode.php#L25-L32
# @used-by :func:`Df.Core.lib.reflection.text.cts.df_cts_lc()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_explode_class_lc(c: Any) -> list[str]:
	return df_lcfirst(df_explode_class(c))
# 2016-04-11 Split class CamelCase segments with lowercased initial letters.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/explode.php#L34-L43
# @used-by :func:`Df.Core.lib.reflection.text.cts.df_cts_lc_camel()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_explode_class_lc_camel(c: Any) -> list[str]:
	return df_lcfirst(df_explode_class_camel(c))
# 2021-02-24 Split `Class::method` on `::`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/explode.php#L45-L50
# @used-by :func:`Df.Core.lib.caller.other.df_caller_c()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_explode_method(m: str) -> list[str]:
	return m.split('::')
