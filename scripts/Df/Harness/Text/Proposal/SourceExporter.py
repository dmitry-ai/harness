# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Text.Proposal.Parser import Parser
from Df.Harness.lib.text_core import dfh_external_section_ref, dfh_scan, dfh_transform_prose
from Df.Harness.lib.text_sections import PROPOSAL_REF, dfh_reassemble_lines
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SourceExporter:
	# @used-by :func:`agent_tools.proposal.to_source()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_proposal_subsystem_roundtrip_and_fields()`
	def __init__(self, text: str) -> None:
		self.__text = text
	# @used-by :meth:`SourceExporter.export()`
	@staticmethod
	def __replace_refs(segment: str) -> str:
		# @used-by :meth:`SourceExporter.__replace_refs()`
		def ref(match) -> str:
			if dfh_external_section_ref(segment, match):
				r = match.group()
			else:
				start, end = match.group('start', 'end')
				r = f'§§@{start}-@{end}' if end else f'§@{start}'
			return r
		return PROPOSAL_REF.sub(ref, segment)
	# @used-by :func:`agent_tools.proposal.to_source()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_proposal_subsystem_roundtrip_and_fields()`
	def export(self) -> str:
		lines = dfh_scan(self.__text)
		by_line = {block.line: block for block in Parser(lines).parse()}
		out: list[str] = []
		for line in lines:
			raw = f'{by_line[line.no].prefix}@{by_line[line.no].name}{by_line[line.no].gap}{by_line[line.no].body}' if line.no in by_line else line.raw
			if 'prose' == line.kind:
				raw = dfh_transform_prose(raw, self.__replace_refs)
			out.append(raw)
		return dfh_reassemble_lines(self.__text, lines, out)
