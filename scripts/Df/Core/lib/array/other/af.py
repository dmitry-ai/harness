# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Iterable
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# @used-by :func:`dfaf()`
def _is_iter(v: Any) -> bool:
	return isinstance(v, Iterable) and (not isinstance(v, (str, bytes)))
# 2017-02-18 Normalize (iterable|callable, iterable|callable) pair to [iterable, callable].
# 2024-06-11 "Improve `dfaf()`": https://github.com/mage2pro/core/issues/421
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/af.php#L2-L42
# @used-by :func:`Df.Core.lib.array.clean.filter.df_filter_f()`
# @used-by :func:`Df.Core.lib.array.find.df_find()`
# @used-by :func:`Df.Core.lib.array.key.transform.dfak_transform()`
# @used-by :func:`Df.Core.lib.array.map.df_map()`
# @used-by :func:`Df.Core.lib.lang.call.a.df_call_a()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
def dfaf(a: Any, b: Any) -> list[Any]:
	ca, cb, ia, ib = (callable(a), callable(b), _is_iter(a), _is_iter(b))
	if ca and cb:
		if not (ia ^ ib):
			from Df.Qa.lib.validation.error import df_error
			df_error('dfaf(): ' + ('none of arguments are `iterable`.' if not ia else 'both arguments are `callable` and `iterable`.'), {'a': a, 'b': b})
		r = [a, b] if ia else [b, a]
	elif ca and ib:
		r = [b, a]
	elif cb and ia:
		r = [a, b]
	else:
		from Df.Qa.lib.validation.error import df_error
		df_error('dfaf(): invalid (iterable, callable) argument pair.', {'a': a, 'b': b})
		r = []
	return r
