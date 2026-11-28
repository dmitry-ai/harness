# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.runtime_cache import dfh_cached_addon_roots, dfh_skip_shell_violations as skip_shell_violations
from Df.Harness.lib.runtime_context import CONTEXT_INSTANCE as _instance, CONTEXT_PLATFORM as _platform, CONTEXT_PROFILE as _profile, dfh_default_user_locale, dfh_platform_name, dfh_platform_settings, dfh_profile_name, dfh_registration_profile_name, dfh_request_day, dfh_role_settings, dfh_using
from Df.Harness.lib.runtime_instances import dfh_all_instances, dfh_default_system_paths, dfh_enabled_platforms, dfh_extract_platform_homes, dfh_extract_platform_instances, dfh_instance_entry, dfh_instance_paths, dfh_platform_active, dfh_platform_adapter_name, dfh_platform_enabled, dfh_platform_homes, dfh_platform_instances, dfh_platform_key_for_adapter, dfh_resolve_platform_cfg
from Df.Harness.lib.runtime_resolve import dfh_antigravity_backend_has_conversation as _antigravity_backend_has_conversation, dfh_codex_home_conversation_trace as _codex_home_conversation_trace, dfh_find_conversation_instance, dfh_resolve_antigravity_backend, dfh_resolve_antigravity_paths, dfh_resolve_codex_home, dfh_resolve_codex_paths
from Df.Harness.lib.runtime_validate import dfh_exists_flag as _exists_flag, dfh_expand_path as _expand_path, dfh_has_glob_wildcard as _has_glob_wildcard, dfh_resolve_glob_paths as _resolve_glob_paths, dfh_validate_runtime as _validate_runtime
import os
import sys
from .path_registry import DEFAULT_REGISTRY_FILE, _CODE_ANCHOR, default_platform_paths, default_runtime_file, derive_platform_system_paths, load_registry, normalize_path_str, store_path, tool_path, var_value
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
PRIMARY = Path(var_value('HARNESS_CODE')).resolve()
HARNESS_ROOT = Path(var_value('HARNESS_ROOT')).resolve()
HARNESS_META = Path(var_value('HARNESS_META')).resolve()
LEGACY_PRIMARY = store_path('legacy_primary')
os.environ.setdefault('GIT_OPTIONAL_LOCKS', '0')
_SHIM_DIR = str(tool_path('git_shim_dir').resolve())
if _SHIM_DIR not in os.environ.get('PATH', '').split(os.pathsep):
	os.environ['PATH'] = _SHIM_DIR + os.pathsep + os.environ.get('PATH', '')
# @used-by unused
def _resolve_platform_cfg(platform, *, config=None):
	return dfh_resolve_platform_cfg(platform, config=config, settings_fn=settings)
# @used-by :meth:`Df.Harness.Upwork.DoctorAuditor.DoctorAuditor.audit()`
# @used-by :meth:`Df.Harness.Upwork.InstancesReporter.InstancesReporter.report()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_custom_adapter_platform_keys_and_instruction_snapshot()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_future_environment_claude_code_is_supported_without_roles_or_adapters()`
# @used-by :mod:`agent_tools.upwork_project`
def all_instances(*, config=None, platform=None, include_disabled=True, check_exists=False):
	return dfh_all_instances(config=config, platform=platform, include_disabled=include_disabled, check_exists=check_exists, settings_fn=settings)
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_default_system_paths_overrides_and_nested_codex_globs()`
def default_system_paths(platform, inst_id, inst_cfg, plat_cfg=None):
	return dfh_default_system_paths(platform, inst_id, inst_cfg, plat_cfg)
# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_language_neutral_slash_commands_enforce_user_default_locale_without_breaking_english_requests()`
def default_user_locale(config=None) -> str | None:
	return dfh_default_user_locale(config=config, settings_fn=settings)
# @used-by unused
def enabled_platforms(*, config=None):
	return dfh_enabled_platforms(config=config, settings_fn=settings)
# @used-by :func:`Df.Harness.lib.browser.dfh_profile()`
# @used-by :func:`agent_tools.platforms.codex._cx_ops()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_codex_custom_system_paths_trace_requests_metadata_and_answers()`
def extract_platform_homes(plat_cfg, *, platform='', include_disabled=False):
	return dfh_extract_platform_homes(plat_cfg, platform=platform, include_disabled=include_disabled)
# @used-by :meth:`Df.Harness.Text.DiagnosticsScanner.DiagnosticsScanner.__scan_codex_profiles()`
# @used-by :meth:`Df.Harness.Upwork.GlobalCustomizationManager.GlobalCustomizationManager.antigravity_global_config_dirs()`
# @used-by :mod:`agent_tools.upwork_project`
def extract_platform_instances(plat_cfg, *, platform='', include_disabled=False):
	return dfh_extract_platform_instances(plat_cfg, platform=platform, include_disabled=include_disabled)
# @used-by :func:`resolve_antigravity_backend()`
# @used-by :func:`resolve_antigravity_paths()`
# @used-by :func:`resolve_codex_home()`
# @used-by :func:`resolve_codex_paths()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__resolve_instance_match()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.resolve_target()`
# @used-by :meth:`Df.Harness.Perf.TimesheetCommon.TimesheetCommon.__lookup_conversation_trace()`
# @used-by :meth:`Df.Harness.Perf.TimesheetCommon.TimesheetCommon.__lookup_summary_db_optional()`
# @used-by :meth:`Df.Harness.Upwork.InstancesReporter.InstancesReporter.report()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cross_instance_handoff_and_audit_resolve_antigravity_and_disabled_codex_traces()`
# @used-by :mod:`agent_tools.upwork_project`
def find_conversation_instance(conversation_id, *, platform=None, config=None, include_disabled=True):
	return dfh_find_conversation_instance(conversation_id, platform=platform, config=config, include_disabled=include_disabled, settings_fn=settings)
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__resolve_instance_match()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.resolve_target()`
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.main()`
# @used-by :meth:`Df.Harness.Upwork.InstancesReporter.InstancesReporter.report()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_custom_adapter_platform_keys_and_instruction_snapshot()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_platform_enabled_false_disables_all_instances_of_environment()`
# @used-by :mod:`agent_tools.upwork_project`
def instance_entry(instance_id, *, platform=None, config=None, include_disabled=True):
	return dfh_instance_entry(instance_id, platform=platform, config=config, include_disabled=include_disabled, settings_fn=settings, instances_fn=platform_instances)
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_live_runtime_declares_environments_instances_enabled_states_and_system_paths()`
def instance_paths(instance_id, *, platform=None, config=None, include_disabled=True):
	return dfh_instance_paths(instance_id, platform=platform, config=config, include_disabled=include_disabled, settings_fn=settings, instances_fn=platform_instances)
# @used-by :meth:`Df.Harness.Project.Registry.Registry.__resolve_targets()`
# @used-by :meth:`Df.Harness.Upwork.GlobalCustomizationManager.GlobalCustomizationManager.antigravity_global_config_dirs()`
# @used-by :meth:`Df.Harness.Workflow.RegistrationStatusChecker.RegistrationStatusChecker.status()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_live_runtime_declares_environments_instances_enabled_states_and_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_platform_enabled_false_disables_all_instances_of_environment()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_single_enabled_codex_instance_works_with_shared_catalog_superset()`
# @used-by :mod:`agent_tools.upwork_project`
def platform_active(platform, *, config=None):
	return dfh_platform_active(platform, config=config, settings_fn=settings)
# @used-by :func:`agent_tools.platforms.adapter()`
def platform_adapter_name(platform, plat_cfg=None, *, config=None):
	return dfh_platform_adapter_name(platform, plat_cfg, config=config, settings_fn=settings)
# @used-by unused
def platform_enabled(platform, *, config=None):
	return dfh_platform_enabled(platform, config=config, settings_fn=settings)
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__build_parser()`
# @used-by :mod:`agent_tools.upwork_project`
def platform_homes(platform, *, config=None, include_disabled=False):
	return dfh_platform_homes(platform, config=config, include_disabled=include_disabled, settings_fn=settings)
# @used-by :func:`agent_tools.platforms.antigravity._ag_ops()`
# @used-by :func:`agent_tools.platforms.antigravity._default_folders_json()`
# @used-by :func:`agent_tools.platforms.antigravity._proof_paths()`
# @used-by :func:`agent_tools.platforms.antigravity._resolve_folders_json()`
# @used-by :func:`instance_entry()`
# @used-by :func:`instance_paths()`
# @used-by :func:`resolve_antigravity_backend()`
# @used-by :func:`resolve_antigravity_paths()`
# @used-by :func:`resolve_codex_home()`
# @used-by :func:`resolve_codex_paths()`
# @used-by :meth:`Df.Harness.Meta.ProjectIdentity.ProjectIdentity.antigravity_project_dirs()`
# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__antigravity_dirs_map()`
# @used-by :meth:`test_addons_profile_adapter.AddonsProfileAdapterTests.test_live_runtime_uses_addons_profiles_json_source_and_paths_registers_profile_manager_tests()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests._make_old_project()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests._init_and_register()`
# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests._make_project()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_per_instance_folders_json_uninitialized_instance_and_stop_gate_a6()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_skips_disabled_codex_and_checks_all_enabled_antigravity_instances()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_dynamic_folders_json_and_cleanup_without_homes()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_live_runtime_declares_environments_instances_enabled_states_and_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_platform_enabled_false_disables_all_instances_of_environment()`
# @used-by :mod:`agent_tools.upwork_project`
def platform_instances(platform, *, config=None, include_disabled=False):
	return dfh_platform_instances(platform, config=config, include_disabled=include_disabled, settings_fn=settings)
# @used-by :mod:`agent_tools.platforms.antigravity`
def platform_key_for_adapter(adapter_name, config=None):
	return dfh_platform_key_for_adapter(adapter_name, config=config, settings_fn=settings)
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :func:`agent_tools.platforms.adapter()`
# @used-by :meth:`Df.Harness.Project.RegistrationStore.RegistrationStore.__init__()`
# @used-by :meth:`Df.Harness.Project.Registry.Registry.register()`
# @used-by :meth:`Df.Harness.Review.InputReceiptBuilder.InputReceiptBuilder.build()`
# @used-by :meth:`Df.Harness.Upwork.DoctorAuditor.DoctorAuditor.__resolve_platform_cfg()`
# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.initialize()`
# @used-by :meth:`Df.Harness.Workflow.RegistrationStatusChecker.RegistrationStatusChecker.status()`
# @used-by :mod:`agent_tools.upwork_project`
def platform_name(value=None, *, config=None):
	return dfh_platform_name(value=value, config=config, settings_fn=settings)
# @used-by :func:`Df.Harness.lib.browser.dfh_resolve_cdp_port()`
# @used-by :func:`agent_tools.platforms.antigravity._ag_ops()`
# @used-by :func:`agent_tools.platforms.antigravity._native_invocation()`
# @used-by :func:`agent_tools.platforms.codex._cx_ops()`
# @used-by :func:`agent_tools.platforms.codex._paths()`
# @used-by :func:`agent_tools.platforms.codex._trace()`
# @used-by :func:`agent_tools.platforms.codex.native_requests()`
# @used-by :func:`agent_tools.platforms.codex.require_current_binding()`
# @used-by :func:`agent_tools.platforms.codex.shared_control()`
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`Df.Harness.Meta.ProjectIdentity.ProjectIdentity.resolve_codex_paths_safe()`
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__init__()`
# @used-by :meth:`Df.Harness.Upwork.DoctorAuditor.DoctorAuditor.__init__()`
# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init__()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.selected()`
# @used-by :meth:`test_portability.CodexEvidenceTests.selected()`
# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
# @used-by :mod:`agent_tools.upwork_project`
def platform_settings(name=None):
	return dfh_platform_settings(name=name, settings_fn=settings)
# @used-by :func:`agent_tools.configuration.global_codex_instructions()`
# @used-by :meth:`Df.Harness.Workflow.RegistrationStatusChecker.RegistrationStatusChecker.__resolve_profile()`
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.test_registration_only_fallback_does_not_relax_native_evidence_profile()`
# @used-by :mod:`agent_tools.configuration`
def profile_name(value=None, *, config=None, include_disabled=True):
	return dfh_profile_name(value=value, config=config, include_disabled=include_disabled, settings_fn=settings)
# @used-by :func:`agent_tools.platforms.codex._cx_ops()`
# @used-by :meth:`Df.Harness.Workflow.RegistrationStatusChecker.RegistrationStatusChecker.__resolve_profile()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_custom_adapter_platform_keys_and_instruction_snapshot()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_platform_enabled_false_disables_all_instances_of_environment()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_single_enabled_codex_instance_works_with_shared_catalog_superset()`
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.test_explicit_unknown_profile_or_unrecognized_home_never_uses_fallback()`
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.test_registration_only_fallback_does_not_relax_native_evidence_profile()`
def registration_profile_name(value=None, *, config=None):
	return dfh_registration_profile_name(value=value, config=config, settings_fn=settings)
# @used-by :func:`agent_tools.platforms.codex._cx_ops()`
# @used-by :meth:`Df.Harness.Project.RegistrationExpectation.RegistrationExpectation.build()`
# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__sync_antigravity_native_files()`
# @used-by :meth:`Df.Harness.Upwork.ProjectDirResolver.ProjectDirResolver.resolve_or_create()`
# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.initialize()`
# @used-by :mod:`agent_tools.upwork_project`
def request_day(value=None):
	return dfh_request_day(value=value, settings_fn=settings)
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cross_instance_handoff_and_audit_resolve_antigravity_and_disabled_codex_traces()`
def resolve_antigravity_backend(backend=None, *, instance=None, conversation_id=None, config=None):
	return dfh_resolve_antigravity_backend(backend=backend, instance=instance, conversation_id=conversation_id, config=config, settings_fn=settings, find_conv_fn=find_conversation_instance, instances_fn=platform_instances)
# @used-by :meth:`Df.Harness.Meta.ProjectIdentity.ProjectIdentity.resolve_ag_paths_safe()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_custom_adapter_platform_keys_and_instruction_snapshot()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
def resolve_antigravity_paths(backend=None, *, instance=None, conversation_id=None, config=None):
	return dfh_resolve_antigravity_paths(backend=backend, instance=instance, conversation_id=conversation_id, config=config, settings_fn=settings, find_conv_fn=find_conversation_instance, instances_fn=platform_instances)
# @used-by unused
def resolve_codex_home(backend=None, *, instance=None, conversation_id=None, config=None, codex_cfg=None):
	return dfh_resolve_codex_home(backend=backend, instance=instance, conversation_id=conversation_id, config=config, codex_cfg=codex_cfg, settings_fn=settings, find_conv_fn=find_conversation_instance, instances_fn=platform_instances)
# @used-by :meth:`Df.Harness.Meta.ProjectIdentity.ProjectIdentity.resolve_codex_paths_safe()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_custom_adapter_platform_keys_and_instruction_snapshot()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_dynamic_folders_json_and_cleanup_without_homes()`
def resolve_codex_paths(backend=None, *, instance=None, conversation_id=None, config=None, codex_cfg=None):
	return dfh_resolve_codex_paths(backend=backend, instance=instance, conversation_id=conversation_id, config=config, codex_cfg=codex_cfg, settings_fn=settings, find_conv_fn=find_conversation_instance, instances_fn=platform_instances)
# @used-by :meth:`Df.Harness.Upwork.DoctorAuditor.DoctorAuditor.audit()`
# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
# @used-by :mod:`agent_tools.upwork_project`
def role_settings(platform, role, seen=()):
	return dfh_role_settings(platform, role, seen=seen, settings_fn=settings)
# @used-by :meth:`Df.Harness.Gate.CdpBypassGate.CdpBypassGate.is_inside_sanctioned_code()`
# @used-by :meth:`Df.Harness.Git.CdpBypassAudit.CdpBypassAudit.__is_sanctioned_addon()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_sanctioned_addon_roots_and_cdp_bypass_gate()`
def sanctioned_addon_code_roots(config=None):
	return dfh_cached_addon_roots(config, sys.modules[__name__], _expand_path)
# @used-by :func:`Df.Harness.lib.browser.dfh_resolve_cdp_port()`
# @used-by :func:`Df.Harness.lib.browser.dfh_resolve_headless_shell()`
# @used-by :func:`Df.Harness.lib.text_core.dfh_default_shell()`
# @used-by :func:`_resolve_platform_cfg()`
# @used-by :func:`agent_tools.cleanup.cleanup_projects()`
# @used-by :func:`agent_tools.cleanup.record_cleanup_answer()`
# @used-by :func:`agent_tools.cleanup_audit.record_cleanup_answer_log()`
# @used-by :func:`agent_tools.cleanup_audit.resolve_cleanup_log_root()`
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :func:`agent_tools.configuration._active_settings()`
# @used-by :func:`agent_tools.native_profiles._active_settings()`
# @used-by :func:`agent_tools.operations.add_parsers()`
# @used-by :func:`agent_tools.platforms.adapter()`
# @used-by :func:`agent_tools.platforms.antigravity._ag_ops()`
# @used-by :func:`agent_tools.platforms.antigravity._antigravity_paths()`
# @used-by :func:`agent_tools.platforms.antigravity._default_folders_json()`
# @used-by :func:`agent_tools.platforms.antigravity._native_invocation()`
# @used-by :func:`agent_tools.platforms.antigravity._proof_paths()`
# @used-by :func:`agent_tools.platforms.antigravity._request_scope()`
# @used-by :func:`agent_tools.platforms.antigravity._resolve_folders_json()`
# @used-by :func:`agent_tools.platforms.antigravity._workspace_context()`
# @used-by :func:`agent_tools.platforms.antigravity.discover_live_daemon()`
# @used-by :func:`agent_tools.platforms.antigravity.native_requests()`
# @used-by :func:`agent_tools.platforms.antigravity.require_current_binding()`
# @used-by :func:`agent_tools.platforms.codex._cx_ops()`
# @used-by :func:`agent_tools.registration.register_project()`
# @used-by :func:`agent_tools.registration.register_projects()`
# @used-by :func:`agent_tools.repo_tags.commit_date_day()`
# @used-by :func:`agent_tools.upwork_project.antigravity_global_config_dirs()`
# @used-by :func:`agent_tools.upwork_project.check_configuration()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :func:`agent_tools.upwork_project.instances_report()`
# @used-by :func:`agent_tools.upwork_project.main()`
# @used-by :func:`agent_tools.upwork_project.register_project()`
# @used-by :func:`all_instances()`
# @used-by :func:`check_pre_invocation._resolve_ag_paths()`
# @used-by :func:`check_pre_invocation.evaluate_pre_invocation_payload()`
# @used-by :func:`check_stop_gate._resolve_stop_paths()`
# @used-by :func:`check_stop_gate.evaluate_stop_payload()`
# @used-by :func:`default_user_locale()`
# @used-by :func:`enabled_platforms()`
# @used-by :func:`find_conversation_instance()`
# @used-by :func:`instance_entry()`
# @used-by :func:`instance_paths()`
# @used-by :func:`platform_active()`
# @used-by :func:`platform_adapter_name()`
# @used-by :func:`platform_enabled()`
# @used-by :func:`platform_homes()`
# @used-by :func:`platform_instances()`
# @used-by :func:`platform_key_for_adapter()`
# @used-by :func:`platform_name()`
# @used-by :func:`platform_settings()`
# @used-by :func:`profile_name()`
# @used-by :func:`registration_profile_name()`
# @used-by :func:`request_day()`
# @used-by :func:`resolve_antigravity_backend()`
# @used-by :func:`resolve_antigravity_paths()`
# @used-by :func:`resolve_codex_home()`
# @used-by :func:`resolve_codex_paths()`
# @used-by :func:`role_settings()`
# @used-by :func:`using()`
# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.__configured_tz()`
# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__configured_tz()`
# @used-by :meth:`Df.Harness.Meta.ProjectIdentity.ProjectIdentity.resolve_ag_paths_safe()`
# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__init__()`
# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.resolve_project()`
# @used-by :meth:`Df.Harness.Project.Registry.Registry.__init__()`
# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__sync_registrations()`
# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.update_projects_index()`
# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.__init__()`
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.collect()`
# @used-by :meth:`Df.Harness.Text.Browser.CdpSession.CdpSession.__init__()`
# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__init__()`
# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.collect()`
# @used-by :meth:`Df.Harness.Text.Browser.HeadlessShell.HeadlessShell.__init__()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__init__()`
# @used-by :meth:`Df.Harness.Text.DiagnosticsScanner.DiagnosticsScanner.__init__()`
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.main()`
# @used-by :meth:`Df.Harness.Upwork.ConfigurationChecker.ConfigurationChecker.__init__()`
# @used-by :meth:`Df.Harness.Upwork.DoctorAuditor.DoctorAuditor.__init__()`
# @used-by :meth:`Df.Harness.Upwork.GlobalCustomizationManager.GlobalCustomizationManager.antigravity_global_config_dirs()`
# @used-by :meth:`Df.Harness.Upwork.InstancesReporter.InstancesReporter.__init__()`
# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.extract()`
# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__init__()`
# @used-by :meth:`Df.Harness.Upwork.ProjectDirResolver.ProjectDirResolver.resolve_or_create()`
# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.initialize()`
# @used-by :meth:`Df.Harness.Workflow.RegistrationStatusChecker.RegistrationStatusChecker.status()`
# @used-by :meth:`test_addons_profile_adapter.AddonsProfileAdapterTests.test_copied_materialized_config_stays_isolated_from_live_profiles()`
# @used-by :meth:`test_addons_profile_adapter.AddonsProfileAdapterTests.test_escapes_template_literals_and_rejects_traversal_and_symlinks()`
# @used-by :meth:`test_addons_profile_adapter.AddonsProfileAdapterTests.test_live_runtime_uses_addons_profiles_json_source_and_paths_registers_profile_manager_tests()`
# @used-by :meth:`test_addons_profile_adapter.AddonsProfileAdapterTests.test_projects_addons_profiles_with_overrides_and_env_expansion()`
# @used-by :meth:`test_addons_profile_adapter.AddonsProfileAdapterTests.test_rejects_conflicts_malformed_schema_and_unknown_overrides()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_native_profiles_generates_arch_auditor_for_antigravity_and_codex()`
# @used-by :meth:`test_cleanup.CleanupTests.setUp()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.setUp()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.setUp()`
# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests.setUp()`
# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests._build_fixture()`
# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests._make_primary()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.setUp()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_live_runtime_declares_environments_instances_enabled_states_and_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_runtime_validation_rejects_invalid_instances_and_dual_homes()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.setUp()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
# @used-by :meth:`test_portability.ProjectionTests.test_global_instructions_are_read_safely_and_local_override_keeps_its_priority()`
# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_cleanup_integration()`
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.setUp()`
# @used-by :meth:`test_registration_portability.RegistrationTests.setUp()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_runtime_settings_cache_invalidates_on_file_or_env_change_and_isolates_mutations()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m2a_extension_manifest_key_and_multi_profile_tab_broker_isolation()`
# @used-by :mod:`agent_tools.configuration`
# @used-by :mod:`agent_tools.intake`
# @used-by :mod:`agent_tools.native_profiles`
# @used-by :mod:`agent_tools.platforms.antigravity`
# @used-by :mod:`agent_tools.registration`
# @used-by :mod:`agent_tools.runtime`
# @used-by :mod:`agent_tools.upwork_project`
def settings(path=None):
	return SettingsLoader(path, default_file_fn=default_runtime_file, primary=PRIMARY, code_anchor=_CODE_ANCHOR, registry_file=DEFAULT_REGISTRY_FILE).run()
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.main()`
# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_discovery_failure_with_conversations_is_preserved_without_an_issue()`
# @used-by :meth:`test_cleanup.CleanupTests.test_preview_is_read_only_and_apply_cleans_both_platforms_preserving_entire_archive()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_native_workspace_supports_self_review_and_empty_metadata_keeps_legacy_job_id()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.selected()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_future_environment_claude_code_is_supported_without_roles_or_adapters()`
# @used-by :meth:`test_portability.CodexEvidenceTests.selected()`
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.test_registration_only_fallback_does_not_relax_native_evidence_profile()`
# @used-by :mod:`agent_tools.upwork_project`
def using(platform=None, profile=None, instance=None):
	return dfh_using(platform=platform, profile=profile, instance=instance, settings_fn=settings)
_UNPATCHED_SETTINGS = settings
