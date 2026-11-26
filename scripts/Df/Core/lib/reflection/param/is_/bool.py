# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import inspect
from Df.Core.lib.reflection.param.type import dfr_param_type
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2024-09-21 Return True iff parameter `p` is annotated as `bool`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/param/is/bool.php#L4-L8
# @used-by :func:`Df.Core.lib.lang.call._bind_named_param()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def dfr_param_is_bool(p: inspect.Parameter) -> bool:
	return 'bool' == dfr_param_type(p)
