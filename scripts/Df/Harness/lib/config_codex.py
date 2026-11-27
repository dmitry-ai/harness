# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Config.ProjectionPublisher import ProjectionPublisher
from Df.Harness.lib.config_blocks import dfh_digest, dfh_extract_managed_block, dfh_load_discovery_manifest, dfh_load_project_receipt, dfh_receipt_sha256, dfh_resolve_manifest_entry, dfh_root_options
from Df.Harness.lib.path_resolve import dfh_project_paths, dfh_relocated_harness_code_dirs, dfh_var_value
from Df.Harness.lib.runtime_context import dfh_profile_name
from Df.Harness.lib.runtime_instances import dfh_extract_platform_instances
import tomllib
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_project_rule_paths()`
def _append_rule_source(paths: list[Path], agents: Path, entry: Any, shared_eq: set[Path]) -> None:
	source, has_extra = dfh_resolve_manifest_entry(agents, entry)
	if None is source:
		raise ValueError('Each rules.json entry needs a path')
	if has_extra:
		raise ValueError('Codex projection does not support filtered rules.json entries; preserve them and resolve explicitly')
	if source not in shared_eq:
		if source.is_dir():
			paths.extend(sorted(source.rglob('*.md')))
		elif source.is_file() and '.md' == source.suffix:
			paths.append(source)
		else:
			raise ValueError(f'Configured rule source is missing or unsupported: {source}')
# @used-by :func:`dfh_global_codex_instructions()`
def _read_global_profile_value(inst: dict) -> str:
	cfg_toml = inst.get('system_paths', {}).get('config_toml')
	path = Path(cfg_toml) if cfg_toml else Path(inst['home']) / 'config.toml'
	value = tomllib.loads(path.read_bytes().decode('utf-8-sig')).get('developer_instructions', '') if path.exists() else ''
	if not isinstance(value, str):
		raise ValueError('Global developer_instructions must be a string')
	return value
# @used-by :func:`dfh_configure_codex_project()`
def _run_codex_project_publish(root: Path, primary: Path, pp: Any, paths: list[Path], *, check: bool, retire_fn: Any) -> dict:
	native = pp.codex_config_toml
	data = tomllib.loads(native.read_bytes().decode('utf-8')) if native.exists() else {}
	current = data.get('developer_instructions', '')
	manual = current.replace(dfh_extract_managed_block(current), '').strip()
	path, text, merge = dfh_native_config(root, dfh_loader(primary, paths, restore_global=False) if manual else None)
	r = ProjectionPublisher(root, {path: text} if text or path.exists() else {}, check=check, merge=merge, retire=[root / 'CODEX.md', *retire_fn(root, primary)]).run()
	if not check and (not r['valid']):
		raise ValueError(r['issues'])
	return r
# @used-by :func:`agent_tools.configuration.configure_codex_project()`
def dfh_configure_codex_project(root: str | Path, primary: str | Path | None=None, job_url: Any=None, label: Any=None, *, check: bool=False, settings_fn: Any=None) -> dict:
	from Df.Harness.lib.native_ag_plan import dfh_legacy_project_projection_paths
	prim_p = Path(primary if None is not primary else dfh_var_value('HARNESS_CODE')).resolve()
	root_p = Path(root).resolve()
	cfg = dfh_primary_settings(prim_p, settings_fn=settings_fn)
	if 'codex' not in (cfg.get('platforms') or {}) or root_p == Path(cfg['workspace_root']).resolve():
		r: dict[str, Any] = {'issues': [], 'valid': True, 'written': []}
	else:
		pp = dfh_project_paths(root_p, exact_root=True)
		agents_dir = pp.agents_config_dir if pp.agents_config_dir.resolve() != prim_p else root_p / '.agents'
		try:
			paths = dfh_project_rule_paths(root_p, prim_p)
			r = _run_codex_project_publish(root_p, prim_p, pp, paths, check=check, retire_fn=dfh_legacy_project_projection_paths)
		except (ValueError, OSError) as exc:
			if not check:
				raise
			err_file = str(agents_dir / 'rules.json') if isinstance(exc, OSError) or 'rules.json' in str(exc) or 'Configured rule source' in str(exc) else str(pp.codex_config_toml)
			r = {'issues': [{'file': err_file, 'message': str(exc)}], 'valid': False, 'written': []}
	return r
# @used-by :func:`agent_tools.configuration.global_codex_instructions()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_native_builder_and_projection_publisher()`
def dfh_global_codex_instructions(*, settings_fn: Any=None, profile_name_fn: Any=None) -> dict:
	from Df.Harness.Runtime.SettingsLoader import SettingsLoader
	cfg = settings_fn() if None is not settings_fn else SettingsLoader().run()
	all_insts = dfh_extract_platform_instances(cfg['platforms'].get('codex') or {}, platform='codex', include_disabled=True)
	enabled_insts = {k: v for k, v in all_insts.items() if v['enabled']}
	try:
		names, pool = ([profile_name_fn() if None is not profile_name_fn else dfh_profile_name(config=cfg)], all_insts)
	except ValueError:
		names, pool = (list(enabled_insts), enabled_insts)
	if not names:
		r = {'developer_instructions': '', 'profile': 'codex disabled (no enabled instances)'}
	else:
		values = [_read_global_profile_value(pool.get(name) or {}) for name in names]
		if 1 != len(set(values)):
			raise ValueError('Global profile instructions differ; select the actual --codex-profile instead of combining accounts')
		r = {'developer_instructions': values[0], 'profile': names[0] if 1 == len(names) else 'identical across configured profiles'}
	return r
# @used-by :func:`Df.Harness.lib.native_ag_plan._populate_codex_shared_outputs()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_legacy_role()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_profile_agents()`
# @used-by :func:`_run_codex_project_publish()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__prepare_codex_outputs()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests._seed_legacy_profiles()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.legacy_codex()`
# @used-by :meth:`test_rules_progressive_disclosure.RulesProgressiveDisclosureTests.test_loader_omits_on_demand_header_when_all_rules_are_always_on()`
# @used-by :meth:`test_rules_progressive_disclosure.RulesProgressiveDisclosureTests.test_loader_separates_always_on_and_catalogs_model_decision_with_description()`
def dfh_loader(primary: str | Path, local: Any=(), *, restore_global: bool=True, display_root: Any=None) -> str:
	from agent_tools.rules_manifest import render_codex_loader
	return render_codex_loader(primary, local, restore_global=restore_global, display_root=display_root)
# @used-by :func:`_run_codex_project_publish()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__build_codex_enabled()`
def dfh_native_config(root: str | Path, instructions: str | None=None) -> tuple[Path, str, dict]:
	root_p = Path(root)
	config_path = dfh_project_paths(root_p, exact_root=True).codex_config_toml
	actual = config_path.read_bytes() if config_path.exists() else None
	existing = actual.decode('utf-8') if None is not actual else ''
	_, _, receipt = dfh_load_project_receipt(root_p)
	owned = receipt.get(str(config_path), {})
	legacy = root_p / 'CODEX.md'
	legacy_bytes = len(legacy.read_bytes()) if legacy.exists() and dfh_receipt_sha256(receipt.get(str(legacy))) == dfh_digest(legacy.read_bytes()) else None
	wanted = dfh_root_options(existing, instructions, legacy_bytes=legacy_bytes, expected_block=owned.get('block_sha256') if isinstance(owned, dict) else None)
	return (config_path, wanted, {config_path: actual})
# @used-by :func:`agent_tools.configuration._primary_settings()`
# @used-by :func:`dfh_configure_codex_project()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.run()`
def dfh_primary_settings(primary: str | Path, *, settings_fn: Any=None) -> dict:
	from Df.Harness.Runtime.SettingsLoader import SettingsLoader
	p = Path(primary).resolve()
	default_prim = Path(dfh_var_value('HARNESS_CODE')).resolve()
	rt = p / 'runtime.json'
	loader = settings_fn if None is not settings_fn else (lambda path=None: SettingsLoader(path).run())
	return loader(rt) if p != default_prim and rt.is_file() else loader()
# @used-by :func:`Df.Harness.lib.completion_checks._collect_base_instruction_sources()`
# @used-by :func:`dfh_configure_codex_project()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__prepare_codex_outputs()`
# @used-by :meth:`test_portability.ProjectionTests.test_extra_rule_sources_are_projected_and_unsupported_selectors_reported()`
def dfh_project_rule_paths(root: str | Path, primary: str | Path) -> list[Path]:
	pp = dfh_project_paths(root, exact_root=True)
	prim_p = Path(primary).resolve()
	agents = pp.agents_config_dir if pp.agents_config_dir.resolve() != prim_p else Path(root) / '.agents'
	paths = list(sorted((agents / 'rules').glob('*.md')))
	data = dfh_load_discovery_manifest(agents / 'rules.json', entries_error='rules.json needs an entries list')
	if data.get('inherits'):
		raise ValueError('Codex projection does not support rules.json inherits; preserve it and resolve explicitly')
	shared_eq = {(prim_p / 'rules').resolve(), *((rc / 'rules').resolve() for rc in dfh_relocated_harness_code_dirs(primary=prim_p))}
	for entry in data.get('entries', []):
		_append_rule_source(paths, agents, entry, shared_eq)
	return list(dict.fromkeys((path.resolve() for path in paths if not any((path.resolve().is_relative_to(sh) for sh in shared_eq)))))
