# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from Df.Harness.lib.text_core import THRESHOLDS
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CodeBlockLinter:
	# @used-by :func:`agent_tools.text_core.check_code()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.lint()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
	def __init__(self, lines: list[Line], findings: list[Finding]) -> None:
		self.__lines = lines
		self.__findings = findings
	# @used-by :meth:`CodeBlockLinter.check()`
	def __check_body(self, body: list[Line]) -> None:
		for line in body:
			if re.search('/assets/(?:index|app|main)[.-][A-Za-z0-9_-]{6,}\\.(?:js|css)\\b', line.raw):
				self.__findings.append(Finding('warning', 'CODE-VOLATILE', line.no, 'hashed build URL can change: resolve the current asset, or pin and identify the historical build the claim concerns', line.raw[:100]))
			for match in re.findall('\'([^\']*)\'|\\"([^\\"]*)\\"', line.raw):
				literal = match[0] or match[1]
				if len(literal) > THRESHOLDS['grep_literal']:
					self.__findings.append(Finding('warning', 'CODE-UNREADABLE', line.no, f'{len(literal)}-character literal: a reader cannot check it; publish a small script and run it as 2725 §11–§12 do', literal[:60] + '…'))
	# @used-by :meth:`CodeBlockLinter.check()`
	def __check_output(self, cursor: int, commands: int) -> None:
		while cursor < len(self.__lines) and 'blank' == self.__lines[cursor].kind:
			cursor += 1
		output: list[Line] = []
		while cursor < len(self.__lines) and 'quote' == self.__lines[cursor].kind:
			output.append(self.__lines[cursor])
			cursor += 1
		values = [re.sub('^\\s*>\\s?', '', l.raw).rstrip() for l in output]
		for value in set(values):
			if value and values.count(value) > max(commands, 1):
				first = output[values.index(value)]
				self.__findings.append(Finding('warning', 'CODE-DUP-OUTPUT', first.no, f'line repeated {values.count(value)}× for {commands} command(s): add sort -u / -m1 or show why the repetition matters', value[:80]))
	# @used-by :func:`agent_tools.text_core.check_code()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.lint()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
	def check(self) -> None:
		index = 0
		while index < len(self.__lines):
			if 'fence' != self.__lines[index].kind:
				index += 1
				continue
			index += 1
			body: list[Line] = []
			while index < len(self.__lines) and 'code' == self.__lines[index].kind:
				body.append(self.__lines[index])
				index += 1
			index += 1
			commands = sum((1 for l in body if l.raw.strip() and (not l.raw.rstrip().endswith('\\')) and (not l.raw.strip().startswith('#'))))
			self.__check_body(body)
			self.__check_output(index, commands)
