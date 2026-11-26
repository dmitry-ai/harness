# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.lang.type.conversion.string import df_string
from Df.Core.lib.reflection.text.cts import df_cts
from Df.Qa.lib.dump import df_dump
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2015-04-05 Describe the type and value of `v` for diagnostic error messages.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/dump/type.php#L16-L20
# @used-by :func:`Df.Qa.lib.validation.assert_.class_._check_ar()`
# @used-by :func:`Df.Qa.lib.validation.result.df_result_s()`
# @used-by :meth:`test_df_qa.TestDfQa.test_type_and_kv()`
def df_type(v: Any) -> str:
	if None is v:
		r = '`null`'
	elif isinstance(v, (bool, int, float, str)):
		r = f'«{df_string(v)}» ({type(v).__name__})'
	elif isinstance(v, (list, dict)):
		c = len(v)
		r = f'an array of {c} elements' if 10 < c else f'an array: {df_dump(v)}'
	else:
		_ = df_dump(v)
		r = f'an object: `{df_cts(v)}`'
	return r