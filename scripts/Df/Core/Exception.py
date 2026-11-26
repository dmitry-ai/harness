# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from typing import override
import builtins
from Df.Core.lib.lang.prop.custom import DF_N, df_prop
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2016-07-31 Base Df exception carrying optional context, HTML message flag, and stack levels to skip.
# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L7-L226
class Exception(builtins.Exception):
	# 2024-05-22 "Provide an ability to specify a context for a `Df\Core\Exception` instance":
	# https://github.com/mage2pro/core/issues/375
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L20-L70
	# @used-by :func:`Df.Qa.lib.validation.error.df_error_create()`
	# @used-by :meth:`Df.Qa.Method.Method.__throwException()`
	# @used-by :meth:`Exception.wrap()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_exception_and_json_class()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_diagnostics_and_exceptions()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_trace_and_failure()`
	# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_326_exception_stack_levels()`
	# @see :meth:`builtins.Exception.__init__()`
	@override
	def __init__(self, *a: Any) -> None:
		self.__messageIsHtml = False
		self.__stackLevelsCountToSkip = 0
		m, prev = self.__parseArg0(a[0] if 0 < len(a) else None)
		prev = self.__parseArg1(a[1] if 1 < len(a) else None, prev)
		if None is m:
			from Df.Qa.lib.exception import df_xts
			# 2024-09-01 "`Df\Core\Exception::__construct()` should log nothing because it could be called in not an error case":
			# https://github.com/mage2pro/core/issues/430
			m = df_xts(prev) if None is not prev else 'No message'
		self.__msg = m
		self.__prev = prev
		super().__init__(m)
		if None is not prev:
			self.__cause__ = prev
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L30-L47
	# @used-by :meth:`Exception.__init__()`
	def __parseArg0(self, a0: Any) -> tuple[str | None, BaseException | None]:
		prev: BaseException | None = None
		m: str | None = None
		if isinstance(a0, dict):
			self.context(a0)
		elif isinstance(a0, BaseException):
			prev = a0
		elif isinstance(a0, str):
			m = a0
		return (m, prev)
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L48-L56
	# @used-by :meth:`Exception.__init__()`
	def __parseArg1(self, a1: Any, prev: BaseException | None) -> BaseException | None:
		r = prev
		if None is not a1:
			if isinstance(a1, BaseException):
				r = a1
			# 2026-11-26 "Fix Df\Core\Exception::__construct() checking $prev instead of $a1 for stack levels": https://github.com/dmitry-ai/harness/issues/326
			# Upstream defect: https://github.com/mage2pro/core/issues/469
			elif int is type(a1):
				self.__stackLevelsCountToSkip = a1
		return r
	# Provide subclasses with a typed accessor for the wrapped previous exception.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L194-L200
	# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_334_method_throws_dfe_with_stack_levels()`
	def _prev(self) -> BaseException | None:
		return self.__prev
	# 2024-05-20 "Provide an ability to specify a context for a `Df\Core\Exception` instance":
	# https://github.com/mage2pro/core/issues/375
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L72-L85
	# @used-by :func:`Df.Qa.lib.validation.error.df_error_create()`
	# @used-by :meth:`Exception.__parseArg0()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_error_helpers()`
	def context(self, v: Any=DF_N) -> Any:
		return df_prop(self, v, {})
	# Return the count of trailing stack frames to omit from diagnostic reports.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L87-L90
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_exception_and_json_class()`
	# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_326_exception_stack_levels()`
	# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_334_method_throws_dfe_with_stack_levels()`
	def getStackLevelsCountToSkip(self) -> int:
		return self.__stackLevelsCountToSkip
	# 2016-07-31
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L92-L98
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_exception_and_json_class()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_error_helpers()`
	def isMessageHtml(self) -> bool:
		return self.__messageIsHtml
	# 2016-07-31
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L100-L104
	# @used-by :func:`Df.Qa.lib.validation.error.df_error_html()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_exception_and_json_class()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_trace_and_failure()`
	def markMessageAsHtml(self) -> Exception:
		self.__messageIsHtml = True
		return self
	# Overridable diagnostic message accessor for subclasses whose message is assembled dynamically.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L106-L137
	# @used-by :meth:`Exception.messageD()`
	# @used-by :meth:`Exception.throw_()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_exception_and_json_class()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_error_helpers()`
	def message(self) -> str:
		return self.__msg
	# A message for the end user; defaults to empty so low-level diagnostics are not leaked.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L139-L154
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_exception_and_json_class()`
	def messageC(self) -> str:
		return ''
	# Message for the developer.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L156-L165
	# @used-by :func:`Df.Qa.lib.exception.df_xtsd()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_exception_and_json_class()`
	def messageD(self) -> str:
		return self.message()
	# 2017-10-03
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L167-L172
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_exception_and_json_class()`
	def sentryType(self) -> str:
		return f'{type(self).__module__}.{type(self).__qualname__}'
	# 2024-05-22 "Implement `Df\Core\Exception::throw_()`": https://github.com/mage2pro/core/issues/386
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L174-L192
	# @used-by :func:`Df.Qa.lib.validation.error.df_error()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_exception_and_json_class()`
	def throw_(self) -> None:
		self.args = (self.message(),)
		raise self
	# 2023-08-02 "Treat `\Throwable` similar to `\Exception`": https://github.com/mage2pro/core/issues/311
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Exception.php#L220-L225
	# @used-by :func:`Df.Qa.lib.validation.error.df_error_create()`
	# @used-by :meth:`Df.Qa.Failure.Exception.Exception.i()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_exception_and_json_class()`
	@staticmethod
	def wrap(r: BaseException) -> Exception:
		return r if isinstance(r, Exception) else Exception(r)
