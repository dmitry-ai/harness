# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2016-10-23 Format a float with dot decimal separator and fixed precision (e.g., 3 => '3.00', 3.333 => '3.33').
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/float.php#L2-L24
# @used-by :func:`dff_2f()`
# @used-by :func:`dff_2i()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def dff_2(v: float, prec: int=2) -> str:
	return f'{float(v):.{prec}f}'
# 2016-09-08 Round numeric input to 2 decimal places via dff_2 and return float.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/float.php#L26-L32
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def dff_2f(v: float | int | str) -> float:
	return float(dff_2(float(v)))
# 2016-10-23 Format non-integers like dff_2() and drop the decimal part for integers.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/float.php#L34-L43
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def dff_2i(v: int | float, prec: int=2) -> str:
	return str(v) if isinstance(v, int) and (not isinstance(v, bool)) else dff_2(v, prec)
# 2015-04-09 Format a float while stripping insignificant trailing zeros after the decimal point.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/float.php#L45-L59
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def dff_chop0(v: Any) -> str:
	from Df.Qa.lib.validation.assert_.float import df_float
	f = df_float(v)
	int_part = int(f)
	# Intentionally compare float and int values with equality.
	return str(int_part) if f == int_part else f'{f:f}'.rstrip('0')
# 2017-09-29 Compare two numeric values within 0.1% deviation of `a`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/float.php#L61-L78
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_327_dff_eq_zero_and_negative()`
def dff_eq(a: float | str | int, b: float | str | int) -> bool:
	# 2026-11-26 "Fix dff_eq() returning False for zero and negative equal values": https://github.com/dmitry-ai/harness/issues/327
	# Upstream defect: https://github.com/mage2pro/core/issues/470
	fa, fb = (float(a), float(b))
	tol = .001 * abs(fa)
	return (fa == fb) if 0.0 == tol else dff_eq0(fa - fb, tol)
# 2016-09-08 Check whether `a` is within `deviation` (default 0.001) of zero.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/float.php#L80-L98
# @used-by :func:`dff_eq()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def dff_eq0(a: float, deviation: float=.001) -> bool:
	return abs(a) < deviation
