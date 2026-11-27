# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Config.NativeBuilder import NativeBuilder
from Df.Harness.Config.ProjectionPublisher import ProjectionPublisher
from Df.Harness.lib.config_blocks import DISCOVERY_KINDS, END, START, _toml_statements, dfh_digest as _digest, dfh_extract_managed_block as extract_managed_block, dfh_frontmatter as _frontmatter, dfh_has_linked_ancestor as has_linked_ancestor, dfh_is_linked_path as is_linked_path, dfh_load_discovery_manifest as load_discovery_manifest, dfh_load_project_receipt as load_project_receipt, dfh_project_discovery_entries as project_discovery_entries, dfh_receipt_sha256 as receipt_sha256, dfh_replace_managed_block as replace_managed_block, dfh_resolve_manifest_entry as resolve_manifest_entry, dfh_root_options as _root_options, dfh_store_content_backup as store_content_backup
from Df.Harness.lib.config_codex import dfh_configure_codex_project, dfh_global_codex_instructions, dfh_loader as _loader, dfh_native_config as _native_config, dfh_primary_settings, dfh_project_rule_paths as _project_rule_paths
from . import runtime as _runtime_mod
from .runtime import PRIMARY, extract_platform_instances, profile_name, settings
_UNPATCHED_SETTINGS = settings
_UNPATCHED_PROFILE_NAME = profile_name
# @used-by :func:`_primary_settings()`
# @used-by :func:`build_native()`
# @used-by :func:`configure_codex_project()`
# @used-by :func:`global_codex_instructions()`
def _active_settings(path=None):
	fn = settings if settings is not _UNPATCHED_SETTINGS else _runtime_mod.settings
	return fn() if None is path else fn(path)
# @used-by unused
def _managed_block(value):
	return extract_managed_block(value)
# @used-by unused
def _primary_settings(primary):
	return dfh_primary_settings(primary, settings_fn=_active_settings)
# @used-by unused
def _publish(root, outputs, *, check=False, merge=None, retire=(), disown=(), preflight=False):
	return ProjectionPublisher(root, outputs, check=check, merge=merge, retire=retire, disown=disown, preflight=preflight).run()
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__run_build_native()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.build()`
# @used-by :meth:`test_df_article.LexiconAndProjectionTests.test_build_native_uses_shared_skills_without_project_wrappers()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
# @used-by :meth:`test_portability.ProjectionTests.test_check_does_not_create_an_uninstalled_workspace()`
# @used-by :meth:`test_portability.ProjectionTests.test_dangling_personal_guidance_links_are_preserved_before_shared_publication()`
# @used-by :meth:`test_portability.ProjectionTests.test_first_install_preserves_an_unowned_antigravity_worker()`
# @used-by :meth:`test_portability.ProjectionTests.test_generation_is_idempotent_detects_source_changes_and_preserves_manual_edits()`
# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
# @used-by :meth:`test_portability.ProjectionTests.test_shared_generation_uses_one_owner_across_projects_and_profile_install()`
# @used-by :meth:`test_portability.ProjectionTests.test_unowned_legacy_prevents_partial_migration()`
# @used-by :meth:`test_portability.ProjectionTests.test_verified_legacy_migrates_but_manual_configuration_and_fallback_survive()`
def build_native(root=None, *, primary=PRIMARY, check=False):
	return NativeBuilder(root, primary=primary, check=check, settings_fn=_active_settings).run()
# @used-by :meth:`Df.Harness.Upwork.ConfigurationChecker.ConfigurationChecker.check()`
# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.configure()`
# @used-by :meth:`test_portability.ProjectionTests.test_project_rules_feed_both_systems_and_detect_stale_codex_projection()`
def configure_codex_project(root, primary=PRIMARY, job_url=None, label=None, *, check=False):
	return dfh_configure_codex_project(root, primary, job_url, label, check=check, settings_fn=_active_settings)
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__run_policy_instructions()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
# @used-by :meth:`test_portability.ProjectionTests.test_global_instructions_are_read_safely_and_local_override_keeps_its_priority()`
def global_codex_instructions():
	pfn = profile_name if profile_name is not _UNPATCHED_PROFILE_NAME else _runtime_mod.profile_name
	return dfh_global_codex_instructions(settings_fn=_active_settings, profile_name_fn=pfn)
