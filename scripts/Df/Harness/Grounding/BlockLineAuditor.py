# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
from Df.Harness.Grounding.ActiveCorpusBuilder import ActiveCorpusBuilder
from Df.Harness.Grounding.DomainFactExtractor import DomainFactExtractor
from Df.Harness.Grounding.FactContradictionChecker import FactContradictionChecker
from Df.Harness.lib.grounding import CLIENT_DELIVERABLE_METRIC_RE, META_REFUTATION_RE, TECHNICAL_SPAN_RE, dfh_clean_line_for_number_grounding, dfh_extract_blockquote_quotes, dfh_filter_primary_sources, dfh_is_client_deliverable_doc, dfh_norm_quote_text, dfh_quote_segments_present
from agent_tools.claims import extract_verified_inline_calc_numbers, standalone_numbers
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_BACKTICK_QUOTE_RE = re.compile('`["\\u201c]([^"\\u201d`]{8,})["\\u201d]`')
_CYR_QUOTE_INTRO_RE = re.compile('(?:\\u043f\\u0438\\u0448\\u0435\\u0442|\\u043d\\u0430\\u043f\\u0438\\u0441\\u0430\\u043b\\w*|\\u0437\\u0430\\u044f\\u0432\\u0438\\u043b\\w*|\\u0441\\u043a\\u0430\\u0437\\u0430\\u043d\\u043e|\\u0446\\u0438\\u0442\\u0430\\u0442\\u0430)\\s*:\\s*\\u00ab', re.I)
class BlockLineAuditor:
	# @used-by :func:`agent_tools.grounding_helpers.audit_active_block()`
	# @used-by :meth:`BlockLineAuditor.audit_lines()`
	# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.__audit_inline_block()`
	def __init__(self, auditor, block, filtered_locals: list[Path], ext_urls: list[str], active_primary: list[Path], norm_fn=None, num_fn=None) -> None:
		self.__auditor = auditor
		self.__block = block
		self.__filtered_locals = filtered_locals
		self.__ext_urls = ext_urls
		self.__active_primary = active_primary
		self.__norm_fn = norm_fn
		self.__num_fn = num_fn
	# @used-by :meth:`BlockLineAuditor.__check_prose_line()`
	def __check_backtick_and_guillemet_quotes(self, sline: str, combined_norm: str, src_label: str, any_cyrillic_source: bool) -> None:
		for bq_str in _BACKTICK_QUOTE_RE.findall(sline):
			if 2 <= len(re.findall('[A-Za-z0-9]{2,}', bq_str)) and (not dfh_quote_segments_present(bq_str, combined_norm, 8)):
				preview = ' '.join(bq_str.split())[:80]
				self.__auditor.errors.append(f'VERIFY-1 / LINK-1: Quoted literal "{preview}" attributed to {src_label} is absent from the primary source')
		sline_for_quotes = re.sub('\\(\\u0430\\s+\\u043d\\u0435\\s+\\u00ab[^\\u00bb]+\\u00bb\\)', ' ', sline, flags=re.I)
		for gq in re.findall('\\u00ab([^\\u00bb]{10,})\\u00bb', sline_for_quotes):
			self.__check_guillemet_quote(sline, gq, combined_norm, src_label, any_cyrillic_source)
	# @used-by :meth:`BlockLineAuditor.audit_lines()`
	def __check_blockquote(self, text: str, combined_norm: str, src_label: str) -> None:
		if not META_REFUTATION_RE.search(text):
			for bq in dfh_extract_blockquote_quotes(text):
				if not dfh_quote_segments_present(bq, combined_norm, 12):
					preview = ' '.join(bq.split())[:80]
					self.__auditor.errors.append(f'VERIFY-1 / LINK-1: Blockquote \u00ab{preview}\u00bb attributed to {src_label} is absent from the primary source')
	# @used-by :meth:`BlockLineAuditor.__check_backtick_and_guillemet_quotes()`
	def __check_guillemet_quote(self, sline: str, gq: str, combined_norm: str, src_label: str, any_cyrillic_source: bool) -> None:
		has_cyr = bool(re.search('[\\u0400-\\u04ff]', gq))
		if not has_cyr:
			if 2 <= len(re.findall('[A-Za-z0-9]{2,}', gq)) and (not dfh_quote_segments_present(gq, combined_norm, 12)):
				preview = ' '.join(gq.split())[:80]
				self.__auditor.errors.append(f'VERIFY-1 / LINK-1: Verbatim quote \u00ab{preview}\u00bb attributed to {src_label} is absent from the primary source')
		elif any_cyrillic_source and 25 <= len(gq.strip()) and _CYR_QUOTE_INTRO_RE.search(sline):
			if not dfh_quote_segments_present(gq, combined_norm, 15):
				preview = ' '.join(gq.split())[:80]
				self.__auditor.errors.append(f'VERIFY-1 / LINK-1: Verbatim quote \u00ab{preview}\u00bb attributed to {src_label} is absent from the primary source')
	# @used-by :meth:`BlockLineAuditor.audit_lines()`
	def __check_prose_line(self, sline: str, infos: list[dict], combined_raw: str, combined_norm: str, ev_nums: set[str], src_label: str, ticket_infos: list[dict], valid_msg_nums: set[int], bound_ticket_ids: set[str], any_cyrillic_source: bool) -> None:
		if sline and (not META_REFUTATION_RE.search(sline)):
			self.__check_backtick_and_guillemet_quotes(sline, combined_norm, src_label, any_cyrillic_source)
			if ticket_infos:
				self.__auditor.errors.extend(DomainFactExtractor.ticket_author_issues(sline, combined_norm, src_label))
			for ungrounded_num in self.line_grounded_numbers_check(sline, ev_nums, valid_msg_nums, bound_ticket_ids, bool(ticket_infos)):
				self.__auditor.errors.append(f'VERIFY-1 / DOC-1: Unverified numeric figure or identifier ({ungrounded_num}) attributed to {src_label} is absent from the primary source')
			self.__auditor.errors.extend(DomainFactExtractor.order_url_issues(sline, ev_nums, combined_raw, src_label))
			self.__auditor.errors.extend(FactContradictionChecker(sline, infos, ledger_tuples=self.__auditor.ledger_tuples).check())
			self.__check_technical_spans(sline, combined_raw, combined_norm, src_label)
	# @used-by :meth:`BlockLineAuditor.__check_prose_line()`
	def __check_technical_spans(self, sline: str, combined_raw: str, combined_norm: str, src_label: str) -> None:
		for code_span in re.findall('`([^`\\n]{3,60})`', sline):
			c_strip = code_span.strip()
			if TECHNICAL_SPAN_RE.match(c_strip):
				c_lookup = c_strip.lstrip('#')
				if dfh_norm_quote_text(c_strip) not in combined_norm and c_strip.lower() not in combined_raw.lower() and c_lookup.lower() not in combined_raw.lower():
					self.__auditor.errors.append(f'VERIFY-1 / DOC-1: Technical literal `{c_strip}` attributed to {src_label} is absent from the primary source')
	# @used-by :meth:`BlockLineAuditor.audit()`
	def __check_unlinked_deliverable_metrics(self, text: str) -> None:
		if dfh_is_client_deliverable_doc(self.__auditor.doc_path) and 0 == self.__auditor.quote_depth and (not META_REFUTATION_RE.search(text)) and CLIENT_DELIVERABLE_METRIC_RE.search(text):
			self.__auditor.errors.append('VERIFY-1 / LINK-1: Client deliverable block asserts quantitative metrics or transaction/order identifiers without linking to a Tier 0 primary source in \ua616/KB/Evidence/')
	# @used-by :meth:`BlockLineAuditor.audit_lines()`
	@staticmethod
	def __tag_new_errors(errors: list[str], start_idx: int, line_no: int | None) -> None:
		if None is not line_no:
			suffix = f' (line {line_no})'
			for idx in range(start_idx, len(errors)):
				if '(line ' not in errors[idx]:
					errors[idx] = errors[idx] + suffix
	# @used-by :func:`agent_tools.grounding_helpers.audit_active_block()`
	# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.__audit_inline_block()`
	def audit(self) -> None:
		if self.__active_primary:
			active_locals = dfh_filter_primary_sources(list(dict.fromkeys(self.__filtered_locals + self.__auditor.section_all_locals + self.__active_primary)))
			active_exts = list(dict.fromkeys(self.__ext_urls + self.__auditor.section_ext_urls))
			infos, combined_raw, combined_norm, ev_nums, src_label = ActiveCorpusBuilder(self.__auditor, active_locals, active_exts, self.__active_primary, self.__norm_fn, self.__num_fn).build()
			self.audit_lines(self.__auditor, self.__block, infos, combined_raw, combined_norm, ev_nums, src_label)
		else:
			active_exts = dfa_unique_fast(self.__ext_urls + self.__auditor.section_ext_urls)
			repo_entries, labels = ActiveCorpusBuilder.collect_local_repo_entries(self.__auditor.root, active_exts, self.__norm_fn, self.__num_fn)
			if repo_entries:
				infos, combined_raw, combined_norm, ev_nums = ActiveCorpusBuilder.assemble([], repo_entries)
				self.audit_lines(self.__auditor, self.__block, infos, combined_raw, combined_norm, ev_nums, ', '.join(labels[:2]))
			else:
				self.__check_unlinked_deliverable_metrics(self.__block.content)
	# @used-by :func:`agent_tools.grounding_helpers.audit_block_lines()`
	# @used-by :meth:`BlockLineAuditor.audit()`
	@classmethod
	def audit_lines(cls, auditor, block, infos: list[dict], combined_raw: str, combined_norm: str, ev_nums: set[str], src_label: str) -> None:
		runner = cls(auditor, block, [], [], [])
		bmap = getattr(block, 'map', None)
		base_line = (int(bmap[0]) + 1) if isinstance(bmap, (list, tuple)) and bmap else None
		if 0 < auditor.quote_depth:
			before = len(auditor.errors)
			runner.__check_blockquote(block.content, combined_norm, src_label)
			cls.__tag_new_errors(auditor.errors, before, base_line)
		else:
			ticket_infos = [inf for inf in infos if inf['is_ticket_source']]
			valid_msg_nums = {n for inf in ticket_infos for n in inf['msg_nums']}
			bound_ticket_ids = {inf['ticket_id'] for inf in ticket_infos if inf['ticket_id']}
			any_cyrillic_source = any((inf['has_cyrillic'] for inf in infos))
			for offset, line in enumerate(block.content.split('\n')):
				before = len(auditor.errors)
				runner.__check_prose_line(line.strip(), infos, combined_raw, combined_norm, ev_nums, src_label, ticket_infos, valid_msg_nums, bound_ticket_ids, any_cyrillic_source)
				cls.__tag_new_errors(auditor.errors, before, None if None is base_line else base_line + offset)
	# @used-by :func:`agent_tools.source_grounding._line_grounded_numbers_check()`
	# @used-by :meth:`BlockLineAuditor.__check_prose_line()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_active_corpus_builder_and_block_line_auditor()`
	@staticmethod
	def line_grounded_numbers_check(sline: str, ev_nums: set[str], valid_msg_nums: set[int], bound_ticket_ids: set[str], is_ticket: bool) -> list[str]:
		r: list[str] = []
		if is_ticket:
			r.extend(DomainFactExtractor.ticket_message_issues(sline, valid_msg_nums, bound_ticket_ids))
		verified_calc_nums, calc_errors = extract_verified_inline_calc_numbers(sline, ev_nums)
		ev_with_calc = set(ev_nums) | set(verified_calc_nums)
		for calc_err in calc_errors:
			r.append(f'{calc_err} (inline arithmetic mismatch)')
		cleaned = dfh_clean_line_for_number_grounding(sline, is_ticket=is_ticket)
		for num in sorted(standalone_numbers(cleaned)):
			norm_num = num.replace(',', '')
			if not (1 == len(norm_num) and norm_num.isdigit()) and num not in ev_with_calc and norm_num not in ev_with_calc:
				r.append(num)
		return r