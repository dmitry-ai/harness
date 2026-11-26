# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.is_ import array_is_list
from Df.Core.lib.array.select import dfa
from Df.Core.lib.empty import df_nes
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# @used-by :func:`dfa_deep()`
def _walk_deep(cur: Any, parts: list[Any]) -> Any:
	r: Any = None
	rest = list(parts)
	while rest:
		key = rest.pop(0)
		r = dfa(cur, key)
		if isinstance(r, (dict, list)):
			cur = r
		else:
			if rest:
				r = None
			break
	return r
# Extract a value from nested dicts/lists via 'key1/key2/key3' or a list of path keys.
# 2022-11-27 dfa_deep({'a': {'b': 3}}, ['a', None]) returns {'b': 3}.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/deep.php#L4-L90
# @used-by :func:`Df.Core.lib.array.select.dfa()`
# @used-by :meth:`Df.Core.O.O.offsetExists()`
# @used-by :meth:`Df.Core.O.O.offsetGet()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def dfa_deep(a: dict[Any, Any] | list[Any], path: Any='', d: Any=None) -> Any:
	if df_nes(path):
		r: Any = a
	elif isinstance(path, list):
		r = _walk_deep(a, path)
	elif isinstance(a, dict) and path in a and None is not a[path]:
		r = a[path]
	else:
		from Df.Core.lib.text.explode import df_explode_xpath
		r = _walk_deep(a, df_explode_xpath(path))
	return d if None is r else r
# 2015-12-07 Mutate nested dict `array` at slash-separated `path` (or key list) to `value`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/deep.php#L92-L117
# @used-by :meth:`Df.Core.O.O.offsetSet()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def dfa_deep_set(array: dict[Any, Any], path: str | list[str], value: Any) -> dict[Any, Any]:
	from Df.Core.lib.text.explode import df_explode_xpath
	parts = df_explode_xpath(path)
	cur: dict[Any, Any] = array
	for key in parts[:-1]:
		if key not in cur or (not isinstance(cur[key], dict)):
			cur[key] = {}
		cur = cur[key]
	if parts:
		cur[parts[-1]] = value
	return array
# 2018-04-24 Truncate a nested dict/list structure to depth `l`, returning keys at the leaf dict level.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/deep.php#L119-L128
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def dfa_deep_slice(a: dict[Any, Any] | list[Any], l: int) -> dict[Any, Any] | list[Any]:
	if 1 == l:
		r: dict[Any, Any] | list[Any] = a if array_is_list(a) else list(a.keys())
	elif isinstance(a, dict):
		r = {k: (dfa_deep_slice(v, l - 1) if isinstance(v, (dict, list)) else v) for k, v in a.items()}
	else:
		r = [dfa_deep_slice(v, l - 1) if isinstance(v, (dict, list)) else v for v in a]
	return r
# 2017-07-13 Remove a nested key at slash-separated `path` (or key list) from dict `a` in place.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/deep.php#L130-L163
# @used-by :meth:`Df.Core.O.O.offsetUnset()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_deep_find_first_insert_and_is()`
def dfa_deep_unset(a: dict[Any, Any], path: str | list[str]) -> None:
	from Df.Core.lib.text.explode import df_explode_xpath
	parts = list(path) if isinstance(path, list) else df_explode_xpath(path)
	if parts:
		first = parts.pop(0)
		if not parts:
			a.pop(first, None)
		elif first in a and isinstance(a[first], dict):
			dfa_deep_unset(a[first], parts)
