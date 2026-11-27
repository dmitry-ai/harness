# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DfHarnessS11Wave2CIssuesTests(unittest.TestCase):
	# @used-by :meth:`DfHarnessS11Wave2CIssuesTests.test_batch_runner_repo_auditor_and_transfer_runner()`
	@staticmethod
	def __fake_batch_api(endpoint: str, *, method: str='GET', payload=None, paginate: bool=False):
		if 'POST' == method and endpoint.endswith('/issues'):
			r = {'number': 5, 'id': 500, 'html_url': 'https://github.com/acme/demo/issues/5', 'title': payload['title'], 'body': payload['body'], 'state': 'open'}
		elif endpoint.endswith('/issues/5'):
			r = {'number': 5, 'id': 500, 'html_url': 'https://github.com/acme/demo/issues/5', 'title': 'Fix single parser bug', 'body': 'Body details.\n', 'state': 'open'}
		elif endpoint.endswith('/transfer'):
			r = {'full_name': 'neworg/demo'}
		elif 'repos/neworg/demo' == endpoint:
			r = {'full_name': 'neworg/demo', 'html_url': 'https://github.com/neworg/demo', 'private': True, 'default_branch': 'main'}
		elif 'comments' in endpoint:
			r = [{'id': 9, 'issue_url': 'https://github.com/acme/demo/issues/5', 'html_url': 'https://github.com/acme/demo/issues/5#issuecomment-9', 'body': 'Clean comment.'}]
		else:
			r = [{'number': 5, 'title': 'Clean issue title', 'html_url': 'https://github.com/acme/demo/issues/5', 'body': 'Clean body.'}]
		return r
	# @used-by :meth:`DfHarnessS11Wave2CIssuesTests.test_dirty_scanner_read_cache_and_locator()`
	# @used-by :meth:`DfHarnessS11Wave2CIssuesTests.test_parity_and_scope_completeness()`
	@staticmethod
	def __init_repo(repo: Path, slug: str='acme/demo') -> None:
		repo.mkdir(parents=True, exist_ok=True)
		subprocess.run(['git', 'init', '-b', 'main', str(repo)], check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
		cfg = repo / '.git/config'
		cfg.write_text(cfg.read_text(encoding='utf-8') + f'[user]\n\temail = t@example.com\n\tname = Test\n[remote "origin"]\n\turl = https://github.com/{slug}.git\n', encoding='utf-8')
	# @used-by :mod:`unittest`
	def test_batch_runner_repo_auditor_and_transfer_runner(self) -> None:
		from Df.Harness.Issue.BatchRunner import BatchRunner
		from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
		from Df.Harness.Issue.Linter import Linter
		from Df.Harness.Issue.RepoAuditor import RepoAuditor
		from Df.Harness.Issue.RepoTransferRunner import RepoTransferRunner
		from Df.Harness.Issue.Service import Service
		with tempfile.TemporaryDirectory() as td:
			base = Path(td)
			spec = base / 'batch.json'
			spec.write_text(json.dumps({'repo': 'acme/demo', 'items': [{'title': 'Fix single parser bug', 'body': 'Body details.\n', 'labels': ['bug'], 'assignees': 'dev'}]}), encoding='utf-8')
			svc = Service(api_fn=self.__fake_batch_api, linter=Linter(), workspace=EvidenceWorkspace())
			b_args = argparse.Namespace(spec_file=str(spec), repo='acme/demo', parent=None, no_metadata=True, consume_input=False, conversation=None, project_root=str(base), repo_root=None, target_locale='en-US')
			self.assertEqual(0, BatchRunner(svc, b_args, 'create').run())
			a_args = argparse.Namespace(repo='acme/demo', state='all', include_comments=True, strict_structure=False, target_locale='en-US')
			self.assertEqual(0, RepoAuditor(self.__fake_batch_api, Linter(), a_args).audit())
			t_args = argparse.Namespace(repo='acme/demo', new_owner='neworg', new_name=None, project_root=str(base), poll_attempts=1, poll_interval=0.0)
			self.assertEqual(0, RepoTransferRunner(self.__fake_batch_api, Linter(), EvidenceWorkspace(), t_args).transfer())
	# @used-by :mod:`unittest`
	def test_bg_scanner_recorder_and_issue_lib_helpers(self) -> None:
		from Df.Harness.Issue.BgTaskRecorder import BgTaskRecorder
		from Df.Harness.Issue.IssueFirstBgScanner import IssueFirstBgScanner
		from Df.Harness.Issue.IssueFirstPreToolEvaluator import IssueFirstPreToolEvaluator
		from Df.Harness.lib.issue import dfh_build_create_payload, dfh_emit_grounding_failure, dfh_extract_actions_from_decoded_obj, dfh_gh_api_call, dfh_is_df_issue_command_text, dfh_is_excluded_meta_rel, dfh_resolve_title
		ns = argparse.Namespace(label=['a, b'], assignee=['u1'], milestone=3, title='My title', title_file=None)
		payload = dfh_build_create_payload(ns, 'My title', 'Body')
		self.assertEqual({'title': 'My title', 'body': 'Body', 'labels': ['a', 'b'], 'assignees': ['u1'], 'milestone': 3}, payload)
		self.assertEqual('My title', dfh_resolve_title(ns, []))
		self.assertTrue(dfh_is_excluded_meta_rel('.git/HEAD'))
		self.assertFalse(dfh_is_excluded_meta_rel('scripts/a.py'))
		self.assertTrue(dfh_is_df_issue_command_text('python df_github_issue.py create --repo acme/demo'))
		self.assertEqual(1, len(dfh_extract_actions_from_decoded_obj({'ok': True, 'action': 'batch-create', 'results': [{'ok': True, 'action': 'create', 'repo': 'acme/demo', 'number': 7, 'state': 'open'}]})))
		self.assertEqual(2, dfh_emit_grounding_failure('comment', 'acme/demo', ['err'], number=1, comment_id=2))
		fake_proc = subprocess.CompletedProcess(['gh'], 0, stdout=b'[{"id": 1}][{"id": 2}]', stderr=b'')
		self.assertEqual([{'id': 1}, {'id': 2}], dfh_gh_api_call('repos/acme/demo/issues', paginate=True, runner=lambda *a, **kw: fake_proc))
		seg = [
			{'type': 'PLANNER_RESPONSE', 'step_index': 1, 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'python df_github_issue.py create --repo acme/demo'}}]},
			{'type': 'GENERIC', 'content': 'Tool is running as a background task with task id: tid-1'},
			{'type': 'SYSTEM_MESSAGE', 'step_index': 2, 'content': 'Task id "tid-1" finished with result:\n{"ok": true, "action": "create", "repo": "acme/demo", "number": 11, "state": "open"}'},
		]
		evs = IssueFirstBgScanner(seg, None, IssueFirstPreToolEvaluator.build_code_write_event, IssueFirstPreToolEvaluator.build_issue_action_events).extract()
		self.assertEqual(1, len(evs))
		seg_box: dict = {'bg_tdd_index': {'tid-1': {'cmd': 'python df_github_issue.py create --repo acme/demo', 'step': 1, 'outcome': {}}}, 'issue_first_events': [], 'issue_actions': []}
		BgTaskRecorder('Task id "tid-1" finished with result:\n{"ok": true, "action": "create", "repo": "acme/demo", "number": 11, "state": "open"}', 2, seg_box, lambda s: {'exit_code': 0}).record()
		self.assertEqual(1, len(seg_box['issue_first_events']))
		self.assertEqual(1, len(seg_box['issue_actions']))
	# @used-by :mod:`unittest`
	def test_dirty_scanner_read_cache_and_locator(self) -> None:
		from Df.Harness.Issue.DirtyIssueFirstScanner import DirtyIssueFirstScanner
		from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
		from Df.Harness.Issue.ReadCache import ReadCache
		from Df.Harness.Issue.RepoLocator import RepoLocator
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			repo = base / 'code'
			self.__init_repo(repo)
			(repo / 'app.py').write_text('# https://github.com/acme/demo/issues/4\nX = 1\n', encoding='utf-8')
			self.assertEqual('acme/demo', RepoLocator().origin_repo_slug(repo))
			self.assertTrue(RepoLocator().repo_matches_slug(repo, 'acme/demo'))
			self.assertEqual(['app.py'], DirtyIssueFirstScanner(EvidenceWorkspace(), 'acme/demo', project_root=base, repo_root=repo).scan())
			cache = ReadCache()
			self.assertIn('app.py', cache.dirty_paths(repo))
			self.assertTrue(cache.has_dirty_for_paths(repo, ['app.py']))
			self.assertEqual(['app.py'], cache.dirty_referencing_issue(repo, 'https://github.com/acme/demo/issues/4', frozenset({'.py'}), lambda t: ['https://github.com/acme/demo/issues/4'] if 'issues/4' in t else []))
			self.assertEqual(['a.py'], ReadCache.parse_porcelain_z('?? a.py\x00'))
	# @used-by :mod:`unittest`
	def test_issue_first_evaluator_inheritor_and_pretool(self) -> None:
		from Df.Harness.Issue.IssueFirstEvaluator import IssueFirstEvaluator
		from Df.Harness.Issue.IssueFirstInheritor import IssueFirstInheritor
		from Df.Harness.Issue.IssueFirstPreToolEvaluator import IssueFirstPreToolEvaluator
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			ev_dir = base / '\ua616/KB/Evidence/GitHub/acme__demo'
			ev_dir.mkdir(parents=True)
			(ev_dir / 'issue-10.json').write_text(json.dumps({'number': 10, 'state': 'open', 'body': 'Problem'}), encoding='utf-8')
			tdir = base / '\ua616/data/turns'
			tdir.mkdir(parents=True)
			(tdir / 'parent.json').write_text(json.dumps({'status': 'open', 'role': 'primary', 'conversation_id': '11111111-1111-1111-1111-111111111111', 'issue_first_check': {'repos': {'acme/demo': {'active_parents': [10]}}}}), encoding='utf-8')
			res = IssueFirstEvaluator([{'kind': 'code_write', 'step': 1, 'repo_slug': 'acme/demo', 'repo_root': str(base), 'rel_path': 'a.py', 'classification': 'production'}], requests=[{'text': 'Fix #10'}], project_root=base).evaluate()
			self.assertTrue(res['verified'])
			bad = IssueFirstEvaluator([{'kind': 'code_write', 'step': 1, 'repo_slug': 'acme/demo', 'repo_root': str(base), 'rel_path': 'a.py', 'classification': 'test'}, {'kind': 'issue_action', 'step': 2, 'action': 'create', 'repo': 'acme/demo', 'number': 12, 'state': 'open'}, {'kind': 'issue_action', 'step': 3, 'action': 'close', 'repo': 'acme/demo', 'number': 12}], project_root=base).evaluate()
			self.assertFalse(bad['verified'])
			db = base / 'conversation_summaries.db'
			conn = sqlite3.connect(str(db))
			conn.execute('CREATE TABLE conversation_summaries (conversation_id TEXT, parent_conversation_id TEXT)')
			conn.execute("INSERT INTO conversation_summaries VALUES ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111')")
			conn.commit()
			conn.close()
			tx = base / 'brain/22222222-2222-2222-2222-222222222222/transcript.jsonl'
			tx.parent.mkdir(parents=True)
			tx.write_text('{"type": "SYSTEM_MESSAGE", "content": "sender=11111111-1111-1111-1111-111111111111"}\n', encoding='utf-8')
			info = {'repo_slug': 'acme/demo', 'repo_root': str(base), 'rel_path': 'a.py'}
			self.assertTrue(IssueFirstInheritor({'conversationId': '22222222-2222-2222-2222-222222222222'}, info, base, tx).has_inherited_open_parent())
			self.assertIsNotNone(IssueFirstInheritor.missing_transcript_error([(base / 'a.py', info)], {}, base))
			self.assertIsNone(IssueFirstPreToolEvaluator('read_file', {}, {'cwd': str(base)}).evaluate())
	# @used-by :mod:`unittest`
	def test_issue_turn_lib_session_scope_and_pending_peers(self) -> None:
		from Df.Harness.Issue.CompetingTurnChecker import CompetingTurnChecker
		from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
		from Df.Harness.Issue.PendingPeerFinder import PendingPeerFinder
		from Df.Harness.Issue.SessionDetector import SessionDetector
		from Df.Harness.Issue.TurnScopeResolver import TurnScopeResolver
		from Df.Harness.lib.issue_turn import dfh_extract_implemented_m_roots, dfh_filter_turn_state_items, dfh_merge_turn_issue_item
		plat, cid = SessionDetector(env={'CODEX_THREAD_ID': 'tid-abc'}).detect()
		self.assertEqual(('codex', 'tid-abc'), (plat, cid))
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			tdir = base / '\ua616/data/turns'
			tdir.mkdir(parents=True)
			t1 = tdir / 't1.json'
			t1.write_text(json.dumps({'status': 'open', 'platform': 'codex', 'conversation_id': 'tid-abc'}), encoding='utf-8')
			t2 = tdir / 't2.json'
			t2.write_text(json.dumps({'status': 'open', 'platform': 'codex', 'conversation_id': 'tid-other'}), encoding='utf-8')
			self.assertTrue(CompetingTurnChecker(base, 'tid-abc').has_competing())
			sel, rec_cid, rec_plat = TurnScopeResolver([(t1, 'codex', 'tid-abc'), (t2, 'codex', 'tid-other')], 'codex', 'tid-abc').select()
			self.assertEqual(([t1], 'tid-abc', 'codex'), (sel, rec_cid, rec_plat))
			self.assertEqual([], PendingPeerFinder(EvidenceWorkspace(), None, repo='acme/demo').find())
		self.assertEqual(['M-1'], dfh_extract_implemented_m_roots('- M-1: done'))
		out: dict = {}
		dfh_merge_turn_issue_item(out, {'url': 'https://github.com/acme/demo/issues/1', 'action': 'create', 'state': 'open'})
		self.assertIn('https://github.com/acme/demo/issues/1', out)
		self.assertEqual(1, len(dfh_filter_turn_state_items([{'recorded_conversation_id': 'c1', 'url': 'u'}], 'c1', 'codex', set())))
	# @used-by :mod:`unittest`
	def test_parity_and_scope_completeness(self) -> None:
		from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
		from Df.Harness.Issue.Linter import Linter
		from Df.Harness.Issue.ParityAuditor import ParityAuditor
		from Df.Harness.Issue.ScopeCompletenessChecker import ScopeCompletenessChecker
		from Df.Harness.Issue.TurnAuditor import TurnAuditor
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			(base / '.agents').mkdir()
			repo = base / 'code'
			self.__init_repo(repo)
			self.assertEqual(['acme/demo'], ParityAuditor.similar_project_repo_slugs(base))
			auditor = TurnAuditor(base, {}, None, None, workspace=EvidenceWorkspace(), linter=Linter())
			self.assertTrue(callable(auditor._resolve_parent_number))
			self.assertEqual({}, ScopeCompletenessChecker(auditor, 'acme/demo').find_open_deferred_children())
			violations: list[str] = []
			ParityAuditor(base, {repo: {'a.py'}}, {}, None, [repo], violations).audit()
			self.assertEqual([], violations)
	# @used-by :mod:`unittest`
	def test_service_metadata_prepender_and_comment_validators(self) -> None:
		from Df.Harness.Issue.AcceptanceGate import AcceptanceGate
		from Df.Harness.Issue.CloseCommentValidator import CloseCommentValidator
		from Df.Harness.Issue.CommentGrounder import CommentGrounder
		from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
		from Df.Harness.Issue.IssueMetadataPrepender import IssueMetadataPrepender
		from Df.Harness.Issue.Linter import Linter
		from Df.Harness.Issue.Service import Service
		with tempfile.TemporaryDirectory() as td:
			base = Path(td).resolve()
			patched: list[dict] = []
			ws = EvidenceWorkspace()
			state: dict = {'body': 'Plain body', 'prepended': False}
			IssueMetadataPrepender(ws, lambda ep, *, method='GET', payload=None: patched.append(payload)).prepend('acme/demo', 3, {'html_url': 'https://github.com/acme/demo/issues/3'}, 'Plain body', base, [], state)
			self.assertTrue(state['prepended'])
			self.assertEqual(1, len(patched))
			cf = base / 'c.md'
			cf.write_text('Closing comment text.\n', encoding='utf-8', newline='\n')
			svc = Service(api_fn=lambda *a, **kw: {}, linter=Linter(), workspace=ws)
			c_body, err_rc = CloseCommentValidator(svc, argparse.Namespace(comment_file=str(cf), repo_root=None), 'acme/demo', 3, [], 'en-US', None, base).validate()
			self.assertIsNone(err_rc)
			self.assertEqual('Closing comment text.\n', c_body)
			self.assertEqual([], CommentGrounder(ws, 'acme/demo', [], project_root=base).check_grounding('Plain clean sentence.'))
			self.assertIsNone(AcceptanceGate(None, 'acme/demo', 3, project_root=base).check_readiness(ws, argparse.Namespace(repo_root=None), [], verify_fn=lambda *a, **kw: {'verified': True}, is_tracked_fn=lambda _p: False)[1])
if '__main__' == __name__:
	unittest.main()
