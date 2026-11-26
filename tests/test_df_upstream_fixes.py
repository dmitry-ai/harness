# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
class TestDfUpstreamFixes(unittest.TestCase):
	# 2026-11-26 "Fix Df\Core\Exception::__construct() checking $prev instead of $a1 for stack levels": https://github.com/dmitry-ai/harness/issues/326
	# Upstream defect: https://github.com/mage2pro/core/issues/469
	# @used-by :mod:`unittest`
	def test_326_exception_stack_levels(self) -> None:
		from Df.Core.Exception import Exception as DFE
		ex = DFE('boom', 2)
		self.assertEqual(2, ex.getStackLevelsCountToSkip())
	# 2026-11-26 "Fix dff_eq() returning False for zero and negative equal values": https://github.com/dmitry-ai/harness/issues/327
	# Upstream defect: https://github.com/mage2pro/core/issues/470
	# @used-by :mod:`unittest`
	def test_327_dff_eq_zero_and_negative(self) -> None:
		from Df.Core.lib.float import dff_eq
		self.assertTrue(dff_eq(0, 0))
		self.assertTrue(dff_eq(-10.0, -10.0))
		self.assertTrue(dff_eq(-100.0, -100.05))
		self.assertFalse(dff_eq(-100.0, -101.0))
	# 2026-11-26 "Fix Marker::marked() return type to bool": https://github.com/dmitry-ai/harness/issues/328
	# Upstream defect: https://github.com/mage2pro/core/issues/471
	# @used-by :mod:`unittest`
	def test_328_marker_marked_returns_bool(self) -> None:
		from Df.Core.Text.Marker import Marker
		mk = Marker('<![CDATA[', ']]>')
		self.assertIs(True, mk.marked('<![CDATA[x]]>'))
		self.assertIs(False, mk.marked('x'))
	# 2026-11-26 "Fix df_option_0() passing None default label to df_map_0()": https://github.com/dmitry-ai/harness/issues/329
	# Upstream defect: https://github.com/mage2pro/core/issues/472
	# @used-by :mod:`unittest`
	def test_329_df_option_0_default_label(self) -> None:
		from Df.Core.lib.option import df_option, df_option_0
		r = df_option_0([df_option('a', 'A')])
		self.assertEqual([{'label': '-- select a value --', 'value': 0}, {'label': 'A', 'value': 'a'}], r)
	# 2026-11-26 "Fix df_option_v() rejecting scalar option values": https://github.com/dmitry-ai/harness/issues/330
	# Upstream defect: https://github.com/mage2pro/core/issues/473
	# @used-by :mod:`unittest`
	def test_330_df_option_v_returns_scalar(self) -> None:
		from Df.Core.lib.option import df_option_v
		self.assertEqual('US', df_option_v({'value': 'US', 'label': 'USA'}))
		self.assertEqual('fallback', df_option_v({}, 'fallback'))
if '__main__' == __name__:
	unittest.main()