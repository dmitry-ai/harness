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
if '__main__' == __name__:
	unittest.main()