# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import math
import re
from Df.Zf.Validate.StringT.Iso2 import Iso2
_EMAIL_RE = re.compile(r'^[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$')
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2021-03-22 Return True iff `v` lies between `min_` and `max_` (inclusive by default).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/check.php#L11-L13
# @used-by :func:`Df.Qa.lib.validation.assert_.numeric_comparison.df_assert_between()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_between(v: Any, min_: Any, max_: Any, inclusive: bool=True) -> bool:
	return (v >= min_ and v <= max_) if inclusive else (v > min_ and v < max_)
# Return True iff `v` is a valid 2-character ISO 3166-1 alpha-2 country code.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/check.php#L49
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_check_iso2(v: Any) -> bool:
	return Iso2.s().isValid(v)
# 2015-02-16 Return True iff `v` is a string, integer, boolean, or None.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/check.php#L62
# @used-by :func:`Df.Qa.lib.validation.result.df_result_s()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_check_s(v: Any) -> bool:
	return isinstance(v, (str, int, bool)) or None is v
# 2024-06-02 "Implement `df_is_email()`": https://github.com/mage2pro/core/issues/398
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/check.php#L25
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_is_email(v: Any) -> bool:
	return isinstance(v, str) and bool(_EMAIL_RE.match(v))
# Return True iff `v` is an integer or numeric value equal to its integer conversion.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/check.php#L34
# @used-by :func:`df_is_nat()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.matchInt()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_is_int(v: Any) -> bool:
	if int is type(v):
		r = True
	elif float is type(v):
		r = (not math.isnan(v)) and (not math.isinf(v)) and v == int(v)
	elif isinstance(v, str) and v == v.strip() and '_' not in v:
		try:
			fv = float(v)
			r = (not math.isnan(fv)) and (not math.isinf(fv)) and fv == int(fv)
		except ValueError:
			r = False
	else:
		r = False
	return r
# 2020-02-03 Return True iff `v` is a strictly positive integer (`> 0`).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/check.php#L43
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_numeric_comparison_and_check()`
def df_is_nat(v: Any) -> bool:
	return df_is_int(v) and 0 < float(v)