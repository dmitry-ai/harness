# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
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
	# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
	# @used-by :mod:`unittest`
	def test_problem_report_evaluator_answer_gates_preparer_and_stop_gate_pipeline(self) -> None:
		from Df.Harness.Gate.StopChecksGate import StopChecksGate
		from Df.Harness.Grounding.ProblemReportEvaluator import ProblemReportEvaluator
		from agent_tools import completion
		with tempfile.TemporaryDirectory() as td:
			b: ProblemReportFixtureBuilder = ProblemReportFixtureBuilder(Path(td)).with_git_repo().add_issue(501).add_issue(502, state='closed')
			ctx = b.build_workspace()
			ev_file = ctx['root'] / 'log.txt'
			ev_file.write_text('exit status 1, timeout reached\n', encoding='utf-8')
			src_link = f'file:///{ev_file.as_posix()}'
			good_md = b.mixed_problem_markdown([{'issue': 'https://github.com/dmitry-ai/harness/issues/501'}], src_link=src_link)
			bad_md = b.mixed_problem_markdown([{'issue': 'https://github.com/dmitry-ai/harness/issues/502'}], src_link=src_link)
			self.assertTrue(ProblemReportEvaluator(ctx['root'], ctx['turn'], ctx['turn_state'], good_md, requests=ctx['requests']).evaluate()['verified'])
			bad_eval = ProblemReportEvaluator(ctx['root'], ctx['turn'], ctx['turn_state'], bad_md, requests=ctx['requests']).evaluate()
			self.assertFalse(bad_eval['verified'])
			self.assertTrue(any(('CLOSED_PROBLEM_ISSUE' in v for v in bad_eval['violations'])), bad_eval)
			fails: list[tuple[str, str]] = []
			runner = SimpleNamespace(root=ctx['root'], turn=ctx['turn'], value=dict(ctx['turn_state']), response=bad_md, native=None, _fail_gate=lambda g, m: fails.append((g, m)))
			ProblemReportEvaluator.check_runner(runner)
			self.assertFalse(runner.value['problem_report_check']['verified'])
			self.assertEqual('problem_report', fails[0][0])
			native = {'platform': 'antigravity', 'conversation_id': ctx['cid'], 'native_backend': td, 'source_file': '', 'primary': True, 'turns': [ctx['turn']], 'active_turn_id': ctx['turn']['turn_id']}
			with patch.object(completion, '_native', return_value=native):
				chk_bad = completion.check_answer(ctx['root'], bad_md, conversation=ctx['cid'], platform='antigravity')
				self.assertFalse(chk_bad['valid'], chk_bad)
				self.assertFalse(chk_bad['checks']['problem_report'], chk_bad)
				self.assertTrue(chk_bad['checks']['source_grounding'], chk_bad['issues'])
				self.assertTrue(any(('problem_report' == i.get('gate_id') for i in chk_bad['issues'])), chk_bad['issues'])
				chk_ok = completion.check_answer(ctx['root'], good_md, conversation=ctx['cid'], platform='antigravity')
				self.assertTrue(chk_ok['checks']['problem_report'], chk_ok['issues'])
			stop_hit = StopChecksGate().run({'status': 'prepared', 'prepared': {}, 'readiness_check': {'verified': True}, 'problem_report_check': {'verified': False, 'violations': ['CLOSED_PROBLEM_ISSUE']}})
			self.assertIsNotNone(stop_hit)
			self.assertIn('CLOSED_PROBLEM_ISSUE', stop_hit['reason'])
			self.assertIsNone(StopChecksGate().run({'status': 'prepared', 'prepared': {}, 'readiness_check': {'verified': True}, 'problem_report_check': {'verified': True, 'violations': []}}))
	# 2026-11-28 "Wire ProblemReportEvaluator into answer-check, answer-prepare, Stop Gate, TurnAuditor, and CrashAuditor": https://github.com/dmitry-ai/harness/issues/430
	# @used-by :mod:`unittest`
	def test_turn_auditor_enforces_mixed_turn_problem_filing_without_false_positive_on_plain_code_turn(self) -> None:
		from Df.Harness.Issue.TurnAuditor import TurnAuditor
		with tempfile.TemporaryDirectory() as td:
			b: ProblemReportFixtureBuilder = ProblemReportFixtureBuilder(Path(td)).with_git_repo().add_issue(501).add_issue(502, state='closed')
			code_file = Path(td).resolve() / 'proj/\u2c0f/\u227b/\u2655/\u26ef/app.py'
			ctx = b.build_workspace(touched_files=[str(code_file)])
			closed_only_turn = {**ctx['turn'], 'issue_actions': [a for a in ctx['turn']['issue_actions'] if 502 == a['number']]}
			closed_only_state = {**ctx['turn_state'], 'github_issues': {k: v for k, v in ctx['turn_state']['github_issues'].items() if 502 == v['number']}}
			mixed_closed = b.mixed_problem_markdown([{'issue': 'https://github.com/dmitry-ai/harness/issues/502'}])
			aud_bad = TurnAuditor(ctx['root'], closed_only_turn, closed_only_state, response=mixed_closed).audit()
			self.assertTrue(any(('Diagnostic audit of dmitry-ai/harness' in v for v in aud_bad['violations'])), aud_bad['violations'])
			mixed_open = b.mixed_problem_markdown([{'issue': 'https://github.com/dmitry-ai/harness/issues/501'}])
			aud_ok = TurnAuditor(ctx['root'], ctx['turn'], ctx['turn_state'], response=mixed_open).audit()
			self.assertFalse(any(('Diagnostic audit of dmitry-ai/harness' in v for v in aud_ok['violations'])), aud_ok['violations'])
			plain_done = 'Implemented `M-1` fixing `C-1` in `app.py` and closed task issue https://github.com/dmitry-ai/harness/issues/502.  \n'
			aud_plain = TurnAuditor(ctx['root'], closed_only_turn, closed_only_state, response=plain_done).audit()
			self.assertFalse(any(('Diagnostic audit of dmitry-ai/harness' in v for v in aud_plain['violations'])), aud_plain['violations'])
	# 2026-11-28 "Build ProblemReportFixtureBuilder and full positive/negative regression matrix": https://github.com/dmitry-ai/harness/issues/431
	# @used-by :mod:`unittest`
	def test_mixed_schema_edge_cases_and_tempdir_isolation(self) -> None:
		from Df.Harness.Grounding.MixedTurnProblemSchema import MixedTurnProblemSchema
		with tempfile.TemporaryDirectory() as td:
			b: ProblemReportFixtureBuilder = ProblemReportFixtureBuilder(Path(td)).with_git_repo().add_issue(501)
			ctx = b.build_workspace()
			turn_ctx = {'root': ctx['root'], 'turn': ctx['turn'], 'turn_state': ctx['turn_state']}
			self.assertEqual([], ProblemIssueSpecification.find_evidence_files(ctx['root'], 'dmitry-ai/harness', 406))
			empty_p2 = '# \U0001d678. Что сделано\n\nГотово.  \n\n# \U0001d678\U0001d678. Новые проблемы\n\n### 1. Неверный уровень\n\n# \U0001d678\U0001d678. Новые проблемы\n'
			errs_empty = statements.validate_df_analysis(empty_p2, requests=ctx['requests'], mode='auto', turn_context=turn_ctx)
			self.assertTrue(any(('only one' in e for e in errs_empty)), errs_empty)
			self.assertTrue(any(('level-2' in e for e in errs_empty)), errs_empty)
			bad_sub_lvl = b.mixed_problem_markdown([{'issue': 'https://github.com/dmitry-ai/harness/issues/501'}]).replace('### 1.1. Метаданные', '#### 1.1. Метаданные')
			errs_sub = statements.validate_df_analysis(bad_sub_lvl, requests=ctx['requests'], mode='auto', turn_context=turn_ctx)
			self.assertTrue(any(('level-3' in e for e in errs_sub)), errs_sub)
			short_slots = b.mixed_problem_markdown([{'issue': 'https://github.com/dmitry-ai/harness/issues/501'}]).replace('Дефект внесён в базовом модуле Harness (`dmitry-ai/harness`); действующие тесты и шлюз `answer-check` пропустили его, обхода Журнала `ꙮ` не зафиксировано.', 'Коротко.').replace('Реализовать `M-1-1` отдельной задачей по открытому родительскому issue и подтвердить тестами.', 'План.')
			errs_short = statements.validate_df_analysis(short_slots, requests=ctx['requests'], mode='auto', turn_context=turn_ctx)
			self.assertTrue(any(('1.4' in e for e in errs_short)), errs_short)
			self.assertTrue(any(('1.6' in e for e in errs_short)), errs_short)
			scatter_md = b.mixed_problem_markdown([{'issue': 'https://github.com/dmitry-ai/harness/issues/501', 'm1_extra': '- Вынести кэш в `%LOCALAPPDATA%/harness/tmp`.  \n'}])
			self.assertTrue(any(('FILE-6' in e for e in statements.validate_df_analysis(scatter_md, requests=ctx['requests'], mode='auto', turn_context=turn_ctx))))
			all_null = b.standalone_four_track_markdown((None, None, None, None), flat_h1=False)
			self.assertTrue(any(('NULL_PROBLEM_ISSUE' in e for e in statements.validate_df_analysis(all_null, requests=ctx['requests'], mode='auto', turn_context=turn_ctx))))
			bad_url = b.mixed_problem_markdown([{'issue': 'not-a-url'}])
			self.assertTrue(any(('valid GitHub issue URL' in e for e in statements.validate_df_analysis(bad_url, requests=ctx['requests'], mode='auto', turn_context=turn_ctx))))
			self.assertIsNotNone(MixedTurnProblemSchema([]).extract())
	# @used-by :mod:`unittest`
	def test_cli_description_exclusion_blocker_detection_and_lazy_answer_gate(self) -> None:
		from Df.Harness.Gate.AnswerChecksGate import AnswerChecksGate
		from Df.Harness.Grounding.CliCommandAuditor import CliCommandAuditor
		from Df.Harness.Grounding.Doc5ReplayAuditor import Doc5ReplayAuditor
		from Df.Harness.lib import blocked_report_ops as bro
		with tempfile.TemporaryDirectory() as td:
			b: ProblemReportFixtureBuilder = ProblemReportFixtureBuilder(Path(td)).with_git_repo().add_issue(501)
			ctx = b.build_workspace()
			desc_cmd = b.mixed_problem_markdown([{'issue': 'https://github.com/dmitry-ai/harness/issues/501', 'desc': 'Запуск `python harness.py rename-project --domain example.com` упал с ошибкой «exit status 1».'}])
			self.assertEqual([], CliCommandAuditor(desc_cmd, turn=ctx['turn'], native=None).audit())
			plan_cmd = desc_cmd + '\nВыполните `python harness.py rename-project --domain example.com` сейчас.  \n'
			self.assertTrue(CliCommandAuditor(plan_cmd, turn=ctx['turn'], native=None).audit())
			self.assertTrue(bro._is_doc5_blocker_analysis(desc_cmd))
			self.assertTrue(bro._is_doc5_blocker_analysis(b.standalone_four_track_markdown((None, None, None, None), flat_h1=False)))
			self.assertFalse(bro._is_doc5_blocker_analysis('Plain prose without metadata.'))
			rf_mixed = ctx['root'] / 'mixed.md'
			rf_mixed.write_text(desc_cmd, encoding='utf-8')
			self.assertTrue(Doc5ReplayAuditor._Doc5ReplayAuditor__is_problem_response({'prepared': {'response_file': str(rf_mixed)}}))
			bad_url = b.mixed_problem_markdown([{'issue': 'not-a-url'}])
			lazy_ctx = {'role': 'primary', 'root': ctx['root'], 'turn': ctx['turn'], 'value': ctx['turn_state'], 'response': bad_url, 'doc4_errs': [], 'link_errs': [], 'prob_errs': [], 'source_errs': [], 'lang_errs': [], 'exec5_chk': {'verified': True}, 'http_chk': {'verified': True}, 'comp_chk': {'verified': True}, 'evicted_cited': [], 'del_chk': {'verified': True}, 'issue_first_chk': {'verified': True}, 'lifecycle_chk': {'verified': True}, 'tdd_chk': {'verified': True}, 'wf_errs': []}
			gate_issues, gate_checks = AnswerChecksGate().run(lazy_ctx)
			self.assertFalse(gate_checks['problem_report'])
			self.assertTrue(any(('problem_report' == it['gate_id'] for it in gate_issues)), gate_issues)
if '__main__' == __name__:
	unittest.main()
