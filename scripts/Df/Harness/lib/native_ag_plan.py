# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
from Df.Harness.Path.CacheStore import CacheStore
from Df.Harness.Runtime.LauncherRenderer import LauncherRenderer
from Df.Harness.lib.config_blocks import DISCOVERY_KINDS, dfh_frontmatter, dfh_has_linked_ancestor, dfh_load_discovery_manifest, dfh_resolve_manifest_entry
from Df.Harness.lib.config_codex import dfh_loader
from Df.Harness.lib.native_links import ISSUE, PURPOSES, dfh_absolute, dfh_configuration, dfh_hash, dfh_json_bytes, dfh_relocated_primaries, dfh_same_path
from Df.Harness.lib.path_resolve import dfh_var_value
from Df.Harness.lib.runtime_launcher_templates import HOOK_RUNNER_HEADER
import json
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_manifest()`
def _manifest_build_inherits(inherits: list, config: Path, shared: Path, relocated_shared: list[Path]) -> list:
	already = False
	new_inherits: list = []
	for entry in inherits:
		source, has_extra = dfh_resolve_manifest_entry(config, entry)
		if None is not source and (dfh_same_path(source, shared) or any((dfh_same_path(source, rs) for rs in relocated_shared))):
			if has_extra:
				raise ValueError('Filtered inherited Harness manifest needs explicit reconciliation; preserved')
			if not already:
				new_inherits.append({'path': shared.as_posix()})
				already = True
		else:
			new_inherits.append(entry)
	if not already:
		new_inherits.append({'path': shared.as_posix()})
	return new_inherits
# @used-by :func:`dfh_manifest()`
def _manifest_filter_entries(entries: list, config: Path, legacy_dirs: list[Path]) -> list:
	remaining: list = []
	for entry in entries:
		source, has_extra = dfh_resolve_manifest_entry(config, entry)
		if None is source or not any((dfh_same_path(source, leg) for leg in legacy_dirs)):
			remaining.append(entry)
		elif has_extra:
			raise ValueError('Filtered legacy Harness discovery entry needs explicit reconciliation; preserved')
	return remaining
# @used-by :func:`_plan_ag_hooks()`
def _merge_ag_hooks(plan: Any, name: str, path: Path, hooks: dict, primary: Path, config: Path, previous: dict, profile: dict) -> None:
	from agent_tools.upwork_project import canonical_global_hooks, legacy_direct_global_hooks, legacy_runner_global_hooks
	owned_legacy = [legacy_direct_global_hooks(cand) for cand in (primary, *dfh_relocated_primaries(primary))] + [legacy_runner_global_hooks(primary), canonical_global_hooks(primary)]
	for hook, desired in canonical_global_hooks(primary, config_dir=config).items():
		is_leg = hook in hooks and any((hooks[hook] == variant.get(hook) for variant in owned_legacy))
		if hook in hooks and hooks[hook] != desired and (not is_leg) and (previous.get('hook_hashes', {}).get(hook) != dfh_hash(dfh_json_bytes(hooks[hook]))):
			plan.issue(path, f'Existing hook {hook} differs from its owned definition; preserved')
		else:
			if hooks.get(hook) != desired:
				plan.details[name]['added_hooks'].append(hook)
			hooks[hook] = desired
		profile['hook_hashes'][hook] = dfh_hash(dfh_json_bytes(desired))
# @used-by :func:`dfh_antigravity_plan()`
def _plan_ag_config_json(plan: Any, config: Path, previous: dict, profile: dict) -> None:
	cfg_json = config / 'config.json'
	if cfg_json.is_file():
		try:
			raw_cfg = cfg_json.read_bytes()
			parsed_cfg = json.loads(raw_cfg.decode('utf-8-sig'))
			allows = (((parsed_cfg.get('userSettings') or {}).get('globalPermissionGrants') or {}).get('allow')) if isinstance(parsed_cfg, dict) else None
			if isinstance(allows, list):
				filtered = [item for item in allows if not (isinstance(item, str) and re.search('(?i)(?:127\\.0\\.0\\.1|localhost|\\[::1\\]):\\d+/json\\b|/devtools/(?:page|browser)/', item))]
				if filtered != allows:
					parsed_cfg['userSettings']['globalPermissionGrants']['allow'] = filtered
					wanted_cfg = dfh_json_bytes(parsed_cfg)
					plan.file(cfg_json, wanted_cfg)
					profile['files'][str(cfg_json)] = dfh_hash(wanted_cfg)
				elif str(cfg_json) in previous.get('files', {}):
					profile['files'][str(cfg_json)] = dfh_hash(raw_cfg)
		except (ValueError, OSError) as exc:
			plan.issue(cfg_json, str(exc))
# @used-by :func:`dfh_antigravity_plan()`
def _plan_ag_hooks(plan: Any, name: str, config: Path, primary: Path, previous: dict, profile: dict) -> None:
	path = config / 'hooks.json'
	try:
		hooks = json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else {}
		if not isinstance(hooks, dict):
			raise ValueError('hooks.json must be a JSON object; preserved')
		_merge_ag_hooks(plan, name, path, hooks, primary, config, previous, profile)
		wanted = dfh_json_bytes(hooks)
		plan.file(path, wanted)
		profile['files'][str(path)] = dfh_hash(wanted)
	except (ValueError, OSError) as exc:
		plan.issue(path, str(exc))
# @used-by :func:`dfh_antigravity_plan()`
def _plan_ag_manifests(plan: Any, name: str, config: Path, primary: Path, profile: dict) -> None:
	for kind in DISCOVERY_KINDS:
		path = config / f'{kind}.json'
		try:
			payload = dfh_load_discovery_manifest(path, entries_error='Discovery manifest entries/inherits must be lists; preserved', check_inherits=True)
			wanted = dfh_json_bytes(dfh_manifest(payload, kind, config, primary))
			plan.file(path, wanted)
			if path in plan.files:
				plan.details[name]['added_entries'].append(kind)
			profile['files'][str(path)] = dfh_hash(wanted)
		except (ValueError, OSError) as exc:
			plan.issue(path, str(exc))
# @used-by :func:`dfh_antigravity_plan()`
def _plan_ag_mcp_json(plan: Any, config: Path, primary: Path, profile: dict, settings_fn: Any) -> None:
	mcp_json = config / 'mcp_config.json'
	if mcp_json.is_file() and mcp_json.read_text(encoding='utf-8-sig').strip():
		try:
			parsed_mcp = json.loads(mcp_json.read_bytes().decode('utf-8-sig'))
			servers = parsed_mcp.get('mcpServers') if isinstance(parsed_mcp, dict) else None
			if isinstance(servers, dict) and _rewrite_mcp_chrome_servers(servers, primary, settings_fn):
				wanted_mcp = dfh_json_bytes(parsed_mcp)
				plan.file(mcp_json, wanted_mcp)
				profile['files'][str(mcp_json)] = dfh_hash(wanted_mcp)
		except (ValueError, OSError) as exc:
			plan.issue(mcp_json, str(exc))
# @used-by :func:`dfh_antigravity_plan()`
def _plan_ag_runner(plan: Any, config: Path, primary: Path, previous: dict, profile: dict) -> None:
	runner_path = config / 'harness_hook_runner.py'
	try:
		wanted = LauncherRenderer(primary, kind='hook_runner').run().encode('utf-8')
		if dfh_has_linked_ancestor(runner_path):
			plan.issue(runner_path, 'Linked native configuration preserved')
		elif runner_path.exists() and (not runner_path.is_file()):
			plan.issue(runner_path, 'Expected a regular configuration file; preserved')
		else:
			actual = runner_path.read_bytes() if runner_path.is_file() else None
			owned = previous.get('files', {}).get(str(runner_path))
			if actual != wanted and None is not actual and (owned != dfh_hash(actual)) and (not actual.startswith(HOOK_RUNNER_HEADER.encode('utf-8'))):
				plan.issue(runner_path, 'Existing harness_hook_runner.py differs from its owned definition; preserved')
			else:
				plan.file(runner_path, wanted)
				profile['files'][str(runner_path)] = dfh_hash(wanted)
	except (ValueError, OSError) as exc:
		plan.issue(runner_path, str(exc))
# @used-by :func:`dfh_shared_native_outputs()`
def _populate_ag_shared_outputs(out: dict, primary: Path, canon: Path, plats: dict) -> None:
	from agent_tools.arch.native_role import populate_antigravity_roles
	from agent_tools.upwork_project import canonical_global_hooks
	for kind in DISCOVERY_KINDS:
		out[primary / f'platforms/antigravity/{kind}.json'] = dfh_json_bytes({'entries': [{'path': (canon / kind).as_posix()}]}).decode('utf-8')
	out[primary / 'platforms/antigravity/hooks.json'] = dfh_json_bytes(canonical_global_hooks(canon)).decode('utf-8')
	populate_antigravity_roles(out, primary, canon, plats.get('antigravity') or {})
# @used-by :func:`dfh_shared_native_outputs()`
def _populate_codex_shared_outputs(out: dict, primary: Path, canon: Path, settings_fn: Any) -> None:
	from agent_tools.arch.native_role import codex_role_protocol_path
	bootstrap = canon / 'platforms/codex/AGENTS.md'
	out[primary / 'platforms/codex/AGENTS.md'] = f'# Harness: Codex\n\n<!-- Generated from canonical rules; {ISSUE} -->\n\n' + dfh_loader(primary, display_root=canon) + '\n'
	for role, name, purpose, _ in dfh_role_values(primary, settings_fn=settings_fn):
		proto_p = codex_role_protocol_path(canon, role)
		instructions = f'Role: {role}.  \n{purpose}  \nRead and execute the shared Codex bootstrap before work, including all mandatory rule sources: {bootstrap.as_posix()}  \nAlso read the protocol: {proto_p}  '
		out[primary / f'platforms/codex/agents/{name}.toml'] = f'# Generated from runtime.json and agents/worker.md; do not edit.\n# {ISSUE}\nname = {json.dumps(name)}\ndescription = {json.dumps(purpose)}\n' + dfh_model_fields(primary, role, settings_fn=settings_fn) + f'developer_instructions = {json.dumps(instructions)}\n'
# @used-by :func:`dfh_shared_plan()`
def _resolve_shared_owned_hash(plan: Any, shared_state: dict, path: Path, prim_abs: Path, relocated: tuple[Path, ...]) -> Any:
	owned_hash = shared_state.get(str(path))
	rel = path.relative_to(prim_abs)
	for rc in relocated:
		old_key = str(dfh_absolute(rc / rel))
		if old_key in shared_state:
			owned_hash = shared_state[old_key] if None is owned_hash else owned_hash
			plan.removed_shared.add(old_key)
	return owned_hash
# @used-by :func:`_plan_ag_mcp_json()`
def _rewrite_mcp_chrome_servers(servers: dict, primary: Path, settings_fn: Any) -> bool:
	from agent_tools.text_browser import headless_mcp_args
	changed = False
	for sname, scfg in servers.items():
		if isinstance(scfg, dict) and isinstance(scfg.get('args'), list) and ('chrome-devtools' in sname.lower() or any(('chrome-devtools-mcp' in str(a) for a in scfg['args']))):
			old_args = [str(a) for a in scfg['args']]
			if any((a.startswith(('--autoConnect', '--browser-url', '--browserUrl')) for a in old_args)):
				kept = [a for a in old_args if not a.startswith(('--autoConnect', '--browser-url', '--browserUrl', '--headless', '--isolated', '--executablePath'))]
				scfg['args'] = kept + headless_mcp_args(dfh_configuration(primary, settings_fn=settings_fn))
				changed = True
	return changed
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_install_native_profiles()`
# @used-by :func:`agent_tools.native_profiles._antigravity_plan()`
def dfh_antigravity_plan(plan: Any, name: str, config: str | Path, primary: Path, state: dict, *, settings_fn: Any=None) -> None:
	cfg_abs = dfh_absolute(config)
	previous = dfh_profile_state(state, name, cfg_abs)
	profile: dict[str, Any] = {'files': {}, 'hook_hashes': {}, 'path': str(cfg_abs), 'platform': 'antigravity'}
	plan.details[name] = {'added_entries': [], 'added_hooks': []}
	_plan_ag_manifests(plan, name, cfg_abs, primary, profile)
	_plan_ag_runner(plan, cfg_abs, primary, previous, profile)
	_plan_ag_hooks(plan, name, cfg_abs, primary, previous, profile)
	_plan_ag_config_json(plan, cfg_abs, previous, profile)
	_plan_ag_mcp_json(plan, cfg_abs, primary, profile, settings_fn)
	plan.profiles[name] = profile
# @used-by :func:`Df.Harness.lib.config_codex.dfh_configure_codex_project()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_retire_owned_project_projections()`
# @used-by :func:`agent_tools.native_profiles.legacy_project_projection_paths()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_disabled()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_enabled()`
def dfh_legacy_project_projection_paths(root: str | Path, primary: str | Path | None=None, *, settings_fn: Any=None) -> list[Path]:
	prim_p = Path(primary if None is not primary else dfh_var_value('HARNESS_CODE')).resolve()
	root_p = Path(root).resolve()
	paths = [root_p / f'.agents/skills/{name}/SKILL.md' for name in dfh_skills(prim_p)] + [root_p / f'.codex/agents/{name}.toml' for _, name, _, _ in dfh_role_values(prim_p, settings_fn=settings_fn)]
	return [path for path in paths if not dfh_has_linked_ancestor(path)]
# @used-by :func:`_plan_ag_manifests()`
def dfh_manifest(payload: Any, kind: str, config: Path, primary: Path) -> dict:
	if not isinstance(payload, dict):
		raise ValueError('Discovery manifest must be a JSON object; preserved')
	r = deepcopy(payload)
	entries, inherits = (r.get('entries', []), r.get('inherits', []))
	if not isinstance(entries, list) or not isinstance(inherits, list):
		raise ValueError('Discovery manifest entries/inherits must be lists; preserved')
	relocated = dfh_relocated_primaries(primary)
	remaining = _manifest_filter_entries(entries, config, [Path(primary) / kind, *(rc / kind for rc in relocated)])
	if 'entries' in r or remaining:
		r['entries'] = remaining
	r['inherits'] = _manifest_build_inherits(inherits, config, Path(primary) / f'platforms/antigravity/{kind}.json', [rc / f'platforms/antigravity/{kind}.json' for rc in relocated])
	return r
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_legacy_role()`
# @used-by :func:`_populate_codex_shared_outputs()`
# @used-by :func:`agent_tools.native_profiles._model_fields()`
def dfh_model_fields(primary: str | Path, role: str, *, settings_fn: Any=None) -> str:
	config = dfh_configuration(primary, settings_fn=settings_fn)['platforms'].get('codex') or {}
	value = (config.get('roles') or {})[role]
	return '' if 'parent' == config.get('subagents', {}).get('selection') or value.get('selection') in ('parent', 'inherit') else f"model = {json.dumps(value['model'])}\nmodel_reasoning_effort = {json.dumps(value['effort'])}\n"
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_codex_plan()`
# @used-by :func:`dfh_antigravity_plan()`
def dfh_profile_state(state: dict, name: str, path: str | Path) -> dict:
	previous = state.get('profiles', {}).get(name, {})
	return previous if previous.get('path') == str(dfh_absolute(path)) else {}
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_config_toml()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_roles()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_retire_profile_roles()`
# @used-by :func:`_populate_codex_shared_outputs()`
# @used-by :func:`agent_tools.native_profiles._role_values()`
# @used-by :func:`dfh_legacy_project_projection_paths()`
def dfh_role_values(primary: str | Path, *, settings_fn: Any=None) -> list[tuple[str, str, str, dict]]:
	config = dfh_configuration(primary, settings_fn=settings_fn)['platforms'].get('codex') or {}
	roles = config.get('roles') or {}
	values = [(role, roles[role]['agent'], PURPOSES[role], roles[role]) for role in ('AA', 'AF', 'ARCH') if role in roles]
	if any((not isinstance(name, str) or not re.fullmatch('[A-Za-z0-9_-]+', name) for _, name, _, _ in values)) or len({name for _, name, _, _ in values}) != len(values):
		raise ValueError('Native role identifiers must be distinct safe filenames')
	return values
# @used-by :func:`agent_tools.native_profiles.shared_native_outputs()`
# @used-by :func:`dfh_shared_plan()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_disabled()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_enabled()`
def dfh_shared_native_outputs(primary: str | Path | None=None, *, settings_fn: Any=None) -> dict[Path, str]:
	prim_p = Path(primary if None is not primary else dfh_var_value('HARNESS_CODE')).resolve()
	out: dict[Path, str] = {}
	canon, plats = (CacheStore(prim_p).run(), dfh_configuration(prim_p, settings_fn=settings_fn)['platforms'])
	if 'antigravity' in plats:
		_populate_ag_shared_outputs(out, prim_p, canon, plats)
	if 'codex' in plats:
		_populate_codex_shared_outputs(out, prim_p, canon, settings_fn)
	return out
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_build_shared_native()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_install_native_profiles()`
# @used-by :func:`agent_tools.native_profiles._shared_plan()`
def dfh_shared_plan(plan: Any, primary: str | Path, state: dict, *, settings_fn: Any=None) -> None:
	prim_abs = dfh_absolute(primary)
	relocated = dfh_relocated_primaries(prim_abs)
	shared_state = state.get('shared', {})
	for raw_path, text in dfh_shared_native_outputs(prim_abs, settings_fn=settings_fn).items():
		path = dfh_absolute(raw_path)
		if dfh_has_linked_ancestor(path):
			plan.issue(path, 'Linked shared native definition preserved')
		else:
			actual, payload = (path.read_bytes() if path.is_file() else None, text.encode('utf-8'))
			owned_hash = _resolve_shared_owned_hash(plan, shared_state, path, prim_abs, relocated)
			if actual != payload and None is not actual and (owned_hash != dfh_hash(actual)):
				plan.issue(path, 'Shared native definition was modified without ownership; preserved')
			else:
				plan.file(path, payload)
				plan.shared[str(path)] = dfh_hash(payload)
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_codex_plan()`
# @used-by :func:`dfh_legacy_project_projection_paths()`
# @used-by :meth:`test_arch_rules_contract.ArchRulesContractTests.test_df_architecture_skill_discovered_and_lints_cleanly()`
# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_skill_rules_and_docs_codify_mandatory_separate_companion_tracks()`
# @used-by :meth:`test_df_analysis_rules_contract.DfAnalysisRulesAndSkillContractTests.test_df_analysis_skill_discovered_by_native_profiles_and_lints_cleanly()`
# @used-by :meth:`test_perf_improvement_skill_contract.PerfImprovementSkillContractTests.test_perf_improvement_skill_discovered_and_references_pass_lint()`
def dfh_skills(primary: str | Path) -> dict[str, tuple[Path, dict]]:
	r: dict[str, tuple[Path, dict]] = {}
	for path in sorted((Path(primary) / 'skills').glob('*/SKILL.md')):
		metadata = dfh_frontmatter(path)
		if not metadata.get('name') or not metadata.get('description'):
			raise ValueError(f'Shared skill needs name and description: {path}')
		r[path.parent.name] = (path, metadata)
	return r
