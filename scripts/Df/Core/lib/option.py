# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.first import df_first
from Df.Core.lib.array.other.combine_self import dfa_combine_self
from Df.Core.lib.array.select import dfa
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2015-12-28 Convert a flat list of strings into `[{'value': v, 'label': v}, ...]` if not already options.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/option.php#L3-L14
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_a_to_options(a: list[Any]) -> list[dict[str, Any]]:
	first = df_first(a)
	return a if None is first or (isinstance(first, dict) and 'value' in first) else df_map_to_options(dfa_combine_self(a))
# 2018-01-29 Prepend a default `0 => label` entry to an options map.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/option.php#L16-L26
# @used-by :func:`df_option_0()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_map_0(tail: dict[Any, str], l: str='') -> dict[Any, str]:
	if not isinstance(l, str):
		raise TypeError('df_map_0(): Argument #2 (l) must be of type str')
	r: dict[Any, str] = {0: l if l else '-- select a value --'}
	for k, v in tail.items():
		if k not in r:
			r[k] = v
	return r
# 2015-02-11 Convert `{value: label}` mapping into `[{'value': ..., 'label': ...}]` options list.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/option.php#L28-L40
# @used-by :func:`df_a_to_options()`
# @used-by :func:`df_option_0()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_map_to_options(m: dict[Any, str]) -> list[dict[str, Any]]:
	return [df_option(k, v) for k, v in m.items()]
# 2015-02-11 Convert `{label: value}` mapping into `[{'value': ..., 'label': ...}]` options list.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/option.php#L53-L62
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_map_to_options_reverse(m: dict[str, Any]) -> list[dict[str, Any]]:
	return [df_option(v, k) for k, v in m.items()]
# Build a single `{'label': l, 'value': v}` option dict.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/option.php#L64-L71
# @used-by :func:`df_map_to_options()`
# @used-by :func:`df_map_to_options_reverse()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_329_df_option_0_default_label()`
def df_option(v: Any, l: str) -> dict[str, Any]:
	return {'label': l, 'value': v}
# 2020-02-02 Prepend a default `0` option to an options list.
# 2026-11-26 "Fix df_option_0() passing None default label to df_map_0()": https://github.com/dmitry-ai/harness/issues/329
# Upstream defect: https://github.com/mage2pro/core/issues/472
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/option.php#L73-L81
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_329_df_option_0_default_label()`
def df_option_0(tail: list[dict[str, Any]], l: str | None=None) -> list[dict[str, Any]]:
	return df_map_to_options(df_map_0({}, '' if None is l else l)) + list(tail)
# Extract the `'value'` field from an option dict.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/option.php#L83-L89
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_option_v(o: dict[str, Any], d: Any=None) -> list[Any]:
	r = dfa(o, 'value', d)
	if not isinstance(r, list):
		raise TypeError('df_option_v(): Return value must be of type list')
	return r
# Extract the list of `'value'` entries from an options list.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/option.php#L91-L97
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_option_values(oo: list[dict[str, Any]]) -> list[Any]:
	return [o['value'] for o in oo if 'value' in o]
# Convert `[{'value': ..., 'label': ...}]` options list back into `{value: label}` dict.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/option.php#L99-L106
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_html_js_and_option()`
def df_options_to_map(options: list[dict[str, Any]]) -> dict[Any, Any]:
	return {o['value']: o['label'] for o in options if 'value' in o and 'label' in o}
