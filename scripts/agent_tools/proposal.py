# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Mapping
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Text.Proposal.Block import Block as ProposalBlock
from Df.Harness.Text.Proposal.FieldLinter import FieldLinter
from Df.Harness.Text.Proposal.Linter import Linter
from Df.Harness.Text.Proposal.Parser import Parser
from Df.Harness.Text.Proposal.Renderer import Renderer
from Df.Harness.Text.Proposal.SourceExporter import SourceExporter
from Df.Harness.lib.text_sections import KEYED_REF as KEY_REF, PROPOSAL_KEYED as KEYED, PROPOSAL_MARKDOWN_LINK as MARKDOWN_LINK, PROPOSAL_NUMBERED as NUMBERED, PROPOSAL_PREFIX as PREFIX, PROPOSAL_REF as REF, PROPOSAL_URL as URL
from .text_core import Finding, Line
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_df_proposal.ProposalFieldTests.test_aggregate_room_cannot_hide_one_oversized_field()`
# @used-by :meth:`test_df_proposal.ProposalFieldTests.test_browser_character_length_cannot_undercount_astral_unicode()`
# @used-by :meth:`test_df_proposal.ProposalFieldTests.test_limits_count_exact_text_including_urls_and_newlines()`
# @used-by :meth:`test_df_proposal.ProposalFieldTests.test_missing_field_and_unconfirmed_limit_are_distinct_errors()`
# @used-by :meth:`test_df_proposal.ProposalFieldTests.test_zero_or_noninteger_limit_is_not_accepted_as_configuration()`
def lint_fields(fields: Mapping[str, str], limits: Mapping[str, int], *, count_mode: str='utf16') -> list[Finding]:
	return FieldLinter(fields, limits, count_mode=count_mode).lint()
# @used-by :func:`test_df_proposal.lint()`
# @used-by :meth:`test_df_proposal.ProposalLintTests.test_owner_subject_uses_shared_lexicon_and_preserves_quotations()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_reordering_changes_local_refs_but_preserves_the_external_paragraph()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_application_hashing_is_distinct_from_service_fingerprints()`
def lint_text(text: str, *, kind: str | None=None, lang: str | None=None, path: Path | None=None, lexicon=None, bans=None, profile: Mapping | None=None) -> list[Finding]:
	return Linter(text, kind=kind, lang=lang, path=path, lexicon=lexicon, bans=bans, profile=profile).lint()
# @used-by :mod:`agent_tools.proposal`
def parse_blocks(value: str | list[Line], findings: list[Finding] | None=None, *, keyed: bool=False) -> list[ProposalBlock]:
	return Parser(value, findings, keyed=keyed).parse()
parse_sections = parse_blocks
parse = parse_blocks
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_both_range_boundaries_renumber_and_reversed_range_fails()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_children_cannot_be_left_behind_after_moving_a_sibling()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_deleted_referenced_point_blocks_render()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_duplicate_and_missing_parent_keys_are_errors()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_explicit_external_codes_and_standards_are_not_internal_points()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_external_spacing_normalization_preserves_quoted_examples_and_code()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_literals_in_ascii_quotation_and_markdown_url_remain_unchanged()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_new_descriptive_keys_assign_numbers_without_article_headings()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_numbers_in_keyed_body_cannot_silently_rebind()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_reordering_changes_local_refs_but_preserves_the_external_paragraph()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_reordering_moves_child_references_and_keeps_prose()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_round_trip_preserves_all_wording_quotes_code_zero_prefaces_and_newlines()`
def render(source: str, previous: str | None=None):
	return Renderer(source, previous).render()
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_explicit_external_codes_and_standards_are_not_internal_points()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_external_spacing_normalization_preserves_quoted_examples_and_code()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_literals_in_ascii_quotation_and_markdown_url_remain_unchanged()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_reordering_changes_local_refs_but_preserves_the_external_paragraph()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_reordering_moves_child_references_and_keeps_prose()`
# @used-by :meth:`test_df_proposal.ProposalTransformTests.test_round_trip_preserves_all_wording_quotes_code_zero_prefaces_and_newlines()`
def to_source(text: str) -> str:
	return SourceExporter(text).export()
