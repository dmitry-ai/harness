# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.ICached import ICached
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2017-08-10
# https://github.com/mage2pro/core/blob/11.6.1/Core/RAM.php#L3-L90
class RAM:
	__s: RAM | None = None
	# 2017-08-10
	# https://github.com/mage2pro/core/blob/11.6.1/Core/RAM.php#L67-L83
	# @used-by :meth:`RAM.s()`
	def __init__(self) -> None:
		# «Cache Key => Cached Data»
		self.__data: dict[str, Any] = {}
		# «Tag ID => Cache Keys»
		self.__tags: dict[str, list[str]] = {}
	# 2017-08-10
	# https://github.com/mage2pro/core/blob/11.6.1/Core/RAM.php#L5-L17
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
	def clean(self, tag: str) -> None:
		if tag in self.__tags:
			for k in self.__tags[tag]:
				self.__data.pop(k, None)
			self.__tags.pop(tag, None)
	# 2017-08-11
	# 2016-09-04 Distinguishes a stored `None` value from a missing key.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/RAM.php#L19-L29
	# 2026-11-26 "Handle worktree-land gate timeouts cleanly and add cross-cutting boundary regressions": https://github.com/dmitry-ai/harness/issues/365
	# @used-by :func:`Df.Core.lib.cache.dfcf.dfcf()`
	# @used-by :func:`Df.Core.lib.git.df_git_root()`
	# @used-by :func:`Df.Harness.lib.admission_ops.dfh_capture_admission()`
	# @used-by :func:`Df.Harness.lib.ag_daemon.dfh_project_item_matches_root()`
	# @used-by :func:`Df.Harness.lib.ag_inputs._resolve_ws_context_entry()`
	# @used-by :func:`Df.Harness.lib.blocked_report_ops.dfh_audit_runner_workflow_scope()`
	# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_run_cleanup_report_cli()`
	# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops._save_pending_snapshot()`
	# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops._unlink_ag_projects()`
	# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_finish_pending()`
	# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_restore_antigravity()`
	# @used-by :func:`Df.Harness.lib.cleanup_store_ops._evaluate_candidate()`
	# @used-by :func:`Df.Harness.lib.cleanup_store_ops._parse_pending_ag_entry()`
	# @used-by :func:`Df.Harness.lib.cleanup_store_ops._read_ag_rows()`
	# @used-by :func:`Df.Harness.lib.cleanup_store_ops.dfh_antigravity_projects()`
	# @used-by :func:`Df.Harness.lib.cli_input.dfh_consume_scratch_input()`
	# @used-by :func:`Df.Harness.lib.cli_input.dfh_consume_unchanged_files()`
	# @used-by :func:`Df.Harness.lib.cli_input.dfh_verify_scratch_input_path()`
	# @used-by :func:`Df.Harness.lib.completion_checks._collect_base_instruction_sources()`
	# @used-by :func:`Df.Harness.lib.completion_core.dfh_persist()`
	# @used-by :func:`Df.Harness.lib.completion_links._resolve_local_target()`
	# @used-by :func:`Df.Harness.lib.completion_record._resolve_legacy_group()`
	# @used-by :func:`Df.Harness.lib.completion_record.dfh_record()`
	# @used-by :func:`Df.Harness.lib.completion_record.dfh_same_turn_artifact_path()`
	# @used-by :func:`Df.Harness.lib.completion_state.dfh_load_turn_state()`
	# @used-by :func:`Df.Harness.lib.config_blocks.dfh_load_discovery_manifest()`
	# @used-by :func:`Df.Harness.lib.config_blocks.dfh_load_project_receipt()`
	# @used-by :func:`Df.Harness.lib.config_blocks.dfh_store_content_backup()`
	# @used-by :func:`Df.Harness.lib.config_codex._read_global_profile_value()`
	# @used-by :func:`Df.Harness.lib.config_codex._run_codex_project_publish()`
	# @used-by :func:`Df.Harness.lib.config_codex.dfh_native_config()`
	# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
	# @used-by :func:`Df.Harness.lib.journal_records._scan_orphan_candidates()`
	# @used-by :func:`Df.Harness.lib.journal_records._validate_answer_group_files()`
	# @used-by :func:`Df.Harness.lib.journal_records.dfh_get_existing_step_ids()`
	# @used-by :func:`Df.Harness.lib.journal_records.dfh_publish_step()`
	# @used-by :func:`Df.Harness.lib.journal_records.dfh_step_errors()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade._apply_upgrade_moves()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade._build_upgrade_plans()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade._merge_one_state_dir()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade._migrate_journal_state_dir()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_ensure_project_journal_upgraded()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_upgrade_journal()`
	# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_runner()`
	# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_config_toml()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_shared_role()`
	# @used-by :func:`Df.Harness.lib.native_links.dfh_load_state()`
	# @used-by :func:`Df.Harness.lib.path_resolve.dfh_resolve_project_root()`
	# @used-by :func:`Df.Harness.lib.path_schema.dfh_canonicalize_root_dir()`
	# @used-by :func:`Df.Harness.lib.path_schema.dfh_infer_default_profile()`
	# @used-by :func:`Df.Harness.lib.path_schema.dfh_v2_software_deliverable_dir()`
	# @used-by :func:`Df.Harness.lib.project.dfh_resolve_overview_md()`
	# @used-by :func:`Df.Harness.lib.request_binding.dfh_completion_project_id()`
	# @used-by :func:`Df.Harness.lib.research._resolve_relocated_target()`
	# @used-by :func:`Df.Harness.lib.research.dfh_inside()`
	# @used-by :func:`Df.Harness.lib.research.dfh_observed_use()`
	# @used-by :func:`Df.Harness.lib.rule_splitter.dfh_split_rules()`
	# @used-by :func:`Df.Harness.lib.rule_splitter.dfh_split_rules_main()`
	# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_ensure_repo_git_hooks()`
	# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_has_git_head()`
	# @used-by :func:`Df.Harness.lib.shadow_clone.dfh_cleanup_shadow_root()`
	# @used-by :func:`Df.Harness.lib.storage.dfh_write_immutable_bytes()`
	# @used-by :func:`Df.Harness.lib.text_claims.dfh_registry_path()`
	# @used-by :func:`Df.Harness.lib.text_review.dfh_text_review_state()`
	# @used-by :func:`Df.Harness.lib.text_sources.dfh_source_attempt()`
	# @used-by :func:`Df.Harness.lib.text_workflow.dfh_has_linked_ancestor()`
	# @used-by :func:`Df.Harness.lib.text_workflow.dfh_target_bytes()`
	# @used-by :func:`Df.Harness.lib.trace_review.dfh_verify_review_proof_core()`
	# @used-by :func:`agent_tools.repo_wait._workspace_code_repos()`
	# @used-by :func:`test_historical_admission._restore_tree_in_place()`
	# @used-by :func:`test_project_rename._assert_renamed_journal_and_state()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__load_state()`
	# @used-by :meth:`Df.Harness.Analysis.LocalSourceResolver.LocalSourceResolver.resolve()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationResolver.ObservationResolver.__lookup_index()`
	# @used-by :meth:`Df.Harness.Analysis.OwnedPublisher.OwnedPublisher.__commit_locked()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__sync_locked()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__write_card()`
	# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.__commit_locked()`
	# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.__find_git_root()`
	# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__prepare_codex_outputs()`
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__apply()`
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__commit_receipt()`
	# @used-by :meth:`Df.Harness.Config.NativeProfile.Plan.Plan.file()`
	# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__commit()`
	# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__plan_outputs()`
	# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__plan_retirements()`
	# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__write_backups_and_planned()`
	# @used-by :meth:`Df.Harness.Gate.CdpBypassGate.CdpBypassGate.is_inside_harness_code()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.enclosing_github_repo()`
	# @used-by :meth:`Df.Harness.Git.BlobSizeValidator.BlobSizeValidator.validate()`
	# @used-by :meth:`Df.Harness.Git.GlobalIgnoreSyncer.GlobalIgnoreSyncer.__plan()`
	# @used-by :meth:`Df.Harness.Git.GlobalIgnoreSyncer.GlobalIgnoreSyncer.sync()`
	# @used-by :meth:`Df.Harness.Git.LandingLease.LandingLease.__init__()`
	# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.__verify_commit()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.extract_added_diff_urls()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.is_issue_tracked()`
	# @used-by :meth:`Df.Harness.Git.RepoResolver.RepoResolver.resolve()`
	# @used-by :meth:`Df.Harness.Git.RepoWaiter.RepoWaiter.__init__()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__map_path_to_repo()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__resolve_target_repos()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__workspace_code_repos()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCleaner.WorktreeCleaner.cleanup()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCreator.WorktreeCreator.begin()`
	# @used-by :meth:`Df.Harness.Git.WorktreePathResolver.WorktreePathResolver.__resolve_deleted()`
	# @used-by :meth:`Df.Harness.Git.WorktreeRemovalGuard.WorktreeRemovalGuard.remove()`
	# @used-by :meth:`Df.Harness.Git.WorktreeTransaction.WorktreeTransaction.__stage_into_worktree()`
	# @used-by :meth:`Df.Harness.Git.WorktreeTransaction.WorktreeTransaction.remove()`
	# @used-by :meth:`Df.Harness.Grounding.Doc5RequirementChecker.Doc5RequirementChecker.__workspace_repo_slugs()`
	# @used-by :meth:`Df.Harness.Grounding.ProblemIssueSpecification.ProblemIssueSpecification.workspace_repo_slugs()`
	# @used-by :meth:`Df.Harness.Issue.DirtyIssueFirstScanner.DirtyIssueFirstScanner.scan()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.__find_git_repo_root()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__check_repo_commits_and_files()`
	# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__load_existing_group()`
	# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__load_or_create_group()`
	# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__write_pending_step()`
	# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__append_executor_receipt()`
	# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__collect_project_executors()`
	# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.project_metrics()`
	# @used-by :meth:`Df.Harness.Path.PathReporter.PathReporter.__check_similar_groups()`
	# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__apply_v2_legacy_dir_names()`
	# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.to_dict()`
	# @used-by :meth:`Df.Harness.Project.AttachmentInventory.AttachmentInventory.__register_bytes()`
	# @used-by :meth:`Df.Harness.Project.AttachmentInventory.AttachmentInventory.__resolve_source_target()`
	# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.__read_state()`
	# @used-by :meth:`Df.Harness.Project.Context.LetterDiscoverer.LetterDiscoverer.__pick_in_dir()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.__process_asset()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__apply_drain()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__prepare_receipt()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__retire_entries()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__unlink_and_mark_drained()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.drain_incoming()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.resolve_project()`
	# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.restore()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakeIndexer.IntakeIndexer.rebuild()`
	# @used-by :meth:`Df.Harness.Project.Intake.IntakePathGuard.IntakePathGuard.inventory()`
	# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.populate()`
	# @used-by :meth:`Df.Harness.Project.RegistrationAttemptStarter.RegistrationAttemptStarter.begin()`
	# @used-by :meth:`Df.Harness.Project.RegistrationStore.RegistrationStore.save()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__rollback()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__validate_inputs()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.update_projects_index()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.migrate_journal_state()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.__commit_result()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.__read_render_state()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.sync()`
	# @used-by :meth:`Df.Harness.Research.Collector.Collector.__persist_fresh()`
	# @used-by :meth:`Df.Harness.Research.Collector.Collector.collect()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__write_cached()`
	# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.__validate_local_target()`
	# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__activate_release()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.run()`
	# @used-by :meth:`Df.Harness.Tdd.CodeClassifier.CodeClassifier.__is_project_marker_dir()`
	# @used-by :meth:`Df.Harness.Tdd.CodeClassifier.CodeClassifier.__resolve_deleted_worktree_scope()`
	# @used-by :meth:`Df.Harness.Tdd.CodeClassifier.CodeClassifier.resolve_code_scope()`
	# @used-by :meth:`Df.Harness.Tdd.CommentDiff.CommentDiff.git_read_text()`
	# @used-by :meth:`Df.Harness.Tdd.DiffContract.DiffContract.__git_batch_texts()`
	# @used-by :meth:`Df.Harness.Tdd.DiffCoverage.DiffCoverage.__touched_git_repos()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__git_read_bytes()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__git_show_text()`
	# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__resolve_event_target_scopes()`
	# @used-by :meth:`Df.Harness.Tdd.Exemption.Exemption.is_write_event_exempt()`
	# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.__resolve_repo_binding()`
	# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.find_matching_recipes()`
	# @used-by :meth:`Df.Harness.Tdd.WorktreeScope.WorktreeScope.canonical_scope_path()`
	# @used-by :meth:`Df.Harness.Tdd.WorktreeScope.WorktreeScope.resolve_command_scope_key()`
	# @used-by :meth:`Df.Harness.Text.ApprovalIntegrityChecker.ApprovalIntegrityChecker.__check_native_proof()`
	# @used-by :meth:`Df.Harness.Text.ClaimRegistryStore.ClaimRegistryStore.__persist()`
	# @used-by :meth:`Df.Harness.Text.ClaimRegistryStore.ClaimRegistryStore.save()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__write_rendered()`
	# @used-by :meth:`Df.Harness.Text.DraftSnapshotter.DraftSnapshotter.snapshot()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__ensure_workspace_identity()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.index()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentDownloader.AttachmentDownloader.download()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_inspect()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor._run_poppler()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_context_config()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_manifests()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectDirResolver.ProjectDirResolver.resolve_or_create()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__load_and_prepare_fs()`
	# @used-by :meth:`Df.Harness.Workflow.RegistrationStatusChecker.RegistrationStatusChecker.status()`
	# @used-by :meth:`Df.Harness.Workflow.StateLoader.StateLoader.load()`
	# @used-by :meth:`Df.Harness.Xref.Java.Tags.Tags.is_valid_external()`
	# @used-by :meth:`Df.Harness.Xref.Js.Tags.Tags.is_valid_external()`
	# @used-by :meth:`Df.Harness.Xref.Python.Tags.Tags.is_valid_external_target()`
	# @used-by :meth:`RAM.get()`
	# @used-by :meth:`test_agent_tools.ContextTests.test_missing_input_fails_and_dry_run_writes_nothing()`
	# @used-by :meth:`test_agent_tools.JournalTests.test_empty_payload_has_no_side_effect()`
	# @used-by :meth:`test_agent_tools.JournalTests.test_exact_bytes_and_no_keyword_authorization()`
	# @used-by :meth:`test_agent_tools.JournalTests.test_existing_same_request_is_not_ownership()`
	# @used-by :meth:`test_agent_tools.JournalTests.test_failed_second_write_recovers_with_token()`
	# @used-by :meth:`test_agent_tools.JournalTests.test_o_journal_20_entry_bucketing_and_partial_range_normalization()`
	# @used-by :meth:`test_agent_tools.JournalTests.test_process_crash_releases_lock_and_reservation_is_recoverable()`
	# @used-by :meth:`test_agent_tools.JournalTests.test_recovery_does_not_overwrite_conflict()`
	# @used-by :meth:`test_agent_tools.SnapshotTests.test_current_bytes_preserved_once_per_turn()`
	# @used-by :meth:`test_agent_tools.UpworkProjectTests.test_agent_data_dir_prefers_vai_directory()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_existing_unowned_guidance_is_preserved_without_partial_installation()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.native_fixture()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_html_links_json_summary_non_destructive_collect_and_scratch_cleanliness()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_void_elements_compact_extracted_disk_json_and_max_bytes_guard()`
	# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
	# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_antigravity_arch_record_review_works_on_bare_code_workspace_without_text_marker()`
	# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_cli_prepare_input_record_needs_changes_and_check_text_roundtrip()`
	# @used-by :meth:`test_bounded_foreign_sync.BoundedForeignSyncTests.test_pending_sync_index_does_not_create_unbootstrapped_file_on_persist()`
	# @used-by :meth:`test_bounded_foreign_sync.BoundedForeignSyncTests.test_reconcile_foreign_does_not_create_index_when_only_own_turn_prepared()`
	# @used-by :meth:`test_cleanup.CleanupReportTests.test_empty_answer_or_naive_timestamp_does_not_create_a_log()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_changed_native_payload_during_final_check_is_never_unlinked()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_chat_after_native_unlink_restores_both_registrations_and_folder_assignment()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_folders_publication_failure_after_unlink_recovers_without_native_file()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_initializing_catalog_is_a_reported_block_without_deleting_anything()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_conflicting_job_or_unowned_manifests_never_authorize_deletion()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_discovery_failure_without_readable_history_stays_unresolved()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_historical_ids_are_compared_in_full_instead_of_their_numeric_prefix()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_init_without_marker_is_discovered_and_old_file_uri_matches_native_registration()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_native_id_conversation_preserves_project_with_unrelated_cwd()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_missing_history_or_invalid_schema_blocks_cleanup()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_multi_root_projects_and_non_init_projects_are_preserved()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_native_unlink_failure_keeps_folders_and_retries_the_exact_ids()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_new_chat_restores_a_partially_held_codex_project()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_new_conversation_after_preview_is_rechecked_before_any_delete()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_pending_codex_keeps_antigravity_and_archive_and_continues_other_projects()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_pending_sibling_restores_full_folder_ancestry_after_other_project_pruned_it()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_preview_is_read_only_and_apply_cleans_both_platforms_preserving_entire_archive()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_strict_72_hour_boundary_and_recent_projects_are_preserved()`
	# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_apply_persists_sidecar_manifest_with_rollback_snapshots_while_dry_run_stays_readonly()`
	# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_cleanup_report_writes_metadata_header_links_manifest_and_consumes_scratch_file()`
	# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.test_apply_and_cleanup_report_manifest_and_metadata_roundtrip()`
	# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.test_rename_project_cleanup_recent_and_old_path_history()`
	# @used-by :meth:`test_cli_common.CliCommonTests.test_scratch_consumption_sha256_and_parallel_answer_guard()`
	# @used-by :meth:`test_df_article.LexiconAndProjectionTests.test_build_native_uses_shared_skills_without_project_wrappers()`
	# @used-by :meth:`test_df_article.ReferenceArticleTests.test_deleted_premise_blocks_rendering_until_dependents_are_resolved()`
	# @used-by :meth:`test_df_article.SlopDetectionTests.test_project_bans_are_discovered_from_the_project_root()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_b.DfHarnessS11Wave2CCovIssuesBTests.test_turn_auditor_scope_completeness_and_turn_scope_resolver()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_path_subsystem_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2d_cli_cov.DfHarnessS11Wave2dCliCovTests.test_cli_input_guards_and_error_payloads()`
	# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_native_builder_and_projection_publisher()`
	# @used-by :meth:`test_df_harness_s11_wave2d_config_cov.DfHarnessS11Wave2dConfigCovTests.test_native_profiles_install_rename_retire_and_rollback()`
	# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_stop_gate_continuation_guard_and_emergency_capture()`
	# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_completion_tail()`
	# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_worktree_land_handles_cross_cutting_commit_and_diff_coverage_timeout()`
	# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_worktree_land_enforces_answer_gate_corpus_before_merge()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_arbitrary_intake_receipt_cannot_promote_own_note_or_attachment()`
	# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_primary_reads_actual_generation_and_executor_configuration_paths()`
	# @used-by :meth:`test_git_fixture_cache.GitFixtureCacheTests.test_clone_template_git_repo_caches_init_and_isolates_clones()`
	# @used-by :meth:`test_git_ignore.GlobalGitIgnoreTests.test_isolated_synthetic_primary_skips_host_git_ignore_mutation()`
	# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_and_consume_input_with_readback_verification()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_new_admission_still_rejects_aged_sources_and_cannot_recover_failed_gate()`
	# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
	# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
	# @used-by :meth:`test_intake.IntakeTests.test_manual_intake_index_is_never_overwritten()`
	# @used-by :meth:`test_intake.IntakeTests.test_scope_name_and_directory_job_mismatch_are_preserved()`
	# @used-by :meth:`test_intake.IntakeTests.test_symlinked_material_cannot_import_or_delete_outside_target()`
	# @used-by :meth:`test_issue_decomposition.IssueDecompositionTests.test_issue_evidence_workspace_uses_locked_atomic_turn_updates()`
	# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_cli_issue_first_check_read_only_and_legacy_delivered_immutability()`
	# @used-by :meth:`test_issue_preflight_and_batch.IssuePreflightAndBatchTests.test_batch_close_enforces_grounding_consumes_inputs_and_extracts_actions()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.check_skill_rename_rollback()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_changed_created_link_does_not_stop_other_guarded_rollback()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_check_creates_no_lock_receipt_or_profile_files()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_concurrent_preimage_change_is_preserved_before_application()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_conflicting_hook_blocks_the_whole_selected_plan()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_custom_same_name_role_and_personal_loader_edit_are_preserved()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_dangling_directory_symlink_skill_is_retired()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_edited_project_projection_blocks_all_retirements()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_edited_wrapper_is_not_retired_or_replaced()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_new_link_failure_rolls_back_existing_profile_files()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_pilot_changes_only_selected_profiles_and_links_original_content()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_project_retirement_requires_exact_ownership_and_keeps_unrelated_files()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_removed_role_retires_its_owned_link_and_definition()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_parent_link_injected_immediately_before_creation_cannot_escape()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_rename_failure_restores_retired_link_definition_and_receipt()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_rename_keeps_unselected_profile_and_shared_target_owned()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_rename_retires_only_owned_links_and_shared_definition()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_shared_manual_edit_is_preserved()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_parent_link_injected_during_backup_is_preserved_without_escape()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_parent_link_injected_immediately_before_creation_cannot_escape()`
	# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_rename_retires_owned_dangling_link_with_identity_backup()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_cli_init_reuses_capture_without_browser()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_invalid_names_dates_and_capture_do_not_create_projects()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_native_manifests_and_full_initial_port()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_reinit_preserves_legacy_v1_project_without_v2_migration()`
	# @used-by :meth:`test_onboarding.InitializationTests.test_repeat_preserves_every_curated_file_and_configuration()`
	# @used-by :meth:`test_onboarding.IsolationTests.test_pending_journal_cannot_be_recovered_into_another()`
	# @used-by :meth:`test_onboarding.RegistrationTests.native_primary()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_polyglot_land_and_health_handle_subprocess_timeout_cleanly()`
	# @used-by :meth:`test_polyglot_land.PolyglotLandTests.test_polyglot_node_repo_runs_in_workspace_sandbox_and_lands()`
	# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
	# @used-by :meth:`test_portability.CodexEvidenceTests.test_second_platform_keeps_original_date_root_manual_kb_and_saved_snapshot()`
	# @used-by :meth:`test_portability.ProjectionTests.test_dangling_personal_guidance_links_are_preserved_before_shared_publication()`
	# @used-by :meth:`test_portability.ProjectionTests.test_extra_rule_sources_are_projected_and_unsupported_selectors_reported()`
	# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
	# @used-by :meth:`test_portability.ProjectionTests.test_project_rules_feed_both_systems_and_detect_stale_codex_projection()`
	# @used-by :meth:`test_portability.ProjectionTests.test_unowned_legacy_prevents_partial_migration()`
	# @used-by :meth:`test_portability.ProjectionTests.test_verified_legacy_migrates_but_manual_configuration_and_fallback_survive()`
	# @used-by :meth:`test_project_labels.ProjectLabelValidationTests.test_init_cli_rejects_kebab_slug_and_bad_domain_with_exit_2()`
	# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_cleanup_integration()`
	# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_cli_and_kebab_rejection()`
	# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_rolls_back_on_collision_or_failure()`
	# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_updates_folder_indexes_registrations_rules_and_journal()`
	# @used-by :meth:`test_project_rename_verification.ProjectRenameVerificationTests.test_post_verify_rolls_back_all_state_on_stage_or_review_regression()`
	# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_collect_receipt_preserves_plan_after_input_is_consumed()`
	# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_failed_or_changed_input_is_retained()`
	# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_invalid_consumption_scope_fails_before_analysis_changes()`
	# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_progress_is_replaced_without_archiving_derived_navigation()`
	# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_stdin_analysis_and_owned_scratch_inputs_leave_no_permanent_candidate()`
	# @used-by :meth:`test_resume_exports.ResumeExportTests.test_atomic_create_does_not_leave_a_partial_final_file()`
	# @used-by :meth:`test_resume_exports.ResumeExportTests.test_failed_extraction_keeps_saved_observation_and_reuses_it()`
	# @used-by :meth:`test_rules_architecture_m2.RulesArchitectureM2Tests.test_always_on_budget_and_three_layer_partition()`
	# @used-by :meth:`test_shadow_replay_m3.ShadowReplayM3Tests.test_shadow_replay_cli_executes_downstream_pipeline_and_cleans_scratch()`
	# @used-by :meth:`test_stop_emergency_capture_and_foreign_sync.StopEmergencyCaptureAndForeignSyncTests.test_begin_syncs_idle_open_foreign_reservation_and_skips_conflict_failed_and_running()`
	# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_cli_ratchet_ok_and_tdd_check_commands()`
	# @used-by :meth:`test_text_integration.TextReviewTests.test_independent_routine_verdict_apply_and_exact_journal()`
	# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_antigravity_native_review_for_text_uses_actual_workspace_binding()`
	# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_codex_native_review_for_text_has_no_fabricated_upwork_job()`
	# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_internal_identity_is_explicit_and_validated_without_creating_upwork_state()`
	# @used-by :meth:`test_text_workflow.TextMapTests.test_explicit_offer_can_be_nonfactual_without_a_registry()`
	# @used-by :meth:`test_text_workflow.TextMapTests.test_standalone_proposal_map_needs_no_five_analysis_stages()`
	# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_automatic_journal_only_upgrade_and_cli_subcommand()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_answer_check_detects_link5_doc4_verify1_and_exec5_without_disk_side_effects()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_antigravity_journal_conversation_auto_titling_and_comma_append()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_compaction_index_offload_stdout_bounds_delivery_cleanup_and_dry_run_non_bypass()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_pre_invocation_hook_idempotent_turn_begin_child_skip_terminate_and_dry_run()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_registered_empty_launcher_project_tracks_pre_init_failures_and_hands_off_to_daily_project()`
	# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
	# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_mid_turn_checkpoint_blocks_until_recover_checkpoint()`
	# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_universal_source_kb_check_blocks_reddit_js_shell_unverified_short_links_missing_anchors_and_fake_quotes()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_begin_and_prepare_cannot_register_or_start_a_daemon_even_with_legacy_watch_true()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_child_foreign_root_and_foreign_profile_never_create_user_pairs()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_explicit_external_journal_binding_is_preserved_during_native_sync()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_external_journal_cannot_bypass_the_current_client_document_gate()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_foreground_integrity_check_preserves_a_deleted_completed_journal_file()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_matching_native_request_ids_reuse_an_existing_record_answer_group()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_ordinary_analysis_needs_no_article_or_fabricated_intake()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_partial_final_aborted_turn_and_commentary_are_not_delivery()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_steering_during_begin_invalidates_the_prepared_request_snapshot()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_switching_active_native_turn_during_prepare_records_no_answer()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_sync_respects_the_custom_journal_of_an_unprepared_turn()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_tracked_initial_analysis_still_requires_answer_bound_approval()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_waiting_for_writer_lock_does_not_allow_a_stale_ready_result()`
	# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_new_v2_upwork_project_creates_dot_md_not_readme()`
	# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_worker_semaphore_bounds_total_slots_and_reclaims_dead_and_expired()`
	# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_worktree_cleanup_fails_closed_with_lock_holders_on_locked_dir()`
	# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_cli_worktree_begin_status_cleanup()`
	# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_resolve_code_scope_keeps_active_worktree_for_new_files_and_falls_back_after_cleanup()`
	# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_two_parallel_worktrees_commit_and_land_with_single_test_run()`
	# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_cli_worktree_land_default_removes_and_keep_preserves()`
	# @used-by :meth:`test_worktree_lifecycle.WorktreeLifecycleTests.test_worktree_land_removes_worktree_and_branch_by_default()`
	def exists(self, k: str) -> bool:
		return k in self.__data
	# 2017-08-11
	# https://github.com/mage2pro/core/blob/11.6.1/Core/RAM.php#L31-L36
	# @used-by :func:`Df.Core.lib.cache.dfcf.dfcf()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
	def get(self, k: str) -> Any:
		return self.__data[k] if self.exists(k) else None
	# 2017-08-11
	# https://github.com/mage2pro/core/blob/11.6.1/Core/RAM.php#L38-L42
	# @used-by :func:`Df.Harness.lib.cleanup_store_ops.dfh_codex_glob_scope()`
	# @used-by :func:`Df.Harness.lib.grounding.dfh_read_only_grounding()`
	# @used-by :func:`Df.Harness.lib.runtime_cache.dfh_skip_shell_violations()`
	# @used-by :func:`Df.Harness.lib.runtime_context.dfh_using()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
	def reset(self) -> None:
		self.__data = {}
		self.__tags = {}
	# 2017-08-10
	# https://github.com/mage2pro/core/blob/11.6.1/Core/RAM.php#L44-L65
	# @used-by :func:`Df.Core.lib.cache.dfcf.dfcf()`
	# @used-by :func:`Df.Harness.lib.cleanup_store_ops.dfh_codex_glob_scope()`
	# @used-by :func:`Df.Harness.lib.grounding.dfh_read_only_grounding()`
	# @used-by :func:`Df.Harness.lib.runtime_cache.dfh_skip_shell_violations()`
	# @used-by :func:`Df.Harness.lib.runtime_context.dfh_using()`
	# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.__stop_siblings()`
	# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.__run_unittest_suite()`
	# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_locked_create_on_held_zero_byte_lock_waits_without_permission_error()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
	# @used-by :meth:`test_registration_portability.RegistrationTests.test_slow_previous_success_does_not_erase_a_newer_failed_attempt()`
	def set(self, k: str, v: Any, tags: list[str] | None=None) -> Any:
		eff_tags = list(tags or ())
		if isinstance(v, ICached):
			eff_tags = eff_tags + [t for t in v.tags() if t not in eff_tags]
		self.__data[k] = v
		for tag in eff_tags:
			if tag not in self.__tags:
				self.__tags[tag] = [k]
			elif k not in self.__tags[tag]:
				self.__tags[tag].append(k)
		return v
	# 2017-08-10
	# https://github.com/mage2pro/core/blob/11.6.1/Core/RAM.php#L85-L89
	# @used-by :func:`Df.Core.lib.cache.o.df_ram()`
	@staticmethod
	def s() -> RAM:
		if None is RAM.__s:
			RAM.__s = RAM()
		return RAM.__s
