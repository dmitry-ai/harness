# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.text.prepend_append.pad import STR_PAD_LEFT, df_pad
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-11-29 Left-pad `s` with leading `'0'` characters to length `count` (supports hex strings).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/prepend-append/pad0.php#L2-L9
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_pad0(count: int, s: str) -> str:
	return df_pad(s, count, '0', STR_PAD_LEFT)
