# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Text.IntegrityVerifier import IntegrityVerifier as TextIntegrityVerifier
from Df.Harness.Text.Workspace import Workspace as ClientTextWorkspace
from Df.Harness.lib.text_sections import TEXT_KINDS as KINDS
from Df.Harness.lib.text_workflow import APPLIED_CHECK_KEYS as _APPLIED_CHECK_KEYS, dfh_find_registered_text as _find_registered, dfh_gate_paths as gate_paths, dfh_gate_requests as gate_requests, dfh_has_linked_ancestor as _has_linked_ancestor, dfh_hash_or_none as _hash_or_none, dfh_immutable_text as _immutable, dfh_read_json_sig as _read, dfh_record_text_answer as record_answer, dfh_target_bytes as _target_bytes, dfh_text_folder as _folder, dfh_text_roots as _roots, dfh_write_candidate_output as write_candidate_output
# @used-by unused
def _applied_integrity(root, name, entry, *, require_live_proof=True):
	return TextIntegrityVerifier(ClientTextWorkspace(root)).applied_integrity(name, entry, require_live_proof=require_live_proof)
# @used-by unused
def _claim_snapshot(root, checked):
	return TextIntegrityVerifier(ClientTextWorkspace(root)).claim_snapshot(checked)
# @used-by unused
def _document(root, name):
	return ClientTextWorkspace(root).document(name)
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_proof_evidence_review_document_and_journal_changes_remain_conflicts()`
def _index(root):
	return ClientTextWorkspace(root).index()
# @used-by unused
def _reconciled_integrity(root, name, entry):
	return TextIntegrityVerifier(ClientTextWorkspace(root)).reconciled_integrity(name, entry)
# @used-by unused
def _save_index(root, value):
	ClientTextWorkspace(root).save_index(value)
# @used-by unused
def _verify_applied_successor(root, name, current, original):
	return TextIntegrityVerifier(ClientTextWorkspace(root)).verify_applied_successor(name, current, original)
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.fixture()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_explicit_reconciled_baseline_preserves_history_without_granting_publication()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_failed_semantic_admission_is_not_granted_by_a_later_valid_apply()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_historical_successor_lineage_preserves_history_when_later_reviewer_trace_is_unverified()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_later_legitimate_applied_revision_does_not_invalidate_old_answer()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_replaying_an_older_applied_target_is_not_a_later_legitimate_revision()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_exact_primary_quote_receipt_is_reused_without_network_and_apply_keeps_it()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_full_native_review_fixture_requires_and_preserves_source_assessments()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_later_failure_invalidates_apply_and_an_already_applied_gate()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_independent_routine_verdict_apply_and_exact_journal()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_map_change_does_not_inherit_an_old_check_approval()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_same_rejected_subject_cannot_be_reset_by_a_new_operation_path()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_significant_subject_needs_two_distinct_reviewers()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_changed_protected_file_is_reported_without_restore()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_manual_change_after_check_preserves_the_users_new_bytes()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_propose_creates_reviewable_candidate_without_writing_target()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_successful_mechanical_apply_has_a_receipt_and_preserves_original()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_target_indirection_created_after_capture_cannot_redirect_apply()`
def apply(root, reference):
	return ClientTextWorkspace(root).apply(reference)
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.reconcile_manual_baseline()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_historical_successor_lineage_preserves_history_when_later_reviewer_trace_is_unverified()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_later_legitimate_applied_revision_does_not_invalidate_old_answer()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_replaying_an_older_applied_target_is_not_a_later_legitimate_revision()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_same_rejected_subject_cannot_be_reset_by_a_new_operation_path()`
# @used-by :meth:`test_text_workflow.TextWorkspaceCase.start()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_external_journal_cannot_bypass_the_current_client_document_gate()`
def begin(root, spec):
	return ClientTextWorkspace(root, strict=True).begin(spec)
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.check_and_review()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.checked()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_full_native_review_fixture_requires_and_preserves_source_assessments()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_missing_map_is_an_invalid_result_instead_of_a_crash()`
# @used-by :meth:`test_text_integration.TextReviewTests.setUp()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_map_change_does_not_inherit_an_old_check_approval()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_same_rejected_subject_cannot_be_reset_by_a_new_operation_path()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_changed_primary_bytes_invalidate_an_existing_semantic_check()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_limited_claim_rejects_lazy_conditional_qualification()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_standalone_proposal_map_needs_no_five_analysis_stages()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_changed_protected_file_is_reported_without_restore()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_manual_change_after_check_preserves_the_users_new_bytes()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_propose_creates_reviewable_candidate_without_writing_target()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_successful_mechanical_apply_has_a_receipt_and_preserves_original()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_target_indirection_created_after_capture_cannot_redirect_apply()`
def check(root, ident, candidate, manifest=None, *, run_replay=False, replay_record=None, warning_dispositions=None, applied=False):
	return ClientTextWorkspace(root).check(ident, candidate, manifest, run_replay=run_replay, replay_record=replay_record, warning_dispositions=warning_dispositions, applied=applied)
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_aged_real_source_and_nested_semantic_approval_preserve_both_platforms()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_explicit_reconciled_baseline_preserves_history_without_granting_publication()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_failed_semantic_admission_is_not_granted_by_a_later_valid_apply()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_exact_primary_quote_receipt_is_reused_without_network_and_apply_keeps_it()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_later_failure_invalidates_apply_and_an_already_applied_gate()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_independent_routine_verdict_apply_and_exact_journal()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_direct_write_bypass_never_acquires_a_valid_receipt()`
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_successful_mechanical_apply_has_a_receipt_and_preserves_original()`
def gate(root, *, targets=None, response=None, publication=False, capture=False):
	return ClientTextWorkspace(root).gate(targets=targets, response=response, publication=publication, capture=capture)
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
def integrity_snapshot(root, entries):
	return TextIntegrityVerifier(ClientTextWorkspace(root)).snapshot(entries)
# @used-by :meth:`test_text_workflow.TextTransactionTests.test_successful_mechanical_apply_has_a_receipt_and_preserves_original()`
def operation(root, ident):
	return ClientTextWorkspace(root).operation(ident)
# @used-by unused
def operation_meta(root, ident):
	return ClientTextWorkspace(root).operation_meta(ident)
# @used-by unused
def read_check(root, reference):
	return ClientTextWorkspace(root).read_check(reference)
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_primary_byte_or_metadata_change_invalidates_a_previously_valid_check()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_changed_primary_bytes_invalidate_an_existing_semantic_check()`
def refresh_check(root, reference, *, applied=False):
	return ClientTextWorkspace(root).refresh_check(reference, applied=applied)
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_links_only_allows_url_presentation_but_preserves_crlf_and_anchor_words()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_renumber_scope_accepts_external_spacing_without_rebinding_its_number()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_section_scope_covers_group_headers_and_protects_part_title()`
# @used-by :meth:`test_text_workflow.TextMechanicalScopeTests.scope()`
# @used-by :meth:`test_text_workflow.TextMechanicalScopeTests.test_inspect_never_allows_even_one_word_change()`
def scope_issues(op, base, candidate):
	return ClientTextWorkspace.scope_issues(op, base, candidate)
# @used-by :func:`Df.Harness.lib.admission_ops.dfh_verify_admission()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
def verify_integrity(graph):
	if not isinstance(graph, dict) or 1 != graph.get('schema_version') or not isinstance(graph.get('root'), str) or not Path(graph['root']).is_absolute() or not isinstance(graph.get('targets'), list):
		raise ValueError('Invalid historical text integrity graph')
	return TextIntegrityVerifier(ClientTextWorkspace(graph['root'])).verify(graph)
