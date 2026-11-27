# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
import re
from Df.Harness.Text.Article.KeyedParser import KeyedParser
from Df.Harness.Text.Article.NumberedParser import NumberedParser
from Df.Harness.Text.Article.StructureAuditor import StructureAuditor
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.KeyedProseRewriter import KeyedProseRewriter
from Df.Harness.lib.text_core import dfh_scan
from Df.Harness.lib.text_sections import ARTICLE_NUMBER_KEY, ARTICLE_SOURCE_META, dfh_assign_tree_numbers, dfh_build_render_report, dfh_part_at
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_REF_RULES = frozenset({'REF-DANGLING', 'REF-LABEL', 'REF-RANGE', 'REF-BARE', 'KEY-UNRENDERED', 'ANCHOR-DUP'})
class Renderer:
	# @used-by :func:`agent_tools.article.render()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__transform_keyed()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def __init__(self, source: str, previous: str | None=None) -> None:
		self.__source = source
		self.__previous = previous
	# @used-by :meth:`Renderer.__render_lines()`
	@staticmethod
	def __format_ref(current: str, mapping: dict, anchors: dict, marks: str, start: str, end: str | None) -> str:
		# @used-by :meth:`Renderer.__format_ref()`
		def label(anchor: str) -> str:
			part, _, number = anchor.partition('.') if re.match('^[IVXLC]+\\.', anchor) else ('', '', anchor)
			return number if part == current else anchor
		left = label(mapping[start])
		return f'[{marks}{left}-{label(mapping[end])}](#{anchors[start]})' if end else f'[{marks}{left}](#{anchors[start]})'
	# @used-by :meth:`Renderer.render()`
	@staticmethod
	def __parse_metadata(lines: list, findings: list[Finding]) -> dict:
		metadata: dict = {}
		for line in lines:
			match = ARTICLE_SOURCE_META.match(line.raw) if 'comment' == line.kind else None
			if match:
				try:
					value = json.loads(match.group(1))
					if not isinstance(value, dict) or value.get('anchor_prefix', '') not in ('', '§') or any((prefix not in ('', '§') for prefix in value.get('anchor_prefixes', {}).values())):
						raise ValueError('anchor prefix must be empty or §')
					metadata.update(value)
				except (ValueError, TypeError, AttributeError) as exc:
					findings.append(Finding('error', 'KEY-METADATA', line.no, str(exc)))
		return metadata
	# @used-by :meth:`Renderer.render()`
	def __render_lines(self, lines: list, numbers: dict, mapping: dict, anchors: dict, findings: list[Finding], external_changes: list) -> str:
		out: list[str] = []
		for line in lines:
			if 'comment' == line.kind and ARTICLE_SOURCE_META.match(line.raw):
				continue
			if line.no in numbers:
				node = numbers[line.no]
				title = (' ' if node.title.startswith('(') else '. ') + node.title if node.title else ''
				out.append('#' * (len(node.number) + 1) + f' {node.dotted}{title}')
				out.append(f"<a name='{anchors[node.name]}'></a>")
			elif line.kind not in ('prose', 'heading'):
				out.append(line.raw)
			else:
				current = dfh_part_at(lines, line.no)
				out.append(KeyedProseRewriter(line.raw, line.no, mapping, findings, external_changes, format_ref=lambda m, s, e: self.__format_ref(current, mapping, anchors, m, s, e), anchors=anchors, dangling_hint=' (deleted premise: delete or re-ground the dependent claim)').rewrite())
		return '\n'.join(out) + ('\n' if self.__source.endswith('\n') else '')
	# @used-by :func:`agent_tools.article.render()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def render(self) -> tuple[str, dict, list[Finding]]:
		lines = dfh_scan(self.__source)
		findings, external_changes = ([], [])
		metadata = self.__parse_metadata(lines, findings)
		sections, roots = KeyedParser(lines, findings).parse()
		numbers, mapping = dfh_assign_tree_numbers(roots, findings)
		if not sections:
			findings.append(Finding('error', 'KEY-EMPTY', 1, 'keyed source has no addressed sections'))
		old_sections = NumberedParser(dfh_scan(self.__previous)).parse() if None is not self.__previous else []
		old_prefixes = {s.key: '§' if (s.anchor or '').startswith('§') else '' for s in old_sections}
		default_prefix = metadata.get('anchor_prefix', '§' if old_prefixes and all(old_prefixes.values()) else '')
		prefixes = metadata.get('anchor_prefixes', {})
		anchors = {key: prefixes.get(key, old_prefixes.get(key, default_prefix)) + number for key, number in mapping.items()}
		markdown = self.__render_lines(lines, numbers, mapping, anchors, findings, external_changes)
		report = dfh_build_render_report(mapping, ARTICLE_NUMBER_KEY, external_changes, [s.key for s in old_sections] if None is not self.__previous else None)
		rendered_lines = dfh_scan(markdown)
		ref_findings: list[Finding] = []
		StructureAuditor(rendered_lines, NumberedParser(rendered_lines).parse(), ref_findings).audit()
		findings.extend((f for f in ref_findings if f.rule in _REF_RULES))
		return (markdown, report, findings)
