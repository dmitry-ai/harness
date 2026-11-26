# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# 2016-03-25 http://stackoverflow.com/a/1320156 Recursively flatten nested lists, tuples, and dict values into a flat list.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/flatten.php#L2-L29
# @used-by :func:`Df.Core.lib.array.unpack.dfa_unpack()`
# @used-by :func:`Df.Core.lib.reflection.text.cc.df_cc_class()`
# @used-by :func:`Df.Core.lib.reflection.text.cc.df_cc_class_uc()`
# @used-by :func:`Df.Core.lib.reflection.text.explode.df_explode_class_camel()`
# @used-by :func:`Df.Core.lib.reflection.text.other.df_class_replace_last()`
# @used-by :func:`Df.Core.lib.text.concatenate.df_c()`
# @used-by :func:`Df.Core.lib.text.concatenate.df_cc()`
# @used-by :func:`Df.Core.lib.text.concatenate.df_cc_br()`
# @used-by :func:`Df.Core.lib.text.concatenate.df_cc_s()`
# @used-by :func:`Df.Core.lib.text.concatenate.df_ccc()`
# @used-by :func:`Df.Core.lib.text.contains.df_contains()`
# @used-by :func:`Df.Core.lib.text.csv.df_csv_pretty()`
# @used-by :func:`Df.Core.lib.text.explode.df_explode_xpath()`
# @used-by :func:`Df.Core.lib.text.filter.df_string_clean()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def dfa_flatten(a: list[Any] | tuple[Any, ...] | dict[Any, Any]) -> list[Any]:
	r: list[Any] = []
	vals = a.values() if isinstance(a, dict) else a
	for item in vals:
		if isinstance(item, (list, tuple, dict)):
			r.extend(dfa_flatten(item))
		else:
			r.append(item)
	return r
