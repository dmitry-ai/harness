# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.empty import df_es
from Df.Qa.Method import Method as Q
from Df.Qa.lib.dump.type import df_type
from Df.Qa.lib.validation.check import df_check_s
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Assert that a method return value is a valid stringable scalar (string/int/bool/None) and return it as str.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/result.php#L13-L15
# @used-by :func:`df_result_sne()`
# @used-by :meth:`test_df_qa._SampleService.checkRes()`
def df_result_s(v: Any, sl: int=0) -> str:
	if not df_check_s(v):
		Q.raiseErrorResult('df_result_s', [f'A string is required, but got {df_type(v)}.'], sl + 1)
	return '' if None is v else str(v)
# Assert that a method return value is a non-empty string (preserving `'0'`).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/result.php#L37-L45
# @used-by :func:`Df.Core.lib.date.df_dts()`
# @used-by :meth:`test_df_qa._SampleService.checkResSne()`
def df_result_sne(v: str, sl: int=0) -> str:
	sl += 1
	df_result_s(v, sl)
	if df_es(v):
		Q.raiseErrorResult('df_result_sne', [Q.NES], sl)
	return v