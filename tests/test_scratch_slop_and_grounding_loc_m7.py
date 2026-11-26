# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import source_grounding
import check_markdown_slop
# 2026-11-24
# "Skip blocking grounding on scratch drafts and add line locations to diagnostics":
# https://github.com/dmitry-ai/harness/issues/214
class ScratchSlopAndGroundingLocM7Tests(unittest.TestCase):
	def _make_project(self, root: Path) -> Path:
		ev = root / '\ua616/KB/Evidence/HTTP/abc123/response.bin'
		ev.parent.mkdir(parents=True, exist_ok=True)
		ev.write_text('GTM-PPXJGN container payload without unrelated ids\n', encoding='utf-8')
		(root / '\ua616/data/scratch').mkdir(parents=True, exist_ok=True)
		return ev
	def test_scratch_draft_defers_grounding_but_keeps_doc4_syntax_checks(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			ev = self._make_project(root)
			scratch = root / '\ua616/data/scratch/answer-deadbeef.md'
			ungrounded = f'# Summary\n\nObserved chunk `7264` in [GTM](<{ev.as_posix()}>).  \n'
			self.assertIsNone(check_markdown_slop.check_markdown_content(ungrounded, str(scratch)))
			bad_table = '| A | B |\n| --- | --- |\n| 1 | 2 |\n'
			self.assertIsNotNone(check_markdown_slop.check_markdown_content(bad_table, str(scratch)))
			bad_doc4 = 'First sentence here. Second sentence on same line.\n'
			self.assertIsNotNone(check_markdown_slop.check_markdown_content(bad_doc4, str(scratch)))
			errs = source_grounding.local_source_grounding_issues(root, ungrounded, doc_path=scratch)
			self.assertEqual(1, len(errs), errs)
			self.assertIn('\ua616/KB/Evidence/HTTP/abc123/response.bin', errs[0])
			self.assertIn('line 3', errs[0])
	def test_non_scratch_md_reports_all_unique_grounding_issues_with_line_numbers_and_relpaths(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			ev = self._make_project(root)
			kb_file = root / '\ua616/KB/Website.md'
			doc = '\n'.join([
				'# Findings',
				'',
				f'Primary capture: [GTM](<{ev.as_posix()}>).  ',
				'Line four reports 11111 events.  ',
				'Line five reports 22222 events.  ',
				'Line six reports 33333 events.  ',
				'Line seven reports 44444 events.  ',
				'Line eight reports 55555 events.  ',
				'',
			])
			violation = check_markdown_slop.check_markdown_content(doc, str(kb_file))
			self.assertIsNotNone(violation)
			for num, line_no in (('11111', 4), ('22222', 5), ('33333', 6), ('44444', 7), ('55555', 8)):
				self.assertIn(num, violation)
				self.assertIn(f'line {line_no}', violation)
			self.assertIn('\ua616/KB/Evidence/HTTP/abc123/response.bin', violation)
if '__main__' == __name__:
	unittest.main()
