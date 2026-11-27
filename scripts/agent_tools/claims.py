# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from decimal import Decimal
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Analysis.Claim.CalculationContract import CalculationContract
from Df.Harness.Analysis.Claim.CalculationValidator import CalculationValidator
from Df.Harness.Analysis.Claim.ClosureCollector import ClosureCollector
from Df.Harness.Analysis.Claim.ComparisonContract import ComparisonContract
from Df.Harness.Analysis.Claim.ComparisonValidator import ComparisonValidator
from Df.Harness.Analysis.Claim.InlineCalcVerifier import InlineCalcVerifier
from Df.Harness.Analysis.Claim.ManifestPrimaryVerifier import ManifestPrimaryVerifier
from Df.Harness.Analysis.Claim.NumericGrounding import NumericGrounding
from Df.Harness.Analysis.Claim.PrimaryCapabilities import PrimaryCapabilities
from Df.Harness.Analysis.Claim.QuantityMatcher import QuantityMatcher
from Df.Harness.Analysis.Claim.SafeArithmetic import SafeArithmetic
from Df.Harness.Analysis.Claim.SourceNumericTokenizer import SourceNumericTokenizer
from Df.Harness.Analysis.Claim.StandaloneNumberExtractor import StandaloneNumberExtractor
from Df.Harness.Analysis.Claim.StructureAuditor import HASH, ID, KINDS, PROPERTIES, STATUSES
from Df.Harness.Analysis.ClaimGraph import ClaimGraph as ClaimGraphValidator
from urllib.parse import urldefrag
import hashlib
import json
SECTIONS = ('identity', 'concerns', 'misconceptions', 'causes', 'methods')
# @used-by :mod:`agent_tools.claims`
def _calculation_structure(value, field, claim):
	return CalculationContract(value, field, claim).issues()
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue46_ast_arithmetic_grounding()`
# @used-by :mod:`agent_tools.claims`
def _check_calculation(claim, index, refs):
	CalculationValidator(claim, index, refs).check()
# @used-by :mod:`agent_tools.claims`
def _check_comparison(claim, index, refs):
	ComparisonValidator(claim, index, refs).check()
# @used-by :mod:`agent_tools.claims`
def _comparison_structure(value, field, claim, evidence):
	return ComparisonContract(value, field, claim, evidence).issues()
# @used-by :meth:`Df.Harness.Text.IntakeSourceEvaluator.IntakeSourceEvaluator.evaluate()`
# @used-by :mod:`agent_tools.claims`
def _manifest_primary(root, ref):
	return ManifestPrimaryVerifier(root, ref).verify()
# @used-by :mod:`agent_tools.claims`
def _primary_capabilities(root, ref):
	return PrimaryCapabilities(root, ref).resolve()
# @used-by :mod:`agent_tools.claims`
def _quantity_matches(reference, decimal_value, unit, source_context=None):
	return QuantityMatcher(reference, decimal_value, unit, source_context).matches()
# @used-by :func:`claim_index()`
# @used-by :mod:`agent_tools.claims`
def _text(value):
	return isinstance(value, str) and bool(value.strip())
# @used-by :meth:`Df.Harness.Text.IntakeSourceEvaluator.IntakeSourceEvaluator.evaluate()`
# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.evaluate()`
# @used-by :mod:`agent_tools.claims`
def _verify_quote(root, ref, *, observation=None):
	from .evidence import verify_saved_quote
	loc = ref['locator']
	base, frag = urldefrag(ref['source'])
	if loc['type'] not in {'anchor', 'json_pointer'}:
		if frag:
			raise ValueError('A fragment source needs an anchor or json_pointer locator')
		src = base
	else:
		if frag and frag != loc['value']:
			raise ValueError('Source fragment and explicit locator disagree')
		src = base + '#' + loc['value']
	return verify_saved_quote(root, src, ref['quote'], mode=ref.get('quote_match', 'exact'), expected_hash=ref['source_sha256'], require_hash=True, observation=observation, documentation=bool(ref.get('documentation')), exception=ref.get('anchor_exception', {}), locator=loc, require_bound_observation=True, hash_error='Primary source bytes changed from source_sha256', absent_error='Exact quote is absent from the located primary source')
# @used-by :func:`Df.Harness.lib.text_claims.dfh_claim_subset()`
# @used-by :func:`Df.Harness.lib.text_claims.dfh_evidence_inputs()`
# @used-by :func:`claim_index()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__find_snapshot()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__verify_target_artifacts()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.claim_snapshot()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_claim_index_includes_facts_and_all_five_stages()`
# @used-by :mod:`agent_tools.claims`
def all_claims(value):
	return [claim for _, _, claim in claim_locations(value)]
# @used-by :func:`test_evidence_contract.v3_analysis()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__audit_block()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.validate()`
# @used-by :meth:`Df.Harness.Text.ClaimRegistryStore.ClaimRegistryStore.__refresh_dep_digests()`
# @used-by :meth:`Df.Harness.Text.ClaimRegistryStore.ClaimRegistryStore.save()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__find_snapshot()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__verify_target_artifacts()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.claim_snapshot()`
# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.test_claim_graph_validator_memoizes_diamond_dag_and_dns_cache()`
# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.test_collect_claim_closure_and_save_registry_single_structural_pass()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.price_analysis()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.signed_price_analysis()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_currency_cannot_be_borrowed_from_another_quantity()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_dependency_change_and_cycle_are_reported()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_html_markup_cannot_hide_a_sign_between_spans()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_json_amount_currency_pair_is_an_exact_quantity_locator()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_misconception_hypothesis_requires_alternatives_and_discriminating_check()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue46_ast_arithmetic_grounding()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_e8_causes_misconceptions_and_methods_cannot_be_downgraded_or_omitted_in_routine_review()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.dependent_registry()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_a_self_authored_note_is_not_a_native_reassessment_of_changed_evidence()`
# @used-by :mod:`agent_tools.claims`
def claim_digest(claim):
	return hashlib.sha256(json.dumps(claim, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
# @used-by :func:`Df.Harness.lib.text_claims.dfh_claim_subset()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__load_registry()`
# @used-by :meth:`Df.Harness.Text.ClaimRegistryStore.ClaimRegistryStore.save()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.test_collect_claim_closure_and_save_registry_single_structural_pass()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_claim_index_includes_facts_and_all_five_stages()`
# @used-by :meth:`test_text_workflow.TextClaimRevisionTests.test_primary_revision_marks_all_transitive_dependents_stale_and_archives_old_bytes()`
# @used-by :mod:`agent_tools.claims`
def claim_index(value):
	return {claim['id']: claim for claim in all_claims(value) if _text(claim.get('id'))}
# @used-by :func:`Df.Harness.lib.text_claims.dfh_claim_subset()`
# @used-by :func:`all_claims()`
# @used-by :mod:`agent_tools.claims`
def claim_locations(value):
	if isinstance(value, dict):
		for section in ('facts', 'claims', *SECTIONS):
			for number, claim in enumerate(value.get(section, []) if isinstance(value.get(section), list) else ()):
				if isinstance(claim, dict):
					yield (f'/{section}/{number}', section, claim)
# @used-by :func:`Df.Harness.lib.text_claims.dfh_claim_subset()`
# @used-by :func:`Df.Harness.lib.text_claims.dfh_primary_numbers()`
# @used-by :meth:`test_evidence_contract.ClaimGraphValidatorTests.test_collect_claim_closure_and_save_registry_single_structural_pass()`
# @used-by :mod:`agent_tools.claims`
def collect_claim_closure(seed_ids, index, *, include_addresses=False, unknown_prefix=None):
	return ClosureCollector(seed_ids, index, include_addresses=include_addresses, unknown_prefix=unknown_prefix).collect()
# @used-by :func:`Df.Harness.lib.text_sources.dfh_check_claim_sources()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__load_registry()`
# @used-by :meth:`Df.Harness.Text.ClaimRegistryStore.ClaimRegistryStore.save()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_malformed_typed_metadata_returns_diagnostics()`
# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_validators_emit_actionable_hints()`
# @used-by :mod:`agent_tools.claims`
def contract_issues(value):
	return ClaimGraphValidator(value).structural_issues()
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue46_ast_arithmetic_grounding()`
# @used-by :mod:`agent_tools.claims`
def evaluate_safe_arithmetic(expr: str, env: dict[str, Decimal] | None=None) -> tuple[Decimal | None, set[str]]:
	return SafeArithmetic(expr, env).evaluate()
# @used-by :func:`Df.Harness.lib.text_sources.dfh_check_claim_sources()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__load_registry()`
# @used-by :meth:`Df.Harness.Text.ClaimRegistryStore.ClaimRegistryStore.save()`
# @used-by :mod:`agent_tools.claims`
def evidence_contract_issues(root, value, *, skip_structural=False):
	return ClaimGraphValidator(value, root=root).evidence_issues(skip_structural=skip_structural)
# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.line_grounded_numbers_check()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue46_ast_arithmetic_grounding()`
# @used-by :mod:`agent_tools.claims`
def extract_verified_inline_calc_numbers(text: str, grounded_nums: set[str]) -> tuple[set[str], list[str]]:
	return InlineCalcVerifier(text, grounded_nums).extract()
# @used-by :mod:`agent_tools.claims`
def grounded_numbers_for_claim(claim, index=None, visited=None, _memo=None):
	return NumericGrounding(claim, index, visited, _memo).grounded_numbers()
# @used-by :meth:`Df.Harness.Grounding.ActiveCorpusBuilder.ActiveCorpusBuilder.resolve_text_helpers()`
# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__build_hydrated_info()`
# @used-by :meth:`test_turn_completion.ResponseEvidenceAuditorTests.test_multi_segment_quote_and_thousand_grouped_numeric_tokens()`
# @used-by :mod:`agent_tools.claims`
# @used-by :mod:`agent_tools.source_grounding`
def source_numeric_tokens(raw_text: str) -> set[str]:
	return SourceNumericTokenizer(raw_text).tokenize()
# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.line_grounded_numbers_check()`
# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.__check_tier2_sole_evidence()`
# @used-by :meth:`Df.Harness.Text.ClaimMapValidator.ClaimMapValidator.__audit_block()`
# @used-by :meth:`test_source_admission.LinkPresentationTests.test_numeric_prose_in_a_link_label_still_needs_grounding()`
# @used-by :meth:`test_source_admission.LinkPresentationTests.test_original_numeric_anchor_is_not_a_quantitative_claim()`
# @used-by :meth:`test_source_admission.LinkPresentationTests.test_reference_links_and_balanced_parentheses_keep_the_same_behavior()`
# @used-by :mod:`agent_tools.claims`
def standalone_numbers(text):
	return StandaloneNumberExtractor(text).extract()
__all__ = ['ClaimGraphValidator', 'HASH', 'ID', 'KINDS', 'PROPERTIES', 'SECTIONS', 'STATUSES', '_calculation_structure', '_check_calculation', '_check_comparison', '_comparison_structure', '_manifest_primary', '_primary_capabilities', '_quantity_matches', '_text', '_verify_quote', 'all_claims', 'claim_digest', 'claim_index', 'claim_locations', 'collect_claim_closure', 'contract_issues', 'evaluate_safe_arithmetic', 'evidence_contract_issues', 'extract_verified_inline_calc_numbers', 'grounded_numbers_for_claim', 'source_numeric_tokens', 'standalone_numbers']