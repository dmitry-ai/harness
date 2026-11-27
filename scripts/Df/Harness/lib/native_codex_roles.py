# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Config.NativeProfile.ManagedLink import ManagedLink
from Df.Harness.lib.config_blocks import dfh_frontmatter, dfh_has_linked_ancestor, dfh_is_linked_path, dfh_replace_managed_block
from Df.Harness.lib.config_codex import dfh_loader
from Df.Harness.lib.native_ag_plan import dfh_model_fields, dfh_role_values
from Df.Harness.lib.native_links import END, ISSUE, START, dfh_absolute, dfh_directory_link_identity, dfh_exists, dfh_hash, dfh_link_matches_target, dfh_link_target_path, dfh_normalized_text, dfh_relocated_primaries
from Df.Harness.lib.storage import dfh_data_dir_for
import json
import re
import tomllib
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_legacy_role_config()`
def _append_role_tables(text: str, additional: list[str]) -> str:
	sep = '' if not text or text.endswith('\n\n') else ('\n' if text.endswith('\n') else '\n\n')
	r = text + sep + f'# Shared Harness roles; {ISSUE}\n' + '\n'.join(additional)
	tomllib.loads(r)
	return r
# @used-by :func:`_strip_owned_role_block()`
def _collect_role_backup_originals(text: str, index: int, path: Path, state: dict, primary: Path) -> list[str]:
	originals = ['', text[:index]]
	backup_root = dfh_data_dir_for(primary) / 'native-profiles/backups'
	for key, saved in state.get('backups', {}).items():
		if key.startswith(str(path) + ':') and isinstance(saved, str):
			backup = Path(saved)
			if not backup.is_file():
				cand = backup_root / backup.parent.name / backup.name
				backup = cand if cand.is_file() else backup
			if backup.resolve().is_relative_to(backup_root.resolve()) and backup.is_file():
				payload = backup.read_bytes()
				if dfh_hash(payload) == key.rsplit(':', 1)[-1]:
					originals.append(payload.decode('utf-8-sig'))
	return originals
# @used-by :func:`dfh_plan_codex_link()`
def _handle_existing_codex_link(plan: Any, link: ManagedLink, active_valid: Any, active_error: str, relocated_valid: Any, ops: dict | None) -> None:
	path = link.path
	if not active_valid():
		if relocated_valid():
			identity = {'kind': 'file-symlink', 'target': dfh_link_target_path(path)} if 'file-symlink' == link.kind else dfh_directory_link_identity(path)
			plan.retired_links[path] = ManagedLink(path, identity['target'], identity['kind'], label=f'relocated {link.label}', ops=ops)
			plan.managed_links[path] = link
		else:
			plan.issue(path, active_error)
# @used-by :func:`_strip_owned_role_block()`
def _match_owned_role_block(text: str, index: int, marker: str, definitions: dict, owned: str, originals: list[str]) -> str:
	blocks: set[str] = set()
	for original in originals:
		try:
			generated = dfh_legacy_role_config(original, definitions)
			offset = generated.find(marker, len(original))
			if 0 <= offset and dfh_hash(generated.encode('utf-8')) == owned:
				blocks.add(generated[offset:])
		except (ValueError, KeyError):
			continue
	matching = [block for block in blocks if text.startswith(block, index)]
	if 1 != len(matching):
		raise ValueError('Former role configuration differs from its exact owned generated block; preserved')
	return matching[0]
# @used-by :func:`_retire_one_profile_skill()`
def _retire_obsolete_skill_entry(plan: Any, profile: dict, path: Path, target: Path, primary: Path, ops: dict | None) -> None:
	valid_targets = {dfh_absolute(cand) / 'skills' / path.name for cand in (primary, *dfh_relocated_primaries(primary))}
	if target not in valid_targets:
		plan.issue(path, 'Obsolete skill link ownership is outside its exact managed target; preserved')
	elif dfh_has_linked_ancestor(path, include_self=False):
		plan.issue(path, 'Linked obsolete skill parent directory preserved')
	elif (dfh_exists(path) or dfh_is_linked_path(path)) and (not dfh_is_linked_path(path) or (not dfh_link_matches_target(path, target))):
		plan.issue(path, 'Obsolete managed skill link changed; preserved')
	else:
		if dfh_exists(path) or dfh_is_linked_path(path):
			identity = dfh_directory_link_identity(path)
			plan.retired_links[path] = ManagedLink(path, identity['target'], identity['kind'], label='obsolete skill', ops=ops)
		if str(path) not in profile['retired']:
			profile['retired'].append(str(path))
# @used-by :func:`dfh_retire_profile_roles()`
def _retire_one_profile_role(plan: Any, profile: dict, raw_path: Any, raw_target: Any, home: Path, primary: Path, state: dict, wanted: set[Path], ops: dict | None) -> None:
	if not isinstance(raw_path, str) or not isinstance(raw_target, str) or (not dfh_role_identity(raw_path, raw_target, home, primary)):
		plan.issue(home / 'agents', 'Previous role link ownership is outside its exact managed paths; preserved')
	else:
		path, target = (dfh_absolute(raw_path), dfh_absolute(raw_target))
		if path not in wanted:
			if dfh_has_linked_ancestor(path, include_self=False):
				plan.issue(path, 'Linked obsolete role parent directory preserved')
			elif dfh_exists(path) and (not path.is_symlink() or (not dfh_link_matches_target(path, target))):
				plan.issue(path, 'Obsolete managed role link changed; preserved')
			elif dfh_exists(path) and target.is_file() and (state.get('shared', {}).get(str(target)) != dfh_hash(target.read_bytes())):
				plan.issue(target, 'Obsolete shared role definition changed; preserved')
			else:
				if dfh_exists(path):
					plan.retired_links[path] = ManagedLink(path, target, 'file-symlink', label='obsolete role', ops=ops)
				if str(path) not in profile['retired']:
					profile['retired'].append(str(path))
# @used-by :func:`dfh_retire_profile_skills()`
def _retire_one_profile_skill(plan: Any, profile: dict, previous: dict, raw_path: Any, raw_target: Any, home: Path, primary: Path, wanted: set[Path], ops: dict | None) -> None:
	if not isinstance(raw_path, str) or not isinstance(raw_target, str):
		plan.issue(home / 'skills', 'Previous link ownership has invalid path types; preserved')
	else:
		path, target = (dfh_absolute(raw_path), dfh_absolute(raw_target))
		if path.parent != dfh_absolute(home) / 'skills':
			if raw_path not in previous.get('role_targets', {}):
				profile['links'].setdefault(raw_path, raw_target)
		elif path not in wanted:
			_retire_obsolete_skill_entry(plan, profile, path, target, primary, ops)
# @used-by :func:`dfh_retire_shared_roles()`
def _retire_one_shared_role(plan: Any, raw_path: str, owned: Any, primary: Path, referenced: set[Path], valid_dirs: set[Path]) -> None:
	path = dfh_absolute(raw_path)
	skip = raw_path in plan.removed_shared or str(path) in plan.shared or path.parent not in valid_dirs or '.toml' != path.suffix or (not re.fullmatch('[A-Za-z0-9_-]+', path.stem)) or (path in referenced)
	if not skip:
		if not path.exists() and path.parent != dfh_absolute(primary) / 'platforms/codex/agents':
			plan.removed_shared.add(raw_path)
		elif dfh_has_linked_ancestor(path) or (path.exists() and (not path.is_file() or dfh_hash(path.read_bytes()) != owned)):
			plan.issue(path, 'Obsolete shared role definition changed or is linked; preserved')
		else:
			if path.exists():
				plan.file(path, None)
			plan.removed_shared.add(str(path))
# @used-by :func:`dfh_role_config()`
def _strip_owned_role_block(text: str, marker: str, definitions: dict, previous: dict, state: dict, path: Path, primary: Path) -> str:
	if 1 != text.count(marker):
		raise ValueError('Existing same-name role tables are not the exact owned installer block; preserved')
	owned = previous.get('files', {}).get(str(path))
	if not isinstance(owned, str):
		raise ValueError('Former role configuration has no ownership proof; preserved')
	index = text.index(marker)
	block = _match_owned_role_block(text, index, marker, definitions, owned, _collect_role_backup_originals(text, index, path, state, primary))
	r = text[:index] + text[index + len(block):]
	remaining = tomllib.loads(r) if r.strip() else {}
	if any((name in remaining.get('agents', {}) for name in definitions)):
		raise ValueError('Same-name role tables outside the owned installer block are preserved')
	return r
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_agents_md()`
# @used-by :func:`dfh_profile_agents()`
def dfh_compact_loader(primary: str | Path) -> str:
	bootstrap = Path(primary) / 'platforms/codex/AGENTS.md'
	return f'{START}\n# Codex: Harness\n\nRead and execute the shared Codex bootstrap [AGENTS.md](<{bootstrap.as_posix()}>) before doing any work.  \nIt applies in every new chat and every child subagent.  \n{END}\n'
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_config_toml()`
def dfh_disable_codex_bundled_chrome_plugin(text: str) -> str:
	data = tomllib.loads(text) if text.strip() else {}
	plugins = data.get('plugins')
	if not isinstance(plugins, dict) or not isinstance(plugins.get('chrome@openai-bundled'), dict) or True is not plugins['chrome@openai-bundled'].get('enabled'):
		r = text
	else:
		updated = re.sub('(?m)^(\\[plugins\\.(?:"chrome@openai-bundled"|\'chrome@openai-bundled\')\\]\\r?\\n(?:[^\\[\\r\\n]*\\r?\\n)*?\\s*enabled\\s*=\\s*)true(\\s*(?:#.*)?)$', '\\1false\\2', text, count=1)
		if updated == text:
			raise ValueError('Could not disable plugins."chrome@openai-bundled" cleanly; preserved')
		if False is not tomllib.loads(updated).get('plugins', {}).get('chrome@openai-bundled', {}).get('enabled'):
			raise ValueError('Disabling plugins."chrome@openai-bundled" did not parse as false; preserved')
		r = updated
	return r
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_roles()`
# @used-by :func:`agent_tools.native_profiles._legacy_role()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests._seed_legacy_profiles()`
def dfh_legacy_role(primary: str | Path, role: str, name: str, purpose: str, *, settings_fn: Any=None) -> str:
	worker_p = (Path(primary) / 'agents/worker.md').as_posix()
	instructions = f'Role: {role}.  \n{purpose}  \n' + dfh_loader(Path(primary)) + f'\nAlso read the worker protocol: {worker_p}  '
	return f'# Generated from runtime.json and agents/worker.md; do not edit.\nname = {json.dumps(name)}\ndescription = {json.dumps(purpose)}\n' + dfh_model_fields(primary, role, settings_fn=settings_fn) + f'developer_instructions = {json.dumps(instructions, ensure_ascii=False)}\n'
# @used-by :func:`_match_owned_role_block()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests._seed_legacy_profiles()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_codex_roles_and_proof_metadata_tail()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.former_role_config()`
def dfh_legacy_role_config(text: str, definitions: dict) -> str:
	data = tomllib.loads(text) if text.strip() else {}
	agents = data.get('agents', {})
	if not isinstance(agents, dict):
		raise ValueError('agents must be a TOML table; preserved')
	additional: list[str] = []
	for name, desired in definitions.items():
		if name not in agents:
			desc_lit, cfg_lit = (json.dumps(desired['description']), json.dumps(desired['config_file']))
			additional.append(f'[agents.{json.dumps(name)}]\ndescription = {desc_lit}\nconfig_file = {cfg_lit}\n')
		elif agents[name] != desired:
			raise ValueError(f'Existing role {name} differs from shared native role configuration; preserved')
	return _append_role_tables(text, additional) if additional else text
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_skills()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests._seed_legacy_profiles()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.legacy_codex()`
def dfh_legacy_skill(name: str, primary: str | Path) -> str:
	path = Path(primary) / f'skills/{name}/SKILL.md'
	description = dfh_frontmatter(path).get('description', '')
	if 'upwork-init' == name:
		description = 'Creates a project workspace and performs the full analysis of an Upwork job post; resumes it after an interruption.'
	elif 'upwork-cleanup' == name:
		description = 'Cleans up empty Upwork projects older than 72 hours in Antigravity and Codex while preserving on-disk history.'
	if re.search(':\\s|\\s#|^[\\\'"\\[{>|*&!%@`]', description):
		description = json.dumps(description, ensure_ascii=False)
	r = f'---\nname: {name}\ndescription: {description}\n---\nRead and execute the shared skill [SKILL.md](<{path.as_posix()}>).  \n'
	if 'upwork-init' == name:
		r += 'Determine the active UI platform from the conversation and use the corresponding platform adapter of the shared skill.  \n'
	elif 'upwork-cleanup' == name:
		r += 'Determine the active UI platform from the conversation; a normal run cleans all enabled environment instances configured in runtime.json.  \n'
	return r
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_roles()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_skills()`
# @used-by :func:`agent_tools.native_profiles._plan_codex_link()`
def dfh_plan_codex_link(plan: Any, profile: dict, link: ManagedLink, active_valid: Any, active_error: str, retire_path: Path, legacy_valid: Any, legacy_error: str, relocated_valid: Any=lambda: False, *, ops: dict | None=None) -> None:
	path = link.path
	profile['links'][str(path)] = str(link.target)
	profile['retired'] = [item for item in profile['retired'] if str(path) != item]
	if dfh_has_linked_ancestor(path, include_self=False):
		plan.issue(path, f'Linked {link.label} parent directory preserved')
	elif dfh_is_linked_path(path):
		_handle_existing_codex_link(plan, link, active_valid, active_error, relocated_valid, ops)
	elif not dfh_exists(path):
		plan.managed_links[path] = link
	elif not legacy_valid():
		plan.issue(path, legacy_error)
	else:
		link.legacy_dir = 'directory' == link.kind
		plan.file(retire_path, None)
		plan.managed_links[path] = link
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_agents_md()`
def dfh_profile_agents(text: str, primary: str | Path, owned: dict) -> str:
	wanted = dfh_compact_loader(primary)
	marker = '# Codex: Upwork\n'
	plain = text.replace('\r\n', '\n')
	if START in text or END in text:
		r = dfh_replace_managed_block(text, wanted.rstrip('\n'), start_marker=START, end_marker=END, expected_sha256=owned.get('managed_block_sha256'), malformed_message='Malformed Harness instruction block; personal instructions preserved', edited_message='Harness instruction block was edited; personal instructions preserved')
	elif marker not in plain:
		separator = '' if not text or text.endswith('\n\n') else ('\n' if text.endswith('\n') else '\n\n')
		r = text + separator + wanted
	else:
		if 1 != plain.count(marker):
			raise ValueError('Ambiguous legacy instruction blocks; personal instructions preserved')
		legacy = f'# Codex: Upwork\n\n<!-- Generated from {Path(primary).as_posix()}; run harness.py build-native to update. -->\n\n' + dfh_loader(Path(primary)) + '\n'
		if dfh_normalized_text(plain[plain.index(marker):]) != dfh_normalized_text(legacy):
			raise ValueError('Legacy instruction block differs from its exact generated template; preserved')
		match = re.search('(?m)^# Codex: Upwork\\r?\\n', text)
		r = text[:match.start()] + wanted
	return r
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_codex_plan()`
# @used-by :func:`agent_tools.native_profiles._retire_profile_roles()`
def dfh_retire_profile_roles(plan: Any, profile: dict, previous: dict, home: Path, primary: Path, state: dict, *, settings_fn: Any=None, ops: dict | None=None) -> None:
	wanted = {dfh_absolute(home) / f'agents/{name}.toml' for _, name, _, _ in dfh_role_values(primary, settings_fn=settings_fn)}
	prior = previous.get('role_targets', {})
	if not isinstance(prior, dict):
		plan.issue(home / 'agents', 'Previous role link ownership is malformed; preserved')
	else:
		for raw_path, raw_target in prior.items():
			_retire_one_profile_role(plan, profile, raw_path, raw_target, home, primary, state, wanted, ops)
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_codex_plan()`
# @used-by :func:`agent_tools.native_profiles._retire_profile_skills()`
def dfh_retire_profile_skills(plan: Any, profile: dict, previous: dict, home: Path, primary: Path, skills: dict, *, ops: dict | None=None) -> None:
	wanted = {dfh_absolute(home) / 'skills' / name for name in skills}
	prior = previous.get('links', {})
	if not isinstance(prior, dict):
		plan.issue(home / 'skills', 'Previous link ownership is malformed; preserved')
	else:
		for raw_path, raw_target in prior.items():
			_retire_one_profile_skill(plan, profile, previous, raw_path, raw_target, home, primary, wanted, ops)
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_build_shared_native()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_install_native_profiles()`
def dfh_retire_shared_roles(plan: Any, primary: Path, state: dict) -> None:
	profiles = {**state.get('profiles', {}), **plan.profiles}
	if not any(('codex' == profile.get('platform') and 'file-links' != profile.get('role_registration') for profile in profiles.values())):
		referenced = {dfh_absolute(target) for profile in profiles.values() for target in profile.get('role_targets', {}).values() if isinstance(target, str)}
		valid_dirs = {dfh_absolute(cand) / 'platforms/codex/agents' for cand in (primary, *dfh_relocated_primaries(primary))}
		for raw_path, owned in state.get('shared', {}).items():
			_retire_one_shared_role(plan, raw_path, owned, primary, referenced, valid_dirs)
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_config_toml()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_codex_roles_and_proof_metadata_tail()`
def dfh_role_config(text: str, definitions: dict, previous: dict, state: dict, path: Path, primary: Path) -> str:
	data = tomllib.loads(text) if text.strip() else {}
	agents = data.get('agents', {})
	if not isinstance(agents, dict):
		raise ValueError('agents must be a TOML table; preserved')
	marker = f'# Shared Harness roles; {ISSUE}\n'
	if not any((name in agents for name in definitions)):
		if marker in text:
			raise ValueError('Former role configuration needs reconciliation for renamed or removed roles; preserved')
		r = text
	else:
		r = _strip_owned_role_block(text, marker, definitions, previous, state, path, primary)
	return r
# @used-by :func:`_retire_one_profile_role()`
def dfh_role_identity(path: str | Path, target: str | Path, home: Path, primary: Path) -> bool:
	p_abs, t_abs = (dfh_absolute(path), dfh_absolute(target))
	valid_targets = {dfh_absolute(cand) / 'platforms/codex/agents' / p_abs.name for cand in (primary, *dfh_relocated_primaries(primary))}
	return p_abs.parent == dfh_absolute(home) / 'agents' and '.toml' == p_abs.suffix and bool(re.fullmatch('[A-Za-z0-9_-]+', p_abs.stem)) and (t_abs in valid_targets)
