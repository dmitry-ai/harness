# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/170
from __future__ import annotations
from pathlib import Path
from typing import Any
from .formatting import posix_path
import json
import tempfile
_PROJECTS_DIR_CACHE: dict[tuple[str, int], list[dict[str, Any]]] = {}
def _antigravity_project_dirs(ag_paths: dict[str, Any] | None=None, *, canon_root: Path | None=None) -> list[Path]:
	dirs: list[Path] = []
	seen: set[str] = set()
	if isinstance(ag_paths, dict):
		_push_project_dir(dirs, seen, ag_paths.get('projects_dir'))
	if None is canon_root or (not _is_temp_path(canon_root)):
		try:
			from ..runtime import platform_instances
			for inst in platform_instances('antigravity', include_disabled=True).values():
				_push_project_dir(dirs, seen, (inst.get('system_paths') or {}).get('projects_dir'))
		except Exception:
			pass
	return dirs
def _is_temp_path(path: Path) -> bool:
	try:
		tmp_root = Path(tempfile.gettempdir()).resolve()
		r = path.resolve().is_relative_to(tmp_root)
	except OSError:
		r = False
	return r
def _load_projects_dir_items(pdir: Path) -> list[dict[str, Any]]:
	try:
		mtime_ns = pdir.stat().st_mtime_ns
	except OSError:
		r: list[dict[str, Any]] = []
	else:
		cache_key = (pdir.as_posix().lower(), mtime_ns)
		cached = _PROJECTS_DIR_CACHE.get(cache_key)
		if None is not cached:
			r = cached
		else:
			if 64 < len(_PROJECTS_DIR_CACHE):
				_PROJECTS_DIR_CACHE.clear()
			loaded = (_read_json_dict(pf) for pf in sorted(pdir.glob('*.json')))
			items = [item for item in loaded if None is not item]
			_PROJECTS_DIR_CACHE[cache_key] = items
			r = items
	return r
def _lookup_name_by_project_id(pdirs: list[Path], canon: Path, project_id: str | None) -> str | None:
	from ..platforms.antigravity import _project_item_matches_root
	r: str | None = None
	pid = project_id.strip() if isinstance(project_id, str) else ''
	if pid:
		for pdir in pdirs:
			cand = pdir / f'{pid}.json'
			data = _read_json_dict(cand) if cand.is_file() else None
			if None is not data and isinstance(data.get('name'), str) and data['name'].strip():
				matched, _ = _project_item_matches_root(data, canon)
				if matched:
					r = data['name'].strip()
					break
	return r
def _lookup_name_from_project_dirs(pdirs: list[Path], canon: Path) -> str | None:
	from ..platforms.antigravity import _project_item_matches_root
	r: str | None = None
	relocated: str | None = None
	for item in (it for pdir in pdirs for it in _load_projects_dir_items(pdir)):
		matched, is_reloc = _project_item_matches_root(item, canon)
		raw_name = item.get('name')
		if matched and isinstance(raw_name, str) and raw_name.strip():
			if not is_reloc:
				r = raw_name.strip()
				break
			if None is relocated:
				relocated = raw_name.strip()
	return r if None is not r else relocated
def _lookup_name_from_project_json(canon: Path) -> str | None:
	from ..path_registry import project_paths
	r: str | None = None
	try:
		pj = project_paths(canon, exact_root=True).project_json
		pdata = _read_json_dict(pj) if pj.is_file() else None
	except (OSError, ValueError):
		pdata = None
	if None is not pdata:
		for key in ('project_name', 'name', 'domain', 'title'):
			val = pdata.get(key)
			if isinstance(val, str) and val.strip():
				r = val.strip()
				break
	return r
def _push_project_dir(dirs: list[Path], seen: set[str], p_val: str | Path | None) -> None:
	if p_val:
		p = Path(p_val)
		if p.is_dir():
			resolved = p.resolve()
			key = resolved.as_posix().lower()
			if key not in seen:
				seen.add(key)
				dirs.append(resolved)
def _read_json_dict(path: Path) -> dict[str, Any] | None:
	try:
		data = json.loads(path.read_text(encoding='utf-8-sig'))
		r: dict[str, Any] | None = data if isinstance(data, dict) else None
	except (OSError, ValueError):
		r = None
	return r
def _resolve_ag_paths_safe(backend=None, *, instance=None, conversation_id=None) -> dict[str, Any] | None:
	try:
		from ..runtime import resolve_antigravity_paths, settings
		r = resolve_antigravity_paths(backend=backend, instance=instance, conversation_id=conversation_id, config=settings())
	except Exception:
		r = None
	return r
def _resolve_codex_paths_safe(backend=None, *, instance=None, conversation_id=None) -> dict[str, Any] | None:
	try:
		from ..runtime import platform_settings, resolve_codex_paths
		r = resolve_codex_paths(backend, instance=instance, conversation_id=conversation_id, codex_cfg=platform_settings('codex'))
	except Exception:
		r = None
	return r
def resolve_project_identity(root: str | Path, *, ag_paths: dict[str, Any] | None=None, project_id: str | None=None) -> dict[str, str]:
	from ..path_registry import canonicalize_root_dir
	canon = canonicalize_root_dir(root)
	pdirs = _antigravity_project_dirs(ag_paths, canon_root=canon)
	name = _lookup_name_by_project_id(pdirs, canon, project_id) or _lookup_name_from_project_dirs(pdirs, canon) or _lookup_name_from_project_json(canon) or canon.name or posix_path(canon)
	return {'Name': name, 'Path': posix_path(canon)}
