# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.map import df_map
from Df.Core.lib.empty import df_nes
from Df.Qa.lib.validation.assert_.numeric_comparison import df_assert_ge, df_assert_gt0
from Df.Qa.lib.validation.error import df_error
from Df.Zf.Validate.StringT.IntT import IntT
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Validate and convert a scalar or array of scalars into integer(s).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/int.php#L16-L36
# @used-by :func:`Df.Core.lib.array.key.transform.dfa_key_int()`
# @used-by :func:`Df.Core.lib.text.csv.df_csv_parse_int()`
# @used-by :func:`df_nat()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_float_and_int()`
def df_int(v: Any, allowNull: bool=True) -> Any:
	if isinstance(v, (list, dict)):
		r: Any = df_map(df_int, v, allowNull)
	elif int is type(v):
		r = v
	elif bool is type(v):
		r = 1 if v else 0
	elif allowNull and df_nes(v):
		r = 0
	elif not IntT.s().isValid(v):
		df_error(IntT.s().message())
		r = 0
	else:
		r = int(v)
	return r
# 2015-04-13 Convert every element of a list or dict to int without validation, preserving dict keys.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/int.php#L49
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_float_and_int()`
def df_int_simple(v: list[Any] | dict[Any, Any]) -> list[int] | dict[Any, int]:
	return {k: int(val) for k, val in v.items()} if isinstance(v, dict) else [int(val) for val in v]
# Validate and convert `v` into a positive integer (or >= 0 when `allow0` is True).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/int.php#L60-L64
# @used-by :func:`df_nat0()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_float_and_int()`
def df_nat(v: Any, allow0: bool=False) -> int:
	r = int(df_int(v, allow0))
	if allow0:
		df_assert_ge(0, r)
	else:
		df_assert_gt0(r)
	return r
# Validate and convert `v` into a non-negative integer (>= 0).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/int.php#L76
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_float_and_int()`
def df_nat0(v: Any) -> int:
	return df_nat(v, True)