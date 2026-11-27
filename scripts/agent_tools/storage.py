# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import os
import tempfile
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.lib.storage import dfh_create_bytes, dfh_data_dir_for, dfh_iter_embedded_json_objects, dfh_journal_data_dir_for, dfh_locked, dfh_read_addressed_json, dfh_replace_bytes, dfh_write_immutable_bytes
# @used-by :func:`agent_tools.analysis.save_analysis()`
# @used-by :func:`agent_tools.cleanup.restore_antigravity()`
# @used-by :func:`agent_tools.intake.commit_capture()`
# @used-by :func:`agent_tools.journal._publish()`
# @used-by :func:`agent_tools.journal.record_answer()`
# @used-by :func:`agent_tools.journal.record_step()`
# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
# @used-by :func:`agent_tools.knowledge.create_once()`
# @used-by :func:`agent_tools.knowledge.populate_agent_kb()`
# @used-by :func:`agent_tools.native_profiles._facade_ops()`
# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
# @used-by :func:`agent_tools.research._write_cached_extraction()`
# @used-by :func:`agent_tools.research.collect()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.text_claims.save_registry()`
# @used-by :func:`agent_tools.text_workflow.write_candidate_output()`
# @used-by :func:`agent_tools.upwork_extract.download_attachment()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`agent_tools.experiments.ExperimentPlanStore.prepare()`
# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.record()`
# @used-by :meth:`agent_tools.knowledge.AttachmentInventory._register_bytes()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.apply()`
# @used-by :meth:`test_agent_tools.JournalTests.test_failed_second_write_recovers_with_token()`
# @used-by :meth:`test_agent_tools.JournalTests.test_recovery_does_not_overwrite_conflict()`
# @used-by :meth:`test_intake.IntakeTests.test_copy_failure_preserves_all_staging_and_retry_reuses_objects()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_atomic_create_does_not_leave_a_partial_final_file()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_group_crash_reserves_all_numbers_and_preserves_previous_context()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_valid_dom_capture_identity_can_resolve_the_http_channel_failure()`
def create_bytes(path: Path, data: bytes):
	dfh_create_bytes(path, data)
# @used-by :func:`agent_tools.context.generate()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.text_core.find_bans()`
# @used-by :func:`agent_tools.text_workflow.write_candidate_output()`
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
# @used-by :meth:`agent_tools.experiments.BrowserTraceInspector.native_geolocation()`
# @used-by :meth:`agent_tools.experiments.ExperimentPlanStore._is_plan_commit()`
def iter_embedded_json_objects(value, *, parse_root: bool=True, recursive: bool=True):
	return dfh_iter_embedded_json_objects(value, parse_root=parse_root, recursive=recursive)
# @used-by unused
def journal_data_dir_for(eff: Path) -> Path:
	return dfh_journal_data_dir_for(eff)
# @used-by :func:`agent_tools.analysis.publish_owned()`
# @used-by :func:`agent_tools.analysis.save_analysis()`
# @used-by :func:`agent_tools.analysis_merge.save_merged_analysis()`
# @used-by :func:`agent_tools.arch.review_store._persist_review_index()`
# @used-by :func:`agent_tools.arch.review_store._register_package_index()`
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :func:`agent_tools.context.generate()`
# @used-by :func:`agent_tools.intake.commit_capture()`
# @used-by :func:`agent_tools.landing_lease._try_acquire_once()`
# @used-by :func:`agent_tools.landing_lease._unqueue_owner()`
# @used-by :func:`agent_tools.landing_lease.release_lease()`
# @used-by :func:`agent_tools.metrics._save_executor_metadata()`
# @used-by :func:`agent_tools.project_card.sync_block()`
# @used-by :func:`agent_tools.project_rename._sync_antigravity_native_files()`
# @used-by :func:`agent_tools.project_rename._update_projects_index()`
# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
# @used-by :func:`agent_tools.registration._begin()`
# @used-by :func:`agent_tools.registration.save_registration()`
# @used-by :func:`agent_tools.research.collect()`
# @used-by :func:`agent_tools.research.observed_use()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.tdd.mechanical.record_mechanical_exemption()`
# @used-by :func:`agent_tools.text_browser._endpoint_lock()`
# @used-by :func:`agent_tools.text_claims.save_registry()`
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :func:`agent_tools.text_sources._attempt()`
# @used-by :func:`agent_tools.text_workflow.write_candidate_output()`
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
# @used-by :func:`agent_tools.worker_semaphore._try_reserve_once()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._update_single_turn_locked()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.apply()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.begin()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.verify()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.update()`
# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_locked_concurrent_fresh_files_succeed_without_permission_error()`
# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_locked_create_on_held_zero_byte_lock_waits_without_permission_error()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_storage_locked_concurrent_threads_no_permission_error()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_waiting_for_writer_lock_does_not_allow_a_stale_ready_result()`
def locked(path: Path, timeout: float=15, *, create=True):
	return dfh_locked(path, timeout=timeout, create=create)
# @used-by :func:`agent_tools.review.read_package()`
# @used-by :func:`agent_tools.review.read_package_envelope()`
# @used-by :func:`agent_tools.text_sources._evaluate()`
# @used-by :func:`agent_tools.text_sources.read_source_check()`
# @used-by :func:`agent_tools.text_sources.source_integrity()`
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
# @used-by :func:`agent_tools.analysis.save_analysis()`
# @used-by :func:`agent_tools.analysis_merge.save_merged_analysis()`
# @used-by :func:`agent_tools.arch.review_store._persist_review_index()`
# @used-by :func:`agent_tools.arch.review_store._register_package_index()`
# @used-by :func:`agent_tools.cleanup._finish_pending()`
# @used-by :func:`agent_tools.cleanup.remove_antigravity()`
# @used-by :func:`agent_tools.cleanup.restore_antigravity()`
# @used-by :func:`agent_tools.context.generate()`
# @used-by :func:`agent_tools.git_ignore._append_exclude_pattern()`
# @used-by :func:`agent_tools.git_ignore._write_verified_ignore()`
# @used-by :func:`agent_tools.intake.commit_capture()`
# @used-by :func:`agent_tools.knowledge._load_media_descriptions()`
# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
# @used-by :func:`agent_tools.knowledge.sync_project_attachments_and_kb()`
# @used-by :func:`agent_tools.landing_lease._save_state()`
# @used-by :func:`agent_tools.metrics._save_executor_metadata()`
# @used-by :func:`agent_tools.native_profiles._facade_ops()`
# @used-by :func:`agent_tools.parallel_runner._save_timings()`
# @used-by :func:`agent_tools.project_card.sync_block()`
# @used-by :func:`agent_tools.project_rename._restore_file_backups()`
# @used-by :func:`agent_tools.project_rename._sync_antigravity_native_files()`
# @used-by :func:`agent_tools.project_rename._update_projects_index()`
# @used-by :func:`agent_tools.project_rename_state._rewrite_json_file()`
# @used-by :func:`agent_tools.project_rename_state._update_folder_rule()`
# @used-by :func:`agent_tools.project_rename_state._update_project_json()`
# @used-by :func:`agent_tools.project_rename_state.rewrite_launcher_handoffs()`
# @used-by :func:`agent_tools.project_rename_state.rewrite_project_internal_state()`
# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
# @used-by :func:`agent_tools.registration._write()`
# @used-by :func:`agent_tools.research._write_cached_extraction()`
# @used-by :func:`agent_tools.research.collect()`
# @used-by :func:`agent_tools.research.observed_use()`
# @used-by :func:`agent_tools.review.update_verified_claims_cache()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.tdd.mechanical.record_mechanical_exemption()`
# @used-by :func:`agent_tools.text_claims.save_registry()`
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :func:`agent_tools.text_sources._attempt()`
# @used-by :func:`agent_tools.text_workflow.write_candidate_output()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
# @used-by :func:`agent_tools.worker_semaphore._try_reserve_once()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._update_single_turn_locked()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.persist_issue_evidence()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.persist_repo_transfer_evidence()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.apply()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.save_index()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.update()`
# @used-by :meth:`test_analysis_workflow.PublicationTests.test_interrupted_state_write_preserves_published_output_for_recovery()`
# @used-by :meth:`test_cleanup.CleanupTests.test_folders_publication_failure_after_unlink_recovers_without_native_file()`
# @used-by :meth:`test_storage_fsync_guard.StorageFsyncGuardTests.test_fsync_runs_by_default_and_when_env_is_zero()`
# @used-by :meth:`test_storage_fsync_guard.StorageFsyncGuardTests.test_fsync_skipped_inside_tempdir_when_env_is_one()`
# @used-by :meth:`test_storage_fsync_guard.StorageFsyncGuardTests.test_fsync_still_runs_outside_tempdir_even_when_env_is_one()`
# @used-by :meth:`test_turn_completion.WatcherLifecycleTests.test_equal_byte_replacement_does_not_create_temporary_files_or_touch_mtime()`
def replace_bytes(path: Path, data: bytes):
	dfh_replace_bytes(path, data)
# @used-by :func:`agent_tools.analysis.publish_owned()`
# @used-by :func:`agent_tools.analysis.save_analysis()`
# @used-by :func:`agent_tools.arch.review_store.prepare_arch_package()`
# @used-by :func:`agent_tools.arch.review_store.record_arch_review()`
# @used-by :func:`agent_tools.metrics._save_executor_metadata()`
# @used-by :func:`agent_tools.review._immutable()`
# @used-by :func:`agent_tools.review.prepare_verdict_record()`
# @used-by :func:`agent_tools.text_browser.save_cdp_identity()`
# @used-by :func:`agent_tools.text_review.prepare()`
# @used-by :func:`agent_tools.text_sources.probe_links()`
# @used-by :func:`agent_tools.text_sources.save_source_check()`
# @used-by :func:`agent_tools.text_workflow._immutable()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_merkle_cached_single_reviewer_quorum_recognizes_approved_digests_and_storage_receipts()`
def write_immutable_bytes(path: Path, payload: bytes, *, diff_error: str='Immutable artifact differs') -> Path:
	return dfh_write_immutable_bytes(path, payload, diff_error=diff_error)
