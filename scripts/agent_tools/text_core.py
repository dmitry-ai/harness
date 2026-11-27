# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Text.CodeBlockLinter import CodeBlockLinter
from Df.Harness.Text.CommandReplayer import CommandReplayer
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from Df.Harness.Text.ProseLinter import ProseLinter
from Df.Harness.Text.ResponseChecker import ResponseChecker
from Df.Harness.lib.text_core import ABBREVIATIONS, ANCHOR, ARROW_CONNECTIVE, BANS, BOLD_LEADIN, FENCE, HEADING, INLINE_LITERAL, KEPT, LEXICON, LIST_MARK, PROTECTED_SPAN, REMOVAL, REPLACED, THRESHOLDS, dfh_author_text as author_text, dfh_bold_spans as bold_spans, dfh_changed_command_lines as changed_command_lines, dfh_check_markdown_lists as check_markdown_lists, dfh_clean as clean, dfh_command_blocks as command_blocks, dfh_default_shell as default_shell, dfh_detect_language as detect_language, dfh_excerpt as _excerpt, dfh_external_section_ref as external_section_ref, dfh_find_bans as find_bans, dfh_load_lexicon as load_lexicon, dfh_normalize_external_refs as normalize_external_refs, dfh_normalized as normalized, dfh_output_lines as _output_lines, dfh_plain as _plain, dfh_prose_spans as prose_spans, dfh_reference_document as reference_document, dfh_scan as scan, dfh_sentences as sentences, dfh_transform_prose as transform_prose
# @used-by :meth:`test_text_core.SharedMechanicsTests.test_hashed_asset_is_a_warning_not_proof_of_an_error()`
def check_code(lines, findings):
	CodeBlockLinter(lines, findings).check()
# @used-by unused
def check_prose(lines, kind, lang, findings, lexicon, bans):
	ProseLinter(lines, kind, lang, findings, lexicon, bans).check()
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.gate()`
# @used-by :meth:`test_df_article.ResponseTests.test_procedural_filler()`
# @used-by :meth:`test_df_article.ResponseTests.test_removal_claims_are_checked_against_the_file()`
# @used-by :meth:`test_df_article.ResponseTests.test_repeated_answer_is_a_signal_only_for_the_later_answer()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_text_core_and_review_authorize_handle_metadata_prefixed_response()`
# @used-by :meth:`test_text_core.SharedMechanicsTests.test_identical_answer_does_not_prove_nonexecution()`
def check_response(path: Path, text: str | None=None, against=(), lexicon=None, journal: Path | None=None) -> list[Finding]:
	return ResponseChecker(path, text=text, against=against, lexicon=lexicon, journal=journal).check()
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace._check_replay()`
# @used-by :meth:`test_text_core.ReplayTests.test_explicit_raw_contract_does_not_require_quote_wrapper()`
# @used-by :meth:`test_text_core.ReplayTests.test_missing_output_uncovered_selector_and_empty_document_are_not_success()`
# @used-by :meth:`test_text_core.ReplayTests.test_negative_grep_observation_requires_explicit_exit_contract()`
# @used-by :meth:`test_text_core.ReplayTests.test_nonzero_exit_cannot_match_printed_stdout()`
# @used-by :meth:`test_text_core.ReplayTests.test_pipeline_and_intermediate_command_failures_are_not_hidden()`
# @used-by :meth:`test_text_core.ReplayTests.test_quoted_numbered_links_are_presentation_of_raw_output()`
# @used-by :meth:`test_text_core.ReplayTests.test_unclosed_fence_is_an_error()`
def replay(text: str, *, shell=None, timeout=60, only=None, expected_exit=None, contracts=None):
	return CommandReplayer(text, shell=shell, timeout=timeout, only=only, expected_exit=expected_exit, contracts=contracts).replay()
