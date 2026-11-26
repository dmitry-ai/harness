# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Iterable
from Df.Core.lib.array.map import df_map
from Df.Core.lib.text.n.cc import df_cc_n
from Df.Core.lib.text.n.explode import df_explode_n
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2022-11-26 Prefix every line of string or iterable `v` with a leading tab character (`\t`).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/prepend-append/tab.php#L2-L15
# @used-by :meth:`Df.Core.Html.Tag.Tag.__contentStr()`
# @used-by :meth:`Df.Core.Html.Tag.Tag.__openTagWithAttributesAsText()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpArray()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpObject()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_tab(v: str | Iterable[str]) -> str:
	return df_tab(df_explode_n(v)) if isinstance(v, str) else df_cc_n(df_map(v, lambda s: f'\t{s}'))
