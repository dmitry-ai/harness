# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
CONTEXT_INSTANCE: ContextVar[str | None] = ContextVar('upwork_instance', default=None)
CONTEXT_PLATFORM: ContextVar[str | None] = ContextVar('upwork_platform', default=None)
CONTEXT_PROFILE: ContextVar[str | None] = ContextVar('upwork_profile', default=None)
# @used-by :func:`_load_cfg()`
# @used-by :func:`dfh_default_user_locale()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_runtime_tail()`
def _default_settings() -> dict:
	from Df.Harness.Runtime.SettingsLoader import SettingsLoader
	return SettingsLoader().run()
# @used-by :func:`dfh_platform_name()`
# @used-by :func:`dfh_platform_settings()`
# @used-by :func:`dfh_profile_name()`
# @used-by :func:`dfh_registration_profile_name()`
# @used-by :func:`dfh_request_day()`
def _load_cfg(config: dict | None, settings_fn: Any) -> dict:
	return config if config else (settings_fn or _default_settings)()
# @used-by :func:`dfh_platform_name()`
def _pick_default_platform(cfg_all: dict, plats: dict, settings_fn: Any) -> str:
	from Df.Harness.lib.runtime_instances import dfh_enabled_platforms, dfh_platform_active, dfh_platform_key_for_adapter
	ag_plat = dfh_platform_key_for_adapter('antigravity', cfg_all, settings_fn=settings_fn)
	if ag_plat and dfh_platform_active(ag_plat, config=cfg_all, settings_fn=settings_fn):
		r = ag_plat
	else:
		active = dfh_enabled_platforms(config=cfg_all, settings_fn=settings_fn)
		r = active[0] if active else (ag_plat if ag_plat else next(iter(plats)))
	return r
# @used-by :func:`dfh_profile_name()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_runtime_tail()`
def _resolve_profile_from_codex_home(homes: dict[str, str]) -> str:
	current = os.environ.get('CODEX_HOME')
	matches = [name for name, home in homes.items() if current and Path(home).resolve() == Path(current).resolve()]
	if 1 != len(matches):
		choices = '/'.join(homes) if homes else 'none'
		raise ValueError(f'Select --codex-profile {choices} or use a recognized CODEX_HOME')
	return matches[0]
# @used-by :func:`dfh_registration_profile_name()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_runtime_tail()`
def _resolve_registration_default(plat_cfg: dict, cx_plat: str) -> str:
	from Df.Harness.lib.runtime_instances import dfh_extract_platform_instances
	name = plat_cfg.get('registration_profile')
	if not name:
		default_inst = [iid for iid, item in dfh_extract_platform_instances(plat_cfg, platform=cx_plat, include_disabled=False).items() if item.get('default_registration')]
		if 1 == len(default_inst):
			name = default_inst[0]
	if not name:
		raise ValueError('Select a Codex registration profile or configure registration_profile')
	return name
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_intermediate_or_language_issues()`
# @used-by :func:`Df.Harness.lib.hook_pre_invocation_ops.dfh_format_turn_begin_message()`
# @used-by :func:`agent_tools.runtime.default_user_locale()`
def dfh_default_user_locale(config: dict | None=None, *, settings_fn: Any=None) -> str | None:
	cfg_all = config
	r: str | None = None
	if None is cfg_all:
		try:
			cfg_all = (settings_fn or _default_settings)()
		except (OSError, ValueError):
			cfg_all = None
	val = (cfg_all or {}).get('user_default_locale')
	if isinstance(val, str) and val.strip():
		r = val.strip()
	return r
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_check_answer()`
# @used-by :func:`Df.Harness.lib.completion_core.dfh_native_scan()`
# @used-by :func:`Df.Harness.lib.completion_recovery._scan_readonly_turn()`
# @used-by :func:`agent_tools.runtime.platform_name()`
# @used-by :func:`dfh_platform_settings()`
# @used-by :func:`dfh_using()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__init_result()`
def dfh_platform_name(value: str | None=None, *, config: dict | None=None, settings_fn: Any=None) -> str:
	from Df.Harness.lib.runtime_instances import dfh_instance_entry, dfh_platform_key_for_adapter
	cfg_all = _load_cfg(config, settings_fn)
	plats = cfg_all['platforms']
	name = value or CONTEXT_PLATFORM.get() or os.environ.get('UPWORK_PLATFORM')
	if not name:
		inst = CONTEXT_INSTANCE.get() or os.environ.get('UPWORK_INSTANCE')
		if inst:
			try:
				name = dfh_instance_entry(inst, config=cfg_all, include_disabled=True, settings_fn=settings_fn)['platform']
			except ValueError:
				name = None
	if not name:
		name = _pick_default_platform(cfg_all, plats, settings_fn)
	if name not in plats:
		resolved_key = dfh_platform_key_for_adapter(name, cfg_all, settings_fn=settings_fn)
		if not resolved_key:
			raise ValueError(f'Unknown Upwork platform: {name}')
		name = resolved_key
	return name
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_native_invocation()`
# @used-by :func:`Df.Harness.lib.codex_control.dfh_shared_control()`
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_paths()`
# @used-by :func:`agent_tools.runtime.platform_settings()`
# @used-by :func:`dfh_role_settings()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.ProofVerifier.ProofVerifier.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.ToolTraceReader.ToolTraceReader.run()`
def dfh_platform_settings(name: str | None=None, *, settings_fn: Any=None) -> dict:
	cfg_all = _load_cfg(None, settings_fn)
	return deepcopy(cfg_all['platforms'][dfh_platform_name(name, config=cfg_all, settings_fn=settings_fn)])
# @used-by :func:`Df.Harness.lib.config_codex.dfh_global_codex_instructions()`
# @used-by :func:`Df.Harness.lib.runtime_resolve._resolve_codex_home_by_conv_or_profile()`
# @used-by :func:`agent_tools.runtime.profile_name()`
# @used-by :func:`dfh_registration_profile_name()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
def dfh_profile_name(value: str | None=None, *, config: dict | None=None, include_disabled: bool=True, settings_fn: Any=None) -> str:
	from Df.Harness.lib.runtime_instances import dfh_extract_platform_homes, dfh_extract_platform_instances, dfh_platform_key_for_adapter
	cfg_all = _load_cfg(config, settings_fn)
	cx_plat = dfh_platform_key_for_adapter('codex', cfg_all, settings_fn=settings_fn)
	codex_cfg = cfg_all['platforms'].get(cx_plat) if cx_plat else None
	if not isinstance(codex_cfg, dict):
		raise ValueError('Unknown Upwork platform: codex')
	all_insts = dfh_extract_platform_instances(codex_cfg, platform=cx_plat, include_disabled=True)
	homes = dfh_extract_platform_homes(codex_cfg, platform=cx_plat, include_disabled=include_disabled)
	explicit_prof = value or CONTEXT_PROFILE.get() or os.environ.get('UPWORK_CODEX_PROFILE')
	explicit_inst = CONTEXT_INSTANCE.get() or os.environ.get('UPWORK_INSTANCE')
	if explicit_prof:
		r = explicit_prof
	elif explicit_inst and explicit_inst in all_insts:
		if not include_disabled and explicit_inst not in homes:
			raise ValueError(f'Codex profile {explicit_inst} is disabled in runtime.json')
		r = explicit_inst
	else:
		r = _resolve_profile_from_codex_home(homes)
	return r
# @used-by :func:`agent_tools.runtime.registration_profile_name()`
# @used-by :meth:`Df.Harness.Platform.Codex.ProjectRegistrar.ProjectRegistrar.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
def dfh_registration_profile_name(value: str | None=None, *, config: dict | None=None, settings_fn: Any=None) -> str:
	from Df.Harness.lib.runtime_instances import dfh_extract_platform_homes, dfh_platform_key_for_adapter
	cfg_all = _load_cfg(config, settings_fn)
	cx_plat = dfh_platform_key_for_adapter('codex', cfg_all, settings_fn=settings_fn)
	if not cx_plat or cx_plat not in cfg_all['platforms']:
		raise ValueError('Unknown Upwork platform: codex')
	plat_cfg = cfg_all['platforms'][cx_plat]
	enabled_homes = dfh_extract_platform_homes(plat_cfg, platform=cx_plat, include_disabled=False)
	all_homes = dfh_extract_platform_homes(plat_cfg, platform=cx_plat, include_disabled=True)
	if not enabled_homes:
		raise ValueError('Codex has no enabled instances in runtime.json')
	explicit_inst = CONTEXT_INSTANCE.get() or os.environ.get('UPWORK_INSTANCE')
	has_explicit = bool(value or CONTEXT_PROFILE.get() or os.environ.get('UPWORK_CODEX_PROFILE') or os.environ.get('CODEX_HOME') or (explicit_inst and explicit_inst in all_homes))
	name = dfh_profile_name(value, config=cfg_all, include_disabled=True, settings_fn=settings_fn) if has_explicit else _resolve_registration_default(plat_cfg, cx_plat)
	if name not in all_homes:
		raise ValueError(f'Unknown Codex registration profile: {name}')
	if name not in enabled_homes:
		raise ValueError(f'Codex registration profile {name} is disabled in runtime.json')
	return name
# @used-by :func:`agent_tools.runtime.request_day()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__resolve_day()`
# @used-by :meth:`Df.Harness.Platform.Codex.ProjectRegistrar.ProjectRegistrar.run()`
def dfh_request_day(value: str | None=None, *, settings_fn: Any=None) -> date:
	return date.fromisoformat(value) if value else datetime.now(ZoneInfo(_load_cfg(None, settings_fn)['timezone'])).date()
# @used-by :func:`agent_tools.runtime.role_settings()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
def dfh_role_settings(platform: str, role: str, seen: tuple[str, ...]=(), *, settings_fn: Any=None) -> dict:
	if role in seen:
		raise ValueError('Cyclic model role inheritance')
	roles = dfh_platform_settings(platform, settings_fn=settings_fn).get('roles') or {}
	if role not in roles:
		raise ValueError(f'Missing role {role} for platform {platform}')
	value = roles[role]
	fallback = value.get('inherit') or value.get('fallback')
	if fallback:
		r = {**dfh_role_settings(platform, fallback, (*seen, role), settings_fn=settings_fn), **{k: v for k, v in value.items() if 'inherit' != k}}
	else:
		if value.get('selection') not in ('parent', 'inherit') and (not value.get('model') or not value.get('effort')):
			raise ValueError(f'Missing model/effort for {platform}/{role}')
		r = value
	return r
# @used-by :func:`agent_tools.runtime.using()`
@contextmanager
def dfh_using(platform: str | None=None, profile: str | None=None, instance: str | None=None, *, settings_fn: Any=None):
	first, second, third = (CONTEXT_PLATFORM.set(dfh_platform_name(platform, settings_fn=settings_fn)), CONTEXT_PROFILE.set(profile), CONTEXT_INSTANCE.set(instance))
	try:
		yield
	finally:
		CONTEXT_PLATFORM.reset(first)
		CONTEXT_PROFILE.reset(second)
		CONTEXT_INSTANCE.reset(third)
