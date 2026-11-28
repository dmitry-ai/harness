# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from Df.Harness.Issue.IssueFirstEvaluator import IssueFirstEvaluator
from Df.Harness.lib.issue import dfh_is_df_issue_command_text
# 2026-11-28 "Evaluate Issue-First parent state chronologically and recognize PowerShell foreach": https://github.com/dmitry-ai/harness/issues/437
class IssueFirstPostCloseReplayTests(unittest.TestCase):
	# @used-by :meth:`IssueFirstPostCloseReplayTests.test_child_create_against_already_closed_parent_still_fails()`
	# @used-by :meth:`IssueFirstPostCloseReplayTests.test_parent_closed_later_in_same_turn_does_not_fail_earlier_child_create()`
	# @used-by :meth:`IssueFirstPostCloseReplayTests.test_retroactive_edit_parent_does_not_backfill_earlier_standalone_create()`
	@staticmethod
	def __write_issue(root: Path, slug: str, number: int, state: str, *, parent_number: int | None=None) -> None:
		ev_dir = root / '\ua616/KB/Evidence/GitHub' / slug.replace('/', '__')
		ev_dir.mkdir(parents=True, exist_ok=True)
		body = f'Parent: https://github.com/{slug}/issues/{parent_number}\n' if None is not parent_number else 'Problem statement.\n'
		payload = {'number': number, 'repo': slug, 'state': state, 'issue': {'number': number, 'state': state, 'body': body}}
		if None is not parent_number:
			payload['parent_number'] = parent_number
		(ev_dir / f'issue-{number}.json').write_text(json.dumps(payload), encoding='utf-8')
	# @used-by :mod:`unittest`
	def test_child_create_against_already_closed_parent_still_fails(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			slug = 'owner/repo'
			self.__write_issue(root, slug, 345, 'closed')
			self.__write_issue(root, slug, 367, 'open', parent_number=345)
			prior_closed_events = [{'kind': 'issue_action', 'step': 2, 'repo': slug, 'number': 367, 'action': 'create', 'parent_number': 345}]
			res_prior = IssueFirstEvaluator(prior_closed_events, project_root=root).evaluate()
			self.assertFalse(res_prior['verified'])
			self.assertTrue(any(('links to closed parent issue #345' in v for v in res_prior['violations'])))
			same_turn_closed_events = [
				{'kind': 'issue_action', 'step': 1, 'repo': slug, 'number': 345, 'action': 'fetch', 'state': 'open'},
				{'kind': 'issue_action', 'step': 2, 'repo': slug, 'number': 345, 'action': 'close', 'state': 'closed'},
				{'kind': 'issue_action', 'step': 3, 'repo': slug, 'number': 367, 'action': 'create', 'parent_number': 345},
			]
			res_same = IssueFirstEvaluator(same_turn_closed_events, project_root=root).evaluate()
			self.assertFalse(res_same['verified'])
			self.assertTrue(any(('links to closed parent issue #345' in v for v in res_same['violations'])))
	# @used-by :mod:`unittest`
	def test_df_issue_cmd_recognizes_powershell_foreach_and_rejects_echo(self) -> None:
		self.assertTrue(dfh_is_df_issue_command_text('foreach ($n in 345,346) { python "C:/repo/scripts/df_github_issue.py" fetch --repo owner/repo --issue $n }'))
		self.assertTrue(dfh_is_df_issue_command_text('345,346 | ForEach-Object { & "C:/tools/python/3.15.2/python.exe" "C:/repo/scripts/df_github_issue.py" fetch --repo owner/repo --issue $_ }'))
		self.assertTrue(dfh_is_df_issue_command_text('$cli = "C:/repo/scripts/df_github_issue.py"; foreach ($n in 1,2) { python $cli fetch --repo owner/repo --issue $n }'))
		self.assertFalse(dfh_is_df_issue_command_text('Write-Output "df_github_issue.py fetch --repo owner/repo --issue 1"'))
		self.assertFalse(dfh_is_df_issue_command_text('foreach ($n in 1,2) { python -c "print(\'df_github_issue.py fetch\')" }'))
	# @used-by :mod:`unittest`
	def test_parent_closed_later_in_same_turn_does_not_fail_earlier_child_create(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			slug = 'owner/repo'
			self.__write_issue(root, slug, 345, 'closed')
			self.__write_issue(root, slug, 367, 'closed', parent_number=345)
			events = [
				{'kind': 'issue_action', 'step': 1, 'repo': slug, 'number': 345, 'action': 'fetch', 'state': 'open'},
				{'kind': 'issue_action', 'step': 2, 'repo': slug, 'number': 367, 'action': 'create', 'parent_number': 345},
				{'kind': 'code_write', 'step': 3, 'repo_slug': slug, 'repo_root': str(root), 'rel_path': 'scripts/mod.py', 'classification': 'production'},
				{'kind': 'issue_action', 'step': 4, 'repo': slug, 'number': 367, 'action': 'close', 'state': 'closed'},
				{'kind': 'issue_action', 'step': 5, 'repo': slug, 'number': 345, 'action': 'close', 'state': 'closed'},
			]
			res = IssueFirstEvaluator(events, project_root=root).evaluate()
			self.assertTrue(res['verified'], res['violations'])
			self.assertEqual([], res['violations'])
			seeded_events = [
				{'kind': 'issue_action', 'step': 2, 'repo': slug, 'number': 367, 'action': 'create', 'parent_number': 345},
				{'kind': 'code_write', 'step': 3, 'repo_slug': slug, 'repo_root': str(root), 'rel_path': 'scripts/mod.py', 'classification': 'production'},
				{'kind': 'issue_action', 'step': 5, 'repo': slug, 'number': 345, 'action': 'close', 'state': 'closed'},
			]
			res_seeded = IssueFirstEvaluator(seeded_events, requests=['Fix #345'], project_root=root).evaluate()
			self.assertTrue(res_seeded['verified'], res_seeded['violations'])
	# @used-by :mod:`unittest`
	def test_retroactive_edit_parent_does_not_backfill_earlier_standalone_create(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			slug = 'owner/repo'
			self.__write_issue(root, slug, 343, 'closed')
			self.__write_issue(root, slug, 344, 'closed', parent_number=343)
			self.__write_issue(root, slug, 388, 'closed', parent_number=343)
			events = [
				{'kind': 'issue_action', 'step': 1, 'repo': slug, 'number': 343, 'action': 'fetch', 'state': 'open'},
				{'kind': 'issue_action', 'step': 2, 'repo': slug, 'number': 344, 'action': 'create', 'parent_number': 343},
				{'kind': 'code_write', 'step': 3, 'repo_slug': slug, 'repo_root': str(root), 'rel_path': 'scripts/a.py', 'classification': 'production'},
				{'kind': 'issue_action', 'step': 4, 'repo': slug, 'number': 343, 'action': 'close', 'state': 'closed'},
				{'kind': 'issue_action', 'step': 5, 'repo': slug, 'number': 388, 'action': 'create', 'state': 'open'},
				{'kind': 'code_write', 'step': 6, 'repo_slug': slug, 'repo_root': str(root), 'rel_path': 'scripts/b.py', 'classification': 'production'},
				{'kind': 'issue_action', 'step': 7, 'repo': slug, 'number': 388, 'action': 'edit', 'parent_number': 343, 'state': 'open'},
				{'kind': 'issue_action', 'step': 8, 'repo': slug, 'number': 388, 'action': 'close', 'state': 'closed'},
			]
			res = IssueFirstEvaluator(events, project_root=root).evaluate()
			self.assertTrue(res['verified'], res['violations'])
			self.assertEqual([], res['violations'])
if '__main__' == __name__:
	unittest.main()
