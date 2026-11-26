# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope budget_check graceful checkpoint flag to client-artifact projects":
# https://github.com/dmitry-ai/harness/issues/369
from __future__ import annotations
from pathlib import Path
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion, links
import check_markdown_slop
# @used-by :meth:`BudgetStatusScopingTests.test_client_project_ignores_delivered_history_and_triggers_on_active_budget()`
# @used-by :meth:`BudgetStatusScopingTests.test_code_project_never_flags_graceful_checkpoint_from_history_or_steps()`
def _seed_turn_file(turns_dir: Path, name: str, *, turn_id: str, status: str, steps: int) -> None:
	turns_dir.mkdir(parents=True, exist_ok=True)
	payload = {'native_turn_id': turn_id, 'status': status, 'delegation_check': {'tool_step_count': steps}}
	(turns_dir / f'{name}.json').write_text(json.dumps(payload), encoding='utf-8')
# 2026-11-26
# "Scope budget_check graceful checkpoint flag to client-artifact projects":
# https://github.com/dmitry-ai/harness/issues/369
class BudgetStatusScopingTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_client_project_ignores_delivered_history_and_triggers_on_active_budget(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'upwork-job'
			(proj / '\ua616').mkdir(parents=True)
			(proj / '\ua616/project.json').write_text(json.dumps({'job_id': '~999'}), encoding='utf-8')
			turns_dir = proj / '\ua616/data/turns'
			_seed_turn_file(turns_dir, 'old1', turn_id='ag-old-1', status='delivered', steps=8000)
			_seed_turn_file(turns_dir, 'old2', turn_id='ag-old-2', status='handed_off', steps=500)
			fresh = {'turn_id': 'ag-cur-1', 'compaction': {'checkpoint_steps': []}, 'delegation': {'tool_step_count': 2}, 'touched_files': []}
			st_fresh = completion._budget_status(proj, fresh)
			self.assertTrue(st_fresh['client_artifacts_scoped'])
			self.assertFalse(st_fresh['graceful_checkpoint_required'], st_fresh)
			self.assertEqual(2, st_fresh['window_5h_tool_steps'])
			heavy = {'turn_id': 'ag-cur-2', 'compaction': {'checkpoint_steps': [10, 20]}, 'delegation': {'tool_step_count': 5}, 'touched_files': []}
			st_heavy = completion._budget_status(proj, heavy)
			self.assertTrue(st_heavy['graceful_checkpoint_required'], st_heavy)
			_seed_turn_file(turns_dir, 'active_other', turn_id='ag-open-9', status='open', steps=410)
			st_open = completion._budget_status(proj, fresh)
			self.assertTrue(st_open['graceful_checkpoint_required'], st_open)
			self.assertEqual(412, st_open['window_5h_tool_steps'])
	# @used-by :mod:`unittest`
	def test_code_project_never_flags_graceful_checkpoint_from_history_or_steps(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'code-repo'
			turns_dir = proj / '\ua616/data/turns'
			_seed_turn_file(turns_dir, 'prev1', turn_id='ag-prev-1', status='delivered', steps=8131)
			_seed_turn_file(turns_dir, 'prev2', turn_id='ag-prev-2', status='open', steps=500)
			fresh = {'turn_id': 'ag-fresh-1', 'compaction': {'checkpoint_steps': []}, 'delegation': {'tool_step_count': 2}, 'touched_files': []}
			st = completion._budget_status(proj, fresh)
			self.assertFalse(st['client_artifacts_scoped'])
			self.assertFalse(st['graceful_checkpoint_required'], st)
			self.assertEqual(2, st['window_5h_tool_steps'])
			heavy = {'turn_id': 'ag-fresh-2', 'compaction': {'checkpoint_steps': [5, 10, 15]}, 'delegation': {'tool_step_count': 288}, 'touched_files': []}
			st_heavy = completion._budget_status(proj, heavy)
			self.assertFalse(st_heavy['graceful_checkpoint_required'], st_heavy)
	# @used-by :mod:`unittest`
	def test_turn_completion_doc_describes_client_artifact_budget_scoping(self) -> None:
		doc = WT_ROOT / 'references/turn-completion.md'
		text = doc.read_text(encoding='utf-8')
		self.assertIn('\ua616/project.json', text)
		self.assertEqual([], links.validate_file(doc, local_anchors=True, readable_links=True))
		self.assertEqual([], check_markdown_slop.markdown_slop_issues(text))
if '__main__' == __name__:
	unittest.main()
