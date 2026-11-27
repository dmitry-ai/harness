# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_resolve import dfh_load_registry
from Df.Harness.lib.path_template import dfh_normalize_path_str
import glob
import os
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_validate_platform_entry()`
def _validate_instance_entry(plat_id: str, inst_id: Any, inst_cfg: Any) -> None:
	if not isinstance(inst_id, str) or not inst_id.strip() or (not isinstance(inst_cfg, dict)):
		raise ValueError(f'runtime.json platforms.{plat_id}.instances entries must map IDs to objects')
	if 'enabled' in inst_cfg and (not isinstance(inst_cfg['enabled'], bool)):
		raise ValueError(f'runtime.json platforms.{plat_id}.instances.{inst_id}.enabled must be a boolean')
	if 'home' in inst_cfg and (not isinstance(inst_cfg['home'], str) or not inst_cfg['home'].strip()):
		raise ValueError(f'runtime.json platforms.{plat_id}.instances.{inst_id}.home must be a non-empty path')
	if 'user_data_dir' in inst_cfg and (None is not inst_cfg['user_data_dir']) and (not isinstance(inst_cfg['user_data_dir'], str) or not inst_cfg['user_data_dir'].strip()):
		raise ValueError(f'runtime.json platforms.{plat_id}.instances.{inst_id}.user_data_dir must be a non-empty path')
	if 'system_paths' in inst_cfg:
		sp = inst_cfg['system_paths']
		if not isinstance(sp, dict) or any((not isinstance(k, str) or not k.strip() or (not isinstance(v, str)) or (not v.strip()) for k, v in sp.items())):
			raise ValueError(f'runtime.json platforms.{plat_id}.instances.{inst_id}.system_paths must map non-empty keys to path strings')
	if not inst_cfg.get('home') and (not inst_cfg.get('system_paths')):
		raise ValueError(f'runtime.json platforms.{plat_id}.instances.{inst_id} requires home or system_paths')
# @used-by :func:`dfh_validate_runtime()`
def _validate_platform_entry(plat_id: Any, plat_cfg: Any) -> None:
	if not isinstance(plat_id, str) or not plat_id.strip() or (not isinstance(plat_cfg, dict)):
		raise ValueError('Each runtime.json platform must map a non-empty name to an object')
	if 'enabled' in plat_cfg and (not isinstance(plat_cfg['enabled'], bool)):
		raise ValueError(f'runtime.json platforms.{plat_id}.enabled must be a boolean')
	if 'instances' in plat_cfg:
		if not isinstance(plat_cfg['instances'], dict):
			raise ValueError(f'runtime.json platforms.{plat_id}.instances must be an object')
		for inst_id, inst_cfg in plat_cfg['instances'].items():
			_validate_instance_entry(plat_id, inst_id, inst_cfg)
	if 'homes' in plat_cfg and (not isinstance(plat_cfg['homes'], dict)):
		raise ValueError(f'runtime.json platforms.{plat_id}.homes must map profile names to home directories')
	if 'homes' in plat_cfg and 'instances' in plat_cfg:
		raise ValueError(f'runtime.json platforms.{plat_id} cannot define both instances and legacy homes')
# @used-by :func:`Df.Harness.lib.runtime_instances._build_instance_record()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_default_system_paths_overrides_and_nested_codex_globs()`
def dfh_exists_flag(path_str: Any) -> bool:
	text = dfh_expand_path(path_str) if isinstance(path_str, str) else str(path_str)
	return any((Path(match).exists() for match in glob.glob(text, recursive=True))) if dfh_has_glob_wildcard(text) else Path(text).exists()
# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_touches_antigravity_addons()`
# @used-by :func:`Df.Harness.lib.runtime_instances._expand_explicit_paths()`
# @used-by :func:`Df.Harness.lib.runtime_instances.dfh_default_system_paths()`
# @used-by :func:`agent_tools.runtime.sanctioned_addon_code_roots()`
# @used-by :func:`dfh_exists_flag()`
# @used-by :func:`dfh_resolve_glob_paths()`
def dfh_expand_path(value: Any) -> str:
	text = str(value)
	return dfh_load_registry().expand(text) if '${' in text or re.search('%[A-Za-z_][A-Za-z0-9_]*%', text) else dfh_normalize_path_str(os.path.expanduser(text))
# @used-by :func:`Df.Harness.lib.runtime_instances.dfh_default_system_paths()`
# @used-by :func:`dfh_exists_flag()`
def dfh_has_glob_wildcard(value: Any) -> bool:
	text = str(value or '')
	return '*' in text or '?' in text
# @used-by :func:`Df.Harness.lib.runtime_conversations._codex_db_files()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
def dfh_resolve_glob_paths(raw_glob: Any, base_dir: Path | None=None) -> list[Path]:
	text = dfh_expand_path(raw_glob) if isinstance(raw_glob, str) and raw_glob.strip() else ''
	if not text:
		r: list[Path] = []
	else:
		p = Path(text)
		if (not p.is_absolute()) and None is base_dir:
			r = []
		else:
			if not p.is_absolute():
				text = (Path(base_dir) / p).as_posix()
			r = sorted((Path(match) for match in glob.glob(text, recursive=True)))
	return r
# @used-by :meth:`Df.Harness.Runtime.SettingsLoader.SettingsLoader.run()`
def dfh_validate_runtime(value: Any) -> None:
	if 2 != value.get('version') or not value.get('workspace_root') or (not isinstance(value.get('platforms'), dict)) or (not value['platforms']):
		raise ValueError('runtime.json needs version 2, workspace_root and platforms')
	if 'user_default_locale' in value and (None is not value['user_default_locale']) and (not isinstance(value['user_default_locale'], str) or not value['user_default_locale'].strip()):
		raise ValueError('runtime.json user_default_locale must be a non-empty locale string')
	for plat_id, plat_cfg in value['platforms'].items():
		_validate_platform_entry(plat_id, plat_cfg)
