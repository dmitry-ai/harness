# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir, dfh_discover_overlay_file
from Df.Harness.lib.path_state import DEFAULT_REGISTRY_FILE, DISCOVERY_STATE, dfh_get_ttl_overlay_links, dfh_mark_overlay_links_refreshed, dfh_overlay_signature_for_roots
from Df.Harness.lib.path_template import EXCLUDED_PROJECT_IDS, INITIAL_HOME, TOKEN_RE, dfh_escape_template_literal, dfh_expand_template, dfh_glob_parent_stat, dfh_lookup_env, dfh_normalize_path_str, dfh_path_key
from Df.Harness.lib.uri import dfh_extract_resource_uri, dfh_local_uri_to_path
import glob
import json
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_derive_ag_ctx_vars()`
def _add_ag_defaults(ctx_vars: dict[str, str], explicit: dict[str, str], defaults: dict[str, str], home_norm: str | None, env: dict[str, str] | None) -> None:
	gem = explicit.get('gemini_dir')
	if not gem and home_norm and defaults.get('gemini_dir'):
		gem = dfh_expand_template(defaults['gemini_dir'], ctx_vars, env=env, normalize=True)
	if gem:
		ctx_vars['INSTANCE_GEMINI_DIR'] = gem
	cfg = _resolve_ag_cfg_dir(ctx_vars, explicit, defaults, gem, env)
	if cfg:
		ctx_vars['INSTANCE_CONFIG_DIR'] = cfg
	bd = _resolve_ag_backend_dir(ctx_vars, explicit, defaults, gem, env)
	if bd:
		ctx_vars['INSTANCE_BACKEND_DIR'] = bd
# @used-by :func:`dfh_candidate_discovery_roots()`
def _collect_candidate_dirs(reg: Any, idx_str: str | None, daily_str: str | None, has_idx: bool) -> tuple[Path, ...]:
	cands, seen = ([], set())
	push = lambda p: (seen.add(dfh_path_key(p)), cands.append(p)) if dfh_path_key(p) not in seen else None
	for r_str in reg.overlay_discovery_roots:
		if Path(r_str).is_dir():
			push(Path(r_str).resolve())
	for g_str in reg.overlay_discovery_globs:
		for match in sorted(glob.glob(g_str)):
			if Path(match).is_dir():
				push(Path(match).resolve())
	if has_idx:
		_collect_index_roots(reg, idx_str, daily_str, push)
	return tuple(cands)
# @used-by :func:`_collect_candidate_dirs()`
def _collect_index_roots(reg: Any, idx_str: str | None, daily_str: str | None, push_fn) -> None:
	if isinstance(idx_str, str) and isinstance(daily_str, str) and Path(daily_str).is_dir():
		try:
			entries = json.loads(Path(idx_str).read_text(encoding='utf-8'))
		except (OSError, ValueError):
			entries = None
		if isinstance(entries, dict):
			daily_dir = Path(daily_str)
			for rel in entries.values():
				_push_index_entry(reg, daily_dir, rel, push_fn)
# @used-by :func:`dfh_is_registered_single_project()`
def _collect_projects_dirs(reg: Any, projects_dirs: Any) -> list[Path]:
	if None is not projects_dirs:
		r = [Path(d) for d in projects_dirs if d]
	else:
		r = _runtime_ag_projects_dirs()
		if not r:
			try:
				p_dir = dfh_default_platform_paths('antigravity', registry=reg).get('projects_dir')
				if p_dir:
					r = [Path(p_dir)]
			except Exception:
				pass
	return r
# @used-by :func:`dfh_default_platform_paths()`
def _default_user_home_vars(reg: Any) -> dict[str, str] | None:
	r: dict[str, str] | None = None
	if None is reg.env:
		try:
			r = {'USER_HOME': dfh_escape_template_literal(Path.home().as_posix())}
		except RuntimeError:
			r = None
	else:
		proc_h = dfh_lookup_env('USERPROFILE', reg.env)
		if proc_h:
			r = {'USER_HOME': dfh_escape_template_literal(proc_h)}
	return r
# @used-by :func:`dfh_derive_platform_system_paths()`
def _derive_ag_ctx_vars(adapter_kind: str, layout: dict[str, Any], explicit: dict[str, str], home_norm: str | None, udd_norm: str | None, reg: Any) -> dict[str, str]:
	ctx_vars = dict(reg.raw_variables)
	if home_norm:
		ctx_vars['INSTANCE_HOME'] = home_norm
	if udd_norm:
		ctx_vars['INSTANCE_USER_DATA'] = udd_norm
	if 'antigravity' == adapter_kind:
		_add_ag_defaults(ctx_vars, explicit, layout.get('defaults') or {}, home_norm, reg.env)
	return ctx_vars
# @used-by :func:`dfh_derive_platform_system_paths()`
def _expand_platform_slots(layout: dict[str, Any], ctx_vars: dict[str, str], env: dict[str, str] | None) -> dict[str, str]:
	out: dict[str, str] = {}
	for slot_key, tpl in (layout.get('system_paths') or {}).items():
		needed = [m.group(1).strip() for m in TOKEN_RE.finditer(tpl) if m.group(1) and (not m.group(1).strip().upper().startswith('ENV:'))]
		if all((v in ctx_vars for v in needed)):
			out[slot_key] = dfh_expand_template(tpl, ctx_vars, env=env, normalize=True)
	return out
# @used-by :func:`_finalize_platform_paths()`
def _fill_ag_derived_parents(paths_out: dict[str, str]) -> None:
	if 'gemini_dir' not in paths_out:
		if 'config_dir' in paths_out and 'config' == Path(paths_out['config_dir']).name:
			paths_out['gemini_dir'] = Path(paths_out['config_dir']).parent.as_posix()
		elif 'backend_dir' in paths_out and 'antigravity' == Path(paths_out['backend_dir']).name:
			paths_out['gemini_dir'] = Path(paths_out['backend_dir']).parent.as_posix()
	if 'home' not in paths_out and 'config_dir' in paths_out:
		cfg_p = Path(paths_out['config_dir'])
		if 'config' == cfg_p.name and '.gemini' == cfg_p.parent.name:
			paths_out['home'] = cfg_p.parent.parent.as_posix()
# @used-by :func:`dfh_derive_platform_system_paths()`
def _finalize_platform_paths(adapter_kind: str, paths_out: dict[str, str], plat_cfg: dict[str, Any], explicit: dict[str, str], reg: Any) -> dict[str, str]:
	keys = ('folders_json', 'addons_profiles_json') if 'antigravity' == adapter_kind else (('ui_manage',) if 'codex' == adapter_kind else ())
	for key in keys:
		if isinstance(plat_cfg.get(key), str) and plat_cfg[key].strip():
			paths_out[key] = reg.expand(plat_cfg[key])
	paths_out.update(explicit)
	if 'antigravity' == adapter_kind:
		_fill_ag_derived_parents(paths_out)
	return paths_out
# @used-by :func:`dfh_find_local_marker_root()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
def _match_journal_fallback(bounded: list[tuple[int, Path]], reg: Any, journal_name: str) -> tuple[int | None, Path | None]:
	r: tuple[int | None, Path | None] = (None, None)
	for idx, anc in bounded:
		if anc.name == journal_name and anc.parent.is_dir() and dfh_path_key(anc.parent) not in reg.workspace_overrides:
			r = (idx, anc.parent)
			break
		if (anc / journal_name).is_dir():
			r = (idx, anc)
			break
	return r
# @used-by :func:`dfh_find_local_marker_root()`
def _match_primary_marker(anc: Path, reg: Any, names: dict[str, str]) -> Path | None:
	r: Path | None = None
	if anc.name in (names['agent'], names['journal']) and anc.parent.name == names['meta'] and anc.parent.parent.is_dir():
		r = dfh_canonicalize_root_dir(anc.parent.parent, reg)
	elif (anc / names['meta']).is_dir() and ((anc / 'code').is_dir() or (anc / names['meta'] / names['journal']).is_dir() or (anc / names['meta'] / names['agent']).is_dir()):
		r = dfh_canonicalize_root_dir(anc, reg)
	elif (anc / names['agent'] / 'project.json').is_file() or (anc / names['agent']).is_dir() or (anc / '.agents').is_dir():
		r = anc
	elif (anc.name == names['agent'] and anc.parent.is_dir() and dfh_path_key(anc.parent) not in reg.workspace_overrides) or ('.agents' == anc.name and anc.parent.is_dir()) or (anc.name == names['book'] and anc.parent.is_dir() and dfh_path_key(anc.parent) not in reg.workspace_overrides):
		r = dfh_canonicalize_root_dir(anc.parent, reg)
	elif (anc / names['book']).is_dir() or (anc / names['art'] / names['art_out']).is_dir() or (anc / names['art'] / names['art_in']).is_dir() or (anc / 'Artifacts' / names['art_out']).is_dir() or (anc / 'Artifacts' / names['art_in']).is_dir():
		r = anc
	return r
# @used-by :func:`dfh_is_registered_single_project()`
def _project_file_matches_root(pf: Path, target_key: str, reg: Any) -> bool:
	r = False
	if pf.stem.casefold() not in EXCLUDED_PROJECT_IDS:
		try:
			data = json.loads(pf.read_text(encoding='utf-8-sig'))
		except (OSError, ValueError):
			data = None
		if isinstance(data, dict) and str(data.get('id') or '').strip().casefold() not in EXCLUDED_PROJECT_IDS:
			resources = (data.get('projectResources') or {}).get('resources') if isinstance(data.get('projectResources'), dict) else None
			uri = dfh_extract_resource_uri(resources[0]) if isinstance(resources, list) and 1 == len(resources) else None
			if uri:
				try:
					r = dfh_path_key(dfh_canonicalize_root_dir(dfh_local_uri_to_path(uri), reg)) == target_key
				except (OSError, ValueError):
					r = False
	return r
# @used-by :func:`_collect_index_roots()`
def _push_index_entry(reg: Any, daily_dir: Path, rel: Any, push_fn) -> None:
	if isinstance(rel, str) and rel.strip():
		cand = (daily_dir / rel).resolve()
		if cand.is_dir():
			push_fn(cand)
		elif dfh_path_key(cand) in reg.relocations:
			reloc = Path(reg.relocations[dfh_path_key(cand)]).resolve()
			if reloc.is_dir():
				push_fn(reloc)
# @used-by :func:`_add_ag_defaults()`
def _resolve_ag_backend_dir(ctx_vars: dict[str, str], explicit: dict[str, str], defaults: dict[str, str], gem: str | None, env: dict[str, str] | None) -> str | None:
	bd = explicit.get('backend_dir') or next((Path(explicit[k]).parent.as_posix() for k in ('conversations_db', 'brain_dir', 'conversations_dir', 'annotations_dir', 'knowledge_dir') if k in explicit), None)
	if not bd and gem and defaults.get('backend_dir'):
		bd = dfh_expand_template(defaults['backend_dir'], ctx_vars, env=env, normalize=True)
	return bd
# @used-by :func:`_add_ag_defaults()`
def _resolve_ag_cfg_dir(ctx_vars: dict[str, str], explicit: dict[str, str], defaults: dict[str, str], gem: str | None, env: dict[str, str] | None) -> str | None:
	cfg = explicit.get('config_dir')
	if not cfg:
		if 'projects_dir' in explicit and 'projects' == Path(explicit['projects_dir']).name:
			cfg = Path(explicit['projects_dir']).parent.as_posix()
		elif gem and defaults.get('config_dir'):
			cfg = dfh_expand_template(defaults['config_dir'], ctx_vars, env=env, normalize=True)
	return cfg
# @used-by :func:`dfh_derive_platform_system_paths()`
def _resolve_initial_home(adapter_kind: str, explicit: dict[str, str], home: str | Path | None) -> str | None:
	has_wc = lambda s: '*' in str(s or '') or '?' in str(s or '')
	raw_home = explicit.get('home') if 'home' in explicit else (str(home) if home else None)
	r = dfh_normalize_path_str(raw_home) if isinstance(raw_home, str) and raw_home.strip() and (not has_wc(raw_home)) else None
	if None is r and 'codex' == adapter_kind:
		for key in ('config_toml', 'agents_md', 'session_index', 'global_state', 'ui_folders', 'logs_db', 'memories_db', 'models_cache_json', 'sessions_dir', 'agents_dir', 'skills_dir', 'state_db_glob'):
			if key in explicit and (not has_wc(Path(explicit[key]).parent)):
				r = Path(explicit[key]).parent.as_posix()
				break
	return r
# @used-by :func:`_collect_projects_dirs()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
def _runtime_ag_projects_dirs() -> list[Path]:
	dirs: list[Path] = []
	seen: set[str] = set()
	try:
		from Df.Harness.Runtime.SettingsLoader import SettingsLoader
		from Df.Harness.lib.runtime_instances import dfh_platform_instances
		cfg = SettingsLoader().run()
		if 'antigravity' in (cfg.get('platforms') or {}):
			for inst in dfh_platform_instances('antigravity', config=cfg, include_disabled=False).values():
				raw_d = (inst.get('system_paths') or {}).get('projects_dir')
				if raw_d and dfh_path_key(Path(raw_d)) not in seen:
					seen.add(dfh_path_key(Path(raw_d)))
					dirs.append(Path(raw_d))
	except Exception:
		pass
	return dirs
# @used-by :func:`dfh_refresh_known_overlay_links()`
def _scan_overlay_links(candidate_roots: tuple[Path, ...], reg: Any) -> tuple[dict[str, Path], dict[str, list[Path]]]:
	from Df.Harness.Path.ProjectPaths import ProjectPaths
	links, similar_links = ({}, {})
	for root_p in candidate_roots:
		rk = dfh_path_key(root_p)
		try:
			if None is not dfh_discover_overlay_file(root_p, reg):
				pp = ProjectPaths(root_p, registry=reg, _register_links=False)
				for ext in (*pp.linked_roots, *pp.code_repos, *pp.auxiliary_repos.values()):
					if dfh_path_key(ext) != rk:
						links[dfh_path_key(ext)] = root_p
				for sp in pp.direct_similar_projects:
					sk = dfh_path_key(sp)
					if sk != rk and all((dfh_path_key(prev) != rk for prev in similar_links.get(sk, ()))):
						similar_links.setdefault(sk, []).append(root_p)
		except (OSError, ValueError):
			continue
	return (links, similar_links)
# @used-by :func:`agent_tools.path_registry._candidate_discovery_roots()`
# @used-by :func:`dfh_refresh_known_overlay_links()`
def dfh_candidate_discovery_roots(reg: Any) -> tuple[tuple, tuple[Path, ...]]:
	idx_str, daily_str = (reg.harness_stores.get('upwork_projects_index'), reg.resolved_variables.get('UPWORK_DAILY_ROOT'))
	try:
		st = os.stat(idx_str) if isinstance(idx_str, str) else None
		idx_stat = (st.st_mtime_ns, st.st_size) if None is not st else None
	except OSError:
		idx_stat = None
	roots_key = (reg.source_path.as_posix(), idx_stat, tuple((dfh_glob_parent_stat(g) for g in reg.overlay_discovery_globs)), tuple(((r_s, os.path.isdir(r_s)) for r_s in reg.overlay_discovery_roots)))
	if DISCOVERY_STATE['roots_key'] == roots_key:
		r = (roots_key, DISCOVERY_STATE['candidate_roots'])
	else:
		frozen = _collect_candidate_dirs(reg, idx_str, daily_str, None is not idx_stat)
		DISCOVERY_STATE['roots_key'], DISCOVERY_STATE['candidate_roots'] = (roots_key, frozen)
		r = (roots_key, frozen)
	return r
# @used-by :func:`Df.Harness.lib.ag_metadata._match_log_path_to_instance()`
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_proof_paths()`
# @used-by :func:`Df.Harness.lib.cleanup_lifecycle_ops._probe_disabled_ag_db()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._fallback_default_ag_paths()`
# @used-by :func:`Df.Harness.lib.runtime_resolve._ag_entry_from_auto()`
# @used-by :func:`_collect_projects_dirs()`
# @used-by :func:`agent_tools.path_registry.default_platform_paths()`
# @used-by :func:`agent_tools.platforms.antigravity._proof_paths()`
# @used-by :meth:`Df.Harness.Cleanup.StoreResolver.StoreResolver.__resolve_ag_instance()`
# @used-by :meth:`Df.Harness.Cleanup.StoreResolver.StoreResolver.__resolve_ag_single()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ToolTraceReader.ToolTraceReader.__resolve_paths()`
# @used-by :mod:`agent_tools.platforms.antigravity`
def dfh_default_platform_paths(adapter_kind: str, *, home: str | Path | None=None, user_data_dir: str | Path | None=None, registry: Any=None) -> dict[str, str]:
	from Df.Harness.lib.path_resolve import dfh_load_registry
	reg = registry or dfh_load_registry()
	layout = reg.platform_layouts.get(adapter_kind) or {}
	extra_vars = _default_user_home_vars(reg) if None is home else None
	fallback_home = dfh_normalize_path_str(Path.home().as_posix()) if None is reg.env else INITIAL_HOME
	eff_home = dfh_normalize_path_str(str(home)) if None is not home else (reg.expand(layout['default_home'], extra_vars) if layout.get('default_home') else fallback_home)
	eff_udd = dfh_normalize_path_str(str(user_data_dir)) if None is not user_data_dir else (reg.expand(layout['default_user_data_dir'], extra_vars) if layout.get('default_user_data_dir') else None)
	return dfh_derive_platform_system_paths(adapter_kind, None, home=eff_home, user_data_dir=eff_udd, registry=reg)
# @used-by :func:`Df.Harness.lib.runtime_instances.dfh_default_system_paths()`
# @used-by :func:`agent_tools.path_registry.derive_platform_system_paths()`
# @used-by :func:`dfh_default_platform_paths()`
def dfh_derive_platform_system_paths(adapter_kind: str, explicit_paths: dict[str, str] | None=None, *, home: str | Path | None=None, user_data_dir: str | Path | None=None, plat_cfg: dict[str, Any] | None=None, registry: Any=None) -> dict[str, str]:
	from Df.Harness.lib.path_resolve import dfh_load_registry
	reg = registry or dfh_load_registry()
	layout, explicit, pcfg = (reg.platform_layouts.get(adapter_kind), dict(explicit_paths or {}), plat_cfg if isinstance(plat_cfg, dict) else {})
	if not isinstance(layout, dict):
		r = {**({'home': dfh_normalize_path_str(str(home))} if home else {}), **({'user_data_dir': dfh_normalize_path_str(str(user_data_dir))} if user_data_dir else {}), **explicit}
	else:
		home_norm = _resolve_initial_home(adapter_kind, explicit, home)
		raw_udd = explicit.get('user_data_dir') if 'user_data_dir' in explicit else (str(user_data_dir) if user_data_dir else None)
		udd_norm = dfh_normalize_path_str(raw_udd) if isinstance(raw_udd, str) and raw_udd.strip() and ('*' not in raw_udd) and ('?' not in raw_udd) else None
		ctx_vars = _derive_ag_ctx_vars(adapter_kind, layout, explicit, home_norm, udd_norm, reg)
		r = _finalize_platform_paths(adapter_kind, _expand_platform_slots(layout, ctx_vars, reg.env), pcfg, explicit, reg)
	return r
# @used-by :func:`Df.Harness.lib.path_resolve._resolve_from_markers_or_reverse()`
def dfh_find_local_marker_root(start: Path, reg: Any) -> tuple[int | None, Path | None]:
	rv = reg.resolved_variables
	names = {'agent': rv.get('AGENT_DIR_NAME', '\ua616'), 'art': rv.get('ARTIFACTS_DIR_NAME', '\u2c0f'), 'art_in': rv.get('ARTIFACTS_IN_DIR_NAME', '\u227a'), 'art_out': rv.get('ARTIFACTS_OUT_DIR_NAME', '\u227b'), 'book': rv.get('BOOK_DIR_NAME', '\U0001f56e'), 'journal': rv.get('JOURNAL_DIR_NAME', '\ua66e'), 'meta': rv.get('META_DIR_NAME', '_')}
	bounded: list[tuple[int, Path]] = []
	for idx, anc in enumerate((start, *start.parents)):
		if dfh_path_key(anc) in reg.workspace_overrides and anc != start:
			break
		bounded.append((idx, anc))
	r: tuple[int | None, Path | None] = (None, None)
	for idx, anc in bounded:
		hit = _match_primary_marker(anc, reg, names)
		if None is not hit:
			r = (idx, hit)
			break
	if None is r[0]:
		r = _match_journal_fallback(bounded, reg, names['journal'])
	return r
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_is_tracked_workspace()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
def dfh_is_registered_single_project(canon: Path, *, registry: Any, projects_dirs: Any=None) -> bool:
	target_key = dfh_path_key(canon)
	r = False
	for pdir in _collect_projects_dirs(registry, projects_dirs):
		if not pdir.is_dir():
			continue
		try:
			files = sorted(pdir.glob('*.json'))
		except OSError:
			files = []
		if any((_project_file_matches_root(pf, target_key, registry) for pf in files)):
			r = True
			break
	return r
# @used-by :func:`Df.Harness.lib.path_resolve._resolve_from_markers_or_reverse()`
# @used-by :func:`agent_tools.path_registry._refresh_known_overlay_links()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.similar_projects()`
def dfh_refresh_known_overlay_links(reg: Any, *, candidate_roots_fn: Any=None, default_registry_file: Path=DEFAULT_REGISTRY_FILE) -> dict[str, Path]:
	ttl_links = dfh_get_ttl_overlay_links(reg, default_registry_file, DISCOVERY_STATE)
	if None is not ttl_links:
		r = ttl_links
	else:
		roots_key, candidate_roots = (candidate_roots_fn or dfh_candidate_discovery_roots)(reg)
		fp = (roots_key, dfh_overlay_signature_for_roots(candidate_roots, reg.overlay_candidates), tuple(((g['id'], tuple((m['project'] for m in g['members']))) for g in reg.similar_project_groups)))
		if DISCOVERY_STATE['fingerprint'] != fp:
			links, similar_links = _scan_overlay_links(candidate_roots, reg)
			DISCOVERY_STATE.update({'fingerprint': fp, 'links': links, 'similar_links': similar_links})
		dfh_mark_overlay_links_refreshed(reg, default_registry_file)
		r = dict(DISCOVERY_STATE['links'])
	return r
