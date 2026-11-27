# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Grounding.DfAnalysisValidator import DfAnalysisValidator
from Df.Harness.Grounding.StatementDirValidator import StatementDirValidator
from Df.Harness.lib.grounding_md import dfh_external_anchor_issues, dfh_extract_top_sections, dfh_find_markdown_table_lines, dfh_is_documentation_url, dfh_markdown_table_issues, dfh_mask_fenced_lines, dfh_parse_explicit_items, dfh_parse_section_items
# @used-by unused
def _extract_top_sections(text: str) -> dict[int, tuple[str, str]]:
	return dfh_extract_top_sections(text)
# @used-by unused
def _mask_fenced_lines(text: str) -> list[tuple[int, str, bool]]:
	return dfh_mask_fenced_lines(text)
# @used-by unused
def _parse_explicit_items(text: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
	return dfh_parse_explicit_items(text)
# @used-by unused
def _parse_section_items(body: str) -> list[tuple[str, str]]:
	return dfh_parse_section_items(body)
# @used-by unused
def analysis_gate_issues(response: str, *, requests: list | tuple=(), turn_context: dict | None=None) -> list[str]:
	return DfAnalysisValidator.analysis_gate_issues(response, requests=requests, turn_context=turn_context)
# @used-by unused
def external_anchor_issues(label: str, href: str, norm_url: str, observed_anchors: dict[str, set[str]], response: str) -> list[str]:
	return dfh_external_anchor_issues(label, href, norm_url, observed_anchors, response)
# @used-by unused
def find_markdown_table_lines(text: str) -> list[int]:
	return dfh_find_markdown_table_lines(text)
# @used-by unused
def is_documentation_url(url: str) -> bool:
	return dfh_is_documentation_url(url)
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_analysis_check()`
# @used-by :func:`Df.Harness.lib.hook_runtime_ops.dfh_scan_doc4_sentence_issues()`
def markdown_table_issues(text: str) -> list[str]:
	return dfh_markdown_table_issues(text)
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_analysis_check()`
# @used-by :meth:`test_df_analysis.DfAnalysisGatesTests.test_general_df_analysis_requires_multiple_hypotheses_methods_and_template_fields()`
# @used-by :meth:`test_df_analysis.DfAnalysisGatesTests.test_problem_analysis_auto_triggers_and_enforces_all_five_sections()`
# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_bundled_companion_topics_inside_single_block_still_rejected()`
# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_four_blocks_missing_or_merged_companion_track_rejected()`
# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_four_separate_problem_analyses_validated_independently_ru_and_en()`
# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_general_mode_and_non_problem_responses_unaffected()`
# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_scatter_banner_enforced_in_earlier_problem_blocks()`
# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_single_problem_block_rejected_when_companion_tracks_missing()`
# @used-by :meth:`test_scatter_banner_gate.ScatterBannerGateTests.test_analysis_check_and_answer_check_enforce_file6_banner()`
# @used-by :meth:`test_scatter_banner_gate.ScatterBannerGateTests.test_banner_must_be_exact_uppercase_and_at_start_of_recommendation()`
# @used-by :meth:`test_scatter_banner_gate.ScatterBannerGateTests.test_detects_english_and_standalone_scattering_recommendations()`
# @used-by :meth:`test_scatter_banner_gate.ScatterBannerGateTests.test_does_not_false_positive_on_safe_methods_native_configs_or_prose()`
def validate_df_analysis(response: str, *, requests: list | tuple=(), mode: str='auto', turn_context: dict | None=None) -> list[str]:
	return DfAnalysisValidator(response, requests=requests, mode=mode, turn_context=turn_context).validate()
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_validate_statements()`
# @used-by :meth:`test_agent_tools.StatementTests.test_missing_test_not_masked_by_words_in_statement()`
def validate_statements(directory: Path) -> list[str]:
	return StatementDirValidator(directory).validate()