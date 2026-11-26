# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Meta.TimestampFormatter import TimestampFormatter
import json
import tempfile
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class ProjectIdentity:
	PROJECTS_DIR_CACHE: dict[tuple[str, int], list[dict[str, Any]]] = {}
	# @used-by :func:`agent_tools.meta.identity.resolve_project_identity()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :mod:`Df.Harness.Meta.Builders`
	def __init__(self, root: str | Path, *, ag_paths: dict[str, Any] | None=None, project_id: str | None=None) -> None:
		self.__root = root
		self.__ag_paths = ag_paths
		self.__project_id = project_id
	# @used-by :func:`agent_tools.meta.identity.resolve_project_identity()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :mod:`Df.Harness.Meta.Builders`
	def resolve(self) -> dict[str, str]:
		from agent_tools.path_registry import canonicalize_root_dir
		canon = canonicalize_root_dir(self.__root)
		pdirs = ProjectIdentity.antigravity_project_dirs(self.__ag_paths, canon_root=canon)
		name = ProjectIdentity.__lookup_name_by_project_id(pdirs, canon, self.__project_id) or ProjectIdentity.__lookup_name_from_project_dirs(pdirs, canon) or ProjectIdentity.__lookup_name_from_project_json(canon) or canon.name or TimestampFormatter.posix_path(canon)
		return {'Name': name, 'Path': TimestampFormatter.posix_path(canon)}
	# @used-by :meth:`ProjectIdentity.resolve()`
	@staticmethod
	def __lookup_name_by_project_id(pdirs: list[Path], canon: Path, project_id: str | None) -> str | None:
		from agent_tools.platforms.antigravity import _project_item_matches_root
		r: str | None = None
		pid = project_id.strip() if isinstance(project_id, str) else ''
		if pid:
			for pdir in pdirs:
				cand = pdir / f'{pid}.json'
				data = ProjectIdentity.__read_json_dict(cand) if cand.is_file() else None
				if None is not data and isinstance(data.get('name'), str) and data['name'].strip():
					matched, _ = _project_item_matches_root(data, canon)
					if matched:
						r = data['name'].strip()
						break
		return r
	# @used-by :meth:`ProjectIdentity.resolve()`
	@staticmethod
	def __lookup_name_from_project_dirs(pdirs: list[Path], canon: Path) -> str | None:
		from agent_tools.platforms.antigravity import _project_item_matches_root
		r, relocated = (None, None)
		for item in (it for pdir in pdirs for it in ProjectIdentity.load_projects_dir_items(pdir)):
			matched, is_reloc = _project_item_matches_root(item, canon)
			raw_name = item.get('name')
			if matched and isinstance(raw_name, str) and raw_name.strip():
				if not is_reloc:
					r = raw_name.strip()
					break
				if None is relocated:
					relocated = raw_name.strip()
		return r if None is not r else relocated
	# @used-by :meth:`ProjectIdentity.resolve()`
	@staticmethod
	def __lookup_name_from_project_json(canon: Path) -> str | None:
		from agent_tools.path_registry import project_paths
		r: str | None = None
		try:
			pj = project_paths(canon, exact_root=True).project_json
			pdata = ProjectIdentity.__read_json_dict(pj) if pj.is_file() else None
		except (OSError, ValueError):
			pdata = None
		if None is not pdata:
			for key in ('project_name', 'name', 'domain', 'title'):
				val = pdata.get(key)
				if isinstance(val, str) and val.strip():
					r = val.strip()
					break
		return r
	# @used-by :meth:`ProjectIdentity.antigravity_project_dirs()`
	@staticmethod
	def __push_project_dir(dirs: list[Path], seen: set[str], p_val: str | Path | None) -> None:
		if p_val:
			p = Path(p_val)
			if p.is_dir():
				resolved = p.resolve()
				key = resolved.as_posix().lower()
				if key not in seen:
					seen.add(key)
					dirs.append(resolved)
	# @used-by :meth:`ProjectIdentity.__lookup_name_by_project_id()`
	# @used-by :meth:`ProjectIdentity.__lookup_name_from_project_json()`
	# @used-by :meth:`ProjectIdentity.load_projects_dir_items()`
	@staticmethod
	def __read_json_dict(path: Path) -> dict[str, Any] | None:
		try:
			data = json.loads(path.read_text(encoding='utf-8-sig'))
			r: dict[str, Any] | None = data if isinstance(data, dict) else None
		except (OSError, ValueError):
			r = None
		return r
	# @used-by :func:`agent_tools.meta.identity._antigravity_project_dirs()`
	# @used-by :meth:`ProjectIdentity.resolve()`
	@staticmethod
	def antigravity_project_dirs(ag_paths: dict[str, Any] | None=None, *, canon_root: Path | None=None) -> list[Path]:
		dirs: list[Path] = []
		seen: set[str] = set()
		if isinstance(ag_paths, dict):
			ProjectIdentity.__push_project_dir(dirs, seen, ag_paths.get('projects_dir'))
		if None is canon_root or (not ProjectIdentity.is_temp_path(canon_root)):
			try:
				from agent_tools.runtime import platform_instances
				for inst in platform_instances('antigravity', include_disabled=True).values():
					ProjectIdentity.__push_project_dir(dirs, seen, (inst.get('system_paths') or {}).get('projects_dir'))
			except Exception:
				pass
		return dirs
	# @used-by :func:`agent_tools.meta.identity._is_temp_path()`
	# @used-by :meth:`ProjectIdentity.antigravity_project_dirs()`
	@staticmethod
	def is_temp_path(path: Path) -> bool:
		try:
			r = path.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
		except OSError:
			r = False
		return r
	# @used-by :func:`agent_tools.meta.identity._load_projects_dir_items()`
	# @used-by :meth:`ProjectIdentity.__lookup_name_from_project_dirs()`
	@staticmethod
	def load_projects_dir_items(pdir: Path) -> list[dict[str, Any]]:
		try:
			mtime_ns = pdir.stat().st_mtime_ns
		except OSError:
			r: list[dict[str, Any]] = []
		else:
			cache_key = (pdir.as_posix().lower(), mtime_ns)
			cached = ProjectIdentity.PROJECTS_DIR_CACHE.get(cache_key)
			if None is not cached:
				r = cached
			else:
				if 64 < len(ProjectIdentity.PROJECTS_DIR_CACHE):
					ProjectIdentity.PROJECTS_DIR_CACHE.clear()
				items = [item for pf in sorted(pdir.glob('*.json')) if None is not (item := ProjectIdentity.__read_json_dict(pf))]
				ProjectIdentity.PROJECTS_DIR_CACHE[cache_key] = items
				r = items
		return r
	# @used-by :func:`agent_tools.meta.identity._resolve_ag_paths_safe()`
	# @used-by :mod:`Df.Harness.Meta.Builders`
	@staticmethod
	def resolve_ag_paths_safe(backend=None, *, instance=None, conversation_id=None) -> dict[str, Any] | None:
		try:
			from agent_tools.runtime import resolve_antigravity_paths, settings
			r = resolve_antigravity_paths(backend=backend, instance=instance, conversation_id=conversation_id, config=settings())
		except Exception:
			r = None
		return r
	# @used-by :func:`agent_tools.meta.identity._resolve_codex_paths_safe()`
	# @used-by :mod:`Df.Harness.Meta.Builders`
	@staticmethod
	def resolve_codex_paths_safe(backend=None, *, instance=None, conversation_id=None) -> dict[str, Any] | None:
		try:
			from agent_tools.runtime import platform_settings, resolve_codex_paths
			r = resolve_codex_paths(backend, instance=instance, conversation_id=conversation_id, codex_cfg=platform_settings('codex'))
		except Exception:
			r = None
		return r
