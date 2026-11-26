# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pushed Git tags on issue-closing commits in lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/263
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import json
import subprocess
import sys
import tempfile
import unittest
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import git_gate, issue_lifecycle
from agent_tools.repo_tags import ensure_commit_tag
# @used-by :meth:`GitLifecycleMemoizationTests.test_audit_memoizes_readonly_git_commands_across_multiple_issues()`
# @used-by :meth:`GitLifecycleMemoizationTests.test_verify_issue_ready_for_close_memoizes_parent_child_and_catches_defects()`
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
# @used-by :meth:`GitLifecycleMemoizationTests.test_audit_memoizes_readonly_git_commands_across_multiple_issues()`
# @used-by :meth:`GitLifecycleMemoizationTests.test_verify_issue_ready_for_close_memoizes_parent_child_and_catches_defects()`
def _init_multi_issue_repo(base: Path) -> tuple[Path, Path]:
	proj = base / 'proj'
	code = proj / 'code'
	bare = base / 'remote.git'
	ev_dir = proj / '_/\ua616/KB/Evidence/GitHub/acme__demo'
	ev_dir.mkdir(parents=True)
	code.mkdir(parents=True)
	subprocess.run(['git', 'init', '--bare', '-b', 'main', str(bare)], check=True, capture_output=True)
	subprocess.run(['git', 'init', '-b', 'main', str(code)], check=True, capture_output=True)
	cfg = code / '.git/config'
	cfg.write_text(cfg.read_text(encoding='utf-8') + f'[user]\n\temail = test@example.com\n\tname = Test\n[remote "origin"]\n\turl = https://github.com/acme/demo.git\n\tpushurl = {bare.as_posix()}\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n', encoding='utf-8')
	_write_ev(ev_dir, 10, state='closed')
	for num, fname in ((11, 'a.py'), (12, 'b.py'), (13, 'c.py')):
		(code / fname).write_text(f'# https://github.com/acme/demo/issues/{num}\nVAL = {num}\n', encoding='utf-8')
		subprocess.run(['git', '-C', str(code), 'add', fname], check=True, capture_output=True)
		subprocess.run(['git', '-C', str(code), 'commit', '-m', f'https://github.com/acme/demo/issues/{num}'], check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
		ensure_commit_tag(code, push=False)
		_write_ev(ev_dir, num, state='closed', parent=10)
	subprocess.run(['git', '-C', str(code), 'push', '-u', 'origin', 'main', '--tags'], check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=30)
	return (proj, code)
# @used-by :func:`_init_multi_issue_repo()`
def _write_ev(ev_dir: Path, num: int, *, state: str='closed', parent: int | None=None) -> None:
	body = f'Parent: [Issue #{parent}](https://github.com/acme/demo/issues/{parent})\n' if None is not parent else 'Problem statement.\n'
	payload = {'url': f'https://github.com/acme/demo/issues/{num}', 'html_url': f'https://github.com/acme/demo/issues/{num}', 'repo': 'acme/demo', 'kind': 'issue', 'number': num, 'state': state, 'title': f'Issue {num}', 'body': body}
	if None is not parent:
		payload['parent_number'] = parent
	(ev_dir / f'issue-{num}.json').write_text(json.dumps(payload), encoding='utf-8')
# 2026-11-24
# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/175
class GitLifecycleMemoizationTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_audit_memoizes_readonly_git_commands_across_multiple_issues(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj, code = _init_multi_issue_repo(Path(tmp).resolve())
			turn = {'touched_files': [str(code / 'a.py'), str(code / 'b.py'), str(code / 'c.py')], 'issue_actions': [{'url': f'https://github.com/acme/demo/issues/{n}', 'action': 'close', 'state': 'closed', 'parent_number': 10} for n in (11, 12, 13)]}
			counts: Counter = Counter()
			real_run = subprocess.run
			# @used-by :meth:`GitLifecycleMemoizationTests.test_audit_memoizes_readonly_git_commands_across_multiple_issues()`
			def spy_run(cmd, *args, **kwargs):
				sub = _git_subcommand(cmd)
				if None is not sub:
					counts[sub] += 1
				return real_run(cmd, *args, **kwargs)
			with patch.object(subprocess, 'run', side_effect=spy_run):
				res = issue_lifecycle.code_and_issue_lifecycle_status(proj, turn)
			self.assertTrue(res['verified'], res)
			self.assertEqual(1, counts['status'], counts)
			self.assertEqual(1, counts['log'], counts)
			self.assertLessEqual(counts['rev-parse'], 1, counts)
			self.assertLessEqual(counts['rev-list'], 1, counts)
	# @used-by :mod:`unittest`
	def test_verify_issue_ready_for_close_memoizes_parent_child_and_catches_defects(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj, code = _init_multi_issue_repo(Path(tmp).resolve())
			counts: Counter = Counter()
			real_run = subprocess.run
			# @used-by :meth:`GitLifecycleMemoizationTests.test_verify_issue_ready_for_close_memoizes_parent_child_and_catches_defects()`
			def spy_run(cmd, *args, **kwargs):
				sub = _git_subcommand(cmd)
				if None is not sub:
					counts[sub] += 1
				return real_run(cmd, *args, **kwargs)
			with patch.object(subprocess, 'run', side_effect=spy_run):
				res = git_gate.verify_repo_issue_ready_for_close(code, 'acme/demo', 10, project_root=proj)
			self.assertTrue(res['verified'], res)
			self.assertEqual([11, 12, 13], res['child_issues'])
			self.assertEqual(1, counts['status'], counts)
			self.assertEqual(1, counts['log'], counts)
			self.assertLessEqual(counts['rev-parse'], 1, counts)
			self.assertLessEqual(counts['rev-list'], 1, counts)
			with self.assertRaisesRegex(ValueError, 'no commit'):
				git_gate.verify_repo_issue_ready_for_close(code, 'acme/demo', 99, project_root=proj)
			(code / 'd.py').write_text('# https://github.com/acme/demo/issues/14\nVAL = 14\n', encoding='utf-8')
			with self.assertRaisesRegex(ValueError, 'uncommitted file'):
				git_gate.verify_repo_issue_ready_for_close(code, 'acme/demo', 14, project_root=proj)
			subprocess.run(['git', '-C', str(code), 'add', 'd.py'], check=True, capture_output=True)
			subprocess.run(['git', '-C', str(code), 'commit', '-m', 'https://github.com/acme/demo/issues/14'], check=True, capture_output=True)
			with self.assertRaisesRegex(ValueError, 'has not been pushed'):
				git_gate.verify_repo_issue_ready_for_close(code, 'acme/demo', 14, project_root=proj)
if '__main__' == __name__:
	unittest.main()
