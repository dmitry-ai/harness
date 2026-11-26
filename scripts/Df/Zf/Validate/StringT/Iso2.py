# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, override
from Df.Zf.Validate import Validate
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Validator checking whether a value is a 2-character ISO 3166-1 alpha-2 country code string.
# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/Iso2.php#L3-L25
class Iso2(Validate):
	__s: Iso2 | None = None
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/Iso2.php#L18
	# @used-by :meth:`Df.Zf.Validate.Validate.message()`
	# @see :meth:`Df.Zf.Validate.Validate._expected()`
	@override
	def _expected(self) -> str:
		return 'an ISO 3166-1 alpha-2 country code'
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/Iso2.php#L11
	# @used-by :func:`Df.Qa.lib.validation.check.df_check_iso2()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_type_and_kv()`
	# @see :meth:`Df.Zf.Validate.Validate.isValid()`
	@override
	def isValid(self, v: Any) -> bool:
		self._v(v)
		return isinstance(v, str) and 2 == len(v)
	# Return the singleton Iso2 validator instance.
	# https://github.com/mage2pro/core/blob/11.6.1/Zf/Validate/StringT/Iso2.php#L24
	# @used-by :func:`Df.Qa.lib.validation.check.df_check_iso2()`
	# @used-by :meth:`Df.Qa.Method.Method.assertParamIsIso2()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_type_and_kv()`
	@classmethod
	def s(cls) -> Iso2:
		if None is cls.__s:
			cls.__s = cls()
		return cls.__s