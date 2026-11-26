# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import unittest
REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26
# "Apply cross-reference annotations across Harness Python and JavaScript":
# https://github.com/dmitry-ai/harness/issues/305
class HarnessXrefComplianceTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_harness_python_and_js_pass_xref_check_with_zero_issues(self) -> None:
		from agent_tools.xref import run_xref_check
		res = run_xref_check(REPO_ROOT, lang='all')
		self.assertGreater(res['file_count'], 300)
		self.assertTrue(res['valid'], '\n'.join(res['issues'][:25]))
if '__main__' == __name__:
	unittest.main()
