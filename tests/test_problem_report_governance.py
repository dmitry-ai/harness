# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for _p in (SCRIPTS, TESTS):
	if str(_p) not in sys.path:
		sys.path.insert(0, str(_p))
from Df.Harness.Grounding.ProblemIssueSpecification import ProblemIssueSpecification
from agent_tools import statements
from git_fixture_cache import run_harness_inprocess
from problem_report_fixtures import ProblemReportFixtureBuilder
_FOREIGN_CID = '99999999-aaaa-4bbb-8ccc-dddddddddddd'
# 2026-11-28 "Implement hierarchical mixed-turn DOC-5 parser and problem-issue specification": https://github.com/dmitry-ai/harness/issues/428
# @used-by :mod:`unittest`
class ProblemReportGovernanceTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_mixed_turn_hierarchical_schema_accepts_valid_and_rejects_flat_or_missing_sections(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			b: ProblemReportFixtureBuilder = ProblemReportFixtureBuilder(Path(td)).with_git_repo().add_issue(501).add_issue(502)
			ctx = b.build_workspace()
			turn_ctx = {'root': ctx['root'], 'turn': ctx['turn'], 'turn_state': ctx['turn_state']}
			good = b.mixed_problem_markdown([{'title': 'Сбой хука', 'issue': 'https://github.com/dmitry-ai/harness/issues/501'}, {'title': 'Пробел гейта', 'issue': 'https://github.com/dmitry-ai/harness/issues/502'}])
			self.assertEqual([], statements.validate_df_analysis(good, requests=ctx['requests'], mode='auto', turn_context=turn_ctx))
			ascii_good = b.mixed_problem_markdown([{'title': 'First issue', 'issue': 'https://github.com/dmitry-ai/harness/issues/501'}], part1_title='# I. Completed Work', part2_title='# II. New Problems')
			self.assertEqual([], statements.validate_df_analysis(ascii_good, requests=ctx['requests'], mode='auto', turn_context=turn_ctx))
			extra_h1 = b.mixed_problem_markdown([{'title': 'Сбой хука', 'issue': 'https://github.com/dmitry-ai/harness/issues/501'}], extra_h1='# Лишний верхний раздел')
			errs_h1 = statements.validate_df_analysis(extra_h1, requests=ctx['requests'], mode='auto', turn_context=turn_ctx)
			self.assertTrue(any('level-1' in e.lower() or 'h1' in e.lower() or '# ' in e for e in errs_h1), errs_h1)
			missing_plan = good.replace('### 1.6. Рекомендуемый план устранения\n\nРеализовать `M-1-1` отдельной задачей по открытому родительскому issue и подтвердить тестами.  \n', '')
			errs_plan = statements.validate_df_analysis(missing_plan, requests=ctx['requests'], mode='auto', turn_context=turn_ctx)
			self.assertTrue(any('1.6' in e or 'plan' in e.lower() for e in errs_plan), errs_plan)
	# @used-by :mod:`unittest`
	def test_problem_issue_specification_rejects_duplicate_closed_child_unverified_null_and_foreign_issues(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			b: ProblemReportFixtureBuilder = ProblemReportFixtureBuilder(Path(td)).with_git_repo().add_issue(501).add_issue(502, state='closed').add_issue(503, parent_number=406).add_issue(504, owner_cid=_FOREIGN_CID, owner_turn_key='tk-foreign-99', action=None).add_issue(505, action='fetch')
			ctx = b.build_workspace()
			self.assertTrue(ProblemIssueSpecification.is_valid_open_parent_issue(ctx['root'], 'dmitry-ai/harness', 501))
			self.assertFalse(ProblemIssueSpecification.is_valid_open_parent_issue(ctx['root'], 'dmitry-ai/harness', 502))
			self.assertFalse(ProblemIssueSpecification.is_valid_open_parent_issue(ctx['root'], 'dmitry-ai/harness', 503))
			turn_ctx = {'root': ctx['root'], 'turn': ctx['turn'], 'turn_state': ctx['turn_state']}
			cases = (
				('duplicate', [{'issue': 'https://github.com/dmitry-ai/harness/issues/501'}, {'issue': 'https://github.com/dmitry-ai/harness/issues/501'}], 'DUPLICATE_PROBLEM_ISSUE'),
				('closed', [{'issue': 'https://github.com/dmitry-ai/harness/issues/502'}], 'CLOSED_PROBLEM_ISSUE'),
				('child', [{'issue': 'https://github.com/dmitry-ai/harness/issues/503'}], 'CHILD_PROBLEM_ISSUE'),
				('foreign_cid', [{'issue': 'https://github.com/dmitry-ai/harness/issues/504'}], 'FOREIGN_PROBLEM_ISSUE'),
				('fetched_not_created', [{'issue': 'https://github.com/dmitry-ai/harness/issues/505'}], 'FOREIGN_PROBLEM_ISSUE'),
				('fabricated', [{'issue': 'https://github.com/dmitry-ai/harness/issues/99999'}], 'UNVERIFIED_PROBLEM_ISSUE'),
				('null_in_github_repo', [{'issue': None}], 'Issue'),
			)
			for name, specs, expected_code in cases:
				with self.subTest(case=name):
					doc = b.mixed_problem_markdown(specs)
					errs = statements.validate_df_analysis(doc, requests=ctx['requests'], mode='auto', turn_context=turn_ctx)
					self.assertTrue(any(expected_code in e for e in errs), (name, errs))
	# @used-by :mod:`unittest`
	def test_standalone_four_track_accepts_nested_and_rejects_flat_h1_and_allows_user_requested_open_issue(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			b: ProblemReportFixtureBuilder = ProblemReportFixtureBuilder(Path(td)).with_git_repo().add_issue(601).add_issue(602).add_issue(603).add_issue(604, owner_cid=_FOREIGN_CID, owner_turn_key='tk-old', action='fetch')
			ctx = b.build_workspace(requests=[{'id': 'r1', 'text': 'Разбери открытый https://github.com/dmitry-ai/harness/issues/604'}])
			reqs = ctx['requests']
			turn_ctx = {'root': ctx['root'], 'turn': ctx['turn'], 'turn_state': ctx['turn_state']}
			urls = ('https://github.com/dmitry-ai/harness/issues/604', 'https://github.com/dmitry-ai/harness/issues/601', 'https://github.com/dmitry-ai/harness/issues/602', None)
			nested_ok = b.standalone_four_track_markdown(urls, flat_h1=False)
			self.assertEqual([], statements.validate_df_analysis(nested_ok, requests=reqs, mode='auto', turn_context=turn_ctx))
			flat_bad = b.standalone_four_track_markdown(urls, flat_h1=True)
			errs_flat = statements.validate_df_analysis(flat_bad, requests=reqs, mode='auto', turn_context=turn_ctx)
			self.assertTrue(any('flat' in e.lower() or 'level-1' in e.lower() for e in errs_flat), errs_flat)
			rf = ctx['root'] / 'cand.md'
			rf.write_text(b.mixed_problem_markdown([{'issue': 'https://github.com/dmitry-ai/harness/issues/99999'}]), encoding='utf-8')
			proc = run_harness_inprocess(['analysis-check', str(ctx['root']), '--response-file', str(rf), '--mode', 'auto'])
			self.assertEqual(2, proc.returncode, proc.stdout or proc.stderr)
			self.assertIn('UNVERIFIED_PROBLEM_ISSUE', json.dumps(json.loads(proc.stdout)))
if '__main__' == __name__:
	unittest.main()
