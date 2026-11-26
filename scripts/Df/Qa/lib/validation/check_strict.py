# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# Return True iff `v` is an `int` instance and not a `bool`.
# @used-by :func:`agent_tools.addon_observability._runtime_issues_from_data()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_text_source_and_strict_validation_helpers()`
def df_is_int_strict(v: Any) -> bool:
	return isinstance(v, int) and (not isinstance(v, bool))
# Return True iff `v` is a string with non-whitespace characters.
# @used-by :func:`agent_tools.review_alignment._nonempty()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_text_source_and_strict_validation_helpers()`
def df_is_sne(v: Any) -> bool:
	return isinstance(v, str) and bool(v.strip())