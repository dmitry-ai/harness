# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.caller.entry import df_caller_entry
from Df.Core.lib.html import df_tag
from Df.Core.lib.reflection.text.cc import df_cc_method
from Df.Core.lib.reflection.text.explode import df_explode_method
from Df.Core.lib.array.first import df_first
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2017-11-19 Return the class name of the calling method.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/caller/other.php#L4-L9
# @used-by :func:`Df.Qa.lib.validation.error.df_abstract()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_caller_c(o: int=0) -> str:
	return str(df_first(df_explode_method(df_caller_m(o + 1))) or '')
# 2016-08-10 Return the function/method name of the caller at offset `o`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/caller/other.php#L11-L55
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_caller_f(o: int=0) -> str:
	return str(df_caller_entry(o + 1).get('function', ''))
# 2016-08-10 Return `Class::method` for the calling class method at offset `o`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/caller/other.php#L57-L79
# @used-by :func:`df_caller_c()`
# @used-by :func:`df_caller_ml()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_caller_m(o: int=0) -> str:
	from Df.Qa.lib.bt.entry import df_bt_entry_is_method
	from Df.Qa.lib.validation.assert_ import df_assert
	return df_cc_method(df_assert(df_caller_entry(o + 1, df_bt_entry_is_method)))
# 2024-03-03 Return `Class::method` or bare function name of the caller at offset `o`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/caller/other.php#L81-L85
# @used-by :func:`Df.Core.lib.lang.other.df_no_rec()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_caller_mf(o: int=0) -> str:
	from Df.Qa.lib.validation.assert_ import df_assert
	return df_cc_method(df_assert(df_caller_entry(o + 1)))
# 2016-08-29 Return HTML bold caller method label `<b>Class::method()</b>`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/caller/other.php#L87-L92
# @used-by :func:`Df.Qa.lib.validation.error.df_abstract()`
# @used-by :func:`Df.Qa.lib.validation.error.df_should_not_be_here()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_caller_mh() -> str:
	return df_tag('b', {}, df_caller_ml(1))
# 2016-08-31 Return caller method label with trailing parentheses `Class::method()`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/caller/other.php#L94-L99
# @used-by :func:`Df.Qa.lib.validation.error.df_abstract()`
# @used-by :func:`df_caller_mh()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_caller_ml(o: int=0) -> str:
	return f'{df_caller_m(o + 1)}()'
