# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.array.select import dfa
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# Text quoting helper singleton.
# https://github.com/mage2pro/core/blob/11.6.1/Core/Helper/Text.php#L3-L50
class Text:
	QUOTE__DOUBLE = 'double'
	QUOTE__RUSSIAN = 'russian'
	QUOTE__SINGLE = 'single'
	__QUOTES: dict[str, tuple[str, str]] = {'double': ('"', '"'), 'russian': ('«', '»'), 'single': ("'", "'")}
	__s: Text | None = None
	# Wrap a string or sequence of strings in double, single, or Russian guillemet quotes.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Helper/Text.php#L4-L28
	# @used-by :func:`Df.Core.lib.text.quote.df_quote_double()`
	# @used-by :func:`Df.Core.lib.text.quote.df_quote_russian()`
	# @used-by :func:`Df.Core.lib.text.quote.df_quote_single()`
	# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
	def quote(self, s: str | list[str] | dict[str, str], t: str=QUOTE__RUSSIAN) -> str | list[str] | dict[str, str]:
		eff = Text.QUOTE__DOUBLE if '"' == t else (Text.QUOTE__SINGLE if "'" == t else t)
		quotes = dfa(Text.__QUOTES, eff)
		if None is quotes:
			from Df.Qa.lib.validation.error import df_error
			df_error(f'An unknown quote: «{eff}».')
		wrap = lambda v: f'{quotes[0]}{v}{quotes[1]}'
		if isinstance(s, dict):
			r: str | list[str] | dict[str, str] = {k: wrap(v) for k, v in s.items()}
		elif isinstance(s, list):
			r = [wrap(v) for v in s]
		else:
			r = wrap(s)
		return r
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Helper/Text.php#L48-L49
	# @used-by :func:`Df.Core.lib.text.main.df_t()`
	# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
	@staticmethod
	def s() -> Text:
		if None is Text.__s:
			Text.__s = Text()
		return Text.__s
