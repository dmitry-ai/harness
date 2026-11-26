# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import inspect
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
class DfCoreTextMiscTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_caller_and_reflection_param(self) -> None:
		from Df.Core.R.ConT import ConT
		from Df.Core.lib.caller.entry import df_caller_entry
		from Df.Core.lib.caller.other import df_caller_c, df_caller_f, df_caller_m, df_caller_mf, df_caller_mh, df_caller_ml
		from Df.Core.lib.reflection.param.is_.bool import dfr_param_is_bool
		from Df.Core.lib.reflection.param.type import dfr_param_type
		from Df.Core.lib.reflection.text.check import df_class_exists, df_class_my, df_is_abstract
		from Df.Core.lib.reflection.text.con_ import df_con_child, df_con_sibling
		# @used-by :meth:`DfCoreTextMiscTests.test_caller_and_reflection_param()`
		def sample(flag: bool) -> bool:
			return flag
		rp = list(inspect.signature(sample).parameters.values())[0]
		self.assertEqual(('bool', True), (dfr_param_type(rp), dfr_param_is_bool(rp)))
		self.assertTrue(df_class_exists('Df.Core.RAM.RAM') and df_class_my('Df\\Core\\RAM') and df_is_abstract('Df.Core.ICached.ICached'))
		self.assertEqual('Df.Core.Json.Json', ConT.p(False, lambda: df_con_sibling('Df.Core.RAM', 'Json.Json')))
		self.assertEqual('Df.Core.O.O', df_con_child('Df.Core', 'O.O'))
		# @used-by :meth:`DfCoreTextMiscTests.test_caller_and_reflection_param()`
		def probe_caller_f() -> str:
			return df_caller_f()
		self.assertEqual('test_caller_and_reflection_param', probe_caller_f())
		# @used-by :meth:`DfCoreTextMiscTests.test_caller_and_reflection_param()`
		def probe_caller_c() -> str:
			return df_caller_c()
		self.assertIn('DfCoreTextMiscTests', probe_caller_c())
		self.assertIn('::', df_caller_m())
		self.assertIn('::', df_caller_mf())
		self.assertTrue(df_caller_ml().endswith('()') and df_caller_mh().startswith('<b>'))
		self.assertIsInstance(df_caller_entry(), dict)
	# @used-by :mod:`unittest`
	def test_date_helpers(self) -> None:
		from Df.Core.lib.date import df_date, df_date_create, df_date_from_db, df_date_from_timestamp_14, df_date_gt, df_date_least, df_date_lt, df_date_max, df_date_min, df_date_parse, df_date_reset_time, df_date_to_db, df_day_of_week_as_digit, df_days_left, df_dts, df_dtss, df_hour, df_is_date_expired, df_month, df_now, df_num_days, df_today_add, df_today_sub, df_tomorrow, df_year, df_yesterday
		d1 = df_date_create(2026, 11, 26, 10, 0, 0)
		d2 = df_date_create(2026, 11, 28, 10, 0, 0)
		self.assertIsInstance(df_date(), datetime)
		self.assertEqual((2026, 11, 10, 4), (df_year(d1), df_month(d1), df_hour(d1), df_day_of_week_as_digit(d1)))
		self.assertTrue(df_date_lt(d1, d2) and df_date_gt(d2, d1))
		self.assertEqual((d1, d2, 2, 0), (df_date_min(d1, d2), df_date_max(d1, d2), df_num_days(d1, d2), df_date_reset_time(d1).hour))
		self.assertEqual((1970, 2013, 2026), (df_date_least().year, df_date_from_timestamp_14('20131115153657').year, df_date_from_db('2026-11-26T10:00:00').year))
		self.assertIn('2026-11-26', df_date_to_db(d1))
		self.assertEqual(2026, df_date_parse('2026-11-26', True, '%Y-%m-%d').year)
		self.assertEqual('26/11/2026', df_dtss('2026-11-26', '%Y-%m-%d', '%d/%m/%Y'))
		self.assertTrue(bool(df_dts(d1, '%Y-%m-%d')) and bool(df_now('%Y-%m-%d', 'UTC')))
		self.assertEqual(5, df_days_left(5))
		self.assertTrue(df_is_date_expired(datetime(2000, 1, 1, tzinfo=timezone.utc)))
		self.assertTrue(df_tomorrow() > df_yesterday() and df_today_add(2) > df_today_sub(2))
	# @used-by :mod:`unittest`
	def test_html_js_and_option(self) -> None:
		from Df.Core.Html.Tag import Tag
		from Df.Core.lib.html import df_html_b, df_style_inline, df_style_inline_hide, df_tag, df_tag_ab, df_tag_if, df_tag_if_ne, df_tag_list
		from Df.Core.lib.js.ejs import df_ejs
		from Df.Core.lib.js.window_data import df_js_data
		from Df.Core.lib.option import df_a_to_options, df_map_0, df_map_to_options, df_map_to_options_reverse, df_option, df_option_0, df_option_v, df_option_values, df_options_to_map
		self.assertEqual('<b>hi</b>', df_html_b('hi'))
		self.assertIn('style', df_style_inline('a{color:red}'))
		self.assertIn('display: none', df_style_inline_hide('.x'))
		self.assertEqual("<div class='c'>ok</div>", Tag('div', {'class': 'c'}, 'ok').render())
		self.assertEqual("<span class='a'>x</span>", df_tag('span', 'a', 'x'))
		self.assertIn("target='_blank'", df_tag_ab('go', 'https://a.test'))
		self.assertEqual(('<span>x</span>', ''), (df_tag_if('x', True, 'span'), df_tag_if_ne('', 'span')))
		self.assertIn('<li>a</li>', df_tag_list(['a']))
		self.assertEqual("'a\\u0027b'", df_ejs("a'b"))
		self.assertIn('window.app =', df_js_data('app', {'x': 1}))
		self.assertEqual([{'label': 'a', 'value': 'a'}], df_a_to_options(['a']))
		self.assertEqual({0: '-- select a value --', 'a': 'A'}, df_map_0({'a': 'A'}))
		self.assertEqual([{'label': 'A', 'value': 'a'}], df_map_to_options({'a': 'A'}))
		self.assertEqual([{'label': 'a', 'value': 'A'}], df_map_to_options_reverse({'a': 'A'}))
		self.assertEqual({'label': 'L', 'value': 'v'}, df_option('v', 'L'))
		self.assertEqual(2, len(df_option_0([df_option('a', 'A')], 'Pick')))
		self.assertEqual((['a'], {'a': 'A'}), (df_option_values([df_option('a', 'A')]), df_options_to_map([df_option('a', 'A')])))
		self.assertIsNotNone(df_option_v({'value': ['a'], 'label': 'A'}))
	# @used-by :mod:`unittest`
	def test_reflection_text(self) -> None:
		from Df.Core.lib.reflection.text.cc import df_cc_class, df_cc_class_uc, df_cc_method
		from Df.Core.lib.reflection.text.cts import df_cts, df_cts_lc, df_cts_lc_camel
		from Df.Core.lib.reflection.text.explode import df_explode_class, df_explode_class_camel, df_explode_class_lc, df_explode_class_lc_camel, df_explode_method
		from Df.Core.lib.reflection.text.other import df_class_file, df_class_replace_last, df_cld, df_const
		from Df.Core.lib.reflection.text.part import df_class_f, df_class_l, df_class_llc, df_class_second, df_class_second_lc, df_class_suffix
		self.assertEqual(('Aa\\Bb\\Cb', 'Aa\\Bb\\Cc', 'A::b'), (df_cc_class('Aa', ['Bb', 'Cb']), df_cc_class_uc('aa', ['bb', 'cc']), df_cc_method('A', 'b')))
		self.assertEqual(('Df\\Core\\RAM', 'df_core_rAM', 'dfe_checkout_com'), (df_cts('Df\\Core\\RAM'), df_cts_lc('Df\\Core\\RAM', '_'), df_cts_lc_camel('Dfe\\CheckoutCom', '_')))
		self.assertEqual(['Df', 'Core'], df_explode_class('Df\\Core'))
		self.assertEqual(['Dfe', 'Checkout', 'Com'], df_explode_class_camel('Dfe\\CheckoutCom'))
		self.assertEqual(['df', 'core'], df_explode_class_lc('Df\\Core'))
		self.assertEqual(['dfe', 'checkout', 'com'], df_explode_class_lc_camel('Dfe\\CheckoutCom'))
		self.assertEqual(['A', 'b'], df_explode_method('A::b'))
		self.assertTrue(df_class_file('Df.Core.RAM.RAM').endswith('RAM.py'))
		self.assertEqual(('Df\\Core\\Json', '\\', 'double'), (df_class_replace_last('Df\\Core\\RAM', 'Json'), df_cld('Df\\Core'), df_const('Df.Core.Helper.Text.Text', 'QUOTE__DOUBLE')))
		self.assertEqual(('Df', 'RAM', 'ram'), (df_class_f('Df\\Core\\RAM'), df_class_l('Df\\Core\\RAM'), df_class_llc('Df\\Core\\RAM')))
		self.assertEqual(('Core', 'core', 'RAM'), (df_class_second('Df\\Core\\RAM'), df_class_second_lc('Df\\Core\\RAM'), df_class_suffix('Df\\Core\\RAM')))
	# @used-by :mod:`unittest`
	def test_text_helpers_part1(self) -> None:
		from Df.Core.Helper.Text import Text
		from Df.Core.Text.Marker import Marker
		from Df.Core.Text.Regex import Regex
		from Df.Core.lib.text.camel import df_camel_to_underscore, df_explode_camel, df_underscore_to_camel
		from Df.Core.lib.text.concatenate import df_c, df_cc, df_cc_br, df_cc_s, df_ccc
		from Df.Core.lib.text.contains import df_contains
		from Df.Core.lib.text.contains.ci import df_contains_ci
		from Df.Core.lib.text.csv import df_csv, df_csv_parse, df_csv_parse_int, df_csv_pretty, df_csv_pretty_quote
		from Df.Core.lib.text.explode import df_explode_multiple, df_explode_path, df_explode_space, df_explode_url, df_explode_xpath
		from Df.Core.lib.text.filter import df_e, df_remove_non_digits, df_string_clean, df_translit
		from Df.Core.lib.text.format import df_desc, df_format, df_sprintf, df_sprintf_strict, df_var
		self.assertEqual('«a»', Text.s().quote('a'))
		mk = Marker('<![CDATA[', ']]>')
		self.assertEqual(('<![CDATA[x]]>', 'x'), (mk.mark('x'), mk.unmark('<![CDATA[x]]>')))
		self.assertTrue(bool(mk.marked('<![CDATA[x]]>')))
		self.assertEqual('42', Regex.i(r'#(\d+)#', 'id=42').match())
		self.assertEqual(('yandex_market', ['Dynamics', '365'], 'RefundIssued'), (df_camel_to_underscore('YandexMarket'), df_explode_camel('Dynamics365'), df_underscore_to_camel('REFUND_ISSUED')))
		self.assertEqual(('ab', 'a-b', 'a<br>b', 'a b', 'a:b'), (df_c('a', 'b'), df_cc('-', 'a', 'b'), df_cc_br('a', '', 'b'), df_cc_s('a', '', 'b'), df_ccc(':', 'a', '', 'b')))
		self.assertTrue(df_contains('hello world', 'world') and df_contains_ci('Hello', 'ell'))
		self.assertEqual(('a,b', ['a', 'b'], [1, 2], 'a, b', '«a», «b»'), (df_csv('a', 'b'), df_csv_parse('a, b'), df_csv_parse_int('1, 2'), df_csv_pretty('a', 'b'), df_csv_pretty_quote('a', 'b')))
		self.assertEqual((['a', 'b', 'c'], ['a', 'b'], ['a', 'b'], ['a', 'b'], ['a', 'b']), (df_explode_multiple(['.', '_'], 'a.b_c'), df_explode_path('a\\b'), df_explode_space(' a  b '), df_explode_url('a/b'), df_explode_xpath('a/b')))
		self.assertEqual(('&lt;&#x27;&gt;', '7962', 'ac', 'Ronan'), (df_e("<'>"), df_remove_non_digits('+79.6-2'), df_string_clean('abc', 'b'), df_translit('Rónán')))
		self.assertEqual(('a (b)', 'hi bob', 'hi 5', 'hi 5', 'hi X'), (df_desc('a', 'b'), df_format('hi {n}', {'{n}': 'bob'}), df_sprintf('hi %d', 5), df_sprintf_strict('hi %d', 5), df_var('hi {a}', {'a': 'X'})))
	# @used-by :mod:`unittest`
	def test_text_helpers_part2(self) -> None:
		from Df.Core.lib.text.is_.guid import df_is_guid
		from Df.Core.lib.text.main import DF_THIN_SPACE, df_string_split, df_strings_are_equal_ci, df_t, df_uid
		from Df.Core.lib.text.n.cc import df_cc_n
		from Df.Core.lib.text.n.explode import df_explode_n
		from Df.Core.lib.text.n.has import df_is_multiline
		from Df.Core.lib.text.n.normalize import df_normalize
		from Df.Core.lib.text.n.prepend import df_n_prepend
		from Df.Core.lib.text.n.remove import df_single_line
		from Df.Core.lib.text.parse import df_parse_colon
		from Df.Core.lib.text.prepend_append import df_append, df_prepend
		from Df.Core.lib.text.prepend_append.pad import df_pad
		from Df.Core.lib.text.prepend_append.pad0 import df_pad0
		from Df.Core.lib.text.prepend_append.tab import df_tab
		from Df.Core.lib.text.quote import df_quote_double, df_quote_russian, df_quote_single
		from Df.Core.lib.text.regex import df_preg_int, df_preg_match, df_preg_prefix, df_preg_test
		from Df.Core.lib.text.starts_ends import df_ends_with, df_starts_with
		from Df.Core.lib.text.transform import df_lcfirst, df_strtolower, df_strtoupper, df_ucfirst, df_ucwords
		from Df.Core.lib.text.trim import df_chop, df_trim, df_trim_left, df_trim_right, df_trim_text, df_trim_text_a, df_trim_text_left, df_trim_text_left_right, df_trim_text_right
		self.assertTrue(df_is_guid('A1B2C3D4-E5F6-7890-ABCD-EF1234567890'))
		self.assertEqual(('\u00a0', ['a', 'б'], True, 8), (DF_THIN_SPACE, df_string_split('aб'), df_strings_are_equal_ci('AbC', 'abc'), len(df_uid(8))))
		self.assertIsNotNone(df_t())
		self.assertEqual(('a\nb', ['a', 'b'], True, 'a\nb', '\nx', 'a b c'), (df_cc_n('a', '', 'b'), df_explode_n('a\r\nb'), df_is_multiline('a\nb'), df_normalize('a\r\nb'), df_n_prepend('x'), df_single_line('a\r\nb\tc')))
		self.assertEqual({'k': 'v'}, df_parse_colon('k: v'))
		self.assertEqual(('ab', 'ab', 'a  ', '007', '\ta\n\tb'), (df_append('a', 'b'), df_prepend('b', 'a'), df_pad('a', 3), df_pad0(3, '7'), df_tab('a\nb')))
		self.assertEqual(('"a"', '«a»', "'a'"), (df_quote_double('a'), df_quote_russian('a'), df_quote_single('a')))
		self.assertEqual((42, '42', 'bar', True), (df_preg_int(r'#(\d+)#', 'x42'), df_preg_match(r'#(\d+)#', 'x42'), df_preg_prefix('foo/', 'foo/bar'), df_preg_test(r'#\d+#', 'x42')))
		self.assertTrue(df_starts_with('abcdef', ['zz', 'ab']) and df_ends_with('abcdef', ['zz', 'ef']))
		self.assertEqual(('aBC', 'abc', 'ABC', 'Abc', 'Hi Bob'), (df_lcfirst('ABC'), df_strtolower('ABC'), df_strtoupper('abc'), df_ucfirst('abc'), df_ucwords('hi bob')))
		self.assertEqual(('ab…', 'hi', 'hi ', ' hi', 'mid', 'mid', 'mid', 'mid', 'mid'), (df_chop('abcdef', 3), df_trim(' hi '), df_trim_left(' hi '), df_trim_right(' hi '), df_trim_text('xmidx', 'x'), df_trim_text_a('xmid', ['y', 'x'], df_trim_text_left), df_trim_text_left('xmid', 'x'), df_trim_text_left_right('[mid]', '[', ']'), df_trim_text_right('midx', 'x')))
if '__main__' == __name__:
	unittest.main()
