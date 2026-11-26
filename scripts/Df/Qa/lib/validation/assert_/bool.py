# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Qa.lib.dump import df_dump
from Df.Qa.lib.validation.error import df_error
_NO = (0, '0', 'false', False, None, 'нет', 'no', 'off', '')
_YES = (1, '1', 'true', True, 'да', 'yes', 'on')
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Strictly parse a boolean-like scalar (English/Russian yes/no/on/off/0/1/bool/None) or raise df_error.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/bool.php#L13-L33
# @used-by :func:`Df.Core.lib.lang.call._bind_named_param()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_array_and_bool()`
def df_bool(v: Any) -> bool:
	if any((type(v) is type(x) and v == x for x in _NO)):
		r = False
	elif any((type(v) is type(x) and v == x for x in _YES)):
		r = True
	else:
		df_error('A boolean value is expected, but got «%s».', df_dump(v))
		r = False
	return r