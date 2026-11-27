# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from Df.Harness.lib.markdown import dfh_display_address, dfh_inline_links, dfh_markdown_it_parser
from Df.Harness.lib.text_core import INLINE_LITERAL
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class LinkStyleAuditor:
	# @used-by :func:`agent_tools.article.check_link_style()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def __init__(self, lines: list[Line], findings: list[Finding], link_style: str | None) -> None:
		self.__lines = lines
		self.__findings = findings
		self.__link_style = link_style
	# @used-by :meth:`LinkStyleAuditor.audit()`
	def __check_bare_urls(self, line: Line) -> None:
		protected = [m.span() for m in INLINE_LITERAL.finditer(line.raw)]
		protected.extend((m.span() for m in re.finditer('(?<!\\w)"[^"\\n]+"', line.raw)))
		protected.extend((m.span() for m in re.finditer('!?\\[[^\\]\\n]*\\]\\((?:<?https?://[^\\s>)]*>?)\\)|<https?://[^>\\n]+>', line.raw)))
		for match in re.finditer('https?://[^\\s<>]+', line.raw):
			if not any((start <= match.start() < end for start, end in protected)):
				self.__findings.append(Finding('error', 'LINK-BARE', line.no, 'the selected article profile requires formatted external links', match.group(0)))
	# @used-by :meth:`LinkStyleAuditor.audit()`
	def __check_inline_labels(self, line: Line, engine, environment: dict) -> None:
		authored = INLINE_LITERAL.sub('', line.raw)
		tokens = engine.parseInline(authored, environment)[0].children or []
		for href, label in dfh_inline_links(tokens):
			if href.startswith(('https://', 'http://')):
				try:
					actual = dfh_display_address(label if '://' in label else 'https://' + label)
					expected = dfh_display_address(href)
				except ValueError:
					actual, expected = (None, href)
				if actual != expected:
					self.__findings.append(Finding('error', 'LINK-LABEL', line.no, 'formatted label must preserve the destination domain, path, query and fragment', label))
	# @used-by :func:`agent_tools.article.check_link_style()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_article_subsystem_roundtrip_and_audit()`
	def audit(self) -> None:
		if 'formatted' == self.__link_style:
			engine, environment = (dfh_markdown_it_parser(), {})
			engine.parse('\n'.join((line.raw for line in self.__lines)), environment)
			definitions = {index for item in environment.get('references', {}).values() for index in range(*item.get('map', (0, 0)))}
			for line in self.__lines:
				if line.kind not in ('prose', 'heading') or line.no - 1 in definitions:
					continue
				self.__check_inline_labels(line, engine, environment)
				self.__check_bare_urls(line)
