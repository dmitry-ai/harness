# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.text.concatenate import df_ccc
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# Concatenate non-empty lines with `\n`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/n/cc.php#L2-L49
# @used-by :func:`Df.Core.lib.html.df_tag_list()`
# @used-by :func:`Df.Core.lib.text.prepend_append.tab.df_tab()`
# @used-by :func:`Df.Qa.lib.dump.kv.df_kv()`
# @used-by :func:`Df.Qa.lib.validation.error.df_error_create()`
# @used-by :meth:`Df.Core.Html.Tag.Tag.__contentStr()`
# @used-by :meth:`Df.Core.Text.Regex.Regex.__getSubjectReportPart()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpArrayElements()`
# @used-by :meth:`Df.Qa.Method.Method.raiseErrorParam()`
# @used-by :meth:`Df.Qa.Method.Method.raiseErrorResult()`
# @used-by :meth:`Df.Qa.Method.Method.raiseErrorVariable()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_cc_n(*a: Any) -> str:
	return df_ccc('\n', *a)
