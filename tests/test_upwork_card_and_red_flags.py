# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import unittest
_SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
if str(_SCRIPTS) not in sys.path:
	sys.path.insert(0, str(_SCRIPTS))
from agent_tools import upwork_project as up
from agent_tools.analysis import publish_analysis, render_analysis
from agent_tools.knowledge import sync_website_card
from agent_tools.path_registry import project_paths
from agent_tools.red_flags import END, START, render_red_flags, sync_project_red_flags
from Df.Harness.Analysis.RedFlagValidator import CARD_HEADINGS
from Df.Harness.Project.CardSyncAuditor import CardSyncAuditor
from Df.Harness.Project.WebsiteCardSyncer import WebsiteCardSyncer
from test_agent_tools import TemporaryCase
from test_evidence_contract import v3_analysis
from test_onboarding import analysis, claim, source
# 2026-11-28 "Switch root .md to bare URLs and structured Red Flags headings": https://github.com/dmitry-ai/harness/issues/417
class UpworkCardAndRedFlagsTests(TemporaryCase):
	# @used-by :meth:`UpworkCardAndRedFlagsTests.test_bare_url_website_sync_and_legacy_migration()`
	# @used-by :meth:`UpworkCardAndRedFlagsTests.test_broken_apex_evidence_keeps_www_in_root_card()`
	# @used-by :meth:`UpworkCardAndRedFlagsTests.test_legacy_website_markers_migrate_and_reject_tampering()`
	# @used-by :meth:`UpworkCardAndRedFlagsTests.test_markerless_red_flags_dual_surface_and_legacy_migration()`
	def __make_project(self, url: str | None='https://www.blueskypeptide.com/', job_id: str='~024170001') -> tuple[Path, Path, dict]:
		data = source(job_id)
		res = up.initialize_upwork_project(data['job_id'], domain_or_topic='blueskypeptide.com', date_str='2026-11-23', daily_root=self.root / 'daily', extracted_data=data, register_antigravity=False)
		proj = Path(res['project_dir'])
		pp = project_paths(proj, exact_root=True)
		card = pp.path('overview_md', proj / '.md')
		val = analysis()
		val['identity'] = [claim('H-IDENTITY-CLIENT'), claim('H-SITE-1')]
		val['websites'] = [{'url': url, 'role': 'target', 'basis_id': 'H-SITE-1'}]
		val['red_flags'] = [{'id': 'RF-CLIENT-INTERMEDIARY', 'status': 'confirmed', 'summary': 'Agency hiring for end merchant.', 'basis_ids': ['H-IDENTITY-CLIENT']}, {'id': 'RF-WEBSITE-UNIDENTIFIED', 'status': 'unresolved', 'summary': 'Target checkout URL not confirmed.', 'basis_ids': ['H-SITE-1']}]
		val = v3_analysis(proj, val)
		(proj / '\ua616/KB/Analysis.json').write_text(json.dumps(val, ensure_ascii=False), encoding='utf-8')
		return (proj, card, val)
	# @used-by :mod:`unittest`
	def test_bare_url_website_sync_and_legacy_migration(self):
		proj, card, val = self.__make_project('https://www.blueskypeptide.com/')
		self.assertEqual(f"# {source('~024170001')['title']}\nhttps://upwork.com/jobs/~024170001\n", card.read_text(encoding='utf-8'))
		self.assertNotIn('<!-- upwork-init:', card.read_text(encoding='utf-8'))
		self.assertEqual('published', sync_website_card(proj, val)['status'])
		expected = f"# {source('~024170001')['title']}\nhttps://upwork.com/jobs/~024170001\nhttps://blueskypeptide.com\n"
		self.assertEqual(expected, card.read_text(encoding='utf-8'))
		self.assertEqual('unchanged', WebsiteCardSyncer(proj, val, check=True).sync()['status'])
		card.write_text(expected + '\nhttps://upwork.com/ab/proposals/12345\n', encoding='utf-8')
		self.assertEqual('unchanged', sync_website_card(proj, val)['status'])
		self.assertIn('https://upwork.com/ab/proposals/12345', card.read_text(encoding='utf-8'))
		card.write_text(card.read_text(encoding='utf-8').replace('https://blueskypeptide.com', 'https://manual-edit.example'), encoding='utf-8')
		self.assertEqual('conflict', sync_website_card(proj, val)['status'])
		null_proj, null_card, null_val = self.__make_project(None, '~024170003')
		pp_null = project_paths(null_proj, exact_root=True)
		self.assertTrue(any(('project.website' == i['code'] for i in CardSyncAuditor(pp_null, null_val).audit())))
		self.assertEqual('unchanged', sync_website_card(null_proj, null_val)['status'])
		self.assertEqual([], [i for i in CardSyncAuditor(pp_null, null_val).audit() if 'project.website' == i['code']])
		self.assertNotIn('<!-- upwork-init:', null_card.read_text(encoding='utf-8'))
	# @used-by :mod:`unittest`
	def test_broken_apex_evidence_keeps_www_in_root_card(self):
		proj, card, val = self.__make_project('https://www.broken-only.test/')
		obs_dir = proj / '\ua616/KB/Evidence/HTTP/apex-err'
		obs_dir.mkdir(parents=True, exist_ok=True)
		(obs_dir / 'observation.json').write_text(json.dumps({'url': 'https://broken-only.test/', 'status': None, 'error': 'URLError'}), encoding='utf-8')
		self.assertEqual('published', sync_website_card(proj, val)['status'])
		self.assertIn('\nhttps://www.broken-only.test\n', card.read_text(encoding='utf-8'))
	# @used-by :mod:`unittest`
	def test_legacy_website_markers_migrate_and_reject_tampering(self):
		proj, card, val = self.__make_project('https://www.blueskypeptide.com/', '~024170004')
		legacy = b'<!-- upwork-init:websites:start -->\n- Target: https://www.blueskypeptide.com/\n<!-- upwork-init:websites:end -->\n'
		card.write_bytes(b'# Title\nhttps://upwork.com/jobs/~024170004\n\n' + legacy + b'\n# Notes\n')
		rendered = {str(card): {'managed_blocks': {'websites': {'sha256': hashlib.sha256(legacy).hexdigest()}}}}
		(proj / '\ua616/data/rendered.json').write_text(json.dumps(rendered), encoding='utf-8')
		self.assertEqual('published', sync_website_card(proj, val)['status'])
		migrated = card.read_text(encoding='utf-8')
		self.assertNotIn('<!-- upwork-init:websites:', migrated)
		self.assertIn('https://blueskypeptide.com\n', migrated)
		self.assertIn('# Notes\n', migrated)
		card.write_bytes(b'# Title\nhttps://upwork.com/jobs/~024170004\n' + legacy.replace(b'Target:', b'Edited:'))
		self.assertEqual('conflict', sync_website_card(proj, val)['status'])
	# @used-by :mod:`unittest`
	def test_markerless_red_flags_dual_surface_and_legacy_migration(self):
		self.assertEqual('Посредник', CARD_HEADINGS['RF-CLIENT-INTERMEDIARY'])
		self.assertEqual('Сайт не установлен', CARD_HEADINGS['RF-WEBSITE-UNIDENTIFIED'])
		proj, card, val = self.__make_project('https://blueskypeptide.com/')
		en_md = render_analysis(val)
		self.assertIn('# Red Flags\n', en_md)
		self.assertNotIn('# Red Flags \u2014', en_md)
		self.assertIn('## Client is an intermediary', en_md)
		self.assertIn('## Target website is unidentified', en_md)
		self.assertIn('Status: confirmed', en_md)
		res = publish_analysis(proj / '\ua616/KB/Analysis.json')
		self.assertEqual('published', res['project_card']['status'])
		card_txt = card.read_text(encoding='utf-8')
		self.assertNotIn('<!-- upwork-init:', card_txt)
		self.assertIn('# Red Flags\n', card_txt)
		self.assertIn('## Посредник\n', card_txt)
		self.assertIn('## Сайт не установлен\n', card_txt)
		self.assertIn('Статус: подтверждено.', card_txt)
		card.write_text(card_txt + '\n# My Notes\nKeep me.\n', encoding='utf-8')
		val2 = deepcopy(val)
		val2['red_flags'] = [val['red_flags'][0]]
		self.assertEqual('published', sync_project_red_flags(proj, val2)['status'])
		updated = card.read_text(encoding='utf-8')
		self.assertIn('# My Notes\nKeep me.\n', updated)
		self.assertIn('## Посредник\n', updated)
		self.assertNotIn('## Сайт не установлен', updated)
		card.write_text(updated.replace('## Посредник', '## Custom Heading'), encoding='utf-8')
		self.assertEqual('conflict', sync_project_red_flags(proj, val2)['status'])
		legacy_body = START + b'\n\nOld body\n' + END + b'\n'
		legacy_heading = '# Red Flags \u2014 1\n\n'.encode('utf-8')
		card.write_bytes(b'# Title\nhttps://upwork.com/jobs/~024170001\n\n' + legacy_heading + legacy_body)
		(proj / '\ua616/data/red-flags.json').write_text(json.dumps({'block_sha256': hashlib.sha256(legacy_body).hexdigest(), 'heading': legacy_heading.decode('utf-8'), 'separator': '\n'}), encoding='utf-8')
		self.assertEqual('published', sync_project_red_flags(proj, val2)['status'])
		self.assertNotIn('<!-- upwork-init:', card.read_text(encoding='utf-8'))
		self.assertIn('## Посредник\n', card.read_text(encoding='utf-8'))
	# @used-by :mod:`unittest`
	def test_sync_initial_hypothesis_writes_bare_url_and_no_markers(self):
		data = source('~024170002')
		hyp = {**claim('H-SITE-1'), 'website_url': 'https://www.blueskypeptide.com/'}
		res = up.initialize_upwork_project(data['job_id'], domain_or_topic='blueskypeptide.com', date_str='2026-11-23', daily_root=self.root / 'daily2', extracted_data=data, site_hypothesis=hyp, register_antigravity=False)
		proj = Path(res['project_dir'])
		card = project_paths(proj, exact_root=True).path('overview_md', proj / '.md')
		self.assertEqual(f"# {data['title']}\nhttps://upwork.com/jobs/~024170002\nhttps://blueskypeptide.com\n", card.read_text(encoding='utf-8'))
		self.assertNotIn('<!-- upwork-init:', card.read_text(encoding='utf-8'))
		self.assertEqual('unassessed', WebsiteCardSyncer.sync_initial(proj, proj / '\ua616/project.json', None)['status'])
if '__main__' == __name__:
	unittest.main()
