# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import hashlib
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# Return lowercase hex SHA-256 digest of raw bytes.
# @used-by :func:`Df.Harness.lib.admission_ops.dfh_admission_binding()`
# @used-by :func:`Df.Harness.lib.admission_ops.dfh_capture_admission()`
# @used-by :func:`Df.Harness.lib.admission_ops.dfh_verify_admission()`
# @used-by :func:`agent_tools.admission._digest()`
# @used-by :func:`agent_tools.analysis.digest()`
# @used-by :func:`agent_tools.intake._hash()`
# @used-by :func:`agent_tools.project_card._digest()`
# @used-by :func:`agent_tools.review.digest()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :func:`agent_tools.text_claims.digest()`
# @used-by :func:`df_sha256_file()`
# @used-by :func:`df_sha256_text()`
# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__check_snapshot()`
# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__load_state()`
# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.__load_base()`
# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.save()`
# @used-by :meth:`Df.Harness.Analysis.OwnedPublisher.OwnedPublisher.__commit_locked()`
# @used-by :meth:`Df.Harness.Analysis.OwnedPublisher.OwnedPublisher.__write_new()`
# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__extract_body()`
# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__sync_locked()`
# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__write_card()`
# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.__load_local()`
# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.__check_expected()`
# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.__commit_locked()`
# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.save()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.__append_aliases()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.__build_item()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.__ingest_trace()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.collector_artifact()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactVerifier.ArtifactVerifier.__verify_artifact()`
# @used-by :meth:`Df.Harness.Experiment.PlanPreparer.PlanPreparer.prepare_plan()`
# @used-by :meth:`Df.Harness.Experiment.PreregistrationAuditor.PreregistrationAuditor.__load_plan()`
# @used-by :meth:`Df.Harness.Experiment.ResultValidator.ResultValidator.__check_run()`
# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__write_run()`
# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.__replace_existing()`
# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.__write_result()`
# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__match_remaining_entry()`
# @used-by :meth:`Df.Harness.Project.Intake.CaptureCommitter.CaptureCommitter.__retire_entries()`
# @used-by :meth:`Df.Harness.Project.Intake.IntakePathGuard.IntakePathGuard.retired_path()`
# @used-by :meth:`Df.Harness.Project.Intake.ReceiptBuilder.ReceiptBuilder.__scan_existing()`
# @used-by :meth:`Df.Harness.Project.Intake.ReceiptBuilder.ReceiptBuilder.build()`
# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.__declared_attachments()`
# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.__verify_permanent_assets()`
# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.validate()`
# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.verify_snapshot()`
# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.__render_selected()`
# @used-by :meth:`Df.Harness.Review.ApprovalChecker.ApprovalChecker.__verify_package()`
# @used-by :meth:`Df.Harness.Review.ClaimMerkleHasher.ClaimMerkleHasher.compute_hash()`
# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.__resolve_claim()`
# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
# @used-by :meth:`Df.Harness.Review.NativeProofVerifier.NativeProofVerifier.verify()`
# @used-by :meth:`Df.Harness.Review.PackageEnvelopeReader.PackageEnvelopeReader.read_envelope()`
# @used-by :meth:`Df.Harness.Review.PackageEnvelopeReader.PackageEnvelopeReader.subject_digest()`
# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__write_candidate()`
# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.prepare()`
# @used-by :meth:`Df.Harness.Review.ReportAuthenticator.ReportAuthenticator.__auth_independent()`
# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.authorize()`
# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__load_and_check()`
# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__write_artifacts()`
# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.__resolve_steps()`
# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.record()`
# @used-by :meth:`Df.Harness.Workflow.HashCollector.HashCollector.file_hash()`
# @used-by :meth:`Df.Harness.Workflow.RequestAdopter.RequestAdopter.__saved_answers()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_sha256_json_io_and_time_helpers()`
def df_sha256(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()
# Return lowercase hex SHA-256 digest of a file's raw bytes.
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_sha256_json_io_and_time_helpers()`
def df_sha256_file(path: str | Path) -> str:
	return df_sha256(Path(path).read_bytes())
# Return lowercase hex SHA-256 digest of UTF-8 encoded text.
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :func:`agent_tools.snapshot.snapshot_draft()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_sha256_json_io_and_time_helpers()`
def df_sha256_text(text: str) -> str:
	return df_sha256(text.encode('utf-8'))