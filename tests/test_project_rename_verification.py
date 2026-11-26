# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Auto-detect launcher root and enforce post-rename invariant verification with rollback":
# https://github.com/dmitry-ai/harness/issues/288
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
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
# @used-by :meth:`ProjectRenameVerificationTests.test_auto_detects_sibling_init_launcher_without_flag()`
# @used-by :meth:`ProjectRenameVerificationTests.test_promote_domain_updates_sibling_init_launcher()`
def _run_harness(base: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run([sys.executable, str(HARNESS_PY), *args], cwd=str(base), env=_iso_env(base / 'home'), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=60, check=False)
# @used-by :meth:`ProjectRenameVerificationTests.test_auto_detects_sibling_init_launcher_without_flag()`
# @used-by :meth:`ProjectRenameVerificationTests.test_post_verify_rolls_back_all_state_on_stage_or_review_regression()`
# @used-by :meth:`ProjectRenameVerificationTests.test_promote_domain_updates_sibling_init_launcher()`
# @used-by :meth:`test_shadow_replay_command.ShadowReplayCommandTests.test_shadow_replay_exec_rename_domain_isolated_and_writes_receipt()`
# @used-by :meth:`test_shadow_replay_command.ShadowReplayCommandTests.test_shadow_replay_generic_command_and_failure_receipt()`
def _seed_proposals_layout(base: Path, *, job_id: str='~022124567641351805598') -> tuple[Path, Path, Path, Path]:
	from agent_tools import upwork_project as up
	from test_onboarding import source
	daily = base / 'proposals/daily'
	launcher = base / 'proposals/init'
	data = {**source(job_id), 'url': f'https://upwork.com/jobs/{job_id}'}
	res = up.initialize_upwork_project(job_id, topic='Magento & GA4', date_str='2026-11-23', daily_root=daily, extracted_data=data, register_native=False)
	proj = Path(res['project_dir']).resolve()
	l_turn = launcher / '\ua616/data/turns/handoff01.json'
	l_turn.parent.mkdir(parents=True, exist_ok=True)
	l_turn.write_text(json.dumps({'key': 'handoff01', 'status': 'handed_off', 'handed_off_to': {'project_root': str(proj), 'job_id': job_id}}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
	return (proj, daily, launcher, l_turn)
# @used-by :meth:`ProjectRenameVerificationTests.test_post_verify_rolls_back_all_state_on_stage_or_review_regression()`
# @used-by :meth:`test_shadow_replay_command.ShadowReplayCommandTests.test_shadow_replay_exec_rename_domain_isolated_and_writes_receipt()`
# @used-by :meth:`test_shadow_replay_command.ShadowReplayCommandTests.test_shadow_replay_generic_command_and_failure_receipt()`
def _seed_complete_workflow(proj: Path) -> None:
	pj_sha = hashlib.sha256((proj / '\ua616/project.json').read_bytes()).hexdigest()
	out_f = proj / '\ua616/KB/Evidence/init-ok.json'
	out_f.parent.mkdir(parents=True, exist_ok=True)
	out_f.write_text('{"ok": true}\n', encoding='utf-8')
	out_sha = hashlib.sha256(out_f.read_bytes()).hexdigest()
	wf_f = proj / '\ua616/data/workflow.json'
	wf_f.parent.mkdir(parents=True, exist_ok=True)
	wf_f.write_text(json.dumps({'schema_version': 1, 'project_root': str(proj), 'job_id': '~022124567641351805598', 'stages': {'capture': {'status': 'complete', 'inputs': {}, 'outputs': {'\ua616/project.json': pj_sha}}, 'identity_init': {'status': 'complete', 'inputs': {'\ua616/project.json': pj_sha}, 'outputs': {'\ua616/KB/Evidence/init-ok.json': out_sha}}}, 'questions': {}, 'reviews': [], 'requests': [], 'events': []}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
# @used-by :meth:`ProjectRenameVerificationTests.test_post_verify_rolls_back_all_state_on_stage_or_review_regression()`
def _snapshot_tree(root: Path) -> dict[str, str]:
	return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
# @used-by :mod:`unittest`
class ProjectRenameVerificationTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_auto_detects_sibling_init_launcher_without_flag(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, _daily, launcher, l_turn = _seed_proposals_layout(base)
			proc = _run_harness(base, 'rename-project', str(proj), '--domain', 'blueskypeptide.com', '--no-register')
			self.assertEqual(0, proc.returncode, f'STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
			payload = json.loads(proc.stdout)
			new_proj = Path(payload['project_dir']).resolve()
			self.assertTrue(payload['valid'], payload)
			self.assertEqual(str(launcher.resolve()), payload.get('launcher_root'))
			self.assertTrue((payload.get('post_verification') or {}).get('valid'), payload)
			self.assertEqual(str(new_proj), json.loads(l_turn.read_text(encoding='utf-8'))['handed_off_to']['project_root'])
	# @used-by :mod:`unittest`
	def test_post_verify_rolls_back_all_state_on_stage_or_review_regression(self) -> None:
		from agent_tools.project_rename import rename_project
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, daily, _launcher, l_turn = _seed_proposals_layout(base)
			_seed_complete_workflow(proj)
			proj_before = _snapshot_tree(proj)
			launcher_before = l_turn.read_bytes()
			idx_file = daily / '\ua616/data/projects.json'
			idx_before = idx_file.read_bytes()
			# @used-by :meth:`ProjectRenameVerificationTests.test_post_verify_rolls_back_all_state_on_stage_or_review_regression()`
			def _fake_stage_statuses(root, state):
				p_res = Path(root).resolve()
				return {'capture': 'complete', 'identity_init': 'stale' if 'blueskypeptide.com' in p_res.name else 'complete'}
			with patch('agent_tools.workflow.stage_statuses', side_effect=_fake_stage_statuses):
				res = rename_project(proj, domain='blueskypeptide.com', register_native=False)
			self.assertFalse(res['valid'], res)
			self.assertTrue(res.get('rolled_back'), res)
			self.assertFalse(res.get('renamed'), res)
			self.assertTrue(proj.is_dir())
			self.assertFalse((proj.parent / '1 - blueskypeptide.com').exists())
			self.assertEqual(proj_before, _snapshot_tree(proj))
			self.assertEqual(launcher_before, l_turn.read_bytes())
			self.assertEqual(idx_before, idx_file.read_bytes())
	# @used-by :mod:`unittest`
	def test_promote_domain_updates_sibling_init_launcher(self) -> None:
		from test_project_rename import _target_analysis
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, _daily, _launcher, l_turn = _seed_proposals_layout(base, job_id='~022124567641351805591')
			cand = proj / '\ua616/data/scratch/cand.json'
			cand.parent.mkdir(parents=True, exist_ok=True)
			cand.write_text(json.dumps(_target_analysis(proj, url='https://www.blueskypeptide.com/', prob=90), ensure_ascii=False), encoding='utf-8')
			proc = _run_harness(base, 'save-analysis', str(proj), '--candidate', str(cand), '--consume-input', '--promote-domain')
			self.assertEqual(0, proc.returncode, f'STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
			out = json.loads(proc.stdout)
			new_proj = Path(out['domain_promotion']['project_dir']).resolve()
			self.assertEqual('1 - blueskypeptide.com', new_proj.name)
			self.assertEqual(str(new_proj), json.loads(l_turn.read_text(encoding='utf-8'))['handed_off_to']['project_root'])
if '__main__' == __name__:
	unittest.main()
