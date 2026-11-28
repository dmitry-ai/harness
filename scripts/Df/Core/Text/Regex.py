# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import re
from Df.Core.O import O
from Df.Core.lib.array.first import df_last
from Df.Core.lib.array.part import df_tail
from Df.Core.lib.cache.dfc import dfc
from Df.Core.lib.text.n.cc import df_cc_n
from Df.Core.lib.text.n.explode import df_explode_n
from Df.Core.lib.text.n.has import df_is_multiline
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# PCRE-style regex helper supporting delimited patterns (e.g., `#pattern#i`) and rich error diagnostics.
# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L3-L278
class Regex(O):
	__P__PATTERN = 'pattern'
	__P__SUBJECT = 'subject'
	__P__THROW_ON_ERROR = 'throw_on_error'
	__P__THROW_ON_NOT_MATCH = 'throw_on_not_match'
	# Compile PCRE-delimited pattern (e.g., `#foo#imsx`) or raw Python regex.
	# @used-by :meth:`Regex.__execMatch()`
	def __compile(self) -> re.Pattern[str]:
		pat = self.__getPattern()
		flags = 0
		if 2 <= len(pat) and pat[0] in '#/~!%@':
			delim = pat[0]
			pos = pat.rfind(delim)
			if 0 < pos:
				body, mod = (pat[1:pos], pat[pos + 1:])
				flags = (re.IGNORECASE if 'i' in mod else 0) | (re.MULTILINE if 'm' in mod else 0) | (re.DOTALL if 's' in mod else 0) | (re.VERBOSE if 'x' in mod else 0)
				pat = body
		return re.compile(pat, flags)
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L16-L47
	# @used-by :meth:`Regex.match()`
	def __execMatch(self) -> str | list[str] | None | bool:
		try:
			m = self.__compile().search(self.__getSubject())
		except re.error as exc:
			if self[Regex.__P__THROW_ON_ERROR]:
				self.__throwInternalError(str(exc))
			r: str | list[str] | None | bool = False
		else:
			if None is not m:
				groups = [m.group(0), *m.groups()]
				r = df_last(groups) if 3 > len(groups) else df_tail(groups)
			else:
				if self.__needThrowOnNotMatch():
					self.__throwNotMatch()
				r = None
		return r
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L69-L74
	# @used-by :meth:`Regex.__compile()`
	# @used-by :meth:`Regex.__throwInternalError()`
	# @used-by :meth:`Regex.__throwNotMatch()`
	def __getPattern(self) -> str:
		return str(self[Regex.__P__PATTERN])
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L89-L97
	# @used-by :meth:`Regex.__execMatch()`
	# @used-by :meth:`Regex.__getSubjectReportPart()`
	# @used-by :meth:`Regex.__getSubjectSplitted()`
	# @used-by :meth:`Regex.__isSubjectMultiline()`
	# @used-by :meth:`Regex.__throwInternalError()`
	# @used-by :meth:`Regex.__throwNotMatch()`
	def __getSubject(self) -> str:
		return str(self[Regex.__P__SUBJECT])
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L99-L108
	# @used-by :meth:`Regex.__getSubjectReportPart()`
	# @used-by :meth:`Regex.__isSubjectTooLongToReport()`
	def __getSubjectMaxLinesToReport(self) -> int:
		return 5
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L110-L118
	# @used-by :meth:`Regex.__throwInternalError()`
	# @used-by :meth:`Regex.__throwNotMatch()`
	def __getSubjectReportPart(self) -> str:
		return dfc(self, lambda: self.__getSubject() if not self.__isSubjectTooLongToReport() else df_cc_n(self.__getSubjectSplitted()[:self.__getSubjectMaxLinesToReport()]))
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L120-L125
	# @used-by :meth:`Regex.__getSubjectReportPart()`
	# @used-by :meth:`Regex.__isSubjectTooLongToReport()`
	def __getSubjectSplitted(self) -> list[str]:
		return dfc(self, lambda: df_explode_n(self.__getSubject()))
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L127-L132
	# @used-by :meth:`Regex.__isSubjectTooLongToReport()`
	# @used-by :meth:`Regex.__throwInternalError()`
	# @used-by :meth:`Regex.__throwNotMatch()`
	def __isSubjectMultiline(self) -> bool:
		return dfc(self, lambda: df_is_multiline(self.__getSubject()))
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L134-L142
	# @used-by :meth:`Regex.__getSubjectReportPart()`
	def __isSubjectTooLongToReport(self) -> bool:
		return dfc(self, lambda: self.__isSubjectMultiline() and self.__getSubjectMaxLinesToReport() < len(self.__getSubjectSplitted()))
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L144-L148
	# @used-by :meth:`Regex.__execMatch()`
	# @used-by :meth:`Regex.matchInt()`
	def __needThrowOnNotMatch(self) -> bool:
		return bool(self[Regex.__P__THROW_ON_NOT_MATCH])
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L150-L199
	# @used-by :meth:`Regex.__execMatch()`
	def __throwInternalError(self, detail: str='') -> None:
		from Df.Qa.lib.validation.error import df_error
		suffix = f' ({detail})' if detail else ''
		if not self.__isSubjectMultiline():
			m = f'Applying regular expression «{self.__getPattern()}» to «{self.__getSubject()}» failed{suffix}.'
		else:
			m = f'Applying regular expression «{self.__getPattern()}» failed{suffix}.\nSubject:\n{self.__getSubjectReportPart()}'
		df_error(m)
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L201-L226
	# @used-by :meth:`Regex.__execMatch()`
	# @used-by :meth:`Regex.matchInt()`
	def __throwNotMatch(self) -> None:
		from Df.Qa.lib.validation.error import df_error
		if not self.__isSubjectMultiline():
			m = f'String «{self.__getSubject()}» does not match regular expression «{self.__getPattern()}».'
		else:
			m = f'Text does not match regular expression «{self.__getPattern()}»:\n{self.__getSubjectReportPart()}'
		df_error(m)
	# Return matched string, list of capture groups (when >= 2 groups), None on no match, or False on regex error.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L4-L47
	# @used-by :func:`Df.Core.lib.date.df_date_from_timestamp_14()`
	# @used-by :func:`Df.Core.lib.fs.df_uri_file_decode()`
	# @used-by :func:`Df.Core.lib.text.is_.guid.df_is_guid()`
	# @used-by :func:`Df.Core.lib.text.regex.df_preg_match()`
	# @used-by :func:`Df.Harness.lib.ag_inputs._extract_event_direct_uuids()`
	# @used-by :func:`Df.Harness.lib.clarifications_ops._parse_answers()`
	# @used-by :func:`Df.Harness.lib.clarifications_ops._parse_output_envelope()`
	# @used-by :func:`Df.Harness.lib.completion_links._normalize_file_href_path()`
	# @used-by :func:`Df.Harness.lib.completion_links._validate_single_href()`
	# @used-by :func:`Df.Harness.lib.config_blocks._collect_root_edits()`
	# @used-by :func:`Df.Harness.lib.config_blocks.dfh_frontmatter()`
	# @used-by :func:`Df.Harness.lib.grounding_md._is_table_header_pair()`
	# @used-by :func:`Df.Harness.lib.grounding_md._parse_list_items()`
	# @used-by :func:`Df.Harness.lib.grounding_md.dfh_extract_top_sections()`
	# @used-by :func:`Df.Harness.lib.grounding_md.dfh_mask_fenced_lines()`
	# @used-by :func:`Df.Harness.lib.grounding_md.dfh_parse_explicit_items()`
	# @used-by :func:`Df.Harness.lib.grounding_md.dfh_parse_section_items()`
	# @used-by :func:`Df.Harness.lib.hook_runtime_ops._scan_hook_line()`
	# @used-by :func:`Df.Harness.lib.hook_runtime_ops._scan_workflow_line()`
	# @used-by :func:`Df.Harness.lib.hook_runtime_ops._update_fence()`
	# @used-by :func:`Df.Harness.lib.issue.dfh_is_df_issue_command_text()`
	# @used-by :func:`Df.Harness.lib.issue_turn._next_skip_depth()`
	# @used-by :func:`Df.Harness.lib.issue_turn.dfh_extract_implemented_m_roots()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade._execute_upgrade()`
	# @used-by :func:`Df.Harness.lib.journal_upgrade._summarize_v2_buckets()`
	# @used-by :func:`Df.Harness.lib.markdown.dfh_decode_file_uri()`
	# @used-by :func:`Df.Harness.lib.path_template._expand_braced_token()`
	# @used-by :func:`Df.Harness.lib.path_template._split_path_root()`
	# @used-by :func:`Df.Harness.lib.path_template.dfh_normalize_path_str()`
	# @used-by :func:`Df.Harness.lib.path_template.dfh_validate_variables_map()`
	# @used-by :func:`Df.Harness.lib.request_binding._plain_text_upwork_ids()`
	# @used-by :func:`Df.Harness.lib.request_binding._slash_link_upwork_ids()`
	# @used-by :func:`Df.Harness.lib.request_binding._strip_user_request_wrapper()`
	# @used-by :func:`Df.Harness.lib.request_binding.dfh_extract_leading_upwork_init_ids()`
	# @used-by :func:`Df.Harness.lib.research.dfh_readable_reference()`
	# @used-by :func:`Df.Harness.lib.rule_splitter._partition_rule_sections()`
	# @used-by :func:`Df.Harness.lib.rule_splitter._used_rule_indices()`
	# @used-by :func:`Df.Harness.lib.shell.dfh_extract_comment_issue_urls()`
	# @used-by :func:`Df.Harness.lib.text_core._classify_unclosed_line()`
	# @used-by :func:`Df.Harness.lib.text_core.dfh_check_markdown_lists()`
	# @used-by :func:`Df.Harness.lib.text_core.dfh_command_blocks()`
	# @used-by :func:`Df.Harness.lib.text_core.dfh_detect_language()`
	# @used-by :func:`Df.Harness.lib.text_core.dfh_normalize_external_refs()`
	# @used-by :func:`Df.Harness.lib.text_core.dfh_scan()`
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_iter_article_headings()`
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_part_at()`
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_scope_blocks()`
	# @used-by :func:`Df.Harness.lib.trace_common.dfh_local_uri_to_path()`
	# @used-by :func:`Df.Harness.lib.uri.dfh_local_uri_to_path()`
	# @used-by :func:`Df.Qa.lib.validation.check.df_is_email()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.QuantityMatcher.QuantityMatcher.__collect_unit_cands()`
	# @used-by :meth:`Df.Harness.Arch.RepoReceiptSpecification.RepoReceiptSpecification.issue_slug()`
	# @used-by :meth:`Df.Harness.Arch.SpecValidator.SpecValidator.__parse_field_line()`
	# @used-by :meth:`Df.Harness.Experiment.CallChainParser.CallChainParser.__tokenize()`
	# @used-by :meth:`Df.Harness.Gate.FailfastGate.FailfastGate.missing_timeout_guard()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentChecker.IssueCommentChecker.__check_header_placement()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentScanner.IssueCommentScanner.__is_line_comment_prefix()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentScanner.IssueCommentScanner.__scan_record_code()`
	# @used-by :meth:`Df.Harness.Gate.IssueCommentScanner.IssueCommentScanner.__xml_span()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__validate_relative_cross_repo()`
	# @used-by :meth:`Df.Harness.Gate.RulesAuditChecker.RulesAuditChecker.__is_blind_reference_line()`
	# @used-by :meth:`Df.Harness.Gate.RulesAuditChecker.RulesAuditChecker.__strip_frontmatter()`
	# @used-by :meth:`Df.Harness.Gate.RulesManifest.RulesManifest.parse_frontmatter()`
	# @used-by :meth:`Df.Harness.Gate.SendMessageGate.SendMessageGate.__is_duplicate_verdict_payload()`
	# @used-by :meth:`Df.Harness.Git.BlobSizeValidator.BlobSizeValidator.__collect_push_revs()`
	# @used-by :meth:`Df.Harness.Git.GitSegmentExtractor.GitSegmentExtractor.extract()`
	# @used-by :meth:`Df.Harness.Git.HostPathNormalizer.HostPathNormalizer.normalize()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_technical_spans()`
	# @used-by :meth:`Df.Harness.Grounding.CliCommandAuditor.CliCommandAuditor.__desc_line_set()`
	# @used-by :meth:`Df.Harness.Grounding.CliOutputJsonParser.CliOutputJsonParser.__truncated_top_level_failure()`
	# @used-by :meth:`Df.Harness.Grounding.DomainFactExtractor.DomainFactExtractor.__collect_dict_fact_tuples()`
	# @used-by :meth:`Df.Harness.Grounding.EvidenceBundleIngestor.EvidenceBundleIngestor.discourse_topic_key()`
	# @used-by :meth:`Df.Harness.Grounding.HeadingTreeParser.HeadingTreeParser.parse()`
	# @used-by :meth:`Df.Harness.Grounding.LocaleVerifier.LocaleVerifier.__extract_inline_chunks()`
	# @used-by :meth:`Df.Harness.Grounding.MixedTurnProblemSchema.MixedTurnProblemSchema.__check_top_h1()`
	# @used-by :meth:`Df.Harness.Grounding.MixedTurnProblemSchema.MixedTurnProblemSchema.__classify_slot()`
	# @used-by :meth:`Df.Harness.Grounding.MixedTurnProblemSchema.MixedTurnProblemSchema.has_mixed_sections()`
	# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__fenced_banner_at_start()`
	# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__parse_standalone()`
	# @used-by :meth:`Df.Harness.Grounding.StandaloneProblemSchema.StandaloneProblemSchema.__extract_nested_block()`
	# @used-by :meth:`Df.Harness.Grounding.StandaloneProblemSchema.StandaloneProblemSchema.__process_h1()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.__check_body_blocks()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.__collect_m_subtask_groups()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.validate_repo()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.validate_slug_part()`
	# @used-by :meth:`Df.Harness.Meta.HeaderRenderer.HeaderRenderer.extract_leading()`
	# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__resolve_rel_to_root()`
	# @used-by :meth:`Df.Harness.Path.SlotResolver.SlotResolver.__prepare_maps()`
	# @used-by :meth:`Df.Harness.Path.SlotResolver.SlotResolver.__resolve_one()`
	# @used-by :meth:`Df.Harness.Perf.TimesheetCommon.TimesheetCommon.__parse_header_meta()`
	# @used-by :meth:`Df.Harness.Project.Context.LetterDiscoverer.LetterDiscoverer.is_excluded()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__validate_inputs()`
	# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.__anchor_offset()`
	# @used-by :meth:`Df.Harness.Research.JsonCollectionSummarizer.JsonCollectionSummarizer.__collect_item_fields()`
	# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.__resolve_local_path_text()`
	# @used-by :meth:`Df.Harness.Research.MarkdownHeadingParser.MarkdownHeadingParser.__extract_frontmatter()`
	# @used-by :meth:`Df.Harness.Runtime.AddonsProfileAdapter.AddonsProfileAdapter.__validate_core_fields()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.scan_word_or_char()`
	# @used-by :meth:`Df.Harness.Tdd.CodeClassifier.CodeClassifier.is_test_file()`
	# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.unwrap_watchdog_prefix()`
	# @used-by :meth:`Df.Harness.Tdd.CommentScanners.CommentScanners.scan_cpp_raw()`
	# @used-by :meth:`Df.Harness.Tdd.CommentScanners.CommentScanners.scan_heredoc()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.lex_dockerfile()`
	# @used-by :meth:`Df.Harness.Tdd.OutcomeParser.OutcomeParser.uri_to_local_path()`
	# @used-by :meth:`Df.Harness.Tdd.RatchetGuard.RatchetGuard.__removed_line_violations()`
	# @used-by :meth:`Df.Harness.Tdd.RatchetGuard.RatchetGuard.parse_ratchet_ok_lines()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__hash_block_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__vbs_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.lex_batch()`
	# @used-by :meth:`Df.Harness.Tdd.ServiceExempt.ServiceExempt.__is_service_command()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__check_conditional_line()`
	# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__record_prose_refs()`
	# @used-by :meth:`Df.Harness.Text.Article.KeyedParser.KeyedParser.parse()`
	# @used-by :meth:`Df.Harness.Text.Article.NumberedParser.NumberedParser.__attach_anchor()`
	# @used-by :meth:`Df.Harness.Text.Article.NumberedParser.NumberedParser.parse()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.__format_ref()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.__parse_metadata()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.__render_lines()`
	# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.__convert_link()`
	# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.export()`
	# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_anchor_link()`
	# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_group_counts()`
	# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_parts_and_addressing()`
	# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__collect_anchors()`
	# @used-by :meth:`Df.Harness.Text.MechanicalProjector.MechanicalProjector.__project_renumber()`
	# @used-by :meth:`Df.Harness.Text.ProseLinter.ProseLinter.__check_prose_details()`
	# @used-by :meth:`Df.Harness.Text.ProseLinter.ProseLinter.__match_entry()`
	# @used-by :meth:`Df.Harness.Text.ProseLinter.ProseLinter.check()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentDownloader.AttachmentDownloader.attachment_path()`
	# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__parse_paragraph()`
	# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__render_link()`
	# @used-by :meth:`Df.Harness.Upwork.JobUrlParser.JobUrlParser.extract_upwork_job_url_id()`
	# @used-by :meth:`Df.Harness.Upwork.LoomVideoExtractor.LoomVideoExtractor.__parse_vtt_block()`
	# @used-by :meth:`Df.Harness.Upwork.MarkdownTableSanitizer.MarkdownTableSanitizer.__is_heading()`
	# @used-by :meth:`Df.Harness.Upwork.MarkdownTableSanitizer.MarkdownTableSanitizer.__process_line()`
	# @used-by :meth:`Df.Harness.Upwork.MarkdownTableSanitizer.MarkdownTableSanitizer.sanitize_kb_markdown()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__build_blocks()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__detect_bold_fonts()`
	# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__render_blocks()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectDirResolver.ProjectDirResolver.__find_existing()`
	# @used-by :meth:`Df.Harness.Upwork.VideoDetector.VideoDetector.__scan_text_urls()`
	# @used-by :meth:`Df.Harness.Upwork.VideoDetector.VideoDetector.canonical_video_url()`
	# @used-by :meth:`Df.Harness.Xref.Java.Lexer.Lexer.__tokenize_java_word_or_punct()`
	# @used-by :meth:`Df.Harness.Xref.Java.Tags.Tags.__build_link_entry()`
	# @used-by :meth:`Df.Harness.Xref.Java.Tags.Tags.__classify_javadoc_line()`
	# @used-by :meth:`Df.Harness.Xref.Js.Lexer.Lexer.__tokenize_js_word_or_punct()`
	# @used-by :meth:`Df.Harness.Xref.Js.Tags.Tags.__resolve_import_link()`
	# @used-by :meth:`Df.Harness.Xref.Js.Tags.Tags.__validate_jsdoc_entry()`
	# @used-by :meth:`Df.Harness.Xref.Js.Tags.Tags.parse_jsdoc_tag_line()`
	# @used-by :meth:`Df.Harness.Xref.Python.Tags.Tags.__validate_tag_entry()`
	# @used-by :meth:`Df.Harness.Xref.Python.Tags.Tags.parse_tag_line()`
	# @used-by :meth:`Regex.matchInt()`
	# @used-by :meth:`Regex.test()`
	# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
	def match(self) -> str | list[str] | None | bool:
		return dfc(self, self.__execMatch)
	# Return matched integer when the pattern matches an integer string, else None (or throw).
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L49-L61
	# @used-by :func:`Df.Core.lib.text.regex.df_preg_int()`
	def matchInt(self) -> int | None | bool:
		from Df.Qa.lib.validation.check import df_is_int
		matched = self.match() if self.test() else None
		if None is not matched and df_is_int(matched):
			r: int | None | bool = int(str(matched))
		else:
			if self.__needThrowOnNotMatch():
				self.__throwNotMatch()
			r = None
		return r
	# Return True iff the subject matches the pattern without error.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L63-L67
	# @used-by :func:`Df.Core.lib.text.regex.df_preg_test()`
	# @used-by :meth:`Regex.matchInt()`
	def test(self) -> bool:
		return dfc(self, lambda: None is not self.match() and False is not self.match())
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Regex.php#L247-L259
	# @used-by :func:`Df.Core.lib.text.regex.df_preg_int()`
	# @used-by :func:`Df.Core.lib.text.regex.df_preg_match()`
	# @used-by :func:`Df.Core.lib.text.regex.df_preg_test()`
	# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
	@staticmethod
	def i(pattern: str, subject: str, throwOnError: bool=True, throwOnNotMatch: bool=False) -> Regex:
		return Regex({Regex.__P__PATTERN: pattern, Regex.__P__SUBJECT: subject, Regex.__P__THROW_ON_ERROR: throwOnError, Regex.__P__THROW_ON_NOT_MATCH: throwOnNotMatch})
