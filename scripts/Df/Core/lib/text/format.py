# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import re
from Df.Core.lib.array.first import df_first
from Df.Core.lib.array.part import df_tail
from Df.Core.lib.array.select import dfa
from Df.Core.lib.array.unpack import df_args
from Df.Core.lib.empty import df_es
from Df.Core.lib.lang.other import df_no_rec
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2020-02-04 Format `s1 (s2)` unless either part is empty or identical.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/format.php#L4-L17
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_desc(s1: str, s2: str) -> str:
	return s2 if df_es(s1) else (s1 if df_es(s2) or s2 == s1 else f'{s1} ({s2})')
# Format message from variadic args: 0 -> '', 1 -> a[0], (str, dict) -> strtr replacement, else df_sprintf.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/format.php#L19-L42
# @used-by :func:`Df.Qa.lib.validation.error.df_error_create()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_format(*a: Any) -> str:
	items = df_args(list(a))
	r: str | None = None
	if 0 == len(items):
		r = ''
	elif 1 == len(items):
		r = str(items[0])
	elif 2 == len(items) and isinstance(items[1], dict):
		res = str(items[0])
		for k, v in items[1].items():
			res = res.replace(str(k), str(v))
		r = res
	return r if None is not r else df_sprintf(items)
# Format printf-style string, falling back to the unformatted template on formatting error.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/format.php#L44-L64
# @used-by :func:`df_format()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_sprintf(s: Any, *rest: Any) -> str:
	tmpl, args = (str(df_first(s)), list(s)) if isinstance(s, list) else (str(s), [s, *rest])
	try:
		r = df_sprintf_strict(args)
	except BaseException:
		r = tmpl
	return r
# Format printf-style string strictly, raising a diagnostic Df error (guarded by df_no_rec) on mismatch.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/format.php#L66-L107
# @used-by :func:`df_sprintf()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_sprintf_strict(s: Any, *rest: Any) -> str:
	tmpl, args = (str(df_first(s)), list(s)) if isinstance(s, list) else (str(s), [s, *rest])
	r = ''
	if 1 == len(args):
		r = tmpl
	else:
		tail = df_tail(args)
		try:
			r = tmpl % tuple(tail)
		except BaseException as th:
			from Df.Qa.lib.dump import df_dump
			from Df.Qa.lib.exception import df_xts
			from Df.Qa.lib.validation.error import df_error
			df_no_rec(lambda: df_error(f'df_sprintf_strict failed: «{{message}}».\nPattern: {tmpl}.\nParameters:\n{{params}}.', {'{message}': df_xts(th), '{params}': df_dump(tail)}))
	return r
# 2016-03-09 Substitute `{key}` placeholders in `s` using `variables` dict and optional `onUnknown` fallback.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/format.php#L109-L124
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_var(s: str, variables: dict[str, Any], onUnknown: Any=None) -> str:
	return re.sub(r'\{([^}]*)\}', lambda m: str(dfa(variables, m.group(1), onUnknown) or ''), s)
