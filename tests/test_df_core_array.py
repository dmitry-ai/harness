# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
class DfCoreArrayTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_assert_clean_and_filter(self) -> None:
		from Df.Core.lib.array.assert_ import dfa_assert_keys, dfa_has_keys
		from Df.Core.lib.array.clean.filter import df_filter, df_filter_f, df_filter_head, df_filter_tail
		from Df.Core.lib.array.clean.main import df_clean, df_clean_keys, df_clean_null, df_clean_r, dfa_remove_objects
		dfa_assert_keys({'a': 1, 'b': 2}, ['a', 'b'])
		self.assertTrue(dfa_has_keys({'a': 1, 'b': 2}, ['a', 'b']))
		self.assertFalse(dfa_has_keys({'a': 1}, ['a', 'b']))
		self.assertEqual([2, 4], df_filter([1, 2, 3, 4], lambda x: 0 == x % 2))
		self.assertEqual([2, 4], df_filter_f([1, 2, 3, 4], lambda x: 0 == x % 2, lambda a, f: [x for x in a if f(x)]))
		self.assertEqual([3, 1], df_filter_head([1, 2, 3, 1], lambda x: 3 > x))
		self.assertEqual([1, 2], df_filter_tail([1, 2, 3, 4], lambda x: 3 <= x))
		self.assertEqual([1, 0], df_clean([1, '', None, [], False, 0]))
		self.assertEqual({'a': 1}, df_clean_keys({'a': 1, '': 2, 'b': 3}, 'b'))
		self.assertEqual({'a': 1, 'c': ''}, df_clean_null({'a': 1, 'b': None, 'c': ''}))
		self.assertEqual({'a': [1, False]}, df_clean_r({'a': [1, '', None, [], False], 'b': []}))
		self.assertEqual({'a': 1}, dfa_remove_objects({'a': 1, 'b': object(), 'c': {'d': object()}}))
	# @used-by :mod:`unittest`
	def test_deep_find_first_insert_and_is(self) -> None:
		from Df.Core.lib.array.deep import dfa_deep, dfa_deep_set, dfa_deep_slice, dfa_deep_unset
		from Df.Core.lib.array.find import df_find, dfa_r
		from Df.Core.lib.array.first import df_first, df_first_key, df_last
		from Df.Core.lib.array.insert import dfa_insert, dfa_prepend_by_keys, dfa_prepend_by_values
		from Df.Core.lib.array.is_ import array_is_list, df_is_assoc, dfa_has_objects
		d: dict = {'a': {'b': 3}}
		self.assertEqual(3, dfa_deep(d, 'a/b'))
		dfa_deep_set(d, 'a/c/d', 7)
		self.assertEqual(7, dfa_deep(d, ['a', 'c', 'd']))
		self.assertEqual(['a'], dfa_deep_slice(d, 1))
		dfa_deep_unset(d, 'a/c/d')
		self.assertIsNone(dfa_deep(d, 'a/c/d'))
		self.assertEqual(4, df_find([1, 4, 6], lambda x: 3 < x))
		self.assertEqual(9, dfa_r({'x': {'y': {'z': 9}}}, 'z'))
		self.assertEqual(1, df_first([1, 2, 3]))
		self.assertEqual('k1', df_first_key({'k1': 1, 'k2': 2}))
		self.assertEqual(3, df_last([1, 2, 3]))
		self.assertEqual([1, 9, 2], dfa_insert([1, 2], 1, 9))
		self.assertEqual(['b', 'a', 'c'], list(dfa_prepend_by_keys({'a': 1, 'b': 2, 'c': 3}, ['b']).keys()))
		self.assertEqual(['B', 'A'], list(dfa_prepend_by_values({'A': 'a', 'B': 'b'}, ['b']).keys()))
		self.assertTrue(array_is_list([1, 2]))
		self.assertTrue(df_is_assoc({'a': 1}))
		self.assertTrue(dfa_has_objects({'a': [object()]}))
	# @used-by :mod:`unittest`
	def test_key_map_and_merge(self) -> None:
		from Df.Core.lib.array.key.transform import dfa_key_case, dfa_key_int, dfa_key_uc, dfak_prefix, dfak_transform, dfak_transform_r
		from Df.Core.lib.array.map import df_map
		from Df.Core.lib.array.map.const import DF_AFTER, DF_BEFORE
		from Df.Core.lib.array.map.each import df_each
		from Df.Core.lib.array.map.k import df_map_k
		from Df.Core.lib.array.map.kr import df_map_kr
		from Df.Core.lib.array.map.r import df_map_r
		from Df.Core.lib.array.merge import df_merge_not_empty, dfa_merge_numeric, dfa_merge_r
		self.assertEqual({'A': 1}, dfa_key_uc({'a': 1}))
		self.assertEqual({'a': 1}, dfa_key_case({'A': 1}, 1))
		self.assertEqual({1: 'x'}, dfa_key_int({'1': 'x'}))
		self.assertEqual({'p_a': 1}, dfak_prefix({'a': 1}, 'p_'))
		self.assertEqual({'A': {'b': 1}}, dfak_transform({'a': {'b': 1}}, str.upper))
		self.assertEqual({'A': {'B': 1}}, dfak_transform_r({'a': {'b': 1}}, str.upper))
		self.assertEqual([2, 4], df_map([1, 2], lambda x: x * 2))
		self.assertEqual((-1, 1), (DF_BEFORE, DF_AFTER))
		self.assertEqual([2, 4], df_each([{'v': 2}, {'v': 4}], 'v'))
		self.assertEqual({'a': 'a:1'}, df_map_k({'a': 1}, lambda k, v: f'{k}:{v}'))
		self.assertEqual({'A': 2}, df_map_kr({'a': 1}, lambda k, v: [k.upper(), v * 2]))
		self.assertEqual({'x': 1}, df_map_r([('x', 1)], lambda pair: [pair[0], pair[1]]))
		self.assertEqual({'a': 1, 'b': 2}, df_merge_not_empty({'a': 1, 'b': 0}, {'a': 0, 'b': 2}))
		self.assertEqual({'99': 'b', '1': 'a'}, dfa_merge_numeric({'1': 'a'}, {'99': 'b'}))
		self.assertEqual({'a': {'x': 1, 'y': 2}}, dfa_merge_r({'a': {'x': 1, 'z': 3}}, {'a': {'y': 2, 'z': None}}))
	# @used-by :mod:`unittest`
	def test_other_and_part(self) -> None:
		from Df.Core.lib.array.other.af import dfaf
		from Df.Core.lib.array.other.array import df_array
		from Df.Core.lib.array.other.chop import dfa_chop
		from Df.Core.lib.array.other.combine_self import dfa_combine_self
		from Df.Core.lib.array.other.flatten import dfa_flatten
		from Df.Core.lib.array.other.group import dfa_group
		from Df.Core.lib.array.other.index import df_index
		from Df.Core.lib.array.other.ita import df_ita
		from Df.Core.lib.array.other.repeated import dfa_repeated
		from Df.Core.lib.array.other.tr import dftr
		from Df.Core.lib.array.other.tuple import df_tuple
		from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
		from Df.Core.lib.array.other.unset import dfa_unset
		from Df.Core.lib.array.other.unshift_assoc import dfa_unshift_assoc
		from Df.Core.lib.array.part import df_head, df_slice, df_tail
		self.assertEqual(([1], str), tuple(dfaf(str, [1])))
		self.assertEqual([5], df_array(5))
		self.assertEqual(['ab', 'cd'], dfa_chop(['abcd', 'cdef'], 2))
		self.assertEqual({'a': 'a', 'b': 'b'}, dfa_combine_self('a', 'b'))
		self.assertEqual([1, 2, 3], dfa_flatten([1, [2, [3]]]))
		self.assertEqual({1: ['a', 'c'], 2: ['b']}, dfa_group({'a': 1, 'b': 2, 'c': 1}))
		self.assertEqual({'k': {'id': 'k', 'v': 1}}, df_index('id', [{'id': 'k', 'v': 1}]))
		self.assertEqual([1, 2], df_ita((x for x in (1, 2))))
		self.assertEqual([2, 3], dfa_repeated([1, 2, 2, 3, 3, 4]))
		self.assertEqual('ONE', dftr('1', {'1': 'ONE'}))
		self.assertEqual([{'a': 1, 'b': 4}, {'a': 2, 'b': None}], df_tuple({'a': [1, 2], 'b': [4]}))
		self.assertEqual([1, 2, 3], dfa_unique_fast([1, 2, 2, 3]))
		self.assertEqual({'b': 2}, dfa_unset({'a': 1, 'b': 2}, 'a'))
		d = {'b': 2}
		dfa_unshift_assoc(d, 'a', 1)
		self.assertEqual(['a', 'b'], list(d.keys()))
		self.assertEqual(([1, 2], [2, 3], [2, 3]), (df_head([1, 2, 3]), df_slice([1, 2, 3], 1), df_tail([1, 2, 3])))
	# @used-by :mod:`unittest`
	def test_select_sort_and_unpack(self) -> None:
		from Df.Core.lib.array.select import dfa
		from Df.Core.lib.array.select.cahed.function import dfac
		from Df.Core.lib.array.select.cahed.method import dfaoc
		from Df.Core.lib.array.select.column import df_column
		from Df.Core.lib.array.select.ordered import dfa_select_ordered
		from Df.Core.lib.array.select.strict import dfa_strict
		from Df.Core.lib.array.select.try_ import dfa_try
		from Df.Core.lib.array.sort import df_ksort, df_ksort_ci, df_ksort_r, df_ksort_r_ci, df_sort, df_sort_a, df_sort_posix
		from Df.Core.lib.array.unpack import df_arg, df_args, dfa_unpack
		self.assertEqual(2, dfa({'a': {'b': 2}}, 'a/b'))
		self.assertEqual({'b': 2, 'a': 1}, dfa_select_ordered({'a': 1, 'b': 2, 'c': 3}, ['b', 'a']))
		self.assertEqual(1, dfa_strict({'a': 1}, 'a'))
		self.assertEqual(2, dfa_try({'b': 2}, 'a', 'b'))
		self.assertEqual({'a': 10}, df_column({'a': {'v': 10}}, 'v'))
		# @used-by :meth:`DfCoreArrayTests.test_select_sort_and_unpack()`
		def cached_map(k: str='') -> object:
			return dfac(lambda: {'x': 7}, k)
		self.assertEqual(7, cached_map('x'))
		class Holder:
			# @used-by :meth:`DfCoreArrayTests.test_select_sort_and_unpack()`
			def data(self, k: str='') -> object:
				return dfaoc(self, lambda: {'y': 8}, k)
		self.assertEqual(8, Holder().data('y'))
		self.assertEqual(['a', 'b'], list(df_ksort({'b': 2, 'a': 1}).keys()))
		self.assertEqual(['a', 'B'], list(df_ksort_ci({'B': 2, 'a': 1}).keys()))
		from Df.Core.lib.array.other.group import dfa_group
		sorted_r = df_ksort_r({'b': {'y': 2, 'x': 1}, 'a': 1})
		self.assertEqual(['a', 'b'], list(sorted_r.keys()))
		self.assertEqual(['x', 'y'], list(sorted_r['b'].keys()))
		self.assertEqual({'x': [1, 2]}, dfa_group([{'g': 'x', 'v': 1}, {'g': 'x', 'v': 2}], 'g'))
		self.assertEqual(['a', 'B'], list(df_ksort_r_ci({'B': 2, 'a': 1}).keys()))
		self.assertEqual([1, 2, 3], df_sort([3, 1, 2]))
		self.assertEqual(['a', 'b'], list(df_sort_a({'b': 2, 'a': 1}).keys()))
		self.assertEqual(['a', 'b'], df_sort_posix(['b', 'a']))
		self.assertEqual((5, [1, 2], [1, 2, 3]), (df_arg([5]), df_args([[1, 2]]), dfa_unpack([1, [2, 3]])))
if '__main__' == __name__:
	unittest.main()
