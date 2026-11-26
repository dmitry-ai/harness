# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, override
import math
import re
from Df.Core.lib.text.starts_ends import df_ends_with
from Df.Zf.Validate import Validate
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Floating-point string validator supporting both dot and comma decimal separators.
# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/FloatT.php#L3-L43
class FloatT(Validate):
	__PATTERN = re.compile(r'^[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)(?:[eE][+-]?\d+)?$')
	__s: FloatT | None = None
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/FloatT.php#L32
	# @used-by :meth:`Df.Zf.Validate.Validate.message()`
	# @see :meth:`Df.Zf.Validate.Validate._expected()`
	@override
	def _expected(self) -> str:
		return 'a float'
	# Accept numeric values or en_US/ru_RU float strings, including trailing decimal dot like `368.`.
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/FloatT.php#L10-L25
	# @used-by :func:`Df.Qa.lib.validation.assert_.float._float_str()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_type_and_kv()`
	# @see :meth:`Df.Zf.Validate.Validate.isValid()`
	@override
	def isValid(self, v: Any) -> bool:
		self._v(v)
		if bool is type(v):
			r = False
		elif isinstance(v, (int, float)):
			r = (not math.isnan(v)) and (not math.isinf(v))
		elif isinstance(v, str):
			s = f'{v}0' if df_ends_with(v, '.') and '.' != v else v
			r = bool(self.__PATTERN.match(s))
		else:
			r = False
		return r
	# Return the singleton FloatT validator instance.
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/FloatT.php#L42
	# @used-by :func:`Df.Qa.lib.validation.assert_.float._float_str()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_type_and_kv()`
	@classmethod
	def s(cls) -> FloatT:
		if None is cls.__s:
			cls.__s = cls()
		return cls.__s