# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.text.n.normalize import df_normalize
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-03-03 Collapse normalized line breaks and tabs to single spaces.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/n/remove.php#L2-L21
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_single_line(s: str) -> str:
	return df_normalize(s).replace('\n', ' ').replace('\t', ' ')
