# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.reflection.text.explode import df_explode_class_lc, df_explode_class_lc_camel
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-08-14 Convert an object, type, or class name string into a normalized class name separated by `del_`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/cts.php#L2-L18
# @used-by :func:`Df.Core.lib.reflection.text.cc.df_cc_method()`
# @used-by :func:`Df.Core.lib.reflection.text.explode.df_explode_class()`
# @used-by :func:`Df.Core.lib.reflection.text.explode.df_explode_class_camel()`
# @used-by :func:`Df.Core.lib.reflection.text.other.df_cld()`
# @used-by :func:`Df.Qa.lib.bt.main._mro_class()`
# @used-by :func:`Df.Qa.lib.dump.type.df_type()`
# @used-by :func:`Df.Qa.lib.validation.assert_.class_._check_ar()`
# @used-by :func:`Df.Qa.lib.validation.error.df_abstract()`
# @used-by :meth:`Df.Core.R.ConT.ConT.generic()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpObject()`
# @used-by :meth:`Df.Qa.Method.Method.__vp()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_cts(c: Any, del_: str='\\') -> str:
	if isinstance(c, str):
		raw = c.lstrip('\\')
	elif isinstance(c, type):
		raw = f'{c.__module__}.{c.__qualname__}'
	else:
		raw = f'{type(c).__module__}.{type(c).__qualname__}'
	return raw if '\\' == del_ else raw.replace('\\', del_)
# 2016-01-29 Join lowercased-first class segments using `del_`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/cts.php#L20-L24
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_cts_lc(c: str, del_: str) -> str:
	return del_.join(df_explode_class_lc(c))
# 2016-04-11 Split CamelCase class segments, lowercase first letters, and join with `del_`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/cts.php#L26-L35
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_reflection_text()`
def df_cts_lc_camel(c: Any, del_: str) -> str:
	return del_.join(df_explode_class_lc_camel(c))
