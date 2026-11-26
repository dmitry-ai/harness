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
	# @used-by :func:`Df.Core.lib.text.is_.guid.df_is_guid()`
	# @used-by :func:`Df.Core.lib.text.regex.df_preg_match()`
	# @used-by :func:`Df.Qa.lib.validation.check.df_is_email()`
	# @used-by :func:`agent_tools.article._iter_headings()`
	# @used-by :func:`agent_tools.article.check_graph()`
	# @used-by :func:`agent_tools.article.check_group_counts()`
	# @used-by :func:`agent_tools.article.check_structure()`
	# @used-by :func:`agent_tools.article.parse_keyed()`
	# @used-by :func:`agent_tools.article.parse_sections()`
	# @used-by :func:`agent_tools.article.render()`
	# @used-by :func:`agent_tools.article.to_source()`
	# @used-by :func:`agent_tools.claims._quantity_matches()`
	# @used-by :func:`agent_tools.cli_command_grounding._extract_recommended_commands()`
	# @used-by :func:`agent_tools.completion._response_link_issues()`
	# @used-by :func:`agent_tools.configuration._frontmatter()`
	# @used-by :func:`agent_tools.configuration._root_options()`
	# @used-by :func:`agent_tools.context._is_excluded()`
	# @used-by :func:`agent_tools.failfast_gate.missing_timeout_guard()`
	# @used-by :func:`agent_tools.gates.send_message_gate._is_duplicate_verdict_payload()`
	# @used-by :func:`agent_tools.grounding_domains._collect_json_fact_tuples()`
	# @used-by :func:`agent_tools.hook_runtime._scan_hook_line()`
	# @used-by :func:`agent_tools.hook_runtime._scan_workflow_line()`
	# @used-by :func:`agent_tools.hook_runtime._update_fence()`
	# @used-by :func:`agent_tools.issue_comment_gate._check_header_placement()`
	# @used-by :func:`agent_tools.issue_comment_gate._is_line_comment_prefix()`
	# @used-by :func:`agent_tools.issue_comment_gate._scan_record_code()`
	# @used-by :func:`agent_tools.issue_comment_gate._xml_span()`
	# @used-by :func:`agent_tools.issue_first_bg._has_direct_issue_seg()`
	# @used-by :func:`agent_tools.issues.parity._next_skip_depth()`
	# @used-by :func:`agent_tools.issues.parity.extract_implemented_m_roots()`
	# @used-by :func:`agent_tools.journal.upgrade_journal()`
	# @used-by :func:`agent_tools.links.parse_markdown_headings()`
	# @used-by :func:`agent_tools.links.readable_reference()`
	# @used-by :func:`agent_tools.links.validate_file()`
	# @used-by :func:`agent_tools.markdown_links.decode_file_uri()`
	# @used-by :func:`agent_tools.meta.headers.extract_leading_metadata_header()`
	# @used-by :func:`agent_tools.path_registry._validate_variables_map()`
	# @used-by :func:`agent_tools.path_registry.expand_template()`
	# @used-by :func:`agent_tools.path_registry.normalize_path_str()`
	# @used-by :func:`agent_tools.perf.timesheet_common._parse_header_meta()`
	# @used-by :func:`agent_tools.platforms.antigravity._extract_subagent_uuids()`
	# @used-by :func:`agent_tools.platforms.clarifications._parse_answers()`
	# @used-by :func:`agent_tools.platforms.clarifications._parse_output_envelope()`
	# @used-by :func:`agent_tools.platforms.request_binding._extract_leading_upwork_init_ids()`
	# @used-by :func:`agent_tools.platforms.request_binding._slash_link_upwork_ids()`
	# @used-by :func:`agent_tools.platforms.request_binding._strip_user_request_wrapper()`
	# @used-by :func:`agent_tools.platforms.trace_common.local_uri_to_path()`
	# @used-by :func:`agent_tools.problem_tracks.extract_problem_blocks()`
	# @used-by :func:`agent_tools.project_rename._target_name_and_root()`
	# @used-by :func:`agent_tools.repo_link_gate._validate_relative_cross_repo()`
	# @used-by :func:`agent_tools.research._summarize_json_collections()`
	# @used-by :func:`agent_tools.response_grounding._discourse_topic_key()`
	# @used-by :func:`agent_tools.rules_audit_checks._is_blind_reference_line()`
	# @used-by :func:`agent_tools.rules_audit_checks._strip_frontmatter()`
	# @used-by :func:`agent_tools.rules_manifest.parse_rule_frontmatter()`
	# @used-by :func:`agent_tools.scatter_banner._fenced_banner_at_start()`
	# @used-by :func:`agent_tools.scatter_banner._parse_standalone_recommendations()`
	# @used-by :func:`agent_tools.shell_audit.extract_comment_issue_urls()`
	# @used-by :func:`agent_tools.shell_audit.normalize_host_path()`
	# @used-by :func:`agent_tools.source_grounding.extract_authored_prose()`
	# @used-by :func:`agent_tools.statements._extract_top_sections()`
	# @used-by :func:`agent_tools.statements._is_table_header_pair()`
	# @used-by :func:`agent_tools.statements._mask_fenced_lines()`
	# @used-by :func:`agent_tools.statements._parse_explicit_items()`
	# @used-by :func:`agent_tools.statements._parse_list_items()`
	# @used-by :func:`agent_tools.statements._parse_section_items()`
	# @used-by :func:`agent_tools.tdd.classifier.is_test_file()`
	# @used-by :func:`agent_tools.tdd.commands.unwrap_watchdog_prefix()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_c.scan_word_or_char()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_markup.lex_dockerfile()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_script._hash_block_step()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_script._vbs_step()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_script.lex_batch()`
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_cpp_raw()`
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_heredoc()`
	# @used-by :func:`agent_tools.tdd.outcomes._uri_to_local_path()`
	# @used-by :func:`agent_tools.tdd.ratchet._parse_ratchet_ok_lines()`
	# @used-by :func:`agent_tools.tdd.ratchet._removed_line_violations()`
	# @used-by :func:`agent_tools.tdd.service_exempt._is_service_command()`
	# @used-by :func:`agent_tools.text_core.check_markdown_lists()`
	# @used-by :func:`agent_tools.text_core.check_prose()`
	# @used-by :func:`agent_tools.text_core.command_blocks()`
	# @used-by :func:`agent_tools.text_core.detect_language()`
	# @used-by :func:`agent_tools.text_core.normalize_external_refs()`
	# @used-by :func:`agent_tools.text_core.scan()`
	# @used-by :func:`agent_tools.text_sections.mechanical_projection()`
	# @used-by :func:`agent_tools.text_sections.part_at()`
	# @used-by :func:`agent_tools.text_sections.scope_blocks()`
	# @used-by :func:`agent_tools.upwork_data.canonical_video_url()`
	# @used-by :func:`agent_tools.upwork_data.detect_client_videos()`
	# @used-by :func:`agent_tools.upwork_data.extract_upwork_job_url_id()`
	# @used-by :func:`agent_tools.upwork_data.parse_webvtt_phrases()`
	# @used-by :func:`agent_tools.upwork_data.sanitize_kb_markdown()`
	# @used-by :func:`agent_tools.upwork_data.structure_job_description()`
	# @used-by :func:`agent_tools.upwork_extract.attachment_path()`
	# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
	# @used-by :func:`agent_tools.xref.java_lex._tokenize_java_word_or_punct()`
	# @used-by :func:`agent_tools.xref.java_tags._build_link_entry()`
	# @used-by :func:`agent_tools.xref.java_tags._classify_javadoc_line()`
	# @used-by :func:`agent_tools.xref.js_lex._tokenize_js_word_or_punct()`
	# @used-by :func:`agent_tools.xref.js_tags._resolve_import_link()`
	# @used-by :func:`agent_tools.xref.js_tags._validate_jsdoc_entry()`
	# @used-by :func:`agent_tools.xref.js_tags.parse_jsdoc_tag_line()`
	# @used-by :func:`agent_tools.xref.python_tags._validate_tag_entry()`
	# @used-by :func:`agent_tools.xref.python_tags.parse_tag_line()`
	# @used-by :func:`split_project_rules.split_rules()`
	# @used-by :meth:`Regex.matchInt()`
	# @used-by :meth:`Regex.test()`
	# @used-by :meth:`agent_tools.experiments.BrowserTraceInspector._tokenize()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_push_blob_sizes()`
	# @used-by :meth:`agent_tools.issues.linter.IssueMarkdownLinter._check_body_blocks()`
	# @used-by :meth:`agent_tools.issues.linter.IssueMarkdownLinter._collect_m_subtask_groups()`
	# @used-by :meth:`agent_tools.issues.linter.IssueMarkdownLinter.validate_repo()`
	# @used-by :meth:`agent_tools.issues.linter.IssueMarkdownLinter.validate_slug_part()`
	# @used-by :meth:`agent_tools.path_registry.ProjectPaths.__init__()`
	# @used-by :meth:`agent_tools.path_registry.ProjectPaths._resolve_rel_to_root()`
	# @used-by :meth:`agent_tools.shell_audit.ShellCommandInspector._iter_git_segments()`
	# @used-by :meth:`agent_tools.source_grounding.LocalSourceGroundingAuditor._check_prose_line()`
	# @used-by :meth:`agent_tools.upwork_data.DocxMarkdownExtractor._parse_paragraph()`
	# @used-by :meth:`agent_tools.upwork_data.DocxMarkdownExtractor._render_link()`
	# @used-by :meth:`agent_tools.upwork_data.PdfMarkdownExtractor._build_blocks()`
	# @used-by :meth:`agent_tools.upwork_data.PdfMarkdownExtractor._detect_bold_fonts()`
	# @used-by :meth:`agent_tools.upwork_data.PdfMarkdownExtractor._render_blocks()`
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
