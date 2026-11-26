# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Require passing shadow-replay acceptance receipt in df_github_issue close gate":
# https://github.com/dmitry-ai/harness/issues/291
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import io
import json
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
# @used-by :meth:`IssueCloseAcceptanceTests.test_close_requires_passing_shadow_replay_for_new_cli_command()`, :meth:`IssueCloseAcceptanceTests.test_close_requires_fresh_passing_receipt_for_upwork_init_and_allows_ordinary_issue()`
def _commit_and_tag(code: Path, rel_path: str, content: str, num: int) -> str:
	from agent_tools.repo_tags import ensure_commit_tag
	from test_repo_tag_close_gate import _git
	url = f'https://github.com/acme/demo/issues/{num}'
	target = code / rel_path
	target.parent.mkdir(parents=True, exist_ok=True)
	target.write_text(f'# {url}\n{content}', encoding='utf-8')
	_git(code, 'add', rel_path)
	_git(code, 'commit', '--no-verify', '-m', url)
	_git(code, 'push', '-u', 'origin', 'main')
	sha = _git(code, 'rev-parse', 'HEAD')
	ensure_commit_tag(code, commit=sha, push=True)
	return sha
# @used-by :meth:`IssueCloseAcceptanceTests.test_close_requires_passing_shadow_replay_for_new_cli_command()`, :meth:`IssueCloseAcceptanceTests.test_close_requires_fresh_passing_receipt_for_upwork_init_and_allows_ordinary_issue()`
def _run_close_cli(proj: Path, code: Path, num: int) -> tuple[int, dict]:
	from agent_tools.github_issue import main
	stored = {'number': num, 'state': 'open', 'state_reason': None, 'title': f'Issue {num}', 'body': 'Body.', 'html_url': f'https://github.com/acme/demo/issues/{num}'}
	def fake_api(path: str, method: str='GET', payload=None):
		if 'PATCH' == method and isinstance(payload, dict):
			stored.update(payload)
		return dict(stored)
	buf = io.StringIO()
	with patch('agent_tools.github_issue._gh_api', side_effect=fake_api), patch('sys.stdout', buf):
		rc = main(['close', '--repo', 'acme/demo', '--issue', str(num), '--project-root', str(proj), '--repo-root', str(code)])
	return (rc, json.loads(buf.getvalue()))
# @used-by :mod:`unittest`
class IssueCloseAcceptanceTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_close_requires_passing_shadow_replay_for_new_cli_command(self) -> None:
		from test_repo_tag_close_gate import _init_tracked_repo
		with tempfile.TemporaryDirectory() as td:
			proj, code, _ = _init_tracked_repo(Path(td).resolve())
			(proj / '\ua616/data').mkdir(parents=True, exist_ok=True)
			sha = _commit_and_tag(code, 'scripts/agent_tools/cli_registry.py', "register_command('my-new-cmd', 'Demo', (), lambda _a: {})\n", 10)
			rc_missing, out_missing = _run_close_cli(proj, code, 10)
			self.assertEqual(2, rc_missing, out_missing)
			self.assertEqual('pre_flight_acceptance_check', out_missing.get('stage'))
			receipt_f = proj / '\ua616/data/shadow-replay-receipt.json'
			receipt_f.write_text(json.dumps({'schema_version': 1, 'repo_head': sha, 'valid': False, 'exit_code': 2}), encoding='utf-8')
			rc_failed, out_failed = _run_close_cli(proj, code, 10)
			self.assertEqual(2, rc_failed, out_failed)
			self.assertEqual('pre_flight_acceptance_check', out_failed.get('stage'))
			receipt_f.write_text(json.dumps({'schema_version': 1, 'repo_head': sha, 'valid': True, 'exit_code': 0}), encoding='utf-8')
			rc_ok, out_ok = _run_close_cli(proj, code, 10)
			self.assertEqual(0, rc_ok, out_ok)
			self.assertTrue(out_ok['ok'])
	# @used-by :mod:`unittest`
	def test_close_requires_fresh_passing_receipt_for_upwork_init_and_allows_ordinary_issue(self) -> None:
		from test_repo_tag_close_gate import _init_tracked_repo
		with tempfile.TemporaryDirectory() as td:
			proj, code, _ = _init_tracked_repo(Path(td).resolve())
			(proj / '\ua616/data').mkdir(parents=True, exist_ok=True)
			old_sha = _commit_and_tag(code, 'scripts/agent_tools/ordinary.py', 'VAL = 1\n', 11)
			rc_ord, out_ord = _run_close_cli(proj, code, 11)
			self.assertEqual(0, rc_ord, out_ord)
			receipt_f = proj / '\ua616/data/shadow-replay-receipt.json'
			receipt_f.write_text(json.dumps({'schema_version': 1, 'repo_head': old_sha, 'valid': True, 'exit_code': 0}), encoding='utf-8')
			new_sha = _commit_and_tag(code, 'scripts/agent_tools/project_rename.py', 'VAL = 2\n', 12)
			rc_stale, out_stale = _run_close_cli(proj, code, 12)
			self.assertEqual(2, rc_stale, out_stale)
			self.assertEqual('pre_flight_acceptance_check', out_stale.get('stage'))
			receipt_f.write_text(json.dumps({'schema_version': 1, 'repo_head': new_sha, 'valid': True, 'exit_code': 0}), encoding='utf-8')
			rc_fresh, out_fresh = _run_close_cli(proj, code, 12)
			self.assertEqual(0, rc_fresh, out_fresh)
if '__main__' == __name__:
	unittest.main()