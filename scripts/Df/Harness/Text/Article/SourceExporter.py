# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from Df.Harness.Text.Article.NumberedParser import NumberedParser
from Df.Harness.lib.text_core import ANCHOR, dfh_external_section_ref, dfh_scan, dfh_transform_prose
from Df.Harness.lib.text_sections import ANCHOR_LINK, ARTICLE_BARE_REF, ARTICLE_SECTION_LABEL, dfh_part_at
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SourceExporter:
	# @used-by :func:`agent_tools.article.to_source()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__transform_keyed()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_text.DfHarnessS11Wave2CCovTextTests.test_article_linter_structure_source_exporter_and_sections()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def __init__(self, text: str) -> None:
		self.__text = text
	# @used-by :meth:`SourceExporter.export()`
	@staticmethod
	def __build_header(sections: list) -> str:
		prefixes = {s.key: '§' if (s.anchor or '').startswith('§') else '' for s in sections}
		default = '§' if prefixes and all(prefixes.values()) else ''
		overrides = {key: prefix for key, prefix in prefixes.items() if prefix != default}
		metadata = {'anchor_prefix': default, **({'anchor_prefixes': overrides} if overrides else {})}
		return '<!-- df-article: ' + json.dumps(metadata, ensure_ascii=False, separators=(',', ':')) + ' -->'
	# @used-by :meth:`SourceExporter.__export_line()`
	@staticmethod
	def __convert_bare(current: str, match) -> str:
		if dfh_external_section_ref(match.string, match):
			r = match.group(0)
		else:
			marks, start_part, start_number, end_part, end_number = match.groups()
			start_part = start_part or current
			start = f'{start_part}.{start_number}' if start_part else start_number
			if not end_number:
				r = f'{marks}@{start}'
			else:
				end_part = end_part or start_part
				endpoint = f'{end_part}.{end_number}' if end_part else end_number
				r = f'{marks}@{start}-@{endpoint}'
		return r
	# @used-by :meth:`SourceExporter.__export_line()`
	@staticmethod
	def __convert_link(current: str, aliases: dict, standalone: set, match) -> str:
		label, target = match.groups()
		key = aliases.get(target, target.removeprefix('§'))
		parsed = ARTICLE_SECTION_LABEL.match(label.replace('**', '').strip())
		if not parsed or not label.strip().startswith('§'):
			r = match.group(0) if target in standalone else f'[{label}](#@{key})'
		else:
			marks = '§§' if label.strip().startswith('§§') else '§'
			if not parsed.group(4):
				r = f'{marks}@{key}'
			else:
				end_part = parsed.group(3) or parsed.group(1) or current
				endpoint = f'{end_part}.{parsed.group(4)}' if end_part else parsed.group(4)
				r = f'{marks}@{key}-@{endpoint}'
		return r
	# @used-by :meth:`SourceExporter.export()`
	def __export_line(self, line, lines: list, by_line: dict, aliases: dict, standalone: set) -> str:
		if line.no in by_line:
			section = by_line[line.no]
			title = f' {section.title}' if section.title else ''
			r = '#' * (len(section.number) + 1) + f' @{section.key}{title}'
		elif line.kind not in ('prose', 'heading'):
			r = line.raw
		else:
			current = dfh_part_at(lines, line.no)
			r = dfh_transform_prose(line.raw, lambda v: ARTICLE_BARE_REF.sub(lambda m: self.__convert_bare(current, m), ANCHOR_LINK.sub(lambda m: self.__convert_link(current, aliases, standalone, m), v)))
		return r
	# @used-by :func:`agent_tools.article.to_source()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_text.DfHarnessS11Wave2CCovTextTests.test_article_linter_structure_source_exporter_and_sections()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def export(self) -> str:
		lines = dfh_scan(self.__text)
		sections = NumberedParser(lines, []).parse()
		by_line = {s.line: s for s in sections}
		aliases = {s.anchor or s.key: s.key for s in sections}
		standalone = {ANCHOR.match(line.raw).group(1) for line in lines if 'anchor' == line.kind} - set(aliases)
		anchor_lines = {next((x.no for x in lines if x.no > s.line and 'blank' != x.kind), None) for s in sections if s.anchor}
		out = [self.__build_header(sections)]
		for line in lines:
			if not (line.no in anchor_lines and 'anchor' == line.kind):
				out.append(self.__export_line(line, lines, by_line, aliases, standalone))
		return '\n'.join(out) + ('\n' if self.__text.endswith('\n') else '')
