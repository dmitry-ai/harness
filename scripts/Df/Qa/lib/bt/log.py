# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Qa.Trace import Trace
from Df.Qa.Trace.Formatter import Formatter
from Df.Qa.lib.bt.main import df_bt, df_bt_inc
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2019-12-16 Format a backtrace (skipping `p` leading caller frames, or inspecting an exception/frame list) as text.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/log.php#L24
# @used-by :meth:`test_df_qa.TestDfQa.test_bt_helpers()`
def df_bt_s(p: Any=0) -> str:
	return str(Formatter.p(Trace(df_bt(df_bt_inc(p)))))