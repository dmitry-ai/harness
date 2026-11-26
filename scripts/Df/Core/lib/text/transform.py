# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.lang.call.a import df_call_a
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2016-01-14 Unicode-safe lowercase first character of string(s).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/transform.php#L2-L15
# @used-by :func:`Df.Core.lib.reflection.text.explode.df_explode_class_lc()`
# @used-by :func:`Df.Core.lib.reflection.text.explode.df_explode_class_lc_camel()`
# @used-by :func:`Df.Core.lib.reflection.text.part.df_class_second_lc()`
# @used-by :func:`Df.Core.lib.text.camel.df_camel_to_underscore()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_lcfirst(*a: Any) -> str | list[str]:
	return df_call_a(lambda s: s[:1].lower() + s[1:], list(a))
# 2016-05-22 Unicode-safe lowercase conversion for string(s).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/transform.php#L17-L24
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_strtolower(*a: Any) -> str | list[str]:
	return df_call_a(list(a), lambda s: s.lower())
# 2016-05-19 Unicode-safe uppercase conversion for string(s).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/transform.php#L26-L34
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_strtoupper(*a: Any) -> str | list[str]:
	return df_call_a(list(a), lambda s: s.upper())
# Unicode-safe uppercase first character of string(s).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/transform.php#L36-L51
# @used-by :func:`Df.Core.lib.reflection.text.cc.df_cc_class_uc()`
# @used-by :func:`Df.Core.lib.text.camel.df_underscore_to_camel()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_ucfirst(*a: Any) -> str | list[str]:
	return df_call_a(lambda s: s[:1].upper() + s[1:], list(a))
# Unicode-safe title-casing of words in string(s).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/transform.php#L53-L65
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_ucwords(*a: Any) -> str | list[str]:
	return df_call_a(lambda s: s.title(), list(a))
