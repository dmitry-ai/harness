# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
import json
from Df.Core.Json import Json
from Df.Core.lib.empty import df_nes
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2016-07-18 Return True iff `v` decodes as non-null JSON without errors.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/json.php#L5-L13
# @used-by :func:`df_check_json_complex()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpS()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_json_and_object_helpers()`
def df_check_json(v: Any) -> bool:
	try:
		r = None is not json.loads(v) if isinstance(v, (str, bytes, bytearray)) else False
	except (TypeError, ValueError):
		r = False
	return r
# 2016-08-19 Return True iff `v` is a JSON object string starting with `{`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/json.php#L15-L21
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_json_and_object_helpers()`
def df_check_json_complex(v: Any) -> bool:
	return isinstance(v, str) and v.startswith('{') and df_check_json(v)
# 2015-12-19 Decode JSON string into Python data, sorting dict keys unless disabled.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/json.php#L23-L112
# @used-by :func:`df_json_file_read()`
# @used-by :func:`df_json_prettify()`
def df_json_decode(s: str | None, throw: bool=True) -> Any:
	if df_nes(s):
		r: Any = s
	else:
		try:
			r = json.loads(str(s))
		except (TypeError, ValueError) as exc:
			if throw:
				from Df.Qa.lib.validation.error import df_error
				df_error(f'Parsing a JSON document failed with the message «{exc}».\nThe document:\n{s}')
			r = None
	return df_json_sort(r)
# 2023-08-04 "Implement `df_json_dont_sort()`": https://github.com/mage2pro/core/issues/313
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/json.php#L114-L126
# @used-by :func:`Df.Qa.lib.dump.df_dump_ds()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_json_and_object_helpers()`
def df_json_dont_sort(f: Callable[[], Any]) -> Any:
	prev = Json.bSort()
	Json.bSort(False)
	try:
		r = f()
	finally:
		Json.bSort(prev)
	return r
# 2015-12-06 Pretty-print value as UTF-8 JSON with unescaped Unicode and slashes.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/json.php#L128-L176
# @used-by :func:`Df.Core.lib.js.ejs.df_ejs()`
# @used-by :func:`df_json_prettify()`
# @used-by :meth:`Df.Core.O.O.j()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpArray()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_json_and_object_helpers()`
def df_json_encode(v: Any, flags: int=0) -> str:
	return json.dumps(df_json_sort(v), ensure_ascii=False, indent=4)
# 2020-02-15 Encode value as JSON while falling back to stringifying unserializable objects.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/json.php#L178-L183
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpObject()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_json_and_object_helpers()`
def df_json_encode_partial(v: Any) -> str:
	return json.dumps(df_json_sort(v), default=str, ensure_ascii=False, indent=4)
# 2022-10-15 Read and decode a UTF-8 JSON file.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/json.php#L185-L196
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cross_module_helpers()`
def df_json_file_read(p: str | Path) -> Any:
	return df_json_decode(Path(p).read_text(encoding='utf-8'))
# 2017-07-05 Re-format a JSON string or mapping with canonical pretty-printing.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/json.php#L198-L203
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpS()`
def df_json_prettify(j: str | dict[str, Any]) -> str:
	return df_json_encode(df_json_decode(j) if isinstance(j, str) else j)
# 2017-09-07 Recursively case-insensitive key-sort associative dicts when Json.bSort() is enabled.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/json.php#L205-L216
# @used-by :func:`df_json_decode()`
# @used-by :func:`df_json_encode()`
# @used-by :func:`df_json_encode_partial()`
def df_json_sort(v: Any) -> Any:
	if (not isinstance(v, dict)) or (not Json.bSort()):
		r = v
	else:
		from Df.Core.lib.array.sort import df_ksort_r_ci
		r = df_ksort_r_ci(v)
	return r
