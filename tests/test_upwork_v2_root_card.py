# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
import os
import unittest
from agent_tools import path_registry as pr
from agent_tools import upwork_project as up
from agent_tools import workflow
from agent_tools.red_flags import sync_project_red_flags
from Df.Harness.Project.CardSyncAuditor import CardSyncAuditor
from Df.Harness.Project.WebsiteCardSyncer import WebsiteCardSyncer
from Df.Harness.Upwork.ProjectConfigurator import ProjectConfigurator
from Df.Harness.Workflow.HealthAuditor import HealthAuditor
from Df.Harness.Workflow.ReceiptVerifier import ReceiptVerifier
from Df.Harness.lib.project import dfh_resolve_overview_md
from test_agent_tools import TemporaryCase
from test_evidence_contract import v3_analysis
from test_onboarding import analysis, claim, source
# 2026-11-28 "Use .md root card via v2_upwork profile": https://github.com/dmitry-ai/harness/issues/415
class UpworkV2RootCardTests(TemporaryCase):
	# @used-by :meth:`UpworkV2RootCardTests.test_legacy_v2_readme_fallback_works_across_card_consumers()`
	def __make_legacy_v2_upwork(self) -> tuple[Path, dict]:
		proj = self.root / 'daily/2026/11/23/1 - legacy.example'
		for rel in ('\U0001f56e', '\u2c0f/\u227b', '\u2c0f/\u227a', '\ua616/KB', '\ua616/data', '\ua66e/\u227b', '\ua66e/\u227a'):
			(proj / rel).mkdir(parents=True, exist_ok=True)
		(proj / '\ua616/project.json').write_text(json.dumps({'job_id': '~02111122223333', 'fs_version': 2, 'journal_version': 3, 'initialized': True}), encoding='utf-8')
		(proj / 'readme.md').write_text('# Legacy V2 Task\nhttps://upwork.com/jobs/~02111122223333\n', encoding='utf-8')
		(proj / '\U0001f56e/Project.md').write_text('# 1. Client\nInfo\n', encoding='utf-8')
		val = analysis()
		val['identity'] = [claim('H-SITE-1')]
		val['websites'] = [{'url': 'https://legacy.example/', 'role': 'target', 'basis_id': 'H-SITE-1'}]
		val['red_flags'] = [{'id': 'RF-CLIENT-INTERMEDIARY', 'status': 'confirmed', 'summary': 'Agency intermediary.', 'basis_ids': ['H-SITE-1']}]
		val = v3_analysis(proj, val)
		(proj / '\ua616/KB/Analysis.json').write_text(json.dumps(val, ensure_ascii=False), encoding='utf-8')
		return (proj, val)
	# @used-by :mod:`unittest`
	def test_custom_registry_without_v2_upwork_falls_back_to_v2(self):
		proj = self.root / 'custom_v2_upwork'
		(proj / '\U0001f56e').mkdir(parents=True)
		(proj / '\ua616').mkdir(parents=True)
		(proj / '\ua616/project.json').write_text(json.dumps({'job_id': '~021111', 'fs_version': 2}), encoding='utf-8')
		reg_raw = deepcopy(pr.load_registry().raw)
		reg_raw['project_profiles'].pop('v2_upwork', None)
		reg_file = self.put('custom-paths.json', json.dumps(reg_raw))
		with patch.dict(os.environ, {'HARNESS_PATHS_FILE': str(reg_file)}):
			pr.clear_registry_cache()
			pp = pr.project_paths(proj, exact_root=True)
			self.assertEqual('v2', pp.profile)
			self.assertEqual(2, pp.fs_version)
			self.assertEqual((proj / 'readme.md').resolve(), pp.path('overview_md').resolve())
		pr.clear_registry_cache()
	# @used-by :mod:`unittest`
	def test_legacy_v2_readme_fallback_works_across_card_consumers(self):
		proj, val = self.__make_legacy_v2_upwork()
		pp = pr.project_paths(proj, exact_root=True)
		self.assertEqual('v2_upwork', pp.profile)
		self.assertEqual((proj / '.md').resolve(), pp.path('overview_md').resolve())
		self.assertEqual((proj / 'readme.md').resolve(), dfh_resolve_overview_md(pp).resolve())
		ctx = ProjectConfigurator.default_context_config(proj)
		self.assertEqual(['readme.md'], ctx['sections'][0]['files'])
		self.assertEqual('published', WebsiteCardSyncer(proj, val).sync()['status'])
		self.assertEqual('published', sync_project_red_flags(proj, val)['status'])
		self.assertEqual([], [i for i in CardSyncAuditor(pp, val).audit() if 'project.website' == i['code']])
		(proj / 'readme.md').write_text((proj / 'readme.md').read_text(encoding='utf-8') + '\n[Bad](https://legacy.example/a%20b)\n', encoding='utf-8')
		health_codes = {i['code'] for i in HealthAuditor(proj).check_project()['issues']}
		self.assertIn('document.link_style', health_codes)
	# @used-by :mod:`unittest`
	def test_new_v2_upwork_project_creates_dot_md_not_readme(self):
		data = source('~0241500001')
		res = up.initialize_upwork_project(data['job_id'], domain_or_topic='Shop', date_str='2026-11-28', daily_root=self.root / 'daily', extracted_data=data, register_antigravity=False)
		root = Path(res['project_dir'])
		pp = pr.project_paths(root, exact_root=True)
		self.assertEqual('v2_upwork', pp.profile)
		self.assertEqual(2, pp.fs_version)
		self.assertTrue((root / '.md').is_file())
		self.assertFalse((root / 'readme.md').exists())
		ctx = json.loads((root / '.agents/context.json').read_text(encoding='utf-8'))
		self.assertEqual(['.md'], ctx['sections'][0]['files'])
	# @used-by :mod:`unittest`
	def test_profile_routing_separates_upwork_and_standalone_v2_repos(self):
		standalone = self.root / 'standalone_v2'
		(standalone / '\U0001f56e').mkdir(parents=True)
		pp_standalone = pr.project_paths(standalone, exact_root=True)
		self.assertEqual('v2', pp_standalone.profile)
		self.assertEqual((standalone / 'readme.md').resolve(), pp_standalone.path('overview_md').resolve())
		sw = self.root / 'software_v2'
		(sw / '\u2c0f/\u227b/\u2655/\u26ef/.git').mkdir(parents=True)
		(sw / '\ua616').mkdir(parents=True)
		(sw / '\ua616/project.json').write_text(json.dumps({'job_id': '~021', 'fs_version': 2}), encoding='utf-8')
		self.assertEqual('v2_software', pr.project_paths(sw, exact_root=True).profile)
		reloc = self.root / 'reloc_v2_no_fs_ver'
		(reloc / '\U0001f56e').mkdir(parents=True)
		(reloc / '\ua616').mkdir(parents=True)
		(reloc / '\ua616/project.json').write_text(json.dumps({'job_id': '~022'}), encoding='utf-8')
		pp_reloc = pr.project_paths(reloc, exact_root=True)
		self.assertEqual('v2_upwork', pp_reloc.profile)
		self.assertEqual(2, pp_reloc.fs_version)
		self.assertEqual((reloc / '\U0001f56e').resolve(), pp_reloc.manual_kb_dir.resolve())
	# @used-by :mod:`unittest`
	def test_receipt_verifier_and_dir_resolver_support_dot_md_and_readme_bidirectional(self):
		daily = self.root / 'daily'
		dot_dir = daily / '2026/11/28/1 - Dot'
		dot_dir.mkdir(parents=True)
		(dot_dir / '.md').write_text('# Dot\nhttps://upwork.com/jobs/~02415999\n', encoding='utf-8')
		self.assertEqual(dot_dir.resolve(), up.resolve_or_create_project_dir('~02415999', 'Other', '2026-11-28', daily))
		proj = self.root / 'bidir_receipt'
		(proj / '\U0001f56e').mkdir(parents=True)
		(proj / '\ua616').mkdir(parents=True)
		(proj / '\ua616/project.json').write_text(json.dumps({'job_id': '~02415888', 'fs_version': 2}), encoding='utf-8')
		dot_md = proj / '.md'
		dot_md.write_text('# Card\n', encoding='utf-8')
		digest = workflow.file_hash(dot_md)
		self.assertTrue(ReceiptVerifier(proj, {'inputs': {}, 'outputs': {'readme.md': digest}}).is_current())
		dot_md.unlink()
		readme_md = proj / 'readme.md'
		readme_md.write_text('# Card\n', encoding='utf-8')
		self.assertTrue(ReceiptVerifier(proj, {'inputs': {}, 'outputs': {'.md': digest}}).is_current())
if '__main__' == __name__:
	unittest.main()
