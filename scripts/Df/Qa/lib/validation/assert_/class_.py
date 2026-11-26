# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.find import df_find
from Df.Core.lib.cache.dfcf import dfcf
from Df.Core.lib.reflection.text.check import _load_class, df_class_exists
from Df.Core.lib.reflection.text.cts import df_cts
from Df.Qa.lib.dump.type import df_type
from Df.Qa.lib.validation.error import df_error
from Df.Qa.lib.validation.param import df_param_sne
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Validate that object/type/class-name `v` is an instance or subclass of `c`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/class.php#L28-L39
# @used-by :func:`df_ar()`
def _check_ar(v: Any, c: Any=None, m: Any=None) -> Any:
	if c:
		c_name = df_cts(c)
		if None is v:
			df_error(m or f'Expected class: «{c_name}», given `null`.')
		if not isinstance(v, (str, object)) or isinstance(v, (int, float, bool, list, dict, tuple, set)):
			df_error(m or 'Expected class: «%s», given: %s.', c_name, df_type(v))
		if not _matches_class(v, c):
			df_error(m or f'Expected class: «{c_name}», given class: «{df_cts(v)}».')
	return v
# Check whether object, type, or class name `v` matches target type or class name `c`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/class.php#L33-L36
# @used-by :func:`_check_ar()`
# @used-by :func:`df_is()`
def _matches_class(v: Any, c: Any) -> bool:
	target = c if isinstance(c, type) else (type(c) if not isinstance(c, str) else _load_class(c))
	if isinstance(v, str):
		v_cls = _load_class(df_assert_class_exists(v))
		r = None is not target and None is not v_cls and issubclass(v_cls, target)
	elif isinstance(v, type):
		r = None is not target and issubclass(v, target)
	else:
		r = None is not target and isinstance(v, target)
	return r
# 2016-11-10 Assert that `v` is an instance or subclass of `c` (when `c` is provided) and return `v`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/class.php#L28-L39
# @used-by :func:`Df.Core.lib.object.new.df_newa()`
# @used-by :func:`Df.Core.lib.object.objects.df_ic()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_class_and_other()`
def df_ar(v: Any, c: Any=None, m: Any=None) -> Any:
	return dfcf(_check_ar, [v, c, m])
# 2016-08-03 Assert that class name `c` exists and can be resolved, returning `c`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/class.php#L48-L51
# @used-by :func:`_matches_class()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_class_and_other()`
def df_assert_class_exists(c: str, m: Any=None) -> str:
	df_param_sne(c, 0)
	if not df_class_exists(c):
		df_error(m or f'The required class «{c}» does not exist.')
	return c
# 2015-03-04 Return True iff `v` belongs to at least one of the specified classes `cc`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/class.php#L85
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_class_and_other()`
def df_is(v: Any, *cc: str | type) -> bool:
	return bool(df_find(list(cc), lambda c: _matches_class(v, c)))