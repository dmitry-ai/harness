# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.clean.main import df_clean
from Df.Core.lib.array.map.k import df_map_k
from Df.Core.lib.text.n.cc import df_cc_n
from Df.Core.lib.text.prepend_append.pad import df_pad
from Df.Qa.lib.dump import df_dump
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2017-07-09 Format a cleaned key-value mapping into aligned `key: dumped_value` lines.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/dump/kv/.php#L12-L14
# @used-by :meth:`test_df_qa.TestDfQa.test_type_and_kv()`
def df_kv(a: dict[str, Any], pad: int=0) -> str:
	return df_cc_n(df_map_k(df_clean(a), lambda k, v: (df_pad(f'{k}:', pad) if pad else f'{k}: ') + df_dump(v)))