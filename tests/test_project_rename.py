# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add transactional rename-project command with automatic domain promotion":
# https://github.com/dmitry-ai/harness/issues/267
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
from git_fixture_cache import run_harness_inprocess
# @used-by :func:`_run_harness()`
def _iso_env(home: Path) -> dict[str, str]:
	return {**os.environ, 'USERPROFILE': str(home), 'HOME': str(home), 'APPDATA': str(home / 'AppData/Roaming'), 'HARNESS_TEST_NO_FSYNC': '1', 'GIT_OPTIONAL_LOCKS': '0', 'PYTHONIOENCODING': 'utf-8'}
# 2026-11-26 "Cache template Git repositories and in-process CLI helpers in slow test fixtures": https://github.com/dmitry-ai/harness/issues/355
# @used-by :func:`test_project_domain_drift._complete_review_and_prepare()`
# @used-by :func:`test_project_domain_drift._prepare_pre_finalize_with_target()`
# @used-by :meth:`ProjectRenameTests.test_rename_project_cli_and_kebab_rejection()`
# @used-by :meth:`ProjectRenameTests.test_save_and_render_analysis_promote_domain_flag()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_finalize_stage_blocks_step_gap_dangling_reservation_and_reconciliation_error()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_finalize_rejects_provisional_topic_when_target_domain_resolved()`
def _run_harness(base: Path, *args: str) -> subprocess.CompletedProcess:
	return run_harness_inprocess(args, cwd=base, env=_iso_env(base / 'home'))
# @used-by :meth:`ProjectRenameTests.test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage()`
# @used-by :meth:`ProjectRenameTests.test_rename_project_cleanup_integration()`
# @used-by :meth:`ProjectRenameTests.test_rename_project_cli_and_kebab_rejection()`
# @used-by :meth:`ProjectRenameTests.test_rename_project_rolls_back_on_collision_or_failure()`
# @used-by :meth:`ProjectRenameTests.test_rename_project_updates_folder_indexes_registrations_rules_and_journal()`
# @used-by :meth:`ProjectRenameTests.test_save_and_render_analysis_promote_domain_flag()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_check_project_allows_unidentified_low_confidence_multi_target_and_exempt()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_check_project_flags_domain_drift_on_folder_and_registration_mismatch()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_finalize_rejects_provisional_topic_when_target_domain_resolved()`
def _init_provisional(base: Path, *, job_id: str='~022124567641351805598', topic: str='Magento & GA4') -> tuple[Path, Path]:
	from agent_tools import upwork_project as up
	from test_onboarding import source
	daily = base / 'daily'
	data = {**source(job_id), 'url': f'https://upwork.com/jobs/{job_id}'}
	res = up.initialize_upwork_project(job_id, topic=topic, date_str='2026-11-23', daily_root=daily, extracted_data=data, register_native=False)
	return (Path(res['project_dir']).resolve(), daily)
# @used-by :func:`_seed_project_artifacts()`
# @used-by :func:`test_project_domain_drift._prepare_pre_finalize_with_target()`
# @used-by :meth:`ProjectRenameTests.test_save_and_render_analysis_promote_domain_flag()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_check_project_allows_unidentified_low_confidence_multi_target_and_exempt()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_check_project_flags_domain_drift_on_folder_and_registration_mismatch()`
# @used-by :meth:`test_project_rename_verification.ProjectRenameVerificationTests.test_promote_domain_updates_sibling_init_launcher()`
def _target_analysis(proj: Path, *, url: str | None='https://www.blueskypeptide.com/', prob: int=90) -> dict:
	from agent_tools.analysis import SECTIONS
	pj = json.loads((proj / '\ua616/project.json').read_text(encoding='utf-8'))
	snap = proj / pj['snapshot']
	ref = snap.relative_to(proj / '\ua616/KB').as_posix()
	title = json.loads(snap.read_text(encoding='utf-8'))['title']
	snap_sha = hashlib.sha256(snap.read_bytes()).hexdigest()
	desc = json.loads(snap.read_text(encoding='utf-8'))['description']
	claim = {'id': 'H-SITE-1', 'essence': title, 'assessment_basis': 'Corroborated target website.', 'knowledge_type': 'hypothesis', 'verification_status': 'limited', 'scope': {'description': 'Saved job title.', 'sample': [ref], 'limitations': []}, 'properties': ['content'], 'missing_checks': ['Verify private storefront admin.'], 'derived_from': [], 'materiality': 'routine', 'novelty': 'new', 'category': 'descriptive', 'impact': {'severity': 'unknown', 'basis': 'No commercial impact measured.', 'evidence_claim_ids': []}, 'probability_percent': prob, 'addresses': [], 'evidence': [{'id': 'E-SITE', 'kind': 'intake', 'source': ref, 'manifest': ref, 'source_sha256': snap_sha, 'quote': title, 'locator': {'type': 'json_pointer', 'value': '/title'}}, {'id': 'E-SITE-CON', 'kind': 'intake', 'source': ref, 'manifest': ref, 'source_sha256': snap_sha, 'quote': desc, 'locator': {'type': 'json_pointer', 'value': '/description'}}], 'for': [{'argument': 'Intake corroborates identity.', 'evidence_id': 'E-SITE'}], 'against': [{'argument': 'Description omits explicit domain URL.', 'evidence_id': 'E-SITE-CON'}]}
	return {'schema_version': 3, 'facts': [], 'identity': [claim], **{s: [] for s in SECTIONS if 'identity' != s}, 'notes': {s: 'No conclusion established.' for s in SECTIONS}, 'red_flags': [], 'websites': [{'role': 'target', 'url': url, 'basis_id': 'H-SITE-1'}]}
# @used-by :func:`_assert_renamed_registrations()`
# @used-by :func:`_seed_dual_antigravity()`
def _dual_ag_registrar(ag_dirs: dict[str, Path], folders: Path):
	from agent_tools.platforms import antigravity
	# @used-by :func:`_dual_ag_registrar()`
	def _reg(root, label, day):
		p0 = antigravity.register_antigravity_project(root, label, day, projects_dir=ag_dirs['A0'], folders_json_path=folders)
		p6 = antigravity.register_antigravity_project(root, label, day, projects_dir=ag_dirs['A6'], folders_json_path=folders, preferred_id=p0['project_id'])
		return {**p0, 'instances': {'A0': p0, 'A6': p6}}
	return _reg
# @used-by :func:`test_finalized_project_contract.seed_finalized_upwork_project()`
# @used-by :meth:`ProjectRenameTests.test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage()`
# @used-by :meth:`ProjectRenameTests.test_rename_project_cleanup_integration()`
# @used-by :meth:`ProjectRenameTests.test_rename_project_updates_folder_indexes_registrations_rules_and_journal()`
# @used-by :meth:`test_shadow_replay_command.ShadowReplayCommandTests.test_shadow_replay_exec_rename_domain_isolated_and_writes_receipt()`
def _seed_dual_antigravity(base: Path, proj: Path) -> tuple[dict[str, Path], Path, dict]:
	from agent_tools import registration
	folders = base / 'ag/folders.json'
	folders.parent.mkdir(parents=True, exist_ok=True)
	folders.write_text('{"folders":[],"projectFolderMap":{}}', encoding='utf-8')
	ag_dirs = {'A0': base / 'ag/A0/projects', 'A6': base / 'ag/A6/projects'}
	for d in ag_dirs.values():
		d.mkdir(parents=True, exist_ok=True)
	reg_fn = _dual_ag_registrar(ag_dirs, folders)
	receipt = registration.register_projects(proj, 'Magento & GA4', '2026-11-23', platform='antigravity', targets=['antigravity'], registrars={'antigravity': reg_fn})
	pfile0 = Path(receipt['project_file'])
	native0 = json.loads(pfile0.read_text(encoding='utf-8'))
	native0['settings']['custom'] = 'keep-me'
	pfile0.write_text(json.dumps(native0, ensure_ascii=False, indent=2), encoding='utf-8')
	return (ag_dirs, folders, receipt)
# @used-by :meth:`ProjectRenameTests.test_rename_project_updates_folder_indexes_registrations_rules_and_journal()`
def _seed_project_artifacts(proj: Path) -> Path:
	from agent_tools import journal
	from agent_tools.analysis import publish_analysis, save_analysis
	save_analysis(proj, _target_analysis(proj))
	publish_analysis(proj / '\ua616/KB/Analysis.json')
	jdir = proj / '\ua66e'
	journal.record_answer(jdir, ['Initial request'], 'Initial answer.  \n', 'turn-1', ['cid-0'], admission_roots=[proj, jdir])
	(proj / '\ua616/data/turns').mkdir(parents=True, exist_ok=True)
	(proj / '\ua616/data/turns/abc123.json').write_text(json.dumps({'key': 'abc123', 'project_root': str(proj), 'journal': str(jdir), 'prepared': {'response_file': str(jdir / '\u227a/1\u201320/1.md')}}, ensure_ascii=False), encoding='utf-8')
	draft_f = proj / '\ua616/data/scratch/answer-abc123.md'
	draft_f.parent.mkdir(parents=True, exist_ok=True)
	readme_posix = (proj / 'readme.md').as_posix()
	draft_f.write_text(f'Ref [readme](<file:///{readme_posix}>).  \n', encoding='utf-8')
	return journal.state_dir(jdir)
# @used-by :meth:`ProjectRenameTests.test_rename_project_updates_folder_indexes_registrations_rules_and_journal()`
def _assert_renamed_registrations(case: unittest.TestCase, new_proj: Path, ag_dirs: dict[str, Path], folders: Path, orig_pid: str, orig_fid: str) -> None:
	from agent_tools import registration
	for iid, pdir in ag_dirs.items():
		native = json.loads((pdir / f'{orig_pid}.json').read_text(encoding='utf-8'))
		case.assertEqual('blueskypeptide.com - U.P.2026.11.23', native['name'], iid)
		case.assertEqual(new_proj.as_uri(), native['projectResources']['resources'][0]['folderUri'], iid)
	case.assertEqual('keep-me', json.loads((ag_dirs['A0'] / f'{orig_pid}.json').read_text(encoding='utf-8'))['settings']['custom'])
	case.assertEqual(orig_fid, json.loads(folders.read_text(encoding='utf-8'))['projectFolderMap'][orig_pid])
	regs = json.loads((new_proj / '\ua616/data/registrations.json').read_text(encoding='utf-8'))
	case.assertTrue(regs['antigravity']['complete'])
	case.assertEqual('blueskypeptide.com - U.P.2026.11.23', regs['antigravity']['project_name'])
	case.assertEqual(orig_pid, regs['antigravity']['project_id'])
	re_reg = registration.register_projects(new_proj, platform='antigravity', targets=['antigravity'], registrars={'antigravity': _dual_ag_registrar(ag_dirs, folders)})
	case.assertTrue(re_reg['complete'], re_reg)
	case.assertEqual('registered', re_reg['status'])
# @used-by :meth:`ProjectRenameTests.test_rename_project_updates_folder_indexes_registrations_rules_and_journal()`
def _assert_renamed_journal_and_state(case: unittest.TestCase, new_proj: Path, old_sdir: Path) -> None:
	from agent_tools import admission, cli, journal, workflow
	new_jdir = new_proj / '\ua66e'
	case.assertTrue(journal.state_dir(new_jdir).is_dir())
	case.assertFalse((new_proj / '\ua616/data/.journal' / old_sdir.name).exists())
	case.assertEqual(0, cli.main('validate_step', ['--dir', str(new_jdir), '--all']))
	group = json.loads((journal.state_dir(new_jdir) / 'answer-groups/turn-1.json').read_text(encoding='utf-8'))
	ver = admission.verify(group['admission'], admission.binding(new_jdir, ['Initial request'], 'Initial answer.  \n', 'turn-1', ['cid-0']))
	case.assertEqual('verified', ver['status'])
	case.assertEqual(str(new_proj), json.loads((new_proj / '\ua616/data/turns/abc123.json').read_text(encoding='utf-8'))['project_root'])
	case.assertIn(new_proj.as_posix(), (new_proj / '\ua616/data/scratch/answer-abc123.md').read_text(encoding='utf-8'))
	chk = workflow.check_project(new_proj)
	case.assertTrue(chk['valid'], chk)
class ProjectRenameTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_rename_project_cli_and_kebab_rejection(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, daily = _init_provisional(base)
			bad = _run_harness(base, 'rename-project', str(proj), '--domain', 'magento-nextjs-ga4-reporting', '--daily-root', str(daily), '--no-register')
			self.assertEqual(2, bad.returncode, bad.stderr)
			self.assertTrue(proj.is_dir())
			ok = _run_harness(base, 'rename-project', str(proj), '--domain', 'blueskypeptide.com', '--daily-root', str(daily), '--no-register')
			self.assertEqual(0, ok.returncode, ok.stderr)
			payload = json.loads(ok.stdout)
			new_proj = Path(payload['project_dir']).resolve()
			self.assertTrue(payload['renamed'])
			self.assertEqual('1 - blueskypeptide.com', new_proj.name)
			self.assertFalse(proj.exists())
			self.assertTrue(new_proj.is_dir())
	# @used-by :mod:`unittest`
	def test_rename_project_rolls_back_on_collision_or_failure(self) -> None:
		from agent_tools.project_rename import rename_project
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, daily = _init_provisional(base)
			collision = proj.parent / '1 - blueskypeptide.com'
			collision.mkdir()
			with self.assertRaises(FileExistsError):
				rename_project(proj, domain='blueskypeptide.com', daily_root=daily, register_native=False)
			self.assertTrue(proj.is_dir())
			collision.rmdir()
			with patch('agent_tools.project_rename._update_projects_index', side_effect=OSError('disk write failed')):
				with self.assertRaises(OSError):
					rename_project(proj, domain='blueskypeptide.com', daily_root=daily, register_native=False)
			self.assertTrue(proj.is_dir())
			self.assertFalse((proj.parent / '1 - blueskypeptide.com').exists())
	# @used-by :mod:`unittest`
	def test_rename_project_updates_folder_indexes_registrations_rules_and_journal(self) -> None:
		from agent_tools.project_rename import rename_project
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, daily = _init_provisional(base)
			ag_dirs, folders, initial_reg = _seed_dual_antigravity(base, proj)
			old_sdir = _seed_project_artifacts(proj)
			res = rename_project(proj, domain='blueskypeptide.com', daily_root=daily, antigravity_projects_dirs=ag_dirs, antigravity_folders_json=folders, targets=['antigravity'])
			new_proj = Path(res['project_dir']).resolve()
			self.assertEqual('1 - blueskypeptide.com', new_proj.name)
			self.assertFalse(proj.exists())
			self.assertEqual('2026/11/23/1 - blueskypeptide.com', json.loads((daily / '\ua616/data/projects.json').read_text(encoding='utf-8'))['~022124567641351805598'])
			state = json.loads((new_proj / '\ua616/project.json').read_text(encoding='utf-8'))
			self.assertEqual(('blueskypeptide.com', 'domain'), (state['label'], state['label_kind']))
			self.assertIn('`blueskypeptide.com`', (new_proj / '.agents/rules/90-project.md').read_text(encoding='utf-8'))
			_assert_renamed_registrations(self, new_proj, ag_dirs, folders, initial_reg['project_id'], initial_reg['folder_id'])
			_assert_renamed_journal_and_state(self, new_proj, old_sdir)
	# @used-by :mod:`unittest`
	def test_save_and_render_analysis_promote_domain_flag(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj1, _ = _init_provisional(base, job_id='~022124567641351805591')
			cand1 = proj1 / '\ua616/data/scratch/cand1.json'
			cand1.parent.mkdir(parents=True, exist_ok=True)
			cand1.write_text(json.dumps(_target_analysis(proj1, url='https://www.blueskypeptide.com/', prob=90), ensure_ascii=False), encoding='utf-8')
			p1 = _run_harness(base, 'save-analysis', str(proj1), '--candidate', str(cand1), '--consume-input', '--promote-domain')
			self.assertEqual(0, p1.returncode, p1.stderr)
			out1 = json.loads(p1.stdout)
			self.assertTrue((out1.get('domain_promotion') or {}).get('renamed'), out1)
			self.assertEqual('1 - blueskypeptide.com', Path(out1['domain_promotion']['project_dir']).name)
			proj2, _ = _init_provisional(base, job_id='~022124567641351805592')
			cand2 = proj2 / '\ua616/data/scratch/cand2.json'
			cand2.parent.mkdir(parents=True, exist_ok=True)
			cand2.write_text(json.dumps(_target_analysis(proj2, url='https://www.example.org/', prob=85), ensure_ascii=False), encoding='utf-8')
			self.assertEqual(0, _run_harness(base, 'save-analysis', str(proj2), '--candidate', str(cand2), '--consume-input').returncode)
			p2 = _run_harness(base, 'render-analysis', str(proj2 / '\ua616/KB/Analysis.json'), '--promote-domain')
			self.assertEqual(0, p2.returncode, p2.stderr)
			out2 = json.loads(p2.stdout)
			self.assertTrue((out2.get('domain_promotion') or {}).get('renamed'), out2)
			self.assertEqual('2 - example.org', Path(out2['domain_promotion']['project_dir']).name)
			proj3, _ = _init_provisional(base, job_id='~022124567641351805593')
			cand3 = proj3 / '\ua616/data/scratch/cand3.json'
			cand3.parent.mkdir(parents=True, exist_ok=True)
			cand3.write_text(json.dumps(_target_analysis(proj3, url='https://www.lowscore.org/', prob=60), ensure_ascii=False), encoding='utf-8')
			p3 = _run_harness(base, 'save-analysis', str(proj3), '--candidate', str(cand3), '--consume-input', '--promote-domain')
			self.assertEqual(0, p3.returncode, p3.stderr)
			self.assertTrue(proj3.is_dir())
	# 2026-11-26 "Preserve finalized workflow and review lineage across rename-project": https://github.com/dmitry-ai/harness/issues/277
	# @used-by :mod:`unittest`
	def test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage(self) -> None:
		from agent_tools import path_registry, workflow
		from agent_tools.platforms.trace_common import reviewer_isolation_issues
		from agent_tools.project_rename import rename_project
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, daily = _init_provisional(base)
			ag_dirs, folders, _ = _seed_dual_antigravity(base, proj)
			reg_f = proj / '\ua616/data/registrations.json'
			reg_sha_before = hashlib.sha256(reg_f.read_bytes()).hexdigest()
			pj_sha_before = hashlib.sha256((proj / '\ua616/project.json').read_bytes()).hexdigest()
			wf_f = proj / '\ua616/data/workflow.json'
			wf_f.parent.mkdir(parents=True, exist_ok=True)
			wf_f.write_text(json.dumps({'schema_version': 1, 'project_root': str(proj), 'job_id': '~022124567641351805598', 'stages': {'identity_init': {'status': 'complete', 'inputs': {'\ua616/project.json': pj_sha_before}, 'outputs': {'\ua616/data/registrations.json': reg_sha_before}}}, 'questions': {}, 'reviews': [], 'requests': [], 'events': []}), encoding='utf-8')
			launcher = base / 'launcher'
			l_turn = launcher / '\ua616/data/turns/handoff01.json'
			l_turn.parent.mkdir(parents=True, exist_ok=True)
			l_turn.write_text(json.dumps({'key': 'handoff01', 'status': 'handed_off', 'handed_off_to': {'project_root': str(proj), 'job_id': '~022124567641351805598'}}), encoding='utf-8')
			res = rename_project(proj, domain='blueskypeptide.com', daily_root=daily, antigravity_projects_dirs=ag_dirs, antigravity_folders_json=folders, targets=['antigravity'], launcher_root=launcher)
			new_proj = Path(res['project_dir']).resolve()
			self.assertEqual(str(new_proj), json.loads(l_turn.read_text(encoding='utf-8'))['handed_off_to']['project_root'])
			wf_after = json.loads((new_proj / '\ua616/data/workflow.json').read_text(encoding='utf-8'))
			reg_sha_after = hashlib.sha256((new_proj / '\ua616/data/registrations.json').read_bytes()).hexdigest()
			self.assertEqual(reg_sha_after, wf_after['stages']['identity_init']['outputs']['\ua616/data/registrations.json'])
			self.assertTrue(workflow.WorkflowStateEngine(new_proj).receipt_current(wf_after['stages']['identity_init']))
			self.assertTrue(path_registry.same_project_root(str(proj), new_proj))
			sibling = proj.parent / '2 - other-client.com'
			self.assertFalse(path_registry.same_project_root(str(sibling), new_proj))
			rows_old = [{'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': str(proj / '\ua616/KB/Analysis.json')}}]}]
			self.assertEqual([], reviewer_isolation_issues(new_proj, rows_old))
			rows_sib = [{'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'read_file', 'args': {'Path': str(sibling / '\ua616/KB/Analysis.json')}}]}]
			self.assertTrue(any(('sibling project path' in msg for msg in reviewer_isolation_issues(new_proj, rows_sib))))
	# 2026-11-26
	# "Add cross-subsystem integration tests for upwork-cleanup lifecycle and audit":
	# https://github.com/dmitry-ai/harness/issues/309
	# @used-by :mod:`unittest`
	def test_rename_project_cleanup_integration(self) -> None:
		from copy import deepcopy
		from datetime import datetime, timedelta, timezone
		import sqlite3
		from agent_tools import cleanup, runtime
		from agent_tools.project_rename import rename_project
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			proj, daily = _init_provisional(base)
			ag_dirs, folders, init_reg = _seed_dual_antigravity(base, proj)
			now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
			pj_f = proj / '\ua616/project.json'
			pj = json.loads(pj_f.read_text(encoding='utf-8'))
			pj['created_at'] = (now - timedelta(hours=120)).isoformat()
			pj_f.write_text(json.dumps(pj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
			res = rename_project(proj, domain='blueskypeptide.com', daily_root=daily, antigravity_projects_dirs=ag_dirs, antigravity_folders_json=folders, targets=['antigravity'])
			new_proj = Path(res['project_dir']).resolve()
			new_pj_f = new_proj / '\ua616/project.json'
			new_pj = json.loads(new_pj_f.read_text(encoding='utf-8'))
			new_pj['renamed_from'][-1]['at'] = (now - timedelta(hours=1)).isoformat()
			new_pj_f.write_text(json.dumps(new_pj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
			backend = base / 'ag/backend'
			backend.mkdir(parents=True, exist_ok=True)
			conn = sqlite3.connect(backend / 'conversation_summaries.db')
			conn.execute('CREATE TABLE conversation_summaries (project_id TEXT, workspace_uris TEXT)')
			conn.commit()
			conn.close()
			cfg = deepcopy(runtime.settings())
			cfg['workspace_root'] = str(base)
			cfg['daily_root'] = 'daily'
			cfg['platforms']['antigravity']['folders_json'] = str(folders)
			cfg['platforms']['codex']['instances'] = {}
			cln = cleanup.cleanup_projects(apply=True, daily_root=daily, now=now, config=cfg, ag_directory=ag_dirs['A0'], ag_backend=backend, folders=folders)
			self.assertTrue(cln['complete'], cln)
			self.assertEqual('recent', cln['projects'][0]['status'])
			self.assertEqual('project.renamed_from', cln['projects'][0]['age_basis'])
			self.assertTrue((ag_dirs['A0'] / f"{init_reg['project_id']}.json").exists())
if '__main__' == __name__:
	unittest.main()
