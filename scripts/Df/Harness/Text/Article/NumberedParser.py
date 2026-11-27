# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Text.Article.Section import Section
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from Df.Harness.lib.text_core import ANCHOR
from Df.Harness.lib.text_sections import ARTICLE_NUMBERED, dfh_close_spans, dfh_iter_article_headings
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class NumberedParser:
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_parse_addressed()`
	# @used-by :func:`agent_tools.article.parse_sections()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.render()`
	# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.export()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_text.DfHarnessS11Wave2CCovTextTests.test_article_linter_structure_source_exporter_and_sections()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def __init__(self, lines: list[Line], findings: list[Finding] | None=None) -> None:
		self.__lines = lines
		self.__findings = [] if None is findings else findings
	# @used-by :meth:`NumberedParser.__register_section()`
	def __attach_anchor(self, index: int, section: Section) -> None:
		following = next((x for x in self.__lines[index + 1:] if 'blank' != x.kind), None)
		if None is not following and 'anchor' == following.kind:
			section.anchor = ANCHOR.match(following.raw).group(1)
	# @used-by :meth:`NumberedParser.parse()`
	def __register_section(self, index: int, line: Line, level: int, part: str, match, by_key: dict, roots: dict) -> Section:
		number = tuple((int(x) for x in match.group(1).split('.')))
		section = Section(part, number, match.group(2), line.no, level)
		if level != len(number) + 1:
			self.__findings.append(Finding('warning', 'STRUCT-LEVEL', line.no, f"heading level {level} does not match number depth {len(number)} (expected {'#' * (len(number) + 1)})", line.raw))
		section.parent = by_key.get((part, number[:-1])) if 1 < len(number) else None
		if 1 < len(number) and None is section.parent:
			self.__findings.append(Finding('error', 'STRUCT-PARENT', line.no, f"no parent section {'.'.join(map(str, number[:-1]))}", line.raw))
		siblings = section.parent.children if section.parent else roots.setdefault(part, [])
		if number[-1] != len(siblings) + 1:
			self.__findings.append(Finding('error', 'STRUCT-SEQ', line.no, f'number {section.dotted} breaks the sequence (expected …{len(siblings) + 1})', line.raw))
		if (part, number) in by_key:
			self.__findings.append(Finding('error', 'STRUCT-DUP', line.no, f'duplicate section {section.key}', line.raw))
		by_key[part, number] = section
		siblings.append(section)
		self.__attach_anchor(index, section)
		return section
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_parse_addressed()`
	# @used-by :func:`agent_tools.article.parse_sections()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.render()`
	# @used-by :meth:`Df.Harness.Text.Article.SourceExporter.SourceExporter.export()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_text.DfHarnessS11Wave2CCovTextTests.test_article_linter_structure_source_exporter_and_sections()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def parse(self) -> list[Section]:
		r, by_key, roots = ([], {}, {})
		for index, line, level, text, part in dfh_iter_article_headings(self.__lines):
			match = ARTICLE_NUMBERED.match(text)
			if match:
				r.append(self.__register_section(index, line, level, part, match, by_key, roots))
		dfh_close_spans(r, self.__lines)
		return r
