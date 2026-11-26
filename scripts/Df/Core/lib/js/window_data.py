# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.html import df_tag
from Df.Core.lib.js.ejs import df_ejs
from Df.Core.lib.text.concatenate import df_cc
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2018-05-21 Render a `<script type='text/javascript'>window.<n> = <v>;</script>` tag.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/js/window-data.php#L2-L14
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_js_data(n: str, v: dict[str, Any]) -> str:
	name = df_cc('.', n)
	return df_tag('script', {'type': 'text/javascript'}, f'window.{name} = {df_ejs(v)};')
