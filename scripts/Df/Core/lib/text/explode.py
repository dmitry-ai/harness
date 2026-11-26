# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.array.clean.main import df_clean
from Df.Core.lib.array.other.array import df_array
from Df.Core.lib.array.other.flatten import dfa_flatten
from Df.Core.lib.text.trim import df_trim
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2016-03-25 Split `s` by any of the strings in `delimiters`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/explode.php#L2-L16
# @used-by :func:`Df.Core.lib.reflection.text.explode.df_explode_class()`
# @used-by :func:`Df.Core.lib.reflection.text.explode.df_explode_class_camel()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_explode_multiple(delimiters: list[str], s: str) -> list[str]:
	dels = list(delimiters)
	main = dels.pop(0)
	cur = s
	for d in dels:
		cur = cur.replace(d, main)
	return cur.split(main)
# 2016-09-03 Normalize backslashes to `/` and split a filesystem path into segments.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/explode.php#L18-L27
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_explode_path(p: str) -> list[str]:
	return df_explode_xpath(p.replace('\\', '/'))
# 2022-11-17 Split a string by spaces, trimming and discarding empty segments.
# 2024-06-11 "Improve `df_explode_space()`": https://github.com/mage2pro/core/issues/422
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/explode.php#L29-L49
# @used-by :func:`Df.Qa.lib.diagnostics.df_webserver()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_explode_space(s: str) -> list[str]:
	return df_clean(df_trim(s.split(' ')))
# Split a URL string on `/`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/explode.php#L51-L55
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_explode_url(url: str) -> list[str]:
	return url.split('/')
# 2015-02-06 Split a slash-delimited string (or list of such strings) into a flat list of path segments.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/explode.php#L57-L70
# @used-by :func:`Df.Core.lib.array.deep.dfa_deep()`
# @used-by :func:`Df.Core.lib.array.deep.dfa_deep_set()`
# @used-by :func:`Df.Core.lib.array.deep.dfa_deep_unset()`
# @used-by :func:`df_explode_path()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_explode_xpath(p: str | list[str]) -> list[str]:
	return dfa_flatten([str(s).split('/') for s in df_array(p)])
