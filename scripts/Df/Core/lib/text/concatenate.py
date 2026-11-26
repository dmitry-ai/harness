# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.clean.main import df_clean
from Df.Core.lib.array.other.flatten import dfa_flatten
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2016-10-17 Concatenate flattened arguments without separator.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/concatenate.php#L2-L8
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_c(*a: Any) -> str:
	return ''.join((str(x) for x in dfa_flatten(list(a))))
# Concatenate flattened arguments using `glue` (preserving empty entries).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/concatenate.php#L10-L19
# @used-by :func:`Df.Core.lib.js.window_data.df_js_data()`
# @used-by :func:`Df.Core.lib.reflection.text.con_.df_con_child()`
# @used-by :meth:`Df.Qa.Trace.Formatter.Formatter.__format()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_cc(glue: str, *a: Any) -> str:
	return glue.join((str(x) for x in dfa_flatten(list(a))))
# 2016-08-13 Concatenate non-empty flattened arguments with `<br>`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/concatenate.php#L21-L30
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_cc_br(*a: Any) -> str:
	return df_ccc('<br>', dfa_flatten(list(a)))
# 2016-08-10 Concatenate non-empty flattened arguments with a single space.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/concatenate.php#L32-L54
# @used-by :func:`Df.Core.lib.cli.df_cli_cmd()`
# @used-by :meth:`Df.Core.Html.Tag.Tag.__formatAttr()`
# @used-by :meth:`Df.Core.Html.Tag.Tag.__openTagWithAttributesAsText()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_cc_s(*a: Any) -> str:
	return df_ccc(' ', dfa_flatten(list(a)))
# Concatenate non-empty flattened arguments using `glue` (filtering out '', None, [], False via df_clean).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/concatenate.php#L56-L82
# @used-by :func:`Df.Core.lib.reflection.text.cc.df_cc_method()`
# @used-by :func:`Df.Core.lib.text.n.cc.df_cc_n()`
# @used-by :func:`df_cc_br()`
# @used-by :func:`df_cc_s()`
# @used-by :meth:`Df.Qa.Trace.Formatter.Formatter.__format()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
def df_ccc(glue: str, *a: Any) -> str:
	return glue.join((str(x) for x in df_clean(dfa_flatten(list(a)))))
