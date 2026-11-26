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
def _iso_env(home: Path) -> dict[str, str]:
	return {**os.environ, 'USERPROFILE': str(home), 'HOME': str(home), 'APPDATA': str(home / 'AppData/Roaming'), 'HARNESS_TEST_NO_FSYNC': '1', 'GIT_OPTIONAL_LOCKS': '0', 'PYTHONIOENCODING': 'utf-8'}
def _run_harness(base: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run([sys.executable, str(HARNESS_PY), *args], cwd=str(base), env=_iso_env(base / 'home'), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=60, check=False)
def _init_provisional(base: Path, *, job_id: str='~022124567641351805598', topic: str='Magento & GA4') -> tuple[Path, Path]:
	from agent_tools import upwork_project as up
	from test_onboarding import source
	daily = base / 'daily'
	data = {**source(job_id), 'url': f'https://upwork.com/jobs/{job_id}'}
	res = up.initialize_upwork_project(job_id, topic=topic, date_str='2026-11-23', daily_root=daily, extracted_data=data, register_native=False)
	return (Path(res['project_dir']).resolve(), daily)
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
def _dual_ag_registrar(ag_dirs: dict[str, Path], folders: Path):
	from agent_tools.platforms import antigravity
	def _reg(root, label, day):
		p0 = antigravity.register_antigravity_project(root, label, day, projects_dir=ag_dirs['A0'], folders_json_path=folders)
		p6 = antigravity.register_antigravity_project(root, label, day, projects_dir=ag_dirs['A6'], folders_json_path=folders, preferred_id=p0['project_id'])
		return {**p0, 'instances': {'A0': p0, 'A6': p6}}
	return _reg
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
if '__main__' == __name__:
	unittest.main()
