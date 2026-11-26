# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pushed Git tags on issue-closing commits in lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/263
from __future__ import annotations
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import git_gate, issue_lifecycle, worktree_flow
def _git(repo: Path, *args: str, env_extra: dict[str, str] | None=None) -> str:
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', **(env_extra or {})}
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', env=env, check=True, timeout=30)
	return proc.stdout.strip()
def _init_tracked_repo(tmp: Path) -> tuple[Path, Path, Path]:
	proj = tmp / 'proj'
	code = proj / 'code'
	bare = tmp / 'origin.git'
	ev_dir = proj / '_/\ua616/KB/Evidence/GitHub/acme__demo'
	ev_dir.mkdir(parents=True)
	code.mkdir(parents=True)
	subprocess.run(['git', 'init', '--bare', '-b', 'main', str(bare)], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30)
	subprocess.run(['git', 'init', '-b', 'main', str(code)], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30)
	cfg = code / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + f'[user]\n\temail = test@example.com\n\tname = Test\n[remote "origin"]\n\turl = https://github.com/acme/demo.git\n\tpushurl = {bare.as_posix()}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n', encoding='utf-8')
	return (proj, code, bare)
def _commit_issue(code: Path, fname: str, num: int, iso_dt: str='2026-11-26T10:00:00+03:00') -> str:
	url = f'https://github.com/acme/demo/issues/{num}'
	(code / fname).write_text(f'# {url}\nVAL = {num}\n', encoding='utf-8')
	_git(code, 'add', fname)
	_git(code, 'commit', '--no-verify', '-m', url, env_extra={'GIT_AUTHOR_DATE': iso_dt, 'GIT_COMMITTER_DATE': iso_dt})
	_git(code, 'push', '-u', 'origin', 'main')
	return _git(code, 'rev-parse', 'HEAD')
class RepoTagCloseGateTests(unittest.TestCase):
	def test_issue_lifecycle_auditor_requires_pushed_tag_on_closing_commit(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			proj, code, _ = _init_tracked_repo(Path(td).resolve())
			ev_dir = proj / '_/\ua616/KB/Evidence/GitHub/acme__demo'
			(ev_dir / 'issue-1.json').write_text(json.dumps({'url': 'https://github.com/acme/demo/issues/1', 'html_url': 'https://github.com/acme/demo/issues/1', 'repo': 'acme/demo', 'kind': 'issue', 'number': 1, 'state': 'closed', 'title': 'Fix one', 'body': 'Body.'}), encoding='utf-8')
			sha = _commit_issue(code, 'a.py', 1)
			turn = {'touched_files': [str(code / 'a.py')], 'issue_actions': [{'url': 'https://github.com/acme/demo/issues/1', 'action': 'close', 'state': 'closed'}]}
			bad = issue_lifecycle.code_and_issue_lifecycle_status(proj, turn)
			self.assertFalse(bad['verified'])
			self.assertTrue(any('repo-tag' in v for v in bad['violations']), bad['violations'])
			_git(code, 'tag', '2026-11-26', sha)
			_git(code, 'push', 'origin', 'refs/tags/2026-11-26')
			good = issue_lifecycle.code_and_issue_lifecycle_status(proj, turn)
			self.assertTrue(good['verified'], good)
	def test_verify_close_rejects_untagged_invalid_and_unpushed_tags_and_accepts_pushed_valid(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			_, code, _ = _init_tracked_repo(Path(td).resolve())
			sha1 = _commit_issue(code, 'a.py', 1)
			with self.assertRaisesRegex(ValueError, 'repo-tag'):
				git_gate.verify_repo_issue_ready_for_close(code, 'acme/demo', 1)
			_git(code, 'tag', '2026-11-26--1', sha1)
			with self.assertRaisesRegex(ValueError, 'repo-tag'):
				git_gate.verify_repo_issue_ready_for_close(code, 'acme/demo', 1)
			_git(code, 'tag', '2026-11-26', sha1)
			with self.assertRaisesRegex(ValueError, 'not pushed'):
				git_gate.verify_repo_issue_ready_for_close(code, 'acme/demo', 1)
			_git(code, 'push', 'origin', 'refs/tags/2026-11-26')
			res1 = git_gate.verify_repo_issue_ready_for_close(code, 'acme/demo', 1)
			self.assertTrue(res1['verified'])
			self.assertEqual('2026-11-26', res1['tag'])
			sha2 = _commit_issue(code, 'b.py', 2)
			_git(code, 'tag', '11.6.1', sha2)
			_git(code, 'push', 'origin', 'refs/tags/11.6.1')
			res2 = git_gate.verify_repo_issue_ready_for_close(code, 'acme/demo', 2)
			self.assertTrue(res2['verified'])
			self.assertEqual('11.6.1', res2['tag'])
	def test_worktree_land_with_tag_tags_and_pushes_landed_commit(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			tmp = Path(td).resolve()
			_, code, bare = _init_tracked_repo(tmp)
			_commit_issue(code, 'base.py', 1)
			beg = worktree_flow.worktree_begin(code, 'tag-land', worktrees_dir=tmp / 'wts')
			wt = Path(beg['worktree'])
			url2 = 'https://github.com/acme/demo/issues/2'
			(wt / 'feat.py').write_text(f'# {url2}\nX = 2\n', encoding='utf-8')
			_git(wt, 'add', 'feat.py')
			_git(wt, 'commit', '--no-verify', '-m', url2, env_extra={'GIT_AUTHOR_DATE': '2026-11-26T12:00:00+03:00', 'GIT_COMMITTER_DATE': '2026-11-26T12:00:00+03:00'})
			landed = worktree_flow.worktree_land(wt, run_tests=False, push=True, tag=True, promote_snapshot=False, leases_dir=tmp / 'leases')
			self.assertTrue(landed['valid'], landed)
			self.assertEqual('2026-11-26', landed['tag'])
			self.assertIn('2026-11-26', _git(bare, 'tag', '-l').splitlines())
	def test_verify_closing_commit_tag_reads_origin_from_config_without_git_config_spawn(self) -> None:
		from unittest.mock import patch
		from agent_tools.repo_tag_gate import verify_closing_commit_tag
		from agent_tools.repo_tags import ensure_commit_tag
		with tempfile.TemporaryDirectory() as td:
			_, code, _ = _init_tracked_repo(Path(td).resolve())
			sha = _commit_issue(code, 'c.py', 3)
			ensure_commit_tag(code, commit=sha, push=True)
			calls: list[list[str]] = []
			real_run = subprocess.run
			def spy(cmd, *args, **kwargs):
				calls.append([str(c) for c in cmd])
				return real_run(cmd, *args, **kwargs)
			with patch.object(subprocess, 'run', side_effect=spy):
				tag = verify_closing_commit_tag(code, sha, 'https://github.com/acme/demo/issues/3')
			self.assertEqual('2026-11-26', tag)
			self.assertFalse(any('config' in c for c in calls), calls)
if '__main__' == __name__:
	unittest.main()
