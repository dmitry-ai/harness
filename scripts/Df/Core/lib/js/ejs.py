# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import json
from Df.Core.lib.json import df_json_encode
from Df.Core.lib.text.quote import df_quote_single
from Df.Core.lib.text.trim import df_trim
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-02-17 Format `v` as a JavaScript literal suitable for `var name = <value>;`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/js/ejs.php#L2-L12
# @used-by :func:`Df.Core.lib.js.window_data.df_js_data()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_ejs(v: Any) -> str:
	return df_json_encode(v) if not isinstance(v, str) else str(df_quote_single(str(df_trim(json.dumps(v), '"')).replace("'", '\\u0027')))
