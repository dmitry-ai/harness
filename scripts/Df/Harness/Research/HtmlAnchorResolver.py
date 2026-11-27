# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_WRAPPER_SKIP = frozenset({'html', 'body', 'main', 'footer', 'nav', 'aside'})
_CONTAINER_SKIP = frozenset({'html', 'body', 'main', 'header', 'footer', 'nav', 'aside'})
class HtmlAnchorResolver:
	# @used-by :meth:`Df.Harness.Research.HtmlData.HtmlData.result()`
	def __init__(self, plain: str, anchors: list[str], anchor_ranges: dict, section_ranges: list[dict]) -> None:
		self.__plain = plain
		self.__plain_len = len(plain)
		self.__anchors = anchors
		self.__anchor_ranges = anchor_ranges
		self.__section_ranges = section_ranges
	# @used-by :meth:`HtmlAnchorResolver.__attach_empty_anchor()`
	def __after_heading_blank(self, h: dict, sp: dict, a_start: int) -> bool:
		head_end = h['start'] if None is h.get('_head_end') else h['_head_end']
		sec_end = self.__plain_len if None is h['end'] else h['end']
		return head_end <= a_start < sec_end and '' == self.__plain[head_end:a_start].strip() and self.__same_parent(sp, h)
	# @used-by :meth:`HtmlAnchorResolver.__attach_empty_anchor()`
	# @used-by :meth:`HtmlAnchorResolver.__attach_glyph_anchor()`
	# @used-by :meth:`HtmlAnchorResolver.__section_frame_candidates()`
	@staticmethod
	def __append_unique(items: list[str], value: str) -> None:
		if value not in items:
			items.append(value)
	# @used-by :meth:`HtmlAnchorResolver.__attach_sibling_anchors()`
	def __attach_empty_anchor(self, anchor: str, sp: dict, a_start: int, a_end: int, sec_lists: list[list[str]]) -> None:
		next_idx = next((idx for idx, h in enumerate(self.__section_ranges) if a_end <= h['start'] and '' == self.__plain[a_end:h['start']].strip() and self.__same_parent(sp, h)), None)
		if None is not next_idx:
			self.__append_unique(sec_lists[next_idx], anchor)
		else:
			hit = next((idx for idx, h in enumerate(self.__section_ranges) if self.__after_heading_blank(h, sp, a_start)), None)
			if None is not hit:
				self.__append_unique(sec_lists[hit], anchor)
	# @used-by :meth:`HtmlAnchorResolver.__attach_sibling_anchors()`
	def __attach_glyph_anchor(self, anchor: str, sp: dict, a_start: int, sec_lists: list[list[str]]) -> None:
		prev_idx = next((idx for idx in range(len(self.__section_ranges) - 1, -1, -1) if self.__follows_heading(self.__section_ranges[idx], sp, a_start)), None)
		if None is not prev_idx:
			self.__append_unique(sec_lists[prev_idx], anchor)
	# @used-by :meth:`HtmlAnchorResolver.resolve()`
	def __attach_sibling_anchors(self, ambiguous_set: set[str], claimed: set[str], sec_lists: list[list[str]]) -> None:
		for anchor, span_objs in self.__anchor_ranges.items():
			if anchor not in ambiguous_set and anchor not in claimed and 1 == len(span_objs):
				sp = span_objs[0]
				if (not sp.get('hidden')) and sp.get('tag') in ('a', 'span'):
					a_start, a_end = (sp['start'], self.__plain_len if None is sp['end'] else sp['end'])
					seg = self.__plain[a_start:a_end]
					if '' == self.__strip_glyphs(seg):
						if '' != seg.strip():
							self.__attach_glyph_anchor(anchor, sp, a_start, sec_lists)
						else:
							self.__attach_empty_anchor(anchor, sp, a_start, a_end, sec_lists)
	# @used-by :meth:`HtmlAnchorResolver.resolve()`
	def __build_sections(self, sec_lists: list[list[str]], cont_lists: list[list[str]], raw_ranges: dict, ambiguous_set: set[str]) -> tuple[list[dict], list[dict]]:
		clean_headings: list[dict] = []
		sections: list[dict] = []
		for idx, h in enumerate(self.__section_ranges):
			sec_end = self.__plain_len if None is h['end'] else h['end']
			expanded = self.__expand_section_anchors(sec_lists[idx], raw_ranges, ambiguous_set)
			cont_valid = [a for a in cont_lists[idx] if a not in ambiguous_set]
			base_h = {k: v for k, v in h.items() if not k.startswith('_')}
			clean_headings.append({**base_h, 'end': sec_end, 'section_anchors': expanded, 'container_anchors': cont_valid})
			sections.append({**base_h, 'end': sec_end, 'section_anchors': expanded, 'container_anchors': cont_valid, 'content': self.__plain[h['start']:sec_end]})
		return (clean_headings, sections)
	# @used-by :meth:`HtmlAnchorResolver.__section_frame_candidates()`
	def __classify_frame(self, h: dict, frame: dict, head_end: int, sec_end: int) -> str | None:
		r: str | None = None
		f_start, f_end = (frame['start'], self.__plain_len if None is frame['end'] else frame['end'])
		if self.__is_frame_eligible(h, frame, f_start, f_end):
			if frame['tag'] not in _WRAPPER_SKIP and '' == self.__strip_glyphs(self.__plain[head_end:f_end]):
				r = 'section'
			elif frame['tag'] not in _CONTAINER_SKIP:
				if '' == self.__strip_glyphs(self.__plain[min(f_end, sec_end):max(f_end, sec_end)]):
					r = 'section'
				elif head_end < f_end <= sec_end:
					r = 'container'
		return r
	# @used-by :meth:`HtmlAnchorResolver.resolve()`
	def __collect_section_lists(self) -> tuple[list[list[str]], list[list[str]], set[str]]:
		sec_lists: list[list[str]] = []
		cont_lists: list[list[str]] = []
		claimed: set[str] = set()
		for h in self.__section_ranges:
			cands, cont_cands = self.__section_frame_candidates(h, claimed)
			sec_lists.append(cands)
			cont_lists.append(cont_cands)
		return (sec_lists, cont_lists, claimed)
	# @used-by :meth:`HtmlAnchorResolver.__section_frame_candidates()`
	@staticmethod
	def __direct_anchors(h: dict) -> list[str]:
		r = [h['anchor']] if h.get('anchor') else []
		r.extend(h.get('_child_anchors') or [])
		return r
	# @used-by :meth:`HtmlAnchorResolver.__build_sections()`
	@staticmethod
	def __expand_section_anchors(anchors: list[str], raw_ranges: dict, ambiguous_set: set[str]) -> list[str]:
		expanded: list[str] = []
		for a in anchors:
			if a not in ambiguous_set and a not in expanded:
				expanded.append(a)
			if a.startswith('user-content-') and 13 < len(a):
				alias = a[13:]
				if (alias not in raw_ranges or alias in anchors) and alias not in ambiguous_set and (alias not in expanded):
					expanded.append(alias)
		return expanded
	# @used-by :meth:`HtmlAnchorResolver.__attach_glyph_anchor()`
	def __follows_heading(self, h: dict, sp: dict, a_start: int) -> bool:
		head_end = h['start'] if None is h.get('_head_end') else h['_head_end']
		return head_end <= a_start and '' == self.__plain[head_end:a_start].strip() and self.__same_parent(sp, h)
	# @used-by :meth:`HtmlAnchorResolver.__classify_frame()`
	def __is_frame_eligible(self, h: dict, frame: dict, f_start: int, f_end: int) -> bool:
		top_only = all((oh is h or oh['level'] > h['level'] for oh in self.__section_ranges if f_start <= oh['start'] and (oh['start'] if None is oh.get('_head_end') else oh['_head_end']) <= f_end))
		is_full_doc = '' == self.__strip_glyphs(self.__plain[:f_start]) and '' == self.__strip_glyphs(self.__plain[f_end:])
		full_blocked = is_full_doc and frame['tag'] not in ('section', 'article')
		return top_only and (not full_blocked) and '' == self.__strip_glyphs(self.__plain[f_start:h['start']])
	# @used-by :meth:`HtmlAnchorResolver.resolve()`
	def __merge_github_aliases(self, raw_ranges: dict, ambiguous_set: set[str]) -> tuple[dict, dict, set[str]]:
		anchor_ranges = dict(raw_ranges)
		anchor_content = {anchor: [self.__plain[s:e] for s, e in ranges] for anchor, ranges in raw_ranges.items()}
		all_anchors = set(self.__anchors)
		gh_aliases: dict[str, list[str]] = {}
		for anchor in sorted(set(self.__anchors)):
			if anchor.startswith('user-content-') and 13 < len(anchor):
				gh_aliases.setdefault(anchor[13:], []).append(anchor)
		for alias, sources in gh_aliases.items():
			if alias not in raw_ranges:
				all_anchors.add(alias)
				merged = [rng for src in sources for rng in raw_ranges.get(src, [])]
				anchor_ranges[alias] = merged
				anchor_content[alias] = [self.__plain[s:e] for s, e in merged]
				if 1 < len(merged) or any((src in ambiguous_set for src in sources)):
					ambiguous_set.add(alias)
		return (anchor_ranges, anchor_content, all_anchors)
	# @used-by :meth:`HtmlAnchorResolver.__after_heading_blank()`
	# @used-by :meth:`HtmlAnchorResolver.__attach_empty_anchor()`
	# @used-by :meth:`HtmlAnchorResolver.__follows_heading()`
	@staticmethod
	def __same_parent(sp: dict, h: dict) -> bool:
		return sp.get('parent') is (h['_frames'][-1] if h.get('_frames') else None)
	# @used-by :meth:`HtmlAnchorResolver.__collect_section_lists()`
	def __section_frame_candidates(self, h: dict, claimed: set[str]) -> tuple[list[str], list[str]]:
		head_end = h['start'] if None is h.get('_head_end') else h['_head_end']
		sec_end = self.__plain_len if None is h['end'] else h['end']
		cands: list[str] = []
		cont_cands: list[str] = []
		for direct in self.__direct_anchors(h):
			self.__append_unique(cands, direct)
			claimed.add(direct)
		for frame in self.__visible_anchor_frames(h):
			kind = self.__classify_frame(h, frame, head_end, sec_end)
			if 'section' == kind:
				self.__append_unique(cands, frame['anchor'])
				claimed.add(frame['anchor'])
			elif 'container' == kind:
				self.__append_unique(cont_cands, frame['anchor'])
		return (cands, cont_cands)
	# @used-by :meth:`HtmlAnchorResolver.__attach_sibling_anchors()`
	# @used-by :meth:`HtmlAnchorResolver.__classify_frame()`
	# @used-by :meth:`HtmlAnchorResolver.__is_frame_eligible()`
	@staticmethod
	def __strip_glyphs(seg: str) -> str:
		return re.sub('[#\u00b6\u00a7\U0001f517\\s]+', '', seg)
	# @used-by :meth:`HtmlAnchorResolver.__section_frame_candidates()`
	@staticmethod
	def __visible_anchor_frames(h: dict) -> list[dict]:
		return [f for f in (h.get('_frames') or []) if (not f.get('hidden')) and f.get('anchor')]
	# @used-by :meth:`Df.Harness.Research.HtmlData.HtmlData.result()`
	def resolve(self) -> tuple[list[dict], list[dict], dict, dict, set[str], set[str]]:
		raw_ranges = {anchor: [[x['start'], self.__plain_len if None is x['end'] else x['end']] for x in ranges] for anchor, ranges in self.__anchor_ranges.items()}
		ambiguous_set = {anchor for anchor, ranges in raw_ranges.items() if 1 < len(ranges)}
		sec_lists, cont_lists, claimed = self.__collect_section_lists()
		self.__attach_sibling_anchors(ambiguous_set, claimed, sec_lists)
		anchor_ranges, anchor_content, all_anchors = self.__merge_github_aliases(raw_ranges, ambiguous_set)
		clean_headings, sections = self.__build_sections(sec_lists, cont_lists, raw_ranges, ambiguous_set)
		return (clean_headings, sections, anchor_ranges, anchor_content, all_anchors, ambiguous_set)
