# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Iterator
from Df.Core.lib.array.clean.filter import df_filter_tail
from Df.Core.lib.array.map import df_map
from Df.Core.lib.text.starts_ends import df_starts_with
from Df.Qa.lib.bt.entry import df_bt_entry_file
from Df.Qa.lib.bt.filter import df_bt_filter_head
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2020-02-27 Filtered iterable collection of backtrace Frame objects.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace.php#L6-L65
class Trace:
	# 2020-02-27 Filter leading internal error frames and trailing archive frames, wrapping the rest in Frame.
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace.php#L13-L39
	# @used-by :func:`Df.Qa.lib.bt.log.df_bt_s()`
	# @used-by :meth:`Df.Qa.Failure.Failure._postface()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_trace_and_failure()`
	def __init__(self, ff: list[dict[str, Any]]) -> None:
		from Df.Qa.Trace.Frame import Frame
		# 2024-03-04 "Skip the leading `df_error()` from the logged backtraces": https://github.com/mage2pro/core/issues/355
		# 2023-07-26 "Skip the leading `df_error_create()` from the logged backtraces": https://github.com/mage2pro/core/issues/262
		# 2023-07-27 "Skip the leading `df_log()` from the logged backtraces": https://github.com/mage2pro/core/issues/284
		ff = df_bt_filter_head(ff, ['df_error', 'df_error_create', 'df_log'])
		# 2017-07-01 Strip trailing archive frames (e.g. phar://) that may carry binary artifacts.
		# 2023-07-26 "Implement `df_filter_tail()`": https://github.com/mage2pro/core/issues/263
		ff = list(df_filter_tail(ff, lambda f: df_starts_with(df_bt_entry_file(f), 'phar://')))
		self.__frames: list[Any] = list(df_map(ff, lambda f: Frame.i(f)))
	# 2020-02-27
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace.php#L55
	# @used-by :meth:`Formatter.Formatter.__format()`
	def __iter__(self) -> Iterator[Any]:
		return self.getIterator()
	# 2020-02-27
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace.php#L47
	# @used-by unused
	def __len__(self) -> int:
		return self.count()
	# 2020-02-27
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace.php#L47
	# @used-by :func:`Df.Harness.lib.completion_compaction._stat_and_hash_file()`
	# @used-by :func:`Df.Harness.lib.config_blocks.dfh_extract_managed_block()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._strip_owned_role_block()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_profile_agents()`
	# @used-by :func:`Df.Harness.lib.research.dfh_bare_urls()`
	# @used-by :func:`agent_tools.git_ignore.merge_managed_git_ignore()`
	# @used-by :func:`agent_tools.text_core.check_code()`
	# @used-by :func:`agent_tools.text_core.check_prose()`
	# @used-by :func:`agent_tools.text_sections.content_blocks()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__extract_body()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentScanner.IssueCommentScanner.__scan_brace_end()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentScanner.IssueCommentScanner.__trailing_comment_urls()`
	# @used-by :meth:`Df.Harness.Git.GlobalIgnoreSyncer.GlobalIgnoreSyncer.__merge_block()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__plan()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.__check_body_blocks()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.__clause_has_triple_enumeration()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.__has_backtick_enumeration()`
	# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.__compute_payload()`
	# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.__replace_existing()`
	# @used-by :meth:`Df.Harness.Research.MarkdownHeadingParser.MarkdownHeadingParser.__extract_frontmatter()`
	# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__normalize_heading_levels()`
	# @used-by :meth:`Df.Harness.Xref.Java.Lexer.Lexer.__tokenize_java_atom()`
	# @used-by :meth:`Df.Harness.Xref.Java.Lexer.Lexer.__tokenize_java_step()`
	# @used-by :meth:`Df.Harness.Xref.Js.Lexer.Lexer.__tokenize_js_step()`
	# @used-by :meth:`Trace.__len__()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.scope_issues()`
	# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_prepends_tab_indented_json_metadata_header_and_supports_opt_out()`
	# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_render_prepend_extract_and_strip_tab_indented_json_header()`
	# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_headers_submodule_roundtrips_and_ignores_non_harness_json()`
	# @used-by :meth:`test_red_flags.RedFlagTests.test_legacy_top_block_moves_to_final_first_level_section_without_losing_text()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_real_http_failure_and_redirect_are_saved_once_per_base_url()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_preflight_is_repeated_and_cannot_use_stale_target()`
	# @used-by :meth:`test_watchdog_and_timeout_gate.WatchdogAndTimeoutGateTests.test_pre_tool_use_normalizes_unbounded_unittest_and_pytest_and_denies_multi_segment()`
	def count(self) -> int:
		return len(self.__frames)
	# 2020-02-27
	# https://github.com/mage2pro/core/blob/11.6.1/Qa/Trace.php#L55
	# @used-by :meth:`Trace.__iter__()`
	def getIterator(self) -> Iterator[Any]:
		return iter(self.__frames)