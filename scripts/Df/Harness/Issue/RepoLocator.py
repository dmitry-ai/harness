# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Core.lib.array.first import df_first
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.lib.worktree import dfh_git_config_file
import os
import re
import tempfile
import time
_GITHUB_SLUG_RE = re.compile(r'github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?(?:\s|$)', re.IGNORECASE)
_GLOBAL_INDEX_TTL_S = 30.0
_MAX_WALK_DEPTH = 8
_PRUNE_DIRS = frozenset({'.git', '.venv', '__pycache__', 'node_modules', 'venv', '\ua616', '\ua66e'})
V2_CODE_RELS = ('\u2c0f/\u227b/\u2655/\u26ef', 'Artifacts/\u227b/Deliverables/\u26ef')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class RepoLocator:
	__global_cache: dict[str, Any] = {'expires_at': 0.0, 'key': None, 'slug_map': {}}
	# @used-by :func:`agent_tools.issues.repo_locator.find_local_code_repo()`
	# @used-by :func:`agent_tools.issues.repo_locator.origin_repo_slug()`
	# @used-by :func:`agent_tools.issues.repo_locator.repo_matches_slug()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.find_local_code_repo()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.origin_repo_slug()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_dirty_scanner_read_cache_and_locator()`
	def __init__(self, *, search_fn=None, git_read_fn=None) -> None:
		self.__search_fn = search_fn
		self.__git_read_fn = git_read_fn
	# @used-by :meth:`RepoLocator.__append_project_paths()`
	@classmethod
	def __append_peer_repos(cls, target: list[Path], peer: Path) -> None:
		from agent_tools.path_registry import project_paths
		try:
			pp_peer = project_paths(peer, exact_root=True)
			target.extend([*pp_peer.code_repos, *pp_peer.auxiliary_repos.values()])
		except (OSError, ValueError):
			pass
		cls.__append_repo_roots(target, peer)
	# @used-by :meth:`RepoLocator.__collect_candidates()`
	@classmethod
	def __append_project_paths(cls, target: list[Path], path: Path) -> None:
		from agent_tools.path_registry import project_paths
		try:
			pp = project_paths(path)
			target.extend([*pp.code_repos, *pp.auxiliary_repos.values()])
			for peer in pp._direct_similar_projects:
				cls.__append_peer_repos(target, peer)
		except (OSError, ValueError):
			pass
	# @used-by :meth:`RepoLocator.__append_peer_repos()`
	# @used-by :meth:`RepoLocator.__collect_candidates()`
	@staticmethod
	def __append_repo_roots(target: list[Path], base: Path) -> None:
		target.extend([base, base / 'code', *(base / rel for rel in V2_CODE_RELS)])
	# @used-by :meth:`RepoLocator.search_registry_and_roots()`
	@classmethod
	def __build_global_slug_index(cls, reg: Any, raw_roots: list[str]) -> dict[str, Path]:
		slug_map: dict[str, Path] = {}
		cls.__index_discovery_roots(reg, slug_map)
		for raw_root in raw_roots:
			search_root = Path(raw_root)
			if search_root.is_dir():
				cls.__index_dir_tree(search_root, slug_map)
		return slug_map
	# @used-by :meth:`RepoLocator.find_local_code_repo()`
	@classmethod
	def __collect_candidates(cls, project_root: str | Path | None, source_files: list[tuple[Path, bytes]] | None, repo_root: str | Path | None) -> list[Path]:
		cwd = Path.cwd().resolve()
		allow_cwd = not (cls.__is_isolated_temp(project_root, source_files, repo_root) and (not cls.__is_under_tempdir(cwd)))
		cands: list[Path] = cls.__initial_candidates(repo_root, cwd, allow_cwd)
		if None is not project_root and str(project_root).strip():
			pr = Path(project_root).resolve()
			cls.__append_project_paths(cands, pr)
			cls.__append_repo_roots(cands, pr)
			cls.__append_repo_roots(cands, pr.parent)
		for fpath, _ in source_files or []:
			resolved = fpath.resolve()
			cls.__append_project_paths(cands, resolved)
			for anc in (resolved, *resolved.parents):
				cls.__append_repo_roots(cands, anc)
		if allow_cwd:
			for anc in (cwd, *cwd.parents):
				cls.__append_repo_roots(cands, anc)
		return cands
	# @used-by :meth:`RepoLocator.origin_repo_slug()`
	@staticmethod
	def __config_may_have_origin(code_repo: Path) -> bool:
		cfg_file = dfh_git_config_file(code_repo)
		r = True
		if cfg_file.is_file():
			try:
				low = cfg_file.read_text(encoding='utf-8', errors='replace').lower()
				r = '[remote "origin"]' in low or '[include' in low
			except OSError:
				r = True
		return r
	# @used-by :meth:`RepoLocator.find_local_code_repo()`
	@classmethod
	def __first_matching(cls, cands: list[Path], repo: str, seen: set[Path]) -> Path | None:
		r = None
		for cand in cands:
			if cand not in seen:
				seen.add(cand)
				if cand.is_dir() and cls.repo_matches_slug(cand, repo):
					r = cand
					break
		return r
	# @used-by :meth:`RepoLocator.__build_global_slug_index()`
	@classmethod
	def __index_dir_tree(cls, search_root: Path, slug_map: dict[str, Path]) -> None:
		base_depth = len(search_root.parts)
		try:
			for dirpath, dirnames, filenames in os.walk(search_root, topdown=True):
				cur = Path(dirpath)
				if '.git' in dirnames or '.git' in filenames:
					cls.__register_repo_slugs(cur, slug_map)
				if _MAX_WALK_DEPTH <= len(cur.parts) - base_depth:
					dirnames[:] = []
				else:
					dirnames[:] = [d for d in dirnames if d not in _PRUNE_DIRS]
		except OSError:
			pass
	# @used-by :meth:`RepoLocator.__build_global_slug_index()`
	@classmethod
	def __index_discovery_roots(cls, reg: Any, slug_map: dict[str, Path]) -> None:
		from agent_tools.path_registry import _candidate_discovery_roots, project_paths
		try:
			for d_root in _candidate_discovery_roots(reg)[1]:
				try:
					pp_d = project_paths(d_root, registry=reg)
					for cand in (*pp_d.code_repos, *pp_d.auxiliary_repos.values()):
						if cand.is_dir():
							cls.__register_repo_slugs(cand, slug_map)
				except (OSError, ValueError):
					continue
		except (OSError, ValueError):
			pass
	# @used-by :meth:`RepoLocator.__collect_candidates()`
	@staticmethod
	def __initial_candidates(repo_root: str | Path | None, cwd: Path, allow_cwd: bool) -> list[Path]:
		cands: list[Path] = [Path(repo_root).resolve()] if None is not repo_root and str(repo_root).strip() else []
		if allow_cwd:
			for anc in (cwd, *cwd.parents):
				if (anc / '.git').is_file():
					cands.append(anc)
					break
		return cands
	# @used-by :meth:`RepoLocator.__collect_candidates()`
	# @used-by :meth:`RepoLocator.find_local_code_repo()`
	@classmethod
	def __is_isolated_temp(cls, project_root: str | Path | None, source_files: list[tuple[Path, bytes]] | None, repo_root: str | Path | None) -> bool:
		ctx: list[Path] = []
		if None is not project_root and str(project_root).strip():
			ctx.append(Path(project_root))
		if None is not repo_root and str(repo_root).strip():
			ctx.append(Path(repo_root))
		ctx.extend((fpath for fpath, _ in source_files or ()))
		return any((cls.__is_under_tempdir(p) for p in ctx))
	# @used-by :meth:`RepoLocator.__collect_candidates()`
	# @used-by :meth:`RepoLocator.__is_isolated_temp()`
	@staticmethod
	def __is_under_tempdir(path: Path) -> bool:
		try:
			r = path.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
		except (OSError, ValueError):
			r = False
		return r
	# @used-by :meth:`RepoLocator.__index_dir_tree()`
	# @used-by :meth:`RepoLocator.__index_discovery_roots()`
	@classmethod
	def __register_repo_slugs(cls, code_repo: Path, slug_map: dict[str, Path]) -> None:
		try:
			resolved = code_repo.resolve()
		except OSError:
			resolved = None
		if None is not resolved:
			for slug in cls.extract_config_slugs(resolved):
				slug_map.setdefault(slug.lower(), resolved)
	# @used-by :func:`agent_tools.issues.repo_locator.clear_repo_locator_cache()`
	@classmethod
	def clear_cache(cls) -> None:
		cls.__global_cache['expires_at'] = 0.0
		cls.__global_cache['key'] = None
		cls.__global_cache['slug_map'] = {}
	# @used-by :func:`agent_tools.issues.repo_locator._extract_config_slugs()`
	# @used-by :meth:`RepoLocator.__register_repo_slugs()`
	# @used-by :meth:`RepoLocator.origin_repo_slug()`
	# @used-by :meth:`RepoLocator.repo_matches_slug()`
	@staticmethod
	def extract_config_slugs(code_repo: Path) -> list[str]:
		cfg_file = dfh_git_config_file(code_repo)
		r: list[str] = []
		if cfg_file.is_file():
			try:
				r = [m.group(1) for m in _GITHUB_SLUG_RE.finditer(cfg_file.read_text(encoding='utf-8', errors='replace'))]
			except OSError:
				r = []
		return r
	# @used-by :func:`agent_tools.issues.repo_locator.find_local_code_repo()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.find_local_code_repo()`
	def find_local_code_repo(self, repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, *, repo_root: str | Path | None=None) -> Path | None:
		seen: set[Path] = set()
		r = self.__first_matching(self.__collect_candidates(project_root, source_files, repo_root), repo, seen)
		if None is r and (not self.__is_isolated_temp(project_root, source_files, repo_root)):
			r = self.__search_fn(repo, seen) if None is not self.__search_fn else self.search_registry_and_roots(repo, seen)
		return r
	# @used-by :func:`agent_tools.issues.repo_locator.origin_repo_slug()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.origin_repo_slug()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_dirty_scanner_read_cache_and_locator()`
	def origin_repo_slug(self, code_repo: Path) -> str | None:
		slugs = self.extract_config_slugs(Path(code_repo))
		r = df_first(slugs)
		if None is r and self.__config_may_have_origin(Path(code_repo)):
			proc = self.__git_read_fn(code_repo, ['remote', 'get-url', 'origin'], check=False) if None is not self.__git_read_fn else RepoGate(Path(code_repo)).run_read(['remote', 'get-url', 'origin'], check=False)
			if 0 == proc.returncode:
				m = _GITHUB_SLUG_RE.search(proc.stdout.decode('utf-8', errors='replace').strip())
				r = m.group(1) if m else None
		return r
	# @used-by :func:`agent_tools.issues.repo_locator.repo_matches_slug()`
	# @used-by :meth:`Df.Harness.Issue.EvidenceWorkspace.EvidenceWorkspace.repo_matches_slug()`
	# @used-by :meth:`RepoLocator.__first_matching()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_dirty_scanner_read_cache_and_locator()`
	@classmethod
	def repo_matches_slug(cls, code_repo: Path, repo: str) -> bool:
		target = repo.lower()
		return any((target == slug.lower() for slug in cls.extract_config_slugs(code_repo)))
	# @used-by :func:`agent_tools.issues.repo_locator._search_registry_and_roots()`
	# @used-by :meth:`RepoLocator.find_local_code_repo()`
	@classmethod
	def search_registry_and_roots(cls, repo: str, seen: set[Path]) -> Path | None:
		from agent_tools.path_registry import load_registry, store_value
		reg = load_registry()
		raw_roots = list(store_value('code_repo_search_roots'))
		cache_key = (reg.source_path.as_posix(), tuple(raw_roots))
		now = time.monotonic()
		if cache_key != cls.__global_cache['key'] or now >= cls.__global_cache['expires_at']:
			cls.__global_cache['slug_map'] = cls.__build_global_slug_index(reg, raw_roots)
			cls.__global_cache['key'] = cache_key
			cls.__global_cache['expires_at'] = now + _GLOBAL_INDEX_TTL_S
		hit = cls.__global_cache['slug_map'].get(repo.lower())
		return hit if None is not hit and hit.is_dir() and hit not in seen else None
