# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from Df.Core.lib.lang.prop.custom import DF_N, df_prop
from Df.Qa.lib.dump import df_dump
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Base abstract validator storing the last tested value and formatting diagnostic messages.
# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate.php#L11-L46
class Validate(ABC):
	# Return a human-readable phrase describing the expected type/format.
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate.php#L18
	# @used-by :meth:`Validate.message()`
	@abstractmethod
	def _expected(self) -> str:
		raise NotImplementedError
	# Store or retrieve the last validated value on this validator instance.
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate.php#L45
	# @used-by :meth:`StringT.FloatT.FloatT.isValid()`
	# @used-by :meth:`StringT.IntT.IntT.isValid()`
	# @used-by :meth:`StringT.Iso2.Iso2.isValid()`
	# @used-by :meth:`Validate.message()`
	def _v(self, v: Any=DF_N) -> Any:
		return df_prop(self, v)
	# Return validation error messages keyed by the validator class name.
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate.php#L25
	# @used-by :meth:`Df.Qa.Method.Method.__vp()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_type_and_kv()`
	def getMessages(self) -> dict[str, str]:
		return {f'{type(self).__module__}.{type(self).__qualname__}': self.message()}
	# Return True iff `v` satisfies this validator.
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate.php#L11
	# @used-by :meth:`Df.Qa.Method.Method.__vp()`
	@abstractmethod
	def isValid(self, v: Any) -> bool:
		raise NotImplementedError
	# Format a diagnostic error message for the last value passed to isValid().
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate.php#L32-L35
	# @used-by :func:`Df.Qa.lib.validation.assert_.float._float_str()`
	# @used-by :func:`Df.Qa.lib.validation.assert_.int.df_int()`
	# @used-by :meth:`Validate.getMessages()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_type_and_kv()`
	# @uses :meth:`Df.Zf.Validate.StringT.FloatT.FloatT._expected()`
	# @uses :meth:`Df.Zf.Validate.StringT.IntT.IntT._expected()`
	# @uses :meth:`Df.Zf.Validate.StringT.Iso2.Iso2._expected()`
	def message(self) -> str:
		v = self._v()
		if None is v:
			r = f'Got `NULL` instead of {self._expected()}.'
		else:
			r = f'Unable to recognize the value «{df_dump(v)}» of type «{type(v).__name__}» as {self._expected()}.'
		return r