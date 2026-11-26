# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from ..git_gate import run_git_read
from ..worktree_flow import git_config_file, prioritized_worktree_candidates
import os
import re
import tempfile
import time
# 2026-11-24
# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
# https://github.com/dmitry-ai/harness/issues/172
_GITHUB_SLUG_RE = re.compile(r'github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?(?:\s|$)', re.IGNORECASE)
_GLOBAL_INDEX_CACHE: dict[str, Any] = {'expires_at': 0.0, 'key': None, 'slug_map': {}}
_GLOBAL_INDEX_TTL_S = 30.0
_MAX_WALK_DEPTH = 8
_PRUNE_DIRS = frozenset({'.git', '.venv', '__pycache__', 'node_modules', 'venv', '\ua616', '\ua66e'})
# 2026-11-24
# "Decompose github_issue.py and issue_lifecycle.py into IssueMarkdownLinter, IssueEvidenceWorkspace, GitHubIssueService, and TurnIssueLifecycleAuditor with locked turn updates":
# https://github.com/dmitry-ai/harness/issues/77
_V2_CODE_RELS = ('\u2c0f/\u227b/\u2655/\u26ef', 'Artifacts/\u227b/Deliverables/\u26ef')
# 2026-11-24
# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
# https://github.com/dmitry-ai/harness/issues/172
# @used-by :func:`_append_project_paths()`
def _append_peer_repos(target: list[Path], peer: Path) -> None:
	from ..path_registry import project_paths
	try:
		pp_peer = project_paths(peer, exact_root=True)
		target.extend([*pp_peer.code_repos, *pp_peer.auxiliary_repos.values()])
	except (OSError, ValueError):
		pass
	_append_repo_roots(target, peer)
# @used-by :func:`_collect_local_repo_candidates()`
def _append_project_paths(target: list[Path], path: Path) -> None:
	from ..path_registry import project_paths
	try:
		pp = project_paths(path)
		target.extend([*pp.code_repos, *pp.auxiliary_repos.values()])
		# 2026-11-24
		# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
		# https://github.com/dmitry-ai/harness/issues/172
		for peer in pp._direct_similar_projects:
			_append_peer_repos(target, peer)
	except (OSError, ValueError):
		pass
# @used-by :func:`_append_peer_repos()`
# @used-by :func:`_collect_local_repo_candidates()`
def _append_repo_roots(target: list[Path], base: Path) -> None:
	target.extend([base, base / 'code', *(base / rel for rel in _V2_CODE_RELS)])
# 2026-11-24
# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
# https://github.com/dmitry-ai/harness/issues/172
# @used-by :func:`_search_registry_and_roots()`
def _build_global_slug_index(reg: Any, raw_roots: list[str]) -> dict[str, Path]:
	slug_map: dict[str, Path] = {}
	_index_discovery_roots(reg, slug_map)
	for raw_root in raw_roots:
		search_root = Path(raw_root)
		if search_root.is_dir():
			_index_dir_tree(search_root, slug_map)
	return slug_map
# 2026-11-24
# "Fix worktree scope resolution for new files in TDD classifier":
# https://github.com/dmitry-ai/harness/issues/188
# @used-by :func:`_collect_local_repo_candidates()`
def _initial_repo_candidates(repo_root: str | Path | None, cwd: Path, allow_cwd: bool) -> list[Path]:
	if allow_cwd:
		r = prioritized_worktree_candidates(repo_root, cwd=cwd)
	else:
		r = [Path(repo_root).resolve()] if None is not repo_root and str(repo_root).strip() else []
	return r
# @used-by :func:`find_local_code_repo()`
def _collect_local_repo_candidates(project_root: str | Path | None, source_files: list[tuple[Path, bytes]] | None, repo_root: str | Path | None) -> list[Path]:
	# 2026-11-24
	# "Fix worktree scope resolution for new files in TDD classifier":
	# https://github.com/dmitry-ai/harness/issues/188
	cwd = Path.cwd().resolve()
	allow_cwd = not (_is_isolated_temp_context(project_root, source_files, repo_root) and (not _is_under_tempdir(cwd)))
	cands: list[Path] = _initial_repo_candidates(repo_root, cwd, allow_cwd)
	if None is not project_root and str(project_root).strip():
		pr = Path(project_root).resolve()
		_append_project_paths(cands, pr)
		_append_repo_roots(cands, pr)
		_append_repo_roots(cands, pr.parent)
	for fpath, _ in source_files or []:
		resolved = fpath.resolve()
		_append_project_paths(cands, resolved)
		for anc in (resolved, *resolved.parents):
			_append_repo_roots(cands, anc)
	if allow_cwd:
		for anc in (cwd, *cwd.parents):
			_append_repo_roots(cands, anc)
	return cands
# 2026-11-24
# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
# https://github.com/dmitry-ai/harness/issues/172
# @used-by :func:`_register_repo_slugs()`
# @used-by :func:`agent_tools.tdd.mechanical.find_matching_mechanical_recipes()`
# @used-by :func:`origin_repo_slug()`
# @used-by :func:`repo_matches_slug()`
def _extract_config_slugs(code_repo: Path) -> list[str]:
	cfg_file = git_config_file(code_repo)
	r: list[str] = []
	if cfg_file.is_file():
		try:
			r = [m.group(1) for m in _GITHUB_SLUG_RE.finditer(cfg_file.read_text(encoding='utf-8', errors='replace'))]
		except OSError:
			r = []
	return r
# @used-by :func:`find_local_code_repo()`
def _first_matching_repo(cands: list[Path], repo: str, seen: set[Path]) -> Path | None:
	r = None
	for cand in cands:
		if cand not in seen:
			seen.add(cand)
			if cand.is_dir() and repo_matches_slug(cand, repo):
				r = cand
				break
	return r
# 2026-11-24
# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
# https://github.com/dmitry-ai/harness/issues/172
# @used-by :func:`_build_global_slug_index()`
def _index_dir_tree(search_root: Path, slug_map: dict[str, Path]) -> None:
	base_depth = len(search_root.parts)
	try:
		for dirpath, dirnames, filenames in os.walk(search_root, topdown=True):
			cur = Path(dirpath)
			if '.git' in dirnames or '.git' in filenames:
				_register_repo_slugs(cur, slug_map)
			if _MAX_WALK_DEPTH <= len(cur.parts) - base_depth:
				dirnames[:] = []
			else:
				dirnames[:] = [d for d in dirnames if d not in _PRUNE_DIRS]
	except OSError:
		pass
# @used-by :func:`_build_global_slug_index()`
def _index_discovery_roots(reg: Any, slug_map: dict[str, Path]) -> None:
	from ..path_registry import _candidate_discovery_roots, project_paths
	try:
		for d_root in _candidate_discovery_roots(reg)[1]:
			try:
				pp_d = project_paths(d_root, registry=reg)
				for cand in (*pp_d.code_repos, *pp_d.auxiliary_repos.values()):
					if cand.is_dir():
						_register_repo_slugs(cand, slug_map)
			except (OSError, ValueError):
				continue
	except (OSError, ValueError):
		pass
# @used-by :func:`_collect_local_repo_candidates()`
# @used-by :func:`find_local_code_repo()`
def _is_isolated_temp_context(project_root: str | Path | None, source_files: list[tuple[Path, bytes]] | None, repo_root: str | Path | None) -> bool:
	ctx: list[Path] = []
	if None is not project_root and str(project_root).strip():
		ctx.append(Path(project_root))
	if None is not repo_root and str(repo_root).strip():
		ctx.append(Path(repo_root))
	ctx.extend((fpath for fpath, _ in source_files or ()))
	return any((_is_under_tempdir(p) for p in ctx))
# @used-by :func:`_collect_local_repo_candidates()`
# @used-by :func:`_is_isolated_temp_context()`
def _is_under_tempdir(path: Path) -> bool:
	try:
		r = path.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
	except (OSError, ValueError):
		r = False
	return r
# @used-by :func:`_index_dir_tree()`
# @used-by :func:`_index_discovery_roots()`
def _register_repo_slugs(code_repo: Path, slug_map: dict[str, Path]) -> None:
	try:
		resolved = code_repo.resolve()
	except OSError:
		resolved = None
	if None is not resolved:
		for slug in _extract_config_slugs(resolved):
			slug_map.setdefault(slug.lower(), resolved)
# 2026-11-24
# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
# https://github.com/dmitry-ai/harness/issues/172
# @used-by :func:`find_local_code_repo()`
def _search_registry_and_roots(repo: str, seen: set[Path]) -> Path | None:
	from ..path_registry import load_registry, store_value
	reg = load_registry()
	raw_roots = list(store_value('code_repo_search_roots'))
	cache_key = (reg.source_path.as_posix(), tuple(raw_roots))
	now = time.monotonic()
	if cache_key != _GLOBAL_INDEX_CACHE['key'] or now >= _GLOBAL_INDEX_CACHE['expires_at']:
		_GLOBAL_INDEX_CACHE['slug_map'] = _build_global_slug_index(reg, raw_roots)
		_GLOBAL_INDEX_CACHE['key'] = cache_key
		_GLOBAL_INDEX_CACHE['expires_at'] = now + _GLOBAL_INDEX_TTL_S
	hit = _GLOBAL_INDEX_CACHE['slug_map'].get(repo.lower())
	return hit if None is not hit and hit.is_dir() and hit not in seen else None
# 2026-11-24
# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
# https://github.com/dmitry-ai/harness/issues/172
# @used-by :func:`agent_tools.path_registry.clear_registry_cache()`
def clear_repo_locator_cache() -> None:
	_GLOBAL_INDEX_CACHE['expires_at'] = 0.0
	_GLOBAL_INDEX_CACHE['key'] = None
	_GLOBAL_INDEX_CACHE['slug_map'] = {}
# @used-by :func:`agent_tools.repo_link_gate._validate_github_url()`
# @used-by :func:`agent_tools.repo_link_gate.resolve_local_github_blob()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.find_local_code_repo()`
# @used-by :meth:`test_repo_locator_perf.RepoLocatorPerformanceTests.test_find_local_code_repo_discovers_direct_similar_project_peer_locally()`
# @used-by :meth:`test_repo_locator_perf.RepoLocatorPerformanceTests.test_find_local_code_repo_isolates_temp_project_from_host_search_roots()`
# @used-by :meth:`test_repo_locator_perf.RepoLocatorPerformanceTests.test_pruned_walk_skips_heavy_dirs_and_respects_ttl_cache_and_reset()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_isolated_temp_project_ignores_unrelated_host_worktree_cwd()`
def find_local_code_repo(repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, *, repo_root: str | Path | None=None) -> Path | None:
	seen: set[Path] = set()
	r = _first_matching_repo(_collect_local_repo_candidates(project_root, source_files, repo_root), repo, seen)
	# 2026-11-24
	# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
	# https://github.com/dmitry-ai/harness/issues/172
	if None is r and (not _is_isolated_temp_context(project_root, source_files, repo_root)):
		r = _search_registry_and_roots(repo, seen)
	return r
# 2026-11-24
# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
# https://github.com/dmitry-ai/harness/issues/172
# @used-by :func:`agent_tools.repo_link_gate._enclosing_github_repo()`
# @used-by :func:`agent_tools.repo_tags.build_github_blob_url()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.origin_repo_slug()`
def origin_repo_slug(code_repo: Path) -> str | None:
	slugs = _extract_config_slugs(Path(code_repo))
	r = slugs[0] if slugs else None
	if None is r:
		proc = run_git_read(code_repo, ['remote', 'get-url', 'origin'], check=False)
		if 0 == proc.returncode:
			m = _GITHUB_SLUG_RE.search(proc.stdout.decode('utf-8', errors='replace').strip())
			r = m.group(1) if m else None
	return r
# 2026-11-24
# "Optimize local GitHub repository discovery with pruned walk and TTL cache":
# https://github.com/dmitry-ai/harness/issues/172
# @used-by :func:`_first_matching_repo()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.repo_matches_slug()`
def repo_matches_slug(code_repo: Path, repo: str) -> bool:
	target = repo.lower()
	return any((target == slug.lower() for slug in _extract_config_slugs(code_repo)))
