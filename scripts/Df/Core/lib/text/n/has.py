# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.text.contains import df_contains
from Df.Core.lib.text.n.normalize import df_normalize
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2024-09-22 Return True iff `s` contains a line break (`\n` or `\r`).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/n/has.php#L2-L8
# @used-by :meth:`Df.Core.Html.Tag.Tag.__contentStr()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.__isSubjectMultiline()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpObject()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_is_multiline(s: str) -> bool:
	return df_contains(df_normalize(s), '\n')
