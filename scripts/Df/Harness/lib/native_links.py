# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.config_blocks import dfh_has_linked_ancestor, dfh_is_linked_path, dfh_store_content_backup
from Df.Harness.lib.path_resolve import dfh_relocated_harness_code_dirs
from Df.Harness.lib.storage import dfh_data_dir_for
import hashlib
import json
import os
import subprocess
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
END = '<!-- harness:native-loader:end -->'
ISSUE = 'https://github.com/dmitry-ai/harness/issues/35'
PURPOSES = {'AA': 'Independent substantive review of the five stages and KB consistency.', 'AF': 'Collection and extraction of evidence for an assigned question.', 'ARCH': 'Independent falsifier audit of software design patterns and architecture specifications.'}
START = '<!-- harness:native-loader:start -->'
# @used-by :func:`Df.Harness.lib.native_ag_plan._resolve_shared_owned_hash()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_antigravity_plan()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_profile_state()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_shared_plan()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_roles()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_skills()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._resolve_target_names()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_codex_plan()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_obsolete_skill_entry()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_profile_role()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_profile_skill()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_shared_role()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_retire_profile_roles()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_retire_profile_skills()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_retire_shared_roles()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_role_identity()`
# @used-by :func:`dfh_direct_link_matches_target()`
# @used-by :func:`dfh_is_relocated_owned_link()`
# @used-by :func:`dfh_link_matches_target()`
# @used-by :func:`dfh_link_target_path()`
# @used-by :func:`dfh_relocated_primaries()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__attach_profile_views()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.__init__()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Plan.Plan.file()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_managed_link_and_native_links_edge_helpers()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_install_global_recovers_dangling_relocated_codex_links_when_receipt_already_points_to_primary()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_install_global_rewrites_manifests_and_codex_links_even_when_compatibility_junction_exists()`
def dfh_absolute(path: str | Path) -> Path:
	return Path(os.path.abspath(path))
# @used-by :func:`agent_tools.native_profiles._facade_ops()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__apply()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.former_role_config()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_concurrent_preimage_change_is_preserved_before_application()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_obsolete_skill_changed_during_backup_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_parent_link_injected_during_backup_is_preserved_without_escape()`
def dfh_backup(primary: str | Path, state: dict, path: str | Path, payload: bytes) -> str:
	backup, digest = dfh_store_content_backup(dfh_data_dir_for(primary) / 'native-profiles/backups', path, payload)
	state.setdefault('backups', {})[str(path) + ':' + digest] = str(backup)
	return str(backup)
# @used-by :func:`Df.Harness.lib.native_ag_plan._rewrite_mcp_chrome_servers()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_model_fields()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_role_values()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_shared_native_outputs()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_install_native_profiles()`
# @used-by :func:`agent_tools.native_profiles._configuration()`
# @used-by :func:`dfh_directory_link()`
def dfh_configuration(primary: str | Path, *, settings_fn: Any=None) -> dict:
	from Df.Harness.Runtime.SettingsLoader import SettingsLoader
	path = Path(primary) / 'runtime.json'
	loader = settings_fn if None is not settings_fn else (lambda p=None: SettingsLoader(p).run())
	return loader(path) if path.is_file() else loader()
# @used-by :func:`agent_tools.native_profiles._directory_link()`
# @used-by :func:`dfh_restore_directory_link()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.create()`
def dfh_directory_link(target: str | Path, path: str | Path, primary: str | Path, *, settings_fn: Any=None) -> None:
	path_p = Path(path)
	dfh_prepare_link_parent(path_p, 'skill')
	if 'nt' != os.name:
		path_p.symlink_to(target, target_is_directory=True)
	else:
		node = (dfh_configuration(primary, settings_fn=settings_fn)['platforms'].get('codex') or {}).get('node', 'node')
		result = subprocess.run([node, '-e', "require('node:fs').symlinkSync(process.argv[1],process.argv[2],'junction')", str(target), str(path_p)], capture_output=True, text=True, timeout=15)
		if result.returncode:
			raise OSError(f'Directory junction creation failed: {result.stderr.strip()}')
# @used-by :func:`Df.Harness.lib.native_codex_roles._handle_existing_codex_link()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_obsolete_skill_entry()`
# @used-by :func:`dfh_verify_retired_directory_link()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_managed_link_and_native_links_edge_helpers()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.check_skill_rename_rollback()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_obsolete_skill_under_linked_parent_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_rename_retires_owned_dangling_link_with_identity_backup()`
def dfh_directory_link_identity(path: str | Path) -> dict[str, str]:
	path_p = Path(path)
	return {'kind': 'directory-junction' if bool(getattr(path_p, 'is_junction', lambda: False)()) else 'directory-symlink', 'target': os.readlink(path_p)}
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_roles()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_skills()`
def dfh_direct_link_matches_target(path: str | Path, target: str | Path) -> bool:
	return dfh_is_linked_path(path) and os.path.normcase(str(dfh_link_target_path(path))) == os.path.normcase(str(dfh_absolute(target)))
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_obsolete_skill_entry()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_profile_role()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_plan_codex_link()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.restore_retired()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.verify_before_create()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_managed_link_and_native_links_edge_helpers()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.check_skill_rename_rollback()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_removed_skill_retires_alias_without_deleting_canonical_directory()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_rename_does_not_touch_unselected_profile_or_forget_ownership()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_rename_retires_owned_dangling_link_with_identity_backup()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def dfh_exists(path: str | Path) -> bool:
	return os.path.lexists(path)
# @used-by :func:`agent_tools.native_profiles._facade_ops()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.create()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.restore_retired()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_changed_created_link_does_not_stop_other_guarded_rollback()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_link_failure_restores_retired_roles_and_config()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_parent_link_injected_immediately_before_creation_cannot_escape()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_rename_failure_restores_retired_link_definition_and_receipt()`
def dfh_file_link(target: str | Path, path: str | Path, primary: str | Path) -> None:
	path_p = Path(path)
	dfh_prepare_link_parent(path_p, 'role')
	path_p.symlink_to(target, target_is_directory=False)
# @used-by :func:`Df.Harness.lib.native_ag_plan._merge_ag_hooks()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_config_json()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_hooks()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_manifests()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_mcp_json()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_runner()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_shared_plan()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_agents_md()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_config_toml()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_retire_owned_project_projections()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._collect_role_backup_originals()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._match_owned_role_block()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_profile_role()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_shared_role()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__handle_failure()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_managed_link_and_native_links_edge_helpers()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_codex_roles_and_proof_metadata_tail()`
def dfh_hash(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_roles()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_skills()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_managed_link_and_native_links_edge_helpers()`
def dfh_is_relocated_owned_link(path: str | Path, prior_target: Any, current_target: str | Path, relocated_targets: Any) -> bool:
	r = False
	if isinstance(prior_target, str):
		owned = {os.path.normcase(str(dfh_absolute(t))) for t in (current_target, *relocated_targets)}
		if os.path.normcase(str(dfh_absolute(prior_target))) in owned:
			try:
				actual = os.path.normcase(str(dfh_link_target_path(path)))
				r = actual in {os.path.normcase(str(dfh_absolute(t))) for t in relocated_targets}
			except OSError:
				r = False
	return r
# @used-by :func:`Df.Harness.lib.native_ag_plan._merge_ag_hooks()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_config_json()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_hooks()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_manifests()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_mcp_json()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._populate_ag_shared_outputs()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_retire_owned_project_projections()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__commit_receipt()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__handle_failure()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.backup_payload()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_rename_retires_owned_dangling_link_with_identity_backup()`
def dfh_json_bytes(data: Any) -> bytes:
	return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_obsolete_skill_entry()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_profile_role()`
# @used-by :func:`dfh_remove_link()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.verify_retired()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_managed_link_and_native_links_edge_helpers()`
def dfh_link_matches_target(path: str | Path, target: str | Path) -> bool:
	r = False
	try:
		r = dfh_same_path(path, target)
	except OSError:
		r = False
	if not r:
		r = dfh_is_linked_path(path) and os.path.normcase(str(dfh_link_target_path(path))) == os.path.normcase(str(dfh_absolute(target)))
	return r
# @used-by :func:`Df.Harness.lib.native_codex_roles._handle_existing_codex_link()`
# @used-by :func:`dfh_direct_link_matches_target()`
# @used-by :func:`dfh_is_relocated_owned_link()`
# @used-by :func:`dfh_link_matches_target()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_managed_link_and_native_links_edge_helpers()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_install_global_recovers_dangling_relocated_codex_links_when_receipt_already_points_to_primary()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_install_global_rewrites_manifests_and_codex_links_even_when_compatibility_junction_exists()`
def dfh_link_target_path(path: str | Path) -> Path:
	raw = os.readlink(path)
	if raw.startswith(('\\\\?\\', '\\??\\')):
		raw = raw[4:]
	cand = Path(raw)
	return dfh_absolute(cand if cand.is_absolute() else Path(path).parent / cand)
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_build_shared_native()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_install_native_profiles()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_retire_owned_project_projections()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_native_profiles_install_rename_retire_and_rollback()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.former_role_config()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_edited_obsolete_role_link_blocks_rename_without_orphaning_ownership()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_former_config_role_block_without_receipt_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_project_retirement_requires_exact_ownership_and_keeps_unrelated_files()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_rename_keeps_unselected_profile_and_shared_target_owned()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_rename_retires_only_owned_links_and_shared_definition()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_rename_does_not_touch_unselected_profile_or_forget_ownership()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_rename_retires_owned_dangling_link_with_identity_backup()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unknown_prior_link_record_is_preserved_during_skill_rename()`
# @used-by :meth:`test_portability.ProjectionTests.test_shared_generation_uses_one_owner_across_projects_and_profile_install()`
def dfh_load_state(primary: str | Path) -> dict:
	path = dfh_state_path(primary)
	data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'backups': {}, 'profiles': {}, 'schema_version': 1, 'shared': {}}
	if not isinstance(data, dict) or 1 != data.get('schema_version') or any((not isinstance(data.get(key, {}), dict) for key in ('shared', 'profiles', 'backups'))):
		raise ValueError('Native profile ownership receipt is malformed; preserved')
	return data
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_roles()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_skills()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_profile_agents()`
def dfh_normalized_text(text: str) -> str:
	return text.replace('\r\n', '\n').replace('/scripts/upwork_project.py', '/scripts/harness.py').replace('via upwork_project.py git-read', 'via harness.py git-read').replace('run upwork_project.py build-native', 'run harness.py build-native').strip()
# @used-by :func:`dfh_directory_link()`
# @used-by :func:`dfh_file_link()`
# @used-by :func:`dfh_restore_directory_link()`
def dfh_prepare_link_parent(path: Path, label: str, action: str='creation') -> None:
	if dfh_has_linked_ancestor(path, include_self=False):
		raise ValueError(f'Linked {label} parent directory appeared before {action}; preserved: {path}')
	path.parent.mkdir(parents=True, exist_ok=True)
	if dfh_has_linked_ancestor(path, include_self=False):
		raise ValueError(f'Linked {label} parent directory appeared before {action}; preserved: {path}')
# @used-by :func:`Df.Harness.lib.native_ag_plan._merge_ag_hooks()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_manifest()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_shared_plan()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_codex_plan()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_obsolete_skill_entry()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_retire_shared_roles()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_role_identity()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_managed_link_and_native_links_edge_helpers()`
def dfh_relocated_primaries(primary: str | Path) -> tuple[Path, ...]:
	return tuple((dfh_absolute(p) for p in dfh_relocated_harness_code_dirs(primary=primary)))
# @used-by :func:`agent_tools.native_profiles._facade_ops()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.remove_created()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.retire()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.check_skill_rename_rollback()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_dangling_directory_symlink_skill_is_retired()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_manually_replaced_obsolete_skill_directory_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_obsolete_skill_changed_during_backup_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_wrong_target_obsolete_skill_link_is_preserved()`
def dfh_remove_link(path: str | Path, target: str | Path) -> None:
	path_p = Path(path)
	if dfh_has_linked_ancestor(path_p, include_self=False) or not dfh_is_linked_path(path_p) or (not dfh_link_matches_target(path_p, target)):
		raise ValueError(f'Created link changed before rollback; preserved: {path_p}')
	path_p.rmdir() if bool(getattr(path_p, 'is_junction', lambda: False)()) else path_p.unlink()
# @used-by :func:`agent_tools.native_profiles._restore_directory_link()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.restore_retired()`
def dfh_restore_directory_link(path: str | Path, identity: dict, primary: str | Path, *, dir_link_fn: Any=None) -> None:
	path_p = Path(path)
	if 'directory-junction' == identity['kind']:
		(dir_link_fn or dfh_directory_link)(identity['target'], path_p, primary)
	else:
		dfh_prepare_link_parent(path_p, 'obsolete skill', 'restoration')
		path_p.symlink_to(identity['target'], target_is_directory=True)
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.retire()`
def dfh_retire_directory_link(path: str | Path, identity: dict) -> None:
	path_p = Path(path)
	dfh_verify_retired_directory_link(path_p, identity)
	path_p.rmdir() if 'directory-junction' == identity['kind'] else path_p.unlink()
# @used-by :func:`Df.Harness.lib.native_ag_plan._manifest_build_inherits()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._manifest_filter_entries()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_roles()`
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_skills()`
# @used-by :func:`dfh_link_matches_target()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.verify_created()`
def dfh_same_path(first: str | Path, second: str | Path) -> bool:
	return Path(first).resolve() == Path(second).resolve()
# @used-by :func:`dfh_load_state()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__apply()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.check_skill_rename_rollback()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.former_role_config()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_concurrent_personal_edit_does_not_stop_other_guarded_rollback()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_concurrent_replacement_during_skill_rollback_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_former_config_role_block_without_receipt_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_install_global_recovers_dangling_relocated_codex_links_when_receipt_already_points_to_primary()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_new_link_failure_rolls_back_existing_profile_files()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_obsolete_skill_changed_during_backup_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_link_failure_restores_retired_roles_and_config()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_rename_failure_restores_retired_link_definition_and_receipt()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unknown_prior_link_record_is_preserved_during_skill_rename()`
def dfh_state_path(primary: str | Path) -> Path:
	return dfh_data_dir_for(primary) / 'native-profiles' / 'ownership.json'
# @used-by :func:`dfh_retire_directory_link()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.verify_retired()`
def dfh_verify_retired_directory_link(path: str | Path, identity: dict) -> None:
	if dfh_has_linked_ancestor(path, include_self=False) or not dfh_is_linked_path(path) or dfh_directory_link_identity(path) != identity:
		raise ValueError(f'Obsolete skill link changed during migration; preserved: {path}')
