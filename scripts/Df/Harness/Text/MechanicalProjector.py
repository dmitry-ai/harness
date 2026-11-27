# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from urllib.parse import unquote
from Df.Harness.lib.research import dfh_bare_urls
from Df.Harness.lib.text_core import dfh_external_section_ref, dfh_normalize_external_refs, dfh_scan
from Df.Harness.lib.text_sections import ANCHOR_LINK, dfh_parse_addressed, dfh_part_at
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class MechanicalProjector:
	# @used-by :func:`agent_tools.text_sections.mechanical_projection()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
	def __init__(self, text: str, kind: str, mode: str) -> None:
		self.__text = text
		self.__kind = kind
		self.__mode = mode
	# @used-by :meth:`MechanicalProjector.__project_prose()`
	@staticmethod
	def __project_links(item: str) -> str:
		# @used-by :meth:`MechanicalProjector.__project_links()`
		def link(match) -> str:
			label, url = match.groups()
			visible = unquote(re.sub('[*`]', '', label))
			address = unquote(re.sub('^https?://', '', url.rstrip('>')))
			return 'URL' if visible.rstrip('/') in (address.rstrip('/'), url.rstrip('>')) else label + '(URL)'
		step = re.sub('\\[([^\\]]+)\\]\\(<?(https?://[^)]+)\\)', link, item)
		return re.sub('https?://\\S+', lambda m: 'URL' + m.group()[len(next(dfh_bare_urls(m.group()))):], step)
	# @used-by :meth:`MechanicalProjector.project()`
	def __project_prose(self, value: str, current: str, identities: dict[str, str]) -> str:
		protected = '`+[^`]*`+|«[^»]*»|“[^”]*”|(?<!\\w)"[^"\\n]+"'
		if 'renumber' == self.__mode:
			protected += '|!?\\[[^\\]\\n]*\\]\\(<?https?://[^)]+\\)|<https?://[^>]+>|https?://[^\\s<>"\\x27]+'
		parts = re.split('(' + protected + ')', value)
		for i in range(0, len(parts), 2):
			parts[i] = self.__project_links(parts[i]) if 'links' == self.__mode else self.__project_renumber(parts[i], current, identities)
		return ''.join(parts)
	# @used-by :meth:`MechanicalProjector.__project_prose()`
	def __project_renumber(self, item: str, current: str, identities: dict[str, str]) -> str:
		item = dfh_normalize_external_refs(item)
		item = ANCHOR_LINK.sub(lambda m: 'REF:' + identities.get(m[2].lstrip('§'), 'MISSING:' + m[2]), item)
		# @used-by :meth:`MechanicalProjector.__project_renumber()`
		def ref(match) -> str:
			if dfh_external_section_ref(item, match):
				r = match.group()
			else:
				target = current + '.' + match.group(1) if 'article' == self.__kind and (not re.match('^[IVXLC]+\\.', match.group(1))) else match.group(1)
				r = 'REF:' + identities.get(target, 'MISSING:' + target)
			return r
		item = re.sub('§+([IVXLC]+\\.\\d+(?:\\.\\d+)*|\\d+(?:\\.\\d+)*)', ref, item)
		if 'proposal' == self.__kind:
			item = re.sub('^\\s*\\d+(?:\\.\\d+)*\\.\\s*', '', item)
		return item
	# @used-by :func:`agent_tools.text_sections.mechanical_projection()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
	def project(self) -> str:
		lines = dfh_scan(self.__text)
		identities = {str(s.key): str(i) for i, s in enumerate(dfh_parse_addressed(lines, self.__kind))}
		out: list[str] = []
		for line, raw in zip(lines, self.__text.splitlines(True)):
			ending = raw[len(line.raw):]
			if 'renumber' == self.__mode and 'anchor' == line.kind:
				continue
			if 'renumber' == self.__mode and 'heading' == line.kind:
				out.append(re.sub('^(#{2,6}\\s+)\\d+(?:\\.\\d+)*\\.?\\s*', '\\1', line.raw) + ending)
				continue
			out.append((self.__project_prose(line.raw, dfh_part_at(lines, line.no), identities) if 'prose' == line.kind else line.raw) + ending)
		return ''.join(out)
