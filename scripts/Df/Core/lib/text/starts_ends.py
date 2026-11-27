# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.array.find import df_find
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# Return True iff `haystack` ends with `n` (or any suffix in list `n`); empty needle returns True.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/starts-ends.php#L2-L34
# @used-by :func:`Df.Core.lib.text.prepend_append.df_append()`
# @used-by :meth:`Df.Core.Text.Marker.Marker.marked()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.__isClosure()`
# @used-by :meth:`Df.Zf.Validate.StringT.FloatT.FloatT.isValid()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_ends_with(haystack: str, n: str | list[str]) -> bool:
	if isinstance(n, list):
		r = None is not df_find(n, df_ends_with, [], [haystack])
	else:
		r = haystack.endswith(n)
	return r
# Return True iff `haystack` starts with `n` (or any prefix in list `n`); empty needle returns True.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/starts-ends.php#L36-L93
# @used-by :func:`Df.Core.lib.text.prepend_append.df_prepend()`
# @used-by :func:`Df.Harness.lib.issue.dfh_is_excluded_meta_rel()`
# @used-by :func:`agent_tools.issue_first_gate._is_excluded_meta_rel()`
# @used-by :meth:`Df.Core.Text.Marker.Marker.marked()`
# @used-by :meth:`Df.Qa.Trace.Trace.__init__()`
# @used-by :meth:`Df.Zf.Validate.StringT.IntT.IntT.isValid()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_first_last_starts_with_and_is_windows_delegation_to_df()`
def df_starts_with(haystack: str, n: str | list[str]) -> bool:
	if isinstance(n, list):
		r = None is not df_find(n, df_starts_with, [], [haystack])
	else:
		r = haystack.startswith(n)
	return r
