# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import html
from Df.Core.lib.array.clean.main import df_clean_r
from Df.Core.lib.array.map.k import df_map_k
from Df.Core.lib.cache.dfc import dfc
from Df.Core.lib.lang.other import df_nop
from Df.Core.lib.text.concatenate import df_cc_s
from Df.Core.lib.text.n.cc import df_cc_n
from Df.Core.lib.text.n.has import df_is_multiline
from Df.Core.lib.text.prepend_append.tab import df_tab
from Df.Core.lib.text.trim import df_trim
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2022-11-21 HTML element renderer supporting single-quoted attributes and optional multiline formatting.
# https://github.com/mage2pro/core/blob/11.6.1/Core/Html/Tag.php#L3-L161
class Tag:
	# 2022-11-21 Clean null/empty/False attributes via df_clean_r().
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Html/Tag.php#L4-L42
	# @used-by :func:`Df.Core.lib.html.df_tag()`
	# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
	def __init__(self, tag: str, attrs: dict[str, Any] | None=None, content: str | list[str]='', multiline: bool | None=None) -> None:
		raw = {} if None is attrs else attrs
		self.__tag = tag.lower()
		self.__attrs: dict[str, Any] = df_clean_r(raw, [False])
		self.__content = content
		self.__multiline = multiline if None is not multiline else 1 < len(raw)
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Html/Tag.php#L51-L55
	# @used-by :meth:`Tag.render()`
	def __contentStr(self) -> str:
		# @used-by :meth:`Tag.__contentStr()`
		def _build() -> str:
			c = str(df_trim(df_cc_n(self.__content), '\n'))
			return c if self.__tagIs('pre', 'code') or (not df_is_multiline(c)) else f'\n{df_tab(c)}\n'
		return dfc(self, _build)
	# Format a single HTML attribute preserving double quotes while escaping single quotes as &#39;.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Html/Tag.php#L73-L105
	# @used-by :meth:`Tag.__openTagWithAttributesAsText()`
	def __formatAttr(self, k: str, v: Any) -> str:
		from Df.Qa.lib.validation.assert_ import df_assert
		from Df.Qa.lib.validation.param import df_param_sne
		df_param_sne(k, 0)
		df_assert(v)
		raw = df_cc_s(v) if isinstance(v, list) else str(v)
		escaped = html.escape(raw, quote=False).replace("'", '&#39;')
		return f"{k}='{escaped}'"
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Html/Tag.php#L57-L109
	# @used-by :meth:`Tag.render()`
	def __openTagWithAttributesAsText(self) -> str:
		fmt = df_tab if self.__multiline else df_nop
		sep = '\n' if self.__multiline else ' '
		attr_map = df_map_k(self.__formatAttr, self.__attrs)
		joined = sep.join(attr_map.values()) if isinstance(attr_map, dict) else sep.join(attr_map)
		return df_cc_s(self.__tag, '\n' if self.__multiline else None, fmt(joined) if joined else '')
	# 2018-03-11 Self-closing div/script/span tags can misrender in browsers.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Html/Tag.php#L111-L118
	# @used-by :meth:`Tag.render()`
	def __shortTagAllowed(self) -> bool:
		return not self.__tagIs('div', 'script', 'span')
	# 2016-08-05
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Html/Tag.php#L120-L125
	# @used-by :meth:`Tag.__contentStr()`
	# @used-by :meth:`Tag.__shortTagAllowed()`
	def __tagIs(self, *tags: str) -> bool:
		return self.__tag in tags
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Html/Tag.php#L44-L49
	# @used-by :func:`Df.Core.lib.html.df_tag()`
	# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
	def render(self) -> str:
		c = self.__contentStr()
		nl = '\n' if self.__multiline else ''
		tail = '/>' if (not c) and self.__shortTagAllowed() else f'>{c}</{self.__tag}>'
		return f'<{self.__openTagWithAttributesAsText()}{nl}{tail}'
