# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/77
from __future__ import annotations
from pathlib import Path
import re
from ..git_gate import run_git_read
from ..worktree_flow import git_config_file, prioritized_worktree_candidates
_V2_CODE_RELS = ('\u2c0f/\u227b/\u2655/\u26ef', 'Artifacts/\u227b/Deliverables/\u26ef')
def _append_project_paths(target: list[Path], path: Path) -> None:
	from ..path_registry import project_paths
	try:
		pp = project_paths(path)
		target.extend([*pp.code_repos, *pp.auxiliary_repos.values()])
	except (OSError, ValueError):
		pass
def _append_repo_roots(target: list[Path], base: Path) -> None:
	target.extend([base, base / 'code', *(base / rel for rel in _V2_CODE_RELS)])
def _collect_local_repo_candidates(project_root: str | Path | None, source_files: list[tuple[Path, bytes]] | None, repo_root: str | Path | None) -> list[Path]:
	cands: list[Path] = prioritized_worktree_candidates(repo_root)
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
	cwd = Path.cwd().resolve()
	for anc in (cwd, *cwd.parents):
		_append_repo_roots(cands, anc)
	return cands
def _first_matching_repo(cands: list[Path], repo: str, seen: set[Path]) -> Path | None:
	r = None
	for cand in cands:
		if cand not in seen:
			seen.add(cand)
			if cand.is_dir() and repo_matches_slug(cand, repo):
				r = cand
				break
	return r
def _search_code_roots(raw_roots: list[str], repo: str, seen: set[Path]) -> Path | None:
	r = None
	for raw_root in raw_roots:
		search_root = Path(raw_root)
		if not search_root.is_dir():
			continue
		try:
			for pat in ('*/.git/config', '**/code/.git/config', '**/\u26ef/.git/config', '**/\U0001d412/.git/config'):
				r = _first_matching_repo([cfg.parent.parent.resolve() for cfg in search_root.glob(pat)], repo, seen)
				if None is not r:
					break
		except OSError:
			pass
		if None is not r:
			break
	return r
def _search_registry_and_roots(repo: str, seen: set[Path]) -> Path | None:
	from ..path_registry import _candidate_discovery_roots, load_registry, project_paths, store_value
	r = None
	try:
		reg = load_registry()
		for d_root in _candidate_discovery_roots(reg)[1]:
			try:
				pp_d = project_paths(d_root, registry=reg)
				r = _first_matching_repo([*pp_d.code_repos, *pp_d.auxiliary_repos.values()], repo, seen)
				if None is not r:
					break
			except (OSError, ValueError):
				continue
	except (OSError, ValueError):
		pass
	if None is r:
		r = _search_code_roots(store_value('code_repo_search_roots'), repo, seen)
	return r
def find_local_code_repo(repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, *, repo_root: str | Path | None=None) -> Path | None:
	seen: set[Path] = set()
	r = _first_matching_repo(_collect_local_repo_candidates(project_root, source_files, repo_root), repo, seen)
	if None is r:
		r = _search_registry_and_roots(repo, seen)
	return r
def origin_repo_slug(code_repo: Path) -> str | None:
	r = None
	cfg_file = git_config_file(Path(code_repo))
	if cfg_file.is_file():
		try:
			cm = re.search('github\\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\\.git)?/?(?:\\s|$)', cfg_file.read_text(encoding='utf-8', errors='replace'))
			r = cm.group(1) if cm else None
		except OSError:
			pass
	if None is r:
		proc = run_git_read(code_repo, ['remote', 'get-url', 'origin'], check=False)
		if 0 == proc.returncode:
			m = re.search('github\\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\\.git)?$', proc.stdout.decode('utf-8', errors='replace').strip())
			r = m.group(1) if m else None
	return r
def repo_matches_slug(code_repo: Path, repo: str) -> bool:
	cfg_file = git_config_file(code_repo)
	r = False
	if cfg_file.is_file():
		try:
			r = bool(re.search(f'github\\.com[:/]{re.escape(repo)}(?:\\.git)?/?(?:\\s|$)', cfg_file.read_text(encoding='utf-8', errors='replace'), re.I))
		except OSError:
			r = False
	return r
