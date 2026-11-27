# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.state import df_is_windows
# 2026-10-30
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
# 2026-11-13
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
# @used-by :func:`replace_bytes()`
def _replace_with_retry(temp: Path, path: Path):
	for attempt in range(10):
		try:
			os.replace(temp, path)
			break
		except PermissionError:
			if 9 == attempt:
				raise
			time.sleep(0.025)
# 2026-11-24
# "Deduplicate historical admission fixtures and guard optional temp fsync":
# https://github.com/dmitry-ai/harness/issues/177
# @used-by :func:`_stage_atomic_write()`
def _should_skip_fsync(path: Path) -> bool:
	r = False
	if '1' == os.environ.get('HARNESS_TEST_NO_FSYNC'):
		try:
			r = path.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
		except (OSError, ValueError):
			r = False
	return r
# @used-by :func:`create_bytes()`
# @used-by :func:`replace_bytes()`
def _stage_atomic_write(path: Path, data: bytes, commit):
	fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
	temp = Path(name)
	try:
		with os.fdopen(fd, 'wb') as stream:
			stream.write(data)
			stream.flush()
			if not _should_skip_fsync(path):
				os.fsync(stream.fileno())
		commit(temp, path)
	finally:
		temp.unlink(missing_ok=True)
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# @used-by :func:`agent_tools.admission.capture()`
# @used-by :func:`agent_tools.cleanup.restore_antigravity()`
# @used-by :func:`agent_tools.cleanup_audit._create_unique_log_file()`
# @used-by :func:`agent_tools.configuration.store_content_backup()`
# @used-by :func:`agent_tools.intake.commit_capture()`
# @used-by :func:`agent_tools.journal._publish()`
# @used-by :func:`agent_tools.journal.record_answer()`
# @used-by :func:`agent_tools.journal.record_step()`
# @used-by :func:`agent_tools.native_profiles._apply()`
# @used-by :func:`agent_tools.platforms.antigravity.register_antigravity_project()`
# @used-by :func:`agent_tools.research._write_cached_extraction()`
# @used-by :func:`agent_tools.research.collect()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.text_claims.save_registry()`
# @used-by :func:`agent_tools.text_workflow.write_candidate_output()`
# @used-by :func:`write_immutable_bytes()`
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
	# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
	_stage_atomic_write(Path(path), data, os.rename if df_is_windows() else os.link)
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# @used-by :func:`agent_tools.admission._resolve_proof_file()`
# @used-by :func:`agent_tools.admission.capture()`
# @used-by :func:`agent_tools.cli_common.load_operation_input()`
# @used-by :func:`agent_tools.cli_common.verify_scratch_input_path()`
# @used-by :func:`agent_tools.configuration._publish()`
# @used-by :func:`agent_tools.configuration.load_project_receipt()`
# @used-by :func:`agent_tools.journal.upgrade_journal()`
# @used-by :func:`agent_tools.native_profiles._apply()`
# @used-by :func:`agent_tools.native_profiles._backup()`
# @used-by :func:`agent_tools.native_profiles._role_config()`
# @used-by :func:`agent_tools.native_profiles._state_path()`
# @used-by :func:`agent_tools.native_profiles.build_shared_native()`
# @used-by :func:`agent_tools.native_profiles.install_native_profiles()`
# @used-by :func:`agent_tools.native_profiles.retire_owned_project_projections()`
# @used-by :func:`agent_tools.runtime_launchers._default_store_dir()`
# @used-by :func:`agent_tools.runtime_snapshot.runtime_store_dir()`
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
	from .path_registry import project_paths
	return project_paths(Path(path), exact_root=exact_root).data_dir
# 2026-11-24
# "Accelerate project_paths and overlay link resolution with fast-path caching":
# https://github.com/dmitry-ai/harness/issues/174
# @used-by :func:`agent_tools.journal._raw_state_dir()`
def journal_data_dir_for(eff: Path) -> Path:
	from .path_cache import resolve_journal_data_dir
	return resolve_journal_data_dir(Path(eff))
# 2026-11-14
# "Decompose experiments.py into ExperimentPlanStore, BrowserTraceInspector, and ExperimentRunValidator classes and unify raw_decode JSON object scanning":
# https://github.com/dmitry-ai/harness/issues/72
# @used-by :func:`agent_tools.issues.service_helpers._decode_gh_stdout()`
# @used-by :func:`agent_tools.platforms.codex._json_objects()`
# @used-by :meth:`Df.Harness.Experiment.NativeGeoExtractor.NativeGeoExtractor.extract_country()`
# @used-by :meth:`Df.Harness.Experiment.PreregistrationAuditor.PreregistrationAuditor.__is_plan_commit()`
def iter_embedded_json_objects(value, *, parse_root: bool=True, recursive: bool=True):
	if isinstance(value, dict):
		yield value
		if recursive:
			for child in value.values():
				yield from iter_embedded_json_objects(child, parse_root=parse_root, recursive=recursive)
	elif isinstance(value, list):
		for child in value:
			yield from iter_embedded_json_objects(child, parse_root=parse_root, recursive=recursive)
	elif isinstance(value, str):
		parsed, loaded = (None, False)
		if parse_root:
			try:
				parsed = json.loads(value)
				loaded = True
			except ValueError:
				loaded = False
		if loaded:
			if not isinstance(parsed, str):
				yield from iter_embedded_json_objects(parsed, parse_root=parse_root, recursive=recursive)
		else:
			decoder, start = (json.JSONDecoder(), 0)
			while 0 <= (start := value.find('{', start)):
				try:
					item, size = decoder.raw_decode(value[start:])
				except ValueError:
					start += 1
				else:
					yield from iter_embedded_json_objects(item, parse_root=parse_root, recursive=recursive)
					start += size
# 2026-10-11
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-03
# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
# https://github.com/dmitry-ai/harness/issues/41
# 2026-11-23
# "Eliminate wall-clock race in context.generate and pre-lock flush race in storage.locked":
# https://github.com/dmitry-ai/harness/issues/158
# @used-by :func:`agent_tools.cleanup.remove_antigravity()`
# @used-by :func:`agent_tools.cleanup.restore_antigravity()`
# @used-by :func:`agent_tools.completion._persist_turn_recovery()`
# @used-by :func:`agent_tools.completion._prepare_once()`
# @used-by :func:`agent_tools.completion.begin()`
# @used-by :func:`agent_tools.completion.handoff_launcher_turn()`
# @used-by :func:`agent_tools.completion.ratchet_ok()`
# @used-by :func:`agent_tools.completion.recover_checkpoint()`
# @used-by :func:`agent_tools.completion.similar_project_exempt()`
# @used-by :func:`agent_tools.configuration._publish()`
# @used-by :func:`agent_tools.journal.record_answer()`
# @used-by :func:`agent_tools.journal.record_step()`
# @used-by :func:`agent_tools.journal.recover_step()`
# @used-by :func:`agent_tools.journal.release_turn_steps()`
# @used-by :func:`agent_tools.journal.reserve_turn_steps()`
# @used-by :func:`agent_tools.journal.upgrade_journal()`
# @used-by :func:`agent_tools.landing_lease._try_acquire_once()`
# @used-by :func:`agent_tools.landing_lease._unqueue_owner()`
# @used-by :func:`agent_tools.landing_lease.release_lease()`
# @used-by :func:`agent_tools.native_profiles.build_shared_native()`
# @used-by :func:`agent_tools.native_profiles.install_native_profiles()`
# @used-by :func:`agent_tools.native_profiles.retire_owned_project_projections()`
# @used-by :func:`agent_tools.platforms.antigravity.register_antigravity_project()`
# @used-by :func:`agent_tools.reconcile_helpers._trim_narrowed_reservation()`
# @used-by :func:`agent_tools.research.collect()`
# @used-by :func:`agent_tools.research.observed_use()`
# @used-by :func:`agent_tools.runtime_snapshot.promote_runtime_snapshot()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.stop_emergency_capture.maybe_emergency_capture_journal()`
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
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner._apply_removal()`
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.run()`
# @used-by :meth:`agent_tools.completion.TurnJournalReconciler.run()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._update_single_turn_locked()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.apply()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.begin()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.verify()`
# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_locked_concurrent_fresh_files_succeed_without_permission_error()`
# @used-by :meth:`test_context_and_storage_determinism.ContextAndStorageDeterminismTests.test_locked_create_on_held_zero_byte_lock_waits_without_permission_error()`
# @used-by :meth:`test_parallel_runner.ParallelRunnerTests.test_storage_locked_concurrent_threads_no_permission_error()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_waiting_for_writer_lock_does_not_allow_a_stale_ready_result()`
@contextmanager
def locked(path: Path, timeout: float=15, *, create=True):
	if create:
		path.parent.mkdir(parents=True, exist_ok=True)
	with path.open('a+b' if create else 'r+b') as stream:
		deadline = time.monotonic() + timeout
		while True:
			try:
				stream.seek(0)
				# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
				if df_is_windows():
					import msvcrt
					msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
				else:
					import fcntl
					fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
				break
			except OSError:
				if time.monotonic() >= deadline:
					raise TimeoutError(f'Lock busy: {path}')
				time.sleep(0.05)
		try:
			yield
		finally:
			stream.seek(0)
			# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
			if df_is_windows():
				msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
			else:
				fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
# 2026-11-13
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
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
	target = Path(path)
	raw = target.read_bytes()
	value = json.loads(raw.decode('utf-8-sig'))
	sha = hashlib.sha256(raw).hexdigest()
	expected = sha if stem_match else sha + suffix
	actual = target.stem if stem_match else target.name
	if not isinstance(value, dict) or actual != expected:
		raise ValueError(error_msg)
	return (raw, value)
# @used-by :func:`agent_tools.analysis.publish_owned()`
# @used-by :func:`agent_tools.cleanup._finish_pending()`
# @used-by :func:`agent_tools.cleanup.remove_antigravity()`
# @used-by :func:`agent_tools.cleanup.restore_antigravity()`
# @used-by :func:`agent_tools.completion._persist_turn_recovery()`
# @used-by :func:`agent_tools.completion._write_compaction_index_file()`
# @used-by :func:`agent_tools.completion.ratchet_ok()`
# @used-by :func:`agent_tools.completion.recover_checkpoint()`
# @used-by :func:`agent_tools.completion.similar_project_exempt()`
# @used-by :func:`agent_tools.configuration._publish()`
# @used-by :func:`agent_tools.git_ignore._append_exclude_pattern()`
# @used-by :func:`agent_tools.git_ignore._write_verified_ignore()`
# @used-by :func:`agent_tools.journal._rewrite_journal_readme()`
# @used-by :func:`agent_tools.journal._sync_overlay_journal_slot()`
# @used-by :func:`agent_tools.journal._write_turn_reservations()`
# @used-by :func:`agent_tools.journal.record_answer()`
# @used-by :func:`agent_tools.journal_pending_index._write_index_doc()`
# @used-by :func:`agent_tools.journal_pending_index.persist_turn_state()`
# @used-by :func:`agent_tools.landing_lease._save_state()`
# @used-by :func:`agent_tools.native_profiles._apply()`
# @used-by :func:`agent_tools.native_profiles._rollback()`
# @used-by :func:`agent_tools.platforms.antigravity.register_antigravity_project()`
# @used-by :func:`agent_tools.research._write_cached_extraction()`
# @used-by :func:`agent_tools.research.collect()`
# @used-by :func:`agent_tools.research.observed_use()`
# @used-by :func:`agent_tools.runtime_snapshot._activate_release()`
# @used-by :func:`agent_tools.runtime_snapshot._deploy_git_hooks()`
# @used-by :func:`agent_tools.runtime_snapshot._promote_locked()`
# @used-by :func:`agent_tools.shadow_replay_command.persist_shadow_replay_receipt()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.stop_hook_guard._save_guard()`
# @used-by :func:`agent_tools.text_claims.save_registry()`
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :func:`agent_tools.text_sources._attempt()`
# @used-by :func:`agent_tools.text_workflow.write_candidate_output()`
# @used-by :func:`agent_tools.trace_event_cache._save_disk_index()`
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
	target = Path(path)
	same = False
	try:
		same = target.read_bytes() == data
	except FileNotFoundError:
		pass
	if not same:
		target.parent.mkdir(parents=True, exist_ok=True)
		_stage_atomic_write(target, data, _replace_with_retry)
# @used-by :func:`agent_tools.completion._conflict()`
# @used-by :func:`agent_tools.platforms.trace_common.persist_review_proof()`
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
	target = Path(path)
	target.parent.mkdir(parents=True, exist_ok=True)
	if target.exists():
		if target.read_bytes() != payload:
			raise ValueError(diff_error)
	else:
		try:
			create_bytes(target, payload)
		except FileExistsError:
			if target.read_bytes() != payload:
				raise ValueError(diff_error)
	return target
