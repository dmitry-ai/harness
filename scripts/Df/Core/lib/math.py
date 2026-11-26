# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import math
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2022-10-30 Round half away from zero to an int, matching PHP round().
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/math.php#L2-L9
# @used-by :func:`Df.Core.lib.date.df_date_from_timestamp_14()`
# @used-by :func:`Df.Core.lib.date.df_num_days()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def df_round(v: float | int) -> int:
	return math.floor(v + 0.5) if 0 <= v else math.ceil(v - 0.5)
# 2015-02-26 Sum two numeric lists as vectors; a scalar `b` is broadcast to all coordinates.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/math.php#L11-L35
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cross_module_helpers()`
def df_vector_sum(a: list[int | float], b: int | float | list[int | float]) -> list[int | float]:
	length = len(a)
	if not isinstance(b, list):
		bv: list[int | float] = [b] * length
	else:
		from Df.Qa.lib.validation.assert_.numeric_comparison import df_assert_eq
		df_assert_eq(length, len(b))
		bv = list(b)
	av = list(a)
	return [av[i] + bv[i] for i in range(length)]
