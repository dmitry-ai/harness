# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Text.AddressedSection import AddressedSection
from Df.Harness.Text.KeyedProseRewriter import KeyedProseRewriter
from Df.Harness.Text.MechanicalProjector import MechanicalProjector
from Df.Harness.lib.text_sections import ANCHOR_LINK, ARTICLE_NUMBER_KEY, KEYED_REF, PART, PROPOSAL_NUMBER_KEY, TEXT_KINDS, dfh_assign_tree_numbers as assign_tree_numbers, dfh_build_render_report as build_render_report, dfh_close_spans as close_spans, dfh_content_blocks as content_blocks, dfh_lint_document as lint_document, dfh_parse_addressed as parse_addressed, dfh_part_at as part_at, dfh_reassemble_lines as reassemble_lines, dfh_scope_blocks as scope_blocks, dfh_section_at as section_at, dfh_validate_ref_range as validate_ref_range
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_text_core.SharedMechanicsTests.test_article_reexports_single_shared_implementation()`
def keyed_engine(kind):
	if kind not in ('article', 'proposal'):
		raise ValueError('Keyed numbering is available for article or proposal; a letter preserves its own form')
	from . import article, proposal
	return proposal if 'proposal' == kind else article
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.scope_issues()`
def mechanical_projection(text, kind, mode):
	return MechanicalProjector(text, kind, mode).project()
# @used-by unused
def rewrite_keyed_prose(raw, line_no, mapping, findings, external_changes, *, format_ref, anchors=None, dangling_hint=''):
	return KeyedProseRewriter(raw, line_no, mapping, findings, external_changes, format_ref=format_ref, anchors=anchors, dangling_hint=dangling_hint).rewrite()
