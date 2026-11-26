# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import html
import re
import unicodedata
from Df.Core.lib.array.other.flatten import dfa_flatten
from Df.Core.lib.lang.call.a import df_call_a
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-02-17 Escape HTML entities including single quotes (matching PHP htmlspecialchars ENT_QUOTES without double-encoding).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/filter.php#L2-L22
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_e(*a: Any) -> str | list[str]:
	return df_call_a(lambda s: html.escape(s, quote=True), list(a))
# 2017-04-22 Remove all non-digit characters (e.g., '+79.6-2' => '7962').
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/filter.php#L24-L30
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_remove_non_digits(s: str) -> str:
	return re.sub(r'\D', '', s)
# 2015-03-03 Remove all substrings listed in `*remove` from `s`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/filter.php#L32-L46
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_string_clean(s: str, *remove: Any) -> str:
	r = s
	for tok in dfa_flatten(list(remove)):
		r = r.replace(str(tok), '')
	return r
# 2017-02-09 Transliterate accented Latin characters to ASCII via Unicode NFKD decomposition.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/filter.php#L48-L97
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_translit(s: str) -> str:
	return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
