# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from Df.Harness.Text.Article.Section import Section
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from Df.Harness.lib.text_core import ANCHOR, HEADING, LIST_MARK, THRESHOLDS, dfh_author_text, dfh_bold_spans, dfh_clean, dfh_external_section_ref
from Df.Harness.lib.text_sections import ANCHOR_LINK, ARTICLE_BARE_REF, ARTICLE_SECTION_LABEL, PART, dfh_part_at, dfh_section_at, dfh_validate_ref_range
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class StructureAuditor:
	# @used-by :func:`agent_tools.article.check_structure()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.render()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def __init__(self, lines: list[Line], sections: list[Section], findings: list[Finding]) -> None:
		self.__lines = lines
		self.__sections = sections
		self.__findings = findings
	# @used-by :meth:`StructureAuditor.__check_line_references()`
	def __check_anchor_link(self, line: Line, match, anchors: dict, by_key: dict, spans: list) -> None:
		label, target = match.groups()
		if target not in anchors:
			self.__findings.append(Finding('error', 'REF-DANGLING', line.no, f'#{target} does not exist', match.group(0)))
		elif label.strip().startswith('§'):
			parsed = ARTICLE_SECTION_LABEL.match(label.replace('**', '').strip())
			if not parsed:
				self.__findings.append(Finding('error', 'REF-LABEL', line.no, 'unparseable § label', match.group(0)))
			else:
				self.__check_section_link(line, match, target, parsed, by_key, spans)
	# @used-by :meth:`StructureAuditor.audit()`
	def __check_group_counts(self) -> None:
		for section in self.__sections:
			match = re.search('\\((\\d+)(?:\\s+[^()]*)?\\)\\s*$', section.title or '')
			if not match:
				continue
			expected = int(match.group(1))
			own = [line for line in self.__lines if section.line < line.no <= section.end]
			items = [line for line in own if line.kind in ('prose', 'quote') and LIST_MARK.match(re.sub('^\\s*>\\s?', '', line.raw))]
			actual = len(items) if items else self.__child_group_count(section)
			if None is not actual and actual != expected:
				self.__findings.append(Finding('error', 'GROUP-COUNT', section.line, f'heading declares {expected} objects, displayed group contains {actual}', section.title or ''))
	# @used-by :meth:`StructureAuditor.audit()`
	def __check_line_references(self, anchors: dict, by_key: dict) -> None:
		for line in self.__lines:
			if line.kind not in ('prose', 'heading'):
				continue
			spans, visible, linked_spans = (dfh_bold_spans(line.raw), dfh_author_text(line.raw), [])
			for match in ANCHOR_LINK.finditer(visible):
				linked_spans.append(match.span())
				self.__check_anchor_link(line, match, anchors, by_key, spans)
			for match in ARTICLE_BARE_REF.finditer(visible):
				if not dfh_external_section_ref(visible, match) and (not any((start <= match.start() < end for start, end in linked_spans))):
					self.__findings.append(Finding('error', 'REF-BARE', line.no, 'article section reference needs a working anchor link', match.group(0)))
			if re.search('§§?@|\\]\\(#@', visible):
				self.__findings.append(Finding('error', 'KEY-UNRENDERED', line.no, 'unrendered keyed reference remains in the numbered article', line.raw[:80]))
	# @used-by :meth:`StructureAuditor.audit()`
	def __check_parts_and_addressing(self) -> None:
		parts = [m.group(1) for line in self.__lines if 'heading' == line.kind and '#' == HEADING.match(line.raw).group(1) for m in (PART.match(HEADING.match(line.raw).group(2)),) if m]
		if ['I', 'II'] != parts:
			self.__findings.append(Finding('error', 'STRUCT-PARTS', 1, 'article requires exactly two ordered parts: # I. Analysis and # II. Recommendations'))
		if not self.__sections:
			self.__findings.append(Finding('error', 'STRUCT-EMPTY', 1, 'article has no addressed numbered sections'))
		for line in self.__lines:
			if line.kind not in ('prose', 'quote', 'fence', 'code'):
				continue
			section = dfh_section_at(self.__sections, line.no)
			if None is section or section.part != dfh_part_at(self.__lines, line.no):
				self.__findings.append(Finding('error', 'STRUCT-UNADDRESSED', line.no, 'article content must belong to a numbered section', line.raw[:80]))
	# @used-by :meth:`StructureAuditor.__check_anchor_link()`
	def __check_section_link(self, line: Line, match, target: str, parsed, by_key: dict, spans: list) -> None:
		label_part = parsed.group(1) or dfh_part_at(self.__lines, line.no)
		expected = f'{label_part}.{parsed.group(2)}' if label_part else parsed.group(2)
		if expected != target.removeprefix('§'):
			self.__findings.append(Finding('error', 'REF-LABEL', line.no, f'label points to {expected}, link goes to #{target}', match.group(0)))
		if parsed.group(4):
			end_part = parsed.group(3) or label_part
			endpoint = f'{end_part}.{parsed.group(4)}' if end_part else parsed.group(4)
			dfh_validate_ref_range(expected, endpoint, by_key, self.__findings, line.no, match.group(0), order_key=lambda k: by_key[k].line, allow_same=True, start_checked=True, end_prefix='range endpoint §')
		if 'heading' != line.kind and (not any((a < match.start() < b for a, b in spans))):
			self.__findings.append(Finding('warning', 'REF-BOLD', line.no, 'section reference is not bold: **[§N](#P.N)**', match.group(0)))
	# @used-by :meth:`StructureAuditor.audit()`
	def __check_sections(self) -> None:
		for section in self.__sections:
			if None is section.anchor:
				self.__findings.append(Finding('error', 'ANCHOR-MISSING', section.line, f"expected <a name='{section.key}'></a> right after the heading"))
			elif section.anchor not in (section.key, '§' + section.key):
				self.__findings.append(Finding('error', 'ANCHOR-MISMATCH', section.line, f'anchor {section.anchor} does not match section {section.key}'))
			if section.title:
				self.__check_title(section)
	# @used-by :meth:`StructureAuditor.__check_sections()`
	def __check_title(self, section: Section) -> None:
		title = section.title or ''
		plain = re.sub('\\(\\s*\\d+[^)]*\\)', '', dfh_clean(title)).strip()
		words = re.findall("[A-Za-z\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u0451][\\w'’-]*", plain)
		if ',' in plain and re.search('\\band\\b|&|\\b\\u0438\\b', plain):
			self.__findings.append(Finding('error', 'HEADING-ENUM', section.line, 'heading enumerates several topics: one section — one claim; split it', title))
		if len(words) > THRESHOLDS['heading_words']:
			self.__findings.append(Finding('warning', 'HEADING-LONG', section.line, f'{len(words)} words in a heading; 2725 uses a bare number or a short group label', title))
		capital = [w for w in words[1:] if 3 < len(w) and w[0].isupper() and (not w.isupper())]
		long_words = [w for w in words[1:] if 3 < len(w)]
		if 2 <= len(capital) and len(capital) * 2 > len(long_words):
			self.__findings.append(Finding('warning', 'HEADING-TITLECASE', section.line, 'Title Case heading (WP:AITITLECASE)', title))
	# @used-by :meth:`StructureAuditor.__check_group_counts()`
	@staticmethod
	def __child_group_count(section: Section) -> int | None:
		r = None
		if section.children:
			child_counts = [re.search('\\((\\d+)(?:\\s+[^()]*)?\\)\\s*$', child.title or '') for child in section.children]
			if all(child_counts):
				r = sum((int(child.group(1)) for child in child_counts))
		return r
	# @used-by :meth:`StructureAuditor.audit()`
	def __collect_anchors(self) -> dict[str, int]:
		anchors: dict[str, int] = {}
		for line in self.__lines:
			if 'anchor' == line.kind:
				name = ANCHOR.match(line.raw).group(1)
				if name in anchors:
					self.__findings.append(Finding('error', 'ANCHOR-DUP', line.no, f'duplicate anchor {name}', line.raw))
				anchors[name] = line.no
		return anchors
	# @used-by :func:`agent_tools.article.check_structure()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.render()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def audit(self) -> None:
		self.__check_parts_and_addressing()
		anchors = self.__collect_anchors()
		self.__check_sections()
		self.__check_line_references(anchors, {section.key: section for section in self.__sections})
		self.__check_group_counts()
