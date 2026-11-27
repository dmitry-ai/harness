# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_discovery import dfh_default_platform_paths
from Df.Harness.lib.path_template import dfh_normalize_path_str
from Df.Harness.lib.runtime_context import CONTEXT_INSTANCE, CONTEXT_PROFILE, dfh_profile_name
from Df.Harness.lib.runtime_conversations import dfh_antigravity_backend_has_conversation, dfh_codex_home_conversation_trace, dfh_find_conversation_instance, dfh_safe_load_cfg
from Df.Harness.lib.runtime_instances import dfh_extract_platform_homes, dfh_extract_platform_instances, dfh_instance_entry, dfh_platform_key_for_adapter
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_ag_entry_from_auto()`
def _active_home_match_info(ag_insts: dict) -> tuple[list[dict], bool]:
	try:
		active_home: Path | None = Path.home().resolve()
	except RuntimeError:
		active_home = None
	matches = [cand for cand in ag_insts.values() if None is not active_home and cand.get('home') and Path(cand['home']).resolve() == active_home]
	raw_ad = dfh_normalize_path_str(os.environ.get('APPDATA', '')).rstrip('/') if os.environ.get('APPDATA', '').strip() else ''
	in_appdata = False
	if None is not active_home and raw_ad and raw_ad.casefold().endswith('/appdata/roaming'):
		ad_res = Path(raw_ad).resolve()
		in_appdata = active_home == ad_res or ad_res in active_home.parents
	redirected = None is not active_home and 1 == len(matches) and (in_appdata or False is matches[0].get('primary'))
	return (matches, redirected)
# @used-by :func:`dfh_resolve_antigravity_paths()`
def _ag_entry_for_explicit_backend(backend_p: Path, ag_insts: dict, explicit_inst: str | None, conversation_id: str | None) -> dict | None:
	backend_res = backend_p.resolve()
	matched: dict | None = None
	if explicit_inst and explicit_inst in ag_insts:
		cand = ag_insts[explicit_inst]
		cand_bd = cand['system_paths'].get('backend_dir')
		if cand_bd and Path(cand_bd).resolve() == backend_res:
			matched = cand
	if None is matched:
		matches = [cand for cand in ag_insts.values() if cand['system_paths'].get('backend_dir') and Path(cand['system_paths']['backend_dir']).resolve() == backend_res]
		if 1 == len(matches):
			matched = matches[0]
		elif 1 < len(matches):
			matched = _disambiguate_ag_matches(matches, backend_p, conversation_id)
	return matched
# @used-by :func:`dfh_resolve_antigravity_paths()`
def _ag_entry_from_auto(ag_insts: dict, ag_plat: str | None, cfg_all: dict | None, explicit_inst: str | None, conversation_id: str | None, settings_fn: Any, find_conv_fn: Any, instances_fn: Any) -> tuple[dict | None, Path]:
	active_matches, redirected = _active_home_match_info(ag_insts)
	matched: dict | None = None
	if explicit_inst:
		matched = dfh_instance_entry(explicit_inst, platform=ag_plat or 'antigravity', config=cfg_all, include_disabled=True, settings_fn=settings_fn, instances_fn=instances_fn)
	elif conversation_id and cfg_all and ag_plat and ag_plat in cfg_all.get('platforms', {}):
		matched = _match_ag_conversation(ag_insts, ag_plat, cfg_all, conversation_id, active_matches, redirected, find_conv_fn)
	default_ag = Path(dfh_default_platform_paths('antigravity')['backend_dir'])
	if None is matched:
		matched = _match_ag_home_fallback(ag_insts, active_matches, default_ag)
	backend_p = Path(matched['system_paths']['backend_dir']) if matched and matched['system_paths'].get('backend_dir') else default_ag
	return (matched, backend_p)
# @used-by :func:`dfh_resolve_antigravity_paths()`
def _build_ag_paths_dict(matched: dict | None, backend_p: Path) -> dict:
	sp = dict((matched or {}).get('system_paths') or {})
	backend_res = backend_p.resolve()
	return {
		'annotations_dir': _sp_path(sp, 'annotations_dir', backend_p / 'annotations'),
		'backend_dir': backend_p,
		'brain_dir': _sp_path(sp, 'brain_dir', backend_p / 'brain'),
		'conversations_db': _sp_path(sp, 'conversations_db', backend_p / 'conversation_summaries.db'),
		'conversations_dir': _sp_path(sp, 'conversations_dir', backend_p / 'conversations'),
		'daemon_dir': _sp_path(sp, 'daemon_dir', backend_p / 'daemon'),
		'folders_json': _sp_path(sp, 'folders_json', None),
		'instance': matched.get('id') if matched else None,
		'projects_dir': _sp_path(sp, 'projects_dir', backend_res.parent / 'config/projects'),
		'system_paths': sp,
	}
# @used-by :func:`dfh_resolve_codex_paths()`
def _build_codex_paths_dict(matched: dict | None, home_p: Path | None) -> dict:
	sp = dict((matched or {}).get('system_paths') or {})
	return {
		'config_toml': _sp_path(sp, 'config_toml', home_p / 'config.toml' if home_p else None),
		'home': home_p,
		'instance': matched.get('id') if matched else None,
		'sessions_dir': _sp_path(sp, 'sessions_dir', home_p / 'sessions' if home_p else None),
		'state_db_glob': sp.get('state_db_glob') or ((home_p / 'state_*.sqlite').as_posix() if home_p else None),
		'system_paths': sp,
	}
# @used-by :func:`_resolve_codex_pair()`
def _codex_entry_for_home(home_p: Path, all_insts: dict, explicit_id: str | None, conversation_id: str | None) -> dict | None:
	matched: dict | None = None
	if explicit_id and explicit_id in all_insts:
		cand = all_insts[explicit_id]
		if not cand.get('home') or Path(cand['home']).resolve() == home_p:
			matched = cand
	if None is matched:
		matched = _codex_match_by_home_dir(home_p, all_insts, conversation_id)
	return matched
# @used-by :func:`_resolve_codex_pair()`
def _codex_entry_from_auto(all_insts: dict, cx_plat: str | None, cfg_all: dict | None, explicit_id: str | None, conversation_id: str | None, find_conv_fn: Any) -> dict | None:
	matched: dict | None = None
	if explicit_id and explicit_id in all_insts:
		matched = all_insts[explicit_id]
	elif not os.environ.get('CODEX_HOME') and conversation_id and cfg_all and cx_plat:
		finder = find_conv_fn or dfh_find_conversation_instance
		matches = finder(conversation_id, platform=cx_plat, config=cfg_all, include_disabled=True)
		if 1 == len(matches):
			matched = all_insts.get(matches[0]['id']) or {'home': matches[0].get('backend_dir'), 'id': matches[0]['id'], 'system_paths': matches[0]['system_paths']}
		elif 1 < len(matches):
			ids = ', '.join((m['id'] for m in matches))
			raise ValueError(f'Conversation UUID {conversation_id} exists in multiple Codex instances ({ids}); pass --instance or --codex-profile')
	return matched
# @used-by :func:`_codex_entry_for_home()`
def _codex_match_by_home_dir(home_p: Path, all_insts: dict, conversation_id: str | None) -> dict | None:
	matches = [inst for inst in all_insts.values() if inst.get('home') and Path(inst['home']).resolve() == home_p]
	r: dict | None = None
	if 1 == len(matches):
		r = matches[0]
	elif 1 < len(matches):
		conv_matches = [inst for inst in matches if dfh_codex_home_conversation_trace(inst.get('home'), conversation_id, system_paths=inst['system_paths'])] if conversation_id else []
		r = conv_matches[0] if 1 == len(conv_matches) else matches[0]
	return r
# @used-by :func:`_ag_entry_for_explicit_backend()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_runtime_tail()`
def _disambiguate_ag_matches(matches: list[dict], backend_p: Path, conversation_id: str | None) -> dict:
	matched: dict | None = None
	if conversation_id:
		conv_matches = [cand for cand in matches if dfh_antigravity_backend_has_conversation(backend_p, conversation_id, system_paths=cand['system_paths'])]
		if 1 == len(conv_matches):
			matched = conv_matches[0]
		elif 1 < len(conv_matches):
			ids = ', '.join((c['id'] for c in conv_matches))
			raise ValueError(f'Conversation UUID {conversation_id} exists in multiple Antigravity instances ({ids}); pass --instance')
	return matched if None is not matched else matches[0]
# @used-by :func:`_ag_entry_from_auto()`
def _match_ag_conversation(ag_insts: dict, ag_plat: str, cfg_all: dict, conversation_id: str, active_matches: list[dict], redirected: bool, find_conv_fn: Any) -> dict | None:
	finder = find_conv_fn or dfh_find_conversation_instance
	matches = finder(conversation_id, platform=ag_plat, config=cfg_all, include_disabled=True)
	r: dict | None = None
	if 1 == len(matches):
		r = ag_insts.get(matches[0]['id']) or {'id': matches[0]['id'], 'system_paths': matches[0]['system_paths']}
	elif 1 < len(matches):
		if redirected and active_matches[0]['id'] in {m['id'] for m in matches}:
			r = ag_insts.get(active_matches[0]['id']) or active_matches[0]
		else:
			ids = ', '.join((m['id'] for m in matches))
			raise ValueError(f'Conversation UUID {conversation_id} exists in multiple Antigravity instances ({ids}); pass --instance')
	return r
# @used-by :func:`_ag_entry_from_auto()`
def _match_ag_home_fallback(ag_insts: dict, active_matches: list[dict], default_ag: Path) -> dict | None:
	r: dict | None = None
	if 1 == len(active_matches):
		r = active_matches[0]
	else:
		home_res = default_ag.resolve()
		home_matches = [cand for cand in ag_insts.values() if cand['system_paths'].get('backend_dir') and Path(cand['system_paths']['backend_dir']).resolve() == home_res]
		if 1 == len(home_matches):
			r = home_matches[0]
	return r
# @used-by :func:`_resolve_codex_home_choice()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_runtime_tail()`
def _resolve_codex_home_by_conv_or_profile(homes: dict[str, str], cx_plat: str, cfg_all: dict, conversation_id: str | None, settings_fn: Any, find_conv_fn: Any) -> Path:
	r: Path | None = None
	if not os.environ.get('CODEX_HOME') and conversation_id:
		finder = find_conv_fn or dfh_find_conversation_instance
		matches = finder(conversation_id, platform=cx_plat, config=cfg_all, include_disabled=True)
		if 1 == len(matches) and matches[0].get('backend_dir'):
			r = Path(matches[0]['backend_dir']).resolve()
		elif 1 < len(matches):
			ids = ', '.join((m['id'] for m in matches))
			raise ValueError(f'Conversation UUID {conversation_id} exists in multiple Codex instances ({ids}); pass --instance or --codex-profile')
	if None is r:
		name = dfh_profile_name(config=cfg_all, include_disabled=True, settings_fn=settings_fn)
		if name not in homes:
			raise ValueError('Unknown Codex profile')
		r = Path(homes[name]).resolve()
	return r
# @used-by :func:`dfh_resolve_codex_home()`
def _resolve_codex_home_choice(homes: dict[str, str], cx_plat: str, cfg_all: dict, instance: str | None, conversation_id: str | None, settings_fn: Any, find_conv_fn: Any, instances_fn: Any) -> Path:
	explicit_prof = CONTEXT_PROFILE.get() or os.environ.get('UPWORK_CODEX_PROFILE')
	context_inst = CONTEXT_INSTANCE.get() or os.environ.get('UPWORK_INSTANCE')
	if explicit_prof:
		if explicit_prof not in homes:
			raise ValueError('Unknown Codex profile')
		r = Path(homes[explicit_prof]).resolve()
	elif instance:
		entry = dfh_instance_entry(instance, platform=cx_plat, config=cfg_all, include_disabled=True, settings_fn=settings_fn, instances_fn=instances_fn)
		if not entry.get('home'):
			raise ValueError('Unknown Codex profile')
		r = Path(entry['home']).resolve()
	elif context_inst and context_inst in homes:
		r = Path(homes[context_inst]).resolve()
	else:
		r = _resolve_codex_home_by_conv_or_profile(homes, cx_plat, cfg_all, conversation_id, settings_fn, find_conv_fn)
	return r
# @used-by :func:`dfh_resolve_codex_paths()`
def _resolve_codex_pair(backend: Any, all_insts: dict, cx_plat: str | None, cfg_all: dict | None, explicit_id: str | None, instance: str | None, conversation_id: str | None, codex_cfg: dict | None, settings_fn: Any, find_conv_fn: Any, instances_fn: Any) -> tuple[dict | None, Path | None]:
	matched: dict | None = None
	home_p = Path(backend).resolve() if None is not backend else None
	if None is home_p:
		matched = _codex_entry_from_auto(all_insts, cx_plat, cfg_all, explicit_id, conversation_id, find_conv_fn)
		if None is not matched:
			home_p = Path(matched['home']).resolve() if matched.get('home') else None
		else:
			home_p = dfh_resolve_codex_home(backend, instance=instance, conversation_id=conversation_id, config=cfg_all, codex_cfg=codex_cfg, settings_fn=settings_fn, find_conv_fn=find_conv_fn, instances_fn=instances_fn)
	if None is not home_p:
		matched = _codex_entry_for_home(home_p, all_insts, explicit_id, conversation_id) or matched
	return (matched, home_p)
# @used-by :func:`_build_ag_paths_dict()`
# @used-by :func:`_build_codex_paths_dict()`
def _sp_path(sp: dict, key: str, default: Path | None) -> Path | None:
	return Path(sp[key]) if sp.get(key) else default
# @used-by :func:`agent_tools.runtime.resolve_antigravity_backend()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
def dfh_resolve_antigravity_backend(backend: Any=None, *, instance: str | None=None, conversation_id: str | None=None, config: dict | None=None, settings_fn: Any=None, find_conv_fn: Any=None, instances_fn: Any=None) -> Path:
	return Path(backend) if None is not backend else dfh_resolve_antigravity_paths(backend=None, instance=instance, conversation_id=conversation_id, config=config, settings_fn=settings_fn, find_conv_fn=find_conv_fn, instances_fn=instances_fn)['backend_dir']
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_antigravity_paths()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._match_ag_instance_by_transcript()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._resolve_ag_from_settings()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_resolve_ag_summary_db()`
# @used-by :func:`agent_tools.runtime.resolve_antigravity_paths()`
# @used-by :func:`dfh_resolve_antigravity_backend()`
# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.__resolve_native_paths()`
def dfh_resolve_antigravity_paths(backend: Any=None, *, instance: str | None=None, conversation_id: str | None=None, config: dict | None=None, settings_fn: Any=None, find_conv_fn: Any=None, instances_fn: Any=None) -> dict:
	cfg_all = dfh_safe_load_cfg(config, settings_fn, reraise=None is backend)
	ag_plat = dfh_platform_key_for_adapter('antigravity', cfg_all, settings_fn=settings_fn) if cfg_all else 'antigravity'
	ag_cfg = ((cfg_all or {}).get('platforms') or {}).get(ag_plat) if ag_plat else None
	ag_insts = dfh_extract_platform_instances(ag_cfg, platform=ag_plat, include_disabled=True) if isinstance(ag_cfg, dict) else {}
	explicit_inst = instance or CONTEXT_INSTANCE.get() or os.environ.get('UPWORK_INSTANCE')
	if None is not backend:
		backend_p = Path(backend)
		matched = _ag_entry_for_explicit_backend(backend_p, ag_insts, explicit_inst, conversation_id)
	else:
		matched, backend_p = _ag_entry_from_auto(ag_insts, ag_plat, cfg_all, explicit_inst, conversation_id, settings_fn, find_conv_fn, instances_fn)
	return _build_ag_paths_dict(matched, backend_p)
# @used-by :func:`_resolve_codex_pair()`
# @used-by :func:`agent_tools.runtime.resolve_codex_home()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
def dfh_resolve_codex_home(backend: Any=None, *, instance: str | None=None, conversation_id: str | None=None, config: dict | None=None, codex_cfg: dict | None=None, settings_fn: Any=None, find_conv_fn: Any=None, instances_fn: Any=None) -> Path:
	if None is not backend:
		r = Path(backend).resolve()
	else:
		cfg_all = dfh_safe_load_cfg(config, settings_fn, reraise=True) or {}
		cx_plat = dfh_platform_key_for_adapter('codex', cfg_all, settings_fn=settings_fn) or 'codex'
		if None is not codex_cfg:
			cfg_all = {**cfg_all, 'platforms': {**cfg_all['platforms'], cx_plat: codex_cfg}}
		if cx_plat not in cfg_all['platforms']:
			raise ValueError('Unknown Upwork platform: codex')
		homes = dfh_extract_platform_homes(cfg_all['platforms'][cx_plat], platform=cx_plat, include_disabled=True)
		r = _resolve_codex_home_choice(homes, cx_plat, cfg_all, instance, conversation_id, settings_fn, find_conv_fn, instances_fn)
	return r
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_paths()`
# @used-by :func:`agent_tools.runtime.resolve_codex_paths()`
def dfh_resolve_codex_paths(backend: Any=None, *, instance: str | None=None, conversation_id: str | None=None, config: dict | None=None, codex_cfg: dict | None=None, settings_fn: Any=None, find_conv_fn: Any=None, instances_fn: Any=None) -> dict:
	cfg_all = dfh_safe_load_cfg(config, settings_fn)
	cx_plat = dfh_platform_key_for_adapter('codex', cfg_all, settings_fn=settings_fn) if cfg_all else None
	rcfg = codex_cfg if None is not codex_cfg else (((cfg_all or {}).get('platforms') or {}).get(cx_plat) if cfg_all and cx_plat else None)
	all_insts = dfh_extract_platform_instances(rcfg, platform=cx_plat or 'codex', include_disabled=True) if isinstance(rcfg, dict) else {}
	explicit_id = CONTEXT_PROFILE.get() or os.environ.get('UPWORK_CODEX_PROFILE') or instance or CONTEXT_INSTANCE.get() or os.environ.get('UPWORK_INSTANCE')
	matched, home_p = _resolve_codex_pair(backend, all_insts, cx_plat, cfg_all, explicit_id, instance, conversation_id, codex_cfg, settings_fn, find_conv_fn, instances_fn)
	return _build_codex_paths_dict(matched, home_p)
