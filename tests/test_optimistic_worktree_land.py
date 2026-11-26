# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Split worktree-land into optimistic pre-lease verification and targeted wait":
# https://github.com/dmitry-ai/harness/issues/350
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import completion
from agent_tools.landing_lease import acquire_lease, lease_status, release_lease
from agent_tools.repo_wait import _workspace_code_repos, run_with_transient_wait
from agent_tools.worktree_flow import worktree_begin, worktree_cleanup, worktree_land
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# @used-by :func:`_init_repo()`
# @used-by :func:`_init_workspace()`
# @used-by :meth:`OptimisticWorktreeLandTests.test_concurrent_main_advance_retries_optimistically_and_lands()`
# @used-by :meth:`OptimisticWorktreeLandTests.test_optimistic_phase1_runs_tests_without_holding_fifo_lease()`
# @used-by :meth:`OptimisticWorktreeLandTests.test_repeated_main_collisions_fall_back_to_fifo_lease()`
def _git(repo: Path, *args: str) -> str:
	proc = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=True, creationflags=_NO_WINDOW)
	return (proc.stdout or '').strip()
# @used-by :meth:`OptimisticWorktreeLandTests.test_concurrent_main_advance_retries_optimistically_and_lands()`
# @used-by :meth:`OptimisticWorktreeLandTests.test_dirty_worktree_fails_fast_without_acquiring_lease()`
# @used-by :meth:`OptimisticWorktreeLandTests.test_optimistic_phase1_runs_tests_without_holding_fifo_lease()`
# @used-by :meth:`OptimisticWorktreeLandTests.test_repeated_main_collisions_fall_back_to_fifo_lease()`
def _init_repo(root: Path, test_code: str) -> Path:
	repo = root / 'repo'
	(repo / 'tests').mkdir(parents=True)
	_git(repo, 'init', '-b', 'main')
	_git(repo, 'config', 'user.email', 'test@example.com')
	_git(repo, 'config', 'user.name', 'Test')
	(repo / 'README.md').write_text('# Demo\n', encoding='utf-8')
	(repo / 'tests/test_probe.py').write_text(test_code, encoding='utf-8')
	_git(repo, 'add', '.')
	_git(repo, 'commit', '-m', 'init')
	return repo
# @used-by :meth:`OptimisticWorktreeLandTests.test_targeted_wait_blocks_when_turn_touches_leased_repo_or_worktree()`
# @used-by :meth:`OptimisticWorktreeLandTests.test_targeted_wait_bypasses_foreign_lease_on_readonly_and_noncode_turns()`
def _init_workspace(root: Path) -> tuple[Path, Path]:
	proj = root / 'proj'
	code_repo = proj / '\u2c0f/\u227b/\u2655/\u26ef'
	code_repo.mkdir(parents=True)
	(proj / '\ua616/data/turns').mkdir(parents=True)
	_git(code_repo, 'init', '-b', 'main')
	_git(code_repo, 'config', 'user.email', 'test@example.com')
	_git(code_repo, 'config', 'user.name', 'Test')
	(code_repo / 'mod.py').write_text('X = 1\n', encoding='utf-8')
	_git(code_repo, 'add', 'mod.py')
	_git(code_repo, 'commit', '-m', 'init')
	return (proj, code_repo)
# @used-by :meth:`OptimisticWorktreeLandTests.test_concurrent_main_advance_retries_optimistically_and_lands()`
# @used-by :meth:`OptimisticWorktreeLandTests.test_optimistic_phase1_runs_tests_without_holding_fifo_lease()`
# @used-by :meth:`OptimisticWorktreeLandTests.test_repeated_main_collisions_fall_back_to_fifo_lease()`
def _probe_script(main_repo: Path, leases_dir: Path, marker: Path, *, advance_mode: str) -> str:
	lines = [
		'from pathlib import Path',
		'import subprocess',
		'import sys',
		'import unittest',
		f'sys.path.insert(0, {str(SCRIPTS)!r})',
		'from agent_tools.landing_lease import lease_status',
		f'MAIN_REPO = Path({str(main_repo)!r})',
		f'LEASES_DIR = Path({str(leases_dir)!r})',
		f'MARKER = Path({str(marker)!r})',
		f'MODE = {advance_mode!r}',
		'class ProbeTests(unittest.TestCase):',
		'\tdef test_probe(self) -> None:',
		"\t\tis_free = bool(lease_status(MAIN_REPO, leases_dir=LEASES_DIR)['free'])",
		"\t\tprev = MARKER.read_text(encoding='utf-8').splitlines() if MARKER.is_file() else []",
		"\t\tMARKER.write_text('\\n'.join([*prev, 'free' if is_free else 'held']) + '\\n', encoding='utf-8')",
		'\t\tcount = len(prev) + 1',
		"\t\tshould_adv = ('once' == MODE and 1 == count) or ('while_free' == MODE and is_free)",
		'\t\tif should_adv:',
		"\t\t\t(MAIN_REPO / f'adv_{count}.txt').write_text(f'{count}\\n', encoding='utf-8')",
		"\t\t\tsubprocess.run(['git', '-C', str(MAIN_REPO), 'add', f'adv_{count}.txt'], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30)",
		"\t\t\tsubprocess.run(['git', '-C', str(MAIN_REPO), 'commit', '-m', f'concurrent {count}'], stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=30)",
		'\t\tself.assertTrue(True)',
	]
	return '\n'.join(lines) + '\n'
# @used-by :meth:`OptimisticWorktreeLandTests.test_targeted_wait_blocks_when_turn_touches_leased_repo_or_worktree()`
# @used-by :meth:`OptimisticWorktreeLandTests.test_targeted_wait_bypasses_foreign_lease_on_readonly_and_noncode_turns()`
def _write_turn_state(proj: Path, name: str, data: dict) -> Path:
	dest = proj / '\ua616/data/turns' / f'{name}.json'
	dest.write_text(json.dumps(data, ensure_ascii=False, indent='\t') + '\n', encoding='utf-8')
	return dest
# @used-by :mod:`unittest`
class OptimisticWorktreeLandTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_concurrent_main_advance_retries_optimistically_and_lands(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			leases = root / 'leases'
			marker = root / 'probe.log'
			repo = _init_repo(root, _probe_script(root / 'repo', leases, marker, advance_mode='once'))
			wt = Path(worktree_begin(repo, 'opt-retry', worktrees_dir=root / 'wts')['worktree'])
			# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
			(wt / 'feat.py').write_text('VAL = 1\n', encoding='utf-8')
			_git(wt, 'add', 'feat.py')
			_git(wt, 'commit', '-m', 'add feature')
			res = worktree_land(wt, run_tests=True, remove=True, owner='retry-1', leases_dir=leases)
			self.assertTrue(res['valid'], res)
			self.assertTrue(res['landed'], res)
			self.assertEqual('optimistic', res['land_mode'])
			self.assertEqual(1, res['optimistic_retries'])
			self.assertEqual(2, res['test_runs'])
			self.assertTrue((repo / 'adv_1.txt').is_file())
			self.assertTrue((repo / 'feat.py').is_file())
			self.assertEqual(['free', 'free'], marker.read_text(encoding='utf-8').splitlines())
			self.assertTrue(lease_status(repo, leases_dir=leases)['free'])
	# @used-by :mod:`unittest`
	def test_dirty_worktree_fails_fast_without_acquiring_lease(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			leases = root / 'leases'
			repo = _init_repo(root, 'import unittest\nclass Ok(unittest.TestCase):\n\tdef test_ok(self) -> None:\n\t\tself.assertTrue(True)\n')
			wt = Path(worktree_begin(repo, 'dirty-wt', worktrees_dir=root / 'wts')['worktree'])
			(wt / 'wip.txt').write_text('uncommitted\n', encoding='utf-8')
			acquire_lease(repo, 'foreign-holder', leases_dir=leases)
			try:
				t0 = time.monotonic()
				res = worktree_land(wt, run_tests=True, remove=False, owner='dirty-owner', wait_timeout=5.0, leases_dir=leases)
				elapsed = time.monotonic() - t0
			finally:
				release_lease(repo, 'foreign-holder', leases_dir=leases)
				worktree_cleanup(repo, wt, force=True)
			self.assertFalse(res['valid'], res)
			self.assertFalse(res['landed'], res)
			self.assertEqual('dirty_worktree', res['stage'])
			self.assertEqual(0, res['test_runs'])
			self.assertLess(elapsed, 1.5)
	# @used-by :mod:`unittest`
	def test_optimistic_phase1_runs_tests_without_holding_fifo_lease(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			leases = root / 'leases'
			marker = root / 'probe.log'
			repo = _init_repo(root, _probe_script(root / 'repo', leases, marker, advance_mode='none'))
			wt = Path(worktree_begin(repo, 'opt-free', worktrees_dir=root / 'wts')['worktree'])
			# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
			(wt / 'feat.py').write_text('VAL = 1\n', encoding='utf-8')
			_git(wt, 'add', 'feat.py')
			_git(wt, 'commit', '-m', 'add feat')
			res = worktree_land(wt, run_tests=True, remove=True, owner='opt-1', leases_dir=leases)
			self.assertTrue(res['valid'], res)
			self.assertTrue(res['landed'], res)
			self.assertEqual('optimistic', res['land_mode'])
			self.assertEqual(0, res['optimistic_retries'])
			self.assertEqual(1, res['test_runs'])
			self.assertEqual(['free'], marker.read_text(encoding='utf-8').splitlines())
			self.assertTrue((repo / 'feat.py').is_file())
			self.assertTrue(lease_status(repo, leases_dir=leases)['free'])
	# @used-by :mod:`unittest`
	def test_repeated_main_collisions_fall_back_to_fifo_lease(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			leases = root / 'leases'
			marker = root / 'probe.log'
			repo = _init_repo(root, _probe_script(root / 'repo', leases, marker, advance_mode='while_free'))
			wt = Path(worktree_begin(repo, 'opt-fallback', worktrees_dir=root / 'wts')['worktree'])
			# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
			(wt / 'feat.py').write_text('VAL = 1\n', encoding='utf-8')
			_git(wt, 'add', 'feat.py')
			_git(wt, 'commit', '-m', 'add fallback feature')
			res = worktree_land(wt, run_tests=True, remove=True, owner='fb-1', leases_dir=leases, max_optimistic_retries=2)
			self.assertTrue(res['valid'], res)
			self.assertTrue(res['landed'], res)
			self.assertEqual('fifo_fallback', res['land_mode'])
			self.assertEqual(2, res['optimistic_retries'])
			self.assertEqual(3, res['test_runs'])
			self.assertEqual(['free', 'free', 'held'], marker.read_text(encoding='utf-8').splitlines())
			self.assertTrue((repo / 'feat.py').is_file())
			self.assertTrue((repo / 'adv_1.txt').is_file())
			self.assertTrue((repo / 'adv_2.txt').is_file())
			self.assertTrue(lease_status(repo, leases_dir=leases)['free'])
	# @used-by :mod:`unittest`
	def test_targeted_wait_blocks_when_turn_touches_leased_repo_or_worktree(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			proj, code_repo = _init_workspace(root)
			wt = Path(worktree_begin(code_repo, 'wait-wt', worktrees_dir=proj / '\ua616/data/worktrees')['worktree'])
			cid = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
			_write_turn_state(proj, 'turnwt', {'conversation_id': cid, 'status': 'open', 'touched_files': [str(wt / 'mod.py')]})
			acquire_lease(code_repo, 'foreign-owner')
			# @used-by :meth:`OptimisticWorktreeLandTests.test_targeted_wait_blocks_when_turn_touches_leased_repo_or_worktree()`
			def _release_soon() -> None:
				time.sleep(0.2)
				release_lease(code_repo, 'foreign-owner')
			worker = threading.Thread(target=_release_soon, daemon=True)
			worker.start()
			try:
				res = run_with_transient_wait(proj, lambda: {'ready': True}, wait_timeout=2.0, poll_interval=0.05, conversation=cid)
			finally:
				worker.join(timeout=3.0)
				release_lease(code_repo, 'foreign-owner')
				worktree_cleanup(code_repo, wt, force=True)
			self.assertTrue(res['ready'], res)
			self.assertGreaterEqual(res['lease_wait_seconds'], 0.15)
	# @used-by :mod:`unittest`
	def test_targeted_wait_bypasses_foreign_lease_on_readonly_and_noncode_turns(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td).resolve()
			proj, code_repo = _init_workspace(root)
			self.assertEqual([code_repo.resolve()], _workspace_code_repos(proj))
			cid_ro = '11111111-1111-1111-1111-111111111111'
			cid_kb = '22222222-2222-2222-2222-222222222222'
			cid_new = '33333333-3333-3333-3333-333333333333'
			_write_turn_state(proj, 'turnro', {'conversation_id': cid_ro, 'status': 'open', 'touched_files': []})
			_write_turn_state(proj, 'turnkb', {'conversation_id': cid_kb, 'status': 'open', 'touched_files': [str(proj / '\ua616/KB/note.md')]})
			acquire_lease(code_repo, 'foreign-owner')
			try:
				t0 = time.monotonic()
				with patch.object(completion, '_prepare_once', return_value={'ready': True, 'status': 'prepared'}):
					res_ro = completion.prepare(proj, 'Read-only reply.', cid_ro, wait_timeout=5.0, wait_poll=0.05)
					res_new = completion.prepare(proj, 'Brand-new reply.', cid_new, wait_timeout=5.0, wait_poll=0.05)
				res_kb = run_with_transient_wait(proj, lambda: {'ready': True}, wait_timeout=5.0, poll_interval=0.05, conversation=cid_kb)
				res_exp = run_with_transient_wait(proj, lambda: {'ready': True}, wait_timeout=5.0, poll_interval=0.05, wait_repos=[])
				elapsed = time.monotonic() - t0
			finally:
				release_lease(code_repo, 'foreign-owner')
			self.assertLess(elapsed, 1.5)
			for item in (res_ro, res_new, res_kb, res_exp):
				self.assertTrue(item['ready'], item)
				self.assertEqual(0.0, item['lease_wait_seconds'], item)
if '__main__' == __name__:
	unittest.main()
