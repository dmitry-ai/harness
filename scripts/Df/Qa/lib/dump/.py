# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.json import df_json_dont_sort
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Dump any value via a fresh Dumper instance (not a singleton, to track per-call recursion cycles).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/dump/.php#L38
# @used-by :func:`Df.Core.lib.array.assert_.dfa_assert_keys()`
# @used-by :func:`Df.Core.lib.lang.type.conversion.string.df_string()`
# @used-by :func:`Df.Core.lib.text.format.df_sprintf_strict()`
# @used-by :func:`Df.Qa.lib.validation.assert_.bool.df_bool()`
# @used-by :func:`Df.Qa.lib.validation.assert_.numeric_comparison.df_assert_eq()`
# @used-by :func:`df_dump_ds()`
# @used-by :func:`kv.df_kv()`
# @used-by :func:`kv.table.df_kv_table()`
# @used-by :func:`type.df_type()`
# @used-by :meth:`Df.Zf.Validate.Validate.message()`
# @used-by :meth:`test_df_qa.TestDfQa.test_dump_and_dumper()`
# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_336_df_assert_stringable_returns_value()`
def df_dump(v: Any) -> str:
	from Df.Qa.Dumper import Dumper
	return Dumper.i().dump(v)
# 2023-08-04 Dump `v` without sorting JSON keys.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/dump/.php#L45
# @used-by :meth:`Df.Qa.Failure.Exception.Exception._postface()`
# @used-by :meth:`test_df_qa.TestDfQa.test_dump_and_dumper()`
def df_dump_ds(v: Any) -> str:
	return str(df_json_dont_sort(lambda: df_dump(v)))