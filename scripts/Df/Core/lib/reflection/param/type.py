# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import inspect
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2024-09-21 Return the parameter type annotation name, or '' when unannotated.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/param/type.php#L5-L12
# @used-by :func:`Df.Core.lib.reflection.param.is_.bool.dfr_param_is_bool()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def dfr_param_type(p: inspect.Parameter) -> str:
	ann = p.annotation
	if inspect.Parameter.empty is ann:
		r = ''
	elif isinstance(ann, type):
		r = ann.__name__
	else:
		r = str(ann)
	return r
