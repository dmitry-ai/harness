# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class EvidenceGrepper:
	# @used-by :meth:`Df.Harness.Research.EvidenceQuerier.EvidenceQuerier.__attach_grep()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_evidence_querier_and_grepper()`
	def __init__(self, rx: re.Pattern, *, context_lines: int=2, max_matches: int=20) -> None:
		self.__rx = rx
		self.__context_lines = context_lines
		self.__max_matches = max_matches
	# @used-by :meth:`EvidenceGrepper.__collect_window_matches()`
	@staticmethod
	def __build_line_windows(lines: list[str], hit_indices: list[int], context_lines: int) -> list[list[int]]:
		windows: list[list[int]] = []
		span_ctx = max(1, context_lines)
		span_max = max(3, context_lines * 2)
		for idx in hit_indices:
			s = max(0, idx - span_ctx)
			e = min(len(lines) - 1, idx + span_ctx)
			while 0 < s and lines[s - 1].strip() and span_max > idx - s:
				s -= 1
			while e + 1 < len(lines) and lines[e + 1].strip() and span_max > e - idx:
				e += 1
			if windows and s <= windows[-1][1] + 1:
				windows[-1][1] = max(windows[-1][1], e)
			else:
				windows.append([s, e])
		return windows
	# @used-by :meth:`EvidenceGrepper.__collect_window_matches()`
	@staticmethod
	def __clip_snippet(snippet: str, rx: re.Pattern) -> str:
		if 1200 >= len(snippet):
			r = snippet
		else:
			m_in = rx.search(snippet)
			pos = m_in.start() if m_in else 0
			ws = max(0, pos - 550)
			r = snippet[ws:min(len(snippet), ws + 1100)].strip()
		return r
	# @used-by :meth:`EvidenceGrepper.__grep_section_unit()`
	@classmethod
	def __collect_window_matches(cls, lines: list[str], hit_indices: list[int], rx: re.Pattern, context_lines: int, max_matches: int, heading, anchor_ref, seen: set[str], out: list[dict]) -> None:
		for s, e in cls.__build_line_windows(lines, hit_indices, context_lines):
			snippet = cls.__clip_snippet('\n'.join(lines[s:e + 1]).strip(), rx)
			if snippet and snippet not in seen:
				seen.add(snippet)
				out.append({'heading': heading, 'anchor': anchor_ref, 'line_start': s + 1, 'line_end': e + 1, 'verbatim_context': snippet})
				if max_matches <= len(out):
					break
	# @used-by :meth:`EvidenceGrepper.grep_sections()`
	@classmethod
	def __grep_section_unit(cls, sec: dict, rx: re.Pattern, context_lines: int, max_matches: int, seen: set[str], out: list[dict]) -> None:
		content = str(sec.get('content') or '')
		sec_anchors = [str(a) for a in (sec.get('section_anchors') or ()) if a]
		anchor_ref = f'#{sec_anchors[0]}' if sec_anchors else (f"#{sec['anchor']}" if sec.get('anchor') else None)
		heading = sec.get('text')
		lines = content.splitlines()
		hit_indices = [idx for idx, ln in enumerate(lines) if rx.search(ln)]
		if hit_indices:
			cls.__collect_window_matches(lines, hit_indices, rx, context_lines, max_matches, heading, anchor_ref, seen, out)
		else:
			snippet = content[:800].strip()
			if snippet and snippet not in seen:
				seen.add(snippet)
				out.append({'heading': heading, 'anchor': anchor_ref, 'line_start': 1, 'line_end': max(1, len(lines)), 'verbatim_context': snippet})
	# @used-by :meth:`Df.Harness.Research.EvidenceQuerier.EvidenceQuerier.__attach_grep()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_evidence_querier_and_grepper()`
	def grep_blob(self, blob_lines: list[str], *, has_lc_anchors: bool) -> list[dict]:
		hit_indices = [idx for idx, ln in enumerate(blob_lines) if self.__rx.search(ln)]
		windows: list[list[int]] = []
		for idx in hit_indices:
			s = max(0, idx - self.__context_lines)
			e = min(len(blob_lines) - 1, idx + self.__context_lines)
			if windows and s <= windows[-1][1] + 1:
				windows[-1][1] = max(windows[-1][1], e)
			else:
				windows.append([s, e, idx])
			if self.__max_matches <= len(windows):
				break
		out: list[dict] = []
		for s, e, first_hit in windows[:self.__max_matches]:
			s1, e1, hit1 = (s + 1, e + 1, first_hit + 1)
			range_anchor = f'#L{s1}' if s1 == e1 else f'#L{s1}-L{e1}'
			out.append({'line_start': s1, 'line_end': e1, 'hit_line': hit1, 'anchor': f'#LC{hit1}' if has_lc_anchors else range_anchor, 'line_anchor': f'#LC{hit1}', 'range_anchor': range_anchor, 'heading': None, 'verbatim_context': '\n'.join(blob_lines[s:e + 1])})
		return out
	# @used-by :meth:`Df.Harness.Research.EvidenceQuerier.EvidenceQuerier.__attach_grep()`
	@classmethod
	def grep_sections(cls, sections: list[dict], fallback_text: str, rx: re.Pattern, *, context_lines: int=2, max_matches: int=20) -> list[dict]:
		out: list[dict] = []
		seen: set[str] = set()
		raw_units = sections if sections else ([{'level': None, 'text': None, 'section_anchors': [], 'content': fallback_text}] if fallback_text else [])
		units = sorted(raw_units, key=lambda s: (len(str(s.get('content') or '')), -(int(s.get('level') or 0)), -int(bool(s.get('section_anchors') or s.get('anchor')))))
		for sec in units:
			content = str(sec.get('content') or '')
			if content and rx.search(content):
				cls.__grep_section_unit(sec, rx, context_lines, max_matches, seen, out)
				if max_matches <= len(out):
					break
		return out