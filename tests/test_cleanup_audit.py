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
from agent_tools import cleanup, metadata, runtime, upwork_project as up
from agent_tools.platforms import antigravity
from test_agent_tools import TemporaryCase
# 2026-11-26
# "Persist cleanup audit manifests and metadata headers aligned with FILE-3":
# https://github.com/dmitry-ai/harness/issues/308
class CleanupAuditTests(TemporaryCase):
	# @used-by :meth:`CleanupAuditTests.test_apply_persists_sidecar_manifest_with_rollback_snapshots_while_dry_run_stays_readonly()`
	# @used-by :meth:`CleanupAuditTests.test_cleanup_report_writes_metadata_header_links_manifest_and_consumes_scratch_file()`
	def _make_old_project(self, number: int, name: str) -> tuple[Path, dict]:
		proj = self.daily / f'2026/11/10/{number} - {name}'
		(proj / '\ua616').mkdir(parents=True, exist_ok=True)
		state = {'job_id': f'~02880000000{number}', 'initialized': True, 'request_date': '2026-11-10', 'created_at': (self.now - timedelta(hours=120)).isoformat()}
		(proj / '\ua616/project.json').write_text(json.dumps(state), encoding='utf-8')
		(proj / 'readme.md').write_text(f'# {name}\n', encoding='utf-8')
		with patch.object(antigravity, 'platform_instances', side_effect=lambda p, **kw: runtime.platform_instances(p, config=self.config, **kw)), patch.object(antigravity, 'platform_settings', return_value=self.config['platforms']['antigravity']), patch.object(runtime, 'settings', return_value=self.config):
			reg = antigravity.register(proj, name, '2026-11-10')
		return (proj, reg)
	# @used-by :meth:`CleanupAuditTests.setUp()`
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
		self.now = datetime(2026, 11, 26, 8, 50, tzinfo=timezone.utc)
		self.workspace = self.root / 'workspace'
		self.daily = self.workspace / 'proposals/daily'
		self.daily.mkdir(parents=True)
		self.folders = self.root / 'ag/folders.json'
		self.folders.parent.mkdir(parents=True, exist_ok=True)
		self.folders.write_text('{"folders":[],"projectFolderMap":{},"collapsedFolders":[]}', encoding='utf-8')
		self.ag_homes = {name: self.root / f'ag/{name}' for name in ('A0', 'A6')}
		for home in self.ag_homes.values():
			(home / '.gemini/config/projects').mkdir(parents=True)
			self._sql(home / '.gemini/antigravity/conversation_summaries.db', 'CREATE TABLE conversation_summaries (project_id TEXT, workspace_uris TEXT)')
		self.config = deepcopy(runtime.settings())
		self.config['workspace_root'] = str(self.workspace)
		self.config['daily_root'] = 'proposals/daily'
		self.config['platforms']['antigravity']['folders_json'] = str(self.folders)
		self.config['platforms']['antigravity']['instances'] = {
			'A0': {'enabled': True, 'primary': True, 'label': 'A0', 'home': str(self.ag_homes['A0'])},
			'A6': {'enabled': True, 'primary': False, 'label': 'A6', 'home': str(self.ag_homes['A6'])},
		}
		self.config['platforms']['codex']['instances'] = {
			'C1': {'enabled': False, 'label': 'C1', 'home': str(self.root / 'cx/C1')},
		}
	# @used-by :mod:`unittest`
	def test_apply_persists_sidecar_manifest_with_rollback_snapshots_while_dry_run_stays_readonly(self) -> None:
		proj, reg = self._make_old_project(1, 'stale-site.com')
		orig_a0_bytes = Path(reg['instances']['A0']['project_file']).read_bytes()
		log_root = self.workspace / 'AI/log/cleanup'
		preview = cleanup.cleanup_projects(apply=False, daily_root=self.daily, now=self.now, config=self.config)
		self.assertTrue(preview['complete'], preview)
		self.assertNotIn('audit_manifest', preview)
		self.assertFalse(log_root.exists())
		applied = cleanup.cleanup_projects(apply=True, daily_root=self.daily, now=self.now, config=self.config)
		self.assertTrue(applied['complete'], applied)
		self.assertIn('audit_manifest', applied)
		m_path = Path(applied['audit_manifest'])
		self.assertTrue(m_path.is_file())
		self.assertEqual('26--11-50.json', m_path.name)
		self.assertTrue(m_path.is_relative_to(log_root))
		manifest = json.loads(m_path.read_text(encoding='utf-8'))
		self.assertEqual(1, manifest['schema_version'])
		self.assertEqual('2026-11-26 11:50 UTC+3', manifest['timestamp'])
		self.assertEqual(applied['cutoff'], manifest['cutoff'])
		self.assertEqual(['A0', 'A6'], manifest['active_instances']['antigravity'])
		self.assertEqual({'codex': ['C1']}, manifest['skipped_disabled_instances'])
		self.assertEqual(1, len(manifest['removed_projects']))
		rec = manifest['removed_projects'][0]
		self.assertEqual(str(proj.resolve()), rec['root'])
		self.assertEqual('~028800000001', rec['job_id'])
		self.assertEqual(reg['project_id'], rec['project_id'])
		self.assertEqual('project.created_at', rec['age_basis'])
		self.assertIn('effective_activity_at', rec)
		self.assertTrue(rec['removed_folders'])
		a0_snaps = rec['instances']['A0']['snapshots']
		self.assertEqual(1, len(a0_snaps))
		self.assertEqual(orig_a0_bytes, base64.b64decode(a0_snaps[0]['payload_base64']))
		self.assertTrue(rec['folder_snapshots']['A0']['folders'])
	# @used-by :mod:`unittest`
	def test_cleanup_report_writes_metadata_header_links_manifest_and_consumes_scratch_file(self) -> None:
		_, _ = self._make_old_project(1, 'removed-site.com')
		applied = cleanup.cleanup_projects(apply=True, daily_root=self.daily, now=self.now, config=self.config)
		m_path = Path(applied['audit_manifest'])
		proj_root = self.root / 'tracked-proj'
		scratch = proj_root / '\ua616/data/scratch/cleanup-report.md'
		scratch.parent.mkdir(parents=True, exist_ok=True)
		body = 'Очистка выполнена.  \nУдалён 1 проект.  \n'
		scratch.write_text(body, encoding='utf-8')
		out = io.StringIO()
		fake_env = {'ANTIGRAVITY_CONVERSATION_ID': '11111111-2222-3333-4444-555555555555', 'ANTIGRAVITY_ACCOUNT': 'A6'}
		with patch.object(cleanup, 'settings', return_value=self.config), patch.dict('os.environ', fake_env, clear=False), redirect_stdout(out):
			rc = up.main(['cleanup-report', '--answer-file', str(scratch), '--consume-input', '--manifest', str(m_path), '--project', str(proj_root), '--platform', 'antigravity'])
		self.assertEqual(0, rc, out.getvalue())
		res = json.loads(out.getvalue())
		self.assertFalse(scratch.exists())
		self.assertEqual(body, res['answer'])
		self.assertEqual(m_path.resolve().as_posix(), res['manifest'])
		log_file = Path(res['path'])
		self.assertTrue(log_file.is_file())
		raw_disk = log_file.read_text(encoding='utf-8')
		hdr, stripped = metadata.extract_leading_metadata_header(raw_disk)
		self.assertIsNotNone(hdr, raw_disk)
		self.assertEqual(body, stripped)
		self.assertEqual(res['timestamp'], hdr['Time'])
		self.assertEqual(proj_root.resolve().as_posix(), hdr['Project']['Path'])
		self.assertEqual('Antigravity', hdr['Agent']['System'])
		self.assertEqual('A6', hdr['Agent']['Instance'])
		self.assertEqual('11111111-2222-3333-4444-555555555555', hdr['Trace']['Conversation ID'])
		self.assertEqual(m_path.resolve().as_posix(), hdr['Trace']['Cleanup Manifest'])
		outside = self.root / 'outside.md'
		outside.write_text(body, encoding='utf-8')
		err_out = io.StringIO()
		with patch.object(cleanup, 'settings', return_value=self.config), redirect_stdout(err_out):
			rc_bad = up.main(['cleanup-report', '--answer-file', str(outside), '--consume-input', '--project', str(proj_root), '--platform', 'antigravity'])
		self.assertNotEqual(0, rc_bad)
		self.assertTrue(outside.exists())
if '__main__' == __name__:
	unittest.main()
