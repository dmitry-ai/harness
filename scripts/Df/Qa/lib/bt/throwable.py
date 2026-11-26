# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2023-08-25 "The exception point is not included to the exception's trace": https://github.com/mage2pro/core/issues/334
# Extract innermost-first backtrace frame dicts from an exception's traceback.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/throwable.php#L8
# @used-by :func:`Df.Qa.lib.bt.main.df_bt()`
# @used-by :meth:`test_df_qa.TestDfQa.test_bt_helpers()`
def df_bt_th(t: BaseException) -> list[dict[str, Any]]:
	from Df.Qa.lib.bt.main import _frame_dict
	r: list[dict[str, Any]] = []
	tb = t.__traceback__
	while None is not tb:
		r.append(_frame_dict(tb.tb_frame, tb.tb_lineno))
		tb = tb.tb_next
	r.reverse()
	return r