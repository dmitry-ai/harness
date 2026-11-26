# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.assert_ import dfa_has_keys
from Df.Core.lib.array.select import dfa
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2023-08-05 Return the class name recorded in backtrace entry `e`, or ''.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/entry.php#L8
# @used-by :meth:`test_df_qa.TestDfQa.test_bt_helpers()`
def df_bt_entry_class(e: dict[str, Any]) -> str:
	return str(dfa(e, 'class', ''))
# 2023-07-26 "Implement `df_bt_entry_file()`": https://github.com/mage2pro/core/issues/279
# 2023-01-28 The 'file' key can be absent in synthetic or dynamic stack frames: https://github.com/mage2pro/core/issues/186
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/entry.php#L21-L40
# @used-by :meth:`Df.Qa.Trace.Trace.__init__()`
# @used-by :meth:`test_df_qa.TestDfQa.test_bt_helpers()`
def df_bt_entry_file(e: dict[str, Any]) -> str:
	return str(dfa(e, 'file', ''))
# 2023-07-28 Return the function name recorded in backtrace entry `e`, or ''.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/entry.php#L48
# @used-by :func:`Df.Qa.lib.bt.filter.df_bt_filter_head()`
# @used-by :meth:`test_df_qa.TestDfQa.test_bt_helpers()`
def df_bt_entry_func(e: dict[str, Any]) -> str:
	return str(dfa(e, 'function', ''))
# 2023-07-26 Return True iff backtrace entry `e` represents a class method call.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/entry.php#L55
# @used-by :func:`Df.Core.lib.caller.other.df_caller_m()`
# @used-by :meth:`test_df_qa.TestDfQa.test_bt_helpers()`
def df_bt_entry_is_method(e: dict[str, Any]) -> bool:
	return dfa_has_keys(e, ['class', 'function'])
# 2023-07-27 Return the line number recorded in backtrace entry `e`, or 0.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/entry.php#L70
# @used-by :meth:`test_df_qa.TestDfQa.test_bt_helpers()`
def df_bt_entry_line(e: dict[str, Any]) -> int:
	return int(dfa(e, 'line', 0) or 0)