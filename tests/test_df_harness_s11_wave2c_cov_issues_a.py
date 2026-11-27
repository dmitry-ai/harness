# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import argparse
import io
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
from Df.Harness.Issue.AcceptanceGate import AcceptanceGate
from Df.Harness.Issue.BatchRunner import BatchRunner
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.Issue.Service import Service
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :meth:`DfHarnessS11Wave2CCovIssuesATests.test_service_all_commands_and_evidence_workspace()`
def _make_issue_api():
	issues: dict[int, dict] = {
		5: {'id': 500, 'number': 5, 'state': 'open', 'title': 'Parent problem issue', 'body': 'Parent problem description.', 'html_url': 'https://github.com/o/r/issues/5'},
		10: {'id': 1000, 'number': 10, 'state': 'open', 'title': 'Child issue title', 'body': 'Parent: #5\nChild body text.', 'html_url': 'https://github.com/o/r/issues/10'},
	}
	comments: dict[int, dict] = {}
	state = {'next_cid': 101}
	# @used-by :func:`_make_issue_api()`
	def _call(endpoint: str, *, method: str='GET', payload=None, paginate: bool=False):
		if endpoint.endswith('/sub_issues'):
			r: object = {'ok': True}
		elif endpoint.endswith('/transfer') or 'repos/o/r2' == endpoint:
			r = {'full_name': 'o/r2', 'html_url': 'https://github.com/o/r2'}
		elif ('/issues?' in endpoint or endpoint.endswith('/issues')) and 'GET' == method:
			r = []
		elif endpoint.endswith('/issues') and 'POST' == method:
			issues[11] = {'id': 1100, 'number': 11, 'state': 'open', 'title': payload['title'], 'body': payload['body'], 'html_url': 'https://github.com/o/r/issues/11'}
			r = issues[11]
		elif '/issues/comments/' in endpoint:
			cid = int(endpoint.rsplit('/', 1)[1])
			if 'PATCH' == method:
				comments[cid]['body'] = payload['body']
			r = comments[cid]
		elif endpoint.endswith('/comments') and 'POST' == method:
			num, cid = (int(endpoint.split('/issues/')[1].split('/')[0]), state['next_cid'])
			state['next_cid'] += 1
			comments[cid] = {'id': cid, 'body': payload['body'], 'html_url': f'https://github.com/o/r/issues/{num}#issuecomment-{cid}', 'issue_url': f'https://api.github.com/repos/o/r/issues/{num}'}
			r = comments[cid]
		else:
			num = int(endpoint.rsplit('/', 1)[1])
			if 'PATCH' == method:
				issues[num].update(payload or {})
			r = issues[num]
		return r
	return _call
class DfHarnessS11Wave2CCovIssuesATests(unittest.TestCase):
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_acceptance_gate_and_batch_runner_close_and_subparsers(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			(root / 'ꘖ/data/shadow-replay-receipt.json').write_text(json.dumps({'valid': False, 'exit_code': 1, 'repo_head': 'bbb'}), encoding='utf-8')
			# @used-by :meth:`DfHarnessS11Wave2CCovIssuesATests.test_acceptance_gate_and_batch_runner_close_and_subparsers()`
			def fake_git(argv, **_kw):
				if 'diff-tree' in argv:
					out = 'scripts/agent_tools/cli_registry.py\n'
				elif 'show' in argv:
					out = '+ register_command("x")\n'
				else:
					out = ''
				return SimpleNamespace(returncode=0, stdout=out, stderr='')
			ws = EvidenceWorkspace()
			with patch('Df.Harness.Issue.AcceptanceGate.subprocess.run', side_effect=fake_git), patch('agent_tools.addon_observability.check_close_companion_health', return_value=None):
				_, err, stage = AcceptanceGate(root, 'o/r', 1, project_root=root).check_readiness(ws, argparse.Namespace(repo_root=None), [], verify_fn=lambda *_a, **_k: {'commit_sha': 'aaa'}, is_tracked_fn=lambda _p: True)
			self.assertEqual('pre_flight_acceptance_check', stage)
			self.assertIn('shadow-replay receipt failed', err)
			spec = root / 'close-batch.json'
			spec.write_text(json.dumps({'repo': 'o/r', 'items': [{'issue': 7, 'comment': 'Closed cleanly.'}]}), encoding='utf-8')
			fake_svc = SimpleNamespace(linter=Service().linter, cmd_close=lambda _a: (print('{"ok": true, "action": "close"}') or 0))
			with patch('sys.stdout', io.StringIO()):
				rc = BatchRunner(fake_svc, argparse.Namespace(spec_file=str(spec), repo='o/r', reason='completed', consume_input=False), 'close').run()
			self.assertEqual(0, rc)
			parser = argparse.ArgumentParser()
			sub = parser.add_subparsers(dest='cmd')
			BatchRunner.register_subparsers(sub, (), (), lambda _a: fake_svc)
			ns = parser.parse_args(['batch-close', '--spec-file', str(spec)])
			self.assertTrue(callable(ns.func))
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_service_all_commands_and_evidence_workspace(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			turns = root / 'ꘖ/data/turns'
			turns.mkdir(parents=True)
			(turns / 'turn-1.json').write_text(json.dumps({'status': 'open', 'platform': 'codex', 'conversation_id': 'c1'}), encoding='utf-8')
			(root / '.git').mkdir()
			(root / '.git/config').write_text('[remote "origin"]\n\turl = https://github.com/o/r.git\n', encoding='utf-8')
			api = _make_issue_api()
			ws = EvidenceWorkspace()
			svc = Service(api_fn=api, workspace=ws, conversation_id='c1')
			body_f = root / 'body.md'
			body_f.write_text('Parent: #5\nChild body text.\n', encoding='utf-8')
			cmt_f = root / 'cmt.md'
			cmt_f.write_text('Verified close comment.\n', encoding='utf-8')
			with patch('sys.stdout', io.StringIO()):
				self.assertEqual(0, svc.cmd_lint(argparse.Namespace(repo='o/r', parent='#5', title='Valid issue title', title_file=None, body_file=str(body_f), target_locale='en-US')))
				self.assertEqual(0, svc.cmd_fetch(argparse.Namespace(repo='o/r', issue=10, project_root=str(root), conversation='c1')))
				self.assertEqual(0, svc.cmd_create(argparse.Namespace(repo='o/r', parent='5', title='Created child', title_file=None, body_file=str(body_f), label=None, assignee=None, milestone=None, no_metadata=True, consume_input=False, project_root=str(root), target_locale='en-US', repo_root=None)))
				self.assertEqual(0, svc.cmd_comment(argparse.Namespace(repo='o/r', issue=10, comment_id=None, body_file=str(cmt_f), consume_input=False, project_root=str(root), target_locale='en-US', repo_root=None, allow_additional_comment=False)))
				self.assertEqual(2, svc.cmd_comment(argparse.Namespace(repo='o/r', issue=10, comment_id=None, body_file=str(cmt_f), consume_input=False, project_root=str(root), target_locale='en-US', repo_root=None, allow_additional_comment=False)))
				self.assertEqual(0, svc.cmd_edit(argparse.Namespace(repo='o/r', issue=10, parent='5', title=None, title_file=None, body_file=None, state=None, consume_input=False, project_root=str(root), target_locale='en-US')))
				self.assertEqual(0, svc.cmd_edit(argparse.Namespace(repo='o/r', issue=10, parent='5', title='Updated child title', title_file=None, body_file=None, state=None, consume_input=False, project_root=str(root), target_locale='en-US')))
				with patch('Df.Harness.Git.RepoGate.RepoGate.is_issue_tracked', return_value=False), patch('agent_tools.addon_observability.check_close_companion_health', return_value=None):
					self.assertEqual(0, svc.cmd_close(argparse.Namespace(repo='o/r', issue=10, reason='completed', comment_file=str(cmt_f), consume_input=False, project_root=str(root), target_locale='en-US', repo_root=None, conversation='c1')))
				self.assertEqual(0, svc.cmd_audit_repo(argparse.Namespace(repo='o/r', state='open', target_locale='en-US', include_comments=False)))
				self.assertEqual(0, svc.cmd_transfer_repo(argparse.Namespace(repo='o/r', new_owner='o', new_name='r2', project_root=str(root), repo_root=None)))
			self.assertEqual('closed', ws.evidence_issue_state(root, 'o/r', 10))
			self.assertTrue(bool(ws.find_tracked_child_issues('o/r', 5, project_root=root)))
			self.assertTrue(bool(ws.find_existing_issue_comments([], 'o/r', 10, project_root=root)))
			self.assertIsNotNone(ws.load_saved_issue_container_text([], 'o/r', 10, project_root=root))
			self.assertIsNotNone(ws.meta_dir_for_project_root(root))
			self.assertTrue(ws.repo_matches_slug(root, 'o/r'))
if '__main__' == __name__:
	unittest.main()
