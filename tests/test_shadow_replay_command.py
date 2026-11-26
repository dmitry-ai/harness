# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add mutating command execution mode to shadow-replay with isolated native profiles":
# https://github.com/dmitry-ai/harness/issues/289
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
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
HARNESS_PY = SCRIPTS / 'harness.py'
# @used-by :func:`_run_harness()`
def _iso_env(home: Path) -> dict[str, str]:
	return {**os.environ, 'USERPROFILE': str(home), 'HOME': str(home), 'APPDATA': str(home / 'AppData/Roaming'), 'HARNESS_TEST_NO_FSYNC': '1', 'GIT_OPTIONAL_LOCKS': '0', 'PYTHONIOENCODING': 'utf-8'}
# @used-by :meth:`ShadowReplayCommandTests.test_shadow_replay_exec_rename_domain_isolated_and_writes_receipt()`
# @used-by :meth:`ShadowReplayCommandTests.test_shadow_replay_generic_command_and_failure_receipt()`
def _run_harness(base: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run([sys.executable, str(HARNESS_PY), *args], cwd=str(base), env=_iso_env(base / 'home'), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=90, check=False)
# @used-by :meth:`ShadowReplayCommandTests.test_shadow_replay_exec_rename_domain_isolated_and_writes_receipt()`
# @used-by :meth:`ShadowReplayCommandTests.test_shadow_replay_generic_command_and_failure_receipt()`
def _snapshot_tree(root: Path) -> dict[str, str]:
	return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
# @used-by :mod:`unittest`
class ShadowReplayCommandTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_shadow_replay_exec_rename_domain_isolated_and_writes_receipt(self) -> None:
		from test_project_rename import _seed_dual_antigravity
		from test_project_rename_verification import _seed_complete_workflow, _seed_proposals_layout
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, _daily, launcher, _l_turn = _seed_proposals_layout(base)
			_seed_complete_workflow(proj)
			ag_dirs, folders, _reg = _seed_dual_antigravity(base, proj)
			ws = base / 'workspace'
			(ws / '\ua616/data/scratch').mkdir(parents=True)
			(ws / '\ua616/paths.json').write_text('{"version": 1}\n', encoding='utf-8')
			proj_before = _snapshot_tree(proj)
			launcher_before = _snapshot_tree(launcher)
			ag_before = _snapshot_tree(base / 'ag')
			proc = _run_harness(base, 'shadow-replay', str(proj), '--exec-rename-domain', 'blueskypeptide.com', '--workspace', str(ws))
			self.assertEqual(0, proc.returncode, f'STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
			res = json.loads(proc.stdout)
			self.assertTrue(res['valid'], res)
			self.assertTrue(res['cleaned_up'])
			self.assertFalse(Path(res['shadow_dir']).exists())
			self.assertIn('command_exec', res['stages_verified'])
			self.assertIn('post_rename_verify', res['stages_verified'])
			self.assertEqual(proj_before, _snapshot_tree(proj))
			self.assertEqual(launcher_before, _snapshot_tree(launcher))
			self.assertEqual(ag_before, _snapshot_tree(base / 'ag'))
			receipt_f = ws / '\ua616/data/shadow-replay-receipt.json'
			self.assertTrue(receipt_f.is_file())
			receipt = json.loads(receipt_f.read_text(encoding='utf-8'))
			self.assertTrue(receipt['valid'], receipt)
			self.assertEqual(0, receipt['exit_code'])
			self.assertEqual('blueskypeptide.com', receipt['exec_rename_domain'])
	# @used-by :mod:`unittest`
	def test_shadow_replay_generic_command_and_failure_receipt(self) -> None:
		from test_project_rename_verification import _seed_complete_workflow, _seed_proposals_layout
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, _daily, launcher, _l_turn = _seed_proposals_layout(base)
			_seed_complete_workflow(proj)
			ws = base / 'workspace'
			(ws / '\ua616/data/scratch').mkdir(parents=True)
			(ws / '\ua616/paths.json').write_text('{"version": 1}\n', encoding='utf-8')
			proj_before = _snapshot_tree(proj)
			launcher_before = _snapshot_tree(launcher)
			ok_proc = _run_harness(base, 'shadow-replay', str(proj), '--command', 'rename-project {project} --domain blueskypeptide.com --no-register', '--workspace', str(ws))
			self.assertEqual(0, ok_proc.returncode, f'STDOUT:\n{ok_proc.stdout}\nSTDERR:\n{ok_proc.stderr}')
			ok_res = json.loads(ok_proc.stdout)
			self.assertTrue(ok_res['valid'], ok_res)
			self.assertIn('command_exec', ok_res['stages_verified'])
			self.assertEqual(proj_before, _snapshot_tree(proj))
			self.assertEqual(launcher_before, _snapshot_tree(launcher))
			bad_proc = _run_harness(base, 'shadow-replay', str(proj), '--command', 'rename-project {project} --domain invalid-kebab-slug --no-register', '--workspace', str(ws))
			self.assertEqual(2, bad_proc.returncode, f'STDOUT:\n{bad_proc.stdout}\nSTDERR:\n{bad_proc.stderr}')
			bad_res = json.loads(bad_proc.stdout)
			self.assertFalse(bad_res['valid'], bad_res)
			self.assertTrue(bad_res['cleaned_up'])
			receipt = json.loads((ws / '\ua616/data/shadow-replay-receipt.json').read_text(encoding='utf-8'))
			self.assertFalse(receipt['valid'], receipt)
			self.assertEqual(2, receipt['exit_code'])
if '__main__' == __name__:
	unittest.main()
