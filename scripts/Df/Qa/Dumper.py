# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections.abc import Iterable
from typing import Any
from Df.Core.lib.array.is_ import dfa_has_objects
from Df.Core.lib.array.map.k import df_map_k
from Df.Core.lib.array.other.ita import df_ita
from Df.Core.lib.array.sort import df_ksort
from Df.Core.lib.json import df_check_json, df_json_encode, df_json_encode_partial, df_json_prettify
from Df.Core.lib.lang.type.conversion.string import df_string
from Df.Core.lib.lang.type.stringable import df_is_stringable
from Df.Core.lib.reflection.text.cts import df_cts
from Df.Core.lib.text.n.cc import df_cc_n
from Df.Core.lib.text.n.has import df_is_multiline
from Df.Core.lib.text.n.normalize import df_normalize
from Df.Core.lib.text.n.prepend import df_n_prepend
from Df.Core.lib.text.prepend_append.tab import df_tab
from Df.Core.lib.text.trim import df_trim
from Df.Qa.lib.dump.bool import df_bts
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2023-07-25 Diagnostic value dumper with cycle tracking and pretty JSON output.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/Dumper.php#L4-L104
class Dumper:
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Dumper.php#L97
	# @used-by :meth:`Dumper.i()`
	def __init__(self) -> None:
		self.__dumped: dict[int, bool] = {}
	# 2023-07-25 "Return JSON from `\Df\Qa\Dumper::dumpArray()` for arrays without object elements":
	# https://github.com/mage2pro/core/issues/252
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Dumper.php#L15-L20
	# @used-by :meth:`Dumper.dump()`
	def __dumpArray(self, a: list[Any] | dict[Any, Any]) -> str:
		return f'[\n{df_tab(self.__dumpArrayElements(a))}\n]' if dfa_has_objects(a) else df_json_encode(a)
	# Handles objects and cyclic references, omits top-level array wrappers, and sorts keys for easy diffing.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Dumper.php#L49-L51
	# @used-by :meth:`Dumper.__dumpArray()`
	# @used-by :meth:`Dumper.__dumpObject()`
	def __dumpArrayElements(self, a: list[Any] | dict[Any, Any]) -> str:
		return df_cc_n(df_map_k(df_ksort(a), lambda k, v: f'{k}: {self.dump(v)}'))
	# Dump an object instance while tracking visited object IDs to avoid infinite recursion.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Dumper.php#L61-L84
	# @used-by :meth:`Dumper.dump()`
	def __dumpObject(self, o: Any) -> str:
		c = df_cts(o)
		oid = id(o)
		if oid in self.__dumped:
			r = f'[recursion: {c}]'
		else:
			self.__dumped[oid] = True
			if df_is_stringable(o):
				v = df_string(o)
				suffix = df_n_prepend(df_tab(v)) if df_is_multiline(v) else f' «{v}»'
				r = f'`{c}::__toString()`{suffix}'
			elif isinstance(o, Iterable):
				# 2023-07-26 "`df_dump()` should handle `Traversable` similar to arrays": https://github.com/mage2pro/core/issues/253
				r = f'{c}(\n{df_tab(self.__dumpArrayElements(df_ita(o)))}\n)'
			else:
				r = f'{c}: {df_json_encode_partial(o)}'
		return r
	# 2024-09-23 Normalize and trim a string, prettifying it if it contains valid JSON.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Dumper.php#L90
	# @used-by :meth:`Dumper.dump()`
	def __dumpS(self, s: str) -> str:
		r = str(df_trim(df_normalize(s)))
		return df_json_prettify(r) if df_check_json(r) else r
	# Format any value (primitives, arrays/dicts, iterables, or objects) into a readable diagnostic string.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Dumper.php#L10-L12
	# @used-by :func:`Df.Qa.lib.dump.df_dump()`
	# @used-by :meth:`Dumper.__dumpArrayElements()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_dump_and_dumper()`
	def dump(self, v: Any) -> str:
		if None is v:
			r = ''
		elif isinstance(v, bool):
			r = df_bts(v)
		elif isinstance(v, str):
			r = self.__dumpS(v)
		elif isinstance(v, (list, dict)):
			r = self.__dumpArray(v)
		elif isinstance(v, (int, float)):
			r = str(v)
		else:
			r = self.__dumpObject(v)
		return r
	# Intentionally returns a fresh instance (not a singleton) so cycle tracking is scoped per dump call.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Dumper.php#L103
	# @used-by :func:`Df.Qa.lib.dump.df_dump()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_dump_and_dumper()`
	@staticmethod
	def i() -> Dumper:
		return Dumper()