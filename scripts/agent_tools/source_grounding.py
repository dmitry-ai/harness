# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from __future__ import annotations
from pathlib import Path
from markdown_it import MarkdownIt
from Df.Harness.Grounding.BlockLineAuditor import BlockLineAuditor
from Df.Harness.Grounding.DomainFactExtractor import DomainFactExtractor
from Df.Harness.Grounding.FactContradictionChecker import FactContradictionChecker
from Df.Harness.Grounding.LocalSourceAuditor import LocalSourceAuditor
from Df.Harness.Grounding.LocaleVerifier import LocaleVerifier
from Df.Harness.Grounding.Tier0Index import Tier0Index, _SOURCE_INFO_CACHE, _TIER0_INDEX_CACHE
from Df.Harness.lib.grounding import ALLOWED_MATH_GREEK, CLIENT_DELIVERABLE_METRIC_RE, EN_FUNCTION_WORDS, META_REFUTATION_RE, NON_EN_LATIN_STOPWORDS, RELATIONAL_MOD_RE, TECHNICAL_SPAN_RE, TIER2_NUMERIC_DOMAIN_RE, _READ_ONLY_GROUNDING, dfh_classify_provenance_tier, dfh_extract_block_links, dfh_extract_blockquote_quotes, dfh_filter_primary_sources, dfh_is_client_deliverable_doc, dfh_is_normative_harness_doc, dfh_is_primary_local_source, dfh_load_fact_ledger, dfh_markdown_parser, dfh_norm_quote_text, dfh_quote_segments_present, dfh_read_only_grounding, dfh_resolve_local_href
from agent_tools.claims import source_numeric_tokens
LocalSourceGroundingAuditor = LocalSourceAuditor
Tier0SourceIndex = Tier0Index
_source_numeric_tokens = source_numeric_tokens
# @used-by unused
def _extract_block_links(block, root: Path, doc_path: Path | None):
	return dfh_extract_block_links(block, root, doc_path)
# @used-by unused
def _filter_primary_sources(paths: list[Path]) -> list[Path]:
	return dfh_filter_primary_sources(paths)
# @used-by unused
def _get_tier0_file_entry(root: Path, rp: Path, mem_idx: dict[str, dict]) -> tuple[str, dict | None, bool]:
	idx = Tier0Index.for_root(root)
	idx.seed_entries(mem_idx)
	return idx.ensure_entry(rp)
# @used-by :func:`_load_local_source_info()`
def _infer_source_root(path: Path) -> Path | None:
	return Tier0Index.infer_source_root(path)
# @used-by unused
def _is_client_deliverable_doc(doc_path: Path | None) -> bool:
	return dfh_is_client_deliverable_doc(doc_path)
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_provenance_tiers_and_tier2_rejection()`
def _is_normative_harness_doc(path: Path) -> bool:
	return dfh_is_normative_harness_doc(path)
# @used-by unused
def _line_grounded_numbers_check(sline: str, ev_nums: set[str], valid_msg_nums: set[int], bound_ticket_ids: set[str], is_ticket: bool) -> list[str]:
	return BlockLineAuditor.line_grounded_numbers_check(sline, ev_nums, valid_msg_nums, bound_ticket_ids, is_ticket)
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_standalone_source_hydration_uses_tier0_index()`
def _load_local_source_info(path: Path, cache: dict | None=None, *, root: Path | None=None) -> dict:
	eff_root = root if None is not root else _infer_source_root(path)
	return Tier0Index.for_root(eff_root).load_source_info(path, cache) if None is not eff_root else Tier0Index.hydrate_standalone(path, cache)
# @used-by unused
def _load_tier0_index(root: Path, tickets: list[str] | tuple[str, ...]=()) -> tuple[list[Path], dict[str, dict]]:
	return Tier0Index.for_root(root).load_index(tickets)
# @used-by unused
def _quote_segments_present(q_raw: str, obs_norm: str, min_seg_len: int=12) -> bool:
	return dfh_quote_segments_present(q_raw, obs_norm, min_seg_len)
# @used-by unused
def _tier0_candidate_files(root: Path, tickets: list[str] | tuple[str, ...]=()) -> list[Path]:
	return Tier0Index.for_root(root).candidate_files(tickets)
# @used-by :meth:`Df.Harness.Review.FalsifierValidator.FalsifierValidator.__check_tier0_source()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_provenance_tiers_and_tier2_rejection()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :mod:`agent_tools.source_grounding`
def classify_provenance_tier(path: Path, root: Path | None=None) -> str:
	return dfh_classify_provenance_tier(path, root)
# @used-by :mod:`agent_tools.source_grounding`
def detect_prose_locale(prose: str) -> dict:
	return LocaleVerifier.detect_prose_locale(prose)
# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_provenance_tiers_and_tier2_rejection()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_issue51_post_finalize_deliverable_decoupling_journal_persistence_and_grounding_cache()`
# @used-by :mod:`agent_tools.source_grounding`
def discover_entity_tier0_sources(root: Path, text: str) -> list[dict]:
	return Tier0Index.for_root(root).discover_entities(text)
# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_language_neutral_slash_commands_enforce_user_default_locale_without_breaking_english_requests()`
# @used-by :mod:`agent_tools.source_grounding`
def extract_authored_prose(text: str, *, is_title: bool=False) -> str:
	return LocaleVerifier.extract_authored_prose(text, is_title=is_title)
# @used-by :func:`Df.Harness.lib.completion_compaction.dfh_find_evicted_cited_files()`
# @used-by :mod:`agent_tools.source_grounding`
def extract_block_links(block, root: Path, doc_path: Path | None):
	return dfh_extract_block_links(block, root, doc_path)
# @used-by :mod:`agent_tools.source_grounding`
def extract_blockquote_quotes(content: str, *, min_guillemet_len: int=8, allow_backtick_quotes: bool=False, min_orig_len: int=12) -> list[str]:
	return dfh_extract_blockquote_quotes(content, min_guillemet_len=min_guillemet_len, allow_backtick_quotes=allow_backtick_quotes, min_orig_len=min_orig_len)
# @used-by :mod:`agent_tools.source_grounding`
def extract_domain_entities(text: str, *, include_substring_metrics: bool=False) -> dict[str, list[str]]:
	return DomainFactExtractor.extract_domain_entities(text, include_substring_metrics=include_substring_metrics)
# @used-by :mod:`agent_tools.source_grounding`
def extract_fact_tuples(path: Path, raw_text: str | None=None, *, root: Path | None=None) -> list[dict]:
	return DomainFactExtractor(path, raw_text, root=root).extract()
# @used-by :mod:`agent_tools.source_grounding`
def extract_ticket_metadata(path: Path, raw: str) -> tuple[bool, set[int], str | None]:
	return DomainFactExtractor.extract_ticket_metadata(path, raw)
# @used-by :mod:`agent_tools.source_grounding`
def fact_tuple_contradictions(sline: str, infos: list[dict], ledger_tuples: list[dict] | None=None) -> list[str]:
	return FactContradictionChecker(sline, infos, ledger_tuples=ledger_tuples).check()
# @used-by :mod:`agent_tools.source_grounding`
def is_normative_harness_doc(path: Path) -> bool:
	return dfh_is_normative_harness_doc(path)
# @used-by :mod:`agent_tools.source_grounding`
def is_primary_local_source(path: Path) -> bool:
	return dfh_is_primary_local_source(path)
# @used-by :mod:`agent_tools.source_grounding`
def load_fact_ledger(root: Path) -> list[dict]:
	return dfh_load_fact_ledger(root)
# @used-by :func:`Df.Harness.lib.hook_markdown_ops.dfh_check_doc_grounding_and_links()`
# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__validate_response()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_provenance_tiers_and_tier2_rejection()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue46_ast_arithmetic_grounding()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue46_fact_tuple_ledger_and_contradictions()`
# @used-by :meth:`test_issue_preflight_and_batch.IssuePreflightAndBatchTests.test_test_summary_counts_allowed_alongside_blob_link_while_ungrounded_numbers_fail()`
# @used-by :meth:`test_scratch_slop_and_grounding_loc_m7.ScratchSlopAndGroundingLocM7Tests.test_scratch_draft_defers_grounding_but_keeps_doc4_syntax_checks()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_client_deliverable_grounding_and_evicted_step_output_gate()`
# @used-by :mod:`agent_tools.source_grounding`
def local_source_grounding_issues(root: Path, content: str, *, doc_path: Path | None=None, observed_texts: dict | None=None, cache: dict | None=None, _visited: set | None=None) -> list[str]:
	return LocalSourceAuditor(root, content, doc_path=doc_path, observed_texts=observed_texts, cache=cache, visited=_visited).run()
# @used-by :func:`Df.Harness.lib.completion_compaction.dfh_find_evicted_cited_files()`
# @used-by :func:`Df.Harness.lib.completion_links.dfh_authored_nonquote_hrefs()`
# @used-by :func:`Df.Harness.lib.request_binding._first_paragraph_line_children()`
# @used-by :mod:`agent_tools.source_grounding`
def markdown_parser() -> MarkdownIt:
	return dfh_markdown_parser()
# @used-by :meth:`Df.Harness.Review.FalsifierValidator.FalsifierValidator.__check_tier0_source()`
# @used-by :meth:`test_grounding_corpus_cache_m9.GroundingCorpusCacheM9Tests.test_repeated_blocks_avoid_per_block_re_normalization_and_tokenization()`
# @used-by :mod:`agent_tools.source_grounding`
def norm_quote_text(value: str) -> str:
	return dfh_norm_quote_text(value)
# @used-by :mod:`agent_tools.source_grounding`
def order_url_issues(sline: str, ev_nums: set[str], combined_raw: str, src_label: str) -> list[str]:
	return DomainFactExtractor.order_url_issues(sline, ev_nums, combined_raw, src_label)
# @used-by :meth:`Df.Harness.Review.FalsifierValidator.FalsifierValidator.__check_tier0_source()`
# @used-by :mod:`agent_tools.source_grounding`
def quote_segments_present(q_raw: str, obs_norm: str, min_seg_len: int=12) -> bool:
	return dfh_quote_segments_present(q_raw, obs_norm, min_seg_len)
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_begin()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_check_answer()`
# @used-by :func:`Df.Harness.lib.completion_recovery._scan_readonly_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_recover_checkpoint()`
# @used-by :mod:`agent_tools.source_grounding`
def read_only_grounding():
	return dfh_read_only_grounding()
# @used-by :mod:`agent_tools.source_grounding`
def resolve_local_href(root: Path, href: str, doc_path: Path | None=None) -> Path | None:
	return dfh_resolve_local_href(root, href, doc_path)
# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__validate_response()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue46_fact_tuple_ledger_and_contradictions()`
# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_auditor_and_domain_rules_deduplicate_ledger_tuples()`
# @used-by :mod:`agent_tools.source_grounding`
def sync_fact_ledger(root: Path) -> dict:
	return Tier0Index.for_root(root).sync_ledger()
# @used-by :mod:`agent_tools.source_grounding`
def ticket_author_issues(sline: str, combined_norm: str, src_label: str) -> list[str]:
	return DomainFactExtractor.ticket_author_issues(sline, combined_norm, src_label)
# @used-by :mod:`agent_tools.source_grounding`
def ticket_message_issues(sline: str, valid_msg_nums: set[int], bound_ticket_ids: set[str]) -> list[str]:
	return DomainFactExtractor.ticket_message_issues(sline, valid_msg_nums, bound_ticket_ids)
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_intermediate_or_language_issues()`
# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_language_neutral_slash_commands_enforce_user_default_locale_without_breaking_english_requests()`
# @used-by :mod:`agent_tools.source_grounding`
def verify_target_locale(text: str, *, target_locale: str='en-US', container_text: str | None=None, is_title: bool=False, allow_explicit_english_request: bool=False, min_target_ratio: float=0.35, min_alpha: int=15, default_locale: str | None=None) -> list[dict]:
	return LocaleVerifier(text, target_locale=target_locale, container_text=container_text, is_title=is_title, allow_explicit_english_request=allow_explicit_english_request, min_target_ratio=min_target_ratio, min_alpha=min_alpha, default_locale=default_locale).verify()
__all__ = ['ALLOWED_MATH_GREEK', 'CLIENT_DELIVERABLE_METRIC_RE', 'EN_FUNCTION_WORDS', 'LocalSourceGroundingAuditor', 'META_REFUTATION_RE', 'NON_EN_LATIN_STOPWORDS', 'RELATIONAL_MOD_RE', 'TECHNICAL_SPAN_RE', 'TIER2_NUMERIC_DOMAIN_RE', 'Tier0SourceIndex', '_READ_ONLY_GROUNDING', '_SOURCE_INFO_CACHE', '_TIER0_INDEX_CACHE', '_source_numeric_tokens', 'classify_provenance_tier', 'detect_prose_locale', 'discover_entity_tier0_sources', 'extract_authored_prose', 'extract_block_links', 'extract_blockquote_quotes', 'extract_domain_entities', 'extract_fact_tuples', 'extract_ticket_metadata', 'fact_tuple_contradictions', 'is_normative_harness_doc', 'is_primary_local_source', 'load_fact_ledger', 'local_source_grounding_issues', 'markdown_parser', 'norm_quote_text', 'order_url_issues', 'quote_segments_present', 'read_only_grounding', 'resolve_local_href', 'sync_fact_ledger', 'ticket_author_issues', 'ticket_message_issues', 'verify_target_locale']