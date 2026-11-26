# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
from Df.Core.lib.array.map import df_map
from Df.Core.lib.empty import df_nts
from Df.Core.lib.lang.try_ import df_try
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2017-06-09 Trim `s` and truncate to `max_` chars with trailing ellipsis `…` if longer.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/trim.php#L7-L20
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_chop(s: str, max_: int=0) -> str:
	t = str(df_trim(s))
	return t if (not max_) or max_ >= len(t) else f'{df_trim_right(t[:max_ - 1])}…'
# Trim whitespace (and optional extra `charlist` characters) from string or list of strings.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/trim.php#L22-L89
# @used-by :func:`Df.Core.lib.empty.df_est()`
# @used-by :func:`Df.Core.lib.js.ejs.df_ejs()`
# @used-by :func:`Df.Core.lib.text.csv.df_csv_parse()`
# @used-by :func:`Df.Core.lib.text.explode.df_explode_space()`
# @used-by :func:`Df.Core.lib.text.n.explode.df_explode_n()`
# @used-by :func:`Df.Core.lib.text.parse.df_parse_colon()`
# @used-by :func:`df_chop()`
# @used-by :meth:`Df.Core.Html.Tag.Tag.__contentStr()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpS()`
# @used-by :meth:`Df.Qa.Failure.Failure._sections()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_trim(s: Any, charlist: str | None=None, throw: Any=False) -> Any:
	# @used-by :func:`df_trim()`
	def _do() -> Any:
		if isinstance(s, (list, dict)):
			r: Any = df_map(df_trim, s, [charlist, throw])
		else:
			txt = str(df_nts(s))
			if None is charlist:
				r = txt.strip()
			else:
				chars = charlist + ''.join((c for c in ('\n', '\r', ' ') if c not in charlist))
				r = txt.strip(chars)
			if ' ' == r:
				r = ''
		return r
	return df_try(_do, s if False is throw else throw)
# Strip leading whitespace or explicit `charlist` characters.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/trim.php#L91-L98
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_trim_left(s: str, charlist: str='') -> str:
	return s.lstrip(charlist if charlist else ' \t\n\r\0\x0b')
# Strip trailing whitespace or explicit `charlist` characters.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/trim.php#L100-L107
# @used-by :func:`df_chop()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_trim_right(s: str, charlist: str='') -> str:
	return s.rstrip(charlist if charlist else ' \t\n\r\0\x0b')
# Chop `trim` prefix and suffix from `s`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/trim.php#L109-L115
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_trim_text(s: str, trim: str | list[str]) -> str:
	return df_trim_text_left_right(s, trim, trim)
# 2016-10-28 Apply trimming callback `f` against candidate affixes `trimA`, stopping at the first change.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/trim.php#L117-L134
# @used-by :func:`df_trim_text_left()`
# @used-by :func:`df_trim_text_right()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_trim_text_a(s: str, trimA: list[str], f: Callable[[str, str], str]) -> str:
	r = s
	orig = len(r)
	for trim in trimA:
		r = f(r, trim)
		if orig != len(r):
			break
	return r
# Chop `trim` prefix (or first matching prefix in list `trim`) from string or list `s`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/trim.php#L136-L171
# @used-by :func:`agent_tools.markdown_links.display_address()`
# @used-by :func:`agent_tools.markdown_links.technical_label()`
# @used-by :func:`agent_tools.worktree_flow._apply_porcelain_line()`
# @used-by :func:`agent_tools.xref.java_tags._classify_javadoc_line()`
# @used-by :func:`agent_tools.xref.js_tags._parse_jsdoc_lines()`
# @used-by :func:`df_trim_text_left_right()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_normalize_and_trim_delegation_to_df()`
def df_trim_text_left(s: str | list[str], trim: str | list[str]) -> str | list[str]:
	if isinstance(s, list):
		r: str | list[str] = df_map(df_trim_text_left, s, [trim])
	elif isinstance(trim, list):
		r = df_trim_text_a(s, trim, df_trim_text_left)
	else:
		r = s[len(trim):] if s.startswith(trim) else s
	return r
# 2021-12-12 Chop `left` prefix and `right` suffix from `s`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/trim.php#L173-L181
# @used-by :func:`agent_tools.xref.java_tags._parse_javadoc_lines()`
# @used-by :func:`agent_tools.xref.js_tags._parse_jsdoc_lines()`
# @used-by :func:`df_trim_text()`
# @used-by :meth:`Df.Core.Text.Marker.Marker.unmark()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_normalize_and_trim_delegation_to_df()`
def df_trim_text_left_right(s: str, left: str | list[str], right: str | list[str]) -> str:
	return str(df_trim_text_right(str(df_trim_text_left(s, left)), right))
# Chop `trim` suffix (or first matching suffix in list `trim`) from string or list `s`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/trim.php#L183-L204
# @used-by :func:`df_trim_text_left_right()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_trim_text_right(s: str | list[str], trim: str | list[str]) -> str | list[str]:
	if isinstance(s, list):
		r: str | list[str] = df_map(df_trim_text_right, s, [trim])
	elif isinstance(trim, list):
		r = df_trim_text_a(s, trim, df_trim_text_right)
	else:
		r = s[:-len(trim)] if trim and s.endswith(trim) else s
	return r
