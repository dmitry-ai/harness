# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Text.Article.Section import Section
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from Df.Harness.lib.text_sections import ARTICLE_KEYED, ARTICLE_NUMBERED, dfh_close_spans, dfh_iter_article_headings
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class KeyedParser:
	# @used-by :func:`agent_tools.article.parse_keyed()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.render()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def __init__(self, lines: list[Line], findings: list[Finding]) -> None:
		self.__lines = lines
		self.__findings = findings
	# @used-by :meth:`KeyedParser.parse()`
	@staticmethod
	def __find_parent(sections: list[Section], part: str, level: int) -> Section | None:
		r = None
		for previous in reversed(sections):
			if previous.part != part:
				break
			if previous.level < level:
				r = previous
				break
		return r
	# @used-by :func:`agent_tools.article.parse_keyed()`
	# @used-by :meth:`Df.Harness.Text.Article.Renderer.Renderer.render()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def parse(self) -> tuple[list[Section], dict]:
		sections, roots = ([], {})
		for _, line, level, text, part in dfh_iter_article_headings(self.__lines):
			match = ARTICLE_KEYED.match(text)
			if not match:
				if ARTICLE_NUMBERED.match(text):
					self.__findings.append(Finding('error', 'KEY-NUMBERED', line.no, 'numbered heading inside a keyed view: use `@key`', line.raw))
				continue
			section = Section(part, (), match.group(2), line.no, level, name=match.group(1))
			section.parent = self.__find_parent(sections, part, section.level)
			expected = section.parent.level + 1 if section.parent else 2
			if section.level != expected:
				self.__findings.append(Finding('error', 'STRUCT-LEVEL', line.no, f'heading level {section.level}, expected {expected}', line.raw))
			(section.parent.children if section.parent else roots.setdefault(part, [])).append(section)
			sections.append(section)
		dfh_close_spans(sections, self.__lines)
		return (sections, roots)
