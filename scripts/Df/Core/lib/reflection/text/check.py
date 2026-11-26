# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import importlib
import inspect
from Df.Core.lib.reflection.text.part import df_class_f
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# @used-by :func:`Df.Core.lib.reflection.text.other.df_class_file()`
# @used-by :func:`Df.Core.lib.reflection.text.other.df_const()`
# @used-by :func:`Df.Qa.lib.validation.assert_.class_._matches_class()`
# @used-by :func:`df_class_exists()`
# @used-by :func:`df_is_abstract()`
# @used-by :meth:`Df.Qa.Trace.Frame.Frame.__resolveSig()`
def _load_class(c: str | type) -> type | None:
	if isinstance(c, type):
		r: type | None = c
	else:
		dotted = c.replace('\\', '.').lstrip('.')
		mod_name, _, attr = dotted.rpartition('.')
		r = None
		if mod_name and attr:
			try:
				obj = getattr(importlib.import_module(mod_name), attr, None)
				r = obj if isinstance(obj, type) else None
			except Exception:
				r = None
	return r
# 2016-05-06 Return True iff class name `c` resolves to a Python type.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/check.php#L4-L19
# @used-by :func:`Df.Qa.lib.validation.assert_.class_.df_assert_class_exists()`
# @used-by :meth:`Df.Core.R.ConT.ConT.__resolve()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_class_exists(c: str | type) -> bool:
	return None is not _load_class(c)
# 2016-01-01 Return True iff `c` belongs to the Df/Dfe/Dfr namespace family.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/check.php#L21-L29
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_class_my(c: Any) -> bool:
	return df_class_f(c) in ('Df', 'Dfe', 'Dfr')
# 2017-01-11 Return True iff class `c` is abstract (has unimplemented abstract methods).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/check.php#L31-L37
# @used-by :meth:`Df.Core.R.ConT.ConT.__resolve()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_is_abstract(c: str | type) -> bool:
	if isinstance(c, str):
		from Df.Qa.lib.validation.param import df_param_sne
		df_param_sne(c, 0)
	cls = _load_class(c)
	return bool(None is not cls and inspect.isabstract(cls))
