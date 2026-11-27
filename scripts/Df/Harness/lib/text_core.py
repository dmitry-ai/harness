# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from Df.Core.lib.state import df_is_windows
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from agent_tools.runtime import PRIMARY, settings
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
ABBREVIATIONS = {'e.g', 'i.e', 'vs', 'etc', 'inc', 'ltd', 'co', 'no', 'mr', 'mrs', 'dr', 'st', 'fig', 'approx', '\u0442.\u0435', '\u0442.\u0434', '\u0442.\u043f', '\u0434\u0440', '\u0441\u043c', '\u0433', '\u0433\u0433'}
ANCHOR = re.compile('^\\s*<a\\s+name=[\'"]([^\'"]+)[\'"]\\s*>\\s*</a>\\s*$')
ARROW_CONNECTIVE = re.compile('^\\s*(?:because|since|as|although|though|while|so|thus|therefore|hence|which|this means|consequently|as a result|\\u043f\\u043e\\u0442\\u043e\\u043c\\u0443 \\u0447\\u0442\\u043e|\\u0442\\u0430\\u043a \\u043a\\u0430\\u043a|\\u043f\\u043e\\u0441\\u043a\\u043e\\u043b\\u044c\\u043a\\u0443|\\u0445\\u043e\\u0442\\u044f|\\u0441\\u043b\\u0435\\u0434\\u043e\\u0432\\u0430\\u0442\\u0435\\u043b\\u044c\\u043d\\u043e|\\u043f\\u043e\\u044d\\u0442\\u043e\\u043c\\u0443|\\u0447\\u0442\\u043e \\u043e\\u0437\\u043d\\u0430\\u0447\\u0430\\u0435\\u0442)\\b', re.I)
BANS = Path('ꘖ/data/text-bans.json')
BOLD_LEADIN = re.compile('^\\*\\*(?!\\{?\\[§)(?!§)([^*\\n]{2,90})\\*\\*\\s*[:—–]')
FENCE = re.compile('^\\s*(```|~~~)')
HEADING = re.compile('^(#{1,6})\\s+(.*?)\\s*$')
INLINE_LITERAL = re.compile('(`+)(?!`)(.*?)\\1(?!`)|«[^»]*»|“[^”]*”|(?<!\\w)"[^"\\n]+"')
KEPT = re.compile('(?i)\\b(?:\\u043e\\u0441\\u0442\\u0430\\u0432\\u043b\\u0435\\u043d\\w*|\\u043e\\u0441\\u0442\\u0430\\u0432\\u0438\\u043b\\w*|\\u043a\\u0440\\u043e\\u043c\\u0435|\\u0437\\u0430 \\u0438\\u0441\\u043a\\u043b\\u044e\\u0447\\u0435\\u043d\\u0438\\u0435\\u043c|except|kept|retained)\\b')
LEXICON = PRIMARY / 'references/client-text/lexicon.json'
LIST_MARK = re.compile('^\\s*(?:[-*+]|\\d+(?:\\.\\d+)*[.)])\\s+')
PROTECTED_SPAN = re.compile(INLINE_LITERAL.pattern + '|!?\\[[^\\]\\n]*\\]\\((?:<?https?://[^\\s>)]*>?)\\)|<https?://[^>\\n]+>|https?://[^\\s<>"\\\']+|(?<!\\w)"[^"\\n]+"')
REMOVAL = re.compile('(?i)\\b(?:\\u0443\\u0434\\u0430\\u043b[\\u0435\\u0451]\\u043d\\w*|\\u0443\\u0434\\u0430\\u043b\\u0438\\u043b\\w*|\\u0443\\u0431\\u0440\\u0430\\u043d\\w*|\\u0443\\u0431\\u0440\\u0430\\u043b\\w*|\\u0443\\u0441\\u0442\\u0440\\u0430\\u043d[\\u0435\\u0451]\\u043d\\w*|\\u0443\\u0441\\u0442\\u0440\\u0430\\u043d\\u0438\\u043b\\w*|\\u0432\\u044b\\u0447\\u0438\\u0449\\u0435\\u043d\\w*|\\u0432\\u044b\\u0447\\u0438\\u0441\\u0442\\u0438\\u043b\\w*|\\u0432\\u044b\\u0440\\u0435\\u0437\\u0430\\u043d\\w*|\\u0438\\u0441\\u043a\\u043b\\u044e\\u0447[\\u0435\\u0451]\\u043d\\w*|\\u0438\\u0441\\u043a\\u043b\\u044e\\u0447\\u0438\\u043b\\w*|removed|deleted|eliminated|stripped|dropped)\\b')
REPLACED = re.compile('(?i)\\b(?:\\u0437\\u0430\\u043c\\u0435\\u043d\\u0435\\u043d\\w*|\\u0437\\u0430\\u043c\\u0435\\u043d\\u0451\\u043d\\w*|\\u0437\\u0430\\u043c\\u0435\\u043d\\u0438\\u043b\\w*|replaced)\\b')
THRESHOLDS = {'sentence_words': 60, 'code_spans': 8, 'parentheses': 3, 'bold_spans': 3, 'heading_words': 8, 'grep_literal': 100}
# @used-by :func:`dfh_scan()`
def _classify_unclosed_line(raw: str) -> str:
	if not raw.strip():
		r = 'blank'
	elif re.fullmatch('\\s*<!--.*-->\\s*', raw):
		r = 'comment'
	elif ANCHOR.match(raw):
		r = 'anchor'
	elif HEADING.match(raw):
		r = 'heading'
	elif raw.lstrip().startswith('>'):
		r = 'quote'
	elif re.match('^\\s*(?:-{3,}|\\*{3,}|_{3,})\\s*$', raw):
		r = 'hr'
	else:
		r = 'prose'
	return r
# @used-by :func:`dfh_find_bans()`
def _load_ban_candidates(paths) -> list:
	result = []
	for candidate in paths:
		if candidate.is_file():
			data = json.loads(candidate.read_text(encoding='utf-8'))
			result.extend(data.get('bans', []) if isinstance(data, dict) else data)
	return result
# @used-by :func:`dfh_command_blocks()`
def _read_quoted_output(lines: list[Line], cursor: int, default_end: int) -> tuple[list[str], list[str], int]:
	expected, presentation, output_end = ([], [], default_end)
	while cursor < len(lines) and lines[cursor].kind in ('blank', 'quote', 'heading', 'anchor'):
		if 'quote' == lines[cursor].kind:
			presentation.append(lines[cursor].raw)
			expected.append(dfh_plain(lines[cursor].raw))
			output_end = lines[cursor].no
		cursor += 1
	return (expected, presentation, output_end)
# @used-by :func:`Df.Harness.lib.text_sections.dfh_proposal_number_refs()`
# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__check_conditional_line()`
# @used-by :meth:`Df.Harness.Text.Article.GraphAuditor.GraphAuditor.__record_prose_refs()`
# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_line_references()`
# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.__check_prose_format()`
# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.__check_sequence()`
# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.check_references()`
# @used-by :meth:`Df.Harness.Text.ProseLinter.ProseLinter.__check_prose_details()`
def dfh_author_text(raw: str) -> str:
	out = [' '] * len(raw)
	for start, end in dfh_prose_spans(raw):
		out[start:end] = raw[start:end]
	return ''.join(out)
# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_line_references()`
def dfh_bold_spans(raw: str) -> list[tuple[int, int]]:
	marks = [m.start() for m in re.finditer('\\*\\*', raw)]
	return [(marks[i], marks[i + 1]) for i in range(0, len(marks) - 1, 2)]
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.check()`
# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
# @used-by :meth:`test_text_core.ReplayTests.test_changed_blocks_need_receipts_unchanged_moves_do_not()`
def dfh_changed_command_lines(text: str, previous: str | None=None) -> list[int]:
	old = Counter(((b['command_sha256'], tuple(b['expected'])) for b in dfh_command_blocks(previous or '')))
	changed = []
	for block in dfh_command_blocks(text):
		identity = (block['command_sha256'], tuple(block['expected']))
		if old[identity]:
			old[identity] -= 1
		else:
			changed.append(block['line'])
	return changed
# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
def dfh_check_markdown_lists(lines: list[Line], findings: list[Finding]) -> None:
	for line in lines:
		if 'prose' != line.kind:
			continue
		match = re.match('^\\s*(\\d+)[.)]\\s+', line.raw)
		if match and '1' != match.group(1):
			findings.append(Finding('error', 'LIST-AUTONUM', line.no, 'use the native Markdown 1. marker for ordinary list items', line.raw[:80]))
# @used-by :func:`dfh_detect_language()`
# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_title()`
# @used-by :meth:`Df.Harness.Text.ProseLinter.ProseLinter.check()`
# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
def dfh_clean(raw: str) -> str:
	s = LIST_MARK.sub('', raw)
	s = INLINE_LITERAL.sub(lambda m: ' CODE ' if m.group(1) else ' QUOTE ', s)
	s = re.sub('\\[§[^\\]]*\\]\\([^)]*\\)', ' REF ', s)
	s = re.sub('§§?@[\\w.\\-]+(?:-@[\\w.\\-]+)?', ' REF ', s)
	s = re.sub('!?\\[([^\\]]*)\\]\\((?:<[^>]*>|[^)\\s]*)\\)', lambda m: ' URL ' if not re.search('\\s', m.group(1).replace('**', '')) else m.group(1), s)
	s = re.sub('<https?://[^>]+>|https?://\\S+', ' URL ', s)
	s = re.sub('«[^»]*»|“[^”]*”', ' QUOTE ', s)
	s = s.replace('**', '').replace('__', '')
	s = re.sub('(?<![\\w*])\\*(?!\\s)([^*\\n]+?)\\*(?!\\w)', '\\1', s)
	s = re.sub('<[^>\\n]+>', ' ', s)
	return re.sub('\\s+', ' ', s).strip()
# @used-by :func:`dfh_changed_command_lines()`
# @used-by :meth:`Df.Harness.Text.CommandReplayer.CommandReplayer.replay()`
def dfh_command_blocks(text: str) -> list[dict]:
	lines, blocks, index = (dfh_scan(text), [], 0)
	while index < len(lines):
		if 'fence' != lines[index].kind or not re.match('^\\s*(?:`{3,}|~{3,})\\s*(bash|sh|shell)\\s*$', lines[index].raw):
			index += 1
			continue
		first = lines[index].no
		index += 1
		body = []
		while index < len(lines) and 'code' == lines[index].kind:
			body.append(lines[index].raw)
			index += 1
		closed = index < len(lines) and 'fence' == lines[index].kind
		index += int(closed)
		expected, presentation, output_end = _read_quoted_output(lines, index, lines[index - 1].no if index else first)
		command = '\n'.join(body)
		blocks.append({'line': first, 'end': output_end, 'command': command, 'command_sha256': hashlib.sha256(command.encode('utf-8')).hexdigest(), 'expected': expected, 'presentation': '\n'.join(presentation), 'closed': closed})
	return blocks
# @used-by :meth:`Df.Harness.Text.CommandReplayer.CommandReplayer.replay()`
# @used-by :meth:`test_text_core.SharedMechanicsTests.test_shell_can_be_configured()`
def dfh_default_shell() -> str:
	from agent_tools.path_registry import tool_list
	configured = os.environ.get('DF_TEXT_BASH') or os.environ.get('CYGWIN_BASH') or settings().get('client_text', {}).get('bash')
	if configured:
		r = configured
	else:
		win_cand = next((c for c in tool_list('bash_candidates') if Path(c).is_file()), None) if df_is_windows() else None
		found = win_cand or shutil.which('bash')
		if found:
			r = found
		else:
			git = shutil.which('git')
			git_cands = (Path(git).resolve().parents[1] / 'bin/bash.exe', Path(git).resolve().parents[1] / 'usr/bin/bash.exe') if git else ()
			r = next((str(c) for c in git_cands if c.is_file()), 'bash')
	return r
# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.lint()`
# @used-by :meth:`Df.Harness.Text.ResponseChecker.ResponseChecker.check()`
# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
def dfh_detect_language(text: str) -> str:
	letters = re.findall('[A-Za-z\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451]', dfh_clean(text))
	cyrillic = sum((1 for ch in letters if re.match('[\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451]', ch)))
	return 'ru' if letters and cyrillic / len(letters) > 0.3 else 'en'
# @used-by :meth:`Df.Harness.Text.ProseLinter.ProseLinter.__check_bans()`
# @used-by :meth:`Df.Harness.Text.ProseLinter.ProseLinter.__check_lexicon()`
# @used-by :meth:`Df.Harness.Text.ProseLinter.ProseLinter.__check_prose_details()`
def dfh_excerpt(text: str, match, width: int=40) -> str:
	start, end = (max(match.start() - width, 0), min(match.end() + width, len(text)))
	return ('…' if start else '') + text[start:end] + ('…' if end < len(text) else '')
# @used-by :func:`Df.Harness.lib.text_sections.dfh_proposal_number_refs()`
# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.__convert_bare()`
# @used-by :meth:`Df.Harness.Text.Article.StructureAuditor.StructureAuditor.__check_line_references()`
# @used-by :meth:`Df.Harness.Text.MechanicalProjector.MechanicalProjector.__project_renumber()`
# @used-by :meth:`Df.Harness.Text.Proposal.SourceExporter.SourceExporter.__replace_refs()`
# @used-by :meth:`Df.Harness.Text.ProseLinter.ProseLinter.__check_prose_details()`
def dfh_external_section_ref(text: str, match) -> bool:
	return None is not dfh_reference_document(text, match)
# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.lint()`
def dfh_find_bans(path: Path | None) -> list:
	r: list = []
	if None is not path:
		resolved = path.resolve()
		for folder in (resolved.parent, *resolved.parents):
			r = _load_ban_candidates((folder / BANS, folder / Path('ꘖ/data/article-bans.json')))
			if r:
				break
		if not r:
			from agent_tools.storage import data_dir_for
			dd = data_dir_for(path)
			r = _load_ban_candidates((dd / 'text-bans.json', dd / 'article-bans.json'))
	return r
# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.lint()`
# @used-by :meth:`Df.Harness.Text.ResponseChecker.ResponseChecker.check()`
# @used-by :meth:`test_df_article.LexiconAndProjectionTests.test_lexicon_entries_are_complete_and_compile()`
def dfh_load_lexicon(path=None):
	return json.loads(Path(path or LEXICON).read_text(encoding='utf-8'))['entries']
# @used-by :meth:`Df.Harness.Text.KeyedProseRewriter.KeyedProseRewriter.__convert()`
# @used-by :meth:`Df.Harness.Text.MechanicalProjector.MechanicalProjector.__project_renumber()`
def dfh_normalize_external_refs(raw: str, *, changes=None, line=None) -> str:
	# @used-by :func:`dfh_normalize_external_refs()`
	def segment(value: str) -> str:
		# @used-by :func:`dfh_normalize_external_refs()`
		def replace(match) -> str:
			document = dfh_reference_document(value, match)
			if None is document:
				r = match.group()
			else:
				if None is not changes:
					number = re.match('\\d+(?:\\.\\d+)*', value[match.end():]).group()
					changes.append({'line': line, 'document': document, 'before': match.group() + number, 'after': match.group(1) + number})
				r = match.group(1)
			return r
		return re.sub('(§{1,2})[ \\t]+(?=\\d)', replace, value)
	return dfh_transform_prose(raw, segment)
# @used-by :meth:`Df.Harness.Text.ResponseChecker.ResponseChecker.__check_duplicates()`
def dfh_normalized(text: str) -> str:
	return re.sub('\\s+', ' ', text).strip()
# @used-by :meth:`Df.Harness.Text.CommandReplayer.CommandReplayer.__execute()`
# @used-by :meth:`Df.Harness.Text.CommandReplayer.CommandReplayer.__run_block()`
def dfh_output_lines(value: str) -> list[str]:
	lines = [line.rstrip() for line in value.splitlines()]
	while lines and (not lines[-1]):
		lines.pop()
	return lines
# @used-by :func:`_read_quoted_output()`
def dfh_plain(value: str) -> str:
	value = re.sub('^\\s*>\\s?', '', value).rstrip()
	value = re.sub('^\\s*(?:\\d+[.)]|[-*+])\\s+', '', value)
	value = re.sub('\\[([^\\]]+)\\]\\((?:<[^>]+>|[^)]*)\\)', '\\1', value)
	value = re.sub('(`+)(.*?)\\1', '\\2', value)
	return '' if '<empty response>' == value else value
# @used-by :func:`dfh_author_text()`
# @used-by :func:`dfh_transform_prose()`
def dfh_prose_spans(raw: str):
	start = 0
	for match in PROTECTED_SPAN.finditer(raw):
		if match.start() > start:
			yield (start, match.start())
		start = match.end()
	if start < len(raw):
		yield (start, len(raw))
# @used-by :func:`dfh_external_section_ref()`
# @used-by :func:`dfh_normalize_external_refs()`
def dfh_reference_document(text: str, match) -> str | None:
	prefix = re.search('\\b(?:(?:RFC|ISO(?:/IEC)?|IEC|IEEE|EN)\\s+\\d+(?::\\d+)?|\\d+\\s+(?:CCR|CFR|U\\.?S\\.?C\\.?))\\s*$', text[:match.start()], re.I)
	return ' '.join(prefix.group().split()) if prefix else None
# @used-by :func:`Df.Harness.lib.text_sections._addressed_content_blocks()`
# @used-by :func:`Df.Harness.lib.text_sections.dfh_scope_blocks()`
# @used-by :func:`agent_tools.article.render_map()`
# @used-by :func:`agent_tools.text_sources.check_links()`
# @used-by :func:`agent_tools.text_sources.source_urls()`
# @used-by :func:`dfh_command_blocks()`
# @used-by :meth:`Df.Harness.Grounding.ProbabilityClaimChecker.ProbabilityClaimChecker.check()`
# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.render()`
# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.export()`
# @used-by :meth:`Df.Harness.Text.MechanicalProjector.MechanicalProjector.project()`
# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.lint()`
# @used-by :meth:`Df.Harness.Text.Proposal.Parser.Parser.__init__()`
# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.render()`
# @used-by :meth:`Df.Harness.Text.Proposal.SourceExporter.SourceExporter.export()`
# @used-by :meth:`Df.Harness.Text.ResponseChecker.ResponseChecker.check()`
# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
# @used-by :meth:`test_source_admission.LinkPresentationTests.findings()`
# @used-by :meth:`test_text_core.SharedMechanicsTests.test_fence_contents_end_only_at_matching_fence()`
# @used-by :meth:`test_text_core.SharedMechanicsTests.test_hashed_asset_is_a_warning_not_proof_of_an_error()`
def dfh_scan(text: str) -> list[Line]:
	lines, fenced = ([], None)
	for no, raw in enumerate(text.splitlines(), 1):
		opening = re.match('^ {0,3}(`{3,}|~{3,})(.*)$', raw)
		closing = re.fullmatch(' {0,3}' + re.escape(fenced[0]) + '{' + str(fenced[1]) + ',}\\s*', raw) if fenced else None
		if closing:
			lines.append(Line(no, raw, 'fence'))
			fenced = None
		elif fenced:
			lines.append(Line(no, raw, 'code'))
		elif opening and (not (opening.group(1).startswith('`') and '`' in opening.group(2))):
			lines.append(Line(no, raw, 'fence'))
			fenced = (opening.group(1)[0], len(opening.group(1)))
		else:
			lines.append(Line(no, raw, _classify_unclosed_line(raw)))
	return lines
# @used-by :meth:`Df.Harness.Text.ProseLinter.ProseLinter.__check_lexicon()`
# @used-by :meth:`Df.Harness.Text.ProseLinter.ProseLinter.__check_sentence_limits()`
# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
def dfh_sentences(cleaned: str) -> list[str]:
	parts, start = ([], 0)
	for match in re.finditer('[.!?](?=\\s+[A-Z\\u0410-\\u042f\\u0401«"(\\[])', cleaned):
		word = re.findall('[\\w.]+$', cleaned[start:match.start()])
		token = (word[-1] if word else '').lower().rstrip('.')
		if token in ABBREVIATIONS or (1 == len(token) and token.isalpha()):
			continue
		parts.append(cleaned[start:match.end()].strip())
		start = match.end()
	tail = cleaned[start:].strip()
	return parts + ([tail] if tail else [])
# @used-by :func:`dfh_normalize_external_refs()`
# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.__export_line()`
# @used-by :meth:`Df.Harness.Text.KeyedProseRewriter.KeyedProseRewriter.rewrite()`
# @used-by :meth:`Df.Harness.Text.Proposal.SourceExporter.SourceExporter.export()`
def dfh_transform_prose(raw: str, transform) -> str:
	pieces, cursor = ([], 0)
	for start, end in dfh_prose_spans(raw):
		pieces.extend((raw[cursor:start], transform(raw[start:end])))
		cursor = end
	pieces.append(raw[cursor:])
	return ''.join(pieces)
