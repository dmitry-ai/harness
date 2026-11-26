# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from Df.Core.Text.Regex import Regex
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# Match an integer captured by `pattern` in `subject`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/regex.php#L4-L10
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_preg_int(pattern: str, subject: str, throwOnNotMatch: bool=False) -> int | None | bool:
	return Regex.i(pattern, subject, True, throwOnNotMatch).matchInt()
# 2015-03-23 Match `pattern` against `subject`, returning a single match string or list of groups.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/regex.php#L12-L20
# @used-by :func:`df_preg_prefix()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_preg_match(pattern: str, subject: str, throwOnNotMatch: bool=False) -> str | list[str] | None | bool:
	return Regex.i(pattern, subject, True, throwOnNotMatch).match()
# 2018-11-11 Match leading literal `prefix` and return the remaining suffix of `subject`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/regex.php#L22-L29
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_preg_prefix(prefix: str, subject: str, throwOnNotMatch: bool=False) -> str | list[str] | None | bool:
	return df_preg_match(f'#^{re.escape(prefix)}([\\S\\s]*)#', subject, throwOnNotMatch)
# Return True iff `pattern` matches `subject`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/regex.php#L31-L37
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_preg_test(pattern: str, subject: str, throwOnError: bool=True) -> bool:
	return Regex.i(pattern, subject, throwOnError, False).test()
