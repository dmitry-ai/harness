# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.other.flatten import dfa_flatten
from Df.Core.lib.array.unpack import df_args
from Df.Core.lib.text.quote import df_quote_russian
from Df.Core.lib.text.trim import df_trim
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-02-07 Join items with `,` (e.g., ['a', 'b'] => 'a,b').
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/csv.php#L3-L16
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_csv(*a: Any) -> str:
	return ','.join((str(x) for x in df_args(list(a))))
# 2015-02-07 Split a delimited string into trimmed string items (empty list for falsy input).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/csv.php#L25-L42
# @used-by :func:`df_csv_parse_int()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_csv_parse(s: str | None, d: str=',') -> list[str]:
	return [] if not s else df_trim(s.split(d))
# Parse a comma-separated string into a list of integers via df_int().
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/csv.php#L44-L51
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_csv_parse_int(s: str | None) -> list[int]:
	from Df.Qa.lib.validation.assert_.int import df_int
	return df_int(df_csv_parse(s))
# 2015-02-07 Join flattened items with `, ` (e.g., ['a', 'b'] => 'a, b').
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/csv.php#L53-L73
# @used-by :func:`Df.Core.lib.html.df_style_inline_hide()`
# @used-by :func:`Df.Qa.lib.validation.assert_.array.df_assert_in()`
# @used-by :func:`df_csv_pretty_quote()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_csv_pretty(*a: Any) -> str:
	return ', '.join((str(x) for x in dfa_flatten(list(a))))
# 2022-10-29 Wrap items in Russian guillemets and join with `, `.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/csv.php#L75-L80
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_csv_pretty_quote(*a: Any) -> str:
	return df_csv_pretty(df_quote_russian(df_args(list(a))))
