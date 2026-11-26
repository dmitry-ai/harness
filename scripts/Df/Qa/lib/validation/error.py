# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.Exception import Exception as DFE
from Df.Core.lib.array.first import df_first
from Df.Core.lib.array.is_ import df_is_assoc
from Df.Core.lib.array.part import df_tail
from Df.Core.lib.array.select import dfa
from Df.Core.lib.caller.other import df_caller_c, df_caller_mh, df_caller_ml
from Df.Core.lib.empty import df_eta
from Df.Core.lib.reflection.text.cts import df_cts
from Df.Core.lib.text.format import df_format
from Df.Core.lib.text.n.cc import df_cc_n
from Df.Qa.lib.exception import df_is_th
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Parse variadic df_error_create arguments into (primary, has_context, context_dict).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/error.php#L204-L218
# @used-by :func:`df_error_create()`
def _parse_error_args(a: list[Any]) -> tuple[Any, bool, dict[str, Any]]:
	from Df.Qa.lib.validation.assert_.numeric_comparison import df_assert_eq
	a0 = dfa(a, 0)
	tail = df_tail(a)
	tail_c = len(tail)
	if not df_is_assoc(a0):
		a1 = df_first(tail)
		has_ctx = 2 > tail_c and (None is a1 or df_is_assoc(a1))
	else:
		df_assert_eq(0, tail_c)
		a0, a1, has_ctx = None, a0, True
	ctx_raw = df_eta(a1) if has_ctx else {}
	return (a0, has_ctx, ctx_raw if isinstance(ctx_raw, dict) else {})
# 2016-08-27 Raise an HTML error stating that the abstract method must be redefined by `caller`.
# 2017-11-19 https://github.com/mage2pro/core/issues/56
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/error.php#L15-L28
# @used-by :meth:`test_df_qa._AbstractBase.doWork()`
def df_abstract(caller: Any) -> None:
	caller_c = df_cts(caller)
	if caller_c == df_caller_c():
		df_error_html(f'The {caller_c} class is abstract: you should redefine at least the %s method.', df_caller_ml())
	df_error_html(f'The method %s should be redefined by the <b>{caller_c}</b> class.', df_caller_mh())
# 2024-05-22 "Implement `Df\Core\Exception::throw_()`": https://github.com/mage2pro/core/issues/386
# Construct and throw a Df\Core\Exception via df_error_create().
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/error.php#L150-L154
# @used-by :func:`Df.Core.lib.array.assert_.dfa_assert_keys()`
# @used-by :func:`Df.Core.lib.array.other.af.dfaf()`
# @used-by :func:`Df.Core.lib.array.select.strict.dfa_strict()`
# @used-by :func:`Df.Core.lib.cache.dfc._caller_method_key()`
# @used-by :func:`Df.Core.lib.json.df_json_decode()`
# @used-by :func:`Df.Core.lib.lang.call._bind_named_param()`
# @used-by :func:`Df.Core.lib.lang.call.df_call()`
# @used-by :func:`Df.Core.lib.lang.call.parent.df_call_parent()`
# @used-by :func:`Df.Core.lib.lang.prop.native.dfr_prop()`
# @used-by :func:`Df.Core.lib.lang.try_.df_try()`
# @used-by :func:`Df.Core.lib.text.format.df_sprintf_strict()`
# @used-by :func:`Df.Core.lib.text.prepend_append.pad._pad_counts()`
# @used-by :func:`Df.Qa.lib.validation.assert_.array.df_assert_array()`
# @used-by :func:`Df.Qa.lib.validation.assert_.array.df_assert_assoc()`
# @used-by :func:`Df.Qa.lib.validation.assert_.array.df_assert_count()`
# @used-by :func:`Df.Qa.lib.validation.assert_.array.df_assert_in()`
# @used-by :func:`Df.Qa.lib.validation.assert_.bool.df_bool()`
# @used-by :func:`Df.Qa.lib.validation.assert_.class_._check_ar()`
# @used-by :func:`Df.Qa.lib.validation.assert_.class_.df_assert_class_exists()`
# @used-by :func:`Df.Qa.lib.validation.assert_.df_assert()`
# @used-by :func:`Df.Qa.lib.validation.assert_.float._float_str()`
# @used-by :func:`Df.Qa.lib.validation.assert_.int.df_int()`
# @used-by :func:`Df.Qa.lib.validation.assert_.numeric_comparison.df_assert_between()`
# @used-by :func:`Df.Qa.lib.validation.assert_.numeric_comparison.df_assert_eq()`
# @used-by :func:`Df.Qa.lib.validation.assert_.numeric_comparison.df_assert_ge()`
# @used-by :func:`Df.Qa.lib.validation.assert_.numeric_comparison.df_assert_gt()`
# @used-by :func:`Df.Qa.lib.validation.assert_.numeric_comparison.df_assert_gt0()`
# @used-by :func:`Df.Qa.lib.validation.assert_.numeric_comparison.df_assert_le()`
# @used-by :func:`Df.Qa.lib.validation.assert_.numeric_comparison.df_assert_lt()`
# @used-by :func:`Df.Qa.lib.validation.assert_.numeric_comparison.df_assert_ne()`
# @used-by :func:`Df.Qa.lib.validation.assert_.other.df_assert_nef()`
# @used-by :func:`df_not_implemented()`
# @used-by :meth:`Df.Core.Helper.Text.Text.quote()`
# @used-by :meth:`Df.Core.R.ConT.ConT.__resolve()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.__throwInternalError()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.__throwNotMatch()`
# @used-by :meth:`Df.Qa.Method.Method.__throwException()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.__getParam()`
# @used-by :meth:`test_df_qa.TestDfQa.test_error_helpers()`
def df_error(*a: Any) -> None:
	df_error_create(*a).throw_()
# 2016-07-31 Construct a Df\Core\Exception with optional formatted message, wrapped cause, and context dict.
# 2024-05-20 "Provide an ability to specify a context for a `Df\Core\Exception` instance":
# https://github.com/mage2pro/core/issues/375
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/error.php#L203-L237
# @used-by :func:`df_error()`
# @used-by :func:`df_error_html()`
# @used-by :meth:`test_df_qa.TestDfQa.test_error_helpers()`
def df_error_create(*a: Any) -> DFE:
	from Df.Qa.lib.validation.assert_ import df_assert
	args = list(a)
	a0, has_ctx, ctx = _parse_error_args(args)
	if df_is_th(a0):
		df_assert(has_ctx)
		r = DFE.wrap(a0)
	else:
		if isinstance(a0, list):
			a0 = df_cc_n(a0)
		if isinstance(a0, str) and (not has_ctx):
			a0 = df_format(args)
		r = DFE(a0)
	if has_ctx and ctx:
		r.context(ctx)
	return r
# 2016-07-31 Raise a Df\Core\Exception whose message is marked as HTML.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/error.php#L248
# @used-by :func:`df_abstract()`
# @used-by :func:`df_should_not_be_here()`
# @used-by :meth:`test_df_qa.TestDfQa.test_error_helpers()`
def df_error_html(*a: str) -> None:
	df_error_create(*a).markMessageAsHtml().throw_()
# 2016-07-27 Raise a Df\Core\Exception stating that method `m` is not implemented yet.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/error.php#L256
# @used-by :meth:`test_df_qa.TestDfQa.test_error_helpers()`
def df_not_implemented(m: str) -> None:
	df_error(f'The method «{m}» is not implemented yet.')
# Raise an HTML Df\Core\Exception indicating that the calling method is forbidden.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/error.php#L274
# @used-by :meth:`test_df_qa._SampleService.forbidden()`
def df_should_not_be_here() -> None:
	df_error_html('The method %s is not allowed to call.', df_caller_mh())