# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.clean.filter import df_filter
from Df.Core.lib.array.map import df_map
from Df.Core.lib.array.unpack import df_args
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# @used-by :func:`df_clean_keys()`
# @used-by :func:`df_clean_r()`
def _in_strict(v: Any, targets: list[Any]) -> bool:
	return any((type(v) is type(t) and v == t for t in targets))
# @used-by :func:`dfa_remove_objects()`
def _is_custom_object(v: Any) -> bool:
	return (not isinstance(v, (str, int, float, bool, list, dict, tuple, set, bytes))) and None is not v
# 2015-02-07 Remove '', None, [], False (and optional extra values) non-recursively while preserving 0.
# 2017-02-13 Added `False` to the removal list.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/clean/main.php#L5-L94
# @used-by :func:`Df.Core.lib.reflection.text.cc.df_cc_class()`
# @used-by :func:`Df.Core.lib.text.concatenate.df_ccc()`
# @used-by :func:`Df.Core.lib.text.explode.df_explode_space()`
# @used-by :func:`Df.Qa.lib.dump.kv.df_kv()`
# @used-by :func:`Df.Qa.lib.dump.kv.table.df_kv_table()`
# @used-by :func:`dfa_remove_objects()`
# @used-by :meth:`Df.Qa.Failure.Failure._sections()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_assert_clean_and_filter()`
def df_clean(r: list[Any] | dict[Any, Any], *k: Any) -> list[Any] | dict[Any, Any]:
	return df_clean_r(r, [False, *df_args(list(k))], False)
# 2017-02-18 Filter out empty, None, or explicitly excluded keys from an associative dict.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/clean/main.php#L96-L117
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_assert_clean_and_filter()`
def df_clean_keys(a: dict[Any, Any], *remove: Any) -> dict[Any, Any]:
	from Df.Qa.lib.validation.assert_.array import df_assert_assoc
	df_assert_assoc(a)
	rem = ['', None, *df_args(list(remove))]
	return {k: v for k, v in a.items() if not _in_strict(k, rem)}
# 2023-07-20 Remove only None values, preserving empty strings, False, and 0.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/clean/main.php#L119-L125
# @used-by :func:`Df.Core.lib.array.select.ordered.dfa_select_ordered()`
# @used-by :func:`agent_tools.diagnostics.problem()`
# @used-by :func:`agent_tools.meta.blocks._build_journal_trace()`
# @used-by :func:`agent_tools.meta.blocks._build_turn_trace()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._execute_edit()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_assert_clean_and_filter()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_clean_null_and_unique_fast_delegation_to_df()`
def df_clean_null(r: list[Any] | dict[Any, Any]) -> list[Any] | dict[Any, Any]:
	return {k: v for k, v in r.items() if None is not v} if isinstance(r, dict) else [v for v in r if None is not v]
# 2020-02-05 Recursively remove '', None, [], {} (does not remove False unless passed in `k`).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/clean/main.php#L127-L146
# @used-by :func:`df_clean()`
# @used-by :meth:`Df.Core.Html.Tag.Tag.__init__()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_assert_clean_and_filter()`
def df_clean_r(r: list[Any] | dict[Any, Any], k: list[Any] | None=None, req: bool=True) -> list[Any] | dict[Any, Any]:
	rem = [*(k or ()), '', None, [], {}]
	cur = df_map(r, lambda v: df_clean_r(v, rem) if isinstance(v, (list, dict)) else v) if req else r
	return df_filter(cur, lambda v: not _in_strict(v, rem))
# 2018-08-11 Recursively strip object instances from nested dicts/lists, optionally cleaning empty containers.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/clean/main.php#L158-L172
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_assert_clean_and_filter()`
def dfa_remove_objects(v: list[Any] | dict[Any, Any], clean: bool=True) -> list[Any] | dict[Any, Any]:
	if isinstance(v, dict):
		r: list[Any] | dict[Any, Any] = {k: (dfa_remove_objects(val, clean) if isinstance(val, (list, dict)) else val) for k, val in v.items() if not _is_custom_object(val)}
	else:
		r = [dfa_remove_objects(val, clean) if isinstance(val, (list, dict)) else val for val in v if not _is_custom_object(val)]
	return df_clean(r) if clean else r
