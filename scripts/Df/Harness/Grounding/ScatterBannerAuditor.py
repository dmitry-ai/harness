# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.lib.grounding import SCATTER_BANNER_LINES
from Df.Harness.lib.grounding_md import dfh_extract_top_sections, dfh_mask_fenced_lines, dfh_parse_explicit_items, dfh_parse_section_items
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_EXT_PATH_RE = re.compile(r'(?i)(?:(?:%(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA|USERPROFILE)%|\$\{?(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA|USERPROFILE|USER_HOME|OS_USER_HOME|XDG_CACHE_HOME|XDG_DATA_HOME)\}?|\$env:(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA|USERPROFILE))[/\\][A-Za-z0-9_.<>/\\-]+|(?:\b(?:\u0432|\u0432\u043e|in|into|to|inside|under)\s+`?)(?:%(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA)%|\$\{?(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA|XDG_CACHE_HOME|XDG_DATA_HOME)\}?|\$env:(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA)\b|/(?:tmp|var/tmp)\b)|\bAppData[/\\](?:Local|Roaming|LocalLow)[/\\][A-Za-z0-9_.<>/\\-]+|[A-Za-z]:[/\\](?:Temp|tmp|ProgramData)[/\\][A-Za-z0-9_.<>/\\-]+|(?<![A-Za-z0-9_./-])/(?:tmp|var/tmp|var/cache)/[A-Za-z0-9_.<>/\\-]+|(?:\$HOME|~)[/\\][A-Za-z0-9_.<>/\\-]+|(?:\b(?:\u0432|\u0432\u043e|in|into|to|at|add|create|move|store|save|put|mkdir|or|\u0438\u043b\u0438)\s+`?)\.\.[/\\][A-Za-z0-9_.<>-]+)')
_HEAD_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\((?:<[^>]+>|[^)\s]+)\)')
_NATIVE_CONFIG_ALLOW_RE = re.compile(r'(?i)(?:(?:\$HOME|\$\{?(?:USER_HOME|OS_USER_HOME|USERPROFILE)\}?|%USERPROFILE%|~)[/\\](?:\.gitconfig|\.git-credentials(?:\.lock)?|\.config[/\\]git[/\\]ignore|\.gemini[/\\]config\b|\.codex[/\\](?:config\.toml|AGENTS\.md)\b|\.ssh[/\\]config\b)|AppData[/\\]Roaming[/\\](?:Antigravity|Code|Cursor|Windsurf)(?:-[A-Za-z0-9]+)?[/\\][A-Za-z0-9_.<>/\\-]*|(?:%APPDATA%|\$\{?APPDATA\}?)[/\\]Antigravity(?:[/\\][A-Za-z0-9_.<>/\\-]*)?)')
_NEG_PREFIX_RE = re.compile(r'(?i)(?:\u043d\u0435\s+(?:\u0432\u044b\u043d\u043e\u0441\u0438\u0442\u044c|\u043f\u0435\u0440\u0435\u043d\u043e\u0441\u0438\u0442\u044c|\u0445\u0440\u0430\u043d\u0438\u0442\u044c|\u0441\u043e\u0437\u0434\u0430\u0432\u0430\u0442\u044c|\u0442\u0440\u0435\u0431\u0443\u0435\u0442|\u043a\u043b\u0430\u0441\u0442\u044c|\u043f\u0438\u0441\u0430\u0442\u044c)|\u0431\u0435\u0437\s+(?:\u043f\u0435\u0440\u0435\u043d\u043e\u0441\u0430|\u0432\u044b\u043d\u043e\u0441\u0430|\u0441\u043e\u0437\u0434\u0430\u043d\u0438\u044f)|\u043e\u0441\u0442\u0430\u0432\u0438\u0442\u044c\s+\u0432\u043d\u0443\u0442\u0440\u0438|\u0432\u043c\u0435\u0441\u0442\u043e\s+(?:\u0432\u044b\u043d\u043e\u0441\u0430|\u043f\u0435\u0440\u0435\u043d\u043e\u0441\u0430)|do\s+not\s+(?:move|store|place|create)|don.?t\s+(?:move|store|place|create)|without\s+(?:moving|storing|creating)|keep\s+inside|avoid\s+(?:moving|storing|placing))\s*[^\n.]{0,60}$')
_OPEN_FENCE_RE = re.compile(r'^(`{3,}|~{3,})[A-Za-z0-9_+-]*$')
_OUTSIDE_PROSE_RE = re.compile(r'(?i)(?:(?:\u0432\u044b\u043d\u043e\u0441\w*|\u0432\u044b\u043d\u0435\u0441\u0442\u0438|\u043f\u0435\u0440\u0435\u043d\u0435\u0441\w*|\u043f\u0435\u0440\u0435\u043c\u0435\u0441\u0442\w*|\u0440\u0430\u0437\u043c\u0435\u0441\u0442\w*|\u0445\u0440\u0430\u043d\u0438\u0442\u044c|\u0441\u043e\u0437\u0434\u0430\w*)\s+[^\n.]{0,90}?(?:\u0437\u0430\s+\u043f\u0440\u0435\u0434\u0435\u043b\w*\s+(?:\u043b\u044e\u0431\u044b\u0445\s+)?(?:git[-\s]*)?(?:\u0440\u0430\u0431\u043e\u0447\w*\s+\u0434\u0435\u0440\u0435\u0432\w*|\u0440\u0435\u043f\u043e\u0437\u0438\u0442\u043e\u0440\u0438\w*|\u043f\u0440\u043e\u0435\u043a\u0442\w*|workspace)|\u0432\u043e?\s+\u0432\u043d\u0435[-\s]?\u0440\u0435\u043f\u043e\u0437\u0438\u0442\u043e\u0440\u043d\w*|\u0432\u043e?\s+\u0432\u043d\u0435\u0448\u043d\w*\s+(?:\u0445\u0440\u0430\u043d\u0438\u043b\u0438\u0449\w*|\u043a\u0430\u0442\u0430\u043b\u043e\u0433\w*|\u0434\u0438\u0440\u0435\u043a\u0442\u043e\u0440\u0438\w*|\u043f\u0430\u043f\u043a\w*|\u043a\u043e\u0440\u0435\u043d\u044c)|\u0432\u043d\u0435\s+(?:\u0440\u0435\u043f\u043e\u0437\u0438\u0442\u043e\u0440\u0438\w*|\u043f\u0440\u043e\u0435\u043a\u0442\w*|\u0440\u0430\u0431\u043e\u0447\w*\s+(?:\u0434\u0435\u0440\u0435\u0432\w*|\u043f\u0440\u043e\u0441\u0442\u0440\u0430\u043d\u0441\u0442\u0432\w*)|workspace))|(?:move|relocate|place|store|create|put|offload)\s+[^\n.]{0,90}?(?:outside\s+(?:the\s+|any\s+)?(?:git\s+)?(?:repo(?:sitory)?|working\s+tree|project|workspace)|external\s+(?:storage|directory|folder|root|location)|out-of-(?:repo|tree|workspace)))')
_PROPOSAL_STOP_RE = re.compile(r'(?im)^\s*(?:(?:#{2,6}\s+)|(?:[-*+]\s+)?(?:\*\*|__)?)(?:\u0434\u043e\u0432\u043e\u0434\u044b\s+(?:\u0437\u0430|\u043f\u0440\u043e\u0442\u0438\u0432)|\u0430\u0440\u0433\u0443\u043c\u0435\u043d\u0442\u044b\s+(?:\u0437\u0430|\u043f\u0440\u043e\u0442\u0438\u0432)|arguments?\s+(?:for|against)|for\s*[:\u2014\u2013-]|against\s*[:\u2014\u2013-]|pros\s*[:\u2014\u2013-]|cons\s*[:\u2014\u2013-]|\u043e\u0446\u0435\u043d\u043a\u0430(?:\s+[^:\n]*)?\s*[:\u2014\u2013-]|score\s*[:\u2014\u2013-])')
_REC_HEAD_RE = re.compile(r'(?i)^(?:\u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\w*|\u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\w*|recommendation\w*|proposal\w*|option\s*\d+|\u0432\u0430\u0440\u0438\u0430\u043d\u0442\s*\d+)\b')
class ScatterBannerAuditor:
	# @used-by :func:`agent_tools.scatter_banner.validate_scatter_banners()`
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
	def __init__(self, body: str, *, sections: dict[int, tuple[str, str]] | None=None, blocks: list[dict] | None=None, mode: str='auto') -> None:
		self.__body = body
		self.__sections = sections
		self.__blocks = blocks
		self.__mode = mode
	# @used-by :meth:`ScatterBannerAuditor.has_leading_banner()`
	@staticmethod
	def __bare_banner_at_start(lines: list[str]) -> bool:
		return 3 <= len(lines) and [ln.rstrip() for ln in lines[:3]] == list(SCATTER_BANNER_LINES)
	# @used-by :meth:`ScatterBannerAuditor.audit()`
	def __collect_candidates(self, sections: dict[int, tuple[str, str]]) -> list[tuple[str, str]]:
		raw_items: list[tuple[str, str]] = []
		if 'problem' == self.__mode:
			sec_list = [b['sections'] for b in self.__blocks] if None is not self.__blocks else [sections]
			for sec in sec_list:
				if 4 in sec:
					raw_items.extend(dfh_parse_section_items(sec[4][1]))
		_, explicit_mets = dfh_parse_explicit_items(self.__body)
		raw_items.extend(explicit_mets)
		raw_items.extend(self.__parse_standalone(self.__body))
		seen: set[tuple[str, str]] = set()
		r: list[tuple[str, str]] = []
		for lbl, item_body in raw_items:
			if (lbl, item_body) not in seen:
				seen.add((lbl, item_body))
				r.append((lbl, item_body))
		return r
	# @used-by :meth:`ScatterBannerAuditor.has_leading_banner()`
	@staticmethod
	def __fenced_banner_at_start(lines: list[str]) -> bool:
		m = _OPEN_FENCE_RE.match(lines[0].strip())
		r = False
		if None is not m:
			marker = m.group(1)[0] * 3
			inner: list[str] = []
			for ln in lines[1:]:
				if ln.strip().startswith(marker):
					r = [x.rstrip() for x in inner if x.strip()] == list(SCATTER_BANNER_LINES)
					break
				inner.append(ln)
		return r
	# @used-by :meth:`ScatterBannerAuditor.proposes_external_scattering()`
	@staticmethod
	def __has_unnegated_match(text: str, pattern: re.Pattern[str]) -> bool:
		return any((not _NEG_PREFIX_RE.search(text[max(0, m.start() - 70):m.start()]) for m in pattern.finditer(text)))
	# @used-by :meth:`ScatterBannerAuditor.__collect_candidates()`
	@staticmethod
	def __parse_standalone(text: str) -> list[tuple[str, str]]:
		items: list[tuple[str, list[str]]] = []
		cur_lvl: int | None = None
		for _, raw, fenced in dfh_mask_fenced_lines(text):
			m = _HEAD_RE.match(raw.strip()) if not fenced else None
			if None is not m:
				lvl, title = (len(m.group(1)), m.group(2).strip())
				if _REC_HEAD_RE.match(title):
					items.append((title, [raw]))
					cur_lvl = lvl
				elif None is not cur_lvl and lvl <= cur_lvl:
					cur_lvl = None
				elif None is not cur_lvl:
					items[-1][1].append(raw)
			elif None is not cur_lvl:
				items[-1][1].append(raw)
		return [(k, '\n'.join(v)) for k, v in items]
	# @used-by :meth:`ScatterBannerAuditor.proposes_external_scattering()`
	@staticmethod
	def __proposal_slice(body: str) -> str:
		m = _PROPOSAL_STOP_RE.search(body)
		raw = body[:m.start()] if None is not m else body
		return _NATIVE_CONFIG_ALLOW_RE.sub(' ', _MD_LINK_RE.sub(r'\1', raw))
	# @used-by :func:`agent_tools.scatter_banner.validate_scatter_banners()`
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
	def audit(self) -> list[str]:
		secs = self.__sections if None is not self.__sections else ({} if None is not self.__blocks else dfh_extract_top_sections(self.__body))
		return [f'FILE-6 / DOC-3: Recommendation "{lbl}" proposes creating, moving, or storing project or tool files outside the project root without starting immediately with the mandatory uppercase FILE-6 warning banner.' for lbl, item in self.__collect_candidates(secs) if self.proposes_external_scattering(item) and (not self.has_leading_banner(item))]
	# @used-by :func:`agent_tools.scatter_banner.has_leading_scatter_banner()`
	# @used-by :meth:`ScatterBannerAuditor.audit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
	@classmethod
	def has_leading_banner(cls, body: str) -> bool:
		tail = (body or '').splitlines()[1:]
		idx = next((i for i, ln in enumerate(tail) if ln.strip()), len(tail))
		rest = tail[idx:]
		return bool(rest) and (cls.__fenced_banner_at_start(rest) or cls.__bare_banner_at_start(rest))
	# @used-by :func:`agent_tools.scatter_banner.proposes_external_scattering()`
	# @used-by :meth:`ScatterBannerAuditor.audit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
	@classmethod
	def proposes_external_scattering(cls, body: str) -> bool:
		prop = cls.__proposal_slice(body or '')
		return cls.__has_unnegated_match(prop, _EXT_PATH_RE) or cls.__has_unnegated_match(prop, _OUTSIDE_PROSE_RE)
