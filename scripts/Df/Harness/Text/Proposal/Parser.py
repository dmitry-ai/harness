# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Mapping
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from Df.Harness.Text.Proposal.Block import Block
from Df.Harness.lib.text_core import dfh_scan
from Df.Harness.lib.text_sections import PROPOSAL_KEYED, PROPOSAL_NUMBERED, dfh_close_spans
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class Parser:
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_parse_addressed()`
	# @used-by :func:`agent_tools.proposal.parse_blocks()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.render()`
	# @used-by :meth:`Df.Harness.Text.Proposal.SourceExporter.SourceExporter.export()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_proposal_subsystem_roundtrip_and_fields()`
	def __init__(self, value: str | list[Line], findings: list[Finding] | None=None, *, keyed: bool=False) -> None:
		self.__lines = dfh_scan(value) if isinstance(value, str) else value
		self.__findings = [] if None is findings else findings
		self.__keyed = keyed
	# @used-by :meth:`Parser.parse()`
	def __build_block(self, line: Line, match, known: dict[str, Block]) -> Block:
		name = match.group('name' if self.__keyed else 'number')
		number = () if self.__keyed else tuple((int(n) for n in name.split('.')))
		block = Block(name, number, line.no, len(self.__lines), match.group('prefix'), match.group('body'), gap=match.group('gap'))
		dup_rule, dup_mark, parent_rule = ('KEY-DUP', '@', 'KEY-PARENT') if self.__keyed else ('PROPOSAL-DUP', '§', 'PROPOSAL-PARENT')
		if name in known:
			self.__findings.append(Finding('error', dup_rule, line.no, f'duplicate {dup_mark}{name}', line.raw))
		parent = self.parent_name(name, known)
		if None is not parent:
			block.parent = known.get(parent)
			if None is block.parent:
				self.__findings.append(Finding('error', parent_rule, line.no, f'no preceding parent {parent}', line.raw))
		known[name] = block
		return block
	# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.__next_number()`
	# @used-by :meth:`Parser.__build_block()`
	@staticmethod
	def parent_name(name: str, known: Mapping[str, Block]) -> str | None:
		segments = name.split('.')
		if 1 == len(segments):
			r = None
		else:
			parent = '.'.join(segments[:-1])
			r = '.'.join(segments[:-2]) if parent not in known and '0' == segments[-2] and ('.'.join(segments[:-2]) in known) else parent
		return r
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_parse_addressed()`
	# @used-by :func:`agent_tools.proposal.parse_blocks()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.render()`
	# @used-by :meth:`Df.Harness.Text.Proposal.SourceExporter.SourceExporter.export()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_proposal_subsystem_roundtrip_and_fields()`
	def parse(self) -> list[Block]:
		r, known = ([], {})
		pattern = PROPOSAL_KEYED if self.__keyed else PROPOSAL_NUMBERED
		for line in self.__lines:
			if 'prose' != line.kind:
				continue
			match = pattern.fullmatch(line.raw)
			if None is match:
				if self.__keyed and PROPOSAL_NUMBERED.fullmatch(line.raw):
					self.__findings.append(Finding('error', 'KEY-NUMBERED', line.no, 'use @key in the keyed view', line.raw))
				continue
			r.append(self.__build_block(line, match, known))
		dfh_close_spans(r, self.__lines)
		return r
