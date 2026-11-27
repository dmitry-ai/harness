# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Review.AddressedReviewResolver import AddressedReviewResolver
from Df.Harness.Review.BlindPredicateBuilder import BlindPredicateBuilder
from Df.Harness.Review.ClaimEvidenceCollector import ClaimEvidenceCollector
from Df.Harness.Review.ClaimMerkleHasher import ClaimMerkleHasher
from Df.Harness.Review.Classifier import Classifier as ReviewClassifier, TASK_FLAGS
from Df.Harness.Review.DispositionRecorder import DispositionRecorder
from Df.Harness.Review.InputReceiptBuilder import InputReceiptBuilder, REPORT_CONTRACT
from Df.Harness.Review.MerkleCacheUpdater import MerkleCacheUpdater
from Df.Harness.Review.MerkleDeltaCalculator import MerkleDeltaCalculator
from Df.Harness.Review.NativeProofVerifier import NativeProofVerifier
from Df.Harness.Review.PackageEnvelopeReader import PackageEnvelopeReader
from Df.Harness.Review.PackagePreparer import PackagePreparer
from Df.Harness.Review.PackageReader import PACKAGE_HANDLERS, PackageReader
from Df.Harness.Review.QuorumEvaluator import QuorumEvaluator as ReviewQuorumEvaluator
from Df.Harness.Review.ReportAuthenticator import ReportAuthenticator
from Df.Harness.Review.ReportParser import ReportParser
from Df.Harness.Review.ReportValidator import REVIEW_SCHEMA, ReportValidator as ReviewReportValidator, SCOPES
from Df.Harness.Review.ReviewAuthorizer import ReviewAuthorizer
from Df.Harness.Review.VerdictPreparer import VerdictPreparer
from Df.Harness.Review.VerdictRecorder import VerdictRecorder
from Df.Qa.lib.validation.check_strict import df_is_sne
from .research import inside, json_data
# @used-by :func:`_approved_digests()`
# @used-by :func:`approval_current()`
# @used-by :func:`authorize()`
# @used-by :func:`prepare()`
# @used-by :func:`read_package()`
# @used-by :func:`update_verified_claims_cache()`
# @used-by :mod:`agent_tools.review`
def _analysis(root):
	from .evidence import evidence_issues
	return PackageEnvelopeReader.load_analysis(root, evidence_issues_fn=evidence_issues)
# @used-by :func:`classification()`
# @used-by :func:`prepare()`
# @used-by :func:`read_package()`
# @used-by :mod:`agent_tools.review`
def _approved_digests(root, state, *, exclude_package=None):
	return ReviewQuorumEvaluator(root, state, analysis_fn=_analysis, package_reader=read_package, inside_fn=inside).approved_claim_digests(exclude_package=exclude_package)
# @used-by :func:`_claim_evidence_sources()`
# @used-by :mod:`agent_tools.review`
def _claim_evidence_pairs(claim_id: str, index: dict, evidence_inputs: dict | None=None, _visited: set | None=None) -> list[tuple[str, str]]:
	return ClaimEvidenceCollector(claim_id, index, evidence_inputs, _visited).pairs()
# @used-by :mod:`agent_tools.review`
def _claim_evidence_sources(claim_id: str, index: dict) -> list[str]:
	return [s for s, _ in _claim_evidence_pairs(claim_id, index, {})]
# @used-by :mod:`agent_tools.review`
def _package_handler(kind):
	return PackageReader.package_handler(kind)
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_workflow_gate_resolved()`
# @used-by :mod:`agent_tools.review`
def approval_current(root, state, approval):
	return ReviewQuorumEvaluator(root, state, analysis_fn=_analysis, package_reader=read_package, inside_fn=inside).approval_current(approval)
# @used-by :mod:`agent_tools.review`
def authenticate_report(root, package, package_path, data, source_payload, *, parent_id, reviewer_id, native_evidence=None, allow_self=True):
	return ReportAuthenticator(root, package, package_path, data, source_payload, parent_id=parent_id, reviewer_id=reviewer_id, native_evidence=native_evidence, allow_self=allow_self, inside_fn=inside).authenticate()
# @used-by :func:`Df.Harness.lib.blocked_report_ops._authorize_workflow_errors()`
# @used-by :func:`agent_tools.project_rename_verify.capture_pre_rename_snapshot()`
# @used-by :func:`agent_tools.project_rename_verify.verify_post_rename()`
# @used-by :func:`agent_tools.workflow.complete_stage()`
# @used-by :func:`agent_tools.workflow.record_current_answer()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__authorize_and_sync_workflow()`
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__run_review_stage()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.test_significant_prepare_review_defaults_to_falsifier_and_authorizes_single_auditor()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :meth:`test_issue44.TestIssue44.test_authorize_post_finalize_enforces_post_finalize_questions()`
# @used-by :meth:`test_issue44.TestIssue44.test_authorize_post_finalize_enforces_request_scoped_questions()`
# @used-by :meth:`test_issue44.TestIssue44.test_authorize_post_finalize_ignores_historical_questions()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_text_core_and_review_authorize_handle_metadata_prefixed_response()`
# @used-by :meth:`test_review_contract.ReviewContractTests.authorize()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_legacy_review_and_analysis_cannot_authorize_new_answer()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_authorize_deduplicates_evidence_issues_across_check_project()`
# @used-by :mod:`agent_tools.review`
def authorize(root, state, *, response=None, package_path=None, request_ids=None):
	from .workflow import check_project
	return ReviewAuthorizer(root, state, response=response, package_path=package_path, request_ids=request_ids, analysis_fn=_analysis, package_reader=read_package, update_cache_fn=update_verified_claims_cache, check_project_fn=check_project, inside_fn=inside).authorize()
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue47_merkle_cache_blind_predicates_and_falsifier_mode()`
# @used-by :mod:`agent_tools.review`
def build_blind_verification_predicates(manifest: list[dict], value: dict) -> list[dict]:
	return BlindPredicateBuilder(manifest, value).build()
# @used-by :mod:`agent_tools.review`
def claim_merkle_hash(claim_entry: dict, index: dict, evidence_inputs: dict) -> str:
	return ClaimMerkleHasher(claim_entry, index, evidence_inputs).compute_hash()
# @used-by :mod:`agent_tools.review`
def classification(root, state, spec, response, value, *, exclude_package=None):
	return ReviewClassifier(root, state, value, exclude_package=exclude_package, approved_fn=_approved_digests).classify(spec, response)
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue47_merkle_cache_blind_predicates_and_falsifier_mode()`
# @used-by :mod:`agent_tools.review`
def compute_claim_merkle_delta(root, manifest: list[dict], value: dict, evidence_inputs: dict) -> dict:
	return MerkleDeltaCalculator(root, manifest, value, evidence_inputs).compute()
# @used-by :func:`agent_tools.text_review.approval_integrity()`
# @used-by :func:`agent_tools.text_review.authorize()`
# @used-by :func:`agent_tools.text_review.prepare()`
# @used-by :func:`agent_tools.text_review.read_package()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_handwritten_empty_manifest_package_cannot_pass_record_review()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_handwritten_routine_package_cannot_bypass_computed_risk()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_merkle_cached_single_reviewer_quorum_recognizes_approved_digests_and_storage_receipts()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_package_handler_registry_dispatches_custom_kind()`
# @used-by :mod:`agent_tools.review`
def digest(payload):
	return df_sha256(payload)
# @used-by :func:`agent_tools.workflow.record_review_disposition()`
# @used-by :mod:`agent_tools.review`
def disposition(root, review_id, finding_id, status, basis, evidence, parent_id):
	return DispositionRecorder(root, review_id, finding_id, status, basis, evidence, parent_id, inside_fn=inside).record()
# @used-by :mod:`agent_tools.review`
def findings_closed(root, entry):
	return ReviewQuorumEvaluator(root, {'reviews': []}, inside_fn=inside).findings_closed(entry)
# @used-by :mod:`agent_tools.review`
def has_unhandled_verdicts(root, state, package, latest):
	return ReviewQuorumEvaluator(root, state, inside_fn=inside).has_unhandled_verdicts(package, latest)
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :func:`agent_tools.workflow.review_input()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_review_input_returns_neutral_report_contract_with_all_options()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_package_handler_registry_dispatches_custom_kind()`
# @used-by :meth:`test_review_target_claim_and_wait_m5.ReviewTargetClaimAndWaitM5Tests.test_review_input_and_validator_expose_verbatim_target_claim_rule_and_diff()`
# @used-by :mod:`agent_tools.review`
def input_receipt(root, package):
	return InputReceiptBuilder(root, package, package_reader=read_package, inside_fn=inside).build()
# @used-by :func:`agent_tools.text_review._source_reviews()`
# @used-by :func:`agent_tools.text_review.prepare()`
# @used-by :mod:`agent_tools.review`
def is_nonempty_text(value):
	return df_is_sne(value)
# @used-by :mod:`agent_tools.review`
def latest_for_subject(state, package):
	return ReviewQuorumEvaluator('.', state).latest_for_subject(package)
# @used-by :mod:`agent_tools.review`
def load_verified_claims_cache(root) -> dict:
	return MerkleDeltaCalculator.load_cache(root)
# @used-by :func:`agent_tools.text_review.approval_integrity()`
# @used-by :func:`agent_tools.text_review.authorize()`
# @used-by :mod:`agent_tools.review`
def parse_report_object(text):
	return ReportParser(text).parse()
# @used-by :func:`agent_tools.workflow.prepare_review()`
# @used-by :func:`test_finalized_project_contract._complete_review_and_finalize()`
# @used-by :mod:`agent_tools.review`
def prepare(root, parent_id, spec, response):
	return PackagePreparer(root, parent_id, spec, response, analysis_fn=_analysis, approved_fn=_approved_digests).prepare()
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :mod:`agent_tools.review`
def prepare_verdict_record(root, report, *, parent_id, reviewer_id, native_evidence=None, allow_self=True, expected_risk=None, package_reader=None, issue_checker=None, reviews_dir_fn=None, artifact_prefix_fn=None, diff_error='Immutable review artifact differs; preserve the original and create a new attempt'):
	reader = read_package if None is package_reader else package_reader
	return VerdictPreparer(root, report, parent_id=parent_id, reviewer_id=reviewer_id, native_evidence=native_evidence, allow_self=allow_self, expected_risk=expected_risk, package_reader=reader, issue_checker=issue_checker, reviews_dir_fn=reviews_dir_fn, artifact_prefix_fn=artifact_prefix_fn, diff_error=diff_error, inside_fn=inside).prepare()
# @used-by :mod:`agent_tools.review`
def quorum_satisfied(root, state, package, latest, eligible, *, allow_falsifier_or_cached=True) -> bool:
	return ReviewQuorumEvaluator(root, state).quorum_satisfied(package, latest, eligible, allow_falsifier_or_cached=allow_falsifier_or_cached)
# @used-by :func:`_approved_digests()`
# @used-by :func:`approval_current()`
# @used-by :func:`authorize()`
# @used-by :func:`input_receipt()`
# @used-by :func:`prepare_verdict_record()`
# @used-by :func:`record()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_handwritten_routine_package_cannot_bypass_computed_risk()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_package_handler_registry_dispatches_custom_kind()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_quorum_evaluator_selects_authorized_group_and_checks_approval_current()`
# @used-by :mod:`agent_tools.review`
def read_package(root, package, *, state=None, require_current=True):
	return PackageReader(root, package, state=state, require_current=require_current, analysis_fn=_analysis, approved_fn=_approved_digests, inside_fn=inside).read_package()
# @used-by :func:`agent_tools.text_review.read_package()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :mod:`agent_tools.review`
def read_package_envelope(root, reference, *, expected_kind=None, error_msg='Invalid immutable review package'):
	return PackageEnvelopeReader(root, reference, expected_kind=expected_kind, error_msg=error_msg, inside_fn=inside).read_envelope()
# @used-by :func:`agent_tools.workflow.record_review()`
# @used-by :func:`test_finalized_project_contract._complete_review_and_finalize()`
# @used-by :mod:`agent_tools.review`
def record(root, report, *, parent_id, reviewer_id, role='AA', native_evidence=None, risk=None):
	return VerdictRecorder(root, report, parent_id=parent_id, reviewer_id=reviewer_id, role=role, native_evidence=native_evidence, risk=risk, package_reader=read_package, inside_fn=inside).record()
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_package_handler_registry_dispatches_custom_kind()`
# @used-by :mod:`agent_tools.review`
# @used-by :mod:`agent_tools.text_review`
def register_package_handler(kind, *, package_reader, contract_factory=None):
	PackageReader.register_handler(kind, package_reader=package_reader, contract_factory=contract_factory)
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue47_merkle_cache_blind_predicates_and_falsifier_mode()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_audit_target_must_equal_the_analysis_claim_and_irrelevant_test_is_unsupported()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_review_package_rejects_ungrounded_numbers_in_response_excerpt_and_reviewer_report()`
# @used-by :meth:`test_review_contract_package_and_paths_m6.ReviewContractPackageAndPathsM6Tests.test_report_contract_and_validator_require_package_envelope_keys()`
# @used-by :meth:`test_review_target_claim_and_wait_m5.ReviewTargetClaimAndWaitM5Tests.test_review_input_and_validator_expose_verbatim_target_claim_rule_and_diff()`
# @used-by :mod:`agent_tools.review`
def report_issues(data, package, *, candidate=None, require_envelope=False):
	return ReviewReportValidator(package, candidate=candidate, require_envelope=require_envelope).validate(data)
# @used-by :mod:`agent_tools.review`
def request_snapshot(state):
	return [{'id': item['id'], 'text': item['text']} for item in state['requests']]
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :mod:`agent_tools.review`
def resolve_addressed_reviews(root, data, package, independent, existing_reviews):
	return AddressedReviewResolver(root, data, package, independent, existing_reviews).resolve_addressed()
# @used-by :mod:`agent_tools.review`
def significant_findings(root, state, subject):
	return ReviewQuorumEvaluator(root, state).significant_findings(subject)
# @used-by :func:`agent_tools.text_review.prepare()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :mod:`agent_tools.review`
def subject_digest(package):
	return PackageEnvelopeReader.subject_digest(package)
# @used-by :func:`authorize()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue47_merkle_cache_blind_predicates_and_falsifier_mode()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_merkle_cached_single_reviewer_quorum_recognizes_approved_digests_and_storage_receipts()`
# @used-by :mod:`agent_tools.review`
def update_verified_claims_cache(root, package: dict, value: dict | None=None) -> dict:
	return MerkleCacheUpdater(root, package, value, analysis_fn=_analysis).update()
# @used-by :func:`agent_tools.text_review.approval_integrity()`
# @used-by :func:`agent_tools.text_review.authorize()`
# @used-by :mod:`agent_tools.review`
def verify_entry_native_proof(root, entry, *, error_msg='Saved report differs from the actual native authored final response'):
	return NativeProofVerifier(root, entry, error_msg=error_msg).verify()
_findings_closed = findings_closed
_latest_for_subject = latest_for_subject
_report_object = parse_report_object
_text = is_nonempty_text
_unhandled_verdicts = has_unhandled_verdicts
__all__ = ['PACKAGE_HANDLERS', 'REPORT_CONTRACT', 'REVIEW_SCHEMA', 'ReviewClassifier', 'ReviewQuorumEvaluator', 'ReviewReportValidator', 'SCOPES', 'TASK_FLAGS', '_analysis', '_approved_digests', '_claim_evidence_pairs', '_claim_evidence_sources', '_findings_closed', '_latest_for_subject', '_package_handler', '_report_object', '_text', '_unhandled_verdicts', 'approval_current', 'authenticate_report', 'authorize', 'build_blind_verification_predicates', 'claim_merkle_hash', 'classification', 'compute_claim_merkle_delta', 'digest', 'disposition', 'findings_closed', 'has_unhandled_verdicts', 'input_receipt', 'is_nonempty_text', 'latest_for_subject', 'load_verified_claims_cache', 'parse_report_object', 'prepare', 'prepare_verdict_record', 'quorum_satisfied', 'read_package', 'read_package_envelope', 'record', 'register_package_handler', 'report_issues', 'request_snapshot', 'resolve_addressed_reviews', 'significant_findings', 'subject_digest', 'update_verified_claims_cache', 'verify_entry_native_proof']
