# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
from typing import Mapping
from Df.Harness.Text.CodeBlockLinter import CodeBlockLinter
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from Df.Harness.Text.Proposal.Block import Block
from Df.Harness.Text.Proposal.Parser import Parser
from Df.Harness.Text.ProseLinter import ProseLinter
from Df.Harness.lib.text_core import dfh_author_text, dfh_detect_language, dfh_find_bans, dfh_load_lexicon, dfh_scan
from Df.Harness.lib.text_sections import KEYED_REF, PROPOSAL_MARKDOWN_LINK, PROPOSAL_URL, dfh_proposal_number_refs, dfh_validate_ref_range
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class Linter:
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_lint_document()`
	# @used-by :func:`agent_tools.proposal.lint_text()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_proposal_subsystem_roundtrip_and_fields()`
	def __init__(self, text: str, *, kind: str | None=None, lang: str | None=None, path: Path | None=None, lexicon=None, bans=None, profile: Mapping | None=None) -> None:
		self.__text = text
		self.__kind = kind
		self.__lang = lang
		self.__path = path
		self.__lexicon = lexicon
		self.__bans = bans
		self.__profile = dict(profile or {})
	# @used-by :meth:`Linter.__check_sequence()`
	def __check_block_order(self, block: Block, groups: dict[tuple, list[int]], findings: list[Finding]) -> None:
		prefix, ordinal = (block.number[:-1], block.number[-1])
		siblings = groups.setdefault(prefix, [])
		if not (0 == ordinal and prefix):
			expected = (int(self.__profile.get('start', 1)) if not prefix else 1) + sum((1 for n in siblings if 0 < n))
			if ordinal != expected:
				findings.append(Finding('error', 'PROPOSAL-SEQ', block.line, f'§{block.key} breaks the sequence (expected {expected} at this level)'))
		siblings.append(ordinal)
	# @used-by :meth:`Linter.lint()`
	def __check_format(self, lines: list[Line], findings: list[Finding]) -> None:
		seen_urls: dict[str, int] = {}
		for line in lines:
			if line.kind in ('code', 'quote', 'comment'):
				continue
			if 'heading' == line.kind:
				findings.append(Finding('error', 'PROPOSAL-HEADING', line.no, 'use plain numbered points in the Upwork proposal', line.raw))
			elif 'anchor' == line.kind:
				findings.append(Finding('error', 'PROPOSAL-ANCHOR', line.no, 'HTML anchors belong to article format; use §N in the proposal', line.raw))
			elif 'fence' == line.kind and line.raw[:1].isspace():
				findings.append(Finding('error', 'PROPOSAL-CODE-INDENT', line.no, 'place the code fence at the left margin', line.raw))
			elif 'prose' == line.kind:
				self.__check_prose_format(line, findings, seen_urls)
	# @used-by :meth:`Linter.__check_format()`
	def __check_prose_format(self, line: Line, findings: list[Finding], seen_urls: dict[str, int]) -> None:
		raw, author = (line.raw, dfh_author_text(line.raw))
		if PROPOSAL_MARKDOWN_LINK.search(raw):
			findings.append(Finding('error', 'PROPOSAL-MARKDOWN-LINK', line.no, 'use a plain URL in the Upwork field', raw))
		if 'technical' == self.__profile.get('voice', 'technical') and re.search('\\bI\\b', author):
			findings.append(Finding('error', 'PROPOSAL-FIRST-PERSON', line.no, 'name the system action or the required step instead of I', raw))
		if re.search('(?i)\\bjourneys?\\b', author):
			findings.append(Finding('error', 'PROPOSAL-JOURNEY', line.no, 'name the precise session/event history', raw))
		if re.search('(?i)\\b(?:Tag|Rule)\\s+\\d+\\b', author):
			findings.append(Finding('warning', 'PROPOSAL-INTERNAL-INDEX', line.no, 'identify the object as the client sees it in the interface', raw))
		for match in PROPOSAL_URL.finditer(raw):
			url = match.group(0).rstrip('.,;!')
			if url not in seen_urls:
				seen_urls[url] = line.no
			else:
				findings.append(Finding('error', 'PROPOSAL-DUP-URL', line.no, f'URL already used at line {seen_urls[url]}; cite its § point', url))
	# @used-by :meth:`Linter.lint()`
	def __check_sequence(self, blocks: list[Block], findings: list[Finding]) -> None:
		groups: dict[tuple, list[int]] = {}
		for block in blocks:
			if not block.number:
				continue
			if re.search('(?<!\\s)' + re.escape(block.key) + '\\.\\s+', dfh_author_text(block.body)):
				findings.append(Finding('error', 'PROPOSAL-CONCAT', block.line, f'a second {block.key}. point is joined onto the same line; remove the duplicate or separate it', block.body))
			if 'flat' == self.__profile.get('numbering') and 1 < len(block.number):
				findings.append(Finding('error', 'PROPOSAL-FLAT', block.line, 'nested point in the selected flat profile', block.key))
			self.__check_block_order(block, groups, findings)
	# @used-by :meth:`Df.Harness.Text.Proposal.Renderer.Renderer.render()`
	# @used-by :meth:`Linter.lint()`
	@staticmethod
	def check_references(lines: list[Line], blocks: list[Block], findings: list[Finding], profile: Mapping) -> None:
		known = {block.key for block in blocks} | {str(n) for n in profile.get('reference_targets', [])}
		for line in lines:
			if line.kind not in ('prose', 'heading'):
				continue
			for match in dfh_proposal_number_refs(line.raw):
				marks, start, dash, end = match.group('marks', 'start', 'dash', 'end')
				if match.group('space'):
					findings.append(Finding('error', 'PROPOSAL-REF-SPACE', line.no, 'write the point number immediately after §', match.group(0)))
				if end and ('§§' != marks or '-' != dash) or (not end and '§§' == marks):
					findings.append(Finding('error', 'PROPOSAL-RANGE', line.no, 'use §N for one point and §§N-M for a range', match.group(0)))
				dfh_validate_ref_range(start, end, known, findings, line.no, match.group(0), order_key=lambda k: tuple(map(int, k.split('.'))), order_rule='PROPOSAL-RANGE-ORDER', order_msg='range endpoints must be in document order', check_dense=True)
			if KEYED_REF.search(dfh_author_text(line.raw)):
				findings.append(Finding('error', 'KEY-UNRENDERED', line.no, 'render keyed references before using the proposal', line.raw))
	# @used-by :func:`Df.Harness.lib.text_sections.dfh_lint_document()`
	# @used-by :func:`agent_tools.proposal.lint_text()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_proposal_subsystem_roundtrip_and_fields()`
	def lint(self) -> list[Finding]:
		if self.__kind not in (None, 'proposal'):
			raise ValueError('proposal.lint_text accepts only kind=proposal')
		if self.__profile.get('numbering', 'nested') not in ('flat', 'nested'):
			raise ValueError('proposal numbering must be flat or nested')
		if self.__profile.get('voice', 'technical') not in ('technical', 'offer'):
			raise ValueError('proposal voice must be technical or offer')
		lines = dfh_scan(self.__text)
		r: list[Finding] = []
		blocks = Parser(lines, r).parse()
		if not blocks:
			r.append(Finding('error', 'PROPOSAL-EMPTY', 1, 'the proposal needs at least one plain numbered point'))
		self.__check_sequence(blocks, r)
		self.check_references(lines, blocks, r, self.__profile)
		self.__check_format(lines, r)
		ProseLinter(lines, 'proposal', self.__lang or dfh_detect_language(self.__text), r, self.__lexicon if None is not self.__lexicon else dfh_load_lexicon(), self.__bans if None is not self.__bans else dfh_find_bans(Path(self.__path) if self.__path else None)).check()
		CodeBlockLinter(lines, r).check()
		return r
