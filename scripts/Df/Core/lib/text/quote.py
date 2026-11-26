# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.Helper.Text import Text
from Df.Core.lib.text.main import df_t
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-11-22 Wrap string(s) in double quotes `"..."`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/quote.php#L4-L10
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_quote_double(s: str | list[str] | dict[str, str]) -> str | list[str] | dict[str, str]:
	return df_t().quote(s, Text.QUOTE__DOUBLE)
# Wrap string(s) in Russian guillemets `«...»`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/quote.php#L12-L19
# @used-by :func:`Df.Core.lib.text.csv.df_csv_pretty_quote()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_quote_russian(s: str | list[str] | dict[str, str]) -> str | list[str] | dict[str, str]:
	return df_t().quote(s, Text.QUOTE__RUSSIAN)
# Wrap string(s) in single quotes `'...'`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/quote.php#L21-L28
# @used-by :func:`Df.Core.lib.js.ejs.df_ejs()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_quote_single(s: str | list[str] | dict[str, str]) -> str | list[str] | dict[str, str]:
	return df_t().quote(s, Text.QUOTE__SINGLE)
