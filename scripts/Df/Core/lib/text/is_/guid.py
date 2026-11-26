# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2019-01-11 Return True iff `s` is a 36-character uppercase GUID string.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/is/guid.php#L2-L9
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_is_guid(s: str) -> bool:
	return 36 == len(s) and bool(re.match(r'^\{?[A-Z0-9]{8}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{12}\}?$', s))
