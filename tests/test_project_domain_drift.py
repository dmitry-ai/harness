# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce project.domain_drift invariant in check-project and finalize":
# https://github.com/dmitry-ai/harness/issues/268
from __future__ import annotations
from pathlib import Path
import json
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for p in (SCRIPTS, TESTS):
	if str(p) not in sys.path:
		sys.path.insert(0, str(p))
from test_project_rename import _init_provisional, _run_harness, _target_analysis
from test_upwork_init_e2e import _upsert_summary, _wire, _write_falsifier_auditor, _write_steps_db, _write_transcript
CID = '44444444-5555-4666-8777-888888888881'
CHILD = '44444444-5555-4666-8777-888888888882'
JOB_ID = '~022124567641351805598'
# @used-by :func:`_prepare_pre_finalize_with_target()`
# @used-by :meth:`ProjectDomainDriftTests.test_check_project_allows_unidentified_low_confidence_multi_target_and_exempt()`
# @used-by :meth:`ProjectDomainDriftTests.test_check_project_flags_domain_drift_on_folder_and_registration_mismatch()`
def _save_and_publish(proj: Path, analysis_val: dict) -> None:
	from agent_tools.analysis import publish_analysis, save_analysis
	save_analysis(proj, analysis_val)
	publish_analysis(proj / '\ua616/KB/Analysis.json')
# @used-by :meth:`ProjectDomainDriftTests.test_finalize_rejects_provisional_topic_when_target_domain_resolved()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_finalize_stage_blocks_step_gap_dangling_reservation_and_reconciliation_error()`
def _prepare_pre_finalize_with_target(base: Path, proj: Path) -> tuple[Path, Path]:
	backend = base / 'home/.gemini/antigravity'
	req1 = f'/upwork-init https://upwork.com/jobs/{JOB_ID}'
	rows = [{'step_index': 0, 'type': 'USER_INPUT', 'content': req1, 'created_at': '2026-11-25T10:00:00Z'}]
	_write_transcript(backend, CID, rows)
	_upsert_summary(backend, CID, '', [proj.as_uri()], 'CASCADE_RUN_STATUS_RUNNING', 0, 'primary')
	_write_steps_db(backend, CID, [(0, 14, 3, _wire(19, _wire(2, req1.encode('utf-8'))))])
	_run_harness(base, 'turn-begin', str(proj), '--conversation', CID, '--platform', 'antigravity')
	_run_harness(base, 'adopt-requests', str(proj), '--conversation', CID, '--platform', 'antigravity')
	_run_harness(base, 'resume', str(proj), '--reason', 'verify_saved_capture')
	(proj / '\ua616/KB/Evidence/init-check.json').write_text('{}', encoding='utf-8')
	(proj / '\ua616/KB/Evidence/research-report.json').write_text('{}', encoding='utf-8')
	_run_harness(base, 'stage', str(proj), 'identity_init', '--input', '\ua616/project.json', '--output', '\ua616/KB/Evidence/init-check.json')
	_run_harness(base, 'stage', str(proj), 'research', '--input', '\ua616/project.json', '--output', '\ua616/KB/Evidence/research-report.json')
	_save_and_publish(proj, _target_analysis(proj, url='https://www.blueskypeptide.com/', prob=90))
	return (backend, rows)
# @used-by :meth:`ProjectDomainDriftTests.test_finalize_rejects_provisional_topic_when_target_domain_resolved()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_finalize_stage_blocks_step_gap_dangling_reservation_and_reconciliation_error()`
def _complete_review_and_prepare(base: Path, proj: Path, backend: Path, rows: list[dict]) -> tuple[Path, str]:
	import test_upwork_init_e2e as e2e
	ev_bin = proj / '\ua616/KB/Evidence/HTTP/e2e/response.bin'
	ev_bin.parent.mkdir(parents=True, exist_ok=True)
	ev_bin.write_bytes(b'ok')
	ev_posix = ev_bin.resolve().as_posix()
	reply = f'\u0417\u0430\u0434\u0430\u0447\u0430 \u043a\u043b\u0438\u0435\u043d\u0442\u0430 Client task \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0430 \u043f\u043e [response.bin](<file:///{ev_posix}>).  \n'
	cand_md = proj / '\ua616/data/scratch/answer-drift.md'
	cand_md.parent.mkdir(parents=True, exist_ok=True)
	cand_md.write_text(reply, encoding='utf-8')
	spec_f = proj / '\ua616/data/scratch/review-spec.json'
	spec_f.write_text(json.dumps({'risk': 'significant', 'basis': 'Significant analysis.', 'request_scope': 'Initial analysis.', 'claim_ids': ['H-SITE-1'], 'claims': [{'claim_id': 'H-SITE-1', 'response_excerpt': 'Client task', 'novelty': 'new'}], 'task_flags': ['material_analysis', 'new_causal_analysis']}), encoding='utf-8')
	pkg = json.loads(_run_harness(base, 'prepare-review', str(proj), '--parent', CID, '--spec', str(spec_f), '--response-file', str(cand_md), '--consume-input', '--platform', 'antigravity').stdout)
	cand_md.write_text(reply, encoding='utf-8')
	orig_p, orig_c = (e2e.PARENT_CID, e2e.CHILD_CID)
	e2e.PARENT_CID, e2e.CHILD_CID = (CID, CHILD)
	try:
		rep_f = _write_falsifier_auditor(backend, proj, pkg, cand_md, rows)
	finally:
		e2e.PARENT_CID, e2e.CHILD_CID = (orig_p, orig_c)
	req1 = f'/upwork-init https://upwork.com/jobs/{JOB_ID}'
	_write_steps_db(backend, CID, [(0, 14, 3, _wire(19, _wire(2, req1.encode('utf-8')))), (2, 15, 3, None)])
	proof = json.loads(_run_harness(base, 'native-review-proof', str(proj), '--parent', CID, '--reviewer', CHILD, '--platform', 'antigravity').stdout)
	rec_proc = _run_harness(base, 'record-review', str(proj), '--parent', CID, '--reviewer', CHILD, '--report', str(rep_f), '--native-evidence', proof['proof'], '--consume-input', '--platform', 'antigravity')
	if 0 != rec_proc.returncode:
		raise AssertionError(f'record-review failed: {rec_proc.stdout}\n{rec_proc.stderr}')
	rec = json.loads(rec_proc.stdout)
	review_out = rec['reviews'][-1]['report'] if isinstance(rec.get('reviews'), list) and rec['reviews'] else proof['proof']
	return (cand_md, review_out)
class ProjectDomainDriftTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_check_project_allows_unidentified_low_confidence_multi_target_and_exempt(self) -> None:
		from agent_tools import workflow
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj1, _ = _init_provisional(base, job_id='~022124567641351805511')
			a1 = _target_analysis(proj1, url=None, prob=90)
			a1['red_flags'] = [{'id': 'RF-WEBSITE-UNIDENTIFIED', 'status': 'unresolved', 'summary': 'Unidentified site.', 'basis_ids': ['H-SITE-1']}]
			_save_and_publish(proj1, a1)
			self.assertTrue(workflow.check_project(proj1)['valid'])
			proj2, _ = _init_provisional(base, job_id='~022124567641351805512')
			_save_and_publish(proj2, _target_analysis(proj2, url='https://www.blueskypeptide.com/', prob=70))
			self.assertTrue(workflow.check_project(proj2)['valid'])
			proj3, _ = _init_provisional(base, job_id='~022124567641351805513')
			a3 = _target_analysis(proj3, url='https://alpha.example.org/', prob=90)
			a3['websites'].append({'role': 'target', 'url': 'https://beta.example.org/', 'basis_id': 'H-SITE-1'})
			_save_and_publish(proj3, a3)
			self.assertTrue(workflow.check_project(proj3)['valid'])
			proj4, _ = _init_provisional(base, job_id='~022124567641351805514')
			_save_and_publish(proj4, _target_analysis(proj4, url='https://www.blueskypeptide.com/', prob=90))
			pj_f = proj4 / '\ua616/project.json'
			pj = json.loads(pj_f.read_text(encoding='utf-8'))
			pj['domain_drift_exempt'] = {'reason': 'Explicit multi-brand portfolio exception.'}
			pj_f.write_text(json.dumps(pj), encoding='utf-8')
			self.assertTrue(workflow.check_project(proj4)['valid'])
	# @used-by :mod:`unittest`
	def test_check_project_flags_domain_drift_on_folder_and_registration_mismatch(self) -> None:
		from agent_tools import workflow
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, _ = _init_provisional(base)
			_save_and_publish(proj, _target_analysis(proj, url='https://www.blueskypeptide.com/', prob=90))
			chk = workflow.check_project(proj)
			self.assertFalse(chk['valid'])
			drift = [i for i in chk['issues'] if 'project.domain_drift' == i.get('code')]
			self.assertEqual(1, len(drift), chk)
			self.assertIn('rename-project', drift[0]['message'])
			self.assertIn('blueskypeptide.com', drift[0]['message'])
			from agent_tools.project_rename import rename_project
			renamed = Path(rename_project(proj, domain='blueskypeptide.com', register_native=False)['project_dir'])
			self.assertTrue(workflow.check_project(renamed)['valid'])
			regs_f = renamed / '\ua616/data/registrations.json'
			regs_f.write_text(json.dumps({'antigravity': {'complete': True, 'status': 'registered', 'project_name': 'magento-nextjs-ga4-reporting - U.P.2026.11.23'}}), encoding='utf-8')
			chk_reg = workflow.check_project(renamed)
			self.assertFalse(chk_reg['valid'])
			self.assertIn('project.domain_drift', {i['code'] for i in chk_reg['issues']})
	# @used-by :mod:`unittest`
	def test_finalize_rejects_provisional_topic_when_target_domain_resolved(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, daily = _init_provisional(base, job_id=JOB_ID, topic='Magento & GA4')
			backend, rows = _prepare_pre_finalize_with_target(base, proj)
			chk_before = json.loads(_run_harness(base, 'check-project', str(proj)).stdout)
			self.assertFalse(chk_before['valid'])
			self.assertIn('project.domain_drift', {i['code'] for i in chk_before['issues']})
			bad_analysis = _run_harness(base, 'stage', str(proj), 'analysis', '--input', '\ua616/project.json', '--output', '\ua616/KB/Analysis.json', '--output', '\ua616/KB/Analysis.md')
			self.assertNotEqual(0, bad_analysis.returncode)
			ren = _run_harness(base, 'rename-project', str(proj), '--domain', 'blueskypeptide.com', '--daily-root', str(daily), '--no-register')
			self.assertEqual(0, ren.returncode, ren.stderr)
			new_proj = Path(json.loads(ren.stdout)['project_dir']).resolve()
			self.assertEqual('1 - blueskypeptide.com', new_proj.name)
			_upsert_summary(backend, CID, '', [new_proj.as_uri()], 'CASCADE_RUN_STATUS_RUNNING', 0, 'primary')
			self.assertEqual(0, _run_harness(base, 'stage', str(new_proj), 'analysis', '--input', '\ua616/project.json', '--output', '\ua616/KB/Analysis.json', '--output', '\ua616/KB/Analysis.md').returncode)
			cand_md, review_out = _complete_review_and_prepare(base, new_proj, backend, rows)
			kb_args = [tok for p in sorted((new_proj / '\ua616/KB').glob('*')) if p.is_file() and 'Progress.md' != p.name for tok in ('--input', p.relative_to(new_proj).as_posix())]
			self.assertEqual(0, _run_harness(base, 'stage', str(new_proj), 'review', '--input', '\ua616/KB/Analysis.json', '--output', review_out).returncode)
			self.assertEqual(0, _run_harness(base, 'stage', str(new_proj), 'kb_review', *kb_args, '--output', '\ua616/KB/Analysis.md', '--note', 'KB consistent').returncode)
			prep = _run_harness(base, 'answer-prepare', str(new_proj), '--conversation', CID, '--response-file', str(cand_md), '--consume-input', '--platform', 'antigravity')
			self.assertEqual(0, prep.returncode, prep.stdout + prep.stderr)
			regs_f = new_proj / '\ua616/data/registrations.json'
			regs_f.write_text(json.dumps({'antigravity': {'complete': True, 'status': 'registered', 'project_name': 'Magento & GA4 - U.P.2026.11.23'}}), encoding='utf-8')
			bad_fin = _run_harness(base, 'stage', str(new_proj), 'finalize', *kb_args, '--output', '\ua66e/\u227a/1\u201320/1.md')
			self.assertNotEqual(0, bad_fin.returncode)
			self.assertIn('blueskypeptide.com', bad_fin.stdout + bad_fin.stderr)
			regs_f.write_text(json.dumps({'antigravity': {'complete': True, 'status': 'registered', 'project_name': 'blueskypeptide.com - U.P.2026.11.23'}}), encoding='utf-8')
			fin = _run_harness(base, 'stage', str(new_proj), 'finalize', *kb_args, '--output', '\ua66e/\u227a/1\u201320/1.md')
			self.assertEqual(0, fin.returncode, fin.stdout + fin.stderr)
			self.assertEqual('complete', json.loads(fin.stdout)['stages']['finalize'])
if '__main__' == __name__:
	unittest.main()
