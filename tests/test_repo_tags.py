# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement daily-counter Git tag engine and repo-tag CLI commands":
# https://github.com/dmitry-ai/harness/issues/262
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
from agent_tools import cli_registry
from agent_tools.repo_tags import build_github_blob_url, ensure_commit_tag, is_valid_date_tag, is_valid_repo_tag, next_date_tag, retro_tag_repo
def _git(repo: Path, *args: str, env_extra: dict[str, str] | None=None) -> str:
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', **(env_extra or {})}
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', env=env, check=True, timeout=30)
	return proc.stdout.strip()
def _init_repo_with_bare_origin(tmp: Path, slug: str='acme/demo') -> tuple[Path, Path]:
	origin = tmp / 'origin.git'
	repo = tmp / 'repo'
	origin.mkdir(parents=True)
	repo.mkdir(parents=True)
	subprocess.run(['git', 'init', '--bare', str(origin)], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30)
	subprocess.run(['git', 'init', '-b', 'main', str(repo)], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30)
	_git(repo, 'config', 'user.name', 'Test User')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'remote', 'add', 'origin', str(origin))
	_git(repo, 'remote', 'add', 'github', f'https://github.com/{slug}.git')
	return (repo, origin)
def _commit_at(repo: Path, rel: str, text: str, msg: str, iso_dt: str) -> str:
	fp = repo / rel
	fp.parent.mkdir(parents=True, exist_ok=True)
	fp.write_text(text, encoding='utf-8')
	_git(repo, 'add', rel)
	env = {'GIT_AUTHOR_DATE': iso_dt, 'GIT_COMMITTER_DATE': iso_dt}
	_git(repo, 'commit', '--no-verify', '-m', msg, env_extra=env)
	return _git(repo, 'rev-parse', 'HEAD')
class RepoTagsTests(unittest.TestCase):
	def test_cli_repo_tag_and_repo_tag_retro_registered(self) -> None:
		cmds = cli_registry.registered_commands()
		self.assertIn('repo-tag', cmds)
		self.assertIn('repo-tag-retro', cmds)
		with tempfile.TemporaryDirectory() as td:
			repo, _ = _init_repo_with_bare_origin(Path(td))
			_commit_at(repo, 'src/a.py', 'x = 1\ny = 2\n', 'https://github.com/acme/demo/issues/1', '2026-11-26T10:00:00+03:00')
			proc = subprocess.run([sys.executable, str(SCRIPTS / 'harness.py'), 'repo-tag', str(repo), '--file', 'src/a.py', '--lines', 'L1-L2'], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', check=False, timeout=30)
			self.assertEqual(0, proc.returncode, proc.stderr + proc.stdout)
			data = json.loads(proc.stdout)
			self.assertEqual('2026-11-26', data['tag'])
			self.assertEqual('https://github.com/acme/demo/blob/2026-11-26/src/a.py#L1-L2', data['github_url'])
	def test_date_tag_and_repo_tag_validation(self) -> None:
		for good in ('2026-11-26', '2026-11-26--2', '2026-11-26--10', '2024-09-20--3'):
			self.assertTrue(is_valid_date_tag(good), good)
			self.assertTrue(is_valid_repo_tag(good), good)
		for bad in ('2026-11-26--1', '2026-11-26--0', '2026-11-26--02', '2026-02-30', '2026-11-26-2', 'main', 'master', 'HEAD', ''):
			self.assertFalse(is_valid_date_tag(bad), bad)
		self.assertTrue(is_valid_repo_tag('11.6.1'))
		self.assertTrue(is_valid_repo_tag('v2.3.4'))
		self.assertFalse(is_valid_repo_tag('main'))
		self.assertFalse(is_valid_repo_tag('2026-11-26--1'))
	def test_ensure_commit_tag_creates_reuses_and_pushes_lightweight_tag(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo, origin = _init_repo_with_bare_origin(Path(td))
			sha1 = _commit_at(repo, 'a.txt', 'one\n', 'https://github.com/acme/demo/issues/1', '2026-11-26T09:00:00+03:00')
			sha2 = _commit_at(repo, 'a.txt', 'two\n', 'https://github.com/acme/demo/issues/2', '2026-11-26T12:00:00+03:00')
			sha3 = _commit_at(repo, 'a.txt', 'three\n', 'https://github.com/acme/demo/issues/3', '2026-11-27T01:00:00+03:00')
			_git(repo, 'push', '-u', 'origin', 'main')
			res1 = ensure_commit_tag(repo, commit=sha1, push=True)
			self.assertEqual('2026-11-26', res1['tag'])
			self.assertTrue(res1['created'])
			self.assertTrue(res1['pushed'])
			self.assertEqual('commit', _git(repo, 'cat-file', '-t', 'refs/tags/2026-11-26'))
			res1_again = ensure_commit_tag(repo, commit=sha1, push=True)
			self.assertEqual('2026-11-26', res1_again['tag'])
			self.assertFalse(res1_again['created'])
			res2 = ensure_commit_tag(repo, commit=sha2, push=True)
			self.assertEqual('2026-11-26--2', res2['tag'])
			res3 = ensure_commit_tag(repo, commit=sha3, push=True)
			self.assertEqual('2026-11-27', res3['tag'])
			remote_tags = _git(origin, 'tag', '-l').splitlines()
			self.assertEqual(['2026-11-26', '2026-11-26--2', '2026-11-27'], sorted(remote_tags))
	def test_github_blob_url_builder_validates_file_and_lines(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo, _ = _init_repo_with_bare_origin(Path(td), slug='dmitry-ai/sample')
			_commit_at(repo, 'pkg/mod.py', 'a = 1\nb = 2\nc = 3\n', 'https://github.com/dmitry-ai/sample/issues/1', '2026-11-26T11:00:00+03:00')
			url = build_github_blob_url(repo / 'pkg/mod.py', lines='L2-L3', push=False)
			self.assertEqual('https://github.com/dmitry-ai/sample/blob/2026-11-26/pkg/mod.py#L2-L3', url)
			with self.assertRaises(ValueError):
				build_github_blob_url(repo / 'pkg/mod.py', lines='L1-L99', push=False)
	def test_next_date_tag_daily_counter_and_reset(self) -> None:
		self.assertEqual('2026-11-26', next_date_tag([], '2026-11-26'))
		self.assertEqual('2026-11-26--2', next_date_tag(['2026-11-26'], '2026-11-26'))
		self.assertEqual('2026-11-26--3', next_date_tag(['2026-11-26', '2026-11-26--2'], '2026-11-26'))
		self.assertEqual('2026-11-27', next_date_tag(['2026-11-26', '2026-11-26--2'], '2026-11-27'))
	def test_retro_tag_repo_tags_closing_commits_chronologically(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			repo, origin = _init_repo_with_bare_origin(Path(td))
			_commit_at(repo, 'a.py', 'v1\n', 'https://github.com/acme/demo/issues/1', '2026-11-24T10:00:00+03:00')
			sha1_end = _commit_at(repo, 'a.py', 'v2\n', 'https://github.com/acme/demo/issues/1', '2026-11-24T11:00:00+03:00')
			sha2_end = _commit_at(repo, 'a.py', 'v3\n', 'https://github.com/acme/demo/issues/2', '2026-11-24T15:00:00+03:00')
			sha3_end = _commit_at(repo, 'a.py', 'v4\n', 'https://github.com/acme/demo/issues/3', '2026-11-25T09:00:00+03:00')
			_git(repo, 'push', '-u', 'origin', 'main')
			preview = retro_tag_repo(repo, apply=False, push=False)
			self.assertEqual(3, len(preview['planned']))
			self.assertEqual([(sha1_end, '2026-11-24'), (sha2_end, '2026-11-24--2'), (sha3_end, '2026-11-25')], [(p['sha'], p['tag']) for p in preview['planned']])
			self.assertEqual('', _git(repo, 'tag', '-l'))
			applied = retro_tag_repo(repo, apply=True, push=True)
			self.assertEqual(3, applied['created_count'])
			self.assertEqual(['2026-11-24', '2026-11-24--2', '2026-11-25'], sorted(_git(origin, 'tag', '-l').splitlines()))
			rerun = retro_tag_repo(repo, apply=True, push=True)
			self.assertEqual(0, rerun['created_count'])
	def test_ensure_commit_tag_uses_bounded_git_subprocesses(self) -> None:
		from unittest.mock import patch
		with tempfile.TemporaryDirectory() as td:
			repo, _ = _init_repo_with_bare_origin(Path(td))
			_commit_at(repo, 'a.py', 'x = 1\n', 'https://github.com/acme/demo/issues/1', '2026-11-26T10:00:00+03:00')
			calls: list[list[str]] = []
			real_run = subprocess.run
			def spy(cmd, *args, **kwargs):
				calls.append([str(c) for c in cmd])
				return real_run(cmd, *args, **kwargs)
			with patch.object(subprocess, 'run', side_effect=spy):
				res = ensure_commit_tag(repo, push=False)
			self.assertTrue(res['created'])
			self.assertLessEqual(len(calls), 3, calls)
if '__main__' == __name__:
	unittest.main()
