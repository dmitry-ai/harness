# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import re
from Df.Core.lib.lang.call.a import df_call_a
from Df.Core.lib.text.transform import df_lcfirst, df_ucfirst
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2021-12-20 Convert CamelCase string(s) to snake_case.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/camel.php#L2-L12
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_camel_to_underscore(*a: Any) -> str | list[str]:
	return df_call_a(lambda s: '_'.join(df_lcfirst(df_explode_camel(s))), list(a))
# Split CamelCase string(s) on lowercase-to-uppercase/digit boundaries (e.g., 'Dynamics365' => ['Dynamics', '365']).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/camel.php#L14-L59
# @used-by :func:`Df.Core.lib.reflection.text.explode.df_explode_class_camel()`
# @used-by :func:`df_camel_to_underscore()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_explode_camel(*a: Any) -> list[Any]:
	return df_call_a(lambda n: re.split(r'(?<=[a-z])(?=[A-Z0-9])', n), list(a))
# 2016-08-10 Convert underscore-separated string(s) to PascalCase (e.g., 'REFUND_ISSUED' => 'RefundIssued').
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/camel.php#L61-L73
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_underscore_to_camel(*a: Any) -> str | list[str]:
	return df_call_a(lambda s: ''.join(df_ucfirst(s.lower().split('_'))), list(a))
