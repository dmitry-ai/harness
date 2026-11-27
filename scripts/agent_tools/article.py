# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Text.Article.GraphAuditor import GraphAuditor
from Df.Harness.Text.Article.KeyedParser import KeyedParser
from Df.Harness.Text.Article.LinkStyleAuditor import LinkStyleAuditor
from Df.Harness.Text.Article.Linter import Linter
from Df.Harness.Text.Article.NumberedParser import NumberedParser
from Df.Harness.Text.Article.Renderer import Renderer
from Df.Harness.Text.Article.Section import Section
from Df.Harness.Text.Article.SourceExporter import SourceExporter
from Df.Harness.Text.Article.StructureAuditor import StructureAuditor
from Df.Harness.lib.text_sections import ARTICLE_BARE_REF as BARE_REF, ARTICLE_KEYED as KEYED, ARTICLE_NUMBERED as NUMBERED, ARTICLE_SECTION_LABEL as SECTION_LABEL, ARTICLE_SOURCE_META as SOURCE_META, dfh_detect_kind as detect_kind
from .text_core import ABBREVIATIONS, ANCHOR, ARROW_CONNECTIVE, BANS, BOLD_LEADIN, FENCE, Finding, HEADING, INLINE_LITERAL, KEPT, LEXICON, LIST_MARK, Line, REMOVAL, REPLACED, THRESHOLDS, _excerpt, _plain, author_text, bold_spans, changed_command_lines, check_code, check_markdown_lists, check_prose, check_response, clean, command_blocks, default_shell, detect_language, external_section_ref, find_bans, load_lexicon, normalize_external_refs, normalized, replay, scan, sentences, transform_prose
from .text_sections import ANCHOR_LINK, ARTICLE_NUMBER_KEY, AddressedSection, KEYED_REF as SOURCE_REF, PART, assign_tree_numbers, build_render_report, close_spans as _close, lint_document, part_at, rewrite_keyed_prose, section_at, validate_ref_range
# @used-by unused
def check_graph(lines, sections, findings):
	GraphAuditor(lines, sections, findings).audit()
# @used-by :meth:`test_source_admission.LinkPresentationTests.findings()`
def check_link_style(lines, findings, link_style):
	LinkStyleAuditor(lines, findings, link_style).audit()
# @used-by unused
def check_proposal(lines, findings):
	findings.extend(lint_document('\n'.join((line.raw for line in lines)), 'proposal', lexicon=[], bans=[]))
# @used-by unused
def check_structure(lines, sections, findings):
	StructureAuditor(lines, sections, findings).audit()
# @used-by :meth:`test_df_article.LexiconAndProjectionTests.test_conditional_recommendation_must_branch_from_part_two_diagnostic_step()`
# @used-by :meth:`test_df_article.LexiconAndProjectionTests.test_trailing_conditional_recommendation_is_flagged()`
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_keyed_view_round_trip_changes_only_normalizations()`
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_reference_article_has_no_errors_and_only_known_warnings()`
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_render_renumbers_references_and_reports_removed_sections()`
# @used-by :meth:`test_df_article.SlopDetectionTests.assertFlags()`
# @used-by :meth:`test_df_article.SlopDetectionTests.test_enumerating_title_case_heading()`
# @used-by :meth:`test_df_article.SlopDetectionTests.test_orphan_analysis_paragraph_is_reported()`
# @used-by :meth:`test_df_article.SlopDetectionTests.test_project_bans_are_discovered_from_the_project_root()`
# @used-by :meth:`test_df_article.SlopDetectionTests.test_proposal_references_and_markdown_links()`
# @used-by :meth:`test_df_article.SlopDetectionTests.test_structure_errors()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.lint()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_formatted_link_style_is_explicit_and_preserves_literals()`
def lint_text(text: str, *, kind: str | None=None, lang: str | None=None, path: Path | None=None, lexicon=None, bans=None, link_style=None) -> list[Finding]:
	return Linter(text, kind=kind, lang=lang, path=path, lexicon=lexicon, bans=bans, link_style=link_style).lint()
# @used-by :mod:`df_article`
def main(argv=None) -> int:
	from .text_cli import main as common_main
	return common_main(argv, default_kind='article')
# @used-by :func:`render_map()`
def parse_keyed(lines: list[Line], findings: list[Finding]):
	return KeyedParser(lines, findings).parse()
# @used-by :func:`render_map()`
def parse_sections(lines: list[Line], findings: list[Finding] | None=None):
	return NumberedParser(lines, findings).parse()
# @used-by :func:`render_map()`
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_deleted_premise_blocks_rendering_until_dependents_are_resolved()`
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_external_document_spacing_preserves_its_number_and_literal_examples()`
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_keyed_view_round_trip_changes_only_normalizations()`
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_new_keys_are_numbered_by_position()`
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_render_renumbers_references_and_reports_removed_sections()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_bare_article_reference_is_converted_or_diagnosed()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_literals_quotes_and_urls_are_not_rewritten()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_mixed_anchor_style_follows_keys_when_renumbering()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_reference_range_checks_both_ends_and_order()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_render_mapping_exposes_keys_and_spans_without_polluting_report()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_section_sign_anchors_survive_source_render_without_previous()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_valid_range_is_renumbered_and_generic_links_are_preserved()`
def render(source: str, previous: str | None=None):
	return Renderer(source, previous).render()
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_render_mapping_exposes_keys_and_spans_without_polluting_report()`
def render_map(source: str, markdown: str | None=None):
	source_sections, _ = parse_keyed(scan(source), [])
	if None is markdown:
		markdown, _, _ = render(source)
	rendered = parse_sections(scan(markdown))
	return [{'key': original.name, 'number': current.key, 'part': current.part, 'anchor': current.anchor, 'source': original.span_dict(), 'rendered': current.span_dict()} for original, current in zip(source_sections, rendered)]
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_deleted_premise_blocks_rendering_until_dependents_are_resolved()`
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_external_document_spacing_preserves_its_number_and_literal_examples()`
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_keyed_view_round_trip_changes_only_normalizations()`
# @used-by :meth:`test_df_article.ReferenceArticleTests.test_render_renumbers_references_and_reports_removed_sections()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_bare_article_reference_is_converted_or_diagnosed()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_literals_quotes_and_urls_are_not_rewritten()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_mixed_anchor_style_follows_keys_when_renumbering()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_reference_range_checks_both_ends_and_order()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_section_sign_anchors_survive_source_render_without_previous()`
# @used-by :meth:`test_text_core.ArticleIntegrityTests.test_valid_range_is_renumbered_and_generic_links_are_preserved()`
def to_source(text: str) -> str:
	return SourceExporter(text).export()
