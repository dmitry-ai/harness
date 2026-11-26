# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Harden addon companion observability and conflict reservation hygiene":
# https://github.com/dmitry-ai/harness/issues/302
from __future__ import annotations
from pathlib import Path
from unittest import mock
import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
WORKTREE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WORKTREE_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion, journal
from agent_tools.issues.service import GitHubIssueService
from agent_tools.issues.service_helpers import dirty_issue_first_files
from agent_tools.issues.workspace import IssueEvidenceWorkspace
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :class:`AddonObservabilityTests`
class AddonObservabilityTests(unittest.TestCase):
	# @used-by :meth:`AddonObservabilityTests._init_addons_repo()`
	def _git(self, repo: Path, *args: str) -> str:
		proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True, creationflags=_NO_WINDOW)
		return (proc.stdout or '').strip()
	# @used-by :meth:`AddonObservabilityTests.test_close_blocks_antigravity_addons_when_companion_unhealthy()`
	# @used-by :meth:`AddonObservabilityTests.test_dirty_issue_first_excludes_live_runtime_data_only()`
	def _init_addons_repo(self, root: Path) -> Path:
		proj = root / 'Addons'
		code = proj / '\u2c0f/\u227b/\u2655/\u26ef'
		(code / 'Folders').mkdir(parents=True)
		(code / 'Upgrade').mkdir(parents=True)
		(proj / '\ua616').mkdir(parents=True)
		(code / 'Folders/folders.json').write_text('{"folders":[]}\n', encoding='utf-8')
		(code / 'Upgrade/package.json').write_text('{"name":"test"}\n', encoding='utf-8')
		self._git(code, 'init', '-b', 'main')
		self._git(code, 'config', 'user.email', 'test@example.com')
		self._git(code, 'config', 'user.name', 'Test')
		self._git(code, 'remote', 'add', 'origin', 'https://github.com/dmitry-ai/antigravity-addons.git')
		self._git(code, 'add', '.')
		self._git(code, 'commit', '-m', 'init')
		return code
	# @used-by :mod:`unittest`
	def test_close_blocks_antigravity_addons_when_companion_unhealthy(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			rt_file = root / 'runtime.json'
			rt_file.write_text(json.dumps({'state': 'error', 'pid': os.getpid(), 'runtimePath': 'C:/work/Addons/Upgrade/cdp-companion.js', 'errors': {'A0:2': 'Debugger not attached'}}), encoding='utf-8')
			code = self._init_addons_repo(root)
			ws = IssueEvidenceWorkspace()
			svc = GitHubIssueService(api_fn=lambda *a, **kw: {'state': 'closed'}, workspace=ws)
			args = argparse.Namespace(repo='dmitry-ai/antigravity-addons', issue=71, reason='completed', comment_file=None, consume_input=False, project_root=str(code.parents[3]), repo_root=str(code), target_locale='en-US')
			with mock.patch.dict(os.environ, {'HARNESS_COMPANION_RUNTIME_JSON': str(rt_file)}), mock.patch('agent_tools.issues.service.verify_repo_issue_ready_for_close', return_value={'verified': True}), mock.patch('agent_tools.issues.service.dump_json') as mocked_dump:
				rc = svc.cmd_close(args)
			self.assertEqual(2, rc)
			payload = mocked_dump.call_args[0][0]
			self.assertFalse(payload['ok'])
			self.assertEqual('pre_flight_companion_health', payload['stage'])
	# @used-by :mod:`unittest`
	def test_companion_runtime_health_detects_error_dead_pid_and_worktree_path(self) -> None:
		from agent_tools.addon_observability import inspect_companion_runtime_health
		with tempfile.TemporaryDirectory() as td:
			rt_file = Path(td) / 'runtime.json'
			self.assertTrue(inspect_companion_runtime_health(rt_file)['healthy'])
			rt_file.write_text(json.dumps({'state': 'connected', 'pid': 12345, 'runtimePath': 'C:/work/Addons/\u2c0f/\u227b/\u2655/\u26ef/Upgrade/cdp-companion.js', 'errors': {}}), encoding='utf-8')
			ok_res = inspect_companion_runtime_health(rt_file, pid_alive_fn=lambda pid: 12345 == pid)
			self.assertTrue(ok_res['healthy'])
			dead_res = inspect_companion_runtime_health(rt_file, pid_alive_fn=lambda _pid: False)
			self.assertFalse(dead_res['healthy'])
			self.assertTrue(any(('dead' in i.lower() or 'pid' in i.lower() for i in dead_res['issues'])))
			rt_file.write_text(json.dumps({'state': 'connected', 'pid': 12345, 'runtimePath': 'C:/work/Addons/\ua616/data/worktrees/tmp/Upgrade/cdp-companion.js', 'errors': {}}), encoding='utf-8')
			wt_res = inspect_companion_runtime_health(rt_file, pid_alive_fn=lambda _pid: True)
			self.assertFalse(wt_res['healthy'])
			self.assertTrue(any(('worktree' in i.lower() for i in wt_res['issues'])))
			rt_file.write_text(json.dumps({'state': 'error', 'pid': 12345, 'runtimePath': 'C:/work/Addons/Upgrade/cdp-companion.js', 'errors': {'A0:2': 'broken'}}), encoding='utf-8')
			err_res = inspect_companion_runtime_health(rt_file, pid_alive_fn=lambda _pid: True)
			self.assertFalse(err_res['healthy'])
			self.assertTrue(any(('error' in i.lower() for i in err_res['issues'])))
	# @used-by :mod:`unittest`
	def test_conflict_recording_and_reconciliation_prune_terminal_reservations(self) -> None:
		from agent_tools.journal_integrity import prune_terminal_conflict_reservations
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			jdir = root / '\ua66e'
			(jdir / '\u227b').mkdir(parents=True)
			(jdir / '\u227a').mkdir(parents=True)
			turns_dir = root / '\ua616/data/turns'
			turns_dir.mkdir(parents=True)
			journal.reserve_turn_steps(jdir, 'k-conflict', 'cid-1', ['cid-1-0'])
			journal.reserve_turn_steps(jdir, 'k-open', 'cid-2', ['cid-2-0'])
			(turns_dir / 'k-conflict.json').write_text(json.dumps({'key': 'k-conflict', 'status': 'conflict', 'conversation_id': 'cid-1', 'delivery': {'verified': False, 'retryable': False, 'conflict_evidence': '\ua616/data/turns/conflicts/k-conflict.txt'}}), encoding='utf-8')
			(turns_dir / 'k-open.json').write_text(json.dumps({'key': 'k-open', 'status': 'open', 'conversation_id': 'cid-2'}), encoding='utf-8')
			pruned = prune_terminal_conflict_reservations(root, jdir, folder_fn=lambda r: r / '\ua616/data/turns', read_fn=lambda p: json.loads(p.read_text(encoding='utf-8')))
			self.assertEqual(['k-conflict'], pruned)
			rem = journal.iter_turn_reservations(jdir)
			self.assertNotIn('k-conflict', rem)
			self.assertIn('k-open', rem)
			self.assertTrue((turns_dir / 'k-conflict.json').is_file())
			journal.reserve_turn_steps(jdir, 'k-new', 'cid-3', ['cid-3-0'])
			st_path = turns_dir / 'k-new.json'
			val = {'key': 'k-new', 'status': 'open', 'journal': str(jdir), 'prepared': None, 'reserved_journal_steps': [2]}
			turn = {'final_step': 5, 'requests': [{'id': 'cid-3-0', 'text': 'hi'}]}
			completion._conflict(root, st_path, val, {'source_file': str(root / 't.jsonl')}, turn, 'resp', 'mismatch')
			self.assertNotIn('k-new', journal.iter_turn_reservations(jdir))
			self.assertNotIn('reserved_journal_steps', json.loads(st_path.read_text(encoding='utf-8')))
			self.assertTrue(st_path.is_file())
			no_j_path = turns_dir / 'k-noj.json'
			completion._conflict(root, no_j_path, {'key': 'k-noj', 'status': 'open', 'prepared': None}, {'source_file': str(root / 't.jsonl')}, turn, 'resp', 'mismatch')
			self.assertEqual('conflict', json.loads(no_j_path.read_text(encoding='utf-8'))['status'])
	# @used-by :mod:`unittest`
	def test_dirty_issue_first_excludes_live_runtime_data_only(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			code = self._init_addons_repo(root)
			(code / 'Folders/folders.json').write_text('{"folders":[{"id":"1"}]}\n', encoding='utf-8')
			ws = IssueEvidenceWorkspace()
			self.assertEqual([], dirty_issue_first_files(ws, 'dmitry-ai/antigravity-addons', repo_root=code))
			(code / 'Upgrade/package.json').write_text('{"name":"changed"}\n', encoding='utf-8')
			self.assertEqual(['Upgrade/package.json'], dirty_issue_first_files(ws, 'dmitry-ai/antigravity-addons', repo_root=code))
	# @used-by :mod:`unittest`
	def test_pre_invocation_surfaces_companion_warning(self) -> None:
		from agent_tools.addon_observability import format_pre_invocation_companion_warning
		with tempfile.TemporaryDirectory() as td:
			rt_file = Path(td) / 'runtime.json'
			rt_file.write_text(json.dumps({'state': 'error', 'pid': os.getpid(), 'runtimePath': 'C:/work/Addons/\ua616/data/worktrees/x/Upgrade/cdp-companion.js', 'errors': {'runtime': 'ENOENT'}}), encoding='utf-8')
			warn = format_pre_invocation_companion_warning(rt_file, pid_alive_fn=lambda _p: True)
			self.assertIn('companion_warning=', warn)
			self.assertIn('worktree', warn.lower())
			rt_file.write_text(json.dumps({'state': 'connected', 'pid': os.getpid(), 'runtimePath': 'C:/work/Addons/Upgrade/cdp-companion.js', 'errors': {}}), encoding='utf-8')
			self.assertEqual('', format_pre_invocation_companion_warning(rt_file, pid_alive_fn=lambda _p: True))
	# @used-by :mod:`unittest`
	def test_suppressed_worktree_removal_error_audit(self) -> None:
		from agent_tools.addon_observability import evaluate_worktree_removal_audit
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			tx = root / 'transcript_full.jsonl'
			rows = [
				{'step_index': 0, 'type': 'USER_INPUT', 'content': 'Fix repo'},
				{'step_index': 1, 'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'git worktree remove wt'}}]},
				{'step_index': 2, 'type': 'GENERIC', 'content': "error: failed to delete 'C:/work/repo/\ua616/data/worktrees/demo': Permission denied"},
			]
			tx.write_text('\n'.join((json.dumps(r) for r in rows)) + '\n', encoding='utf-8')
			native = {'source_file': str(tx)}
			turn = {'start_step': 0, 'completed': False}
			bad = evaluate_worktree_removal_audit(root, native, turn, {'key': 'k1'}, 'Everything succeeded cleanly.')
			self.assertFalse(bad['verified'])
			self.assertIn('Permission denied', bad['detail'])
			ok = evaluate_worktree_removal_audit(root, native, turn, {'key': 'k1'}, 'Worktree cleanup hit Permission denied while deleting worktrees/demo.')
			self.assertTrue(ok['verified'])
if '__main__' == __name__:
	unittest.main()
