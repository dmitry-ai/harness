# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, override
import re
from Df.Core.Exception import Exception as DFE
from Df.Qa.Failure import Failure
from Df.Qa.lib.bt.main import df_bt
from Df.Qa.lib.dump import df_dump_ds
from Df.Qa.lib.exception import df_xf
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2023-08-03 "Treat `\Throwable` similar to `\Exception`": https://github.com/mage2pro/core/issues/311
# Failure report adapter wrapping an exception and its diagnostic context and root-cause backtrace.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure/Exception.php#L5-L55
class Exception(Failure):
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure/Exception.php#L51-L54
	# @used-by :meth:`Exception.i()`
	def __init__(self, e: DFE) -> None:
		self.__e = e
	# Return the developer message, stripping HTML tags when the message is marked as HTML.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure/Exception.php#L11-L14
	# @used-by :meth:`Df.Qa.Failure.Failure.report()`
	# @see :meth:`Df.Qa.Failure.Failure._main()`
	@override
	def _main(self) -> str:
		r = self.__e.messageD()
		return re.sub(r'<[^>]+>', '', r) if self.__e.isMessageHtml() else r
	# 2023-01-28 https://github.com/mage2pro/core/issues/178
	# Prepend the dumped exception context before the formatted stack trace.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure/Exception.php#L25
	# @used-by :meth:`Df.Qa.Failure.Failure.report()`
	# @see :meth:`Df.Qa.Failure.Failure._postface()`
	@override
	def _postface(self) -> str:
		ctx = self.__e.context()
		return self._sections(df_dump_ds(ctx) if ctx else '', super()._postface())
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure/Exception.php#L32
	# @used-by :meth:`Df.Qa.Failure.Failure._postface()`
	# @see :meth:`Df.Qa.Failure.Failure._stackLevel()`
	@override
	def _stackLevel(self) -> int:
		return self.__e.getStackLevelsCountToSkip()
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure/Exception.php#L40
	# @used-by :meth:`Df.Qa.Failure.Failure._postface()`
	# @see :meth:`Df.Qa.Failure.Failure._trace()`
	@override
	def _trace(self) -> list[dict[str, Any]]:
		return df_bt(df_xf(self.__e))
	# Wrap `t` into a Df\Core\Exception and construct a Failure\Exception reporter.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure/Exception.php#L54
	# @used-by :meth:`test_df_qa.TestDfQa.test_trace_and_failure()`
	@staticmethod
	def i(t: BaseException) -> Exception:
		return Exception(DFE.wrap(t))