# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import closing, redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import override
from unittest.mock import patch
import base64
import io
import json
import sqlite3
import sys
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
TESTS = WT_ROOT / 'tests'
for _p in (SCRIPTS, TESTS):
	if str(_p) not in sys.path:
		sys.path.insert(0, str(_p))
from agent_tools import cleanup, metadata, project_rename, runtime, upwork_project as up
from agent_tools.platforms import antigravity
# 2026-11-26 "Add contract invariants for metadata test env isolation and worktree-land gates": https://github.com/dmitry-ai/harness/issues/366
from agent_tools.env_isolation_contracts import isolated_host_env
from test_agent_tools import TemporaryCase
from test_onboarding import source
# 2026-11-26
# "Add cross-subsystem integration tests for upwork-cleanup lifecycle and audit":
# https://github.com/dmitry-ai/harness/issues/309
class CleanupIntegrationTests(TemporaryCase):
	# @used-by :meth:`CleanupIntegrationTests.test_apply_and_cleanup_report_manifest_and_metadata_roundtrip()`
	# @used-by :meth:`CleanupIntegrationTests.test_disabled_codex_history_preserves_antigravity_registrations_without_shared_control()`
	# @used-by :meth:`CleanupIntegrationTests.test_init_handoff_delayed_finalize_preserved_as_recent()`
	# @used-by :meth:`CleanupIntegrationTests.test_rename_project_cleanup_recent_and_old_path_history()`
	def _init_and_register(self, job_id: str, topic: str, *, created_hours: float, launcher: Path | None=None) -> tuple[Path, dict]:
		data = {**source(job_id), 'url': f'https://upwork.com/jobs/{job_id}'}
		res = up.initialize_upwork_project(job_id, topic=topic, date_str='2026-11-20', daily_root=self.daily, extracted_data=data, register_native=False, launcher_root=launcher)
		proj = Path(res['project_dir']).resolve()
		pj_file = proj / '\ua616/project.json'
		state = json.loads(pj_file.read_text(encoding='utf-8'))
		state['created_at'] = (self.now - timedelta(hours=created_hours)).isoformat()
		pj_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
		with patch.object(antigravity, 'platform_instances', side_effect=lambda p, **kw: runtime.platform_instances(p, config=self.config, **kw)), patch.object(antigravity, 'platform_settings', return_value=self.config['platforms']['antigravity']), patch.object(runtime, 'settings', return_value=self.config):
			reg = antigravity.register(proj, proj.name.split(' - ', 1)[1], '2026-11-20')
		return (proj, reg)
	# @used-by :meth:`CleanupIntegrationTests.test_apply_and_cleanup_report_manifest_and_metadata_roundtrip()`
	# @used-by :meth:`CleanupIntegrationTests.test_disabled_codex_history_preserves_antigravity_registrations_without_shared_control()`
	# @used-by :meth:`CleanupIntegrationTests.test_init_handoff_delayed_finalize_preserved_as_recent()`
	# @used-by :meth:`CleanupIntegrationTests.test_rename_project_cleanup_recent_and_old_path_history()`
	def _run_cleanup_no_codex(self, *, apply: bool=True) -> dict:
		# @used-by :meth:`CleanupIntegrationTests._run_cleanup_no_codex()`
		def _boom(_req):
			raise AssertionError('Disabled Codex must not invoke shared_control')
		return cleanup.cleanup_projects(apply=apply, daily_root=self.daily, now=self.now, config=self.config, control=_boom)
	# @used-by :meth:`CleanupIntegrationTests.setUp()`
	# @used-by :meth:`CleanupIntegrationTests.test_disabled_codex_history_preserves_antigravity_registrations_without_shared_control()`
	# @used-by :meth:`CleanupIntegrationTests.test_rename_project_cleanup_recent_and_old_path_history()`
	def _sql(self, path: Path, stmt: str, params: tuple=()) -> None:
		path.parent.mkdir(parents=True, exist_ok=True)
		with closing(sqlite3.connect(path)) as conn:
			conn.execute(stmt, params)
			conn.commit()
	# @used-by :mod:`unittest`
	# @see :meth:`test_agent_tools.TemporaryCase.setUp()`
	@override
	def setUp(self) -> None:
		super().setUp()
		self.now = datetime(2026, 11, 26, 9, 0, tzinfo=timezone.utc)
		self.workspace = self.root / 'workspace'
		self.daily = self.workspace / 'proposals/daily'
		self.launcher = self.workspace / 'proposals/init'
		self.daily.mkdir(parents=True)
		self.launcher.mkdir(parents=True)
		self.folders = self.root / 'ag/folders.json'
		self.folders.parent.mkdir(parents=True, exist_ok=True)
		self.folders.write_text('{"folders":[],"projectFolderMap":{},"collapsedFolders":[]}', encoding='utf-8')
		self.ag_homes = {name: self.root / f'ag/{name}' for name in ('A0', 'A6')}
		self.cx_homes = {name: self.root / f'cx/{name}' for name in ('C1', 'C2')}
		for home in self.ag_homes.values():
			(home / '.gemini/config/projects').mkdir(parents=True)
			self._sql(home / '.gemini/antigravity/conversation_summaries.db', 'CREATE TABLE conversation_summaries (project_id TEXT, workspace_uris TEXT)')
		for home in self.cx_homes.values():
			home.mkdir(parents=True)
		self.config = deepcopy(runtime.settings())
		self.config['workspace_root'] = str(self.workspace)
		self.config['daily_root'] = 'proposals/daily'
		self.config['platforms']['antigravity']['folders_json'] = str(self.folders)
		self.config['platforms']['antigravity']['instances'] = {
			'A0': {'enabled': True, 'primary': True, 'label': 'A0', 'home': str(self.ag_homes['A0'])},
			'A6': {'enabled': True, 'primary': False, 'label': 'A6', 'home': str(self.ag_homes['A6'])},
		}
		self.config['platforms']['codex']['instances'] = {
			'C1': {'enabled': False, 'label': 'C1', 'home': str(self.cx_homes['C1'])},
			'C2': {'enabled': False, 'label': 'C2', 'home': str(self.cx_homes['C2'])},
		}
	# @used-by :mod:`unittest`
	def test_apply_and_cleanup_report_manifest_and_metadata_roundtrip(self) -> None:
		proj, reg = self._init_and_register('~029100000001', 'Stale Integration Topic', created_hours=120)
		orig_a0 = Path(reg['instances']['A0']['project_file']).read_bytes()
		applied = self._run_cleanup_no_codex(apply=True)
		self.assertTrue(applied['complete'], applied)
		self.assertEqual(1, applied['counts']['removed'])
		m_path = Path(applied['audit_manifest'])
		manifest = json.loads(m_path.read_text(encoding='utf-8'))
		self.assertEqual(1, len(manifest['removed_projects']))
		rec = manifest['removed_projects'][0]
		self.assertEqual(str(proj), rec['root'])
		self.assertEqual(reg['project_id'], rec['project_id'])
		self.assertEqual(orig_a0, base64.b64decode(rec['instances']['A0']['snapshots'][0]['payload_base64']))
		scratch = self.workspace / '\ua616/data/scratch/cleanup-audit.md'
		scratch.parent.mkdir(parents=True, exist_ok=True)
		body = f'Очистка завершена.  \nМанифест: `{m_path.as_posix()}`.  \n'
		scratch.write_text(body, encoding='utf-8')
		out = io.StringIO()
		# 2026-11-26 "Add contract invariants for metadata test env isolation and worktree-land gates": https://github.com/dmitry-ai/harness/issues/366
		fake_env = isolated_host_env(ANTIGRAVITY_ACCOUNT='A0', ANTIGRAVITY_CONVERSATION_ID='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
		with patch.object(cleanup, 'settings', return_value=self.config), patch.dict('os.environ', fake_env, clear=False), redirect_stdout(out):
			rc = up.main(['cleanup-report', '--answer-file', str(scratch), '--consume-input', '--manifest', str(m_path), '--project', str(self.workspace), '--platform', 'antigravity'])
		self.assertEqual(0, rc, out.getvalue())
		rep = json.loads(out.getvalue())
		self.assertFalse(scratch.exists())
		self.assertEqual(body, rep['answer'])
		hdr, stripped = metadata.extract_leading_metadata_header(Path(rep['path']).read_text(encoding='utf-8'))
		self.assertIsNotNone(hdr)
		self.assertEqual(body, stripped)
		self.assertEqual('A0', hdr['Agent']['Instance'])
		self.assertEqual(m_path.resolve().as_posix(), hdr['Trace']['Cleanup Manifest'])
	# @used-by :mod:`unittest`
	def test_disabled_codex_history_preserves_antigravity_registrations_without_shared_control(self) -> None:
		p_cx, r_cx = self._init_and_register('~029200000001', 'Codex Preserved Topic', created_hours=140)
		p_drop, r_drop = self._init_and_register('~029200000002', 'Empty Drop Topic', created_hours=140)
		self._sql(self.cx_homes['C1'] / 'state_5.sqlite', 'CREATE TABLE threads (id TEXT, project_id TEXT, cwd TEXT, archived INTEGER)')
		self._sql(self.cx_homes['C1'] / 'state_5.sqlite', 'INSERT INTO threads VALUES (?,?,?,?)', ('cx-thread-1', 'cx-p1', str(p_cx), 1))
		res = self._run_cleanup_no_codex(apply=True)
		self.assertTrue(res['complete'], res)
		by_root = {Path(p['root']).resolve(): p for p in res['projects']}
		self.assertEqual('preserved', by_root[p_cx]['status'])
		self.assertEqual(1, by_root[p_cx]['conversations']['codex:C1'])
		self.assertEqual('removed', by_root[p_drop]['status'])
		for iid in ('A0', 'A6'):
			self.assertTrue(Path(r_cx['instances'][iid]['project_file']).exists())
			self.assertFalse(Path(r_drop['instances'][iid]['project_file']).exists())
		folders_data = json.loads(self.folders.read_text(encoding='utf-8'))
		self.assertIn(r_cx['project_id'], folders_data['projectFolderMap'])
		self.assertNotIn(r_drop['project_id'], folders_data['projectFolderMap'])
	# @used-by :mod:`unittest`
	def test_init_handoff_delayed_finalize_preserved_as_recent(self) -> None:
		l_turn = self.launcher / '\ua616/data/turns/turn01.json'
		l_turn.parent.mkdir(parents=True, exist_ok=True)
		l_turn.write_text(json.dumps({'key': 'turn01', 'status': 'open', 'conversation_id': 'be6873ea-5b72-4a7f-82bd-420b873f13f9', 'updated_at': (self.now - timedelta(hours=80)).isoformat(), 'requests': [{'id': 'r0', 'text': '/upwork-init https://upwork.com/jobs/~029300000001'}]}), encoding='utf-8')
		proj, reg = self._init_and_register('~029300000001', 'Delayed Finalize Topic', created_hours=82, launcher=self.launcher)
		ho_data = json.loads(l_turn.read_text(encoding='utf-8'))
		self.assertEqual('handed_off', ho_data['status'])
		ho_data['updated_at'] = (self.now - timedelta(hours=80)).isoformat()
		l_turn.write_text(json.dumps(ho_data), encoding='utf-8')
		fin_at = (self.now - timedelta(hours=15)).isoformat()
		(proj / '\ua616/data/workflow.json').write_text(json.dumps({'schema_version': 1, 'project_root': str(proj), 'job_id': '~029300000001', 'stages': {'finalize': {'status': 'complete', 'time': fin_at}}}), encoding='utf-8')
		res = self._run_cleanup_no_codex(apply=True)
		self.assertTrue(res['complete'], res)
		by_root = {Path(p['root']).resolve(): p for p in res['projects']}
		self.assertEqual('recent', by_root[proj]['status'])
		self.assertEqual('workflow.finalize', by_root[proj]['age_basis'])
		self.assertEqual(fin_at, by_root[proj]['effective_activity_at'])
		for iid in ('A0', 'A6'):
			self.assertTrue(Path(reg['instances'][iid]['project_file']).exists())
		self.assertIn(reg['project_id'], json.loads(self.folders.read_text(encoding='utf-8'))['projectFolderMap'])
	# @used-by :mod:`unittest`
	def test_rename_project_cleanup_recent_and_old_path_history(self) -> None:
		ag_dirs = {iid: home / '.gemini/config/projects' for iid, home in self.ag_homes.items()}
		p1, r1 = self._init_and_register('~029400000001', 'Provisional One', created_hours=100)
		ren1 = project_rename.rename_project(p1, domain='fresh-renamed.com', daily_root=self.daily, antigravity_projects_dirs=ag_dirs, antigravity_folders_json=self.folders, targets=['antigravity'])
		new_p1 = Path(ren1['project_dir']).resolve()
		pj1_path = new_p1 / '\ua616/project.json'
		pj1 = json.loads(pj1_path.read_text(encoding='utf-8'))
		pj1['renamed_from'][-1]['at'] = (self.now - timedelta(hours=2)).isoformat()
		pj1_path.write_text(json.dumps(pj1, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
		p2, r2 = self._init_and_register('~029400000002', 'Provisional Two', created_hours=150)
		ren2 = project_rename.rename_project(p2, domain='old-renamed.com', daily_root=self.daily, antigravity_projects_dirs=ag_dirs, antigravity_folders_json=self.folders, targets=['antigravity'])
		new_p2 = Path(ren2['project_dir']).resolve()
		pj2_path = new_p2 / '\ua616/project.json'
		pj2 = json.loads(pj2_path.read_text(encoding='utf-8'))
		pj2['renamed_from'][-1]['at'] = (self.now - timedelta(hours=100)).isoformat()
		pj2_path.write_text(json.dumps(pj2, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
		self._sql(self.ag_homes['A0'] / '.gemini/antigravity/conversation_summaries.db', 'INSERT INTO conversation_summaries VALUES (?,?)', ('unrelated-proj', json.dumps([p2.as_uri()])))
		res = self._run_cleanup_no_codex(apply=True)
		self.assertTrue(res['complete'], res)
		by_root = {Path(p['root']).resolve(): p for p in res['projects']}
		self.assertEqual('recent', by_root[new_p1]['status'])
		self.assertEqual('project.renamed_from', by_root[new_p1]['age_basis'])
		self.assertEqual('preserved', by_root[new_p2]['status'])
		self.assertEqual(1, by_root[new_p2]['conversations']['antigravity:A0'])
		for pid in (r1['project_id'], r2['project_id']):
			self.assertTrue((ag_dirs['A0'] / f'{pid}.json').exists())
			self.assertTrue((ag_dirs['A6'] / f'{pid}.json').exists())
if '__main__' == __name__:
	unittest.main()
