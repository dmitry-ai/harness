# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.array.map.r import df_map_r
from Df.Core.lib.text.n.explode import df_explode_n
from Df.Core.lib.text.trim import df_trim
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2018-09-27 Parse `key: value` lines into a trimmed dict.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/parse.php#L2-L9
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_parse_colon(s: str) -> dict[str, str]:
	return df_map_r(df_explode_n(s), lambda line: df_trim(line.split(':', 1)))
