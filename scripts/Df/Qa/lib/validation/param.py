# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.empty import df_es
from Df.Qa.Method import Method as Q
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Assert that method parameter at index `ord_` is an ISO 3166-1 alpha-2 country code.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/param.php#L9
# @used-by :meth:`test_df_qa._SampleService.checkIso()`
def df_param_iso2(v: str, ord_: int, sl: int=0) -> str:
	return Q.assertParamIsIso2(v, ord_, sl + 1)
# Assert that method parameter at index `ord_` is a non-empty string (preserving `'0'`).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/param.php#L25-L32
# @used-by :func:`Df.Core.lib.date.df_date_from_db()`
# @used-by :func:`Df.Core.lib.reflection.text.check.df_is_abstract()`
# @used-by :func:`Df.Qa.lib.validation.assert_.class_.df_assert_class_exists()`
# @used-by :meth:`Df.Core.Html.Tag.Tag.__formatAttr()`
# @used-by :meth:`test_df_qa._SampleService.checkSne()`
# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_334_method_throws_dfe_with_stack_levels()`
def df_param_sne(v: str, ord_: int, sl: int=0) -> str:
	sl += 1
	if df_es(v):
		Q.raiseErrorParam('df_param_sne', [Q.NES], ord_, sl)
	return v