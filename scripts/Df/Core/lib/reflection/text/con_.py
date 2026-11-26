# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.R.ConT import ConT
from Df.Core.lib.reflection.text.other import df_class_replace_last, df_cld
from Df.Core.lib.text.concatenate import df_cc
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2016-10-26 Resolve child class `<c><sep><suf>` via convention-over-configuration.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/con_.php#L28-L37
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_con_child(c: Any, suf: str | list[str], df_def: str='', throw: bool=True) -> str | None:
	return ConT.generic(lambda cls_s, sfx: df_cc(df_cld(cls_s), cls_s, sfx), c, suf, df_def, throw)
# 2016-07-10 Resolve sibling class sharing `c`'s namespace with final segment replaced by `nameLast`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/reflection/text/con_.php#L175-L199
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
def df_con_sibling(c: Any, nameLast: str | list[str], df_def: str='', throw: bool=True) -> str | None:
	return ConT.generic(lambda cls_s, last: df_class_replace_last(cls_s, last), c, nameLast, df_def, throw)
