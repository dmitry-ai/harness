# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from Df.Harness.lib.markdown import dfh_markdown_it_parser
import html as html_lib
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class MarkdownHeadingParser:
	# @used-by :func:`agent_tools.links.heading_anchors()`
	# @used-by :func:`agent_tools.links.parse_markdown_headings()`
	# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.__validate_target_fragment()`
	# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.validate_content()`
	# @used-by :meth:`Df.Harness.Research.MarkdownExtractor.MarkdownExtractor.extract()`
	def __init__(self, content: str) -> None:
		self.__content = content
	# @used-by :meth:`MarkdownHeadingParser.parse()`
	@staticmethod
	def __collect_rows(body_text: str, line_offset: int) -> tuple[list[tuple[int, str, str | None, str, int]], Counter]:
		tokens = dfh_markdown_it_parser(html=False).parse(body_text)
		explicit_counts: Counter = Counter()
		rows: list[tuple[int, str, str | None, str, int]] = []
		for index, token in enumerate(tokens):
			if 'heading_open' == token.type:
				inline = tokens[index + 1]
				raw_title = ''.join((t.content for t in inline.children or [] if t.type in ('text', 'code_inline', 'image')))
				unesc = html_lib.unescape(raw_title).strip()
				attr_m = re.search('\\s*\\{#([^\\s}]+)\\}\\s*$', unesc)
				explicit_id = attr_m.group(1) if attr_m else None
				clean = unesc[:attr_m.start()].strip() if attr_m else html_lib.unescape(raw_title)
				slug = re.sub('[^\\w\\- ]', '', clean.lower()).replace(' ', '-')
				if explicit_id:
					explicit_counts[explicit_id] += 1
				rows.append((int(token.tag[1]), clean.strip(), explicit_id, slug, (token.map[0] if token.map else 0) + line_offset))
		return (rows, explicit_counts)
	# @used-by :meth:`MarkdownHeadingParser.__resolve_anchors()`
	@staticmethod
	def __dedup_slug(slug: str, used_slugs: set[str]) -> str:
		anchor, number = (slug, 0)
		while anchor in used_slugs:
			number += 1
			anchor = f'{slug}-{number}'
		used_slugs.add(anchor)
		return anchor
	# @used-by :meth:`MarkdownHeadingParser.parse()`
	def __extract_frontmatter(self) -> tuple[str, str, int]:
		raw_lines = self.__content.splitlines(keepends=True)
		fm_title, body_text, line_offset = ('', self.__content, 0)
		fm_m = re.match('\\A---[ \\t]*\\r?\\n([^\\r\\n]+(?:\\r?\\n.*?)?)\\r?\\n(?:---|\\.\\.\\.)[ \\t]*(?:\\r?\\n|$)', self.__content)
		if fm_m:
			fm_lines = fm_m.group(1).splitlines()
			valid_yaml = bool(fm_lines) and (not fm_lines[0].lstrip().startswith('#')) and all((re.match('^(?:[A-Za-z0-9_.-]+\\s*:.*|[ \\t]+(?:-|\\S).*|-\\s+.*|[ \\t]*#.*|[ \\t]*)$', ln) for ln in fm_lines)) and any((re.match('^[A-Za-z0-9_.-]+\\s*:', ln) for ln in fm_lines))
			if valid_yaml:
				tm_hit = next((re.match('^title:\\s*(.+?)\\s*$', ln) for ln in fm_lines if re.match('^title:\\s*(.+?)\\s*$', ln)), None)
				fm_title = tm_hit.group(1).strip().strip('"\'') if tm_hit else ''
				line_offset = self.__content[:fm_m.end()].count('\n')
				body_text = ''.join(raw_lines[line_offset:])
		return (fm_title, body_text, line_offset)
	# @used-by :meth:`MarkdownHeadingParser.parse()`
	@classmethod
	def __resolve_anchors(cls, rows: list[tuple[int, str, str | None, str, int]], explicit_counts: Counter) -> tuple[list[dict], set[str]]:
		used_slugs: set[str] = set(explicit_counts.keys())
		all_anchors: set[str] = set(explicit_counts.keys())
		headings: list[dict] = []
		for level, clean_title, explicit_id, slug, start_line in rows:
			sec_anchors: list[str] = [explicit_id] if explicit_id else []
			if slug:
				anchor = slug if slug == explicit_id else cls.__dedup_slug(slug, used_slugs)
				all_anchors.add(anchor)
				if anchor not in sec_anchors:
					sec_anchors.append(anchor)
			headings.append({'level': level, 'text': clean_title, 'anchor': explicit_id or (sec_anchors[0] if sec_anchors else None), 'section_anchors': sec_anchors, 'start_line': start_line})
		return (headings, all_anchors)
	# @used-by :func:`agent_tools.links.heading_anchors()`
	# @used-by :func:`agent_tools.links.parse_markdown_headings()`
	# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.__validate_target_fragment()`
	# @used-by :meth:`Df.Harness.Research.LinkAuditor.LinkAuditor.validate_content()`
	# @used-by :meth:`Df.Harness.Research.MarkdownExtractor.MarkdownExtractor.extract()`
	def parse(self) -> tuple[list[dict], set[str], set[str], str]:
		fm_title, body_text, line_offset = self.__extract_frontmatter()
		rows, explicit_counts = self.__collect_rows(body_text, line_offset)
		headings, all_anchors = self.__resolve_anchors(rows, explicit_counts)
		ambiguous = {aid for aid, cnt in explicit_counts.items() if 1 < cnt}
		doc_title = fm_title or next((h['text'] for h in headings if 1 == h['level'] and h['text']), '') or next((h['text'] for h in headings if h['text']), '')
		return (headings, all_anchors, ambiguous, doc_title)
