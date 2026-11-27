# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from typing import Any
from Df.Harness.Config.NativeProfile.Applier import Applier
from Df.Harness.Config.NativeProfile.ManagedLink import ManagedLink
from Df.Harness.Config.NativeProfile.Plan import Plan
from Df.Harness.lib.config_blocks import dfh_is_linked_path, dfh_load_project_receipt, dfh_receipt_sha256
from Df.Harness.lib.native_ag_plan import dfh_antigravity_plan, dfh_legacy_project_projection_paths, dfh_profile_state, dfh_role_values, dfh_shared_plan, dfh_skills
from Df.Harness.lib.native_codex_roles import dfh_compact_loader, dfh_disable_codex_bundled_chrome_plugin, dfh_legacy_role, dfh_legacy_skill, dfh_plan_codex_link, dfh_profile_agents, dfh_retire_profile_roles, dfh_retire_profile_skills, dfh_retire_shared_roles, dfh_role_config
from Df.Harness.lib.native_links import dfh_absolute, dfh_configuration, dfh_direct_link_matches_target, dfh_hash, dfh_is_relocated_owned_link, dfh_json_bytes, dfh_load_state, dfh_normalized_text, dfh_relocated_primaries, dfh_same_path
from Df.Harness.lib.path_resolve import dfh_var_value
from Df.Harness.lib.runtime_instances import dfh_extract_platform_instances
from Df.Harness.lib.storage import dfh_data_dir_for, dfh_locked
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_codex_plan()`
def _plan_codex_agents_md(plan: Plan, profile: dict, previous: dict, home: Path, primary: Path) -> None:
	path = home / 'AGENTS.md'
	try:
		text = path.read_bytes().decode('utf-8') if path.is_file() else ''
		wanted = dfh_profile_agents(text, primary, previous).encode('utf-8')
		plan.file(path, wanted)
		profile['files'][str(path)] = dfh_hash(wanted)
		profile['managed_block_sha256'] = dfh_hash(dfh_compact_loader(primary).rstrip('\n').encode('utf-8'))
	except (ValueError, OSError) as exc:
		plan.issue(path, str(exc))
# @used-by :func:`dfh_codex_plan()`
def _plan_codex_config_toml(plan: Plan, profile: dict, previous: dict, home: Path, primary: Path, state: dict, settings_fn: Any) -> None:
	definitions = {agent: {'config_file': (Path(primary) / f'platforms/codex/agents/{agent}.toml').as_posix(), 'description': purpose} for _, agent, purpose, _ in dfh_role_values(primary, settings_fn=settings_fn)}
	path = home / 'config.toml'
	try:
		actual = path.read_bytes() if path.is_file() else b''
		wanted = dfh_disable_codex_bundled_chrome_plugin(dfh_role_config(actual.decode('utf-8-sig'), definitions, previous, state, path, primary)).encode('utf-8')
		if actual.startswith(b'\xef\xbb\xbf'):
			wanted = b'\xef\xbb\xbf' + wanted
		if actual or wanted or path.exists():
			plan.file(path, wanted)
			profile['files'][str(path)] = dfh_hash(wanted)
	except (ValueError, OSError) as exc:
		plan.issue(path, str(exc))
# @used-by :func:`dfh_codex_plan()`
def _plan_codex_roles(plan: Plan, profile: dict, prior_links: dict, prior_roles: dict, home: Path, primary: Path, relocated: tuple[Path, ...], settings_fn: Any, ops: dict | None) -> None:
	for role, agent, purpose, _ in dfh_role_values(primary, settings_fn=settings_fn):
		role_path, role_target = (home / f'agents/{agent}.toml', Path(primary) / f'platforms/codex/agents/{agent}.toml')
		profile['role_targets'][str(dfh_absolute(role_path))] = str(role_target)
		prior_t = prior_roles.get(str(dfh_absolute(role_path))) or prior_links.get(str(dfh_absolute(role_path)))
		rel_ts = {dfh_absolute(rc / f'platforms/codex/agents/{agent}.toml') for rc in relocated}
		dfh_plan_codex_link(plan, profile, ManagedLink(role_path, role_target, 'file-symlink', label='role', ops=ops), lambda p=role_path, t=role_target: p.is_symlink() and p.is_file() and dfh_same_path(p, t) and dfh_direct_link_matches_target(p, t) and (p.read_bytes() == t.read_bytes()), 'Role link points to a different or missing file; preserved', role_path, lambda p=role_path, rl=role, ag=agent, pr=purpose: p.is_file() and dfh_normalized_text(p.read_text(encoding='utf-8-sig')) == dfh_normalized_text(dfh_legacy_role(primary, rl, ag, pr, settings_fn=settings_fn)), 'Legacy role differs from its exact generated template; preserved', relocated_valid=lambda p=role_path, pt=prior_t, t=role_target, rts=rel_ts: p.is_symlink() and dfh_is_relocated_owned_link(p, pt, t, rts), ops=ops)
# @used-by :func:`dfh_codex_plan()`
def _plan_codex_skills(plan: Plan, profile: dict, prior_links: dict, home: Path, primary: Path, skills: dict, relocated: tuple[Path, ...], ops: dict | None) -> None:
	for skill, (source, _) in skills.items():
		skill_path, skill_target = (home / 'skills' / skill, source.parent.resolve())
		wrapper = skill_path / 'SKILL.md'
		prior_t = prior_links.get(str(dfh_absolute(skill_path)))
		rel_ts = {dfh_absolute(rc / 'skills' / skill) for rc in relocated}
		dfh_plan_codex_link(plan, profile, ManagedLink(skill_path, skill_target, 'directory', label='skill', ops=ops), lambda p=skill_path, t=skill_target: p.is_dir() and dfh_same_path(p, t) and dfh_direct_link_matches_target(p, t), 'Skill link points to a different or missing directory; preserved', wrapper, lambda p=skill_path, w=wrapper, s=skill: p.is_dir() and ['SKILL.md'] == sorted((c.name for c in p.iterdir())) and (not dfh_is_linked_path(w)) and w.is_file() and (dfh_normalized_text(w.read_text(encoding='utf-8-sig')) == dfh_normalized_text(dfh_legacy_skill(s, primary))), 'Existing skill directory is not an exact generated wrapper; preserved', relocated_valid=lambda p=skill_path, pt=prior_t, t=skill_target, rts=rel_ts: dfh_is_relocated_owned_link(p, pt, t, rts), ops=ops)
# @used-by :func:`dfh_install_native_profiles()`
def _resolve_install_pools(platforms_cfg: dict, config_dirs: dict | None, codex_homes: dict | None) -> tuple[dict, dict, dict, dict]:
	if None is config_dirs:
		ag_all = dfh_extract_platform_instances(platforms_cfg.get('antigravity') or {}, platform='antigravity', include_disabled=True)
		g_all = {name: Path(inst['system_paths']['config_dir']) for name, inst in ag_all.items() if 'config_dir' in inst['system_paths']}
		g_en = {name: path for name, path in g_all.items() if ag_all[name]['enabled']}
	else:
		g_all = g_en = {name: Path(path) for name, path in config_dirs.items()}
	if None is codex_homes:
		cx_all = dfh_extract_platform_instances(platforms_cfg.get('codex') or {}, platform='codex', include_disabled=True)
		c_all = {name: Path(inst['home']) for name, inst in cx_all.items() if inst.get('home')}
		c_en = {name: path for name, path in c_all.items() if cx_all[name]['enabled']}
	else:
		c_all = c_en = {name: Path(path) for name, path in codex_homes.items()}
	if set(g_all) & set(c_all):
		raise ValueError('Antigravity and Codex profile identifiers must be distinct')
	return (g_all, g_en, c_all, c_en)
# @used-by :func:`dfh_install_native_profiles()`
def _resolve_target_names(target_profiles: Any, platforms_cfg: dict, g_all: dict, g_en: dict, c_all: dict, c_en: dict, config_dirs: Any, codex_homes: Any) -> tuple[list[str], list[str]]:
	all_declared = list(dict.fromkeys([*g_all, *c_all]))
	if None is target_profiles:
		names = list(dict.fromkeys([*g_en, *c_en]))
		if not all_declared and ('antigravity' in platforms_cfg or 'codex' in platforms_cfg):
			raise ValueError('Select existing target profile names from runtime.json')
	else:
		names = list(dict.fromkeys(target_profiles))
		missing = any((name not in g_all and name not in c_all for name in names))
		if missing or ((None is config_dirs or None is codex_homes) and (not names)):
			raise ValueError('Select existing target profile names from runtime.json')
	if len({dfh_absolute(g_all[name] if name in g_all else c_all[name]) for name in names}) != len(names):
		raise ValueError('Selected profile configuration directories must be distinct')
	return (all_declared, names)
# @used-by :func:`agent_tools.native_profiles.build_shared_native()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_disabled()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_enabled()`
def dfh_build_shared_native(primary: str | Path | None=None, *, check: bool=False, settings_fn: Any=None, ops: dict | None=None) -> dict:
	prim_p = Path(primary if None is not primary else dfh_var_value('HARNESS_CODE')).resolve()
	with nullcontext() if check else dfh_locked(dfh_data_dir_for(prim_p) / 'native-profiles/install.lock'):
		state, plan = (dfh_load_state(prim_p), Plan())
		dfh_shared_plan(plan, prim_p, state, settings_fn=settings_fn)
		dfh_retire_shared_roles(plan, prim_p, state)
		r = Applier(plan, prim_p, state, check=check, ops=ops).run()
	return r
# @used-by :func:`agent_tools.native_profiles._codex_plan()`
# @used-by :func:`dfh_install_native_profiles()`
def dfh_codex_plan(plan: Plan, name: str, home: str | Path, primary: Path, state: dict, *, settings_fn: Any=None, ops: dict | None=None) -> None:
	home_abs = dfh_absolute(home)
	previous = dfh_profile_state(state, name, home_abs)
	relocated = dfh_relocated_primaries(primary)
	profile: dict[str, Any] = {'files': {}, 'links': {}, 'path': str(home_abs), 'platform': 'codex', 'retired': list(previous.get('retired', [])), 'role_registration': 'file-links', 'role_targets': {}}
	dfh_retire_profile_roles(plan, profile, previous, home_abs, primary, state, settings_fn=settings_fn, ops=ops)
	skills = dfh_skills(primary)
	dfh_retire_profile_skills(plan, profile, previous, home_abs, primary, skills, ops=ops)
	_plan_codex_agents_md(plan, profile, previous, home_abs, primary)
	_plan_codex_config_toml(plan, profile, previous, home_abs, primary, state, settings_fn)
	prior_links = previous.get('links') if isinstance(previous.get('links'), dict) else {}
	prior_roles = previous.get('role_targets') if isinstance(previous.get('role_targets'), dict) else {}
	_plan_codex_skills(plan, profile, prior_links, home_abs, primary, skills, relocated, ops)
	_plan_codex_roles(plan, profile, prior_links, prior_roles, home_abs, primary, relocated, settings_fn, ops)
	plan.profiles[name] = profile
# @used-by :func:`agent_tools.native_profiles.install_native_profiles()`
def dfh_install_native_profiles(target_profiles: Any=None, *, check: bool=False, primary: str | Path | None=None, config_dirs: dict | None=None, codex_homes: dict | None=None, git_ignore_path: Any=None, settings_fn: Any=None, ops: dict | None=None) -> dict:
	from agent_tools.git_ignore import finalize_install_result
	prim_p = Path(primary if None is not primary else dfh_var_value('HARNESS_CODE')).resolve()
	platforms_cfg = dfh_configuration(prim_p, settings_fn=settings_fn).get('platforms') or {}
	g_all, g_en, c_all, c_en = _resolve_install_pools(platforms_cfg, config_dirs, codex_homes)
	all_declared, names = _resolve_target_names(target_profiles, platforms_cfg, g_all, g_en, c_all, c_en, config_dirs, codex_homes)
	with nullcontext() if check else dfh_locked(dfh_data_dir_for(prim_p) / 'native-profiles/install.lock'):
		state, plan = (dfh_load_state(prim_p), Plan())
		dfh_shared_plan(plan, prim_p, state, settings_fn=settings_fn)
		for name in names:
			if name in g_all:
				dfh_antigravity_plan(plan, name, g_all[name], prim_p, state, settings_fn=settings_fn)
			else:
				dfh_codex_plan(plan, name, c_all[name], prim_p, state, settings_fn=settings_fn, ops=ops)
		dfh_retire_shared_roles(plan, prim_p, state)
		r = finalize_install_result(Applier(plan, prim_p, state, check=check, ops=ops).run(), all_declared, names, prim_p, check=check, git_ignore_path=git_ignore_path)
	return r
# @used-by :func:`agent_tools.native_profiles.retire_owned_project_projections()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_native_builder_and_projection_publisher()`
def dfh_retire_owned_project_projections(root: str | Path, *, check: bool=False, primary: str | Path | None=None, settings_fn: Any=None, ops: dict | None=None) -> dict:
	prim_p = Path(primary if None is not primary else dfh_var_value('HARNESS_CODE')).resolve()
	root_p = Path(root).resolve()
	receipt, _, previous = dfh_load_project_receipt(root_p)
	with nullcontext() if check else dfh_locked(dfh_data_dir_for(prim_p) / 'native-profiles/install.lock'):
		state, plan, remaining = (dfh_load_state(prim_p), Plan(), deepcopy(previous))
		for path in dfh_legacy_project_projection_paths(root_p, prim_p, settings_fn=settings_fn):
			if path.is_file():
				if dfh_receipt_sha256(previous.get(str(path.resolve()))) != dfh_hash(path.read_bytes()):
					plan.issue(path, 'Legacy project projection is edited or unowned; preserved')
				else:
					plan.file(path, None)
					remaining.pop(str(path.resolve()), None)
		if remaining != previous:
			plan.file(receipt, dfh_json_bytes(remaining) if remaining else None)
		r = Applier(plan, prim_p, state, check=check, ops=ops).run()
	return r
