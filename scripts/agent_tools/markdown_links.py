# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.text.trim import df_trim_text_left
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.lib.markdown import dfh_decode_file_uri, dfh_display_address, dfh_inline_links, dfh_iter_inline_segments, dfh_markdown_it_parser, dfh_numeric_text, dfh_technical_label
# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__validate_file_uri()`
def decode_file_uri(reference: str, *, reject_remote: bool=False) -> str:
	return dfh_decode_file_uri(reference, reject_remote=reject_remote)
# @used-by :func:`agent_tools.article.check_link_style()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_normalize_and_trim_delegation_to_df()`
def display_address(href):
	return dfh_display_address(href, trim_fn=df_trim_text_left)
# @used-by :func:`agent_tools.article.check_link_style()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_markdown_parser_and_inline_segments_shared()`
def inline_links(tokens, *, include_images: bool=True):
	return dfh_inline_links(tokens, include_images=include_images)
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_markdown_parser_and_inline_segments_shared()`
def iter_inline_segments(tokens, *, include_images: bool=True):
	return dfh_iter_inline_segments(tokens, include_images=include_images)
# @used-by :meth:`Df.Harness.Analysis.Claim.StandaloneNumberExtractor.StandaloneNumberExtractor.extract()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_markdown_parser_and_inline_segments_shared()`
def numeric_text(text):
	return dfh_numeric_text(text, trim_fn=df_trim_text_left)
# @used-by :func:`agent_tools.article.check_link_style()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__authored_targets()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_markdown_parser_and_inline_segments_shared()`
def parser(*, preserve_links: bool=False, allow_file_links: bool=False, html: bool=True):
	return dfh_markdown_it_parser(preserve_links=preserve_links, allow_file_links=allow_file_links, html=html)
# @used-by unused
def technical_label(label, href):
	return dfh_technical_label(label, href, trim_fn=df_trim_text_left)