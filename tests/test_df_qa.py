# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any, Iterator
import os
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
class _AbstractBase:
	# @used-by :meth:`TestDfQa.test_error_helpers()`
	def doWork(self) -> None:
		from Df.Qa.lib.validation.error import df_abstract
		df_abstract(self)
class _AbstractSub(_AbstractBase):
	pass
class _CycleBox:
	# @used-by :meth:`TestDfQa.test_dump_and_dumper()`
	def __init__(self, label: str) -> None:
		self.label = label
		self.ref: Any = None
	# @used-by :meth:`TestDfQa.test_dump_and_dumper()`
	def __iter__(self) -> Iterator[Any]:
		return iter([self.label, self.ref])
class _IterObj:
	# @used-by :meth:`TestDfQa.test_dump_and_dumper()`
	def __init__(self, items: list[Any]) -> None:
		self.__items = items
	# @used-by :meth:`TestDfQa.test_dump_and_dumper()`
	def __iter__(self) -> Iterator[Any]:
		return iter(self.__items)
class _PlainObj:
	# @used-by :meth:`TestDfQa.test_assert_class_and_other()`
	# @used-by :meth:`TestDfQa.test_dump_and_dumper()`
	# @used-by :meth:`TestDfQa.test_type_and_kv()`
	def __init__(self, v: int) -> None:
		self.v = v
class _SampleService:
	# @used-by :meth:`TestDfQa.test_method_and_param_result()`
	def checkIso(self, code: str) -> str:
		from Df.Qa.lib.validation.param import df_param_iso2
		return df_param_iso2(code, 0)
	# @used-by :meth:`TestDfQa.test_method_and_param_result()`
	def checkRes(self, val: Any) -> str:
		from Df.Qa.lib.validation.result import df_result_s
		return df_result_s(val)
	# @used-by :meth:`TestDfQa.test_method_and_param_result()`
	def checkResSne(self, val: str) -> str:
		from Df.Qa.lib.validation.result import df_result_sne
		return df_result_sne(val)
	# @used-by :meth:`TestDfQa.test_method_and_param_result()`
	def checkSne(self, token: str) -> str:
		from Df.Qa.lib.validation.param import df_param_sne
		return df_param_sne(token, 0)
	# @used-by :meth:`TestDfQa.test_method_and_param_result()`
	def checkVar(self, val: str) -> str:
		from Df.Qa.lib.validation.assert_.other import df_assert_sne
		return df_assert_sne(val)
	# @used-by :meth:`TestDfQa.test_error_helpers()`
	def forbidden(self) -> None:
		from Df.Qa.lib.validation.error import df_should_not_be_here
		df_should_not_be_here()
class _StringableObj:
	# @used-by :meth:`TestDfQa.test_dump_and_dumper()`
	def __init__(self, text: str) -> None:
		self.__text = text
	# @used-by :func:`Df.Core.lib.lang.type.stringable.df_is_stringable()`
	def __str__(self) -> str:
		return self.__text
class TestDfQa(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_assert_array_and_bool(self) -> None:
		from Df.Core.Exception import Exception as DFE
		from Df.Qa.lib.validation.assert_ import df_assert
		from Df.Qa.lib.validation.assert_.array import df_assert_array, df_assert_assoc, df_assert_count, df_assert_in
		from Df.Qa.lib.validation.assert_.bool import df_bool
		self.assertEqual(42, df_assert(42, 'fail'))
		with self.assertRaises(DFE):
			df_assert(False, 'boom')
		self.assertEqual([1, 2], df_assert_array([1, 2]))
		with self.assertRaises(DFE):
			df_assert_array('not-array')
		self.assertEqual({'a': 1}, df_assert_assoc({'a': 1}))
		with self.assertRaises(DFE):
			df_assert_assoc([1, 2])
		self.assertEqual([1, 2], df_assert_count(2, [1, 2]))
		with self.assertRaises(DFE):
			df_assert_count(3, [1, 2])
		self.assertEqual('a', df_assert_in('a', ['a', 'b']))
		with self.assertRaises(DFE):
			df_assert_in('z', ['a', 'b'])
		with self.assertRaises(DFE):
			df_assert_in('z', list(range(12)))
		self.assertTrue(df_bool(True))
		self.assertTrue(df_bool('yes'))
		self.assertTrue(df_bool('да'))
		self.assertFalse(df_bool(False))
		self.assertFalse(df_bool('нет'))
		self.assertFalse(df_bool(None))
		with self.assertRaises(DFE):
			df_bool('maybe')
	# @used-by :mod:`unittest`
	def test_assert_class_and_other(self) -> None:
		from Df.Core.Exception import Exception as DFE
		from Df.Core.O import O
		from Df.Qa.lib.validation.assert_.class_ import df_ar, df_assert_class_exists, df_is
		from Df.Qa.lib.validation.assert_.other import df_assert_nef
		from Df.Qa.lib.validation.assert_.stringable import df_assert_stringable
		o = O({'a': 1})
		self.assertIs(o, df_ar(o, O))
		self.assertIs(o, df_ar(o))
		self.assertEqual('Df.Core.O.O', df_assert_class_exists('Df.Core.O.O'))
		with self.assertRaises(DFE):
			df_ar(None, O)
		with self.assertRaises(DFE):
			df_ar(123, O)
		with self.assertRaises(DFE):
			df_ar(_PlainObj(1), O)
		with self.assertRaises(DFE):
			df_assert_class_exists('Df.Core.DoesNotExist.Nope')
		self.assertTrue(df_is(o, 'Df.Core.O.O'))
		self.assertFalse(df_is(o, 'Df.Core.RAM.RAM'))
		self.assertEqual(0, df_assert_nef(0))
		with self.assertRaises(DFE):
			df_assert_nef(False)
		self.assertTrue(df_assert_stringable('ok', 'bad'))
		with self.assertRaises(DFE):
			df_assert_stringable([1, 2], 'not stringable')
	# @used-by :mod:`unittest`
	def test_assert_float_and_int(self) -> None:
		from Df.Core.Exception import Exception as DFE
		from Df.Qa.lib.validation.assert_.float import df_float, df_float_positive, df_float_positive0
		from Df.Qa.lib.validation.assert_.int import df_int, df_int_simple, df_nat, df_nat0
		self.assertEqual(1.5, df_float(1.5))
		self.assertEqual(2.0, df_float(2))
		self.assertEqual(0.0, df_float(None))
		self.assertEqual(60.15, df_float('60,15'))
		self.assertEqual(368.0, df_float('368.'))
		self.assertEqual([1.0, 2.5], df_float([1, '2.5']))
		with self.assertRaises(DFE):
			df_float('abc')
		self.assertEqual(3.5, df_float_positive('3.5'))
		self.assertIsNone(df_float_positive(-1, False, False))
		self.assertEqual(0.0, df_float_positive0(0))
		self.assertEqual(5, df_int(5))
		self.assertEqual(1, df_int(True))
		self.assertEqual(0, df_int(None))
		self.assertEqual(9, df_int('09'))
		self.assertEqual([1, 2], df_int(['1', 2]))
		with self.assertRaises(DFE):
			df_int('1.5')
		self.assertEqual([1, 2], df_int_simple(['1', '2']))
		self.assertEqual({'a': 3}, df_int_simple({'a': '3'}))
		self.assertEqual(7, df_nat('7'))
		self.assertEqual(0, df_nat0(0))
		with self.assertRaises(DFE):
			df_nat(-2)
	# @used-by :mod:`unittest`
	def test_assert_numeric_comparison_and_check(self) -> None:
		from Df.Core.Exception import Exception as DFE
		from Df.Qa.lib.validation.assert_.numeric_comparison import df_assert_between, df_assert_eq, df_assert_ge, df_assert_gt, df_assert_gt0, df_assert_le, df_assert_lt, df_assert_ne
		from Df.Qa.lib.validation.check import df_between, df_check_iso2, df_check_s, df_is_email, df_is_int, df_is_nat
		self.assertTrue(df_between(5, 1, 5))
		self.assertFalse(df_between(5, 1, 5, False))
		self.assertEqual(3, df_assert_between(3, 1, 5))
		with self.assertRaises(DFE):
			df_assert_between(9, 1, 5)
		self.assertEqual(3, df_assert_eq(3, 3))
		with self.assertRaises(DFE):
			df_assert_eq(3, 4)
		self.assertEqual(5, df_assert_ge(5, 5))
		with self.assertRaises(DFE):
			df_assert_ge(5, 4)
		self.assertEqual(6, df_assert_gt(5, 6))
		with self.assertRaises(DFE):
			df_assert_gt(5, 4)
		self.assertEqual(2, df_assert_gt0(2))
		with self.assertRaises(DFE):
			df_assert_gt0(-1)
		self.assertEqual(5, df_assert_le(5, 5))
		with self.assertRaises(DFE):
			df_assert_le(5, 6)
		self.assertEqual(3, df_assert_lt(5, 3))
		with self.assertRaises(DFE):
			df_assert_lt(5, 7)
		self.assertEqual(2, df_assert_ne(1, 2))
		with self.assertRaises(DFE):
			df_assert_ne(1, 1)
		self.assertTrue(df_is_email('user@example.com'))
		self.assertFalse(df_is_email('not-an-email'))
		self.assertTrue(df_is_int('12'))
		self.assertFalse(df_is_int('12.5'))
		self.assertTrue(df_is_nat('3'))
		self.assertFalse(df_is_nat(0))
		self.assertTrue(df_check_iso2('US'))
		self.assertFalse(df_check_iso2('USA'))
		self.assertTrue(df_check_s(None))
		self.assertFalse(df_check_s([1]))
	# @used-by :mod:`unittest`
	def test_bt_helpers(self) -> None:
		from Df.Qa.lib.bt.entry import df_bt_entry_class, df_bt_entry_file, df_bt_entry_func, df_bt_entry_is_method, df_bt_entry_line
		from Df.Qa.lib.bt.filter import df_bt_filter_head
		from Df.Qa.lib.bt.log import df_bt_s
		from Df.Qa.lib.bt.main import df_bt, df_bt_has, df_bt_inc
		from Df.Qa.lib.bt.throwable import df_bt_th
		bt = df_bt()
		self.assertGreater(len(bt), 0)
		self.assertEqual('test_bt_helpers', df_bt_entry_func(bt[0]))
		self.assertTrue(df_bt_entry_file(bt[0]).endswith('test_df_qa.py'))
		self.assertGreater(df_bt_entry_line(bt[0]), 0)
		self.assertTrue(df_bt_entry_is_method(bt[0]))
		self.assertTrue(df_bt_entry_class(bt[0]).endswith('TestDfQa'))
		self.assertTrue(df_bt_has(df_bt_entry_class(bt[0]), 'test_bt_helpers'))
		self.assertEqual(3, df_bt_inc(1, 2))
		self.assertEqual([{'function': 'realFn'}], df_bt_filter_head([{'function': 'dfc'}, {'function': 'realFn'}]))
		self.assertIn('test_bt_helpers', df_bt_s())
		err: BaseException | None = None
		try:
			raise ValueError('inner boom')
		except ValueError as exc:
			err = exc
		self.assertGreater(len(df_bt_th(err)), 0)
	# @used-by :mod:`unittest`
	def test_diagnostics_and_exceptions(self) -> None:
		from Df.Core.Exception import Exception as DFE
		from Df.Qa.lib.diagnostics import df_break, df_webserver
		from Df.Qa.lib.exception import df_is_th, df_is_x, df_th2x, df_xf, df_xts, df_xtsd
		df_break(False)
		old_bp = os.environ.get('PYTHONBREAKPOINT')
		os.environ['PYTHONBREAKPOINT'] = '0'
		try:
			df_break(True)
		finally:
			if None is old_bp:
				os.environ.pop('PYTHONBREAKPOINT', None)
			else:
				os.environ['PYTHONBREAKPOINT'] = old_bp
		ws = df_webserver()
		self.assertIsInstance(ws, str)
		self.assertEqual(2, len(df_webserver(True)))
		root_err = ValueError('root')
		outer = DFE('outer', root_err)
		self.assertTrue(df_is_th(outer))
		self.assertTrue(df_is_x(outer))
		self.assertIs(outer, df_th2x(outer))
		ke = KeyboardInterrupt('stop')
		self.assertIsInstance(df_th2x(ke), Exception)
		self.assertIs(root_err, df_xf(outer))
		self.assertEqual('outer', df_xts(outer))
		self.assertEqual('outer', df_xtsd(outer))
		self.assertEqual('plain', df_xts('plain'))
	# @used-by :mod:`unittest`
	# @uses :meth:`_CycleBox.__iter__()`
	# @uses :meth:`_IterObj.__iter__()`
	def test_dump_and_dumper(self) -> None:
		from Df.Qa.Dumper import Dumper
		from Df.Qa.lib.dump import df_dump, df_dump_ds
		from Df.Qa.lib.dump.bool import df_bts, df_bts_yn
		self.assertEqual('true', df_bts(True))
		self.assertEqual('false', df_bts(False))
		self.assertEqual('yes', df_bts_yn(True))
		self.assertEqual('no', df_bts_yn(False))
		self.assertEqual('true', df_dump(True))
		self.assertEqual('42', df_dump(42))
		self.assertEqual('hello', df_dump('  hello  '))
		self.assertIn('"b": 1', df_dump('{"b":1,"a":2}'))
		self.assertIn('__toString()', df_dump(_StringableObj('one line')))
		self.assertIn('__toString()', df_dump(_StringableObj('line1\nline2')))
		self.assertIn('_IterObj', df_dump(_IterObj([1, 2])))
		self.assertIn('_PlainObj', df_dump(_PlainObj(9)))
		box = _CycleBox('head')
		box.ref = box
		self.assertIn('[recursion:', Dumper.i().dump(box))
		self.assertIn('_PlainObj', df_dump([_PlainObj(1)]))
		ds = df_dump_ds({'b': 1, 'a': 2})
		self.assertLess(ds.index('"b"'), ds.index('"a"'))
	# @used-by :mod:`unittest`
	def test_error_helpers(self) -> None:
		from Df.Core.Exception import Exception as DFE
		from Df.Qa.lib.validation.error import df_error, df_error_create, df_error_html, df_not_implemented
		e1 = df_error_create('hello %s', 'world')
		self.assertEqual('hello world', e1.message())
		e2 = df_error_create(['a', 'b'], {'ctx': 1})
		self.assertEqual('a\nb', e2.message())
		self.assertEqual({'ctx': 1}, e2.context())
		e3 = df_error_create({'only': 2})
		self.assertEqual({'only': 2}, e3.context())
		with self.assertRaises(DFE):
			df_error('bad %s', 'x')
		with self.assertRaises(DFE) as cm_html:
			df_error_html('<b>hi</b>')
		self.assertTrue(cm_html.exception.isMessageHtml())
		with self.assertRaises(DFE):
			df_not_implemented('foo')
		with self.assertRaises(DFE) as cm_ab:
			_AbstractBase().doWork()
		self.assertIn('is abstract', cm_ab.exception.message())
		with self.assertRaises(DFE) as cm_sub:
			_AbstractSub().doWork()
		self.assertIn('should be redefined', cm_sub.exception.message())
		with self.assertRaises(DFE) as cm_forb:
			_SampleService().forbidden()
		self.assertIn('not allowed to call', cm_forb.exception.message())
	# @used-by :mod:`unittest`
	def test_method_and_param_result(self) -> None:
		from Df.Core.Exception import Exception as DFE
		from Df.Qa.Trace.Frame import Frame
		svc = _SampleService()
		self.assertEqual('US', svc.checkIso('US'))
		with self.assertRaises(DFE) as cm_iso:
			svc.checkIso('USA')
		self.assertIn('code', cm_iso.exception.message())
		self.assertEqual('abc', svc.checkSne('abc'))
		with self.assertRaises(DFE) as cm_sne:
			svc.checkSne('')
		self.assertIn('token', cm_sne.exception.message())
		self.assertEqual('ok', svc.checkVar('ok'))
		with self.assertRaises(DFE):
			svc.checkVar('')
		self.assertEqual('ok', svc.checkRes('ok'))
		with self.assertRaises(DFE):
			svc.checkRes([1, 2])
		self.assertEqual('ok', svc.checkResSne('ok'))
		with self.assertRaises(DFE):
			svc.checkResSne('')
		frame = Frame.i({'class': f'{_SampleService.__module__}._SampleService', 'function': 'checkIso'})
		self.assertEqual('code', frame.methodParameter(0).name)
		with self.assertRaises(DFE):
			frame.methodParameter(5)
	# @used-by :mod:`unittest`
	def test_trace_and_failure(self) -> None:
		from Df.Core.Exception import Exception as DFE
		from Df.Qa.Failure.Exception import Exception as FailureException
		from Df.Qa.Trace import Trace
		from Df.Qa.Trace.Formatter import Formatter
		from Df.Qa.Trace.Frame import Frame
		tr = Trace([{'file': 'a.py', 'line': 10, 'class': 'C', 'function': 'm'}, {'file': 'phar://x', 'line': 1, 'function': 'p'}])
		self.assertEqual(1, len(tr))
		self.assertEqual('C::m', list(tr)[0].method())
		self.assertIn('1\tC::m', Formatter.p(tr))
		self.assertEqual('a.py', Frame.i({'file': 'a.py', 'line': 4}).file())
		err: BaseException | None = None
		try:
			raise ValueError('inner boom')
		except ValueError as exc:
			err = exc
		wrapped = DFE('<b>oops</b>', err)
		wrapped.markMessageAsHtml().context({'k': 'v'})
		rep = FailureException.i(wrapped).report()
		self.assertIn('oops', rep)
		self.assertNotIn('<b>', rep)
		self.assertIn('k', rep)
	# @used-by :mod:`unittest`
	def test_type_and_kv(self) -> None:
		from Df.Qa.lib.dump.kv import df_kv
		from Df.Qa.lib.dump.kv.table import df_kv_table
		from Df.Qa.lib.dump.type import df_type
		from Df.Zf.Validate.StringT.FloatT import FloatT
		from Df.Zf.Validate.StringT.IntT import IntT
		from Df.Zf.Validate.StringT.Iso2 import Iso2
		self.assertEqual('a: 1\nb: two', df_kv({'a': 1, 'b': 'two', 'c': ''}))
		self.assertEqual('a:   1', df_kv({'a': 1}, 5))
		self.assertEqual('<table>\n\t<tr>\n\t\t<td>a</td>\n\t\t<td>1</td>\n\t</tr>\n</table>', df_kv_table({'a': 1}))
		self.assertEqual('`null`', df_type(None))
		self.assertIn('an object:', df_type(_PlainObj(1)))
		self.assertIn('an array:', df_type([1, 2]))
		self.assertEqual('an array of 12 elements', df_type(list(range(12))))
		self.assertIn('(str)', df_type('hi'))
		self.assertFalse(FloatT.s().isValid(None))
		self.assertIn('`NULL`', FloatT.s().message())
		self.assertFalse(IntT.s().isValid('bad'))
		self.assertIn('an integer', IntT.s().message())
		self.assertFalse(Iso2.s().isValid('123'))
		self.assertIn('ISO 3166-1', next(iter(Iso2.s().getMessages().values())))
if '__main__' == __name__:
	unittest.main()