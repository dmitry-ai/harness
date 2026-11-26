# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
# 2026-11-18
# "Fix runtime instance path derivation and store validation":
# https://github.com/dmitry-ai/harness/issues/89
import glob
import json
import os
from pathlib import Path
import re
import sqlite3
# 2026-11-19
# "Add declarative path registry paths.json with template variable resolution and runtime.json integration":
# https://github.com/dmitry-ai/harness/issues/95
# 2026-11-24
# "Deploy immutable Harness runtime snapshots with LKG fallback":
# https://github.com/dmitry-ai/harness/issues/184
from .path_registry import DEFAULT_REGISTRY_FILE, _CODE_ANCHOR, default_platform_paths, default_runtime_file, derive_platform_system_paths, load_registry, normalize_path_str, store_path, tool_path, var_value
# 2026-11-19
# "Add declarative path registry paths.json with template variable resolution and runtime.json integration":
# https://github.com/dmitry-ai/harness/issues/95
PRIMARY = Path(var_value('HARNESS_CODE')).resolve()
HARNESS_ROOT = Path(var_value('HARNESS_ROOT')).resolve()
HARNESS_META = Path(var_value('HARNESS_META')).resolve()
LEGACY_PRIMARY = store_path('legacy_primary')
# 2026-10-24
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0')
_SHIM_DIR = str(tool_path('git_shim_dir').resolve())
if _SHIM_DIR not in os.environ.get('PATH', '').split(os.pathsep):
	os.environ['PATH'] = _SHIM_DIR + os.pathsep + os.environ.get('PATH', '')
_platform = ContextVar('upwork_platform', default=None)
_profile = ContextVar('upwork_profile', default=None)
_instance = ContextVar('upwork_instance', default=None)
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
# 2026-11-19
# "Add declarative path registry paths.json with template variable resolution and runtime.json integration":
# https://github.com/dmitry-ai/harness/issues/95
# @used-by :func:`_exists_flag()`
# @used-by :func:`_resolve_glob_paths()`
# @used-by :func:`default_system_paths()`
# @used-by :func:`sanctioned_addon_code_roots()`
def _expand_path(value):
	text = str(value)
	if '${' in text or re.search('%[A-Za-z_][A-Za-z0-9_]*%', text):
		return load_registry().expand(text)
	return normalize_path_str(os.path.expanduser(text))
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
# @used-by :func:`settings()`
def _validate_runtime(value):
	if 2 != value.get('version') or not value.get('workspace_root') or (not isinstance(value.get('platforms'), dict)) or (not value['platforms']):
		raise ValueError('runtime.json needs version 2, workspace_root and platforms')
	# 2026-11-23
	# "Configure default user locale for language-neutral commands in TEXT-1 and locale gate":
	# https://github.com/dmitry-ai/harness/issues/131
	if 'user_default_locale' in value and (None is not value['user_default_locale']) and (not isinstance(value['user_default_locale'], str) or not value['user_default_locale'].strip()):
		raise ValueError('runtime.json user_default_locale must be a non-empty locale string')
	for plat_id, plat_cfg in value['platforms'].items():
		if not isinstance(plat_id, str) or not plat_id.strip() or (not isinstance(plat_cfg, dict)):
			raise ValueError('Each runtime.json platform must map a non-empty name to an object')
		if 'enabled' in plat_cfg and (not isinstance(plat_cfg['enabled'], bool)):
			raise ValueError(f'runtime.json platforms.{plat_id}.enabled must be a boolean')
		if 'instances' in plat_cfg:
			raw = plat_cfg['instances']
			if not isinstance(raw, dict):
				raise ValueError(f'runtime.json platforms.{plat_id}.instances must be an object')
			for inst_id, inst_cfg in raw.items():
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
		if 'homes' in plat_cfg and (not isinstance(plat_cfg['homes'], dict)):
			raise ValueError(f'runtime.json platforms.{plat_id}.homes must map profile names to home directories')
		if 'homes' in plat_cfg and 'instances' in plat_cfg:
			raise ValueError(f'runtime.json platforms.{plat_id} cannot define both instances and legacy homes')
# 2026-10-15
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-24
# "Deploy immutable Harness runtime snapshots with LKG fallback":
# https://github.com/dmitry-ai/harness/issues/184
# 2026-11-24
# "Cache runtime settings and deduplicate evidence validation in hot paths":
# https://github.com/dmitry-ai/harness/issues/227
# @used-by :func:`_resolve_platform_cfg()`
# @used-by :func:`agent_tools.cleanup.record_cleanup_answer()`
# @used-by :func:`agent_tools.cleanup_audit.record_cleanup_answer_log()`
# @used-by :func:`agent_tools.cleanup_audit.resolve_cleanup_log_root()`
# @used-by :func:`agent_tools.completion._instruction_snapshot()`
# @used-by :func:`agent_tools.configuration._primary_settings()`
# @used-by :func:`agent_tools.configuration.global_codex_instructions()`
# @used-by :func:`agent_tools.meta.identity._resolve_ag_paths_safe()`
# @used-by :func:`agent_tools.native_profiles._configuration()`
# @used-by :func:`agent_tools.operations.add_parsers()`
# @used-by :func:`agent_tools.path_registry._is_registered_single_project()`
# @used-by :func:`agent_tools.platforms.adapter()`
# @used-by :func:`agent_tools.platforms.antigravity._antigravity_paths()`
# @used-by :func:`agent_tools.platforms.antigravity._default_folders_json()`
# @used-by :func:`agent_tools.platforms.antigravity._proof_paths()`
# @used-by :func:`agent_tools.platforms.antigravity.native_tool_trace()`
# @used-by :func:`agent_tools.registration.register_projects()`
# @used-by :func:`agent_tools.repo_tags._configured_timezone()`
# @used-by :func:`agent_tools.text_browser.browser_anchor_status()`
# @used-by :func:`agent_tools.text_browser.collect_cdp_dom()`
# @used-by :func:`agent_tools.text_browser.collect_headless_dom()`
# @used-by :func:`agent_tools.text_browser.preflight()`
# @used-by :func:`agent_tools.text_browser.resolve_cdp_port()`
# @used-by :func:`agent_tools.text_browser.resolve_headless_shell()`
# @used-by :func:`agent_tools.text_core.default_shell()`
# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
# @used-by :func:`agent_tools.upwork_project.antigravity_global_config_dirs()`
# @used-by :func:`agent_tools.upwork_project.check_configuration()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :func:`agent_tools.upwork_project.instances_report()`
# @used-by :func:`agent_tools.upwork_project.main()`
# @used-by :func:`all_instances()`
# @used-by :func:`check_pre_invocation._resolve_ag_paths()`
# @used-by :func:`check_stop_gate._resolve_stop_paths()`
# @used-by :func:`default_user_locale()`
# @used-by :func:`enabled_platforms()`
# @used-by :func:`find_conversation_instance()`
# @used-by :func:`instance_entry()`
# @used-by :func:`platform_active()`
# @used-by :func:`platform_adapter_name()`
# @used-by :func:`platform_key_for_adapter()`
# @used-by :func:`platform_name()`
# @used-by :func:`platform_settings()`
# @used-by :func:`profile_name()`
# @used-by :func:`registration_profile_name()`
# @used-by :func:`request_day()`
# @used-by :func:`resolve_antigravity_paths()`
# @used-by :func:`resolve_codex_home()`
# @used-by :func:`resolve_codex_paths()`
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
# @used-by :meth:`agent_tools.text_browser.CDPSession.__init__()`
# @used-by :meth:`agent_tools.text_browser.GuardedCDP.__init__()`
# @used-by :meth:`agent_tools.text_browser.ManagedHeadlessShell.__init__()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner.__init__()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.registration_status()`
# @used-by :meth:`test_cleanup.CleanupTests.setUp()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.setUp()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.setUp()`
# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests.setUp()`
# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests._make_primary()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.setUp()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_live_runtime_declares_environments_instances_enabled_states_and_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_runtime_validation_rejects_invalid_instances_and_dual_homes()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.setUp()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
# @used-by :meth:`test_portability.ProjectionTests.test_global_instructions_are_read_safely_and_local_override_keeps_its_priority()`
# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_cleanup_integration()`
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.setUp()`
# @used-by :meth:`test_registration_portability.RegistrationTests.setUp()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_runtime_settings_cache_invalidates_on_file_or_env_change_and_isolates_mutations()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m2a_extension_manifest_key_and_multi_profile_tab_broker_isolation()`
# @used-by :mod:`agent_tools.intake`
# @used-by :mod:`agent_tools.platforms.antigravity`
# @used-by :mod:`agent_tools.runtime`
# @used-by :mod:`agent_tools.upwork_project`
def settings(path=None):
	from .runtime_cache import load_cached_settings
	runtime_file = Path(path) if None is not path else default_runtime_file(PRIMARY, _CODE_ANCHOR, DEFAULT_REGISTRY_FILE)
	return load_cached_settings(runtime_file, _validate_runtime)
_UNPATCHED_SETTINGS = settings
from .runtime_cache import skip_shell_violations
# @used-by :func:`agent_tools.cleanup_lifecycle._disabled_ag_history()`
# @used-by :func:`agent_tools.cleanup_lifecycle._disabled_codex_history()`
# @used-by :func:`agent_tools.completion._instruction_snapshot()`
# @used-by :func:`agent_tools.completion._sync_antigravity_conversation_title()`
# @used-by :func:`agent_tools.journal_liveness.is_conversation_running_live()`
# @used-by :func:`agent_tools.journal_sync_all._is_native_idle_for_sync()`
# @used-by :func:`agent_tools.platforms.adapter()`
# @used-by :func:`all_instances()`
# @used-by :func:`default_system_paths()`
# @used-by :func:`extract_platform_instances()`
# @used-by :func:`find_conversation_instance()`
# @used-by :func:`platform_key_for_adapter()`
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
def platform_adapter_name(platform, plat_cfg=None, *, config=None):
	if None is plat_cfg:
		plat_cfg = (config or settings()).get('platforms', {}).get(platform) or {}
	return plat_cfg.get('adapter') or platform
# 2026-11-18
# "Fix runtime instance path derivation and store validation":
# https://github.com/dmitry-ai/harness/issues/89
# @used-by :func:`_exists_flag()`
# @used-by :func:`default_system_paths()`
def _has_glob_wildcard(value):
	text = str(value or '')
	return '*' in text or '?' in text
# 2026-11-18
# "Fix runtime instance path derivation and store validation":
# https://github.com/dmitry-ai/harness/issues/89
# @used-by :func:`_codex_home_conversation_trace()`
def _resolve_glob_paths(raw_glob, base_dir=None):
	text = _expand_path(raw_glob) if isinstance(raw_glob, str) and raw_glob.strip() else ''
	if not text:
		return []
	p = Path(text)
	if not p.is_absolute():
		if None is base_dir:
			return []
		text = (Path(base_dir) / p).as_posix()
	return sorted((Path(match) for match in glob.glob(text, recursive=True)))
# 2026-11-18
# "Fix runtime instance path derivation and store validation":
# https://github.com/dmitry-ai/harness/issues/89
# @used-by :func:`_resolve_platform_cfg()`
# @used-by :func:`agent_tools.platforms.antigravity._default_folders_json()`
# @used-by :func:`platform_name()`
# @used-by :func:`profile_name()`
# @used-by :func:`registration_profile_name()`
# @used-by :func:`resolve_antigravity_paths()`
# @used-by :func:`resolve_codex_home()`
# @used-by :func:`resolve_codex_paths()`
# @used-by :mod:`agent_tools.platforms.antigravity`
def platform_key_for_adapter(adapter_name, config=None):
	cfg_all = config or settings()
	plats = cfg_all.get('platforms') or {}
	direct = plats.get(adapter_name)
	if isinstance(direct, dict) and platform_adapter_name(adapter_name, direct) == adapter_name:
		return adapter_name
	matches = [name for name, plat_cfg in plats.items() if isinstance(plat_cfg, dict) and platform_adapter_name(name, plat_cfg) == adapter_name]
	if not matches:
		return None
	enabled = [name for name in matches if bool(plats[name].get('enabled', True))]
	return enabled[0] if enabled else matches[0]
# @used-by :func:`extract_platform_instances()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_default_system_paths_overrides_and_nested_codex_globs()`
def default_system_paths(platform, inst_id, inst_cfg, plat_cfg=None):
	plat_cfg = plat_cfg if isinstance(plat_cfg, dict) else {}
	adapter_kind = platform_adapter_name(platform, plat_cfg)
	explicit_raw = inst_cfg.get('system_paths') or {}
	if not isinstance(explicit_raw, dict):
		raise ValueError(f'system_paths for {platform}/{inst_id} must be an object')
	explicit = {}
	for key, val in explicit_raw.items():
		if not isinstance(key, str) or not key.strip() or (not isinstance(val, str)) or (not val.strip()):
			raise ValueError(f'system_paths.{key} for {platform}/{inst_id} must be a non-empty string')
		explicit[key] = _expand_path(val)
	raw_home = explicit.get('home') if 'home' in explicit else inst_cfg.get('home')
	home_exp = _expand_path(raw_home) if isinstance(raw_home, str) and raw_home.strip() and (not _has_glob_wildcard(raw_home)) else None
	raw_udd = explicit.get('user_data_dir') if 'user_data_dir' in explicit else inst_cfg.get('user_data_dir')
	udd_exp = _expand_path(raw_udd) if isinstance(raw_udd, str) and raw_udd.strip() and (not _has_glob_wildcard(raw_udd)) else None
	return derive_platform_system_paths(adapter_kind, explicit, home=home_exp, user_data_dir=udd_exp, plat_cfg=plat_cfg)
# @used-by :func:`agent_tools.configuration.global_codex_instructions()`
# @used-by :func:`agent_tools.native_profiles.install_native_profiles()`
# @used-by :func:`agent_tools.upwork_project.antigravity_global_config_dirs()`
# @used-by :func:`all_instances()`
# @used-by :func:`extract_platform_homes()`
# @used-by :func:`find_conversation_instance()`
# @used-by :func:`platform_active()`
# @used-by :func:`platform_instances()`
# @used-by :func:`profile_name()`
# @used-by :func:`registration_profile_name()`
# @used-by :func:`resolve_antigravity_paths()`
# @used-by :func:`resolve_codex_paths()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_codex_profiles()`
def extract_platform_instances(plat_cfg, *, platform='', include_disabled=False):
	if not isinstance(plat_cfg, dict):
		return {}
	plat_enabled = plat_cfg.get('enabled', True)
	if not isinstance(plat_enabled, bool):
		raise ValueError(f'runtime.json platforms.{platform or "<platform>"}.enabled must be a boolean')
	raw_instances = plat_cfg.get('instances')
	if 'homes' in plat_cfg and isinstance(plat_cfg['homes'], dict):
		raw_homes = plat_cfg.get('homes') or {}
		raw_instances = {name: {'enabled': True, 'home': str(home)} for name, home in raw_homes.items()}
	elif None is raw_instances:
		raw_homes = plat_cfg.get('homes') or {}
		if not isinstance(raw_homes, dict):
			raise ValueError(f'runtime.json platforms.{platform or "<platform>"}.homes must map profile names to home directories')
		raw_instances = {name: {'enabled': True, 'home': str(home)} for name, home in raw_homes.items()}
	elif not isinstance(raw_instances, dict):
		raise ValueError(f'runtime.json platforms.{platform or "<platform>"}.instances must be an object')
	out = {}
	for inst_id, inst_cfg in raw_instances.items():
		if not isinstance(inst_cfg, dict):
			raise ValueError(f'Instance {platform}/{inst_id} configuration must be an object')
		inst_enabled = inst_cfg.get('enabled', True)
		if not isinstance(inst_enabled, bool):
			raise ValueError(f'Instance {platform}/{inst_id}.enabled must be a boolean')
		effective = bool(plat_enabled and inst_enabled)
		if not include_disabled and (not effective):
			continue
		paths = default_system_paths(platform, inst_id, inst_cfg, plat_cfg)
		home_str = paths.get('home') or (str(inst_cfg['home']) if inst_cfg.get('home') else None)
		entry = deepcopy(inst_cfg)
		entry.update({
			'id': inst_id,
			'platform': platform,
			'adapter': platform_adapter_name(platform, plat_cfg),
			'surface': plat_cfg.get('surface'),
			'enabled': effective,
			'platform_enabled': plat_enabled,
			'instance_enabled': inst_enabled,
			'home': home_str,
			'system_paths': paths,
		})
		out[inst_id] = entry
	return out
# @used-by :func:`agent_tools.platforms.codex.native_tool_trace()`
# @used-by :func:`agent_tools.platforms.codex.verify_native_proof()`
# @used-by :func:`agent_tools.text_browser._profile()`
# @used-by :func:`platform_homes()`
# @used-by :func:`profile_name()`
# @used-by :func:`registration_profile_name()`
# @used-by :func:`resolve_codex_home()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_codex_custom_system_paths_trace_requests_metadata_and_answers()`
def extract_platform_homes(plat_cfg, *, platform='', include_disabled=False):
	return {name: item['home'] for name, item in extract_platform_instances(plat_cfg, platform=platform, include_disabled=include_disabled).items() if item.get('home')}
# @used-by :func:`all_instances()`
# @used-by :func:`find_conversation_instance()`
# @used-by :func:`instance_entry()`
# @used-by :func:`platform_active()`
# @used-by :func:`platform_enabled()`
# @used-by :func:`platform_homes()`
# @used-by :func:`platform_instances()`
def _resolve_platform_cfg(platform, *, config=None):
	cfg_all = config or settings()
	plats = cfg_all.get('platforms') or {}
	if platform in plats:
		return (platform, plats[platform])
	key = platform_key_for_adapter(platform, cfg_all)
	if key and key in plats:
		return (key, plats[key])
	return (platform, None)
# @used-by :func:`all_instances()`
# @used-by :func:`platform_active()`
def platform_enabled(platform, *, config=None):
	_, cfg = _resolve_platform_cfg(platform, config=config)
	if not isinstance(cfg, dict):
		raise ValueError(f'Unknown Upwork platform: {platform}')
	val = cfg.get('enabled', True)
	if not isinstance(val, bool):
		raise ValueError(f'runtime.json platforms.{platform}.enabled must be a boolean')
	return val
# @used-by :func:`agent_tools.cleanup_lifecycle._disabled_ag_history()`
# @used-by :func:`agent_tools.cleanup_lifecycle._disabled_codex_history()`
# @used-by :func:`agent_tools.cleanup_lifecycle.resolve_readonly_history()`
# @used-by :func:`agent_tools.meta.identity._antigravity_project_dirs()`
# @used-by :func:`agent_tools.path_registry._is_registered_single_project()`
# @used-by :func:`agent_tools.platforms.antigravity._default_folders_json()`
# @used-by :func:`agent_tools.platforms.antigravity._proof_paths()`
# @used-by :func:`agent_tools.platforms.antigravity.native_tool_trace()`
# @used-by :func:`agent_tools.platforms.antigravity.register()`
# @used-by :func:`agent_tools.project_rename._antigravity_dirs_map()`
# @used-by :func:`check_pre_invocation._resolve_ag_paths()`
# @used-by :func:`check_stop_gate._resolve_stop_paths()`
# @used-by :func:`instance_entry()`
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests._make_old_project()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests._init_and_register()`
# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests._make_project()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_per_instance_folders_json_uninitialized_instance_and_stop_gate_a6()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_skips_disabled_codex_and_checks_all_enabled_antigravity_instances()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_dynamic_folders_json_and_cleanup_without_homes()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_live_runtime_declares_environments_instances_enabled_states_and_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_platform_enabled_false_disables_all_instances_of_environment()`
def platform_instances(platform, *, config=None, include_disabled=False):
	resolved_id, cfg = _resolve_platform_cfg(platform, config=config)
	if None is cfg:
		raise ValueError(f'Unknown Upwork platform: {platform}')
	return extract_platform_instances(cfg, platform=resolved_id, include_disabled=include_disabled)
# @used-by :func:`agent_tools.upwork_project.main()`
def platform_homes(platform, *, config=None, include_disabled=False):
	resolved_id, cfg = _resolve_platform_cfg(platform, config=config)
	if None is cfg:
		raise ValueError(f'Unknown Upwork platform: {platform}')
	return extract_platform_homes(cfg, platform=resolved_id, include_disabled=include_disabled)
# @used-by :func:`agent_tools.registration.register_projects()`
# @used-by :func:`agent_tools.upwork_project.antigravity_global_config_dirs()`
# @used-by :func:`all_instances()`
# @used-by :func:`enabled_platforms()`
# @used-by :func:`platform_name()`
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.registration_status()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_live_runtime_declares_environments_instances_enabled_states_and_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_platform_enabled_false_disables_all_instances_of_environment()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_single_enabled_codex_instance_works_with_shared_catalog_superset()`
def platform_active(platform, *, config=None):
	cfg_all = config or settings()
	resolved_id, plat_cfg = _resolve_platform_cfg(platform, config=cfg_all)
	if not isinstance(plat_cfg, dict) or (not platform_enabled(resolved_id, config=cfg_all)):
		return False
	declared = extract_platform_instances(plat_cfg, platform=resolved_id, include_disabled=True)
	if declared:
		return any((item['enabled'] for item in declared.values()))
	return True
# @used-by :func:`platform_name()`
def enabled_platforms(*, config=None):
	cfg_all = config or settings()
	return [name for name in cfg_all['platforms'] if platform_active(name, config=cfg_all)]
# @used-by :func:`agent_tools.metrics._resolve_target()`
# @used-by :func:`agent_tools.metrics.summarize_instance()`
# @used-by :func:`agent_tools.upwork_project.instances_report()`
# @used-by :func:`agent_tools.upwork_project.main()`
# @used-by :func:`instance_paths()`
# @used-by :func:`platform_name()`
# @used-by :func:`resolve_antigravity_paths()`
# @used-by :func:`resolve_codex_home()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_custom_adapter_platform_keys_and_instruction_snapshot()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_platform_enabled_false_disables_all_instances_of_environment()`
def instance_entry(instance_id, *, platform=None, config=None, include_disabled=True):
	cfg_all = config or settings()
	matches = []
	if platform:
		resolved_id, resolved_cfg = _resolve_platform_cfg(platform, config=cfg_all)
		if None is resolved_cfg:
			raise ValueError(f'Unknown Upwork platform: {platform}')
		targets = [resolved_id]
	else:
		targets = list(cfg_all['platforms'])
	for plat_id in targets:
		insts = platform_instances(plat_id, config=cfg_all, include_disabled=include_disabled)
		if instance_id in insts:
			matches.append(insts[instance_id])
	if not matches:
		scope = f'platform {platform}' if platform else 'runtime.json'
		raise ValueError(f'Unknown instance {instance_id!r} in {scope}')
	if 1 < len(matches):
		raise ValueError(f'Instance {instance_id!r} exists in multiple platforms; specify --platform')
	return matches[0]
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_live_runtime_declares_environments_instances_enabled_states_and_system_paths()`
def instance_paths(instance_id, *, platform=None, config=None, include_disabled=True):
	return instance_entry(instance_id, platform=platform, config=config, include_disabled=include_disabled)['system_paths']
# @used-by :func:`all_instances()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_default_system_paths_overrides_and_nested_codex_globs()`
def _exists_flag(path_str):
	text = _expand_path(path_str) if isinstance(path_str, str) else str(path_str)
	if _has_glob_wildcard(text):
		return any((Path(match).exists() for match in glob.glob(text, recursive=True)))
	return Path(text).exists()
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :func:`agent_tools.upwork_project.instances_report()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_custom_adapter_platform_keys_and_instruction_snapshot()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_future_environment_claude_code_is_supported_without_roles_or_adapters()`
def all_instances(*, config=None, platform=None, include_disabled=True, check_exists=False):
	cfg_all = config or settings()
	if platform:
		resolved_id, resolved_cfg = _resolve_platform_cfg(platform, config=cfg_all)
		if None is resolved_cfg:
			raise ValueError(f'Unknown Upwork platform: {platform}')
		plat_names = [resolved_id]
	else:
		plat_names = list(cfg_all['platforms'])
	envs = {}
	flat = {}
	for plat_id in plat_names:
		plat_cfg = cfg_all['platforms'][plat_id]
		insts = extract_platform_instances(plat_cfg, platform=plat_id, include_disabled=include_disabled)
		all_decl = extract_platform_instances(plat_cfg, platform=plat_id, include_disabled=True)
		env_entry = {
			'enabled': platform_enabled(plat_id, config=cfg_all),
			'active': platform_active(plat_id, config=cfg_all),
			'label': plat_cfg.get('label', plat_id),
			'surface': plat_cfg.get('surface'),
			'adapter': platform_adapter_name(plat_id, plat_cfg),
			'capabilities': list(plat_cfg.get('capabilities') or []),
			'handoff': deepcopy(plat_cfg.get('handoff') or {}),
			'enabled_instances': [k for k, v in all_decl.items() if v['enabled']],
			'disabled_instances': [k for k, v in all_decl.items() if not v['enabled']],
			'instances': {},
		}
		for iid, item in insts.items():
			record = {
				'id': iid,
				'platform': plat_id,
				'adapter': item['adapter'],
				'surface': item.get('surface'),
				'label': item.get('label', iid),
				'enabled': item['enabled'],
				'platform_enabled': item['platform_enabled'],
				'instance_enabled': item['instance_enabled'],
				'home': item.get('home'),
				'user_data_dir': item.get('user_data_dir'),
				'disabled_reason': item.get('disabled_reason'),
				'system_paths': deepcopy(item['system_paths']),
			}
			if check_exists:
				record['paths_exist'] = {k: _exists_flag(v) for k, v in item['system_paths'].items()}
			env_entry['instances'][iid] = record
			key = f'{plat_id}:{iid}' if iid in flat else iid
			flat[key] = record
		envs[plat_id] = env_entry
	handoff_targets = [{'id': iid, 'platform': plat_id, 'label': inst['label'], 'home': inst['home'], 'system_paths': inst['system_paths']} for plat_id, env in envs.items() for iid, inst in env['instances'].items() if inst['enabled']]
	return {'environments': envs, 'instances': flat, 'enabled_environments': [p for p, e in envs.items() if e['active']], 'available_handoff_targets': handoff_targets}
# @used-by :func:`find_conversation_instance()`
# @used-by :func:`resolve_antigravity_paths()`
def _antigravity_backend_has_conversation(backend_dir, conversation_id, *, system_paths=None):
	backend = Path(backend_dir) if backend_dir else None
	if not re.fullmatch('[a-f0-9-]{36}', str(conversation_id or '')):
		return False
	sp = system_paths or {}
	brain_dir = Path(sp['brain_dir']) if sp.get('brain_dir') else (backend / 'brain' if backend else None)
	conv_dir = Path(sp['conversations_dir']) if sp.get('conversations_dir') else (backend / 'conversations' if backend else None)
	if (brain_dir and (brain_dir / conversation_id).is_dir()) or (conv_dir and ((conv_dir / f'{conversation_id}.pb').is_file() or (conv_dir / f'{conversation_id}.db').is_file())):
		return True
	db_path = Path(sp['conversations_db']) if sp.get('conversations_db') else (backend / 'conversation_summaries.db' if backend else None)
	if db_path and db_path.is_file():
		try:
			conn = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
			try:
				row = conn.execute('SELECT 1 FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
				return bool(row)
			finally:
				conn.close()
		except sqlite3.Error:
			return False
	return False
# @used-by :func:`agent_tools.meta.builders._collect_codex_issue_ctx()`
# @used-by :func:`find_conversation_instance()`
# @used-by :func:`resolve_codex_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_default_system_paths_overrides_and_nested_codex_globs()`
def _codex_home_conversation_trace(home_dir, conversation_id, *, system_paths=None):
	home = Path(home_dir) if home_dir else None
	if not re.fullmatch('[a-f0-9-]{36}', str(conversation_id or '')):
		return None
	sp = system_paths or {}
	glob_raw = sp.get('state_db_glob')
	if glob_raw:
		db_files = [p for p in _resolve_glob_paths(glob_raw, home) if p.is_file()]
	else:
		db_files = [p for p in sorted(home.glob('state_*.sqlite')) if p.is_file()] if home else []
	for db_file in db_files:
		try:
			conn = sqlite3.connect(db_file.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
			try:
				row = conn.execute('SELECT rollout_path FROM threads WHERE id=?', (conversation_id,)).fetchone()
				if row and row[0]:
					return str(Path(row[0]))
			finally:
				conn.close()
		except sqlite3.Error:
			continue
	sessions = Path(sp['sessions_dir']) if sp.get('sessions_dir') else (home / 'sessions' if home else None)
	if sessions and sessions.is_dir():
		matches = sorted(sessions.rglob(f'*{conversation_id}*.jsonl'))
		if matches:
			return str(matches[0])
	return None
# @used-by :func:`agent_tools.metrics._resolve_target()`
# @used-by :func:`agent_tools.metrics.summarize_instance()`
# @used-by :func:`agent_tools.perf.timesheet_common._lookup_conversation_trace()`
# @used-by :func:`agent_tools.upwork_project.instances_report()`
# @used-by :func:`resolve_antigravity_paths()`
# @used-by :func:`resolve_codex_home()`
# @used-by :func:`resolve_codex_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cross_instance_handoff_and_audit_resolve_antigravity_and_disabled_codex_traces()`
def find_conversation_instance(conversation_id, *, platform=None, config=None, include_disabled=True):
	cfg_all = config or settings()
	if platform:
		resolved_id, resolved_cfg = _resolve_platform_cfg(platform, config=cfg_all)
		if None is resolved_cfg:
			raise ValueError(f'Unknown Upwork platform: {platform}')
		targets = [resolved_id]
	else:
		targets = list(cfg_all['platforms'])
	found = []
	for plat_id in targets:
		plat_cfg = cfg_all['platforms'][plat_id]
		adapter_kind = platform_adapter_name(plat_id, plat_cfg)
		for iid, item in extract_platform_instances(plat_cfg, platform=plat_id, include_disabled=include_disabled).items():
			sp = item['system_paths']
			if 'antigravity' == adapter_kind:
				backend_str = sp.get('backend_dir')
				if (backend_str or sp.get('brain_dir') or sp.get('conversations_dir') or sp.get('conversations_db')) and _antigravity_backend_has_conversation(backend_str, conversation_id, system_paths=sp):
					backend = Path(backend_str) if backend_str else None
					brain_root = Path(sp['brain_dir']) if sp.get('brain_dir') else (backend / 'brain' if backend else None)
					trace = None
					if brain_root:
						logs_dir = brain_root / conversation_id / '.system_generated/logs'
						full_trace = logs_dir / 'transcript_full.jsonl'
						compact_trace = logs_dir / 'transcript.jsonl'
						trace = full_trace if full_trace.is_file() else compact_trace if compact_trace.is_file() else None
					found.append({'id': iid, 'platform': plat_id, 'enabled': item['enabled'], 'backend_dir': str(backend) if backend else None, 'trace_file': str(trace) if trace else None, 'system_paths': sp})
			elif 'codex' == adapter_kind:
				home_str = sp.get('home')
				if home_str or sp.get('state_db_glob') or sp.get('sessions_dir'):
					trace = _codex_home_conversation_trace(home_str, conversation_id, system_paths=sp)
					if trace:
						found.append({'id': iid, 'platform': plat_id, 'enabled': item['enabled'], 'backend_dir': str(Path(home_str)) if home_str else None, 'trace_file': trace, 'system_paths': sp})
	return found
# @used-by :func:`agent_tools.journal_sync_all._resolve_ag_summary_db()`
# @used-by :func:`agent_tools.meta.identity._resolve_ag_paths_safe()`
# @used-by :func:`agent_tools.platforms.antigravity._antigravity_paths()`
# @used-by :func:`agent_tools.shadow_replay._resolve_native_paths()`
# @used-by :func:`check_pre_invocation._resolve_ag_paths()`
# @used-by :func:`check_stop_gate._resolve_stop_paths()`
# @used-by :func:`resolve_antigravity_backend()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_custom_adapter_platform_keys_and_instruction_snapshot()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
def resolve_antigravity_paths(backend=None, *, instance=None, conversation_id=None, config=None):
	cfg_all = config
	if None is cfg_all:
		try:
			cfg_all = settings()
		except (OSError, ValueError):
			if None is backend:
				raise
			cfg_all = None
	ag_plat = platform_key_for_adapter('antigravity', cfg_all) if cfg_all else 'antigravity'
	ag_cfg = ((cfg_all or {}).get('platforms') or {}).get(ag_plat) if ag_plat else None
	ag_insts = extract_platform_instances(ag_cfg, platform=ag_plat, include_disabled=True) if isinstance(ag_cfg, dict) else {}
	explicit_inst = instance or _instance.get() or os.environ.get('UPWORK_INSTANCE')
	matched_entry = None
	if None is not backend:
		backend_p = Path(backend)
		backend_res = backend_p.resolve()
		if explicit_inst and explicit_inst in ag_insts:
			cand = ag_insts[explicit_inst]
			cand_bd = cand['system_paths'].get('backend_dir')
			if cand_bd and Path(cand_bd).resolve() == backend_res:
				matched_entry = cand
		if None is matched_entry:
			matches = [cand for cand in ag_insts.values() if cand['system_paths'].get('backend_dir') and Path(cand['system_paths']['backend_dir']).resolve() == backend_res]
			if 1 == len(matches):
				matched_entry = matches[0]
			elif 1 < len(matches):
				if conversation_id:
					conv_matches = [cand for cand in matches if _antigravity_backend_has_conversation(backend_p, conversation_id, system_paths=cand['system_paths'])]
					if 1 == len(conv_matches):
						matched_entry = conv_matches[0]
					elif 1 < len(conv_matches):
						ids = ', '.join((c['id'] for c in conv_matches))
						raise ValueError(f'Conversation UUID {conversation_id} exists in multiple Antigravity instances ({ids}); pass --instance')
				if None is matched_entry:
					matched_entry = matches[0]
		sp = dict((matched_entry or {}).get('system_paths') or {})
	else:
		# 2026-11-21
		# "Separate OS user home from instance USERPROFILE and auto-detect active Antigravity instance":
		# https://github.com/dmitry-ai/harness/issues/115
		try:
			active_home = Path.home().resolve()
		except RuntimeError:
			active_home = None
		active_home_matches = [cand for cand in ag_insts.values() if None is not active_home and cand.get('home') and Path(cand['home']).resolve() == active_home]
		raw_ad = normalize_path_str(os.environ.get('APPDATA', '')).rstrip('/') if os.environ.get('APPDATA', '').strip() else ''
		in_appdata = False
		if None is not active_home and raw_ad and raw_ad.casefold().endswith('/appdata/roaming'):
			ad_res = Path(raw_ad).resolve()
			in_appdata = active_home == ad_res or ad_res in active_home.parents
		is_redirected_instance_home = None is not active_home and (1 == len(active_home_matches)) and (in_appdata or False is active_home_matches[0].get('primary'))
		if explicit_inst:
			matched_entry = instance_entry(explicit_inst, platform=ag_plat or 'antigravity', config=cfg_all, include_disabled=True)
		elif conversation_id and cfg_all and ag_plat and (ag_plat in cfg_all.get('platforms', {})):
			matches = find_conversation_instance(conversation_id, platform=ag_plat, config=cfg_all, include_disabled=True)
			if 1 == len(matches):
				matched_entry = ag_insts.get(matches[0]['id']) or {'id': matches[0]['id'], 'system_paths': matches[0]['system_paths']}
			elif 1 < len(matches):
				if is_redirected_instance_home and active_home_matches[0]['id'] in {m['id'] for m in matches}:
					matched_entry = ag_insts.get(active_home_matches[0]['id']) or active_home_matches[0]
				else:
					ids = ', '.join((m['id'] for m in matches))
					raise ValueError(f'Conversation UUID {conversation_id} exists in multiple Antigravity instances ({ids}); pass --instance')
		default_ag_backend = Path(default_platform_paths('antigravity')['backend_dir'])
		if None is matched_entry:
			if 1 == len(active_home_matches):
				matched_entry = active_home_matches[0]
			else:
				home_backend = default_ag_backend
				home_res = home_backend.resolve()
				home_matches = [cand for cand in ag_insts.values() if cand['system_paths'].get('backend_dir') and Path(cand['system_paths']['backend_dir']).resolve() == home_res]
				if 1 == len(home_matches):
					matched_entry = home_matches[0]
			backend_p = Path(matched_entry['system_paths']['backend_dir']) if matched_entry and matched_entry['system_paths'].get('backend_dir') else default_ag_backend
		else:
			backend_p = Path(matched_entry['system_paths']['backend_dir']) if matched_entry and matched_entry['system_paths'].get('backend_dir') else default_ag_backend
		sp = dict((matched_entry or {}).get('system_paths') or {})
	backend_res = backend_p.resolve()
	return {
		'instance': matched_entry.get('id') if matched_entry else None,
		'backend_dir': backend_p,
		'brain_dir': Path(sp['brain_dir']) if sp.get('brain_dir') else backend_p / 'brain',
		# 2026-11-22
		# "Auto-name Antigravity conversations from project journal step numbers":
		# https://github.com/dmitry-ai/harness/issues/120
		'annotations_dir': Path(sp['annotations_dir']) if sp.get('annotations_dir') else backend_p / 'annotations',
		'daemon_dir': Path(sp['daemon_dir']) if sp.get('daemon_dir') else backend_p / 'daemon',
		'conversations_dir': Path(sp['conversations_dir']) if sp.get('conversations_dir') else backend_p / 'conversations',
		'conversations_db': Path(sp['conversations_db']) if sp.get('conversations_db') else backend_p / 'conversation_summaries.db',
		'projects_dir': Path(sp['projects_dir']) if sp.get('projects_dir') else backend_res.parent / 'config/projects',
		'folders_json': Path(sp['folders_json']) if sp.get('folders_json') else None,
		'system_paths': sp,
	}
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cross_instance_handoff_and_audit_resolve_antigravity_and_disabled_codex_traces()`
def resolve_antigravity_backend(backend=None, *, instance=None, conversation_id=None, config=None):
	if None is not backend:
		return Path(backend)
	return resolve_antigravity_paths(backend=None, instance=instance, conversation_id=conversation_id, config=config)['backend_dir']
# @used-by :func:`resolve_codex_paths()`
def resolve_codex_home(backend=None, *, instance=None, conversation_id=None, config=None, codex_cfg=None):
	if None is not backend:
		return Path(backend).resolve()
	cfg_all = config or settings()
	cx_plat = platform_key_for_adapter('codex', cfg_all) or 'codex'
	if None is not codex_cfg:
		cfg_all = {**cfg_all, 'platforms': {**cfg_all['platforms'], cx_plat: codex_cfg}}
	if cx_plat not in cfg_all['platforms']:
		raise ValueError('Unknown Upwork platform: codex')
	resolved_codex_cfg = cfg_all['platforms'][cx_plat]
	homes = extract_platform_homes(resolved_codex_cfg, platform=cx_plat, include_disabled=True)
	explicit_profile = _profile.get() or os.environ.get('UPWORK_CODEX_PROFILE')
	if explicit_profile:
		if explicit_profile not in homes:
			raise ValueError('Unknown Codex profile')
		return Path(homes[explicit_profile]).resolve()
	if instance:
		entry = instance_entry(instance, platform=cx_plat, config=cfg_all, include_disabled=True)
		if not entry.get('home'):
			raise ValueError('Unknown Codex profile')
		return Path(entry['home']).resolve()
	context_inst = _instance.get() or os.environ.get('UPWORK_INSTANCE')
	if context_inst and context_inst in homes:
		return Path(homes[context_inst]).resolve()
	if not os.environ.get('CODEX_HOME') and conversation_id:
		matches = find_conversation_instance(conversation_id, platform=cx_plat, config=cfg_all, include_disabled=True)
		if 1 == len(matches) and matches[0].get('backend_dir'):
			return Path(matches[0]['backend_dir']).resolve()
		if 1 < len(matches):
			ids = ', '.join((m['id'] for m in matches))
			raise ValueError(f'Conversation UUID {conversation_id} exists in multiple Codex instances ({ids}); pass --instance or --codex-profile')
	name = profile_name(config=cfg_all, include_disabled=True)
	if name not in homes:
		raise ValueError('Unknown Codex profile')
	return Path(homes[name]).resolve()
# @used-by :func:`agent_tools.meta.identity._resolve_codex_paths_safe()`
# @used-by :func:`agent_tools.platforms.codex._paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_custom_adapter_platform_keys_and_instruction_snapshot()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_dynamic_folders_json_and_cleanup_without_homes()`
def resolve_codex_paths(backend=None, *, instance=None, conversation_id=None, config=None, codex_cfg=None):
	cfg_all = config
	if None is cfg_all:
		try:
			cfg_all = settings()
		except (OSError, ValueError):
			cfg_all = None
	resolved_codex_cfg = codex_cfg
	cx_plat = platform_key_for_adapter('codex', cfg_all) if cfg_all else None
	if None is resolved_codex_cfg and cfg_all and cx_plat:
		resolved_codex_cfg = (cfg_all.get('platforms') or {}).get(cx_plat)
	all_insts = extract_platform_instances(resolved_codex_cfg, platform=cx_plat or 'codex', include_disabled=True) if isinstance(resolved_codex_cfg, dict) else {}
	explicit_id = _profile.get() or os.environ.get('UPWORK_CODEX_PROFILE') or instance or _instance.get() or os.environ.get('UPWORK_INSTANCE')
	matched_entry = None
	home_p = Path(backend).resolve() if None is not backend else None
	if None is home_p:
		if explicit_id and explicit_id in all_insts:
			matched_entry = all_insts[explicit_id]
		elif not os.environ.get('CODEX_HOME') and conversation_id and cfg_all and cx_plat:
			matches = find_conversation_instance(conversation_id, platform=cx_plat, config=cfg_all, include_disabled=True)
			if 1 == len(matches):
				matched_entry = all_insts.get(matches[0]['id']) or {'id': matches[0]['id'], 'home': matches[0].get('backend_dir'), 'system_paths': matches[0]['system_paths']}
			elif 1 < len(matches):
				ids = ', '.join((m['id'] for m in matches))
				raise ValueError(f'Conversation UUID {conversation_id} exists in multiple Codex instances ({ids}); pass --instance or --codex-profile')
		if None is not matched_entry and matched_entry.get('home'):
			home_p = Path(matched_entry['home']).resolve()
		elif None is matched_entry:
			home_p = resolve_codex_home(backend, instance=instance, conversation_id=conversation_id, config=cfg_all, codex_cfg=codex_cfg)
	if None is not home_p:
		if explicit_id and explicit_id in all_insts:
			cand = all_insts[explicit_id]
			if not cand.get('home') or Path(cand['home']).resolve() == home_p:
				matched_entry = cand
		if None is matched_entry:
			matches = [inst for inst in all_insts.values() if inst.get('home') and Path(inst['home']).resolve() == home_p]
			if 1 == len(matches):
				matched_entry = matches[0]
			elif 1 < len(matches):
				if conversation_id:
					conv_matches = [inst for inst in matches if _codex_home_conversation_trace(inst.get('home'), conversation_id, system_paths=inst['system_paths'])]
					if 1 == len(conv_matches):
						matched_entry = conv_matches[0]
				if None is matched_entry:
					matched_entry = matches[0]
	sp = dict((matched_entry or {}).get('system_paths') or {})
	return {
		'instance': matched_entry.get('id') if matched_entry else None,
		'home': home_p,
		'state_db_glob': sp.get('state_db_glob') or ((home_p / 'state_*.sqlite').as_posix() if home_p else None),
		'sessions_dir': Path(sp['sessions_dir']) if sp.get('sessions_dir') else (home_p / 'sessions' if home_p else None),
		'config_toml': Path(sp['config_toml']) if sp.get('config_toml') else (home_p / 'config.toml' if home_p else None),
		'system_paths': sp,
	}
# @used-by :func:`agent_tools.completion._native()`
# @used-by :func:`agent_tools.completion.check_answer()`
# @used-by :func:`agent_tools.completion.issue_first_check_turn()`
# @used-by :func:`agent_tools.completion.tdd_check_turn()`
# @used-by :func:`agent_tools.platforms.adapter()`
# @used-by :func:`agent_tools.registration.register_project()`
# @used-by :func:`agent_tools.registration.register_projects()`
# @used-by :func:`agent_tools.registration.save_registration()`
# @used-by :func:`agent_tools.review.input_receipt()`
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
# @used-by :func:`platform_settings()`
# @used-by :func:`using()`
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.registration_status()`
def platform_name(value=None, *, config=None):
	cfg_all = config or settings()
	plats = cfg_all['platforms']
	name = value or _platform.get() or os.environ.get('UPWORK_PLATFORM')
	if not name:
		inst = _instance.get() or os.environ.get('UPWORK_INSTANCE')
		if inst:
			try:
				name = instance_entry(inst, config=cfg_all, include_disabled=True)['platform']
			except ValueError:
				name = None
	if not name:
		ag_plat = platform_key_for_adapter('antigravity', cfg_all)
		if ag_plat and platform_active(ag_plat, config=cfg_all):
			name = ag_plat
		else:
			active = enabled_platforms(config=cfg_all)
			name = active[0] if active else (ag_plat if ag_plat else next(iter(plats)))
	if name not in plats:
		resolved_key = platform_key_for_adapter(name, cfg_all)
		if not resolved_key:
			raise ValueError(f'Unknown Upwork platform: {name}')
		name = resolved_key
	r = name
	return r
# @used-by :func:`agent_tools.configuration.global_codex_instructions()`
# @used-by :func:`agent_tools.workflow._target_complete()`
# @used-by :func:`registration_profile_name()`
# @used-by :func:`resolve_codex_home()`
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.test_registration_only_fallback_does_not_relax_native_evidence_profile()`
def profile_name(value=None, *, config=None, include_disabled=True):
	cfg_all = config or settings()
	cx_plat = platform_key_for_adapter('codex', cfg_all)
	codex_cfg = cfg_all['platforms'].get(cx_plat) if cx_plat else None
	if not isinstance(codex_cfg, dict):
		raise ValueError('Unknown Upwork platform: codex')
	all_insts = extract_platform_instances(codex_cfg, platform=cx_plat, include_disabled=True)
	homes = extract_platform_homes(codex_cfg, platform=cx_plat, include_disabled=include_disabled)
	explicit_inst = _instance.get() or os.environ.get('UPWORK_INSTANCE')
	if value or _profile.get() or os.environ.get('UPWORK_CODEX_PROFILE'):
		r = value or _profile.get() or os.environ['UPWORK_CODEX_PROFILE']
	elif explicit_inst and explicit_inst in all_insts:
		if not include_disabled and explicit_inst not in homes:
			raise ValueError(f'Codex profile {explicit_inst} is disabled in runtime.json')
		r = explicit_inst
	else:
		current = os.environ.get('CODEX_HOME')
		matches = [name for name, home in homes.items() if current and Path(home).resolve() == Path(current).resolve()]
		if 1 != len(matches):
			choices = '/'.join(homes) if homes else 'none'
			raise ValueError(f'Select --codex-profile {choices} or use a recognized CODEX_HOME')
		r = matches[0]
	return r
# @used-by :func:`agent_tools.platforms.codex.register()`
# @used-by :func:`agent_tools.workflow._target_complete()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_custom_adapter_platform_keys_and_instruction_snapshot()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_platform_enabled_false_disables_all_instances_of_environment()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_single_enabled_codex_instance_works_with_shared_catalog_superset()`
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.test_explicit_unknown_profile_or_unrecognized_home_never_uses_fallback()`
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.test_registration_only_fallback_does_not_relax_native_evidence_profile()`
def registration_profile_name(value=None, *, config=None):
	cfg_all = config or settings()
	cx_plat = platform_key_for_adapter('codex', cfg_all)
	if not cx_plat or cx_plat not in cfg_all['platforms']:
		raise ValueError('Unknown Upwork platform: codex')
	plat_cfg = cfg_all['platforms'][cx_plat]
	enabled_homes = extract_platform_homes(plat_cfg, platform=cx_plat, include_disabled=False)
	all_homes = extract_platform_homes(plat_cfg, platform=cx_plat, include_disabled=True)
	if not enabled_homes:
		raise ValueError('Codex has no enabled instances in runtime.json')
	explicit_inst = _instance.get() or os.environ.get('UPWORK_INSTANCE')
	if value or _profile.get() or os.environ.get('UPWORK_CODEX_PROFILE') or os.environ.get('CODEX_HOME') or (explicit_inst and explicit_inst in all_homes):
		name = profile_name(value, config=cfg_all, include_disabled=True)
	else:
		name = plat_cfg.get('registration_profile')
		if not name:
			default_inst = [iid for iid, item in extract_platform_instances(plat_cfg, platform=cx_plat, include_disabled=False).items() if item.get('default_registration')]
			if 1 == len(default_inst):
				name = default_inst[0]
		if not name:
			raise ValueError('Select a Codex registration profile or configure registration_profile')
	if name not in all_homes:
		raise ValueError(f'Unknown Codex registration profile: {name}')
	if name not in enabled_homes:
		raise ValueError(f'Codex registration profile {name} is disabled in runtime.json')
	r = name
	return r
# @used-by :func:`agent_tools.meta.identity._resolve_codex_paths_safe()`
# @used-by :func:`agent_tools.platforms.antigravity._native_invocation()`
# @used-by :func:`agent_tools.platforms.codex._paths()`
# @used-by :func:`agent_tools.platforms.codex.native_tool_trace()`
# @used-by :func:`agent_tools.platforms.codex.shared_control()`
# @used-by :func:`agent_tools.platforms.codex.verify_native_proof()`
# @used-by :func:`agent_tools.text_browser.resolve_cdp_port()`
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :func:`role_settings()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.selected()`
# @used-by :meth:`test_portability.CodexEvidenceTests.selected()`
# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
def platform_settings(name=None):
	return deepcopy(settings()['platforms'][platform_name(name)])
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
def role_settings(platform, role, seen=()):
	if role in seen:
		raise ValueError('Cyclic model role inheritance')
	plat = platform_settings(platform)
	roles = plat.get('roles') or {}
	if role not in roles:
		raise ValueError(f'Missing role {role} for platform {platform}')
	value = roles[role]
	fallback = value.get('inherit') or value.get('fallback')
	if fallback:
		r = {**role_settings(platform, fallback, (*seen, role)), **{k: v for k, v in value.items() if 'inherit' != k}}
	else:
		if value.get('selection') not in ('parent', 'inherit') and (not value.get('model') or not value.get('effort')):
			raise ValueError(f'Missing model/effort for {platform}/{role}')
		r = value
	return r
# @used-by :func:`agent_tools.upwork_project.main()`
# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_discovery_failure_with_conversations_is_preserved_without_an_issue()`
# @used-by :meth:`test_cleanup.CleanupTests.test_preview_is_read_only_and_apply_cleans_both_platforms_preserving_entire_archive()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_native_workspace_supports_self_review_and_empty_metadata_keeps_legacy_job_id()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.selected()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_future_environment_claude_code_is_supported_without_roles_or_adapters()`
# @used-by :meth:`test_portability.CodexEvidenceTests.selected()`
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.test_registration_only_fallback_does_not_relax_native_evidence_profile()`
@contextmanager
def using(platform=None, profile=None, instance=None):
	first, second, third = (_platform.set(platform_name(platform)), _profile.set(profile), _instance.set(instance))
	try:
		yield
	finally:
		_platform.reset(first)
		_profile.reset(second)
		_instance.reset(third)
# @used-by :func:`agent_tools.platforms.antigravity.register_antigravity_project()`
# @used-by :func:`agent_tools.platforms.codex.register()`
# @used-by :func:`agent_tools.project_rename._sync_antigravity_native_files()`
# @used-by :func:`agent_tools.registration._expected()`
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
def request_day(value=None):
	from datetime import date, datetime
	from zoneinfo import ZoneInfo
	r = date.fromisoformat(value) if value else datetime.now(ZoneInfo(settings()['timezone'])).date()
	return r
# 2026-11-23
# "Configure default user locale for language-neutral commands in TEXT-1 and locale gate":
# https://github.com/dmitry-ai/harness/issues/131
# @used-by :func:`agent_tools.completion._intermediate_or_language_issues()`
# @used-by :func:`check_pre_invocation._format_turn_begin_message()`
# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_language_neutral_slash_commands_enforce_user_default_locale_without_breaking_english_requests()`
def default_user_locale(config=None) -> str | None:
	cfg_all = config
	if None is cfg_all:
		try:
			cfg_all = settings()
		except (OSError, ValueError):
			return None
	val = (cfg_all or {}).get('user_default_locale')
	return val.strip() if isinstance(val, str) and val.strip() else None
# 2026-11-19
# "Integrate declarative Antigravity addons health and sanctioning into Harness":
# https://github.com/dmitry-ai/harness/issues/92
# 2026-11-24
# "Cache runtime settings and deduplicate evidence validation in hot paths":
# https://github.com/dmitry-ai/harness/issues/227
# @used-by :func:`agent_tools.addon_observability._touches_antigravity_addons()`
# @used-by :func:`agent_tools.gates.cdp_bypass._is_inside_sanctioned_code()`
# @used-by :func:`agent_tools.shell_audit._is_sanctioned_addon_command()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_sanctioned_addon_roots_and_cdp_bypass_gate()`
def sanctioned_addon_code_roots(config=None):
	import sys
	from .runtime_cache import cached_addon_roots
	return cached_addon_roots(config, sys.modules[__name__], _expand_path)
