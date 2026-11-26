# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.text.contains import df_contains
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-08-24 Case-insensitive substring check.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/contains/ci.php#L2-L6
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_contains_ci(haystack: str, n: str) -> bool:
	return df_contains(haystack.upper(), n.upper())
