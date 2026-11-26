# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import json
import os
import sys
import tempfile
import unittest
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from agent_tools import path_registry
from agent_tools.issues import repo_locator
from agent_tools.issues.workspace import IssueEvidenceWorkspace
def _make_git_config(repo_dir: Path, slug: str) -> Path:
	cfg = repo_dir / '.git/config'
	cfg.parent.mkdir(parents=True, exist_ok=True)
	cfg.write_text(f'[remote "origin"]\n\turl = https://github.com/{slug}.git\n', encoding='utf-8')
	return repo_dir.resolve()
# 2026-11-24
# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
# https://github.com/dmitry-ai/harness/issues/172
class RepoLocatorPerformanceTests(unittest.TestCase):
	def tearDown(self) -> None:
		path_registry.clear_registry_cache()
	def test_find_local_code_repo_discovers_direct_similar_project_peer_locally(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			base = Path(tmp).resolve()
			peer_a = base / 'peer_a'
			peer_b = base / 'peer_b'
			(peer_a / '_/\ua616').mkdir(parents=True)
			(peer_a / '_/\ua616/paths.json').write_text(json.dumps({'profile': 'dual_repo', 'similar_projects': [peer_b.as_posix()]}), encoding='utf-8')
			(peer_b / '_/\ua616').mkdir(parents=True)
			(peer_b / '_/\ua616/paths.json').write_text(json.dumps({'profile': 'dual_repo'}), encoding='utf-8')
			code_b = _make_git_config(peer_b / 'code', 'acme/peer-b')
			with patch.object(repo_locator, '_search_registry_and_roots', side_effect=AssertionError('must not scan global roots')):
				found = repo_locator.find_local_code_repo('acme/peer-b', project_root=peer_a)
			self.assertEqual(code_b, found)
	def test_find_local_code_repo_isolates_temp_project_from_host_search_roots(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'isolated_proj'
			(proj / '\ua616').mkdir(parents=True)
			with patch.object(repo_locator, '_search_registry_and_roots', side_effect=AssertionError('must not scan host roots for temp project')):
				found = repo_locator.find_local_code_repo('nonexistent-org/missing-repo', project_root=proj)
			self.assertIsNone(found)
	def test_find_tracked_child_issues_passes_code_repo_without_rescanning(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			proj = Path(tmp).resolve() / 'proj'
			code = _make_git_config(proj / 'code', 'acme/demo')
			ev_dir = proj / '_/\ua616/KB/Evidence/GitHub/acme__demo'
			ev_dir.mkdir(parents=True)
			(ev_dir / 'issue-20.json').write_text(json.dumps({'number': 20, 'state': 'closed', 'parent_number': 10, 'html_url': 'https://github.com/acme/demo/issues/20'}), encoding='utf-8')
			ws = IssueEvidenceWorkspace()
			with patch.object(ws, 'find_local_code_repo', side_effect=AssertionError('must reuse explicit code_repo')):
				children = ws.find_tracked_child_issues('acme/demo', 10, project_root=proj, code_repo=code)
			self.assertEqual([20], [c['number'] for c in children])
	def test_pruned_walk_skips_heavy_dirs_and_respects_ttl_cache_and_reset(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve() / 'search_root'
			valid = _make_git_config(root / 'proj/code', 'acme/valid')
			_make_git_config(root / 'node_modules/pkg', 'acme/in-node-modules')
			_make_git_config(root / 'proj/.git/nested_repo', 'acme/in-dot-git')
			_make_git_config(root / 'a/b/c/d/e/f/g/h/i/too_deep', 'acme/too-deep')
			walk_calls: list[str] = []
			real_walk = os.walk
			def spy_walk(top, *args, **kwargs):
				walk_calls.append(str(top))
				return real_walk(top, *args, **kwargs)
			with patch.object(path_registry, 'store_value', return_value=[str(root)]), patch.object(path_registry, '_candidate_discovery_roots', return_value=((), ())), patch.object(os, 'walk', side_effect=spy_walk):
				self.assertEqual(valid, repo_locator.find_local_code_repo('acme/valid'))
				self.assertEqual(1, len(walk_calls))
				self.assertEqual(valid, repo_locator.find_local_code_repo('acme/valid'))
				self.assertIsNone(repo_locator.find_local_code_repo('acme/in-node-modules'))
				self.assertIsNone(repo_locator.find_local_code_repo('acme/in-dot-git'))
				self.assertIsNone(repo_locator.find_local_code_repo('acme/too-deep'))
				self.assertIsNone(repo_locator.find_local_code_repo('acme/missing-slug'))
				self.assertEqual(1, len(walk_calls))
				fresh = _make_git_config(root / 'fresh_repo', 'acme/fresh')
				path_registry.clear_registry_cache()
				self.assertEqual(fresh, repo_locator.find_local_code_repo('acme/fresh'))
				self.assertEqual(2, len(walk_calls))
if '__main__' == __name__:
	unittest.main()
