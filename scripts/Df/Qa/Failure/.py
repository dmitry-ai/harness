# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from Df.Core.lib.array.clean.main import df_clean
from Df.Core.lib.cache.dfc import dfc
from Df.Core.lib.text.trim import df_trim
from Df.Qa.Trace import Trace
from Df.Qa.Trace.Formatter import Formatter
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Abstract failure report formatter assembling preface, main message, and formatted stack trace sections.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure.php#L8-L61
class Failure(ABC):
	# Return the primary diagnostic message section.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure.php#L14
	# @used-by :meth:`Failure.report()`
	@abstractmethod
	def _main(self) -> str:
		raise NotImplementedError
	# Format the postface section containing the filtered stack trace.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure.php#L38
	# @used-by :meth:`Exception.Exception._postface()`
	# @used-by :meth:`Failure.report()`
	# @uses :meth:`Df.Qa.Failure.Exception.Exception._stackLevel()`
	# @uses :meth:`Df.Qa.Failure.Exception.Exception._trace()`
	def _postface(self) -> str:
		return Formatter.p(Trace(self._trace()[self._stackLevel():]))
	# Return an optional preface section placed above the main message.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure.php#L44
	# @used-by :meth:`Failure.report()`
	def _preface(self) -> str:
		return ''
	# Join non-empty trimmed report sections with a 36-asterisk horizontal divider.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure.php#L50-L53
	# @used-by :meth:`Exception.Exception._postface()`
	# @used-by :meth:`Failure.report()`
	def _sections(self, *a: str) -> str:
		sep = '\n' + ('*' * 36) + '\n'
		return sep.join((str(x) for x in df_clean(df_trim(list(a)))))
	# Return the number of leading stack frames to omit from the trace.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure.php#L60
	# @used-by :meth:`Failure._postface()`
	def _stackLevel(self) -> int:
		return 0
	# Return the raw backtrace frame entries for this failure.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure.php#L23
	# @used-by :meth:`Failure._postface()`
	@abstractmethod
	def _trace(self) -> list[dict[str, Any]]:
		raise NotImplementedError
	# Build and cache the complete multi-section diagnostic report.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Failure.php#L29-L31
	# @used-by :meth:`test_df_qa.TestDfQa.test_trace_and_failure()`
	# @uses :meth:`Df.Qa.Failure.Exception.Exception._main()`
	# @uses :meth:`Df.Qa.Failure.Exception.Exception._postface()`
	def report(self) -> str:
		return str(dfc(self, lambda: self._sections(self._preface(), self._main(), self._postface())))