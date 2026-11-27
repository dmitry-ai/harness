# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.LabelValidator import LabelValidator
from Df.Harness.Project.RegistrationStore import RegistrationStore
from Df.Harness.Project.Registry import Registry
from Df.Harness.Upwork.CliRunner import CliRunner
from Df.Harness.Upwork.ConfigurationChecker import ConfigurationChecker
from Df.Harness.Upwork.DoctorAuditor import DoctorAuditor
from Df.Harness.Upwork.GlobalCustomizationManager import GlobalCustomizationManager
from Df.Harness.Upwork.InstancesReporter import InstancesReporter
from Df.Harness.Upwork.ProjectConfigurator import ProjectConfigurator
from Df.Harness.Upwork.ProjectDirResolver import ProjectDirResolver
from Df.Harness.Upwork.ProjectInitializer import ProjectInitializer
from pathlib import Path
from .platforms.antigravity import ANTIGRAVITY_FOLDERS_JSON, ANTIGRAVITY_PROJECTS_DIR, register as register_antigravity_default, register_antigravity_project
from .runtime import HARNESS_META, PRIMARY as PRIMARY_AGENTS_DIR, all_instances, extract_platform_instances, find_conversation_instance, instance_entry, platform_active, platform_homes, platform_instances, platform_name, platform_settings, request_day, role_settings, settings, using
from .upwork_data import normalize_job_id
from .upwork_extract import attachment_path, extract_upwork_job
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
WORKSPACE_ROOT = Path(settings()['workspace_root']).resolve()
DAILY_PROPOSALS_ROOT = WORKSPACE_ROOT / settings()['daily_root']
GLOBAL_KINDS = GlobalCustomizationManager.GLOBAL_KINDS
HOOK_RUNNER_HEADER = GlobalCustomizationManager.HOOK_RUNNER_HEADER
UNDECLARED_ANTIGRAVITY_HOME = GlobalCustomizationManager.UNDECLARED_ANTIGRAVITY_HOME
# @used-by :mod:`agent_tools.upwork_project`
def _has_entry(entries, target):
	return GlobalCustomizationManager.has_entry(entries, target)
# @used-by :mod:`agent_tools.upwork_project`
def _install_profile_customizations(config, primary=PRIMARY_AGENTS_DIR):
	return GlobalCustomizationManager.install_profile_customizations(config, primary)
# @used-by :func:`check_global_customizations()`
# @used-by :func:`install_global_customizations()`
# @used-by :meth:`test_onboarding.RegistrationTests.test_undeclared_current_antigravity_home_is_reported()`
# @used-by :mod:`agent_tools.upwork_project`
def antigravity_global_config_dirs():
	return GlobalCustomizationManager.antigravity_global_config_dirs(settings_fn=settings)
# @used-by :func:`Df.Harness.lib.native_ag_plan._merge_ag_hooks()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._populate_ag_shared_outputs()`
# @used-by :meth:`test_ask_question_pre_tool_gate.AskQuestionPreToolGateTests.test_hooks_manifest_and_canonical_hooks_include_ask_question()`
# @used-by :meth:`test_failfast_and_schedule_gate.FailFastAndScheduleGateTests.test_hooks_manifest_and_canonical_hooks_match_schedule()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_build_native_publishes_shared_hooks_and_upgrades_stop_only_final_turn_gate()`
# @used-by :meth:`test_onboarding.RegistrationTests.test_global_install_repairs_profile_without_rules_and_merges_missing_hooks()`
# @used-by :mod:`agent_tools.upwork_project`
def canonical_global_hooks(primary=PRIMARY_AGENTS_DIR, *, config_dir: str | Path | None=None):
	return GlobalCustomizationManager.canonical_global_hooks(primary, config_dir=config_dir)
# @used-by :func:`run()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_portability.ProjectionTests.test_extra_rule_sources_are_projected_and_unsupported_selectors_reported()`
# @used-by :meth:`test_portability.ProjectionTests.test_project_rules_feed_both_systems_and_detect_stale_codex_projection()`
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
def check_configuration(project_root, primary_agents_dir=PRIMARY_AGENTS_DIR):
	return ConfigurationChecker(project_root, primary_agents_dir, settings_fn=settings).check()
# @used-by :func:`doctor()`
# @used-by :func:`install_global_customizations()`
# @used-by :meth:`test_onboarding.RegistrationTests.test_global_install_repairs_profile_without_rules_and_merges_missing_hooks()`
# @used-by :mod:`agent_tools.upwork_project`
def check_global_customizations(config_dirs=None, primary=PRIMARY_AGENTS_DIR, *, git_ignore_path=None):
	return GlobalCustomizationManager.check_global(config_dirs, primary, git_ignore_path=git_ignore_path, dirs_fn=antigravity_global_config_dirs)
# @used-by :func:`initialize_upwork_project()`
# @used-by :func:`run()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
# @used-by :meth:`test_onboarding.InitializationTests.test_existing_neighbor_material_is_untouched()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_known_old_context_is_upgraded_with_a_preserved_original()`
# @used-by :meth:`test_portability.ProjectionTests.test_extra_rule_sources_are_projected_and_unsupported_selectors_reported()`
# @used-by :meth:`test_portability.ProjectionTests.test_global_instructions_are_read_safely_and_local_override_keeps_its_priority()`
# @used-by :meth:`test_portability.ProjectionTests.test_project_rules_feed_both_systems_and_detect_stale_codex_projection()`
# @used-by :meth:`test_portability.ProjectionTests.test_project_setup_merges_native_entries_and_preserves_custom_context()`
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
def configure_project(project_root, primary_agents_dir=PRIMARY_AGENTS_DIR, job_url=None, domain_or_topic=None, *, platform=None):
	return ProjectConfigurator(project_root, primary_agents_dir, job_url, domain_or_topic, platform=platform, settings_fn=settings).configure()
# @used-by :meth:`test_portability.CodexEvidenceTests.test_known_old_context_is_upgraded_with_a_preserved_original()`
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
def default_context_config(root: Path | None=None):
	return ProjectConfigurator.default_context_config(root)
# @used-by :func:`run()`
# @used-by :meth:`test_arch_rules_contract.ArchRulesContractTests.test_architecture_rule_is_compact_always_on_and_passes_doctor_and_rules_audit()`
# @used-by :meth:`test_code_formatting_rules.CodeFormattingRulesContractTests.test_general_rule_passes_doctor_native_bootstrap_and_lint()`
# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests.test_doctor_reports_and_validates_global_git_ignore()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_all_disabled_and_claude_code_only_environment_without_antigravity_or_codex()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_future_environment_claude_code_is_supported_without_roles_or_adapters()`
# @used-by :meth:`test_rules_architecture_m2.RulesArchitectureM2Tests.test_always_on_budget_and_three_layer_partition()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_cli_rules_audit_and_semantic_brief_and_live_harness_green()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_doctor_and_rules_audit_default_to_active_checkout_rules()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_pre_tool_use_rules_budget_and_doctor_and_pre_commit_enforce_limits()`
# @used-by :meth:`test_rules_progressive_disclosure.RulesProgressiveDisclosureTests.test_doctor_accepts_model_decision_and_reports_trigger_metrics()`
# @used-by :meth:`test_rules_progressive_disclosure.RulesProgressiveDisclosureTests.test_doctor_rejects_invalid_trigger_or_undescribed_model_decision()`
# @used-by :meth:`test_tdd_rules_contract.TddRulesAndDocumentationContractTests.test_cli_help_and_doctor_expose_tdd_commands()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_doctor_and_turn_begin_exclude_addons_health()`
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
def doctor(primary=None, *, git_ignore_path=None):
	return DoctorAuditor(primary, git_ignore_path=git_ignore_path, settings_fn=settings, platform_settings_fn=platform_settings, check_global_fn=check_global_customizations).audit()
# @used-by :mod:`agent_tools.upwork_project`
def harness_hook_runner_source(primary=PRIMARY_AGENTS_DIR, *, store_dir=None) -> str:
	return GlobalCustomizationManager.harness_hook_runner_source(primary, store_dir=store_dir)
# @used-by :func:`run()`
# @used-by :func:`test_atomic_prepare_and_narrowed_reconcile_m7._init_review_ready_project()`
# @used-by :func:`test_contract_invariants._init_tracked_project()`
# @used-by :func:`test_finalized_project_contract.seed_finalized_upwork_project()`
# @used-by :func:`test_journal_integrity._init_domain()`
# @used-by :func:`test_project_rename._init_provisional()`
# @used-by :func:`test_project_rename_verification._seed_proposals_layout()`
# @used-by :meth:`test_analysis_workflow.MetricsTests.test_collect_http_positional_batch_extract_profile_and_14_url_evidence_query()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.setUp()`
# @used-by :meth:`test_cleanup.CleanupTests.test_init_persists_creation_time_and_repeat_never_resets_it()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests._init_and_register()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_instance_flag_and_codex_auto_lookup_for_handoff_and_audit()`
# @used-by :meth:`test_onboarding.AttachmentTests.test_docx_and_text_attachments_saved_in_source_and_both_kbs()`
# @used-by :meth:`test_onboarding.CapturedProjectTests.test_real_captures_preserve_description_port_and_curated_work()`
# @used-by :meth:`test_onboarding.InitializationTests.init()`
# @used-by :meth:`test_onboarding.InitializationTests.test_invalid_names_dates_and_capture_do_not_create_projects()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_second_platform_keeps_original_date_root_manual_kb_and_saved_snapshot()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_creation_publishes_supplied_site_and_reinit_keeps_the_card()`
# @used-by :meth:`test_registration_portability.RegistrationTests.setUp()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_registered_empty_launcher_project_tracks_pre_init_failures_and_hands_off_to_daily_project()`
# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_new_v2_upwork_project_creates_dot_md_not_readme()`
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
def initialize_upwork_project(url_or_id, domain_or_topic=None, date_str=None, daily_root=DAILY_PROPOSALS_ROOT, primary_agents_dir=PRIMARY_AGENTS_DIR, extracted_data=None, register_antigravity=None, antigravity_projects_dir=None, antigravity_folders_json=None, site_hypothesis=None, platform=None, register_native=None, all_platforms=None, launcher_root=None, conversation_id=None, topic=None):
	from . import knowledge
	return ProjectInitializer(url_or_id, domain_or_topic, date_str, daily_root, primary_agents_dir, extracted_data, register_antigravity, antigravity_projects_dir, antigravity_folders_json, site_hypothesis, platform, register_native, all_platforms, launcher_root, conversation_id, topic, default_daily_root=DAILY_PROPOSALS_ROOT, platform_settings_fn=platform_settings, configure_fn=configure_project, resolve_dir_fn=resolve_or_create_project_dir, register_ag_fn=register_antigravity_default, extra_sources_fn=knowledge.build_project_extra_sources).initialize()
# @used-by :meth:`test_onboarding.RegistrationTests.test_global_install_preserves_other_customizations_and_is_idempotent()`
# @used-by :meth:`test_onboarding.RegistrationTests.test_global_install_repairs_profile_without_rules_and_merges_missing_hooks()`
# @used-by :meth:`test_onboarding.RegistrationTests.test_undeclared_current_antigravity_home_is_reported()`
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
def install_global_customizations(config_dir=None, primary=PRIMARY_AGENTS_DIR):
	return GlobalCustomizationManager.install_global(config_dir, primary, dirs_fn=antigravity_global_config_dirs, check_fn=check_global_customizations)
# @used-by :func:`run()`
# @used-by :mod:`agent_tools.upwork_project`
def instances_report(*, platform=None, instance=None, conversation=None, include_disabled=True, check_exists=True):
	return InstancesReporter(platform=platform, instance=instance, conversation=conversation, include_disabled=include_disabled, check_exists=check_exists, settings_fn=settings).report()
# @used-by :func:`Df.Harness.lib.native_ag_plan._merge_ag_hooks()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_v2_unicode_primary_generates_ascii_hook_runner_upgrades_legacy_hooks_and_runs_via_cmd_exe()`
# @used-by :mod:`agent_tools.upwork_project`
def legacy_direct_global_hooks(primary=PRIMARY_AGENTS_DIR):
	return GlobalCustomizationManager.legacy_direct_global_hooks(primary)
# @used-by :func:`Df.Harness.lib.native_ag_plan._merge_ag_hooks()`
# @used-by :meth:`test_failfast_and_schedule_gate.FailFastAndScheduleGateTests.test_hooks_manifest_and_canonical_hooks_match_schedule()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_build_native_publishes_shared_hooks_and_upgrades_stop_only_final_turn_gate()`
# @used-by :mod:`agent_tools.upwork_project`
def legacy_runner_global_hooks(primary=PRIMARY_AGENTS_DIR):
	return GlobalCustomizationManager.legacy_runner_global_hooks(primary)
# @used-by :func:`git_fixture_cache.run_harness_inprocess()`
# @used-by :meth:`test_analysis_workflow.MetricsTests.test_collect_http_positional_batch_extract_profile_and_14_url_evidence_query()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_cli_logs_actual_stdin_answer_from_either_platform_without_running_cleanup()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_cleanup_report_isolates_conflicting_host_a0_and_codex_env()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_cleanup_report_writes_metadata_header_links_manifest_and_consumes_scratch_file()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.test_apply_and_cleanup_report_manifest_and_metadata_roundtrip()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_declarative_arg_specs_and_routers_parse_expected_flags()`
# @used-by :meth:`test_cli_registry.CliRegistryTests.test_cli_docs_renders_registered_commands_and_runs_via_cli()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cli_instances_and_metrics_commands()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_instance_flag_and_codex_auto_lookup_for_handoff_and_audit()`
# @used-by :meth:`test_intake.IntakeTests.test_cli_dry_run_then_apply_and_managed_init_integration()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_cli_land_acquire_status_release()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_parallel_runner_passes_all_modules_via_cli()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_answer_prepare_cli_reports_retryable_false_fast_and_true_on_transient_timeout()`
# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_wait_repo_cli_and_registry_expose_wait_repo()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_collection_cli_signals_unavailable_content_with_saved_diagnostics()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_malformed_evidence_fields_return_diagnostics_without_crashing()`
# @used-by :meth:`test_review_contract.ReviewContractTests.cli()`
# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_automatic_journal_only_upgrade_and_cli_subcommand()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_cli_worktree_begin_status_cleanup()`
# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_cli_worktree_land_default_removes_and_keep_preserves()`
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
# @used-by :mod:`harness`
# @used-by :mod:`upwork_project`
def main(argv=None):
	return CliRunner.main(argv, settings_fn=settings, daily_root=DAILY_PROPOSALS_ROOT, run_fn=run, description=__doc__)
# @used-by :func:`run()`
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
def register_project(project, label=None, day=None, *, platform=None):
	return Registry(project, label, day, settings_fn=settings).register(platform=platform, single=True)
# @used-by :func:`initialize_upwork_project()`
# @used-by :meth:`test_onboarding.InitializationTests.test_concurrent_numbers_and_same_job_are_exclusive()`
# @used-by :meth:`test_onboarding.InitializationTests.test_invalid_names_dates_and_capture_do_not_create_projects()`
# @used-by :meth:`test_onboarding.InitializationTests.test_registry_is_stable_across_dates_and_labels()`
# @used-by :meth:`test_onboarding.InitializationTests.test_resolve_or_create_reuses_unindexed_v2_project_dir()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_receipt_verifier_and_dir_resolver_support_dot_md_and_readme_bidirectional()`
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
def resolve_or_create_project_dir(job_id, domain_or_topic, date_str=None, daily_root=DAILY_PROPOSALS_ROOT):
	return ProjectDirResolver(job_id, domain_or_topic, date_str, daily_root, default_daily_root=DAILY_PROPOSALS_ROOT).resolve_or_create()
# @used-by :func:`main()`
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
def run(args):
	from . import intake
	return CliRunner(args, doctor_fn=doctor, configure_fn=configure_project, check_cfg_fn=check_configuration, init_fn=initialize_upwork_project, extract_fn=extract_upwork_job, instances_fn=instances_report, register_fn=register_project, platform_settings_fn=platform_settings, incoming_fn=lambda: intake.INCOMING, commit_capture_fn=intake.commit_capture, drain_incoming_fn=intake.drain_incoming).run()
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
def save_registration(root, platform, result):
	return RegistrationStore(root, platform, result).save()
# @used-by :meth:`test_project_labels.ProjectLabelValidationTests.test_validate_label_and_helpers_enforce_slug_and_domain_rules()`
# @used-by :mod:`agent_tools.harness_cli`
# @used-by :mod:`agent_tools.upwork_project`
def validate_label(value):
	return LabelValidator(value).validate(kind='safe')
__all__ = ['ANTIGRAVITY_FOLDERS_JSON', 'ANTIGRAVITY_PROJECTS_DIR', 'DAILY_PROPOSALS_ROOT', 'GLOBAL_KINDS', 'HARNESS_META', 'HOOK_RUNNER_HEADER', 'PRIMARY_AGENTS_DIR', 'UNDECLARED_ANTIGRAVITY_HOME', 'WORKSPACE_ROOT', '_has_entry', '_install_profile_customizations', 'all_instances', 'antigravity_global_config_dirs', 'attachment_path', 'canonical_global_hooks', 'check_configuration', 'check_global_customizations', 'configure_project', 'default_context_config', 'doctor', 'extract_platform_instances', 'extract_upwork_job', 'find_conversation_instance', 'harness_hook_runner_source', 'initialize_upwork_project', 'install_global_customizations', 'instance_entry', 'instances_report', 'legacy_direct_global_hooks', 'legacy_runner_global_hooks', 'main', 'platform_active', 'platform_homes', 'platform_instances', 'platform_name', 'platform_settings', 'register_antigravity_default', 'register_antigravity_project', 'register_project', 'request_day', 'resolve_or_create_project_dir', 'role_settings', 'run', 'save_registration', 'settings', 'using', 'validate_label']
if '__main__' == __name__:
	raise SystemExit(main())
