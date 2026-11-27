# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Meta.TimestampFormatter import TimestampFormatter
import json
import tempfile
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class ProjectIdentity:
	PROJECTS_DIR_CACHE: dict[tuple[str, int], list[dict[str, Any]]] = {}
	# @used-by :func:`agent_tools.meta.identity.resolve_project_identity()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :mod:`Df.Harness.Meta.Builders`
	def __init__(self, root: str | Path, *, ag_paths: dict[str, Any] | None=None, project_id: str | None=None) -> None:
		self.__root = root
		self.__ag_paths = ag_paths
		self.__project_id = project_id
	# @used-by :func:`agent_tools.analysis.publish_analysis()`
	# @used-by :func:`agent_tools.cleanup.candidates()`
	# @used-by :func:`agent_tools.cleanup.legacy_initialization()`
	# @used-by :func:`agent_tools.cleanup.remove_antigravity()`
	# @used-by :func:`agent_tools.cleanup.restore_antigravity()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._disabled_codex_history()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._launcher_turn_dirs()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._probe_disabled_ag_db()`
	# @used-by :func:`agent_tools.completion._build_compaction_file_index()`
	# @used-by :func:`agent_tools.completion._find_evicted_cited_files()`
	# @used-by :func:`agent_tools.completion._instruction_snapshot()`
	# @used-by :func:`agent_tools.completion._response_link_issues()`
	# @used-by :func:`agent_tools.configuration._project_rule_paths()`
	# @used-by :func:`agent_tools.configuration._publish()`
	# @used-by :func:`agent_tools.configuration.build_native()`
	# @used-by :func:`agent_tools.configuration.configure_codex_project()`
	# @used-by :func:`agent_tools.configuration.resolve_manifest_entry()`
	# @used-by :func:`agent_tools.context._inside_allowed()`
	# @used-by :func:`agent_tools.context.assemble()`
	# @used-by :func:`agent_tools.context.generate()`
	# @used-by :func:`agent_tools.context.inside()`
	# @used-by :func:`agent_tools.evidence.local_file()`
	# @used-by :func:`agent_tools.evidence.source_reference()`
	# @used-by :func:`agent_tools.evidence_loader._resolve_html_data()`
	# @used-by :func:`agent_tools.git_ignore._detect_enclosing_repo()`
	# @used-by :func:`agent_tools.git_ignore.prepare_worktrees_base_dir()`
	# @used-by :func:`agent_tools.git_ignore.resolve_global_git_ignore_path()`
	# @used-by :func:`agent_tools.grounding_domains.extract_fact_tuples()`
	# @used-by :func:`agent_tools.intake._project()`
	# @used-by :func:`agent_tools.issue_first_gate.build_code_write_issue_first_event()`
	# @used-by :func:`agent_tools.issue_first_gate.evaluate_pre_tool_use_issue_first()`
	# @used-by :func:`agent_tools.issue_first_gate.resolve_issue_first_target()`
	# @used-by :func:`agent_tools.issue_first_inherit._find_parent_from_summary_db()`
	# @used-by :func:`agent_tools.issue_first_inherit._turns_and_evidence_dirs()`
	# @used-by :func:`agent_tools.issues.batch_commands._resolve_optional_path()`
	# @used-by :func:`agent_tools.issues.git_read_cache._read_ref_oid()`
	# @used-by :func:`agent_tools.issues.git_read_cache._resolve_git_dir()`
	# @used-by :func:`agent_tools.issues.parity._peer_code_repo_candidates()`
	# @used-by :func:`agent_tools.issues.parity.check_similar_project_parity()`
	# @used-by :func:`agent_tools.issues.repo_locator._collect_local_repo_candidates()`
	# @used-by :func:`agent_tools.issues.repo_locator._is_under_tempdir()`
	# @used-by :func:`agent_tools.issues.repo_locator._register_repo_slugs()`
	# @used-by :func:`agent_tools.issues.turn_scope._candidate_turns_dirs()`
	# @used-by :func:`agent_tools.journal._migrate_journal_state_dir()`
	# @used-by :func:`agent_tools.journal._raw_state_dir()`
	# @used-by :func:`agent_tools.journal._sync_overlay_journal_slot()`
	# @used-by :func:`agent_tools.journal._unit_needs_upgrade()`
	# @used-by :func:`agent_tools.journal.canonicalize_journal_dir_identity()`
	# @used-by :func:`agent_tools.journal.ensure_project_journal_upgraded()`
	# @used-by :func:`agent_tools.journal.get_existing_step_ids()`
	# @used-by :func:`agent_tools.journal.journal_pair_names()`
	# @used-by :func:`agent_tools.journal.resolve_journal_dir()`
	# @used-by :func:`agent_tools.journal.resolve_migrated_step_file()`
	# @used-by :func:`agent_tools.journal.upgrade_journal()`
	# @used-by :func:`agent_tools.links.validate_file()`
	# @used-by :func:`agent_tools.meta.identity.resolve_project_identity()`
	# @used-by :func:`agent_tools.native_profiles._codex_plan()`
	# @used-by :func:`agent_tools.native_profiles._role_config()`
	# @used-by :func:`agent_tools.native_profiles.retire_owned_project_projections()`
	# @used-by :func:`agent_tools.operations._execute_collect()`
	# @used-by :func:`agent_tools.path_cache._linked_worktree_main_repo()`
	# @used-by :func:`agent_tools.path_cache.default_runtime_file()`
	# @used-by :func:`agent_tools.path_cache.get_ttl_overlay_links()`
	# @used-by :func:`agent_tools.path_cache.is_under_tempdir()`
	# @used-by :func:`agent_tools.path_cache.mark_overlay_links_refreshed()`
	# @used-by :func:`agent_tools.path_cache.resolve_reverse_map()`
	# @used-by :func:`agent_tools.path_registry._candidate_discovery_roots()`
	# @used-by :func:`agent_tools.path_registry._infer_harness_anchor()`
	# @used-by :func:`agent_tools.path_registry.canonicalize_root_dir()`
	# @used-by :func:`agent_tools.path_registry.discover_overlay_file()`
	# @used-by :func:`agent_tools.path_registry.load_registry()`
	# @used-by :func:`agent_tools.path_registry.paths_report()`
	# @used-by :func:`agent_tools.path_registry.resolve_project_root()`
	# @used-by :func:`agent_tools.platforms.trace_common.open_readonly_sqlite()`
	# @used-by :func:`agent_tools.platforms.trace_common.partial_candidate_read_issues()`
	# @used-by :func:`agent_tools.platforms.trace_common.record_canonical_path()`
	# @used-by :func:`agent_tools.polyglot_land._execute_polyglot_spec()`
	# @used-by :func:`agent_tools.project_card.sync_block()`
	# @used-by :func:`agent_tools.project_rename._infer_daily_root()`
	# @used-by :func:`agent_tools.project_rename._sync_registrations()`
	# @used-by :func:`agent_tools.project_rename._update_projects_index()`
	# @used-by :func:`agent_tools.project_rename_state.migrate_journal_state()`
	# @used-by :func:`agent_tools.project_rename_verify.infer_launcher_root()`
	# @used-by :func:`agent_tools.repo_tags._find_git_root()`
	# @used-by :func:`agent_tools.repo_wait._map_touched_path_to_repo()`
	# @used-by :func:`agent_tools.research.evidence_query()`
	# @used-by :func:`agent_tools.research.extract_file()`
	# @used-by :func:`agent_tools.research.extract_observation()`
	# @used-by :func:`agent_tools.research.inside()`
	# @used-by :func:`agent_tools.research.load_observation()`
	# @used-by :func:`agent_tools.runtime._antigravity_backend_has_conversation()`
	# @used-by :func:`agent_tools.runtime._codex_home_conversation_trace()`
	# @used-by :func:`agent_tools.runtime.resolve_antigravity_paths()`
	# @used-by :func:`agent_tools.runtime_snapshot._safe_extract_tar()`
	# @used-by :func:`agent_tools.runtime_snapshot._set_local_hooks_path()`
	# @used-by :func:`agent_tools.runtime_snapshot.effective_git_hooks_dir()`
	# @used-by :func:`agent_tools.runtime_snapshot.runtime_store_dir()`
	# @used-by :func:`agent_tools.shadow_replay._execute_finalize_reply()`
	# @used-by :func:`agent_tools.shadow_replay_command.persist_shadow_replay_receipt()`
	# @used-by :func:`agent_tools.source_grounding._infer_source_root()`
	# @used-by :func:`agent_tools.source_grounding.resolve_local_href()`
	# @used-by :func:`agent_tools.stop_subagent_check._query_summary_children()`
	# @used-by :func:`agent_tools.storage._should_skip_fsync()`
	# @used-by :func:`agent_tools.text_browser.resolve_headless_shell()`
	# @used-by :func:`agent_tools.text_claims.registry_path()`
	# @used-by :func:`agent_tools.text_cli.main()`
	# @used-by :func:`agent_tools.text_core.check_response()`
	# @used-by :func:`agent_tools.text_core.find_bans()`
	# @used-by :func:`agent_tools.text_workflow.gate_paths()`
	# @used-by :func:`agent_tools.trace_event_cache.load_transcript_rows_cached()`
	# @used-by :func:`agent_tools.turn_routing._extract_step_text_from_db()`
	# @used-by :func:`agent_tools.upwork_extract.attachment_path()`
	# @used-by :func:`agent_tools.upwork_project.antigravity_global_config_dirs()`
	# @used-by :func:`agent_tools.upwork_project.check_configuration()`
	# @used-by :func:`agent_tools.upwork_project.configure_project()`
	# @used-by :func:`agent_tools.upwork_project.doctor()`
	# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
	# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
	# @used-by :func:`agent_tools.upwork_project.run()`
	# @used-by :func:`agent_tools.workflow.evidence_paths()`
	# @used-by :func:`agent_tools.worktree_flow._enrich_worktree_entry()`
	# @used-by :func:`agent_tools.worktree_flow._resolve_deleted_worktree_file()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_begin()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_status()`
	# @used-by :func:`check_markdown_slop._infer_project_root()`
	# @used-by :func:`check_pre_invocation._expected_turn_key()`
	# @used-by :func:`check_pre_invocation._has_planner_steps()`
	# @used-by :func:`check_pre_invocation._latest_completed_user_step()`
	# @used-by :func:`check_pre_invocation._pre_flush_begin_context()`
	# @used-by :func:`check_pre_invocation._resolve_ag_paths()`
	# @used-by :func:`check_pre_invocation._summary_primary_status()`
	# @used-by :func:`check_stop_gate._is_child_conversation()`
	# @used-by :func:`check_stop_gate._resolve_stop_paths()`
	# @used-by :func:`git_shim.resolve_system_git()`
	# @used-by :func:`test_contract_invariants._run_parity_defect_case()`
	# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
	# @used-by :func:`test_hook_lazy_imports._run_probe()`
	# @used-by :func:`test_incomplete_scope_regression_matrix._build_ag_turn()`
	# @used-by :func:`test_journal_clarifications_and_disclosure._setup_ag_turn_with_clarifications()`
	# @used-by :func:`test_project_domain_drift._complete_review_and_prepare()`
	# @used-by :func:`test_repo_locator_perf._make_git_config()`
	# @used-by :func:`test_runtime_cache_and_evidence_fastpath_m9._write_minimal_v3_project()`
	# @used-by :func:`test_stop_emergency_capture_and_foreign_sync._seed_ag_conversation()`
	# @used-by :func:`test_upwork_init_e2e._run_turn1_init_and_review()`
	# @used-by :func:`test_upwork_init_e2e._run_turn2_continuation()`
	# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.__load_declared_participants()`
	# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.__resolve_pre_tool_target()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__load_verified_package()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.read_review_input()`
	# @used-by :meth:`Df.Harness.Gate.CdpBypassGate.CdpBypassGate.is_inside_harness_code()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeAnalyzer.CodeSizeAnalyzer.resolve_python_target()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentScanner.IssueCommentScanner.resolve_target()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.enclosing_github_repo()`
	# @used-by :meth:`Df.Harness.Gate.RulesAuditor.RulesAuditor.__load_rule_entries()`
	# @used-by :meth:`Df.Harness.Gate.RulesAuditor.RulesAuditor.__prospective_always_on_totals()`
	# @used-by :meth:`Df.Harness.Gate.RulesAuditor.RulesAuditor.__read_staged_overrides()`
	# @used-by :meth:`Df.Harness.Gate.WorktreeIsolationGate.WorktreeIsolationGate.__resolve_target_path()`
	# @used-by :meth:`Df.Harness.Gate.XrefChecker.XrefChecker.resolve_target()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.__resolve_optional_path()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.build_trace()`
	# @used-by :meth:`Df.Harness.Meta.TranscriptReader.TranscriptReader.__turn_state_candidate()`
	# @used-by :meth:`Df.Harness.Meta.TranscriptReader.TranscriptReader.ag_transcript_file()`
	# @used-by :meth:`Df.Harness.Perf.SuiteWorker.SuiteWorker.__discover_suite()`
	# @used-by :meth:`Df.Harness.Tdd.CodeClassifier.CodeClassifier.__resolve_deleted_worktree_scope()`
	# @used-by :meth:`Df.Harness.Tdd.CodeClassifier.CodeClassifier.resolve_code_scope()`
	# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.__resolve_shell_target()`
	# @used-by :meth:`Df.Harness.Tdd.DiffCoverage.DiffCoverage.__changed_test_paths()`
	# @used-by :meth:`Df.Harness.Tdd.DiffCoverage.DiffCoverage.__touched_git_repos()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_write()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__resolve_worktree_git_dirs()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__resolve_event_target_scopes()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.git_main_repo_root()`
	# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.build_file_write_event()`
	# @used-by :meth:`Df.Harness.Tdd.Exemption.Exemption.__resolve_scope_rel_path()`
	# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.__resolve_existing_repo()`
	# @used-by :meth:`Df.Harness.Tdd.WorktreeScope.WorktreeScope.__norm_lower()`
	# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.__resolve_tests_dir()`
	# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.discover_modules()`
	# @used-by :meth:`ProjectIdentity.__push_project_dir()`
	# @used-by :meth:`ProjectIdentity.is_temp_path()`
	# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
	# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner._inspect_unresolved()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.main_repo()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.normalize_paths()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.run_hook()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_write_invocation()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._bind_issue_repos()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._collect_repos_and_issues()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._collect_touched_repos()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.evidence_issue_files()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.find_tracked_child_issues()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.issue_target_for_path()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.meta_dir_for_project_root()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.resolve_issue_targets()`
	# @used-by :meth:`agent_tools.path_registry.PathRegistry.__init__()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._check_local_grounding()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._ingest_evidence_files()`
	# @used-by :meth:`agent_tools.review.ReviewReportValidator._check_disproved_claim()`
	# @used-by :meth:`agent_tools.shell_audit.ShellCommandInspector.scan_git_global_opts()`
	# @used-by :meth:`agent_tools.source_grounding.LocalSourceGroundingAuditor.__init__()`
	# @used-by :meth:`agent_tools.source_grounding.LocalSourceGroundingAuditor._check_tier2_sole_evidence()`
	# @used-by :meth:`agent_tools.source_grounding.LocalSourceGroundingAuditor._load_ledger_tuples()`
	# @used-by :meth:`agent_tools.source_grounding.LocalSourceGroundingAuditor._resolve_block_sources()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex._candidate_files()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex._stat_and_read()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.load_source_info()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.locator_for()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._discover_references()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_ancestry_scope()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.__init__()`
	# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor.check_project()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.status()`
	# @used-by :meth:`test_agent_tools.ContextTests.test_default_context_config_includes_agent_kb_and_excludes_evidence_subfolder()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_check_detects_missing_guidance_without_writing_and_build_repairs_it()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_edit_to_generated_guidance_blocks_other_pending_configuration_updates()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_guidance_uses_current_canonical_loader_without_copying_rule_bodies()`
	# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_chat_reply_link_issues_allows_unencoded_file_uri_and_rejects_encoded()`
	# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_completion_and_grounding_match_chat_reply_link_policy()`
	# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
	# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_apply_persists_sidecar_manifest_with_rollback_snapshots_while_dry_run_stays_readonly()`
	# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_cleanup_report_writes_metadata_header_links_manifest_and_consumes_scratch_file()`
	# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.test_apply_and_cleanup_report_manifest_and_metadata_roundtrip()`
	# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests.test_delayed_finalize_and_recent_rename_extend_effective_activity_window()`
	# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests.test_disabled_codex_and_antigravity_history_dbs_preserve_projects_without_mutating()`
	# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests.test_post_init_deliverables_and_multi_turn_work_preserve_while_single_init_is_cleaned()`
	# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests.test_renamed_from_paths_preserve_projects_with_old_path_conversations()`
	# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_parallel_deleted_worktrees_isolate_tdd_scopes_and_accept_main_full_green()`
	# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests.test_doctor_reports_and_validates_global_git_ignore()`
	# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests.test_resolve_global_git_ignore_path_precedence()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_proof_evidence_review_document_and_journal_changes_remain_conflicts()`
	# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_in_process_cache_shares_single_disk_read_across_pre_tool_gates()`
	# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
	# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
	# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_per_instance_folders_json_uninitialized_instance_and_stop_gate_a6()`
	# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_codex_custom_system_paths_trace_requests_metadata_and_answers()`
	# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cross_instance_handoff_and_audit_resolve_antigravity_and_disabled_codex_traces()`
	# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_default_system_paths_overrides_and_nested_codex_globs()`
	# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_dynamic_folders_json_and_cleanup_without_homes()`
	# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_post_checkpoint_evicted_citation_gate_and_issue48_defect_filing_gate()`
	# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_provenance_tiers_and_tier2_rejection()`
	# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_shell_write_targets_detects_test_production_and_doc_writes()`
	# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_antigravity_prepare_prepends_metadata_and_stop_gate_and_sync_accept_clean_chat_reply()`
	# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_resolve_project_identity_skips_user_registry_for_isolated_temp_dir()`
	# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_text_core_and_review_authorize_handle_metadata_prefixed_response()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_edited_project_projection_blocks_all_retirements()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_pilot_changes_only_selected_profiles_and_links_original_content()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_project_retirement_requires_exact_ownership_and_keeps_unrelated_files()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_wrong_skill_link_is_preserved()`
	# @used-by :meth:`test_observability_diagnostics.ObservabilityDiagnosticsTests.test_resolve_trace_source_populates_summary_db_from_journal_step()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_reinit_preserves_legacy_v1_project_without_v2_migration()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_resolve_or_create_reuses_unindexed_v2_project_dir()`
	# @used-by :meth:`test_optimistic_worktree_land.OptimisticWorktreeLandTests.test_targeted_wait_bypasses_foreign_lease_on_readonly_and_noncode_turns()`
	# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_linked_worktree_scope_accepts_full_suite_green_on_main_repo()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_df_servers_relocation_and_nested_server_artifact_root()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_is_tracked_workspace_supports_registered_single_projects_and_declarative_opt_outs()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_mid_process_overlay_creation_and_edit_invalidate_reverse_links_and_stay_fast()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_transitive_escapes_literal_dollar_in_env_and_relative_slot_anchoring()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_data_dir_for_supports_exact_root_and_state_dir_skips_host_scan()`
	# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_project_paths_fast_cache_hits_and_invalidates_on_fs_mutations()`
	# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_resolve_project_root_skips_host_overlay_scan_for_temp_subdirs()`
	# @used-by :meth:`test_portability.ProjectionTests.test_extra_rule_sources_are_projected_and_unsupported_selectors_reported()`
	# @used-by :meth:`test_project_rename_verification.ProjectRenameVerificationTests.test_auto_detects_sibling_init_launcher_without_flag()`
	# @used-by :meth:`test_resume_exports.ResumeExportTests.test_group_crash_reserves_all_numbers_and_preserves_previous_context()`
	# @used-by :meth:`test_rules_audit.RulesAuditTests.test_doctor_and_rules_audit_default_to_active_checkout_rules()`
	# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_ensure_hooks_uses_deployed_immutable_git_hooks_dir()`
	# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_promote_exports_snapshot_surviving_live_tree_corruption_and_preserving_anchor()`
	# @used-by :meth:`test_shadow_replay_m3.ShadowReplayM3Tests.test_shadow_replay_cli_executes_downstream_pipeline_and_cleans_scratch()`
	# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_tier0_source_index_schema_upgrade_and_single_read()`
	# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_commands_module_behavior_and_parity()`
	# @used-by :meth:`test_text_diagnostics.TextDiagnosticsTests.source()`
	# @used-by :meth:`test_text_diagnostics.TextDiagnosticsTests.test_explicit_root_required_and_sibling_not_discovered()`
	# @used-by :meth:`test_text_diagnostics.TextDiagnosticsTests.test_projection_receipt_detects_manual_edit_without_writing()`
	# @used-by :meth:`test_text_workflow.TextTransactionTests.test_workspace_and_integrity_verifier_single_pass_invariants()`
	# @used-by :meth:`test_turn_begin_status_and_auditors.TurnBeginStatusAndAuditorsTests.test_begin_returns_top_level_ok_true_for_primary_dry_run_and_child_with_foreign_reconciliation()`
	# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_gate_id_auto_clearing_and_resolve_journal_dir()`
	# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_adopt_requests_isolates_foreign_answer_group_mismatch()`
	# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_orphan_pair_adopted_without_duplicate_and_overwritten_claimed_pair_flags_conflict()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_instruction_snapshot_inventories_sources_without_claiming_model_delivery()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_malformed_local_rule_registration_is_retained_as_an_inventory_error()`
	# @used-by :meth:`test_turn_completion.TurnJournalReconcilerTests.test_compacted_status5_steps_single_pass_authorize_and_group_helpers()`
	# @used-by :meth:`test_upwork_init_e2e.UpworkInitFullE2ETests.test_e2e_blocked_report_doc5_and_shadowing_stop_gate_cli()`
	# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_isolated_temp_project_ignores_unrelated_host_worktree_cwd()`
	# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_resolve_code_anchor_maps_linked_worktree_to_canonical_main_repo()`
	# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_resolve_code_scope_keeps_active_worktree_for_new_files_and_falls_back_after_cleanup()`
	# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_worktree_scoped_issue_first_ignores_dirty_main_checkout()`
	# @used-by :mod:`Df.Harness.Meta.Builders`
	def resolve(self) -> dict[str, str]:
		from agent_tools.path_registry import canonicalize_root_dir
		canon = canonicalize_root_dir(self.__root)
		pdirs = ProjectIdentity.antigravity_project_dirs(self.__ag_paths, canon_root=canon)
		name = ProjectIdentity.__lookup_name_by_project_id(pdirs, canon, self.__project_id) or ProjectIdentity.__lookup_name_from_project_dirs(pdirs, canon) or ProjectIdentity.__lookup_name_from_project_json(canon) or canon.name or TimestampFormatter.posix_path(canon)
		return {'Name': name, 'Path': TimestampFormatter.posix_path(canon)}
	# @used-by :meth:`ProjectIdentity.resolve()`
	@staticmethod
	def __lookup_name_by_project_id(pdirs: list[Path], canon: Path, project_id: str | None) -> str | None:
		from agent_tools.platforms.antigravity import _project_item_matches_root
		r: str | None = None
		pid = project_id.strip() if isinstance(project_id, str) else ''
		if pid:
			for pdir in pdirs:
				cand = pdir / f'{pid}.json'
				data = ProjectIdentity.__read_json_dict(cand) if cand.is_file() else None
				if None is not data and isinstance(data.get('name'), str) and data['name'].strip():
					matched, _ = _project_item_matches_root(data, canon)
					if matched:
						r = data['name'].strip()
						break
		return r
	# @used-by :meth:`ProjectIdentity.resolve()`
	@staticmethod
	def __lookup_name_from_project_dirs(pdirs: list[Path], canon: Path) -> str | None:
		from agent_tools.platforms.antigravity import _project_item_matches_root
		r, relocated = (None, None)
		for item in (it for pdir in pdirs for it in ProjectIdentity.load_projects_dir_items(pdir)):
			matched, is_reloc = _project_item_matches_root(item, canon)
			raw_name = item.get('name')
			if matched and isinstance(raw_name, str) and raw_name.strip():
				if not is_reloc:
					r = raw_name.strip()
					break
				if None is relocated:
					relocated = raw_name.strip()
		return r if None is not r else relocated
	# @used-by :meth:`ProjectIdentity.resolve()`
	@staticmethod
	def __lookup_name_from_project_json(canon: Path) -> str | None:
		from agent_tools.path_registry import project_paths
		r: str | None = None
		try:
			pj = project_paths(canon, exact_root=True).project_json
			pdata = ProjectIdentity.__read_json_dict(pj) if pj.is_file() else None
		except (OSError, ValueError):
			pdata = None
		if None is not pdata:
			for key in ('project_name', 'name', 'domain', 'title'):
				val = pdata.get(key)
				if isinstance(val, str) and val.strip():
					r = val.strip()
					break
		return r
	# @used-by :meth:`ProjectIdentity.antigravity_project_dirs()`
	@staticmethod
	def __push_project_dir(dirs: list[Path], seen: set[str], p_val: str | Path | None) -> None:
		if p_val:
			p = Path(p_val)
			if p.is_dir():
				resolved = p.resolve()
				key = resolved.as_posix().lower()
				if key not in seen:
					seen.add(key)
					dirs.append(resolved)
	# @used-by :meth:`ProjectIdentity.__lookup_name_by_project_id()`
	# @used-by :meth:`ProjectIdentity.__lookup_name_from_project_json()`
	# @used-by :meth:`ProjectIdentity.load_projects_dir_items()`
	@staticmethod
	def __read_json_dict(path: Path) -> dict[str, Any] | None:
		try:
			data = json.loads(path.read_text(encoding='utf-8-sig'))
			r: dict[str, Any] | None = data if isinstance(data, dict) else None
		except (OSError, ValueError):
			r = None
		return r
	# @used-by :func:`agent_tools.meta.identity._antigravity_project_dirs()`
	# @used-by :meth:`ProjectIdentity.resolve()`
	@staticmethod
	def antigravity_project_dirs(ag_paths: dict[str, Any] | None=None, *, canon_root: Path | None=None) -> list[Path]:
		dirs: list[Path] = []
		seen: set[str] = set()
		if isinstance(ag_paths, dict):
			ProjectIdentity.__push_project_dir(dirs, seen, ag_paths.get('projects_dir'))
		if None is canon_root or (not ProjectIdentity.is_temp_path(canon_root)):
			try:
				from agent_tools.runtime import platform_instances
				for inst in platform_instances('antigravity', include_disabled=True).values():
					ProjectIdentity.__push_project_dir(dirs, seen, (inst.get('system_paths') or {}).get('projects_dir'))
			except Exception:
				pass
		return dirs
	# @used-by :func:`agent_tools.meta.identity._is_temp_path()`
	# @used-by :meth:`ProjectIdentity.antigravity_project_dirs()`
	@staticmethod
	def is_temp_path(path: Path) -> bool:
		try:
			r = path.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
		except OSError:
			r = False
		return r
	# @used-by :func:`agent_tools.meta.identity._load_projects_dir_items()`
	# @used-by :meth:`ProjectIdentity.__lookup_name_from_project_dirs()`
	@staticmethod
	def load_projects_dir_items(pdir: Path) -> list[dict[str, Any]]:
		try:
			mtime_ns = pdir.stat().st_mtime_ns
		except OSError:
			r: list[dict[str, Any]] = []
		else:
			cache_key = (pdir.as_posix().lower(), mtime_ns)
			cached = ProjectIdentity.PROJECTS_DIR_CACHE.get(cache_key)
			if None is not cached:
				r = cached
			else:
				if 64 < len(ProjectIdentity.PROJECTS_DIR_CACHE):
					ProjectIdentity.PROJECTS_DIR_CACHE.clear()
				items = [item for pf in sorted(pdir.glob('*.json')) if None is not (item := ProjectIdentity.__read_json_dict(pf))]
				ProjectIdentity.PROJECTS_DIR_CACHE[cache_key] = items
				r = items
		return r
	# @used-by :func:`agent_tools.meta.identity._resolve_ag_paths_safe()`
	# @used-by :mod:`Df.Harness.Meta.Builders`
	@staticmethod
	def resolve_ag_paths_safe(backend=None, *, instance=None, conversation_id=None) -> dict[str, Any] | None:
		try:
			from agent_tools.runtime import resolve_antigravity_paths, settings
			r = resolve_antigravity_paths(backend=backend, instance=instance, conversation_id=conversation_id, config=settings())
		except Exception:
			r = None
		return r
	# @used-by :func:`agent_tools.meta.identity._resolve_codex_paths_safe()`
	# @used-by :mod:`Df.Harness.Meta.Builders`
	@staticmethod
	def resolve_codex_paths_safe(backend=None, *, instance=None, conversation_id=None) -> dict[str, Any] | None:
		try:
			from agent_tools.runtime import platform_settings, resolve_codex_paths
			r = resolve_codex_paths(backend, instance=instance, conversation_id=conversation_id, codex_cfg=platform_settings('codex'))
		except Exception:
			r = None
		return r
