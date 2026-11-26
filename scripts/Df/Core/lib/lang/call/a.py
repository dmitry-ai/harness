# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2016-01-14 Apply `f` to a single scalar or recursively map across a list/dict of arguments.
# 2024-06-10 "`df_call_a()` should accept the first 2 arguments in an arbitrary ordering": https://github.com/mage2pro/core/issues/417
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/call/a.php#L2-L50
# @used-by :func:`Df.Core.lib.html.df_html_b()`
# @used-by :func:`Df.Core.lib.text.camel.df_camel_to_underscore()`
# @used-by :func:`Df.Core.lib.text.camel.df_explode_camel()`
# @used-by :func:`Df.Core.lib.text.camel.df_underscore_to_camel()`
# @used-by :func:`Df.Core.lib.text.filter.df_e()`
# @used-by :func:`Df.Core.lib.text.transform.df_lcfirst()`
# @used-by :func:`Df.Core.lib.text.transform.df_strtolower()`
# @used-by :func:`Df.Core.lib.text.transform.df_strtoupper()`
# @used-by :func:`Df.Core.lib.text.transform.df_ucfirst()`
# @used-by :func:`Df.Core.lib.text.transform.df_ucwords()`
def df_call_a(a1: Any, a2: Any, pAppend: Any=None, pPrepend: Any=None, keyPosition: int=0) -> Any:
	from Df.Core.lib.array.map import df_map
	from Df.Core.lib.array.other.af import dfaf
	from Df.Core.lib.array.other.array import df_array
	a, f = dfaf(a1, a2)
	app = [] if None is pAppend else df_array(pAppend)
	prep = [] if None is pPrepend else df_array(pPrepend)
	items = list(a) if isinstance(a, (list, tuple)) else a
	if isinstance(items, list) and 1 == len(items):
		items = items[0]
	return df_map(f, items, app, prep, keyPosition) if isinstance(items, (list, dict)) else f(*prep, items, *app)
