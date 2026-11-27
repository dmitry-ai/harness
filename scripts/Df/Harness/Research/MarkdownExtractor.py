# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from Df.Harness.Research.LinkAuditor import LinkAuditor
from Df.Harness.Research.MarkdownHeadingParser import MarkdownHeadingParser
import html as html_lib
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class MarkdownExtractor:
	# @used-by :func:`agent_tools.research.extract_markdown()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_document_text()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.extract()`
	# @used-by :meth:`Df.Harness.Research.NetworkLinkChecker.NetworkLinkChecker.__check_anchor_status()`
	# @used-by :meth:`Df.Harness.Research.ObservationBundleScanner.ObservationBundleScanner.__scan_raw_markdown()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_extractor_json_summarizer_and_challenge_classifier()`
	def __init__(self, text: str) -> None:
		self.__text = text
	# @used-by :meth:`MarkdownExtractor.extract()`
	@staticmethod
	def __build_masked_text(text: str, raw_lines: list[str]) -> str:
		from markdown_it import MarkdownIt
		masked_lines = list(raw_lines)
		for tok in MarkdownIt('commonmark', {'html': True}).parse(text):
			if tok.type in ('fence', 'code_block') and tok.map:
				for li in range(max(0, tok.map[0]), min(len(masked_lines), tok.map[1])):
					masked_lines[li] = ' ' * len(masked_lines[li])
		return re.sub('`+[^`]*`+', lambda m: ' ' * len(m.group(0)), ''.join(masked_lines))
	# @used-by :meth:`MarkdownExtractor.extract()`
	@staticmethod
	def __build_sections(headings_meta: list[dict], raw_lines: list[str], line_offsets: list[int], ambiguous_set: set[str]) -> tuple[list[dict], list[dict], dict, dict]:
		clean_headings, sections, anchor_ranges, anchor_content = ([], [], {}, {})
		for idx, h in enumerate(headings_meta):
			start_line = h['start_line']
			end_line = next((nh['start_line'] for nh in headings_meta[idx + 1:] if nh['level'] <= h['level']), len(raw_lines))
			c_start, c_end = (line_offsets[min(start_line, len(raw_lines))], line_offsets[min(end_line, len(raw_lines))])
			raw_sec = ''.join(raw_lines[start_line:end_line])
			unesc_sec = html_lib.unescape(raw_sec)
			sec_text = raw_sec if unesc_sec == raw_sec else raw_sec + '\n' + unesc_sec
			sec_anchors = [a for a in h['section_anchors'] if a not in ambiguous_set]
			entry = {'level': h['level'], 'text': h['text'], 'anchor': h['anchor'] if h['anchor'] not in ambiguous_set else None, 'ancestor_anchors': [], 'section_anchors': sec_anchors, 'container_anchors': [], 'start': c_start, 'end': c_end}
			clean_headings.append(entry)
			sections.append({**entry, 'content': sec_text})
			for a in h['section_anchors']:
				anchor_ranges.setdefault(a, []).append([c_start, c_end])
				anchor_content.setdefault(a, []).append(sec_text)
		return (clean_headings, sections, anchor_ranges, anchor_content)
	# @used-by :meth:`MarkdownExtractor.extract()`
	@staticmethod
	def __collect_html_anchors(text: str, masked_text: str, html_anchors: list[str], md_anchors: set[str], sections: list[dict], anchor_ranges: dict, anchor_content: dict, ambiguous_set: set[str]) -> None:
		for ha in sorted(set(html_anchors)):
			if ha not in md_anchors:
				pat = re.compile('\\b(?:id|name)=["\\\']' + re.escape(ha) + '["\\\']')
				for m in pat.finditer(masked_text):
					pos = m.start()
					enclosing = next((s for s in reversed(sections) if s['start'] <= pos < s['end']), None)
					s_end = enclosing['end'] if enclosing else len(text)
					seg = text[pos:s_end]
					unesc = html_lib.unescape(seg)
					anchor_ranges.setdefault(ha, []).append([pos, s_end])
					anchor_content.setdefault(ha, []).append(seg if unesc == seg else seg + '\n' + unesc)
				if 1 < len(anchor_ranges.get(ha, [])):
					ambiguous_set.add(ha)
	# @used-by :func:`agent_tools.research.extract_markdown()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_document_text()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.extract()`
	# @used-by :meth:`Df.Harness.Research.NetworkLinkChecker.NetworkLinkChecker.__check_anchor_status()`
	# @used-by :meth:`Df.Harness.Research.ObservationBundleScanner.ObservationBundleScanner.__scan_raw_markdown()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_extractor_json_summarizer_and_challenge_classifier()`
	def extract(self) -> dict:
		headings_meta, md_anchors, md_ambiguous, doc_title = MarkdownHeadingParser(self.__text).parse()
		doc_links, html_anchors = LinkAuditor.references(self.__text)
		raw_lines = self.__text.splitlines(keepends=True)
		line_offsets = [0]
		for ln in raw_lines:
			line_offsets.append(line_offsets[-1] + len(ln))
		masked_text = self.__build_masked_text(self.__text, raw_lines)
		ambiguous_set = set(md_ambiguous) | {a for a, cnt in Counter(html_anchors).items() if 1 < cnt} | (set(html_anchors) & set(md_anchors))
		clean_headings, sections, anchor_ranges, anchor_content = self.__build_sections(headings_meta, raw_lines, line_offsets, ambiguous_set)
		self.__collect_html_anchors(self.__text, masked_text, html_anchors, md_anchors, sections, anchor_ranges, anchor_content, ambiguous_set)
		unesc_full = html_lib.unescape(self.__text)
		word_count = len(re.findall('\\w+', unesc_full))
		h1_count = sum((1 for h in clean_headings if 1 == h.get('level')))
		return {'title': doc_title, 'meta': {}, 'meta_all': {}, 'canonical': [], 'headings': clean_headings, 'anchors': sorted(set(md_anchors) | set(html_anchors)), 'links': [{'href': u, 'text': ''} for u in doc_links], 'scripts': [], 'images': [], 'image_alt_summary': {'total': 0, 'empty_alt': 0, 'filename_like_alt': 0, 'repeated_site_name_alt': 0, 'descriptive_alt': 0}, 'embeds': [], 'word_count': word_count, 'seo_diagnostics': {'h1_count': h1_count, 'missing_h1': 0 == h1_count, 'multiple_h1': 1 < h1_count, 'title_length': len(doc_title), 'overlong_title': 65 < len(doc_title), 'meta_description_length': 0, 'missing_meta_description': True, 'spaced_brand_name': False, 'json_ld_types': [], 'empty_json_ld_description': False, 'insecure_or_relative_json_ld_image': False}, 'json_ld': [], 'sections': sections, 'anchor_ranges': anchor_ranges, 'anchor_content': anchor_content, 'ambiguous_anchors': sorted(ambiguous_set), 'browser_check_required': 0 == word_count, 'text': unesc_full}
