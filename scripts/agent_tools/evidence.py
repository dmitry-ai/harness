# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Analysis.EvidenceAuditor import EvidenceAuditor
from Df.Harness.Analysis.HtmlQuoteVerifier import HtmlQuoteVerifier
from Df.Harness.Analysis.JsonPointer import JsonPointer
from Df.Harness.Analysis.LocalSourceResolver import LocalSourceResolver
from Df.Harness.Analysis.SavedQuoteVerifier import SavedQuoteVerifier
from Df.Harness.Analysis.SavedSourceLoader import SavedSourceLoader
from . import evidence_loader
from .research import inside
# @used-by unused
def contains_quote(text, quote, mode='exact'):
	if 'exact' == mode:
		r = quote in text
	elif 'whitespace' != mode:
		raise ValueError('quote_match must be exact or whitespace')
	else:
		r = ' '.join(quote.split()) in ' '.join(text.split())
	return r
# @used-by :func:`agent_tools.review._analysis()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor._analysis_card_issues()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_anchored_quote_from_another_section_is_rejected()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_content_addressed_primary_evidence_tampering_is_detected()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_existing_heading_or_ancestor_anchor_is_required()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_local_markdown_quote_must_belong_to_the_linked_section()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_no_anchor_exception_uses_an_observed_specific_section()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_no_counterevidence_needs_documented_review_and_real_sources()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_quote_from_another_json_field_is_rejected()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_source_registry_and_escaped_pointers_resolve()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.valid_review_analysis()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_6395_relative_to_5395_is_185357_percent_not_20()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_agent_site_hypothesis_in_intake_manifest_is_not_primary()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_arbitrary_intake_receipt_cannot_promote_own_note_or_attachment()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_calculation_operand_must_match_its_own_primary_quote()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_calculation_requires_sourced_common_units_and_explicit_percent_result()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_currency_cannot_be_borrowed_from_another_quantity()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e1_and_e2_sitemap_alone_and_unobserved_sample_urls_are_rejected()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e3_network_error_classification_and_unverified_dns_claim_rejection()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e4_site_wide_schema_absence_requires_multi_page_or_product_template_sample()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e8_relational_comparison_and_modification_require_two_distinct_operands_with_verified_hashes()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_experiment_primary_uses_recorder_artifact_and_actual_method()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_explicit_text_locator_does_not_cover_another_part_of_page()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_full_real_intake_receipt_binds_source_to_snapshot_and_rejects_relabelled_note()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_html_markup_cannot_hide_a_sign_between_spans()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_http_does_not_establish_click_currency_ip_or_admin()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_json_amount_currency_pair_is_an_exact_quantity_locator()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_limited_hypothesis_keeps_missing_browser_check_and_can_be_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_m1_and_m2_html_wrapper_anchors_and_markdown_explicit_heading_ids_in_evidence_contract()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_malformed_properties_and_dependency_keep_field_diagnostics_in_cli()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_missing_or_revised_primary_hash_is_rejected()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_own_prya_kb_note_in_evidence_is_not_a_primary_observation()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_primary_http_fact_accepts_and_renders_with_scope()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_registered_intake_and_attachment_are_primary_but_quote_must_match_locator()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_signed_quantity_cannot_be_replaced_with_its_positive_substring()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_supported_signed_quantities_preserve_decimal_value_and_units()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_unavailable_result_is_valid_with_explicit_gap()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_documentation_requires_verified_anchor_or_genuine_no_anchor_section()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_malformed_evidence_fields_return_diagnostics_without_crashing()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_public_example_passes_structure_evidence_and_project_checks()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_remote_json_pointer_checks_only_the_target_field()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_authorize_deduplicates_evidence_issues_across_check_project()`
def evidence_issues(root, value, *, skip_structural=False):
	return EvidenceAuditor(root, value, skip_structural=skip_structural).issues()
# @used-by :func:`agent_tools.text_claims.evidence_inputs()`
# @used-by :func:`agent_tools.text_sources._evaluate()`
def local_file(root, reference):
	return LocalSourceResolver(root, reference).resolve()
# @used-by :func:`source_reference()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_source_registry_and_escaped_pointers_resolve()`
def pointer(*parts):
	return JsonPointer.render_pointer(*parts)
# @used-by :func:`agent_tools.completion._response_link_issues()`
# @used-by :func:`agent_tools.experiments._select_raw()`
# @used-by :func:`agent_tools.links.validate_file()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.__validate_doc_or_json_anchor()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_source_registry_and_escaped_pointers_resolve()`
def resolve_pointer(value, fragment, *, decode_uri: bool=True):
	return JsonPointer(value, fragment, decode_uri=decode_uri).resolve()
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_m1_and_m2_html_wrapper_anchors_and_markdown_explicit_heading_ids_in_evidence_contract()`
def saved_source(root, source, observation=None, *, need_sections=True):
	return SavedSourceLoader(root, source, observation, need_sections=need_sections, extract_fn=evidence_loader.extract_bytes).load()
# @used-by :func:`agent_tools.cli_domains._op_source_ref()`
def source_reference(root, file, parts=()):
	from .path_registry import project_paths
	kb_dir = project_paths(root, exact_root=True).kb_dir.resolve()
	target = inside(kb_dir, file)
	return target.relative_to(kb_dir).as_posix() + ('#' + pointer(*parts) if parts else '')
# @used-by unused
def verify_html_quote_scope(saved, quote, mode='exact', *, documentation=False, exception=None, observation=None, require_bound_observation=False) -> str:
	return HtmlQuoteVerifier(saved, quote, mode, documentation=documentation, exception=exception, observation=observation, require_bound_observation=require_bound_observation).verify()
# @used-by :func:`agent_tools.claims._verify_quote()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_evidence_loader_reuses_saved_extracted_html_and_caches_fragment_parse()`
def verify_saved_quote(root, source, quote, *, mode='exact', expected_hash=None, require_hash=False, observation=None, documentation=False, exception=None, locator=None, require_bound_observation=False, hash_error='Source hash differs from the referenced observation', absent_error='Quote is absent from the referenced source fragment'):
	return SavedQuoteVerifier(root, source, quote, mode=mode, expected_hash=expected_hash, require_hash=require_hash, observation=observation, documentation=documentation, exception=exception, locator=locator, require_bound_observation=require_bound_observation, hash_error=hash_error, absent_error=absent_error, extract_fn=evidence_loader.extract_bytes).verify()