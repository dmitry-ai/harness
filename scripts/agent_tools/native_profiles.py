# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Config.NativeProfile.Applier import Applier
from Df.Harness.Config.NativeProfile.ApplyFailure import ApplyFailure as _ApplyFailure
from Df.Harness.Config.NativeProfile.ManagedLink import ManagedLink as _ManagedLink
from Df.Harness.Config.NativeProfile.Plan import Plan as _Plan
from Df.Harness.lib.config_blocks import DISCOVERY_KINDS as KINDS, dfh_has_linked_ancestor as _linked_ancestor, dfh_is_linked_path as _linked
from Df.Harness.lib.native_ag_plan import dfh_antigravity_plan, dfh_legacy_project_projection_paths, dfh_manifest as _manifest, dfh_model_fields, dfh_profile_state as _profile_state, dfh_role_values, dfh_shared_native_outputs, dfh_shared_plan, dfh_skills as _skills
from Df.Harness.lib.native_codex_plan import dfh_build_shared_native, dfh_codex_plan, dfh_install_native_profiles, dfh_retire_owned_project_projections
from Df.Harness.lib.native_codex_roles import dfh_compact_loader as _compact_loader, dfh_disable_codex_bundled_chrome_plugin as _disable_codex_bundled_chrome_plugin, dfh_legacy_role, dfh_legacy_role_config as _legacy_role_config, dfh_legacy_skill as _legacy_skill, dfh_plan_codex_link, dfh_profile_agents as _profile_agents, dfh_retire_profile_roles, dfh_retire_profile_skills, dfh_retire_shared_roles as _retire_shared_roles, dfh_role_config as _role_config, dfh_role_identity as _role_identity
from Df.Harness.lib.native_links import END, ISSUE, PURPOSES, START, dfh_absolute as _absolute, dfh_backup as _backup, dfh_configuration, dfh_direct_link_matches_target as _direct_link_matches_target, dfh_directory_link, dfh_directory_link_identity as _directory_link_identity, dfh_exists as _exists, dfh_file_link as _file_link, dfh_hash as _hash, dfh_is_relocated_owned_link as _is_relocated_owned_link, dfh_json_bytes as _json, dfh_link_matches_target as _link_matches_target, dfh_link_target_path as _link_target_path, dfh_load_state as _load_state, dfh_normalized_text as _normalized, dfh_prepare_link_parent as _prepare_link_parent, dfh_relocated_primaries as _relocated_primaries, dfh_remove_link as _remove_link, dfh_restore_directory_link, dfh_retire_directory_link as _retire_directory_link, dfh_same_path as _same_path, dfh_state_path as _state_path, dfh_verify_retired_directory_link as _verify_retired_directory_link
from . import runtime as _runtime_mod
from .runtime import PRIMARY, settings
from .storage import create_bytes, data_dir_for, locked, replace_bytes
_UNPATCHED_SETTINGS = settings
# @used-by :func:`_antigravity_plan()`
# @used-by :func:`_codex_plan()`
# @used-by :func:`_configuration()`
# @used-by :func:`_directory_link()`
# @used-by :func:`_legacy_role()`
# @used-by :func:`_model_fields()`
# @used-by :func:`_retire_profile_roles()`
# @used-by :func:`_role_values()`
# @used-by :func:`_shared_plan()`
# @used-by :func:`build_shared_native()`
# @used-by :func:`install_native_profiles()`
# @used-by :func:`legacy_project_projection_paths()`
# @used-by :func:`retire_owned_project_projections()`
# @used-by :func:`shared_native_outputs()`
def _active_settings(path=None):
	fn = settings if settings is not _UNPATCHED_SETTINGS else _runtime_mod.settings
	return fn() if None is path else fn(path)
# @used-by :func:`_codex_plan()`
# @used-by :func:`_execute()`
# @used-by :func:`_plan_codex_link()`
# @used-by :func:`_retire_profile_roles()`
# @used-by :func:`_retire_profile_skills()`
# @used-by :func:`build_shared_native()`
# @used-by :func:`install_native_profiles()`
# @used-by :func:`retire_owned_project_projections()`
def _facade_ops() -> dict:
	return {'backup': _backup, 'create_bytes': create_bytes, 'directory_link': _directory_link, 'file_link': _file_link, 'remove_link': _remove_link, 'replace_bytes': replace_bytes}
# @used-by unused
def _antigravity_plan(plan, name, config, primary, state):
	return dfh_antigravity_plan(plan, name, config, primary, state, settings_fn=_active_settings)
# @used-by unused
def _codex_plan(plan, name, home, primary, state):
	return dfh_codex_plan(plan, name, home, primary, state, settings_fn=_active_settings, ops=_facade_ops())
# @used-by unused
def _configuration(primary):
	return dfh_configuration(primary, settings_fn=_active_settings)
# @used-by :func:`_facade_ops()`
# @used-by :func:`_restore_directory_link()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.check_skill_rename_rollback()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_install_global_recovers_dangling_relocated_codex_links_when_receipt_already_points_to_primary()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_install_global_rewrites_manifests_and_codex_links_even_when_compatibility_junction_exists()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_new_link_failure_rolls_back_existing_profile_files()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_obsolete_skill_changed_during_backup_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_obsolete_skill_under_linked_parent_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_project_retirement_skips_a_linked_source_directory()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_parent_link_injected_immediately_before_creation_cannot_escape()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_parent_link_injected_during_backup_is_preserved_without_escape()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_parent_link_injected_immediately_before_creation_cannot_escape()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_rename_retires_owned_dangling_link_with_identity_backup()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unknown_prior_link_record_is_preserved_during_skill_rename()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_wrong_skill_link_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_wrong_target_obsolete_skill_link_is_preserved()`
def _directory_link(target, path, primary):
	return dfh_directory_link(target, path, primary, settings_fn=_active_settings)
# @used-by unused
def _execute(plan, primary, state, *, check=False):
	return Applier(plan, primary, state, check=check, ops=_facade_ops()).run()
# @used-by :meth:`test_native_profiles.NativeProfileTests.legacy_codex()`
def _legacy_role(primary, role, name, purpose):
	return dfh_legacy_role(primary, role, name, purpose, settings_fn=_active_settings)
# @used-by unused
def _model_fields(primary, role):
	return dfh_model_fields(primary, role, settings_fn=_active_settings)
# @used-by unused
def _plan_codex_link(plan, profile, link, active_valid, active_error, retire_path, legacy_valid, legacy_error, relocated_valid=lambda: False):
	return dfh_plan_codex_link(plan, profile, link, active_valid, active_error, retire_path, legacy_valid, legacy_error, relocated_valid=relocated_valid, ops=_facade_ops())
# @used-by unused
def _restore_directory_link(path, identity, primary):
	return dfh_restore_directory_link(path, identity, primary, dir_link_fn=_directory_link)
# @used-by unused
def _retire_profile_roles(plan, profile, previous, home, primary, state):
	return dfh_retire_profile_roles(plan, profile, previous, home, primary, state, settings_fn=_active_settings, ops=_facade_ops())
# @used-by unused
def _retire_profile_skills(plan, profile, previous, home, primary, skills):
	return dfh_retire_profile_skills(plan, profile, previous, home, primary, skills, ops=_facade_ops())
# @used-by :meth:`test_native_profiles.NativeProfileTests.former_role_config()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.legacy_codex()`
def _role_values(primary):
	return dfh_role_values(primary, settings_fn=_active_settings)
# @used-by unused
def _shared_plan(plan, primary, state):
	return dfh_shared_plan(plan, primary, state, settings_fn=_active_settings)
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_build_native_publishes_shared_hooks_and_upgrades_stop_only_final_turn_gate()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_concurrent_personal_edit_does_not_stop_other_guarded_rollback()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_shared_manual_edit_is_preserved()`
def build_shared_native(primary=PRIMARY, *, check=False):
	return dfh_build_shared_native(primary, check=check, settings_fn=_active_settings, ops=_facade_ops())
# @used-by :func:`agent_tools.upwork_project._install_profile_customizations()`
# @used-by :func:`agent_tools.upwork_project.check_global_customizations()`
# @used-by :func:`agent_tools.upwork_project.install_global_customizations()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests.test_doctor_reports_and_validates_global_git_ignore()`
# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests.test_install_global_check_and_apply_preserve_user_rules_and_are_idempotent()`
# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests.test_isolated_synthetic_primary_skips_host_git_ignore_mutation()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_all_disabled_and_claude_code_only_environment_without_antigravity_or_codex()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_future_environment_claude_code_is_supported_without_roles_or_adapters()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.install()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_install_global_recovers_dangling_relocated_codex_links_when_receipt_already_points_to_primary()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_install_global_rewrites_manifests_and_codex_links_even_when_compatibility_junction_exists()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_v2_unicode_primary_generates_ascii_hook_runner_upgrades_legacy_hooks_and_runs_via_cmd_exe()`
# @used-by :meth:`test_portability.ProjectionTests.test_shared_generation_uses_one_owner_across_projects_and_profile_install()`
def install_native_profiles(target_profiles=None, *, check=False, primary=PRIMARY, config_dirs=None, codex_homes=None, git_ignore_path=None):
	return dfh_install_native_profiles(target_profiles, check=check, primary=primary, config_dirs=config_dirs, codex_homes=codex_homes, git_ignore_path=git_ignore_path, settings_fn=_active_settings, ops=_facade_ops())
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_edited_project_projection_blocks_all_retirements()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_project_retirement_requires_exact_ownership_and_keeps_unrelated_files()`
def legacy_project_projection_paths(root, primary=PRIMARY):
	return dfh_legacy_project_projection_paths(root, primary, settings_fn=_active_settings)
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_edited_project_projection_blocks_all_retirements()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_project_retirement_requires_exact_ownership_and_keeps_unrelated_files()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_project_retirement_skips_a_linked_source_directory()`
def retire_owned_project_projections(root, *, check=False, primary=PRIMARY):
	return dfh_retire_owned_project_projections(root, check=check, primary=primary, settings_fn=_active_settings, ops=_facade_ops())
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_native_profiles_generates_arch_auditor_for_antigravity_and_codex()`
# @used-by :meth:`test_arch_rules_contract.ArchRulesContractTests.test_architecture_rule_is_compact_always_on_and_passes_doctor_and_rules_audit()`
# @used-by :meth:`test_code_formatting_rules.CodeFormattingRulesContractTests.test_general_rule_passes_doctor_native_bootstrap_and_lint()`
# @used-by :meth:`test_comment_exemption_and_denied_writes.CommentExemptionAndDeniedWritesTests.test_issue_comment_gate_skips_body_misalignment_on_comment_only_diff()`
# @used-by :meth:`test_portability.ProjectionTests.test_shared_generation_uses_one_owner_across_projects_and_profile_install()`
# @used-by :meth:`test_rules_architecture_m2.RulesArchitectureM2Tests.test_codex_adapter_and_bootstrap_match_three_layer_rules()`
# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_shared_native_outputs_af_worker_includes_file_handoff_contract()`
def shared_native_outputs(primary=PRIMARY):
	return dfh_shared_native_outputs(primary, settings_fn=_active_settings)
