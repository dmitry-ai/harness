# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.Issue.IssueFirstEvaluator import IssueFirstEvaluator
from Df.Harness.Issue.IssueFirstPreToolEvaluator import IssueFirstPreToolEvaluator
from Df.Harness.Issue.ParityAuditor import ParityAuditor
from Df.Harness.Issue.PendingPeerFinder import PendingPeerFinder
from Df.Harness.Issue.ReadCache import ReadCache
from Df.Harness.Issue.RepoLocator import RepoLocator
from Df.Harness.Issue.TurnAuditor import TurnAuditor
from Df.Harness.Issue.TurnScopeResolver import TurnScopeResolver
from Df.Harness.lib.issue import dfh_is_df_issue_command_text
from Df.Harness.lib.shell import ISSUE_LINKED_CODE_SUFFIXES, dfh_extract_issue_urls
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DfHarnessS11Wave2CCovIssuesBTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_issue_first_pretool_evaluator_bg_scanner_and_var_match(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/KB/Evidence/GitHub/o__r').mkdir(parents=True)
			(root / 'ꘖ/KB/Evidence/GitHub/o__r/issue-5.json').write_text(json.dumps({'issue': {'number': 5, 'state': 'open', 'body': 'parent'}}), encoding='utf-8')
			(root / '.git').mkdir()
			(root / '.git/config').write_text('[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding='utf-8')
			ev_res = IssueFirstEvaluator([{'kind': 'issue_action', 'step': 1, 'action': 'fetch', 'repo': 'o/r', 'number': 10, 'parent_number': 5, 'state': 'open'}], project_root=root).evaluate()
			self.assertTrue(ev_res['verified'])
			tr = root / 'transcript.jsonl'
			rows = [
				{'type': 'USER_INPUT', 'content': 'Fix a.py'},
				{'type': 'MODEL_TURN', 'step_index': 1, 'tool_calls': [{'name': 'write_file', 'arguments': {'Path': str(root / 'a.py'), 'Content': 'x = 1\n'}}]},
			]
			tr.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			with patch('Df.Harness.Git.RepoGate.RepoGate.is_issue_tracked', return_value=True):
				err = IssueFirstPreToolEvaluator('write_file', {'Path': str(root / 'b.py'), 'Content': 'y = 2\n'}, {'cwd': str(root), 'transcriptPath': str(tr)}).evaluate()
			self.assertIsNotNone(err)
			self.assertTrue(dfh_is_df_issue_command_text('$tool = "df_github_issue.py"; python $tool create --repo o/r'))
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_parity_auditor_pending_peers_read_cache_and_repo_locator(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			peer = root / 'peer'
			turns = root / 'ꘖ/data/turns'
			turns.mkdir(parents=True)
			peer.mkdir()
			(turns / 'tk-similar-exemptions.json').write_text(json.dumps({'exemptions': [{'peer_root': str(peer), 'reason': 'Technical exemption justification strictly over thirty chars'}]}), encoding='utf-8')
			(turns / 'turn-1.json').write_text(json.dumps({'status': 'open', 'github_issues': {'u': {'repo': 'o/p', 'actions': ['create']}}}), encoding='utf-8')
			touches = [{'group_id': 'g1', 'source_label': 'src', 'source_projects': [str(root)], 'peer_root': str(peer), 'peer_touched': False}]
			with patch('agent_tools.path_registry.evaluate_similar_project_touches', return_value=touches), patch.object(ParityAuditor, 'similar_project_repo_slugs', return_value=['o/p']), patch.object(ParityAuditor, 'peer_code_repo_candidates', return_value=[]):
				par = ParityAuditor(root, {root: {'a.py'}}, {'https://github.com/o/p/issues/1': {'repo': 'o/p', 'number': 1, 'actions': ['create']}}, {'key': 'tk'}, [], []).audit()
			self.assertTrue(par['verified'])
			pp_stub = SimpleNamespace(root=root, similar_projects=[peer], turns_dir=turns, agent_dir=root / 'ꘖ', evidence_dir=root / 'ꘖ/KB/Evidence', has_overlay=False, fs_version=2, code_repos=[], auxiliary_repos={}, _direct_similar_projects=[])
			with patch('agent_tools.path_registry.project_paths', return_value=pp_stub), patch.object(ParityAuditor, 'similar_project_repo_slugs', return_value=['o/p']):
				self.assertEqual([], PendingPeerFinder(EvidenceWorkspace(), root, repo='o/r', project_root=root).find())
			repo = root / 'myrepo'
			(repo / '.git').mkdir(parents=True)
			(repo / '.git/config').write_text('[remote "origin"]\n\turl = https://github.com/o/found.git\n', encoding='utf-8')
			(repo / 'a.py').write_text('# https://github.com/o/found/issues/10\n', encoding='utf-8')
			rc = ReadCache()
			# @used-by :meth:`DfHarnessS11Wave2CCovIssuesBTests.test_parity_auditor_pending_peers_read_cache_and_repo_locator()`
			def fake_git(argv, **_kw):
				if 'status' in argv:
					out = b' M a.py\x00'
				elif 'diff' in argv:
					out = b'--- a.py\n+++ a.py\n+# https://github.com/o/found/issues/10\n'
				elif 'log' in argv:
					out = b'\x1eabcdef\x1fhttps://github.com/o/found/issues/10\x1fa.py\n'
				elif 'rev-parse' in argv:
					out = b'origin/main\n'
				else:
					out = b'0\n'
				return SimpleNamespace(returncode=0, stdout=out, stderr=b'')
			with patch('Df.Harness.Issue.ReadCache.subprocess.run', side_effect=fake_git):
				self.assertIn('a.py', rc.dirty_referencing_issue(repo, 'https://github.com/o/found/issues/10', ISSUE_LINKED_CODE_SUFFIXES, dfh_extract_issue_urls))
				self.assertEqual(['https://github.com/o/found/issues/10'], rc.latest_commit_urls_for_files(repo, ['a.py'], dfh_extract_issue_urls))
				self.assertTrue(rc.verify_commit_pushed(repo, 'abcdef123456', 'https://github.com/o/found/issues/10'))
			RepoLocator.clear_cache()
			reg = SimpleNamespace(source_path=root / 'paths.json')
			pp_d = SimpleNamespace(code_repos=[repo], auxiliary_repos={}, _direct_similar_projects=[repo])
			with patch('agent_tools.path_registry.load_registry', return_value=reg), patch('agent_tools.path_registry.store_value', return_value=[str(root)]), patch('agent_tools.path_registry._candidate_discovery_roots', return_value=([], [root])), patch('agent_tools.path_registry.project_paths', return_value=pp_d):
				self.assertEqual(repo.resolve(), RepoLocator.search_registry_and_roots('o/found', set()))
				self.assertEqual(repo.resolve(), RepoLocator().find_local_code_repo('o/found', project_root=root))
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_turn_auditor_scope_completeness_and_turn_scope_resolver(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			ev = root / 'ꘖ/KB/Evidence/GitHub/o__r'
			ev.mkdir(parents=True)
			(root / '.git').mkdir()
			(root / '.git/config').write_text('[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding='utf-8')
			(root / 'app.py').write_text('# https://github.com/o/r/issues/10\nx = 1\n', encoding='utf-8')
			(ev / 'issue-5.json').write_text(json.dumps({'issue': {'number': 5, 'state': 'open', 'title': 'Parent', 'body': 'Parent body'}}), encoding='utf-8')
			(ev / 'issue-10.json').write_text(json.dumps({'issue': {'number': 10, 'state': 'closed', 'parent_number': 5, 'title': 'Child 10', 'body': 'Parent: #5'}}), encoding='utf-8')
			(ev / 'issue-11.json').write_text(json.dumps({'issue': {'number': 11, 'state': 'open', 'parent_number': 5, 'title': 'Child 11', 'body': 'Parent: #5'}}), encoding='utf-8')
			(ev / 'comment-101.json').write_text(json.dumps({'id': 101, 'body': 'Verified update.'}), encoding='utf-8')
			turn = {'touched_files': ['app.py'], 'issue_actions': [
				{'url': 'https://github.com/o/r/issues/10', 'repo': 'o/r', 'number': 10, 'state': 'closed', 'parent_number': 5, 'action': 'create', 'comment_ids': [101]},
				{'url': 'https://github.com/o/r/issues/11', 'repo': 'o/r', 'number': 11, 'state': 'open', 'parent_number': 5, 'action': 'create'},
			]}
			resp = 'Implemented M-1 and M-2 cleanly.'
			with patch('Df.Harness.Git.RepoGate.RepoGate.is_issue_tracked', lambda s: (s.root / '.git').exists()), patch('Df.Harness.Git.RepoGate.RepoGate.verify_issue_ready_for_close', return_value={'verified': True}), patch.object(ReadCache, 'has_dirty_for_paths', return_value=False), patch.object(ReadCache, 'latest_commit_urls_for_files', return_value=['https://github.com/o/r/issues/10', 'https://github.com/o/r/issues/11']), patch('agent_tools.python_integrity.verify_touched_python_files', return_value=[]), patch('agent_tools.tdd.diff_executability.check_touched_mixed_commit_warning', return_value=None):
				out = TurnAuditor(root, turn, {'conversation_id': 'c1'}, resp).audit()
				self.assertTrue(bool(out['violations']))
				aud2 = TurnAuditor(root, {'touched_files': []}, {'conversation_id': 'c1'}, 'Found H-1 and M-1 in app.py.')
				self.assertFalse(aud2.audit()['verified'])
				aud3 = TurnAuditor(root, {'touched_files': ['app.py'], 'issue_actions': [{'url': 'https://github.com/o/r/issues/12', 'repo': 'o/r', 'number': 12, 'state': 'closed', 'action': 'create'}]}, None, 'Single fix.')
				aud3.repo_touched[root.resolve()] = {'app.py'}
				aud3.turn_issues['https://github.com/o/r/issues/12'] = {'repo': 'o/r', 'number': 12, 'actions': ['create']}
				aud3.check_multi_subtask_decomposition({root.resolve(): {'https://github.com/o/r/issues/12', 'https://github.com/o/r/issues/13'}}, {root.resolve(): set()})
				self.assertTrue(any(('lacks a --parent link' in v for v in aud3.violations)))
			with patch('agent_tools.meta.builders._collect_ag_issue_ctx', return_value={'primary_cid': 'parent-cid'}):
				targs, _, _ = TurnScopeResolver([(root / 't1.json', 'antigravity', '')], 'antigravity', 'child-cid').select()
			self.assertEqual([root / 't1.json'], targs)
if '__main__' == __name__:
	unittest.main()
