# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Accelerate project_paths and overlay link resolution with fast-path caching":
# https://github.com/dmitry-ai/harness/issues/174
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import sys
import tempfile
import unittest
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import journal, path_registry as pr, storage
class PathRegistryPerformanceTests(unittest.TestCase):
	def tearDown(self) -> None:
		pr.clear_registry_cache()
	def test_data_dir_for_supports_exact_root_and_state_dir_skips_host_scan(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			(proj / '\ua616/data').mkdir(parents=True)
			j_dir = proj / '\ua66e'
			j_dir.mkdir(parents=True)
			with patch.object(pr, 'resolve_project_root', side_effect=AssertionError('exact_root must skip resolve_project_root')):
				self.assertEqual((proj / '\ua616/data').resolve(), storage.data_dir_for(proj, exact_root=True))
			with patch.object(pr, '_refresh_known_overlay_links', side_effect=AssertionError('must not scan host overlays')):
				s_dir = journal.state_dir(j_dir)
			self.assertEqual((proj / '\ua616/data/.journal').resolve(), s_dir.parent.resolve())
	def test_project_paths_fast_cache_hits_and_invalidates_on_fs_mutations(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			(proj / '\ua616').mkdir(parents=True)
			j_dir = proj / '\ua66e'
			j_dir.mkdir(parents=True)
			pp1 = pr.project_paths(j_dir)
			self.assertEqual(1, pp1.fs_version)
			self.assertEqual(3, pp1.journal_version)
			with patch.object(pr, 'resolve_project_root', side_effect=AssertionError('fast cache must skip resolve_project_root')), patch.object(pr, '_journal_cache_sig', side_effect=AssertionError('fast cache must skip 14-stat journal sig')):
				pp2 = pr.project_paths(j_dir)
			self.assertIs(pp1, pp2)
			(j_dir / 'req').mkdir()
			pp_v1j = pr.project_paths(j_dir)
			self.assertEqual(1, pp_v1j.journal_version)
			(proj / '\U0001f56e').mkdir()
			pp_v2 = pr.project_paths(proj)
			self.assertEqual(2, pp_v2.fs_version)
			(proj / '.agents').mkdir()
			(proj / '.agents/paths.json').write_text(json.dumps({'version': 1, 'paths': {'agent_dir': '${PROJECT_ROOT}/_custom_agent'}}), encoding='utf-8')
			pp_ov = pr.project_paths(proj)
			self.assertEqual((proj / '_custom_agent').resolve(), pp_ov.agent_dir)
			(proj / '.agents/paths.json').write_text(json.dumps({'version': 1, 'paths': {'agent_dir': '${PROJECT_ROOT}/_edited_agent'}}), encoding='utf-8')
			pp_ov2 = pr.project_paths(proj)
			self.assertEqual((proj / '_edited_agent').resolve(), pp_ov2.agent_dir)
	def test_project_paths_lru_retains_more_than_256_entries(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			pr.clear_registry_cache()
			for idx in range(280):
				p = base / f'p_{idx}'
				p.mkdir()
				pr.project_paths(p, exact_root=True)
			self.assertGreaterEqual(len(pr._PROJECT_PATHS_CACHE), 280)
	def test_refresh_known_overlay_links_uses_ttl_and_resets_on_clear(self) -> None:
		pr.clear_registry_cache()
		reg = pr.load_registry()
		with patch.object(pr, '_candidate_discovery_roots', wraps=pr._candidate_discovery_roots) as spy:
			first = pr._refresh_known_overlay_links(reg)
			second = pr._refresh_known_overlay_links(reg)
			self.assertEqual(first, second)
			self.assertEqual(1, spy.call_count)
			pr.clear_registry_cache()
			pr._refresh_known_overlay_links(reg)
			self.assertEqual(2, spy.call_count)
	def test_resolve_project_root_skips_host_overlay_scan_for_temp_subdirs(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'temp_proj'
			(proj / '\ua616').mkdir(parents=True)
			j_dir = proj / '\ua66e'
			j_dir.mkdir(parents=True)
			with patch.object(pr, '_refresh_known_overlay_links', side_effect=AssertionError('must not scan host overlays for temp dir')):
				self.assertEqual(proj.resolve(), pr.resolve_project_root(j_dir))
if '__main__' == __name__:
	unittest.main()
