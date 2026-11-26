# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.empty import df_es
from Df.Qa.Method import Method as Q
from Df.Qa.lib.validation.error import df_error
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2017-01-14 Assert that `v` is strictly not False and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/other.php#L18-L20
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_class_and_other()`
def df_assert_nef(v: Any, m: Any=None) -> Any:
	if False is v:
		df_error(m or 'The «false» value is rejected, any others are allowed.')
	return v
# Assert that variable `v` is a non-empty string (preserving `'0'`) and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/other.php#L37-L41
# @used-by :meth:`test_df_qa._SampleService.checkVar()`
def df_assert_sne(v: str, sl: int=0) -> str:
	sl += 1
	if df_es(v):
		Q.raiseErrorVariable('df_assert_sne', [Q.NES], sl)
	return v