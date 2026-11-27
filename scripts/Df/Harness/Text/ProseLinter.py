# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
from Df.Harness.Text.Finding import Finding
from Df.Harness.Text.Line import Line
from Df.Harness.lib.text_core import ARROW_CONNECTIVE, BOLD_LEADIN, HEADING, LIST_MARK, THRESHOLDS, dfh_author_text, dfh_clean, dfh_excerpt, dfh_external_section_ref, dfh_sentences
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ProseLinter:
	# @used-by :func:`agent_tools.text_core.check_prose()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.ResponseChecker.ResponseChecker.check()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
	def __init__(self, lines: list[Line], kind: str, lang: str, findings: list[Finding], lexicon: list, bans: list) -> None:
		self.__lines = lines
		self.__kind = kind
		self.__lang = lang
		self.__findings = findings
		entries = [e for e in lexicon if kind in e['kinds'] and e['lang'] in ('*', lang)]
		self.__compiled = [(e, [re.compile(p, 0 if e.get('case') else re.I) for p in e['patterns']]) for e in entries]
		self.__ban_patterns = [(b, re.compile(b['pattern'], 0 if b.get('case') else re.I)) for b in bans]
		self.__first_prose = next((l.no for l in lines if 'prose' == l.kind), 0)
	# @used-by :meth:`ProseLinter.check()`
	def __check_bans(self, line: Line) -> None:
		for ban, pattern in self.__ban_patterns:
			match = pattern.search(line.raw)
			if match:
				self.__findings.append(Finding(ban.get('severity', 'error'), 'BAN', line.no, ban.get('why', 'project ban'), dfh_excerpt(line.raw, match)))
	# @used-by :meth:`ProseLinter.check()`
	def __check_lexicon(self, line: Line, text: str) -> None:
		for entry, patterns in self.__compiled:
			targets = dfh_sentences(text) if 'start' == entry['where'] else [text]
			hit = self.__match_entry(entry['where'], targets, patterns)
			if None is not hit:
				self.__findings.append(Finding(entry['severity'], entry['id'], line.no, entry['fix'], dfh_excerpt(hit[0], hit[1])))
	# @used-by :meth:`ProseLinter.check()`
	def __check_prose_details(self, line: Line, text: str) -> None:
		raw = line.raw
		for arrow in re.finditer('→', text):
			if ARROW_CONNECTIVE.match(text[arrow.end():]):
				self.__findings.append(Finding('error', 'ARROW-CONNECTIVE', line.no, '`→` already means «follows from the premises»; a connective after it restates or re-argues the premise', dfh_excerpt(text, arrow)))
		if 'response' != self.__kind:
			authored = dfh_author_text(raw)
			for reference in re.finditer('§{1,2}[ \\t]+(?=\\d)', authored):
				if dfh_external_section_ref(authored, reference):
					self.__findings.append(Finding('error', 'REF-EXTERNAL-SPACE', line.no, 'write the external paragraph immediately after §; keep its document and number', raw[:100]))
			self.__check_sentence_limits(line, text)
			self.__check_inline_density(line)
	# @used-by :meth:`ProseLinter.__check_prose_details()`
	def __check_inline_density(self, line: Line) -> None:
		raw = line.raw
		spans = len(re.findall('`[^`]+`', raw))
		if spans > THRESHOLDS['code_spans']:
			self.__findings.append(Finding('warning', 'SENT-IDENTIFIERS', line.no, f'{spans} code identifiers on one line: keep only those the claim needs', raw[:60] + '…'))
		bold = [s for s in re.findall('\\*\\*(.+?)\\*\\*', raw) if '§' not in s]
		if len(bold) > THRESHOLDS['bold_spans']:
			self.__findings.append(Finding('warning', 'BOLD-DENSITY', line.no, f'{len(bold)} bold fragments on one line (WP:AIBOLD)', raw[:60] + '…'))
		if self.__kind in ('article', 'proposal') and re.search('\\]\\((?!<?https?://|#|mailto:)', raw):
			self.__findings.append(Finding('error', 'LINK-LOCAL', line.no, 'link to a local file: the client cannot open it', raw[:80]))
	# @used-by :meth:`ProseLinter.__check_prose_details()`
	def __check_sentence_limits(self, line: Line, text: str) -> None:
		found = dfh_sentences(text)
		lead = 'proposal' == self.__kind and line.no == self.__first_prose
		if 1 < len(found) and (not lead):
			self.__findings.append(Finding('error', 'SENT-SPLIT', line.no, f'{len(found)} sentences on one line (DOC-4): one sentence — one line', found[1][:60]))
		for sentence in found:
			words = re.findall("[A-Za-z\\u0410-\\u042f\\u0430-\\u044f\\u0401\\u04510-9][\\w'’-]*", sentence)
			if len(words) > THRESHOLDS['sentence_words']:
				self.__findings.append(Finding('warning', 'SENT-LONG', line.no, f'{len(words)} words in one sentence', sentence[:60] + '…'))
			parens = sentence.count('(')
			if parens > THRESHOLDS['parentheses']:
				self.__findings.append(Finding('warning', 'SENT-PARENS', line.no, f'{parens} parenthetical groups: move details into their own paragraphs or drop them', sentence[:60] + '…'))
	# @used-by :meth:`ProseLinter.__check_lexicon()`
	@staticmethod
	def __match_entry(where: str, targets: list[str], patterns: list):
		r = None
		for target in targets:
			for pattern in patterns:
				match = pattern.match(target) if 'start' == where else pattern.search(target)
				if match:
					r = (target, match)
					break
			if None is not r:
				break
		return r
	# @used-by :func:`agent_tools.text_core.check_prose()`
	# @used-by :meth:`Df.Harness.Text.Article.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.Proposal.Linter.Linter.lint()`
	# @used-by :meth:`Df.Harness.Text.ResponseChecker.ResponseChecker.check()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_docs.DfHarnessS11Wave2CTextDocsTests.test_text_core_linters_replayer_and_sections()`
	def check(self) -> None:
		for line in self.__lines:
			if line.kind not in ('prose', 'heading'):
				continue
			text = dfh_clean(HEADING.match(line.raw).group(2) if 'heading' == line.kind else line.raw)
			if not text:
				continue
			stripped = LIST_MARK.sub('', line.raw).strip()
			if 'prose' == line.kind and BOLD_LEADIN.match(stripped):
				self.__findings.append(Finding('error' if 'response' != self.__kind else 'warning', 'BOLD-LEADIN', line.no, 'inline bold label before a colon (WP:AILIST); state the claim itself', stripped[:80]))
			self.__check_lexicon(line, text)
			self.__check_bans(line)
			if 'prose' == line.kind:
				self.__check_prose_details(line, text)
