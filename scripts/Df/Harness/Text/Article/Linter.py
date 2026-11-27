# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Text.Article.GraphAuditor import GraphAuditor
from Df.Harness.Text.Article.LinkStyleAuditor import LinkStyleAuditor
from Df.Harness.Text.Article.NumberedParser import NumberedParser
from Df.Harness.Text.Article.StructureAuditor import StructureAuditor
from Df.Harness.Text.CodeBlockLinter import CodeBlockLinter
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.ProseLinter import ProseLinter
from Df.Harness.lib.text_core import dfh_check_markdown_lists, dfh_detect_language, dfh_find_bans, dfh_load_lexicon, dfh_scan
from Df.Harness.lib.text_sections import dfh_detect_kind, dfh_lint_document
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class Linter:
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_lint_document()`
	# @used-by :func:`agent_tools.article.lint_text()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_text.DfHarnessS11Wave2CCovTextTests.test_article_linter_structure_source_exporter_and_sections()`
	def __init__(self, text: str, *, kind: str | None=None, lang: str | None=None, path: Path | None=None, lexicon=None, bans=None, link_style=None) -> None:
		self.__text = text
		self.__kind = kind
		self.__lang = lang
		self.__path = path
		self.__lexicon = lexicon
		self.__bans = bans
		self.__link_style = link_style
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_lint_document()`
	# @used-by :func:`agent_tools.article.lint_text()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_text.DfHarnessS11Wave2CCovTextTests.test_article_linter_structure_source_exporter_and_sections()`
	def lint(self) -> list[Finding]:
		kind = self.__kind or dfh_detect_kind(self.__path, self.__text)
		if 'proposal' == kind:
			r = dfh_lint_document(self.__text, 'proposal', path=self.__path, lang=self.__lang, lexicon=self.__lexicon, bans=self.__bans)
		else:
			lines = dfh_scan(self.__text)
			findings: list[Finding] = []
			if 'article' == kind:
				sections = NumberedParser(lines, findings).parse()
				StructureAuditor(lines, sections, findings).audit()
				GraphAuditor(lines, sections, findings).audit()
				CodeBlockLinter(lines, findings).check()
				dfh_check_markdown_lists(lines, findings)
				LinkStyleAuditor(lines, findings, self.__link_style).audit()
			ProseLinter(lines, kind, self.__lang or dfh_detect_language(self.__text), findings, dfh_load_lexicon() if None is self.__lexicon else self.__lexicon, dfh_find_bans(self.__path) if None is self.__bans else self.__bans).check()
			r = sorted(findings, key=lambda f: (f.line, 'error' != f.severity, f.rule))
		return r
