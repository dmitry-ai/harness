# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from typing import Any
from Df.Harness.lib.path_discovery import dfh_derive_platform_system_paths
from Df.Harness.lib.runtime_validate import dfh_exists_flag, dfh_expand_path, dfh_has_glob_wildcard
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_all_instances()`
def _build_env_entry(plat_id: str, plat_cfg: dict, cfg_all: dict, include_disabled: bool, check_exists: bool, settings_fn: Any) -> dict:
	insts = dfh_extract_platform_instances(plat_cfg, platform=plat_id, include_disabled=include_disabled)
	all_decl = dfh_extract_platform_instances(plat_cfg, platform=plat_id, include_disabled=True)
	env_entry: dict[str, Any] = {
		'active': dfh_platform_active(plat_id, config=cfg_all, settings_fn=settings_fn),
		'adapter': dfh_platform_adapter_name(plat_id, plat_cfg),
		'capabilities': list(plat_cfg.get('capabilities') or []),
		'disabled_instances': [k for k, v in all_decl.items() if not v['enabled']],
		'enabled': dfh_platform_enabled(plat_id, config=cfg_all, settings_fn=settings_fn),
		'enabled_instances': [k for k, v in all_decl.items() if v['enabled']],
		'handoff': deepcopy(plat_cfg.get('handoff') or {}),
		'instances': {},
		'label': plat_cfg.get('label', plat_id),
		'surface': plat_cfg.get('surface'),
	}
	for iid, item in insts.items():
		env_entry['instances'][iid] = _build_instance_record(plat_id, iid, item, check_exists)
	return env_entry
# @used-by :func:`dfh_extract_platform_instances()`
def _build_instance_entry(platform: str, plat_cfg: dict, inst_id: str, inst_cfg: dict, plat_enabled: bool, inst_enabled: bool) -> dict:
	paths = dfh_default_system_paths(platform, inst_id, inst_cfg, plat_cfg)
	home_str = paths.get('home') or (str(inst_cfg['home']) if inst_cfg.get('home') else None)
	entry = deepcopy(inst_cfg)
	entry.update({
		'adapter': dfh_platform_adapter_name(platform, plat_cfg),
		'enabled': bool(plat_enabled and inst_enabled),
		'home': home_str,
		'id': inst_id,
		'instance_enabled': inst_enabled,
		'platform': platform,
		'platform_enabled': plat_enabled,
		'surface': plat_cfg.get('surface'),
		'system_paths': paths,
	})
	return entry
# @used-by :func:`_build_env_entry()`
def _build_instance_record(plat_id: str, iid: str, item: dict, check_exists: bool) -> dict:
	record: dict[str, Any] = {
		'adapter': item['adapter'],
		'disabled_reason': item.get('disabled_reason'),
		'enabled': item['enabled'],
		'home': item.get('home'),
		'id': iid,
		'instance_enabled': item['instance_enabled'],
		'label': item.get('label', iid),
		'platform': plat_id,
		'platform_enabled': item['platform_enabled'],
		'surface': item.get('surface'),
		'system_paths': deepcopy(item['system_paths']),
		'user_data_dir': item.get('user_data_dir'),
	}
	if check_exists:
		record['paths_exist'] = {k: dfh_exists_flag(v) for k, v in item['system_paths'].items()}
	return record
# @used-by :func:`dfh_default_system_paths()`
def _expand_explicit_paths(platform: str, inst_id: str, explicit_raw: Any) -> dict[str, str]:
	if not isinstance(explicit_raw, dict):
		raise ValueError(f'system_paths for {platform}/{inst_id} must be an object')
	explicit: dict[str, str] = {}
	for key, val in explicit_raw.items():
		if not isinstance(key, str) or not key.strip() or (not isinstance(val, str)) or (not val.strip()):
			raise ValueError(f'system_paths.{key} for {platform}/{inst_id} must be a non-empty string')
		explicit[key] = dfh_expand_path(val)
	return explicit
# @used-by :func:`dfh_all_instances()`
# @used-by :func:`dfh_enabled_platforms()`
# @used-by :func:`dfh_instance_entry()`
# @used-by :func:`dfh_platform_active()`
# @used-by :func:`dfh_platform_adapter_name()`
# @used-by :func:`dfh_platform_key_for_adapter()`
# @used-by :func:`dfh_resolve_platform_cfg()`
def _load_cfg(config: dict | None, settings_fn: Any) -> dict:
	if config:
		r = config
	elif None is not settings_fn:
		r = settings_fn()
	else:
		from Df.Harness.Runtime.SettingsLoader import SettingsLoader
		r = SettingsLoader().run()
	return r
# @used-by :func:`dfh_extract_platform_instances()`
def _raw_instances_map(plat_cfg: dict, platform: str) -> dict:
	raw_instances = plat_cfg.get('instances')
	label = platform or '<platform>'
	if 'homes' in plat_cfg and isinstance(plat_cfg['homes'], dict):
		r = {name: {'enabled': True, 'home': str(home)} for name, home in (plat_cfg.get('homes') or {}).items()}
	elif None is raw_instances:
		raw_homes = plat_cfg.get('homes') or {}
		if not isinstance(raw_homes, dict):
			raise ValueError(f'runtime.json platforms.{label}.homes must map profile names to home directories')
		r = {name: {'enabled': True, 'home': str(home)} for name, home in raw_homes.items()}
	elif isinstance(raw_instances, dict):
		r = raw_instances
	else:
		raise ValueError(f'runtime.json platforms.{label}.instances must be an object')
	return r
# @used-by :func:`agent_tools.runtime.all_instances()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
def dfh_all_instances(*, config: dict | None=None, platform: str | None=None, include_disabled: bool=True, check_exists: bool=False, settings_fn: Any=None) -> dict:
	cfg_all = _load_cfg(config, settings_fn)
	if platform:
		resolved_id, resolved_cfg = dfh_resolve_platform_cfg(platform, config=cfg_all, settings_fn=settings_fn)
		if None is resolved_cfg:
			raise ValueError(f'Unknown Upwork platform: {platform}')
		plat_names = [resolved_id]
	else:
		plat_names = list(cfg_all['platforms'])
	envs: dict[str, dict] = {}
	flat: dict[str, dict] = {}
	for plat_id in plat_names:
		env_entry = _build_env_entry(plat_id, cfg_all['platforms'][plat_id], cfg_all, include_disabled, check_exists, settings_fn)
		envs[plat_id] = env_entry
		for iid, record in env_entry['instances'].items():
			flat[f'{plat_id}:{iid}' if iid in flat else iid] = record
	handoff_targets = [{'home': inst['home'], 'id': iid, 'label': inst['label'], 'platform': plat_id, 'system_paths': inst['system_paths']} for plat_id, env in envs.items() for iid, inst in env['instances'].items() if inst['enabled']]
	return {'available_handoff_targets': handoff_targets, 'enabled_environments': [p for p, e in envs.items() if e['active']], 'environments': envs, 'instances': flat}
# @used-by :func:`_build_instance_entry()`
# @used-by :func:`agent_tools.runtime.default_system_paths()`
def dfh_default_system_paths(platform: str, inst_id: str, inst_cfg: dict, plat_cfg: dict | None=None) -> dict:
	pc = plat_cfg if isinstance(plat_cfg, dict) else {}
	adapter_kind = dfh_platform_adapter_name(platform, pc)
	explicit = _expand_explicit_paths(platform, inst_id, inst_cfg.get('system_paths') or {})
	raw_home = explicit.get('home') if 'home' in explicit else inst_cfg.get('home')
	home_exp = dfh_expand_path(raw_home) if isinstance(raw_home, str) and raw_home.strip() and (not dfh_has_glob_wildcard(raw_home)) else None
	raw_udd = explicit.get('user_data_dir') if 'user_data_dir' in explicit else inst_cfg.get('user_data_dir')
	udd_exp = dfh_expand_path(raw_udd) if isinstance(raw_udd, str) and raw_udd.strip() and (not dfh_has_glob_wildcard(raw_udd)) else None
	return dfh_derive_platform_system_paths(adapter_kind, explicit, home=home_exp, user_data_dir=udd_exp, plat_cfg=pc)
# @used-by :func:`Df.Harness.lib.runtime_context._pick_default_platform()`
# @used-by :func:`agent_tools.runtime.enabled_platforms()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
def dfh_enabled_platforms(*, config: dict | None=None, settings_fn: Any=None) -> list[str]:
	cfg_all = _load_cfg(config, settings_fn)
	return [name for name in cfg_all['platforms'] if dfh_platform_active(name, config=cfg_all, settings_fn=settings_fn)]
# @used-by :func:`Df.Harness.lib.runtime_context.dfh_profile_name()`
# @used-by :func:`Df.Harness.lib.runtime_context.dfh_registration_profile_name()`
# @used-by :func:`Df.Harness.lib.runtime_resolve.dfh_resolve_codex_home()`
# @used-by :func:`agent_tools.runtime.extract_platform_homes()`
# @used-by :func:`dfh_platform_homes()`
# @used-by :meth:`Df.Harness.Platform.Codex.ProofVerifier.ProofVerifier.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.ToolTraceReader.ToolTraceReader.run()`
def dfh_extract_platform_homes(plat_cfg: Any, *, platform: str='', include_disabled: bool=False) -> dict[str, str]:
	return {name: item['home'] for name, item in dfh_extract_platform_instances(plat_cfg, platform=platform, include_disabled=include_disabled).items() if item.get('home')}
# @used-by :func:`Df.Harness.lib.config_codex.dfh_global_codex_instructions()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._resolve_install_pools()`
# @used-by :func:`Df.Harness.lib.runtime_context._resolve_registration_default()`
# @used-by :func:`Df.Harness.lib.runtime_context.dfh_profile_name()`
# @used-by :func:`Df.Harness.lib.runtime_conversations.dfh_find_conversation_instance()`
# @used-by :func:`Df.Harness.lib.runtime_resolve.dfh_resolve_antigravity_paths()`
# @used-by :func:`Df.Harness.lib.runtime_resolve.dfh_resolve_codex_paths()`
# @used-by :func:`_build_env_entry()`
# @used-by :func:`agent_tools.runtime.extract_platform_instances()`
# @used-by :func:`dfh_extract_platform_homes()`
# @used-by :func:`dfh_platform_active()`
# @used-by :func:`dfh_platform_instances()`
def dfh_extract_platform_instances(plat_cfg: Any, *, platform: str='', include_disabled: bool=False) -> dict[str, dict]:
	out: dict[str, dict] = {}
	if isinstance(plat_cfg, dict):
		plat_enabled = plat_cfg.get('enabled', True)
		label = platform or '<platform>'
		if not isinstance(plat_enabled, bool):
			raise ValueError(f'runtime.json platforms.{label}.enabled must be a boolean')
		for inst_id, inst_cfg in _raw_instances_map(plat_cfg, platform).items():
			if not isinstance(inst_cfg, dict):
				raise ValueError(f'Instance {platform}/{inst_id} configuration must be an object')
			inst_enabled = inst_cfg.get('enabled', True)
			if not isinstance(inst_enabled, bool):
				raise ValueError(f'Instance {platform}/{inst_id}.enabled must be a boolean')
			if include_disabled or (plat_enabled and inst_enabled):
				out[inst_id] = _build_instance_entry(platform, plat_cfg, inst_id, inst_cfg, plat_enabled, inst_enabled)
	return out
# @used-by :func:`Df.Harness.lib.runtime_context.dfh_platform_name()`
# @used-by :func:`Df.Harness.lib.runtime_resolve._ag_entry_from_auto()`
# @used-by :func:`Df.Harness.lib.runtime_resolve._resolve_codex_home_choice()`
# @used-by :func:`agent_tools.runtime.instance_entry()`
# @used-by :func:`dfh_instance_paths()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
def dfh_instance_entry(instance_id: str, *, platform: str | None=None, config: dict | None=None, include_disabled: bool=True, settings_fn: Any=None, instances_fn: Any=None) -> dict:
	cfg_all = _load_cfg(config, settings_fn)
	if platform:
		resolved_id, resolved_cfg = dfh_resolve_platform_cfg(platform, config=cfg_all, settings_fn=settings_fn)
		if None is resolved_cfg:
			raise ValueError(f'Unknown Upwork platform: {platform}')
		targets = [resolved_id]
	else:
		targets = list(cfg_all['platforms'])
	inst_loader = instances_fn or (lambda p, *, config=None, include_disabled=False: dfh_platform_instances(p, config=config, include_disabled=include_disabled, settings_fn=settings_fn))
	matches = [insts[instance_id] for plat_id in targets for insts in (inst_loader(plat_id, config=cfg_all, include_disabled=include_disabled),) if instance_id in insts]
	if not matches:
		scope = f'platform {platform}' if platform else 'runtime.json'
		raise ValueError(f'Unknown instance {instance_id!r} in {scope}')
	if 1 < len(matches):
		raise ValueError(f'Instance {instance_id!r} exists in multiple platforms; specify --platform')
	return matches[0]
# @used-by :func:`agent_tools.runtime.instance_paths()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
def dfh_instance_paths(instance_id: str, *, platform: str | None=None, config: dict | None=None, include_disabled: bool=True, settings_fn: Any=None, instances_fn: Any=None) -> dict:
	return dfh_instance_entry(instance_id, platform=platform, config=config, include_disabled=include_disabled, settings_fn=settings_fn, instances_fn=instances_fn)['system_paths']
# @used-by :func:`Df.Harness.lib.runtime_context._pick_default_platform()`
# @used-by :func:`_build_env_entry()`
# @used-by :func:`agent_tools.runtime.platform_active()`
# @used-by :func:`dfh_enabled_platforms()`
# @used-by :meth:`Df.Harness.Cleanup.StoreResolver.StoreResolver.__platform_ids()`
def dfh_platform_active(platform: str, *, config: dict | None=None, settings_fn: Any=None) -> bool:
	cfg_all = _load_cfg(config, settings_fn)
	resolved_id, plat_cfg = dfh_resolve_platform_cfg(platform, config=cfg_all, settings_fn=settings_fn)
	if not isinstance(plat_cfg, dict) or (not dfh_platform_enabled(resolved_id, config=cfg_all, settings_fn=settings_fn)):
		r = False
	else:
		declared = dfh_extract_platform_instances(plat_cfg, platform=resolved_id, include_disabled=True)
		r = any((item['enabled'] for item in declared.values())) if declared else True
	return r
# @used-by :func:`Df.Harness.lib.cleanup_lifecycle_ops._disabled_ag_history()`
# @used-by :func:`Df.Harness.lib.cleanup_lifecycle_ops._disabled_codex_history()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_instruction_snapshot()`
# @used-by :func:`Df.Harness.lib.completion_core._scan_native_for_platform()`
# @used-by :func:`Df.Harness.lib.completion_core.dfh_sync_antigravity_conversation_title()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_is_conversation_running_live()`
# @used-by :func:`Df.Harness.lib.journal_sync_ops._is_native_idle_for_sync()`
# @used-by :func:`Df.Harness.lib.runtime_conversations.dfh_find_conversation_instance()`
# @used-by :func:`_build_env_entry()`
# @used-by :func:`_build_instance_entry()`
# @used-by :func:`agent_tools.runtime.platform_adapter_name()`
# @used-by :func:`dfh_default_system_paths()`
# @used-by :func:`dfh_platform_key_for_adapter()`
# @used-by :meth:`Df.Harness.Cleanup.StoreResolver.StoreResolver.__platform_ids()`
def dfh_platform_adapter_name(platform: str, plat_cfg: dict | None=None, *, config: dict | None=None, settings_fn: Any=None) -> str:
	pc = plat_cfg if None is not plat_cfg else (_load_cfg(config, settings_fn).get('platforms', {}).get(platform) or {})
	return pc.get('adapter') or platform
# @used-by :func:`_build_env_entry()`
# @used-by :func:`agent_tools.runtime.platform_enabled()`
# @used-by :func:`dfh_platform_active()`
def dfh_platform_enabled(platform: str, *, config: dict | None=None, settings_fn: Any=None) -> bool:
	_, cfg = dfh_resolve_platform_cfg(platform, config=config, settings_fn=settings_fn)
	if not isinstance(cfg, dict):
		raise ValueError(f'Unknown Upwork platform: {platform}')
	val = cfg.get('enabled', True)
	if not isinstance(val, bool):
		raise ValueError(f'runtime.json platforms.{platform}.enabled must be a boolean')
	return val
# @used-by :func:`agent_tools.runtime.platform_homes()`
def dfh_platform_homes(platform: str, *, config: dict | None=None, include_disabled: bool=False, settings_fn: Any=None) -> dict[str, str]:
	resolved_id, cfg = dfh_resolve_platform_cfg(platform, config=config, settings_fn=settings_fn)
	if None is cfg:
		raise ValueError(f'Unknown Upwork platform: {platform}')
	return dfh_extract_platform_homes(cfg, platform=resolved_id, include_disabled=include_disabled)
# @used-by :func:`Df.Harness.lib.ag_daemon.dfh_default_folders_json()`
# @used-by :func:`Df.Harness.lib.ag_metadata._load_ag_instances()`
# @used-by :func:`Df.Harness.lib.cleanup_lifecycle_ops._disabled_ag_history()`
# @used-by :func:`Df.Harness.lib.cleanup_lifecycle_ops._disabled_codex_history()`
# @used-by :func:`Df.Harness.lib.cleanup_lifecycle_ops.dfh_resolve_readonly_history()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._resolve_ag_from_settings()`
# @used-by :func:`Df.Harness.lib.path_discovery._runtime_ag_projects_dirs()`
# @used-by :func:`agent_tools.runtime.platform_instances()`
# @used-by :func:`dfh_instance_entry()`
# @used-by :meth:`Df.Harness.Cleanup.StoreResolver.StoreResolver.__resolve_ag_multi()`
# @used-by :meth:`Df.Harness.Cleanup.StoreResolver.StoreResolver.__resolve_codex_homes()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__register_multi()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ToolTraceReader.ToolTraceReader.__resolve_paths()`
def dfh_platform_instances(platform: str, *, config: dict | None=None, include_disabled: bool=False, settings_fn: Any=None) -> dict[str, dict]:
	resolved_id, cfg = dfh_resolve_platform_cfg(platform, config=config, settings_fn=settings_fn)
	if None is cfg:
		raise ValueError(f'Unknown Upwork platform: {platform}')
	return dfh_extract_platform_instances(cfg, platform=resolved_id, include_disabled=include_disabled)
# @used-by :func:`Df.Harness.lib.ag_daemon.dfh_default_folders_json()`
# @used-by :func:`Df.Harness.lib.runtime_context._pick_default_platform()`
# @used-by :func:`Df.Harness.lib.runtime_context.dfh_platform_name()`
# @used-by :func:`Df.Harness.lib.runtime_context.dfh_profile_name()`
# @used-by :func:`Df.Harness.lib.runtime_context.dfh_registration_profile_name()`
# @used-by :func:`Df.Harness.lib.runtime_resolve.dfh_resolve_antigravity_paths()`
# @used-by :func:`Df.Harness.lib.runtime_resolve.dfh_resolve_codex_home()`
# @used-by :func:`Df.Harness.lib.runtime_resolve.dfh_resolve_codex_paths()`
# @used-by :func:`agent_tools.runtime.platform_key_for_adapter()`
# @used-by :func:`dfh_resolve_platform_cfg()`
def dfh_platform_key_for_adapter(adapter_name: str, config: dict | None=None, *, settings_fn: Any=None) -> str | None:
	plats = _load_cfg(config, settings_fn).get('platforms') or {}
	direct = plats.get(adapter_name)
	if isinstance(direct, dict) and dfh_platform_adapter_name(adapter_name, direct) == adapter_name:
		r: str | None = adapter_name
	else:
		matches = [name for name, plat_cfg in plats.items() if isinstance(plat_cfg, dict) and dfh_platform_adapter_name(name, plat_cfg) == adapter_name]
		if not matches:
			r = None
		else:
			enabled = [name for name in matches if bool(plats[name].get('enabled', True))]
			r = enabled[0] if enabled else matches[0]
	return r
# @used-by :func:`Df.Harness.lib.runtime_conversations.dfh_find_conversation_instance()`
# @used-by :func:`agent_tools.runtime._resolve_platform_cfg()`
# @used-by :func:`dfh_all_instances()`
# @used-by :func:`dfh_instance_entry()`
# @used-by :func:`dfh_platform_active()`
# @used-by :func:`dfh_platform_enabled()`
# @used-by :func:`dfh_platform_homes()`
# @used-by :func:`dfh_platform_instances()`
def dfh_resolve_platform_cfg(platform: str, *, config: dict | None=None, settings_fn: Any=None) -> tuple[str, dict | None]:
	cfg_all = _load_cfg(config, settings_fn)
	plats = cfg_all.get('platforms') or {}
	if platform in plats:
		r: tuple[str, dict | None] = (platform, plats[platform])
	else:
		key = dfh_platform_key_for_adapter(platform, cfg_all, settings_fn=settings_fn)
		r = (key, plats[key]) if key and key in plats else (platform, None)
	return r
