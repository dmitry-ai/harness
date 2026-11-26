# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.text.n.normalize import df_normalize
from Df.Core.lib.text.trim import df_trim
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2018-04-24 Trim `s`, normalize line endings to `\n`, and split into lines.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/n/explode.php#L2-L16
# @used-by :func:`Df.Core.lib.text.parse.df_parse_colon()`
# @used-by :func:`Df.Core.lib.text.prepend_append.tab.df_tab()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.__getSubjectSplitted()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_explode_n(s: str) -> list[str]:
	return df_normalize(str(df_trim(s))).split('\n')
