# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
class DfCoreBaseTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_cache_dfc_dfcf_and_ram(self) -> None:
		from Df.Core.ICached import ICached
		from Df.Core.RAM import RAM
		from Df.Core.lib.cache.dfc import dfc
		from Df.Core.lib.cache.dfcf import dfcf
		from Df.Core.lib.cache.o import df_ram
		class SampleCached(ICached):
			# @used-by :meth:`DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
			# @see :meth:`Df.Core.ICached.ICached.tags()`
			def tags(self) -> list[str]:
				return ['t1']
		ram = df_ram()
		self.assertIsInstance(ram, RAM)
		ram.reset()
		obj = SampleCached()
		self.assertIs(obj, ram.set('k1', obj, ['t0']))
		self.assertTrue(ram.exists('k1'))
		self.assertIs(obj, ram.get('k1'))
		ram.clean('t1')
		self.assertFalse(ram.exists('k1'))
		calls = []
		class Counter:
			# @used-by :meth:`DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
			def compute(self, x: int) -> int:
				return dfc(self, lambda v: (calls.append(v), v * 2)[1], [x])
		c = Counter()
		self.assertEqual(10, c.compute(5))
		self.assertEqual(10, c.compute(5))
		self.assertEqual([5], calls)
		f_calls = []
		# @used-by :meth:`DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
		def cached_fn(x: int) -> int:
			return dfcf(lambda v: (f_calls.append(v), v + 1)[1], [x])
		self.assertEqual(4, cached_fn(3))
		self.assertEqual(4, cached_fn(3))
		self.assertEqual([3], f_calls)
	# @used-by :mod:`unittest`
	def test_cli_state_and_hash(self) -> None:
		from Df.Core.lib.cli import df_cli_argv, df_cli_cmd, df_cli_script, df_cli_user, df_is_cli
		from Df.Core.lib.hash import df_hash_a, df_hash_o
		from Df.Core.lib.state import df_is_localhost, df_is_windows
		self.assertIsInstance(df_cli_argv(), list)
		self.assertIsInstance(df_cli_cmd(), str)
		self.assertIsInstance(df_cli_script(), str)
		self.assertTrue(bool(df_cli_user()))
		self.assertTrue(df_is_cli())
		self.assertIsInstance(df_is_localhost(), bool)
		self.assertIsInstance(df_is_windows(), bool)
		class WithId:
			# @used-by :meth:`DfCoreBaseTests.test_cli_state_and_hash()`
			def getId(self) -> int:
				return 42
		self.assertTrue(df_hash_o(WithId()).endswith('::42'))
		self.assertIn('a=>1', df_hash_a({'a': 1, 'b': [2]}))
	# @used-by :mod:`unittest`
	def test_cross_module_helpers(self) -> None:
		import tempfile
		from Df.Core.O import O
		from Df.Core.lib.json import df_json_file_read
		from Df.Core.lib.lang.call import df_call
		from Df.Core.lib.lang.other import df_no_rec
		from Df.Core.lib.math import df_vector_sum
		from Df.Core.lib.object.new import df_newa
		from Df.Core.lib.object.objects import df_ic, df_sc
		with tempfile.TemporaryDirectory() as td:
			jp = Path(td) / 'sample.json'
			jp.write_text('{"b": 2, "a": 1}', encoding='utf-8')
			self.assertEqual({'a': 1, 'b': 2}, df_json_file_read(jp))
		class Target:
			# @used-by :meth:`DfCoreBaseTests.test_cross_module_helpers()`
			def compute(self, flag: bool, count: int=3) -> tuple[bool, int]:
				return (flag, count)
		self.assertEqual((True, 3), df_call(Target(), 'compute', {'flag': 'yes'}))
		hits: list[int] = []
		# @used-by :meth:`DfCoreBaseTests.test_cross_module_helpers()`
		def guard() -> None:
			df_no_rec(lambda: (hits.append(1), guard()))
		guard()
		self.assertEqual([1], hits)
		self.assertEqual([5, 7], df_vector_sum([1, 2], [4, 5]))
		self.assertIsInstance(df_newa(O, O, {'x': 1}), O)
		self.assertIsInstance(df_ic('Df.Core.O.O', O, {'x': 1}), O)
		self.assertIsInstance(df_sc('Df.Core.RAM.RAM', 'Df.Core.RAM.RAM'), object)
	# @used-by :mod:`unittest`
	def test_empty_float_and_math(self) -> None:
		from Df.Core.lib.empty import df_es, df_etn, df_ets, df_fnes, df_ftn, df_fts, df_nes, df_nts
		from Df.Core.lib.float import dff_2, dff_2f, dff_2i, dff_chop0, dff_eq, dff_eq0
		from Df.Core.lib.math import df_round
		self.assertTrue(df_es(''))
		self.assertFalse(df_es('a'))
		self.assertIsNone(df_etn(''))
		self.assertEqual('x', df_etn('x'))
		self.assertEqual('', df_ets(0))
		self.assertTrue(df_fnes(False))
		self.assertFalse(df_fnes(0))
		self.assertIsNone(df_ftn(False))
		self.assertEqual('', df_fts(False))
		self.assertTrue(df_nes(None))
		self.assertEqual('', df_nts(None))
		self.assertEqual('3.00', dff_2(3))
		self.assertEqual(3.33, dff_2f('3.333'))
		self.assertEqual('3', dff_2i(3))
		self.assertEqual('3.30', dff_2i(3.3))
		self.assertEqual('3', dff_chop0(3.0))
		self.assertEqual('3.3', dff_chop0(3.300))
		self.assertTrue(dff_eq(100.0, 100.05))
		self.assertTrue(dff_eq0(0.0005))
		self.assertEqual(4, df_round(3.6))
	# @used-by :mod:`unittest`
	def test_exception_and_json_class(self) -> None:
		from Df.Core.Exception import Exception as DFE
		from Df.Core.Json import Json
		self.assertTrue(Json.bSort())
		Json.bSort(False)
		self.assertFalse(Json.bSort())
		Json.bSort(True)
		ex = DFE('boom')
		self.assertEqual('boom', ex.message())
		self.assertEqual('', ex.messageC())
		self.assertEqual('boom', ex.messageD())
		self.assertFalse(ex.isMessageHtml())
		self.assertIs(ex, ex.markMessageAsHtml())
		self.assertTrue(ex.isMessageHtml())
		self.assertEqual(0, ex.getStackLevelsCountToSkip())
		self.assertIn('Exception', ex.sentryType())
		wrapped = DFE.wrap(RuntimeError('inner'))
		self.assertIsInstance(wrapped, DFE)
		self.assertEqual('inner', wrapped.message())
		with self.assertRaises(DFE):
			ex.throw_()
	# @used-by :mod:`unittest`
	def test_json_and_object_helpers(self) -> None:
		from Df.Core.lib.json import df_check_json, df_check_json_complex, df_json_dont_sort, df_json_encode, df_json_encode_partial
		from Df.Core.lib.lang.type.stringable import df_is_stringable
		from Df.Core.lib.object.new import df_new
		from Df.Core.lib.object.objects import dfo
		class Box:
			# @used-by :meth:`DfCoreBaseTests.test_json_and_object_helpers()`
			def __init__(self, v: str='ok') -> None:
				self.pub = v
		inst = df_new(Box, 'val')
		self.assertIsInstance(inst, Box)
		self.assertEqual('val', dfo(inst, 'pub'))
		self.assertEqual('def', dfo(inst, 'missing', 'def'))
		self.assertTrue(df_is_stringable('ok'))
		self.assertFalse(df_is_stringable([1]))
		self.assertTrue(df_check_json('{"a": 1}'))
		self.assertFalse(df_check_json('{bad'))
		self.assertTrue(df_check_json_complex('{"a": 1}'))
		self.assertFalse(df_check_json_complex('123'))
		self.assertIn('"a": 1', df_json_dont_sort(lambda: df_json_encode({'b': 2, 'a': 1})))
		self.assertIn('a', df_json_encode_partial({'a': object()}))
	# @used-by :mod:`unittest`
	def test_lang_call_if_and_prop(self) -> None:
		from Df.Core.lib.lang.call.if_ import df_call_if
		from Df.Core.lib.lang.call.parent import df_call_parent
		from Df.Core.lib.lang.if_ import df_if, df_if1, df_if2
		from Df.Core.lib.lang.other import df_b, df_nop
		from Df.Core.lib.lang.prop.custom import DF_N, df_n_get, df_n_set, df_prop_k
		from Df.Core.lib.lang.prop.native import dfr_prop, dfr_prop_get, dfr_prop_set
		self.assertEqual(7, df_call_if(lambda x: x + 2, 5))
		self.assertEqual(9, df_call_if(9, 5))
		self.assertEqual(1, df_if(True, lambda: 1, lambda: 2))
		self.assertEqual(2, df_if(False, lambda: 1, lambda: 2))
		self.assertEqual(3, df_if1(True, lambda: 3, 4))
		self.assertEqual(4, df_if2(False, 3, lambda: 4))
		self.assertEqual('yes', df_b(['yes', 'no'], True))
		self.assertEqual('no', df_b(['yes', 'no'], False))
		self.assertTrue(df_b([], True))
		self.assertEqual('abc', df_nop('abc'))
		self.assertIsNone(df_n_get(DF_N))
		self.assertEqual(DF_N, df_n_set(None))
		class Parent:
			# @used-by :meth:`DfCoreBaseTests.test_lang_call_if_and_prop()`
			def greet(self, who: str) -> str:
				return f'hi {who}'
		class Child(Parent):
			# @used-by :meth:`DfCoreBaseTests.test_lang_call_if_and_prop()`
			def __init__(self) -> None:
				self.__secret = 1
		ch = Child()
		self.assertEqual('hi py', df_call_parent(ch, 'greet', ['py']))
		self.assertIs(ch, df_prop_k(ch, 'k', 123))
		self.assertEqual(123, df_prop_k(ch, 'k'))
		self.assertEqual(1, dfr_prop_get(ch, '_Child__secret'))
		dfr_prop_set(ch, '_Child__secret', 9)
		self.assertEqual(9, dfr_prop(ch, '_Child__secret').getValue(ch))
if '__main__' == __name__:
	unittest.main()
