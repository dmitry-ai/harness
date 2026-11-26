# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Iterable
from Df.Core.lib.array.other.ita import df_ita
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# Return the first value of an iterable/dict, or None if empty (preserving falsy elements like False).
# 2024-06-18 "`df_first()` should accept `iterable` as its argument": https://github.com/mage2pro/core/issues/429
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/first.php#L2-L36
# @used-by :func:`Df.Core.lib.array.other.group._group_by_key()`
# @used-by :func:`Df.Core.lib.array.select.try_.dfa_try()`
# @used-by :func:`Df.Core.lib.caller.entry.df_caller_entry()`
# @used-by :func:`Df.Core.lib.caller.other.df_caller_c()`
# @used-by :func:`Df.Core.lib.option.df_a_to_options()`
# @used-by :func:`Df.Core.lib.reflection.text.part.df_class_f()`
# @used-by :func:`Df.Core.lib.text.format.df_sprintf()`
# @used-by :func:`Df.Core.lib.text.format.df_sprintf_strict()`
# @used-by :func:`Df.Qa.lib.diagnostics.df_webserver()`
# @used-by :func:`Df.Qa.lib.validation.error._parse_error_args()`
# @used-by :func:`agent_tools.cleanup_audit._extract_removed_record()`
# @used-by :func:`agent_tools.issues.repo_locator.origin_repo_slug()`
# @used-by :func:`agent_tools.perf.timesheet_ag._ag_timestamps()`
# @used-by :func:`agent_tools.repo_tags.pick_preferred_tag()`
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.find_matching_recipes()`
# @used-by :meth:`Df.Harness.Tdd.OutcomeParser.OutcomeParser.__extract_bg_meta()`
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner._apply_removal()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_first_last_starts_with_and_is_windows_delegation_to_df()`
def df_first(i: Iterable[Any]) -> Any:
	a = df_ita(i)
	if not a:
		r: Any = None
	else:
		r = next(iter(a.values())) if isinstance(a, dict) else a[0]
	return r
# 2019-08-21 Return the first key of a dict (or 0 for a non-empty list), or None if empty.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/first.php#L38-L51
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def df_first_key(a: dict[Any, Any] | list[Any]) -> Any:
	if not a:
		r: Any = None
	else:
		r = next(iter(a.keys())) if isinstance(a, dict) else 0
	return r
# Return the last value of an iterable/dict, or None if empty.
# 2024-06-18 "`df_last()` should accept `iterable` as its argument": https://github.com/mage2pro/core/issues/428
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/first.php#L53-L96
# @used-by :func:`Df.Core.lib.reflection.text.part.df_class_l()`
# @used-by :func:`agent_tools.hook_runtime._slice_after_last_user()`
# @used-by :func:`agent_tools.perf.timesheet_ag._ag_timestamps()`
# @used-by :func:`agent_tools.platforms.clarifications._find_generic_output()`
# @used-by :func:`agent_tools.platforms.clarifications.build_segment_metadata()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.__execMatch()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_first_last_starts_with_and_is_windows_delegation_to_df()`
def df_last(i: Iterable[Any]) -> Any:
	a = df_ita(i)
	if not a:
		r: Any = None
	else:
		r = list(a.values())[-1] if isinstance(a, dict) else a[-1]
	return r
