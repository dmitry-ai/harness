# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
from Df.Harness.Path.CacheStore import CacheStore
from Df.Harness.lib.path_schema import dfh_validate_similar_project_groups
from Df.Harness.lib.path_state import CODE_ANCHOR
from Df.Harness.lib.path_template import dfh_escape_template_literal, dfh_expand_structure, dfh_expand_template, dfh_infer_harness_anchor, dfh_path_key, dfh_validate_string_list, dfh_validate_string_map, dfh_validate_variables_map
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class Registry:
	# @used-by :func:`Df.Harness.lib.path_resolve.dfh_load_registry()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_path_subsystem_classes()`
	def __init__(self, source_path: Path, raw: dict[str, Any], *, primary: Path | None=None, env: dict[str, str] | None=None) -> None:
		self.source_path = Path(source_path).resolve()
		self.env = dict(env) if None is not env else None
		if not isinstance(raw, dict) or 1 != raw.get('version'):
			raise ValueError(f'{self.source_path.name} requires version 1')
		self.__init_variables(raw, primary)
		self.__init_core_maps(raw)
		self.__init_overlays_and_profiles(raw)
	# @used-by :meth:`Registry.__init_variables()`
	def __anchor_overrides(self, variables: dict[str, str]) -> dict[str, str]:
		configured = dfh_expand_template(variables['HARNESS_CODE'], variables, env=self.env, normalize=True) if 'HARNESS_CODE' in variables else ''
		if dfh_path_key(self.anchor_code) != dfh_path_key(configured) or dfh_path_key(self.anchor_code) != dfh_path_key(CODE_ANCHOR):
			anchor_root, anchor_meta, anchor_ver = dfh_infer_harness_anchor(self.anchor_code)
			overrides = {'HARNESS_CODE': dfh_escape_template_literal(self.anchor_code.as_posix()), 'HARNESS_META': dfh_escape_template_literal(anchor_meta.as_posix()), 'HARNESS_ROOT': dfh_escape_template_literal(anchor_root.as_posix())}
			if 1 == anchor_ver and 'HARNESS_CLEANUP_LOG_DIR' in variables:
				overrides['HARNESS_CLEANUP_LOG_DIR'] = dfh_escape_template_literal((anchor_meta / 'Data/Log/cleanup').as_posix())
			r = {**variables, **overrides}
		else:
			r = variables
		return r
	# @used-by :meth:`Registry.__resolve_profile_chain()`
	def __build_profile_spec(self, name: str, cfg: dict[str, Any], base: dict[str, Any], fs_ver: int, j_ver: int) -> dict[str, Any]:
		prof_tools = deepcopy(cfg.get('tools') or {})
		if not isinstance(prof_tools, dict):
			raise ValueError(f'project_profiles.{name}.tools must be an object')
		r = {'auxiliary_repos': {**base['auxiliary_repos'], **dfh_validate_string_map(cfg.get('auxiliary_repos'), f'project_profiles.{name}.auxiliary_repos')}, 'fs_version': fs_ver, 'journal_version': j_ver, 'paths': {**base['paths'], **dfh_validate_string_map(cfg.get('paths'), f'project_profiles.{name}.paths')}, 'tools': {**base['tools'], **prof_tools}, 'variables': {**base['variables'], **dfh_validate_variables_map(cfg.get('variables'), f'project_profiles.{name}.variables')}}
		for key in ('code_repos', 'journal_legacy_fallbacks', 'linked_roots', 'similar_projects'):
			vals = dfh_validate_string_list(cfg.get(key), f'project_profiles.{name}.{key}')
			r[key] = vals if key in cfg else list(base[key])
		return r
	# @used-by :meth:`Registry.__init__()`
	def __init_core_maps(self, raw: dict[str, Any]) -> None:
		v = self.raw_variables
		if not isinstance(raw.get('tools'), dict):
			raise ValueError('paths.json requires a tools object')
		self.tools = dfh_expand_structure(raw['tools'], v, env=self.env)
		if not isinstance(raw.get('harness_stores'), dict):
			raise ValueError('paths.json requires a harness_stores object')
		self.harness_stores = dfh_expand_structure(raw['harness_stores'], v, env=self.env)
		self.workspace_overrides = self.__parse_workspace_overrides(raw.get('workspace_overrides') or {})
		raw_untracked = dfh_validate_string_list(raw.get('untracked_workspaces'), 'paths.json untracked_workspaces')
		self.untracked_workspaces: frozenset[str] = frozenset((dfh_path_key(Path(os.path.abspath(dfh_expand_template(item, v, env=self.env, normalize=True)))) for item in raw_untracked))
		raw_reloc = dfh_validate_string_map(raw.get('relocations') or {}, 'paths.json relocations')
		self.relocations = {dfh_path_key(dfh_expand_template(src, v, env=self.env, normalize=True)): dfh_expand_template(dst, v, env=self.env, normalize=True) for src, dst in raw_reloc.items()}
	# @used-by :meth:`Registry.__init__()`
	def __init_overlays_and_profiles(self, raw: dict[str, Any]) -> None:
		v = self.raw_variables
		raw_plats = raw.get('platform_layouts') or {}
		if not isinstance(raw_plats, dict):
			raise ValueError('paths.json platform_layouts must be an object')
		self.platform_layouts = deepcopy(raw_plats)
		raw_overlays = raw.get('project_overlays') or {}
		if not isinstance(raw_overlays, dict):
			raise ValueError('paths.json project_overlays must be an object')
		self.overlay_candidates = [dfh_expand_template(c, v, env=self.env, normalize=True) for c in dfh_validate_string_list(raw_overlays.get('candidates') or ['.agents/paths.json'], 'project_overlays.candidates')]
		self.overlay_discovery_roots = [dfh_expand_template(r, v, env=self.env, normalize=True) for r in dfh_validate_string_list(raw_overlays.get('discovery_roots') or [], 'project_overlays.discovery_roots')]
		self.overlay_discovery_globs = [dfh_expand_template(g, v, env=self.env, normalize=True) for g in dfh_validate_string_list(raw_overlays.get('discovery_globs') or [], 'project_overlays.discovery_globs')]
		self.similar_project_groups = dfh_validate_similar_project_groups(raw.get('similar_projects'), v, env=self.env)
		raw_profiles = raw.get('project_profiles') or {}
		if not isinstance(raw_profiles, dict) or 'default' not in raw_profiles:
			raise ValueError('paths.json project_profiles must define at least "default"')
		self.project_profiles = deepcopy(raw_profiles)
		self.resolved_profiles = {prof_name: self.__resolve_profile_chain(prof_name) for prof_name in self.project_profiles}
	# @used-by :meth:`Registry.__init__()`
	def __init_variables(self, raw: dict[str, Any], primary: Path | None) -> None:
		variables = dfh_validate_variables_map(raw.get('variables'), 'paths.json variables')
		if not variables:
			raise ValueError('paths.json requires non-empty variables')
		self.anchor_code = Path(primary).resolve() if None is not primary else CacheStore(self.source_path.parent.resolve()).run()
		self.has_synthetic_primary = None is not primary and dfh_path_key(self.anchor_code) != dfh_path_key(self.source_path.parent.resolve())
		variables = self.__anchor_overrides(variables)
		self.raw = deepcopy(raw)
		self.raw_variables = variables
		self.resolved_variables = {name: dfh_expand_template(val, variables, env=self.env, normalize=True) for name, val in variables.items()}
	# @used-by :meth:`Registry.__init_core_maps()`
	def __parse_workspace_overrides(self, raw_ws: Any) -> dict[str, dict[str, Any]]:
		if not isinstance(raw_ws, dict):
			raise ValueError('paths.json workspace_overrides must be an object')
		r: dict[str, dict[str, Any]] = {}
		for ws_tpl, ws_cfg in raw_ws.items():
			if not isinstance(ws_cfg, dict):
				raise ValueError('paths.json workspace_overrides values must be objects')
			ws_resolved = dfh_expand_template(ws_tpl, self.raw_variables, env=self.env, normalize=True)
			r[dfh_path_key(ws_resolved)] = {'root': ws_resolved, **dfh_expand_structure(ws_cfg, self.raw_variables, env=self.env)}
		return r
	# @used-by :meth:`Registry.__resolve_profile_chain()`
	def __profile_base(self, name: str, cfg: dict[str, Any], seen: tuple[str, ...]) -> dict[str, Any]:
		parent_name = cfg.get('extends')
		if None is not parent_name:
			if not isinstance(parent_name, str) or not parent_name.strip():
				raise ValueError(f'project_profiles.{name}.extends must be a profile name')
			r = self.__resolve_profile_chain(parent_name, (*seen, name))
		else:
			r = {'auxiliary_repos': {}, 'code_repos': [], 'fs_version': 1, 'journal_legacy_fallbacks': [], 'journal_version': 1, 'linked_roots': [], 'paths': {}, 'similar_projects': [], 'tools': {}, 'variables': {}}
		return r
	# @used-by :meth:`Registry.__init_overlays_and_profiles()`
	# @used-by :meth:`Registry.__profile_base()`
	def __resolve_profile_chain(self, name: str, seen: tuple[str, ...]=()) -> dict[str, Any]:
		if name in seen:
			raise ValueError(f"Cyclic project profile inheritance: {' -> '.join((*seen, name))}")
		if name not in self.project_profiles:
			raise ValueError(f'Unknown project path profile: {name!r}')
		cfg = self.project_profiles[name]
		if not isinstance(cfg, dict):
			raise ValueError(f'project_profiles.{name} must be an object')
		base = self.__profile_base(name, cfg, seen)
		fs_ver, j_ver = self.__validate_profile_versions(name, cfg, base)
		return self.__build_profile_spec(name, cfg, base, fs_ver, j_ver)
	# @used-by :meth:`Registry.__resolve_profile_chain()`
	@staticmethod
	def __validate_profile_versions(name: str, cfg: dict[str, Any], base: dict[str, Any]) -> tuple[int, int]:
		raw_fs_ver = cfg.get('fs_version', base['fs_version'])
		if int is not type(raw_fs_ver) or raw_fs_ver not in (1, 2):
			raise ValueError(f'project_profiles.{name}.fs_version must be 1 or 2')
		raw_j_ver = cfg.get('journal_version', base['journal_version'])
		if int is not type(raw_j_ver) or raw_j_ver not in (1, 2, 3):
			raise ValueError(f'project_profiles.{name}.journal_version must be 1, 2, or 3')
		return (raw_fs_ver, raw_j_ver)
	# @used-by :func:`Df.Harness.lib.runtime_validate.dfh_expand_path()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_path_subsystem_classes()`
	def expand(self, template: str, extra_variables: dict[str, str] | None=None) -> str:
		merged = self.raw_variables if not extra_variables else {**self.raw_variables, **extra_variables}
		return dfh_expand_template(template, merged, env=self.env, normalize=True)
	# @used-by :func:`Df.Harness.lib.runtime_cache._load_uncached_settings()`
	def expand_data(self, data: Any, extra_variables: dict[str, str] | None=None) -> Any:
		merged = self.raw_variables if not extra_variables else {**self.raw_variables, **extra_variables}
		return dfh_expand_structure(data, merged, env=self.env)
