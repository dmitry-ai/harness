# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.text.starts_ends import df_ends_with, df_starts_with
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2016-03-08 Append `tail` to `s` unless `s` already ends with `tail`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/prepend-append/.php#L2-L7
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_append(s: str, tail: str) -> str:
	return s if df_ends_with(s, tail) else s + tail
# 2016-03-08 Prepend `head` to `s` unless `s` already starts with `head`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/prepend-append/.php#L9-L15
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_prepend(s: str, head: str) -> str:
	return s if df_starts_with(s, head) else head + s
