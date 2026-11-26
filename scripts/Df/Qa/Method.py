# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import builtins
from Df.Core.lib.reflection.text.cts import df_cts
from Df.Core.lib.text.n.cc import df_cc_n
from Df.Qa.Trace.Frame import Frame
from Df.Qa.lib.bt.main import df_bt
from Df.Qa.lib.validation.error import df_error
from Df.Zf.Validate import Validate
from Df.Zf.Validate.StringT.Iso2 import Iso2
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Method parameter, variable, and result validation error reporter.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/Method.php#L8-L101
class Method:
	# 2017-01-12
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Method.php#L70
	NES = 'A non-empty string is required, but got an empty one.'
	# Construct a Frame at offset `o + 2` to capture the method that called the validator helper.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Method.php#L79
	# @used-by :meth:`Method.raiseErrorParam()`
	# @used-by :meth:`Method.raiseErrorResult()`
	# @used-by :meth:`Method.raiseErrorVariable()`
	@staticmethod
	def __caller(o: int) -> Frame:
		bt = df_bt(0, 3 + o)
		idx = 2 + o
		return Frame.i(bt[idx] if idx < len(bt) else {})
	# 2015-01-28 Raise diagnostic validation error via df_error().
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Method.php#L90
	# @used-by :meth:`Method.raiseErrorParam()`
	# @used-by :meth:`Method.raiseErrorResult()`
	# @used-by :meth:`Method.raiseErrorVariable()`
	@staticmethod
	def __throwException(message: str, sl: int=0) -> None:
		df_error(builtins.Exception(message, sl + 1))
	# Validate parameter value `v` with `vd`, raising a parameter error if invalid.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Method.php#L98-L100
	# @used-by :meth:`Method.assertParamIsIso2()`
	@staticmethod
	def __vp(vd: Validate, v: Any, ord_: int, sl: int=1) -> Any:
		if vd.isValid(v):
			r = v
		else:
			Method.raiseErrorParam(df_cts(vd), list(vd.getMessages().values()), ord_, sl + 1)
			r = v
		return r
	# Validate that method parameter at `ord_` is an ISO 3166-1 alpha-2 country code.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Method.php#L13
	# @used-by :func:`Df.Qa.lib.validation.param.df_param_iso2()`
	@staticmethod
	def assertParamIsIso2(v: str, ord_: int, sl: int=0) -> str:
		return str(Method.__vp(Iso2.s(), v, ord_, sl + 1))
	# Raise a formatted diagnostic exception for an invalid method argument.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Method.php#L20-L33
	# @used-by :func:`Df.Qa.lib.validation.param.df_param_sne()`
	# @used-by :meth:`Method.__vp()`
	@staticmethod
	def raiseErrorParam(method: str, messages: list[str], ord_: int, sl: int=1) -> None:
		frame = Method.__caller(sl)
		name = frame.methodParameter(ord_).name if None is not frame.methodR() else 'unknown'
		messages_s = df_cc_n(messages)
		Method.__throwException(f'[{frame.method()}]\nThe argument «{name}» is rejected by the «{method}» validator.\nThe diagnostic message:\n{messages_s}\n\n', sl)
	# Raise a formatted diagnostic exception for an invalid method return value.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Method.php#L40-L48
	# @used-by :func:`Df.Qa.lib.validation.result.df_result_s()`
	# @used-by :func:`Df.Qa.lib.validation.result.df_result_sne()`
	@staticmethod
	def raiseErrorResult(vd: str, messages: list[str], sl: int=1) -> None:
		messages_s = df_cc_n(messages)
		method = Method.__caller(sl).method()
		Method.__throwException(f'[{method}]\nA result of this method is rejected by the «{vd}» validator.\nThe diagnostic message:\n{messages_s}\n\n', sl)
	# Raise a formatted diagnostic exception for an invalid local variable value.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Method.php#L54-L62
	# @used-by :func:`Df.Qa.lib.validation.assert_.other.df_assert_sne()`
	@staticmethod
	def raiseErrorVariable(vd: str, messages: list[str], sl: int=1) -> None:
		messages_s = df_cc_n(messages)
		method = Method.__caller(sl).method()
		Method.__throwException(f'[{method}]\nThe validator «{vd}» has catched a variable with an invalid value.\nThe diagnostic message:\n{messages_s}\n\n', sl)