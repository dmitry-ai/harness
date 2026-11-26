# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.lang.type.stringable import df_is_stringable
from Df.Qa.lib.validation.assert_ import df_assert
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2024-09-22 Assert that `v` is stringable, raising df_error(*a) otherwise.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/validation/assert/stringable.php#L11
# @used-by :func:`Df.Core.lib.lang.type.conversion.string.df_string()`
# @used-by :meth:`test_df_qa.TestDfQa.test_assert_class_and_other()`
# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_336_df_assert_stringable_returns_value()`
def df_assert_stringable(v: Any, *a: Any) -> Any:
	# 2026-11-26 "Fix df_assert_stringable returning bool instead of input value": https://github.com/dmitry-ai/harness/issues/336
	# Upstream defect: https://github.com/mage2pro/core/issues/479
	df_assert(df_is_stringable(v), *a)
	return v