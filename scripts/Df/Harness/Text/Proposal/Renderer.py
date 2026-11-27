# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.KeyedProseRewriter import KeyedProseRewriter
from Df.Harness.Text.Proposal.Linter import Linter
from Df.Harness.Text.Proposal.Parser import Parser
from Df.Harness.lib.text_core import dfh_scan
from Df.Harness.lib.text_sections import PROPOSAL_NUMBER_KEY, dfh_build_render_report, dfh_proposal_number_refs, dfh_reassemble_lines
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class Renderer:
	# @used-by :func:`agent_tools.proposal.render()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_proposal_subsystem_roundtrip_and_fields()`
	def __init__(self, source: str, previous: str | None=None) -> None:
		self.__source = source
		self.__previous = previous
	# @used-by :meth:`Renderer.render()`
	def __assign_numbers(self, blocks: list, findings: list[Finding]) -> tuple[dict, dict]:
		by_name, by_line, groups, mapping = ({}, {}, {}, {})
		closed_paths, active_path = (set(), [])
		for block in blocks:
			parts = block.name.split('.')
			path = ['.'.join(parts[:i]) for i in range(1, len(parts) + 1)]
			shared = 0
			while shared < min(len(path), len(active_path)) and path[shared] == active_path[shared]:
				shared += 1
			closed_paths.update(active_path[shared:])
			if any((name in closed_paths for name in path)):
				findings.append(Finding('error', 'KEY-NONCONTIGUOUS', block.line, 'move a parent together with all its child points', block.name))
			active_path = path
			block.number = self.__next_number(block.name, parts, by_name, groups)
			by_name[block.name] = by_line[block.line] = block
			mapping[block.name] = block.key
		return (by_line, mapping)
	# @used-by :meth:`Renderer.__assign_numbers()`
	@staticmethod
	def __next_number(name: str, parts: list[str], by_name: dict, groups: dict) -> tuple[int, ...]:
		parent_name = Parser.parent_name(name, by_name)
		parent_num = by_name[parent_name].number if parent_name and parent_name in by_name else ()
		if parent_name and parent_name in by_name and '0' == parts[-2] and parent_name != '.'.join(parts[:-1]):
			parent_num = (*parent_num, 0)
		ordinal = 0 if 1 < len(parts) and '0' == parts[-1] else groups.setdefault(parent_num, 0) + 1
		if ordinal:
			groups[parent_num] = ordinal
		return (*parent_num, ordinal)
	# @used-by :meth:`Renderer.render()`
	def __render_lines(self, lines: list, by_line: dict, mapping: dict, findings: list[Finding], external_changes: list) -> str:
		out: list[str] = []
		for line in lines:
			raw = line.raw
			if 'prose' == line.kind and any(dfh_proposal_number_refs(raw)):
				findings.append(Finding('error', 'KEY-NUMERIC-REF', line.no, 'use §@key in the keyed view; a number may bind to a different point after reordering', raw))
			if line.no in by_line:
				block = by_line[line.no]
				raw = f'{block.prefix}{block.key}.{block.gap}{block.body}'
			if 'prose' == line.kind:
				raw = KeyedProseRewriter(raw, line.no, mapping, findings, external_changes, format_ref=lambda _m, s, e: f'§§{mapping[s]}-{mapping[e]}' if e else f'§{mapping[s]}').rewrite()
			out.append(raw)
		return dfh_reassemble_lines(self.__source, lines, out)
	# @used-by :func:`agent_tools.proposal.render()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_proposal_subsystem_roundtrip_and_fields()`
	def render(self) -> tuple[str, dict, list[Finding]]:
		lines = dfh_scan(self.__source)
		findings, external_changes = ([], [])
		blocks = Parser(lines, findings, keyed=True).parse()
		if not blocks:
			findings.append(Finding('error', 'KEY-EMPTY', 1, 'the keyed proposal has no @points'))
		by_line, mapping = self.__assign_numbers(blocks, findings)
		rendered = self.__render_lines(lines, by_line, mapping, findings, external_changes)
		old_keys = [block.key for block in Parser(self.__previous).parse()] if None is not self.__previous else []
		report = dfh_build_render_report(mapping, PROPOSAL_NUMBER_KEY, external_changes, old_keys)
		final_lines = dfh_scan(rendered)
		Linter.check_references(final_lines, Parser(final_lines).parse(), findings, {})
		return (rendered, report, findings)
