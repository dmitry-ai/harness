# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add reusable finalized Upwork project fixture and lifecycle contract tests":
# https://github.com/dmitry-ai/harness/issues/293
from __future__ import annotations
from contextlib import nullcontext
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
_SEVEN_STAGES = ('capture', 'identity_init', 'research', 'analysis', 'review', 'kb_review', 'finalize')
# @used-by :func:`_run_harness()`
def _iso_env(home: Path) -> dict[str, str]:
	return {**os.environ, 'USERPROFILE': str(home), 'HOME': str(home), 'APPDATA': str(home / 'AppData/Roaming'), 'HARNESS_TEST_NO_FSYNC': '1', 'GIT_OPTIONAL_LOCKS': '0', 'PYTHONIOENCODING': 'utf-8'}
# @used-by :meth:`FinalizedProjectContractTests.test_render_analysis_promote_domain_preserves_finalized_invariants()`, :meth:`FinalizedProjectContractTests.test_shadow_replay_exec_rename_domain_passes_on_finalized_fixture_with_zero_mutation()`
def _run_harness(base: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run([sys.executable, str(HARNESS_PY), *args], cwd=str(base), env=_iso_env(base / 'home'), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=90, check=False)
# @used-by :meth:`FinalizedProjectContractTests.test_rename_rolls_back_finalized_fixture_on_review_authorize_regression()`, :meth:`FinalizedProjectContractTests.test_shadow_replay_exec_rename_domain_passes_on_finalized_fixture_with_zero_mutation()`
def _snapshot_tree(root: Path) -> dict[str, str]:
	return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and (not p.name.endswith('.lock'))}
# @used-by :func:`_seed_pre_review()`
def _build_fixture_analysis(proj: Path, domain_in_analysis: str | None) -> dict:
	from test_upwork_init_e2e import _significant_analysis
	val = _significant_analysis(proj)
	if domain_in_analysis:
		val['websites'] = [{'role': 'target', 'url': f'https://www.{domain_in_analysis}/', 'basis_id': 'F-TITLE'}]
	return val
# @used-by :func:`seed_finalized_upwork_project()`
def _seed_pre_review(proj: Path, backend: Path, launcher: Path, job_id: str, *, with_reg: bool, domain_in_analysis: str | None) -> tuple[str, list[dict], Path, str]:
	from agent_tools import completion, workflow
	from agent_tools.analysis import publish_analysis, save_analysis
	from test_upwork_init_e2e import PARENT_CID, _upsert_summary, _wire, _write_steps_db, _write_transcript
	req1 = f'/upwork-init https://upwork.com/jobs/{job_id}'
	parent_rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': req1, 'created_at': '2026-11-23T10:00:00Z'}]
	_write_transcript(backend, PARENT_CID, parent_rows)
	_upsert_summary(backend, PARENT_CID, '', [launcher.as_uri()], 'CASCADE_RUN_STATUS_RUNNING', 0, 'primary')
	_write_steps_db(backend, PARENT_CID, [(0, 14, 3, _wire(19, _wire(2, req1.encode('utf-8'))))])
	beg = completion.begin(proj, PARENT_CID, platform='antigravity', backend=backend)
	workflow.adopt_requests(proj, PARENT_CID, platform='antigravity', backend=backend)
	workflow.resume(proj, 'verify_saved_capture')
	(proj / '\ua616/KB/Evidence/research-report.json').write_text('{}\n', encoding='utf-8')
	id_out = ['\ua616/data/registrations.json'] if with_reg else ['\ua616/project.json']
	workflow.complete_stage(proj, 'identity_init', ['\ua616/project.json'], id_out)
	workflow.complete_stage(proj, 'research', ['\ua616/project.json'], ['\ua616/KB/Evidence/research-report.json'])
	save_analysis(proj, _build_fixture_analysis(proj, domain_in_analysis))
	publish_analysis(proj / '\ua616/KB/Analysis.json')
	workflow.complete_stage(proj, 'analysis', ['\ua616/project.json'], ['\ua616/KB/Analysis.json', '\ua616/KB/Analysis.md'])
	ev_bin = proj / '\ua616/KB/Evidence/HTTP/fx/response.bin'
	ev_bin.parent.mkdir(parents=True, exist_ok=True)
	ev_bin.write_bytes(b'ok')
	reply1 = f'\u0417\u0430\u0434\u0430\u0447\u0430 \u043a\u043b\u0438\u0435\u043d\u0442\u0430 Client task \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0430 \u043f\u043e [response.bin](<file:///{ev_bin.resolve().as_posix()}>).  \n'
	cand_md = proj / f"\ua616/data/scratch/answer-{beg['turn_key']}.md"
	cand_md.parent.mkdir(parents=True, exist_ok=True)
	cand_md.write_text(reply1, encoding='utf-8')
	return (req1, parent_rows, cand_md, reply1)
# @used-by :func:`seed_finalized_upwork_project()`
def _complete_review_and_finalize(proj: Path, backend: Path, req1: str, parent_rows: list[dict], cand_md: Path, reply1: str, *, allow_drift_finalize: bool) -> list[dict]:
	from agent_tools import completion, metrics, review, workflow
	from test_upwork_init_e2e import CHILD_CID, PARENT_CID, _wire, _write_falsifier_auditor, _write_steps_db
	spec = {'risk': 'significant', 'basis': 'Significant analysis requiring falsifier audit.', 'request_scope': 'Answer initial request.', 'claim_ids': ['F-TITLE'], 'claims': [{'claim_id': 'F-TITLE', 'response_excerpt': 'Client task', 'novelty': 'new'}], 'task_flags': ['material_analysis', 'new_causal_analysis']}
	pkg = review.prepare(proj, PARENT_CID, spec, reply1)
	rep_f = _write_falsifier_auditor(backend, proj, pkg, cand_md, parent_rows)
	_write_steps_db(backend, PARENT_CID, [(0, 14, 3, _wire(19, _wire(2, req1.encode('utf-8')))), (2, 15, 3, None)])
	proof = metrics.native_review_proof(proj, PARENT_CID, CHILD_CID, backend=backend, platform='antigravity')
	review.record(proj, rep_f, parent_id=PARENT_CID, reviewer_id=CHILD_CID, native_evidence=proof['proof'])
	rev_out = workflow.load(proj)['reviews'][-1]['report']
	workflow.complete_stage(proj, 'review', ['\ua616/KB/Analysis.json'], [rev_out])
	kb_inputs = [p.relative_to(proj).as_posix() for p in sorted((proj / '\ua616/KB').glob('*')) if p.is_file() and 'Progress.md' != p.name]
	workflow.complete_stage(proj, 'kb_review', kb_inputs, ['\ua616/KB/Analysis.md'], note='KB consistent')
	prep = completion.prepare(proj, reply1, conversation=PARENT_CID, platform='antigravity', backend=backend)
	cand_md.unlink(missing_ok=True)
	rep_f.unlink(missing_ok=True)
	reply_rel = Path(prep['response_file']).resolve().relative_to(proj).as_posix()
	workflow.complete_stage(proj, 'finalize', ['\ua616/KB/Analysis.json'], [reply_rel])
	child_tx = backend / 'brain' / CHILD_CID / '.system_generated/logs/transcript_full.jsonl'
	return [json.loads(ln) for ln in child_tx.read_text(encoding='utf-8').splitlines() if ln.strip()]
# @used-by :class:`FinalizedProjectContractTests`
def seed_finalized_upwork_project(base: Path, *, topic: str='Magento & GA4', job_id: str='~022124567641351805598', with_reg: bool=True, domain_in_analysis: str | None=None) -> dict:
	from agent_tools import upwork_project as up
	from test_onboarding import source
	from test_project_rename import _seed_dual_antigravity
	daily = base / 'proposals/daily'
	launcher = base / 'proposals/init'
	backend = base / 'home/.gemini/antigravity'
	drift_ctx = patch('agent_tools.project_drift.domain_drift_issues', return_value=[]) if domain_in_analysis else nullcontext()
	with patch.dict(os.environ, _iso_env(base / 'home')), drift_ctx:
		data = {**source(job_id), 'url': f'https://upwork.com/jobs/{job_id}'}
		init_res = up.initialize_upwork_project(job_id, topic=topic, date_str='2026-11-23', daily_root=daily, extracted_data=data, register_native=False)
		proj = Path(init_res['project_dir']).resolve()
		l_turn = launcher / '\ua616/data/turns/handoff01.json'
		l_turn.parent.mkdir(parents=True, exist_ok=True)
		l_turn.write_text(json.dumps({'key': 'handoff01', 'status': 'handed_off', 'handed_off_to': {'project_root': str(proj), 'job_id': job_id}}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
		ag_dirs, folders, initial_reg = _seed_dual_antigravity(base, proj) if with_reg else (None, None, None)
		req1, parent_rows, cand_md, reply1 = _seed_pre_review(proj, backend, launcher, job_id, with_reg=with_reg, domain_in_analysis=domain_in_analysis)
		reviewer_rows = _complete_review_and_finalize(proj, backend, req1, parent_rows, cand_md, reply1, allow_drift_finalize=bool(domain_in_analysis))
	return {'project': proj, 'daily': daily, 'launcher': launcher, 'launcher_turn': l_turn, 'backend': backend, 'ag_dirs': ag_dirs, 'folders_json': folders, 'initial_reg': initial_reg, 'reviewer_rows': reviewer_rows, 'job_id': job_id}
# @used-by :mod:`unittest`
class FinalizedProjectContractTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage(self) -> None:
		from agent_tools import cli, review, upwork_project as up, workflow
		from agent_tools.platforms.trace_common import reviewer_isolation_issues
		from agent_tools.project_rename import rename_project
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			fx = seed_finalized_upwork_project(base)
			proj = fx['project']
			with patch.dict(os.environ, _iso_env(base / 'home')):
				res = rename_project(proj, domain='blueskypeptide.com', antigravity_projects_dirs=fx['ag_dirs'], antigravity_folders_json=fx['folders_json'], targets=['antigravity'])
				self.assertTrue(res['valid'], res)
				self.assertTrue(res['renamed'], res)
				self.assertTrue((res.get('post_verification') or {}).get('valid'), res)
				new_proj = Path(res['project_dir']).resolve()
				self.assertEqual('1 - blueskypeptide.com', new_proj.name)
				wf_after = workflow.load(new_proj)
				stages = workflow.stage_statuses(new_proj, wf_after)
				for name in _SEVEN_STAGES:
					self.assertEqual('complete', stages.get(name), stages)
				self.assertTrue(bool(review.authorize(new_proj, wf_after)['review_ids']))
				self.assertTrue(up.check_configuration(new_proj)['valid'])
				self.assertEqual(0, cli.main('validate_step', ['--dir', str(new_proj / '\ua66e'), '--all', '--strict-sequence']))
				self.assertTrue(workflow.check_project(new_proj)['valid'])
				self.assertEqual(str(new_proj), json.loads(fx['launcher_turn'].read_text(encoding='utf-8'))['handed_off_to']['project_root'])
				self.assertEqual([], reviewer_isolation_issues(new_proj, fx['reviewer_rows']))
	# @used-by :mod:`unittest`
	def test_render_analysis_promote_domain_preserves_finalized_invariants(self) -> None:
		from agent_tools import workflow
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			fx = seed_finalized_upwork_project(base, job_id='~022124567641351805594', with_reg=False, domain_in_analysis='blueskypeptide.com')
			proj = fx['project']
			proc = _run_harness(base, 'render-analysis', str(proj / '\ua616/KB/Analysis.json'), '--promote-domain')
			self.assertEqual(0, proc.returncode, f'STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
			out = json.loads(proc.stdout)
			new_proj = Path(out['domain_promotion']['project_dir']).resolve()
			self.assertEqual('1 - blueskypeptide.com', new_proj.name)
			self.assertEqual(str(new_proj), json.loads(fx['launcher_turn'].read_text(encoding='utf-8'))['handed_off_to']['project_root'])
			with patch.dict(os.environ, _iso_env(base / 'home')):
				self.assertEqual('complete', workflow.stage_statuses(new_proj, workflow.load(new_proj)).get('finalize'))
	# @used-by :mod:`unittest`
	def test_shadow_replay_exec_rename_domain_passes_on_finalized_fixture_with_zero_mutation(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			fx = seed_finalized_upwork_project(base)
			proj, launcher = (fx['project'], fx['launcher'])
			ws = base / 'workspace'
			(ws / '\ua616/data/scratch').mkdir(parents=True)
			(ws / '\ua616/paths.json').write_text('{"version": 1}\n', encoding='utf-8')
			proj_before, launcher_before, ag_before = (_snapshot_tree(proj), _snapshot_tree(launcher), _snapshot_tree(base / 'ag'))
			proc = _run_harness(base, 'shadow-replay', str(proj), '--exec-rename-domain', 'blueskypeptide.com', '--workspace', str(ws))
			self.assertEqual(0, proc.returncode, f'STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}')
			res = json.loads(proc.stdout)
			self.assertTrue(res['valid'], res)
			self.assertIn('command_exec', res['stages_verified'])
			self.assertIn('post_rename_verify', res['stages_verified'])
			self.assertEqual(proj_before, _snapshot_tree(proj))
			self.assertEqual(launcher_before, _snapshot_tree(launcher))
			self.assertEqual(ag_before, _snapshot_tree(base / 'ag'))
	# @used-by :mod:`unittest`
	def test_rename_rolls_back_finalized_fixture_on_review_authorize_regression(self) -> None:
		from agent_tools.project_rename import rename_project
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			fx = seed_finalized_upwork_project(base)
			proj, launcher = (fx['project'], fx['launcher'])
			proj_before, launcher_before, ag_before = (_snapshot_tree(proj), _snapshot_tree(launcher), _snapshot_tree(base / 'ag'))
			def _fake_auth(root, _state, **_kw):
				if 'blueskypeptide.com' in Path(root).name:
					raise ValueError('simulated post-rename review regression')
				return {'authorized': True}
			with patch.dict(os.environ, _iso_env(base / 'home')), patch('agent_tools.review.authorize', side_effect=_fake_auth):
				res = rename_project(proj, domain='blueskypeptide.com', antigravity_projects_dirs=fx['ag_dirs'], antigravity_folders_json=fx['folders_json'], targets=['antigravity'])
			self.assertFalse(res['valid'], res)
			self.assertTrue(res.get('rolled_back'), res)
			self.assertTrue(proj.is_dir())
			self.assertEqual(proj_before, _snapshot_tree(proj))
			self.assertEqual(launcher_before, _snapshot_tree(launcher))
			self.assertEqual(ag_before, _snapshot_tree(base / 'ag'))
__all__ = ['FinalizedProjectContractTests', 'seed_finalized_upwork_project']
if '__main__' == __name__:
	unittest.main()