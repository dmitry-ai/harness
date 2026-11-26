# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.other.flatten import dfa_flatten
from Df.Core.lib.array.unpack import df_arg
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-04-17 Return True iff `haystack` contains any needle from `*n` (accepts strings or nested lists).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/contains/.php#L2-L46
# @used-by :func:`Df.Core.lib.reflection.text.other.df_cld()`
# @used-by :func:`Df.Core.lib.text.n.has.df_is_multiline()`
# @used-by :func:`Df.Qa.lib.bt.filter.df_bt_filter_head()`
# @used-by :func:`ci.df_contains_ci()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_contains(haystack: str, *n: Any) -> bool:
	n0 = df_arg(list(n))
	if not isinstance(n0, list):
		r = str(n0) in haystack
	else:
		r = any((str(item) in haystack for item in dfa_flatten(list(n))))
	return r
