# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, override
from Df.Core.lib.text.starts_ends import df_starts_with
from Df.Zf.Validate import Validate
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Integer string validator supporting leading zeroes such as `09` while rejecting floats such as `0.0`.
# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/IntT.php#L3-L39
class IntT(Validate):
	__s: IntT | None = None
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/IntT.php#L35
	# @used-by :meth:`Df.Zf.Validate.Validate.message()`
	# @see :meth:`Df.Zf.Validate.Validate._expected()`
	@override
	def _expected(self) -> str:
		return 'an integer'
	# Validate integer values and integer strings including leading zeroes like `09`.
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/IntT.php#L10-L28
	# @used-by :func:`Df.Qa.lib.validation.assert_.int.df_int()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_type_and_kv()`
	# @see :meth:`Df.Zf.Validate.Validate.isValid()`
	@override
	def isValid(self, v: Any) -> bool:
		self._v(v)
		if int is type(v):
			r = True
		elif isinstance(v, str) and v == v.strip() and '_' not in v:
			norm = v.lstrip('0') if '0' != v and (not df_starts_with(v, '0.')) else v
			try:
				r = str(int(v)) == norm
			except ValueError:
				r = False
		else:
			r = False
		return r
	# Return the singleton IntT validator instance.
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/IntT.php#L38
	# @used-by :func:`Df.Qa.lib.validation.assert_.int.df_int()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_type_and_kv()`
	@classmethod
	def s(cls) -> IntT:
		if None is cls.__s:
			cls.__s = cls()
		return cls.__s