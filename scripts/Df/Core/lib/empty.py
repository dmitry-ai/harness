# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# Return True iff `v` is strictly the empty string.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/empty.php#L2-L24
# @used-by :func:`Df.Core.lib.text.format.df_desc()`
# @used-by :func:`Df.Core.lib.text.n.prepend.df_n_prepend()`
# @used-by :func:`Df.Qa.lib.validation.assert_.other.df_assert_sne()`
# @used-by :func:`Df.Qa.lib.validation.param.df_param_sne()`
# @used-by :func:`Df.Qa.lib.validation.result.df_result_sne()`
# @used-by :func:`df_est()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def df_es(v: Any) -> bool:
	return '' == v
# 2024-04-14 Return True iff trimming `v` yields the empty string.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/empty.php#L26-L31
# @used-by :func:`Df.Core.lib.html.df_tag_if_ne()`
def df_est(v: Any) -> bool:
	from Df.Core.lib.text.trim import df_trim
	return df_es(df_trim(v))
# 2017-04-26 Convert an empty non-array value to an empty list/dict, asserting emptiness.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/empty.php#L33-L73
# @used-by :func:`Df.Core.lib.caller.entry.df_caller_entry()`
# @used-by :func:`Df.Qa.lib.validation.error._parse_error_args()`
def df_eta(v: Any) -> list[Any] | dict[Any, Any]:
	r = v
	if not isinstance(r, (list, dict)):
		from Df.Qa.lib.validation.assert_ import df_assert
		df_assert(not r)
		r = []
	return r
# 2020-01-29 Convert any falsy value to None.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/empty.php#L75-L88
# @used-by :func:`Df.Core.lib.array.other.chop.dfa_chop()`
# @used-by :func:`Df.Core.lib.array.part.df_slice()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def df_etn(v: Any) -> Any:
	return v if v else None
# 2023-07-26 "Implement `df_ets()`": https://github.com/mage2pro/core/issues/280
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/empty.php#L90-L97
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def df_ets(v: Any) -> Any:
	return v if v else ''
# 2024-05-16 "Implement `df_fnes()`": https://github.com/mage2pro/core/issues/374
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/empty.php#L99-L103
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def df_fnes(v: Any) -> bool:
	return None is v or '' == v or False is v
# Convert strict False to None.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/empty.php#L105-L112
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def df_ftn(v: Any) -> Any:
	return None if False is v else v
# 2022-10-15 Convert strict False to an empty string.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/empty.php#L114-L122
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def df_fts(v: Any) -> Any:
	return '' if False is v else v
# 2016-08-04 Return True iff `v` is None or the empty string.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/empty.php#L124-L150
# @used-by :func:`Df.Core.lib.array.deep.dfa_deep()`
# @used-by :func:`Df.Core.lib.array.other.tr.dftr()`
# @used-by :func:`Df.Core.lib.array.select.dfa()`
# @used-by :func:`Df.Core.lib.array.select.strict.dfa_strict()`
# @used-by :func:`Df.Core.lib.json.df_json_decode()`
# @used-by :func:`Df.Qa.lib.validation.assert_.float.df_float()`
# @used-by :func:`Df.Qa.lib.validation.assert_.int.df_int()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def df_nes(v: Any) -> bool:
	return None is v or '' == v
# Convert None to an empty string, leaving other values untouched.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/empty.php#L152-L180
# @used-by :func:`Df.Core.lib.text.trim.df_trim()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.__class_()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.__function_()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.file()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_empty_float_and_math()`
def df_nts(v: Any) -> Any:
	return v if None is not v else ''
