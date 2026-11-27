# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import os
import tempfile
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Core.lib.state import df_is_windows
from Df.Harness.lib.storage import dfh_create_bytes, dfh_data_dir_for, dfh_iter_embedded_json_objects, dfh_journal_data_dir_for, dfh_locked, dfh_read_addressed_json, dfh_replace_bytes, dfh_write_immutable_bytes
# @used-by :func:`agent_tools.cleanup.restore_antigravity()`
# @used-by :func:`agent_tools.intake.commit_capture()`
# @used-by :func:`agent_tools.journal._publish()`
# @used-by :func:`agent_tools.journal.record_answer()`
# @used-by :func:`agent_tools.journal.record_step()`
# @used-by :func:`agent_tools.native_profiles._facade_ops()`
# @used-by :func:`agent_tools.research._write_cached_extraction()`
# @used-by :func:`agent_tools.research.collect()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.text_claims.save_registry()`
# @used-by :func:`agent_tools.text_workflow.write_candidate_output()`
# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__write_card()`
# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.__commit_locked()`
# @used-by :meth:`Df.Harness.Experiment.PlanPreparer.PlanPreparer.prepare_plan()`
# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__write_run()`
# @used-by :meth:`Df.Harness.Project.AttachmentInventory.AttachmentInventory.__register_bytes()`
# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.__process_asset()`
# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__init__()`
# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.populate()`
# @used-by :meth:`Df.Harness.Project.OnceFileWriter.OnceFileWriter.write()`
# @used-by :meth:`Df.Harness.Upwork.AttachmentDownloader.AttachmentDownloader.download()`
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_inspect()`
# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_context_config()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.apply()`
# @used-by :meth:`test_agent_tools.JournalTests.test_failed_second_write_recovers_with_token()`
# @used-by :meth:`test_agent_tools.JournalTests.test_recovery_does_not_overwrite_conflict()`
# @used-by :meth:`test_intake.IntakeTests.test_copy_failure_preserves_all_staging_and_retry_reuses_objects()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_atomic_create_does_not_leave_a_partial_final_file()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_group_crash_reserves_all_numbers_and_preserves_previous_context()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_valid_dom_capture_identity_can_resolve_the_http_channel_failure()`
# @used-by :mod:`agent_tools.intake`
def create_bytes(path: Path, data: bytes):
	dfh_create_bytes(path, data)
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.text_core.find_bans()`
# @used-by :func:`agent_tools.text_workflow.write_candidate_output()`
# @used-by :meth:`Df.Harness.Project.Context.ContextGenerator.ContextGenerator.generate()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._verify_projection_receipt()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_check_creates_no_lock_receipt_or_profile_files()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_edited_project_projection_blocks_all_retirements()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_project_retirement_requires_exact_ownership_and_keeps_unrelated_files()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_mid_process_overlay_creation_and_edit_invalidate_reverse_links_and_stay_fast()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_data_dir_for_supports_exact_root_and_state_dir_skips_host_scan()`
# @used-by :meth:`test_portability.ProjectionTests.test_shared_generation_uses_one_owner_across_projects_and_profile_install()`
def data_dir_for(path: Path, *, exact_root: bool=False) -> Path:
	return dfh_data_dir_for(path, exact_root=exact_root)
# @used-by :func:`agent_tools.issues.service_helpers._decode_gh_stdout()`
# @used-by :meth:`Df.Harness.Experiment.NativeGeoExtractor.NativeGeoExtractor.extract_country()`
# @used-by :meth:`Df.Harness.Experiment.PreregistrationAuditor.PreregistrationAuditor.__is_plan_commit()`
def iter_embedded_json_objects(value, *, parse_root: bool=True, recursive: bool=True):
	return dfh_iter_embedded_json_objects(value, parse_root=parse_root, recursive=recursive)
# @used-by unused
def journal_data_dir_for(eff: Path) -> Path:
	return dfh_journal_data_dir_for(eff)
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :func:`agent_tools.landing_lease._try_acquire_once()`
# @used-by :func:`agent_tools.landing_lease._unqueue_owner()`
# @used-by :func:`agent_tools.landing_lease.release_lease()`
# @used-by :func:`agent_tools.research.collect()`
# @used-by :func:`agent_tools.research.observed_use()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.text_browser._endpoint_lock()`
# @used-by :func:`agent_tools.text_claims.save_registry()`
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :func:`agent_tools.text_sources._attempt()`
# @used-by :func:`agent_tools.text_workflow.write_candidate_output()`
# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.save()`
# @used-by :meth:`Df.Harness.Analysis.OwnedPublisher.OwnedPublisher.publish()`
# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.sync()`
# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.__commit_locked()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__persist_review_index()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__register_package_index()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__append_executor_receipt()`
# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.sync()`
# @used-by :meth:`Df.Harness.Project.Context.ContextGenerator.ContextGenerator.generate()`
# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__run_commit()`
# @used-by :meth:`Df.Harness.Project.RegistrationAttemptStarter.RegistrationAttemptStarter.begin()`
# @used-by :meth:`Df.Harness.Project.RegistrationStore.RegistrationStore.save()`
# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__sync_antigravity_native_files()`
# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.update_projects_index()`
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.record_exemption()`
# @used-by :meth:`Df.Harness.TestRunner.WorkerSemaphore.WorkerSemaphore.__try_reserve_once()`
# @used-by :meth:`Df.Harness.Upwork.ProjectDirResolver.ProjectDirResolver.resolve_or_create()`
# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.initialize()`
# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._update_single_turn_locked()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.apply()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.begin()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.verify()`
# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_locked_concurrent_fresh_files_succeed_without_permission_error()`
# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_locked_create_on_held_zero_byte_lock_waits_without_permission_error()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_storage_locked_concurrent_threads_no_permission_error()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_waiting_for_writer_lock_does_not_allow_a_stale_ready_result()`
def locked(path: Path, timeout: float=15, *, create=True):
	return dfh_locked(path, timeout=timeout, create=create)
# @used-by :func:`agent_tools.text_sources._evaluate()`
# @used-by :func:`agent_tools.text_sources.read_source_check()`
# @used-by :func:`agent_tools.text_sources.source_integrity()`
# @used-by :meth:`Df.Harness.Review.PackageEnvelopeReader.PackageEnvelopeReader.read_envelope()`
# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.read_package()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace._check_replay()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace._gate_target()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.read_check()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.applied_integrity()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.reconciled_integrity()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.verify_applied_successor()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_merkle_cached_single_reviewer_quorum_recognizes_approved_digests_and_storage_receipts()`
def read_addressed_json(path: Path, *, suffix: str='', stem_match: bool=False, error_msg: str='Invalid immutable artifact') -> tuple[bytes, dict]:
	return dfh_read_addressed_json(path, suffix=suffix, stem_match=stem_match, error_msg=error_msg)
# @used-by :func:`agent_tools.analysis.publish_owned()`
# @used-by :func:`agent_tools.cleanup._finish_pending()`
# @used-by :func:`agent_tools.cleanup.remove_antigravity()`
# @used-by :func:`agent_tools.cleanup.restore_antigravity()`
# @used-by :func:`agent_tools.git_ignore._append_exclude_pattern()`
# @used-by :func:`agent_tools.git_ignore._write_verified_ignore()`
# @used-by :func:`agent_tools.landing_lease._save_state()`
# @used-by :func:`agent_tools.native_profiles._facade_ops()`
# @used-by :func:`agent_tools.research._write_cached_extraction()`
# @used-by :func:`agent_tools.research.collect()`
# @used-by :func:`agent_tools.research.observed_use()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.text_claims.save_registry()`
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :func:`agent_tools.text_sources._attempt()`
# @used-by :func:`agent_tools.text_workflow.write_candidate_output()`
# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.save()`
# @used-by :meth:`Df.Harness.Analysis.OwnedPublisher.OwnedPublisher.__init__()`
# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__write_card()`
# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.__commit_locked()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__persist_review_index()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__register_package_index()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__append_executor_receipt()`
# @used-by :meth:`Df.Harness.Project.AttachmentKbSyncer.AttachmentKbSyncer.sync()`
# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.__write_files()`
# @used-by :meth:`Df.Harness.Project.Context.ContextGenerator.ContextGenerator.__build()`
# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.__resolve_loom_body()`
# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.load_media_descriptions()`
# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__unlink_and_mark_drained()`
# @used-by :meth:`Df.Harness.Project.RegistrationAttemptStarter.RegistrationAttemptStarter.begin()`
# @used-by :meth:`Df.Harness.Project.RegistrationStore.RegistrationStore.save()`
# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__rollback()`
# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__sync_antigravity_native_files()`
# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.update_projects_index()`
# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.__rewrite_json_file()`
# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.__update_folder_rule()`
# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.__update_project_json()`
# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.rewrite()`
# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.rewrite_launcher_handoffs()`
# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.update()`
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.record_exemption()`
# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.__save_timings()`
# @used-by :meth:`Df.Harness.TestRunner.WorkerSemaphore.WorkerSemaphore.__try_reserve_once()`
# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_context_config()`
# @used-by :meth:`Df.Harness.Upwork.ProjectConfigurator.ProjectConfigurator.__sync_manifests()`
# @used-by :meth:`Df.Harness.Upwork.ProjectDirResolver.ProjectDirResolver.__resolve_or_make_new()`
# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__load_and_prepare_fs()`
# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._update_single_turn_locked()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.persist_issue_evidence()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.persist_repo_transfer_evidence()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.apply()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.save_index()`
# @used-by :meth:`test_analysis_workflow.PublicationTests.test_interrupted_state_write_preserves_published_output_for_recovery()`
# @used-by :meth:`test_cleanup.CleanupTests.test_folders_publication_failure_after_unlink_recovers_without_native_file()`
# @used-by :meth:`test_storage_fsync_guard.StorageFsyncGuardTests.test_fsync_runs_by_default_and_when_env_is_zero()`
# @used-by :meth:`test_storage_fsync_guard.StorageFsyncGuardTests.test_fsync_skipped_inside_tempdir_when_env_is_one()`
# @used-by :meth:`test_storage_fsync_guard.StorageFsyncGuardTests.test_fsync_still_runs_outside_tempdir_even_when_env_is_one()`
# @used-by :meth:`test_turn_completion.WatcherLifecycleTests.test_equal_byte_replacement_does_not_create_temporary_files_or_touch_mtime()`
def replace_bytes(path: Path, data: bytes):
	dfh_replace_bytes(path, data)
# @used-by :func:`agent_tools.text_browser.save_cdp_identity()`
# @used-by :func:`agent_tools.text_review.prepare()`
# @used-by :func:`agent_tools.text_sources.probe_links()`
# @used-by :func:`agent_tools.text_sources.save_source_check()`
# @used-by :func:`agent_tools.text_workflow._immutable()`
# @used-by :meth:`Df.Harness.Analysis.OwnedPublisher.OwnedPublisher.__commit_locked()`
# @used-by :meth:`Df.Harness.Analysis.OwnedPublisher.OwnedPublisher.__write_new()`
# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.__commit_locked()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.prepare_package()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.record_review()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__save_executor_metadata()`
# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__write_candidate()`
# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.prepare()`
# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__write_artifacts()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_merkle_cached_single_reviewer_quorum_recognizes_approved_digests_and_storage_receipts()`
def write_immutable_bytes(path: Path, payload: bytes, *, diff_error: str='Immutable artifact differs') -> Path:
	return dfh_write_immutable_bytes(path, payload, diff_error=diff_error)
