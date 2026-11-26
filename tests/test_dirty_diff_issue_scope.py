# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pushed Git tags on issue-closing commits in lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/263
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import subprocess
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import git_gate
from agent_tools.issues.git_read_cache import RepoReadCache
from agent_tools.repo_tags import ensure_commit_tag
URL_174 = 'https://github.com/acme/demo/issues/174'
URL_177 = 'https://github.com/acme/demo/issues/177'
URL_180 = 'https://github.com/acme/demo/issues/180'
SUFFIXES = frozenset({'.py'})
def _git_subcommand(cmd) -> str | None:
	r = None
	if isinstance(cmd, (list, tuple)) and cmd and 'git' == Path(str(cmd[0])).stem.lower():
		idx = 1
		while idx < len(cmd):
			tok = str(cmd[idx])
			if tok in ('-C', '-c', '--git-dir', '--work-tree'):
				idx += 2
			elif tok.startswith('-'):
				idx += 1
			else:
				r = tok
				break
	return r
def _init_repo(base: Path) -> Path:
	code = base / 'code'
	bare = base / 'remote.git'
	code.mkdir(parents=True)
	subprocess.run(['git', 'init', '--bare', '-b', 'main', str(bare)], check=True, capture_output=True)
	subprocess.run(['git', 'init', '-b', 'main', str(code)], check=True, capture_output=True)
	cfg = code / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + f'[user]\n\temail = test@example.com\n\tname = Test\n[remote "origin"]\n\turl = https://github.com/acme/demo.git\n\tpushurl = {bare.as_posix()}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n', encoding='utf-8')
	(code / 'storage.py').write_text(f'# {URL_174}\nVAL = 1\n', encoding='utf-8')
	subprocess.run(['git', '-C', str(code), 'add', 'storage.py'], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(code), 'commit', '-m', URL_174], check=True, capture_output=True)
	subprocess.run(['git', '-C', str(code), 'push', '-u', 'origin', 'main'], check=True, capture_output=True)
	ensure_commit_tag(code, push=True)
	return code
# 2026-11-24
# "Scope dirty_referencing_issue to uncommitted diff lines instead of full file text":
# https://github.com/dmitry-ai/harness/issues/196
class DirtyDiffIssueScopeTests(unittest.TestCase):
	def test_diff_cache_runs_once_for_dirty_repo_and_zero_times_for_clean_repo(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			code = _init_repo(Path(tmp).resolve())
			counts: Counter = Counter()
			real_run = subprocess.run
			def spy_run(cmd, *args, **kwargs):
				sub = _git_subcommand(cmd)
				if None is not sub:
					counts[sub] += 1
				return real_run(cmd, *args, **kwargs)
			clean_cache = RepoReadCache()
			with patch.object(subprocess, 'run', side_effect=spy_run):
				self.assertEqual([], clean_cache.dirty_referencing_issue(code, URL_174, SUFFIXES, git_gate.extract_issue_urls))
			self.assertEqual(0, counts['diff'])
			(code / 'storage.py').write_text(f'# {URL_177}\n# {URL_174}\nVAL = 2\n', encoding='utf-8')
			dirty_cache = RepoReadCache()
			with patch.object(subprocess, 'run', side_effect=spy_run):
				self.assertEqual([], dirty_cache.dirty_referencing_issue(code, URL_174, SUFFIXES, git_gate.extract_issue_urls))
				self.assertEqual(['storage.py'], dirty_cache.dirty_referencing_issue(code, URL_177, SUFFIXES, git_gate.extract_issue_urls))
				self.assertEqual([], dirty_cache.dirty_referencing_issue(code, URL_180, SUFFIXES, git_gate.extract_issue_urls))
			self.assertEqual(1, counts['diff'])
	def test_historical_header_ignored_while_added_removed_and_untracked_refs_caught(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			code = _init_repo(Path(tmp).resolve())
			(code / 'storage.py').write_text(f'# {URL_177}\n# {URL_174}\nVAL = 2\n', encoding='utf-8')
			cache = RepoReadCache()
			self.assertEqual([], cache.dirty_referencing_issue(code, URL_174, SUFFIXES, git_gate.extract_issue_urls))
			self.assertEqual(['storage.py'], cache.dirty_referencing_issue(code, URL_177, SUFFIXES, git_gate.extract_issue_urls))
			subprocess.run(['git', '-C', str(code), 'add', 'storage.py'], check=True, capture_output=True)
			staged_cache = RepoReadCache()
			self.assertEqual([], staged_cache.dirty_referencing_issue(code, URL_174, SUFFIXES, git_gate.extract_issue_urls))
			self.assertEqual(['storage.py'], staged_cache.dirty_referencing_issue(code, URL_177, SUFFIXES, git_gate.extract_issue_urls))
			(code / 'storage.py').write_text(f'# {URL_177}\nVAL = 3\n', encoding='utf-8')
			removed_cache = RepoReadCache()
			self.assertEqual(['storage.py'], removed_cache.dirty_referencing_issue(code, URL_174, SUFFIXES, git_gate.extract_issue_urls))
			(code / 'new_mod.py').write_text(f'# {URL_180}\nX = 1\n', encoding='utf-8')
			(code / 'pkg').mkdir()
			(code / 'pkg/helper.py').write_text(f'# {URL_180}\nY = 2\n', encoding='utf-8')
			untracked_cache = RepoReadCache()
			self.assertEqual(['new_mod.py', 'pkg/helper.py'], sorted(untracked_cache.dirty_referencing_issue(code, URL_180, SUFFIXES, git_gate.extract_issue_urls)))
	def test_verify_issue_ready_for_close_allows_committed_header_issue_during_sibling_edit(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			code = _init_repo(Path(tmp).resolve())
			(code / 'storage.py').write_text(f'# {URL_177}\n# {URL_174}\nVAL = 2\n', encoding='utf-8')
			res_174 = git_gate.verify_repo_issue_ready_for_close(code, 'acme/demo', 174)
			self.assertTrue(res_174['verified'])
			with self.assertRaisesRegex(ValueError, 'still reference https://github\\.com/acme/demo/issues/177: storage\\.py'):
				git_gate.verify_repo_issue_ready_for_close(code, 'acme/demo', 177)
if '__main__' == __name__:
	unittest.main()