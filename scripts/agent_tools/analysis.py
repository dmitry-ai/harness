# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
from Df.Core.lib.sha256 import df_sha256
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Analysis.OwnedPublisher import OwnedPublisher
from Df.Harness.Analysis.Publisher import Publisher
from Df.Harness.Analysis.Renderer import Renderer, TITLES
from Df.Harness.Analysis.Saver import Saver
from Df.Harness.Analysis.Validator import SECTIONS, Validator
from .diagnostics import require_valid
from .storage import replace_bytes
# @used-by :func:`agent_tools.workflow.check_project()`
# @used-by :func:`validate_analysis()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_many_independent_errors_are_reported_with_fields_and_ids()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_no_anchor_exception_uses_an_observed_specific_section()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_no_counterevidence_needs_documented_review_and_real_sources()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_source_registry_and_escaped_pointers_resolve()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.valid_review_analysis()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_6395_relative_to_5395_is_185357_percent_not_20()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_arbitrary_intake_receipt_cannot_promote_own_note_or_attachment()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_calculation_requires_sourced_common_units_and_explicit_percent_result()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_causal_alternatives_and_recommendation_conditions_are_required()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_critical_severity_needs_impact_evidence()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_currency_cannot_be_borrowed_from_another_quantity()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_dependency_change_and_cycle_are_reported()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e7_contradictory_evidence_reuse_in_against_and_intake_only_counterevidence_cap()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e8_relational_comparison_and_modification_require_two_distinct_operands_with_verified_hashes()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_experiment_primary_uses_recorder_artifact_and_actual_method()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_html_markup_cannot_hide_a_sign_between_spans()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_json_amount_currency_pair_is_an_exact_quantity_locator()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_legacy_is_readable_but_cannot_be_newly_saved_or_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_limited_hypothesis_keeps_missing_browser_check_and_can_be_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_misconception_hypothesis_requires_alternatives_and_discriminating_check()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_primary_http_fact_accepts_and_renders_with_scope()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_referenced_primary_cannot_be_replaced_with_an_own_kb_quote()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_signed_quantity_cannot_be_replaced_with_its_positive_substring()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_unavailable_result_is_valid_with_explicit_gap()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_unverified_hypothesis_with_empty_against_caps_probability_at_75()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_documentation_requires_verified_anchor_or_genuine_no_anchor_section()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_verified_observation_rejects_ungrounded_numbers_in_essence()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_website_requires_valid_url_and_identity_basis()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_legacy_analysis_does_not_silently_clear_existing_risks()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_unknown_duplicate_and_unsupported_basis_cannot_be_published()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_malformed_evidence_fields_return_diagnostics_without_crashing()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_public_example_passes_structure_evidence_and_project_checks()`
# @used-by :mod:`agent_tools.analysis`
# @used-by :mod:`agent_tools.workflow`
def analysis_issues(value):
	return Validator(value).issues()
# @used-by :func:`agent_tools.operations._execute_collect()`
# @used-by :mod:`agent_tools.analysis`
def digest(data):
	return df_sha256(data)
# @used-by :mod:`agent_tools.analysis`
def iter_arguments(value):
	return Validator.iter_arguments(value)
# @used-by :func:`agent_tools.cli_domains._op_render_analysis()`
# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
# @used-by :func:`test_project_domain_drift._save_and_publish()`
# @used-by :func:`test_project_rename._seed_project_artifacts()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_legacy_is_readable_but_cannot_be_newly_saved_or_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_limited_hypothesis_keeps_missing_browser_check_and_can_be_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_save_checks_real_evidence_and_does_not_overwrite_invalid_candidate()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_explicit_website_is_published_and_reused_without_overwriting_card_or_metadata()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_new_analysis_cannot_finish_with_an_unpublished_website_card()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_website_and_red_flags_have_stable_order_and_preserve_manual_edits()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_both_risks_precede_technical_analysis_and_are_duplicated_in_card()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_repeated_render_preserves_new_user_notes_and_does_not_duplicate_block()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_resolved_risks_update_both_surfaces_and_keep_original_card_history()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_standalone_input_never_updates_project_card()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_public_example_passes_structure_evidence_and_project_checks()`
# @used-by :mod:`agent_tools.analysis`
def publish_analysis(source, target=None):
	return Publisher(source, target).publish()
# @used-by :func:`agent_tools.operations._execute_collect()`
# @used-by :func:`test_atomic_prepare_and_narrowed_reconcile_m7._init_review_ready_project()`
# @used-by :func:`test_contract_invariants._init_tracked_project()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_analysis_workflow.PublicationTests.test_interrupted_state_write_preserves_published_output_for_recovery()`
# @used-by :meth:`test_analysis_workflow.PublicationTests.test_repeat_render_updates_owned_file_and_archives_previous_bytes()`
# @used-by :meth:`test_analysis_workflow.PublicationTests.test_untracked_or_manually_edited_file_is_preserved_with_candidate()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_exact_quotes_code_and_source_copies_are_not_rewritten_or_rejected()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_publication_guard_keeps_previous_document_and_primary_json_intact()`
# @used-by :mod:`agent_tools.analysis`
# @used-by :mod:`agent_tools.knowledge`
# @used-by :mod:`agent_tools.workflow`
def publish_owned(target, content, *, source=None, history=True):
	return OwnedPublisher(target, content, source=source, history=history, replace_fn=replace_bytes).publish()
# @used-by :func:`test_atomic_prepare_and_narrowed_reconcile_m7._init_review_ready_project()`
# @used-by :func:`test_contract_invariants._init_tracked_project()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_source_registry_and_escaped_pointers_resolve()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_legacy_is_readable_but_cannot_be_newly_saved_or_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_primary_http_fact_accepts_and_renders_with_scope()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_documentation_requires_verified_anchor_or_genuine_no_anchor_section()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_analysis_links_causes_to_concerns_and_methods_to_causes()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_readable_links.ReadableProjectTests.test_analysis_sources_are_readable_while_quotes_keep_their_exact_bytes()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_each_risk_can_be_shown_alone_without_combination_warning()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_no_flags_does_not_create_warning_or_change_original_card()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_suspected_intermediary_is_not_reported_as_confirmed()`
# @used-by :mod:`agent_tools.analysis`
# @used-by :mod:`agent_tools.knowledge`
def render_analysis(value):
	return Renderer(value).render()
# @used-by :mod:`agent_tools.analysis`
def require_current_contract(value):
	Validator.require_current_contract(value)
# @used-by :func:`agent_tools.cli_domains._op_save_analysis()`
# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
# @used-by :func:`test_project_domain_drift._save_and_publish()`
# @used-by :func:`test_project_rename._seed_project_artifacts()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_arbitrary_intake_receipt_cannot_promote_own_note_or_attachment()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_html_markup_cannot_hide_a_sign_between_spans()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_legacy_is_readable_but_cannot_be_newly_saved_or_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_limited_hypothesis_keeps_missing_browser_check_and_can_be_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_signed_quantity_cannot_be_replaced_with_its_positive_substring()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_documentation_requires_verified_anchor_or_genuine_no_anchor_section()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_save_checks_real_evidence_and_does_not_overwrite_invalid_candidate()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_analysis_commit_requires_current_hash_and_preserves_history()`
# @used-by :mod:`agent_tools.analysis`
def save_analysis(root, candidate, expected_sha256=None):
	return Saver(root, candidate, expected_sha256).save()
# @used-by :mod:`agent_tools.analysis`
def source_uri(argument, registry):
	return Validator.source_uri(argument, registry)
# @used-by :mod:`agent_tools.analysis`
def valid_gap(gap):
	return isinstance(gap, dict) and gap.get('status') in ('not_found', 'unavailable') and isinstance(gap.get('reviewed_sources'), list) and bool(gap['reviewed_sources']) and all((isinstance(x, str) and x.strip() for x in gap['reviewed_sources'])) and isinstance(gap.get('limitations'), str) and bool(gap['limitations'].strip())
# @used-by :meth:`test_onboarding.EvidenceTests.test_analysis_links_causes_to_concerns_and_methods_to_causes()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_malformed_analysis_has_actionable_errors()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_missing_counterevidence_probability_or_documentation_anchor_is_rejected()`
# @used-by :mod:`agent_tools.analysis`
# @used-by :mod:`agent_tools.knowledge`
def validate_analysis(value):
	require_valid(analysis_issues(value))
__all__ = ['SECTIONS', 'TITLES', 'analysis_issues', 'digest', 'iter_arguments', 'publish_analysis', 'publish_owned', 'render_analysis', 'require_current_contract', 'save_analysis', 'source_uri', 'valid_gap', 'validate_analysis']