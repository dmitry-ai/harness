# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from collections import Counter
from dataclasses import dataclass
from typing import override
import html as html_lib
from html.parser import HTMLParser
from pathlib import Path
import re
import json
from urllib.parse import unquote, urldefrag, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError
# 2026-10-17
# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
# https://github.com/dmitry-ai/harness/issues/9
# @used-by :func:`readable_reference()`
def _readable_escapes(value: str) -> str:
	# @used-by :func:`_readable_escapes()`
	def decode(match):
		encoded = match.group()
		raw = bytes.fromhex(encoded.replace('%', ''))
		result, offset = ([], 0)
		for char in raw.decode('utf-8', errors='surrogateescape'):
			size = len(char.encode('utf-8', errors='surrogateescape')) * 3
			original = encoded[offset:offset + size]
			offset += size
			safe_ascii = char.isascii() and (char.isalnum() or char in ' -._~')
			safe_unicode = 160 <= ord(char) < 55296 or 57344 <= ord(char) <= 1114111
			result.append(char if safe_ascii or safe_unicode else original)
		return ''.join(result)
	return re.sub('(?:%[0-9a-fA-F]{2})+', decode, value)
# @used-by :func:`agent_tools.markdown_links.display_address()`
# @used-by :func:`agent_tools.text_sources._attempt()`
# @used-by :func:`agent_tools.text_sources._evaluate()`
# @used-by :func:`agent_tools.text_sources.save_source_check()`
# @used-by :func:`agent_tools.text_sources.source_urls()`
# @used-by :func:`markdown_link()`
# @used-by :func:`readable_link_issues()`
# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__text_element_raw()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_original_file_uri_becomes_a_readable_local_reference()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_query_signatures_delimiters_literal_percent_and_invalid_utf8_are_preserved()`
def readable_reference(value: str | Path) -> str:
	value = value.as_posix() if isinstance(value, Path) else value
	base, fragment_sep, fragment = value.partition('#')
	path, query_sep, query = base.partition('?')
	if path.lower().startswith('file:'):
		parsed = urlsplit(path)
		path = parsed.path
		if parsed.netloc and 'localhost' != parsed.netloc:
			path = '//' + parsed.netloc + path
		elif re.match('^/[A-Za-z]:/', path):
			path = path[1:]
	return _readable_escapes(path) + query_sep + query + fragment_sep + _readable_escapes(fragment)
# @used-by :meth:`Df.Harness.Analysis.Renderer.Renderer.render()`
# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.render_evidence_md()`
# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.render_projects_md()`
# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.__render_selected()`
# @used-by :meth:`Df.Harness.Project.WebsiteCardSyncer.WebsiteCardSyncer.sync_initial()`
# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__render_link()`
# @used-by :meth:`Df.Harness.Upwork.KbProjectMdFormatter.KbProjectMdFormatter.__site_text()`
# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__text_element_raw()`
# @used-by :meth:`Df.Harness.Workflow.ProgressPublisher.ProgressPublisher.publish()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_cli_readability_check_catches_original_encoding_and_accepts_readable_destination()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_original_file_uri_becomes_a_readable_local_reference()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_query_signatures_delimiters_literal_percent_and_invalid_utf8_are_preserved()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_navigation_links_can_address_a_directory()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_source_survives_a_renderer_that_encodes_its_href()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_utf8_anchor_and_balanced_parentheses_need_no_url_encoding()`
def markdown_link(label: str | None, target: str | Path) -> str:
	target = readable_reference(target)
	if any((char in target for char in '\r\n<>')):
		raise ValueError('A document link cannot contain line endings or literal angle brackets')
	text = target if None is label else label
	text = text.replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')
	destination = f'<{target}>' if any((char.isspace() or char in '()' for char in target)) else target
	return f'[{text}]({destination})'
# 2026-11-25
# "Unify chat reply LINK-5 validation via chat_reply_link_issues helper":
# https://github.com/dmitry-ai/harness/issues/230
# 2026-11-26 "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs": https://github.com/dmitry-ai/harness/issues/264
# @used-by :func:`Df.Harness.lib.completion_links.dfh_response_link_issues()`
# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.record()`
# @used-by :meth:`Df.Harness.Workflow.FinalizeStageRunner.FinalizeStageRunner.run()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor.__init__()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_chat_reply_link_issues_allows_unencoded_file_uri_and_rejects_encoded()`
# @used-by :meth:`test_repo_link_gate.RepoLinkGateTests.test_rejects_file_uri_to_github_repo_and_allows_non_repo_and_gitignored_files()`
# @used-by :meth:`test_repo_link_gate.RepoLinkGateTests.test_validates_github_blob_and_tree_tags_paths_lines_and_anchors()`
def chat_reply_link_issues(content: str, *, root: Path | None=None) -> list[str]:
	from .repo_link_gate import chat_repo_link_issues
	return readable_link_issues(content, allow_unencoded_file_uri=True) + chat_repo_link_issues(content, root=root)
# 2026-11-23
# "Unify local Tier 0 source hydration, HTTP/DOM Evidence observation loading, CommonMark helpers, and file:// path parsing across source_grounding.py, response_grounding.py, evidence.py, links.py, text_sources.py, and markdown_links.py":
# https://github.com/dmitry-ai/harness/issues/76
# @used-by :func:`agent_tools.source_grounding.resolve_local_href()`
# @used-by :meth:`Df.Harness.Analysis.LocalSourceResolver.LocalSourceResolver.resolve()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_decode_file_uri_handles_windows_relative_and_remote()`
def decode_file_uri(reference: str, *, reject_remote: bool=False) -> str:
	from .markdown_links import decode_file_uri as _decode
	return _decode(reference, reject_remote=reject_remote)
# 2026-10-17
# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
# https://github.com/dmitry-ai/harness/issues/9
# @used-by :func:`chat_reply_link_issues()`
# @used-by :func:`validate_content()`
# @used-by :meth:`Df.Harness.Analysis.OwnedPublisher.OwnedPublisher.__check_links()`
# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.__validate_inputs()`
# @used-by :meth:`Df.Harness.Project.OnceFileWriter.OnceFileWriter.write()`
# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.__check_deliverable_links()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_chat_reply_link_issues_allows_unencoded_file_uri_and_rejects_encoded()`
# @used-by :meth:`test_readable_links.ReadableProjectTests.test_analysis_sources_are_readable_while_quotes_keep_their_exact_bytes()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_docx_hyperlinks_are_readable_without_altering_their_visible_source_text()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_encoded_authored_links_are_detected_in_all_supported_text_forms()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_exact_quotes_code_and_source_copies_are_not_rewritten_or_rejected()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_original_file_uri_becomes_a_readable_local_reference()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_query_signatures_delimiters_literal_percent_and_invalid_utf8_are_preserved()`
def readable_link_issues(content: str, *, allow_unencoded_file_uri: bool=False) -> list[str]:
	from .markdown_links import parser as md_parser
	parser = md_parser(preserve_links=True)
	targets, quote_depth = ([], 0)
	html = HTMLReferences(authored_only=True)
	for block in parser.parse(content):
		if 'blockquote_open' == block.type:
			quote_depth += 1
		elif 'blockquote_close' == block.type:
			quote_depth -= 1
		if quote_depth:
			continue
		if 'html_block' == block.type:
			html.feed(block.content)
		for token in block.children or []:
			if 'link_open' == token.type:
				targets.append(token.attrGet('href'))
			elif 'image' == token.type:
				targets.append(token.attrGet('src'))
			elif 'html_inline' == token.type:
				html.feed(token.content)
			elif 'text' == token.type:
				targets.extend(_document_urls(token.content))
	errors = []
	for target in dict.fromkeys(targets + html.links):
		# 2026-10-30
		# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
		# https://github.com/dmitry-ai/harness/issues/21
		if allow_unencoded_file_uri and target.lower().startswith('file:///') and ('%' not in target):
			target_check = re.sub('^file:///+(?=[A-Za-z]:/)', '', target, flags=re.IGNORECASE)
			if readable_reference(target_check) == target_check:
				continue
		readable = readable_reference(target)
		if target != readable:
			errors.append(f'LINK-5: Use a readable document link: {readable} (instead of {target})')
	return errors
class HTMLReferences(HTMLParser):
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :func:`Df.Harness.lib.completion_links.dfh_authored_nonquote_hrefs()`
	# @used-by :func:`check_network()`
	# @used-by :func:`readable_link_issues()`
	# @used-by :func:`references()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__authored_targets()`
	# @see :meth:`html.parser.HTMLParser.__init__()`
	@override
	def __init__(self, *, authored_only=False):
		super().__init__(convert_charrefs=True)
		self.anchors = []
		self.links = []
		self.authored_only = authored_only
		self.literal_depth = 0
	# @used-by :meth:`html.parser.HTMLParser.handle_starttag()`
	# @see :meth:`html.parser.HTMLParser.handle_starttag()`
	@override
	def handle_starttag(self, tag, attrs):
		if self.authored_only and tag in ('pre', 'code', 'blockquote'):
			self.literal_depth += 1
		if self.authored_only and self.literal_depth:
			return
		values = dict(attrs)
		if values.get('id'):
			self.anchors.append(values['id'])
		if 'a' == tag:
			if values.get('name') and values['name'] != values.get('id'):
				self.anchors.append(values['name'])
			if values.get('href'):
				self.links.append(values['href'])
		elif 'img' == tag and values.get('src'):
			self.links.append(values['src'])
	# @used-by :meth:`html.parser.HTMLParser.handle_endtag()`
	# @see :meth:`html.parser.HTMLParser.handle_endtag()`
	@override
	def handle_endtag(self, tag):
		if self.authored_only and tag in ('pre', 'code', 'blockquote'):
			self.literal_depth = max(0, self.literal_depth - 1)
	# @used-by :meth:`html.parser.HTMLParser.handle_data()`
	# @see :meth:`html.parser.HTMLParser.handle_data()`
	@override
	def handle_data(self, data):
		if self.authored_only and (not self.literal_depth):
			self.links.extend(_document_urls(data))
# @used-by :func:`Df.Harness.lib.completion_links.dfh_authored_nonquote_hrefs()`
# @used-by :func:`_document_urls()`
# @used-by :func:`agent_tools.text_sections.mechanical_projection()`
# @used-by :func:`references()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._check_kb_membership()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._collect_client_urls()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._extract_markdown_refs()`
def _bare_urls(text: str):
	for match in re.finditer('https?://[^\\s<>`"\\x00-\\x1f]+', text):
		url = match.group().rstrip('.,;!?')
		for left, right in [('(', ')'), ('[', ']')]:
			while url.endswith(right) and url.count(right) > url.count(left):
				url = url[:-1]
		yield url
# @used-by :func:`readable_link_issues()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__collect_block_targets()`
# @used-by :meth:`HTMLReferences.handle_data()`
def _document_urls(text: str):
	yield from _bare_urls(text)
	for match in re.finditer('(?:file://|[A-Za-z]:[/\\\\])[^\\s<>`"\\x00-\\x1f]+', text):
		yield match.group().rstrip('.,;!?)')
# @used-by :func:`Df.Harness.lib.completion_links.dfh_response_link_issues()`
# @used-by :func:`agent_tools.research.extract_markdown()`
# @used-by :func:`agent_tools.text_sources.check_links()`
# @used-by :func:`agent_tools.text_sources.source_urls()`
# @used-by :func:`validate_content()`
# @used-by :func:`validate_file()`
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_validate_links()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.__validate_doc_or_json_anchor()`
# @used-by :meth:`test_agent_tools.LinkTests.test_code_samples_are_not_document_links()`
# @used-by :meth:`test_agent_tools.LinkTests.test_markdown_reference_links_balanced_parentheses_and_html()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_source_survives_a_renderer_that_encodes_its_href()`
def references(content: str, include_code: bool=False) -> tuple[list[str], list[str]]:
	from .markdown_links import parser as md_parser
	parser = md_parser(allow_file_links=True)
	links = []
	html = HTMLReferences()
	for block in parser.parse(content):
		if 'html_block' == block.type:
			html.feed(block.content)
		depth = 0
		for token in block.children or []:
			if 'link_open' == token.type:
				depth += 1
				links.append(token.attrGet('href'))
			elif 'link_close' == token.type:
				depth -= 1
			elif 'html_inline' == token.type:
				html.feed(token.content)
			elif 'text' == token.type and 0 == depth:
				links.extend(_bare_urls(token.content))
			elif 'code_inline' == token.type and include_code:
				links.extend(_bare_urls(token.content))
	r = (links + html.links, html.anchors)
	return r
# @used-by :func:`validate_file()`
# @used-by :meth:`test_agent_tools.LinkTests.test_invalid_port_is_diagnostic_not_crash()`
# @used-by :meth:`test_agent_tools.LinkTests.test_local_anchors_decode_and_are_case_sensitive()`
# @used-by :meth:`test_agent_tools.LinkTests.test_preserves_valid_urls_and_markdown()`
# @used-by :meth:`test_agent_tools.LinkTests.test_same_id_and_name_on_one_anchor_are_not_duplicates()`
# @used-by :meth:`test_agent_tools.LinkTests.test_unique_urls_is_explicit_policy()`
def validate_content(content: str, *, local_anchors: bool=False, unique_urls: bool=False, include_code: bool=False, readable_links: bool=False) -> list[str]:
	links, anchors = references(content, include_code)
	errors = []
	for anchor, count in Counter(anchors).items():
		if count > 1:
			errors.append(f'Duplicate explicit HTML anchor: {anchor}')
	available_anchors = set(anchors) | heading_anchors(content)
	for url in links:
		try:
			parsed = urlsplit(url)
			if parsed.scheme.lower() in ('http', 'https'):
				if not parsed.hostname or any((c.isspace() for c in url)):
					errors.append(f'Invalid HTTP URL: {url}')
				_ = parsed.port
			elif local_anchors and url.startswith('#') and (unquote(url[1:]) not in available_anchors):
				errors.append(f'Missing local anchor: {url}')
		except ValueError as exc:
			errors.append(f'Invalid URL {url}: {exc}')
	if unique_urls:
		for url, count in Counter(links).items():
			if count > 1 and url.startswith(('http://', 'https://')):
				errors.append(f'Repeated URL ({count}): {url}')
	if readable_links:
		errors.extend(readable_link_issues(content))
	r = errors
	return r
# 2026-11-16
# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
# https://github.com/dmitry-ai/harness/issues/81
# @used-by :func:`agent_tools.research.extract_markdown()`
# @used-by :func:`heading_anchors()`
# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.__markdown_section()`
def parse_markdown_headings(content: str) -> tuple[list[dict], set[str], set[str], str]:
	from .markdown_links import parser as md_parser
	raw_lines = content.splitlines(keepends=True)
	fm_title = ''
	body_text = content
	line_offset = 0
	fm_match = re.match('\\A---[ \\t]*\\r?\\n([^\\r\\n]+(?:\\r?\\n.*?)?)\\r?\\n(?:---|\\.\\.\\.)[ \\t]*(?:\\r?\\n|$)', content)
	if fm_match:
		fm_lines = fm_match.group(1).splitlines()
		valid_yaml = bool(fm_lines) and (not fm_lines[0].lstrip().startswith('#')) and all((re.match('^(?:[A-Za-z0-9_.-]+\\s*:.*|[ \\t]+(?:-|\\S).*|-\\s+.*|[ \\t]*#.*|[ \\t]*)$', ln) for ln in fm_lines)) and any((re.match('^[A-Za-z0-9_.-]+\\s*:', ln) for ln in fm_lines))
		if valid_yaml:
			for fm_line in fm_lines:
				tm = re.match('^title:\\s*(.+?)\\s*$', fm_line)
				if tm:
					fm_title = tm.group(1).strip().strip('"\'')
					break
			line_offset = content[:fm_match.end()].count('\n')
			body_text = ''.join(raw_lines[line_offset:])
	tokens = md_parser(html=False).parse(body_text)
	explicit_counts: Counter = Counter()
	parsed_rows: list[tuple[int, str, str | None, str, int]] = []
	for index, token in enumerate(tokens):
		if 'heading_open' != token.type:
			continue
		inline = tokens[index + 1]
		raw_title = ''.join((t.content for t in inline.children or [] if t.type in ('text', 'code_inline', 'image')))
		unesc_title = html_lib.unescape(raw_title).strip()
		attr_match = re.search('\\s*\\{#([^\\s}]+)\\}\\s*$', unesc_title)
		explicit_id = attr_match.group(1) if attr_match else None
		clean_title = unesc_title[:attr_match.start()].strip() if attr_match else html_lib.unescape(raw_title)
		slug = re.sub('[^\\w\\- ]', '', clean_title.lower()).replace(' ', '-')
		if explicit_id:
			explicit_counts[explicit_id] += 1
		start_line = (token.map[0] if token.map else 0) + line_offset
		parsed_rows.append((int(token.tag[1]), clean_title.strip(), explicit_id, slug, start_line))
	used_slugs: set[str] = set(explicit_counts.keys())
	all_anchors: set[str] = set(explicit_counts.keys())
	headings: list[dict] = []
	for level, clean_title, explicit_id, slug, start_line in parsed_rows:
		sec_anchors: list[str] = []
		if explicit_id:
			sec_anchors.append(explicit_id)
		if slug:
			if slug == explicit_id:
				if slug not in sec_anchors:
					sec_anchors.append(slug)
			else:
				anchor, number = (slug, 0)
				while anchor in used_slugs:
					number += 1
					anchor = f'{slug}-{number}'
				used_slugs.add(anchor)
				all_anchors.add(anchor)
				if anchor not in sec_anchors:
					sec_anchors.append(anchor)
		headings.append({'level': level, 'text': clean_title, 'anchor': explicit_id or (sec_anchors[0] if sec_anchors else None), 'section_anchors': sec_anchors, 'start_line': start_line})
	ambiguous = {aid for aid, cnt in explicit_counts.items() if 1 < cnt}
	doc_title = fm_title or next((h['text'] for h in headings if 1 == h['level'] and h['text']), '') or next((h['text'] for h in headings if h['text']), '')
	return (headings, all_anchors, ambiguous, doc_title)
# 2026-10-14
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
# @used-by :func:`Df.Harness.lib.completion_links.dfh_response_link_issues()`
# @used-by :func:`validate_content()`
# @used-by :func:`validate_file()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.__validate_doc_or_json_anchor()`
def heading_anchors(content: str) -> set[str]:
	return parse_markdown_headings(content)[1]
# 2026-10-11
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_validate_step_cli()`
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_validate_links()`
# @used-by :meth:`Df.Harness.Gate.RulesAuditChecker.RulesAuditChecker.check_links_and_blind_references()`
# @used-by :meth:`Df.Harness.Workflow.KbAuditor.KbAuditor.issues()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.check_commit()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_stage4_docs_document_arch_audit_gate_and_lint_cleanly()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_native_profiles_generates_arch_auditor_for_antigravity_and_codex()`
# @used-by :meth:`test_arch_rules_contract.ArchRulesContractTests.test_architecture_rule_is_compact_always_on_and_passes_doctor_and_rules_audit()`
# @used-by :meth:`test_arch_rules_contract.ArchRulesContractTests.test_df_architecture_skill_discovered_and_lints_cleanly()`
# @used-by :meth:`test_ask_question_clarifications_m8.AskQuestionClarificationsM8Tests.test_skill_and_turn_completion_docs_prohibit_ask_question_stop_gate_bypass()`
# @used-by :meth:`test_ask_question_pre_tool_gate.AskQuestionPreToolGateTests.test_pre_tool_gate_blocks_stop_gate_bypass_and_docs_codify_rule()`
# @used-by :meth:`test_budget_status_scoping.BudgetStatusScopingTests.test_turn_completion_doc_describes_client_artifact_budget_scoping()`
# @used-by :meth:`test_cli_registry.CliRegistryTests.test_modular_docs_and_per_feature_test_rule_valid()`
# @used-by :meth:`test_code_formatting_rules.CodeFormattingRulesContractTests._assert_clean_doc()`
# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_rules_doc_codifies_code4_size_ratchet()`
# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_skill_rules_and_docs_codify_mandatory_separate_companion_tracks()`
# @used-by :meth:`test_df_analysis_rules_contract.DfAnalysisRulesAndSkillContractTests.test_df_analysis_skill_discovered_by_native_profiles_and_lints_cleanly()`
# @used-by :meth:`test_df_analysis_rules_contract.DfAnalysisRulesAndSkillContractTests.test_rules_adapters_and_docs_codify_df_analysis_and_pass_lint()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_docs_and_rules_codify_contract_within_rules_audit_budgets()`
# @used-by :meth:`test_issue_first_rules_contract.IssueFirstRulesAndDocsContractTests.test_rules_skill_and_docs_codify_issue_first_before_tdd_and_pass_lint()`
# @used-by :meth:`test_journal_clarifications_and_disclosure.JournalClarificationsAndDisclosureTests.test_turn_completion_doc_covers_clarifications_header_and_deferral_disclosure()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_exec4_documents_fifo_lease_and_swarm()`
# @used-by :meth:`test_metadata_rules_contract.MetadataRulesAndDocsContractTests.test_rules_skill_and_docs_codify_json_metadata_headers_and_pass_lint()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_df_github_issue_skill_documents_decomposition_and_passes_lint()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_analysis_links_causes_to_concerns_and_methods_to_causes()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_cross_file_markdown_anchors_and_missing_file()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_json_pointer_is_checked()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_windows_file_uris_and_absolute_paths()`
# @used-by :meth:`test_perf_improvement_skill_contract.PerfImprovementSkillContractTests.test_adapters_and_readme_document_skill_and_perf_cli_and_pass_lint()`
# @used-by :meth:`test_perf_improvement_skill_contract.PerfImprovementSkillContractTests.test_perf_improvement_skill_discovered_and_references_pass_lint()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_creation_publishes_supplied_site_and_reinit_keeps_the_card()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_navigation_links_can_address_a_directory()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_source_survives_a_renderer_that_encodes_its_href()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_utf8_anchor_and_balanced_parentheses_need_no_url_encoding()`
# @used-by :meth:`test_repo_link_gate.RepoLinkGateTests.test_cross_repo_relative_link_rejected_while_intra_repo_relative_link_allowed()`
# @used-by :meth:`test_repo_tags_docs.RepoTagsDocsTests.test_rules_and_docs_codify_daily_tagging_and_link6_within_budgets()`
# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_exec4_documents_wait_repo_wait_timeout_and_no_premature_user_escalation()`
# @used-by :meth:`test_rules_architecture_m2.RulesArchitectureM2Tests.test_rules_have_zero_html_comments_valid_links_and_legacy_reference()`
# @used-by :meth:`test_scatter_banner_gate.ScatterBannerGateTests.test_rules_and_skill_codify_file6_banner_and_pass_lint()`
# @used-by :meth:`test_shadow_replay_m3.ShadowReplayM3Tests.test_exec2_rules_and_readme_document_shadow_replay_gate()`
# @used-by :meth:`test_snapshot_latency_and_delegation_policy.SnapshotLatencyAndDelegationPolicyTests.test_delegation_rule_and_worktree_doc_codify_multi_track_policy_and_pass_audits()`
# @used-by :meth:`test_tdd_rules_contract.TddRulesAndDocumentationContractTests.test_rules_and_docs_codify_tdd_contract_and_pass_lint_checks()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_exec5_documents_worktree_and_landing_only_host_mutations()`
def validate_file(file_path: Path, **options) -> list[str]:
	try:
		file_path = Path(file_path).resolve()
		content = file_path.read_text(encoding='utf-8')
		# 2026-11-26 "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs": https://github.com/dmitry-ai/harness/issues/264
		from .repo_link_gate import file_repo_link_issues
		errors = validate_content(content, **options) + file_repo_link_issues(file_path, content)
		for href in references(content, options.get('include_code', False))[0]:
			parsed = urlsplit(href)
			windows_path = bool(re.match('^[A-Za-z]:[/\\\\]', href))
			if parsed.scheme and 'file' != parsed.scheme and (not windows_path) or href.startswith('#'):
				continue
			path_text = unquote(urldefrag(href)[0] if windows_path else parsed.path)
			if 'file' == parsed.scheme:
				if parsed.netloc and 'localhost' != parsed.netloc:
					path_text = parsed.netloc + path_text if re.fullmatch('[A-Za-z]:', parsed.netloc) else f'//{parsed.netloc}{path_text}'
				if re.match('^/[A-Za-z]:/', path_text):
					path_text = path_text[1:]
			if not path_text:
				continue
			target = (file_path.parent / path_text).resolve()
			# 2026-11-21
			# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
			# https://github.com/dmitry-ai/harness/issues/109
			if not target.exists():
				from .journal import resolve_migrated_step_file
				migrated = resolve_migrated_step_file(target)
				target = migrated if migrated.exists() else target
			if not target.exists():
				errors.append(f'Missing local file: {href}')
				continue
			fragment = unquote(parsed.fragment)
			if target.is_dir():
				if fragment:
					errors.append(f'A directory link cannot have a document anchor: {href}')
				continue
			if fragment and target.suffix.lower() in ('.md', '.html', '.htm'):
				other = target.read_text(encoding='utf-8')
				ids = set(references(other)[1]) | heading_anchors(other)
				if fragment not in ids:
					errors.append(f'Missing cross-file anchor: {href}')
			elif fragment and '.json' == target.suffix.lower():
				value = json.loads(target.read_text(encoding='utf-8'))
				try:
					# 2026-10-15
					# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
					# https://github.com/dmitry-ai/harness/issues/4
					from .evidence import resolve_pointer
					resolve_pointer(value, fragment)
				except (KeyError, ValueError, IndexError, TypeError):
					errors.append(f'Missing JSON pointer: {href}')
		r = errors
	except (OSError, UnicodeError, ValueError) as exc:
		r = [f'{file_path}: {exc}']
	return r
@dataclass(frozen=True)
class Page:
	url: str
	status: int
	content_type: str
	text: str
# @used-by :func:`check_network()`
def fetch_page(url: str, timeout: float=15) -> Page:
	if urlsplit(url).scheme not in ('http', 'https'):
		raise ValueError('Only HTTP(S) fetching is supported')
	request = Request(url, headers={'User-Agent': 'ProjectLinkCheck/1.0', 'Accept': 'text/html,application/xhtml+xml,text/markdown;q=0.9,*/*;q=0.8'})
	try:
		response = urlopen(request, timeout=timeout)
	except HTTPError as exc:
		exc.close()
		raise
	with response:
		data = response.read(16 * 1024 * 1024 + 1)
		if len(data) > 16 * 1024 * 1024:
			raise ValueError('Response exceeds 16 MiB')
		charset = response.headers.get_content_charset() or 'utf-8'
		r = Page(response.url, response.status, response.headers.get_content_type(), data.decode(charset, errors='replace'))
	return r
# @used-by :func:`agent_tools.text_sources.check_links()`
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_validate_links()`
# @used-by :meth:`test_agent_tools.LinkTests.test_anchor_html_parser_handles_spacing_entities_and_case()`
# @used-by :meth:`test_agent_tools.LinkTests.test_failed_cached_fetch_reports_each_anchor()`
# @used-by :meth:`test_agent_tools.LinkTests.test_real_http_redirect_anchor_and_404()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids()`
def check_network(urls: list[str], *, anchors: bool=False, timeout: float=15, fetcher=None) -> list[dict]:
	fetcher = fetcher or fetch_page
	cache = {}
	results = []
	for url in dict.fromkeys(urls):
		base, fragment = urldefrag(url)
		if not base.startswith(('http://', 'https://')):
			continue
		if anchors and (not fragment):
			continue
		if base not in cache:
			try:
				cache[base] = fetcher(base, timeout)
			except Exception as exc:
				cache[base] = exc
		page = cache[base]
		if isinstance(page, Exception):
			results.append({'url': url, 'status': 'fetch-error', 'detail': str(page)})
			continue
		status = 'http-ok'
		details = {}
		if not 200 <= page.status < 300:
			status = 'http-error'
		elif anchors:
			if page.content_type in ('text/markdown', 'text/x-markdown'):
				from .research import extract_markdown
				md_info = extract_markdown(page.text)
				md_all = set(md_info['anchors']) - set(md_info['ambiguous_anchors'])
				status = 'found-in-source' if unquote(fragment) in md_all else 'not-found-in-source'
				if 'not-found-in-source' == status:
					avail = sorted(md_all)
					details = {'available_anchors': avail[:100], 'anchor_count': len(avail), 'source_bytes': len(page.text.encode('utf-8'))}
			elif page.content_type not in ('text/html', 'application/xhtml+xml'):
				status = 'not-html'
			elif ':~:text=' in fragment:
				status = 'browser-check-required'
			else:
				html = HTMLReferences()
				html.feed(page.text)
				status = 'found-in-source' if unquote(fragment) in html.anchors else 'not-found-in-source'
				if 'not-found-in-source' == status:
					details = {'available_anchors': html.anchors[:100], 'anchor_count': len(html.anchors), 'source_bytes': len(page.text.encode('utf-8'))}
		results.append({'url': url, 'status': status, 'http_status': page.status, 'final_url': page.url, **details})
	return results
