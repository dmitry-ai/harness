# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.map import df_map
from Df.Core.lib.empty import df_nes
from Df.Qa.lib.validation.assert_ import df_assert
from Df.Qa.lib.validation.assert_.numeric_comparison import df_assert_ge, df_assert_gt0
from Df.Qa.lib.validation.error import df_error
from Df.Zf.Validate.StringT.FloatT import FloatT
_FLOAT_CACHE: dict[str, float] = {}
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Validate, parse (supporting comma decimal separator and trailing dot), and cache a float string.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/float.php#L30-L58
# @used-by :func:`df_float()`
def _float_str(v: Any) -> float:
	is_s = isinstance(v, str)
	if is_s and v in _FLOAT_CACHE:
		r = _FLOAT_CACHE[v]
	elif not FloatT.s().isValid(v):
		df_error(FloatT.s().message())
		r = 0.0
	else:
		df_assert(is_s)
		r = float(v.replace(',', '.'))
		_FLOAT_CACHE[v] = r
	return r
# Validate and convert a scalar or array of scalars into float(s), reporting type failures via df_error().
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/float.php#L16-L61
# @used-by :func:`Df.Core.lib.float.dff_chop0()`
# @used-by :func:`df_float_positive()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_float_and_int()`
def df_float(v: Any, allowNull: bool=True) -> Any:
	if isinstance(v, (list, dict)):
		r: Any = df_map(df_float, v, allowNull)
	elif float is type(v):
		r = v
	elif int is type(v):
		r = float(v)
	elif allowNull and df_nes(v):
		r = 0.0
	else:
		r = _float_str(v)
	return r
# Validate and convert `v` into a positive float (or >= 0 if `allow0`), optionally returning None on failure.
# 2023-11-27 https://github.com/mage2pro/core/issues/337
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/float.php#L69-L84
# @used-by :func:`df_float_positive0()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_float_and_int()`
def df_float_positive(v: Any, allow0: bool=False, throw: bool=True) -> float | None:
	if not throw:
		try:
			r: float | None = df_float_positive(v, allow0, True)
		except BaseException:
			r = None
	else:
		r = df_float(v, allow0)
		if allow0:
			df_assert_ge(0, r)
		else:
			df_assert_gt0(r)
	return r
# 2021-03-06 Validate and convert `v` into a non-negative float (>= 0).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/float.php#L91
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_float_and_int()`
def df_float_positive0(v: Any) -> float:
	return float(df_float_positive(v, True))