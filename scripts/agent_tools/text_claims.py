# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Text.ClaimMapValidator import ClaimMapValidator
from Df.Harness.Text.ClaimRegistryStore import ClaimRegistryStore
from Df.Harness.lib.text_claims import dfh_claim_subset as subset, dfh_evidence_inputs as evidence_inputs, dfh_primary_numbers as primary_numbers, dfh_registry_path as registry_path, dfh_text_digest as digest, dfh_text_issue as _issue, dfh_text_nonempty as _nonempty
from .text_sections import content_blocks as blocks
# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.test_collect_claim_closure_and_save_registry_single_structural_pass()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_unrelated_registry_revision_and_target_do_not_invalidate_selected_history()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_a_self_authored_note_is_not_a_native_reassessment_of_changed_evidence()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_primary_revision_marks_all_transitive_dependents_stale_and_archives_old_bytes()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_registry_compare_and_swap_never_overwrites_manual_revision()`
# @used-by :meth:`test_text_workflow.TextWorkspaceCase.registry()`
def save_registry(root, candidate, *, expected_sha256=None, reference=None, reassessments=None):
	return ClaimRegistryStore(root, candidate, expected_sha256=expected_sha256, reference=reference, reassessments=reassessments).save()
# @used-by :meth:`test_text_workflow.TextMapTests.test_explicit_offer_can_be_nonfactual_without_a_registry()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_numeric_measurement_cannot_come_from_claim_wording_alone()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_stale_block_bytes_or_missing_coverage_fail()`
# @used-by :meth:`test_text_workflow.TextMapTests.test_substantive_paragraph_cannot_be_unmapped_or_unsourced()`
def validate_map(root, text, kind, manifest):
	return ClaimMapValidator(root, text, kind, manifest).validate()
