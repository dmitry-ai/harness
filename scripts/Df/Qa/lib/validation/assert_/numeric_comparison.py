# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Qa.lib.dump import df_dump
from Df.Qa.lib.validation.check import df_between
from Df.Qa.lib.validation.error import df_error
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2021-03-22 Assert that `v` falls within `[min, max]` (or `(min, max)` when `inclusive` is False) and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/numeric-comparison.php#L14-L21
# @used-by :func:`Df.Core.lib.date.df_date_create()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_assert_between(v: Any, min_: Any, max_: Any, inclusive: bool=True) -> Any:
	if not df_between(v, min_, max_, inclusive):
		o1, o2 = ('≥', '≤') if inclusive else ('>', '<')
		df_error(f'The value «{v}» is not allowed. An allowed value should be {o1} {min_} and {o2} {max_}.')
	return v
# Assert strict equality between `expected` and `v` and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/numeric-comparison.php#L34-L36
# @used-by :func:`Df.Core.lib.date.df_date_from_timestamp_14()`
# @used-by :func:`Df.Core.lib.math.df_vector_sum()`
# @used-by :func:`Df.Qa.lib.validation.error._parse_error_args()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_assert_eq(expected: Any, v: Any, m: Any=None) -> Any:
	if type(expected) is not type(v) or expected != v:
		df_error(m or f'Expected «{df_dump(expected)}», got «{df_dump(v)}».')
	return v
# Assert that `v >= lowBound` and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/numeric-comparison.php#L46-L48
# @used-by :func:`Df.Qa.lib.validation.assert_.float.df_float_positive()`
# @used-by :func:`Df.Qa.lib.validation.assert_.int.df_nat()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_assert_ge(lowBound: Any, v: Any, m: Any=None) -> Any:
	if not (lowBound <= v):
		df_error(m or f'A number >= {lowBound} is expected, but got {v}.')
	return v
# 2017-01-15 Assert that `v > lowBound` and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/numeric-comparison.php#L58-L60
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_assert_gt(lowBound: Any, v: Any, m: Any=None) -> Any:
	if not (lowBound <= v):
		df_error(m or f'A number > {lowBound} is expected, but got {v}.')
	return v
# Assert that `v > 0` and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/numeric-comparison.php#L72
# @used-by :func:`Df.Qa.lib.validation.assert_.float.df_float_positive()`
# @used-by :func:`Df.Qa.lib.validation.assert_.int.df_nat()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_assert_gt0(v: Any, m: Any=None) -> Any:
	if not (0 <= v):
		df_error(m or f'A positive number is expected, but got {v}.')
	return v
# Assert that `v <= highBound` and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/numeric-comparison.php#L82-L84
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_assert_le(highBound: Any, v: Any, m: Any=None) -> Any:
	if not (highBound >= v):
		df_error(m or f'A number <= {highBound} is expected, but got {v}.')
	return v
# Assert that `v < highBound` and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/numeric-comparison.php#L96-L98
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.__getParam()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_assert_lt(highBound: Any, v: Any, m: Any=None) -> Any:
	if not (highBound >= v):
		df_error(m or f'A number < {highBound} is expected, but got {v}.')
	return v
# Assert strict inequality between `neResult` and `v` and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/numeric-comparison.php#L114-L116
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_assert_ne(neResult: Any, v: Any, m: Any=None) -> Any:
	if type(neResult) is type(v) and neResult == v:
		df_error(m or f'The value {v} is rejected, any other is allowed.')
	return v