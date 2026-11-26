# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.clean.main import df_clean
from Df.Core.lib.array.map.k import df_map_k
from Df.Core.lib.html import df_tag
from Df.Qa.lib.dump import df_dump
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2019-06-13 Format a cleaned key-value mapping into an HTML `<table>` of `<tr><td>k</td><td>v</td></tr>` rows.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/dump/kv/table.php#L8-L15
# @used-by :meth:`test_df_qa.TestDfQa.test_type_and_kv()`
def df_kv_table(a: dict[str, Any]) -> str:
	return df_tag('table', {}, df_map_k(df_clean(a), lambda k, v: df_tag('tr', {}, [df_tag('td', {}, str(k)), df_tag('td', {}, df_dump(v))])))