# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.first import df_first, df_last
from Df.Core.lib.reflection.text.explode import df_explode_class
from Df.Core.lib.text.transform import df_lcfirst
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2016-01-01 Return the first namespace segment of class `c`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/part.php#L2-L9
# @used-by :func:`Df.Core.lib.reflection.text.check.df_class_my()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_class_f(c: Any) -> str:
	return str(df_first(df_explode_class(c)) or '')
# 2015-12-29 Return the final class name segment of `c`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/part.php#L11-L27
# @used-by :func:`df_class_llc()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_class_l(c: Any) -> str:
	return str(df_last(df_explode_class(c)) or '')
# 2018-01-30 Return the lowercased final class name segment of `c`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/part.php#L29-L35
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_class_llc(c: Any) -> str:
	return df_class_l(c).lower()
# 2016-02-09 Return the second namespace segment of class `c`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/part.php#L37-L45
# @used-by :func:`df_class_second_lc()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_class_second(c: Any) -> str:
	return df_explode_class(c)[1]
# 2016-02-09 Return the second namespace segment of class `c` with lowercased first character.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/part.php#L47-L57
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_class_second_lc(c: Any) -> str:
	return str(df_lcfirst(df_class_second(c)))
# 2016-11-25 Return the suffix of class `c` after its first two namespace segments.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/part.php#L59-L76
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_class_suffix(c: Any) -> str:
	from Df.Core.lib.reflection.text.other import df_cld
	return df_cld(c).join(df_explode_class(c)[2:])
