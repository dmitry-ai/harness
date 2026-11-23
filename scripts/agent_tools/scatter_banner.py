# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add FILE-6 warning banner rule for out-of-workspace file-scattering recommendations":
# https://github.com/dmitry-ai/harness/issues/200
from __future__ import annotations
import re
SCATTER_BANNER_BORDER = '*' * 63
SCATTER_BANNER_LINE = 'Я, ПИДОРАС, ПРЕДЛАГАЮ РАСКИДЫВАТЬ КАКАШКИ ПО ТВОЕМУ КОМПЬЮТЕРУ.'
SCATTER_BANNER_LINES = (SCATTER_BANNER_BORDER, SCATTER_BANNER_LINE, SCATTER_BANNER_BORDER)
SCATTER_BANNER = '\n'.join(SCATTER_BANNER_LINES)
_EXT_PATH_RE = re.compile(
	r'(?i)(?:'
	r'(?:%(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA|USERPROFILE)%|\$\{?(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA|USERPROFILE|USER_HOME|OS_USER_HOME|XDG_CACHE_HOME|XDG_DATA_HOME)\}?|\$env:(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA|USERPROFILE))[/\\][A-Za-z0-9_.<>/\\-]+'
	r'|(?:\b(?:в|во|in|into|to|inside|under)\s+`?)(?:%(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA)%|\$\{?(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA|XDG_CACHE_HOME|XDG_DATA_HOME)\}?|\$env:(?:LOCALAPPDATA|APPDATA|TEMP|TMP|PROGRAMDATA)\b|/(?:tmp|var/tmp)\b)'
	r'|\bAppData[/\\](?:Local|Roaming|LocalLow)[/\\][A-Za-z0-9_.<>/\\-]+'
	r'|[A-Za-z]:[/\\](?:Temp|tmp|ProgramData)[/\\][A-Za-z0-9_.<>/\\-]+'
	r'|(?<![A-Za-z0-9_./-])/(?:tmp|var/tmp|var/cache)/[A-Za-z0-9_.<>/\\-]+'
	r'|(?:\$HOME|~)[/\\][A-Za-z0-9_.<>/\\-]+'
	r'|(?:\b(?:в|во|in|into|to|at|add|create|move|store|save|put|mkdir|or|или)\s+`?)\.\.[/\\][A-Za-z0-9_.<>-]+'
	r')'
)
_HEAD_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\((?:<[^>]+>|[^)\s]+)\)')
_NATIVE_CONFIG_ALLOW_RE = re.compile(
	r'(?i)(?:'
	r'(?:\$HOME|\$\{?(?:USER_HOME|OS_USER_HOME|USERPROFILE)\}?|%USERPROFILE%|~)[/\\](?:\.gitconfig|\.git-credentials(?:\.lock)?|\.config[/\\]git[/\\]ignore|\.gemini[/\\]config\b|\.codex[/\\](?:config\.toml|AGENTS\.md)\b|\.ssh[/\\]config\b)'
	r'|AppData[/\\]Roaming[/\\](?:Antigravity|Code|Cursor|Windsurf)(?:-[A-Za-z0-9]+)?[/\\][A-Za-z0-9_.<>/\\-]*'
	r'|(?:%APPDATA%|\$\{?APPDATA\}?)[/\\]Antigravity(?:[/\\][A-Za-z0-9_.<>/\\-]*)?'
	r')'
)
_NEG_PREFIX_RE = re.compile(
	r'(?i)(?:не\s+(?:выносить|переносить|хранить|создавать|требует|класть|писать)|без\s+(?:переноса|выноса|создания)|оставить\s+внутри|вместо\s+(?:выноса|переноса)|do\s+not\s+(?:move|store|place|create)|don.?t\s+(?:move|store|place|create)|without\s+(?:moving|storing|creating)|keep\s+inside|avoid\s+(?:moving|storing|placing))\s*[^\n.]{0,60}$'
)
_OPEN_FENCE_RE = re.compile(r'^(`{3,}|~{3,})[A-Za-z0-9_+-]*$')
_OUTSIDE_PROSE_RE = re.compile(
	r'(?i)(?:'
	r'(?:вынос\w*|вынести|перенес\w*|перемест\w*|размест\w*|хранить|созда\w*)\s+[^\n.]{0,90}?(?:за\s+предел\w*\s+(?:любых\s+)?(?:git[-\s]*)?(?:рабоч\w*\s+дерев\w*|репозитори\w*|проект\w*|workspace)|во?\s+вне[-\s]?репозиторн\w*|во?\s+внешн\w*\s+(?:хранилищ\w*|каталог\w*|директори\w*|папк\w*|корень)|вне\s+(?:репозитори\w*|проект\w*|рабоч\w*\s+(?:дерев\w*|пространств\w*)|workspace))'
	r'|(?:move|relocate|place|store|create|put|offload)\s+[^\n.]{0,90}?(?:outside\s+(?:the\s+|any\s+)?(?:git\s+)?(?:repo(?:sitory)?|working\s+tree|project|workspace)|external\s+(?:storage|directory|folder|root|location)|out-of-(?:repo|tree|workspace))'
	r')'
)
_PROPOSAL_STOP_RE = re.compile(
	r'(?im)^\s*(?:(?:#{2,6}\s+)|(?:[-*+]\s+)?(?:\*\*|__)?)(?:доводы\s+(?:за|против)|аргументы\s+(?:за|против)|arguments?\s+(?:for|against)|for\s*[:—–-]|against\s*[:—–-]|pros\s*[:—–-]|cons\s*[:—–-]|оценка(?:\s+[^:\n]*)?\s*[:—–-]|score\s*[:—–-])'
)
_REC_HEAD_RE = re.compile(r'(?i)^(?:рекомендаци\w*|предложени\w*|recommendation\w*|proposal\w*|option\s*\d+|вариант\s*\d+)\b')
def _bare_banner_at_start(lines: list[str]) -> bool:
	return 3 <= len(lines) and [ln.rstrip() for ln in lines[:3]] == list(SCATTER_BANNER_LINES)
def _collect_candidate_recommendations(body: str, sections: dict[int, tuple[str, str]], mode: str) -> list[tuple[str, str]]:
	from .statements import _parse_explicit_items, _parse_section_items
	raw_items: list[tuple[str, str]] = []
	if 'problem' == mode and 4 in sections:
		raw_items.extend(_parse_section_items(sections[4][1]))
	_, explicit_mets = _parse_explicit_items(body)
	raw_items.extend(explicit_mets)
	raw_items.extend(_parse_standalone_recommendations(body))
	seen: set[str] = set()
	r: list[tuple[str, str]] = []
	for lbl, item_body in raw_items:
		if lbl not in seen:
			seen.add(lbl)
			r.append((lbl, item_body))
	return r
def _fenced_banner_at_start(lines: list[str]) -> bool:
	m = _OPEN_FENCE_RE.match(lines[0].strip())
	r = False
	if None is not m:
		marker = m.group(1)[0] * 3
		inner: list[str] = []
		for ln in lines[1:]:
			if ln.strip().startswith(marker):
				trimmed = [x.rstrip() for x in inner if x.strip()]
				r = trimmed == list(SCATTER_BANNER_LINES)
				break
			inner.append(ln)
	return r
def _has_unnegated_match(text: str, pattern: re.Pattern[str]) -> bool:
	return any((not _NEG_PREFIX_RE.search(text[max(0, m.start() - 70):m.start()]) for m in pattern.finditer(text)))
def _parse_standalone_recommendations(text: str) -> list[tuple[str, str]]:
	from .statements import _mask_fenced_lines
	items: list[tuple[str, list[str]]] = []
	cur_lvl: int | None = None
	for _, raw, fenced in _mask_fenced_lines(text):
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
def _proposal_slice(body: str) -> str:
	m = _PROPOSAL_STOP_RE.search(body)
	raw = body[:m.start()] if None is not m else body
	return _NATIVE_CONFIG_ALLOW_RE.sub(' ', _MD_LINK_RE.sub(r'\1', raw))
def has_leading_scatter_banner(body: str) -> bool:
	tail = (body or '').splitlines()[1:]
	idx = next((i for i, ln in enumerate(tail) if ln.strip()), len(tail))
	rest = tail[idx:]
	return bool(rest) and (_fenced_banner_at_start(rest) or _bare_banner_at_start(rest))
def proposes_external_scattering(body: str) -> bool:
	prop = _proposal_slice(body or '')
	return _has_unnegated_match(prop, _EXT_PATH_RE) or _has_unnegated_match(prop, _OUTSIDE_PROSE_RE)
def validate_scatter_banners(body: str, *, sections: dict[int, tuple[str, str]] | None=None, mode: str='auto') -> list[str]:
	from .statements import _extract_top_sections
	secs = sections if None is not sections else _extract_top_sections(body)
	return [f'FILE-6 / DOC-3: Recommendation "{lbl}" proposes creating, moving, or storing project or tool files outside the project root without starting immediately with the mandatory uppercase FILE-6 warning banner.' for lbl, item in _collect_candidate_recommendations(body, secs, mode) if proposes_external_scattering(item) and (not has_leading_scatter_banner(item))]
