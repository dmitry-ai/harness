# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# @used-by :func:`dfa_has_objects()`
def _is_object_value(v: Any) -> bool:
	return (not isinstance(v, (str, int, float, bool, list, dict, tuple, set, bytes))) and None is not v
# 2015-02-07 Return True iff `a` is a sequential 0..N-1 list (or empty list/dict with integer keys 0..N-1).
# 2017-10-29 Returns True for an empty list/dict.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/is.php#L2-L43
# @used-by :func:`Df.Core.lib.array.deep.dfa_deep_slice()`
# @used-by :func:`Df.Core.lib.array.insert.dfa_insert()`
# @used-by :func:`Df.Core.lib.array.key.transform.dfak_transform()`
# @used-by :func:`Df.Core.lib.array.sort.df_ksort_r_ci()`
# @used-by :func:`df_is_assoc()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def array_is_list(a: Any) -> bool:
	if isinstance(a, list):
		r = True
	elif isinstance(a, dict):
		r = all((k == idx and int is type(k) for idx, k in enumerate(a.keys())))
	else:
		r = False
	return r
# 2015-02-07 Return True iff `a` is an associative dict (or empty dict/list).
# 2017-10-29 Returns True for an empty dict/list.
# 2024-05-20 "`df_is_assoc()` should accept a non-array argument": https://github.com/mage2pro/core/issues/378
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/is.php#L45-L60
# @used-by :func:`Df.Core.lib.array.clean.filter.df_filter_f()`
# @used-by :func:`Df.Core.lib.array.sort.df_ksort()`
# @used-by :func:`Df.Qa.lib.validation.assert_.array.df_assert_assoc()`
# @used-by :func:`Df.Qa.lib.validation.error._parse_error_args()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def df_is_assoc(a: Any) -> bool:
	return isinstance(a, (dict, list)) and ((not a) or (not array_is_list(a)))
# 2023-07-25 Return True iff any element at any nesting depth of `a` is a custom object instance.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/is.php#L62-L68
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpArray()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def dfa_has_objects(a: Any) -> bool:
	from Df.Core.lib.array.find import df_find
	return bool(df_find(a, _is_object_value, [], [], 0, True))
