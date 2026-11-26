# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.is_ import df_is_assoc
from Df.Core.lib.text.csv import df_csv_pretty
from Df.Qa.lib.validation.error import df_error
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Assert that `a` is a list or dict (PHP array equivalent) and return it.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/array.php#L11
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_array_and_bool()`
def df_assert_array(a: Any) -> list[Any] | dict[Any, Any]:
	if not isinstance(a, (list, dict)):
		df_error('An array is expected.')
	return a
# 2017-02-18 Assert that `a` is an associative mapping and return it.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/array.php#L19
# @used-by :func:`Df.Core.lib.array.clean.main.df_clean_keys()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_array_and_bool()`
def df_assert_assoc(a: list[Any] | dict[Any, Any]) -> list[Any] | dict[Any, Any]:
	if not df_is_assoc(a):
		df_error('The array should be associative.')
	return a
# 2024-05-21 "Implement `df_assert_count()`": https://github.com/mage2pro/core/issues/380
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/array.php#L26-L28
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_array_and_bool()`
# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_332_df_assert_count_no_stray_brace()`
def df_assert_count(expected: int, a: list[Any] | dict[Any, Any], m: Any=None) -> list[Any] | dict[Any, Any]:
	v = len(a)
	if expected != v:
		# 2026-11-26 "Fix stray closing brace in df_assert_count() error message": https://github.com/dmitry-ai/harness/issues/332
		# Upstream defect: https://github.com/mage2pro/core/issues/475
		df_error(m or f'The array should have {expected} elements, but it has {v}.', {'array': a})
	return a
# 2017-01-14 Assert that `v` is strictly present in `a` and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/array.php#L42-L51
# @used-by :func:`Df.Core.lib.date.df_date_from_timestamp_14()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_array_and_bool()`
def df_assert_in(v: Any, a: list[Any] | dict[Any, Any], m: Any=None) -> Any:
	vals = list(a.values()) if isinstance(a, dict) else a
	if not any((type(v) is type(x) and v == x for x in vals)):
		suffix = f'. Allowed values: «{df_csv_pretty(vals)}».' if 10 >= len(vals) else ' because it is absent in the list of allowed values.'
		df_error(m or f'The value «{v}» is rejected{suffix}')
	return v