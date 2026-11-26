# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import uuid
from Df.Core.Helper.Text import Text
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-12-31 Non-breaking space constant (preserved exact codepoint from mage2pro/core).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/main.php#L3-L11
DF_THIN_SPACE = '\u00a0'
# Split a Unicode string into a list of individual characters.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/main.php#L13-L18
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_string_split(s: str) -> list[str]:
	return list(s)
# Case-insensitive Unicode string equality check.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/main.php#L20-L21
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_strings_are_equal_ci(s1: str, s2: str) -> bool:
	return s1.lower() == s2.lower()
# Return the Text helper singleton.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/main.php#L23-L28
# @used-by :func:`Df.Core.lib.text.quote.df_quote_double()`
# @used-by :func:`Df.Core.lib.text.quote.df_quote_russian()`
# @used-by :func:`Df.Core.lib.text.quote.df_quote_single()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_t() -> Text:
	return Text.s()
# 2016-07-05 Generate an alphanumeric unique identifier with optional prefix and suffix length.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/main.php#L30-L67
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_uid(length: int=0, prefix: str='') -> str:
	raw = uuid.uuid4().hex
	return prefix + (raw if 0 == length else raw[-length:])
