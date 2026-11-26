# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.Html.Tag import Tag
from Df.Core.lib.empty import df_est
from Df.Core.lib.lang.call.a import df_call_a
from Df.Core.lib.text.csv import df_csv_pretty
from Df.Core.lib.text.n.cc import df_cc_n
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2016-11-13 Wrap string(s) in `<b>...</b>`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/html.php#L3-L10
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_html_b(*a: Any) -> str | list[str]:
	return df_call_a(list(a), lambda s: df_tag('b', {}, s))
# 2015-12-21 Render an inline `<style type='text/css'>` block (empty string if `css` is empty).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/html.php#L54-L61
# @used-by :func:`df_style_inline_hide()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_style_inline(css: str) -> str:
	return '' if not css else df_tag('style', {'type': 'text/css'}, css)
# 2016-12-04 Render an inline `<style>` rule hiding the given CSS selectors.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/html.php#L63-L71
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_style_inline_hide(*s: str) -> str:
	return '' if not s else df_style_inline(f'{df_csv_pretty(list(s))} {{display: none !important;}}')
# 2015-04-16 Render an HTML tag; string `attrs` is shorthand for `{'class': attrs}`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/html.php#L73-L149
# @used-by :func:`Df.Core.lib.caller.other.df_caller_mh()`
# @used-by :func:`Df.Core.lib.js.window_data.df_js_data()`
# @used-by :func:`Df.Qa.lib.dump.kv.table.df_kv_table()`
# @used-by :func:`df_html_b()`
# @used-by :func:`df_style_inline()`
# @used-by :func:`df_tag_ab()`
# @used-by :func:`df_tag_if()`
# @used-by :func:`df_tag_list()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_tag(tag: str, attrs: dict[str, Any] | str | None=None, content: str | list[str]='', multiline: bool | None=None) -> str:
	eff = {} if None is attrs else (attrs if isinstance(attrs, dict) else {'class': attrs})
	return Tag(tag, eff, content, multiline).render()
# 2016-11-17 Render an anchor tag opening in a new tab (`target='_blank'`).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/html.php#L151-L158
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_tag_ab(s: str, u: str) -> str:
	return df_tag('a', {'href': u, 'target': '_blank'}, s)
# 2016-10-24 Wrap `s` in `<tag>` only when `cond` is True.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/html.php#L160-L170
# @used-by :func:`df_tag_if_ne()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_tag_if(s: str, cond: bool, tag: str, attrs: dict[str, Any] | str | None=None) -> str:
	return s if not cond else df_tag(tag, attrs, s)
# 2024-04-14 Wrap `s` in `<tag>` only when `s` is non-empty after trimming.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/html.php#L172-L177
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_tag_if_ne(s: str, tag: str, attrs: dict[str, Any] | str | None=None) -> str:
	return df_tag_if(s, not df_est(s), tag, attrs)
# Render an ordered (`ol`) or unordered (`ul`) HTML list.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/html.php#L179-L189
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_tag_list(items: list[str], isOrdered: bool=False, cssList: str | None=None, cssItem: str | None=None) -> str:
	list_attrs = {'class': cssList} if cssList else {}
	item_attrs = {'class': cssItem} if cssItem else {}
	return df_tag('ol' if isOrdered else 'ul', list_attrs, df_cc_n([df_tag('li', item_attrs, i) for i in items]))
