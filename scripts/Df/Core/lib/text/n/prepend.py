# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.empty import df_es
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-12-25 Prepend `\n` to a non-empty string.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/n/prepend.php#L2-L7
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpObject()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_n_prepend(s: str) -> str:
	return s if df_es(s) else f'\n{s}'
