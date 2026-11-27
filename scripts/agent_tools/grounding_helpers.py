# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Grounding.ActiveCorpusBuilder import ActiveCorpusBuilder
from Df.Harness.Grounding.BlockLineAuditor import BlockLineAuditor
from Df.Harness.lib.grounding import dfh_clean_line_for_number_grounding
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by unused
def _assemble_corpus(infos: list[dict], ext_entries: list[tuple[str, str, set[str]]]) -> tuple[list[dict], str, str, set[str]]:
	return ActiveCorpusBuilder.assemble(infos, ext_entries)
# @used-by unused
def audit_active_block(auditor, block, filtered_locals: list[Path], ext_urls: list[str], active_primary: list[Path], norm_fn, num_fn) -> None:
	BlockLineAuditor(auditor, block, filtered_locals, ext_urls, active_primary, norm_fn, num_fn).audit()
# @used-by unused
def audit_block_lines(auditor, block, infos: list[dict], combined_raw: str, combined_norm: str, ev_nums: set[str], src_label: str) -> None:
	BlockLineAuditor.audit_lines(auditor, block, infos, combined_raw, combined_norm, ev_nums, src_label)
# @used-by unused
def build_active_corpus_cached(auditor, active_locals: list[Path], active_exts: list[str], active_primary: list[Path], norm_fn, num_fn) -> tuple[list[dict], str, str, set[str], str]:
	return ActiveCorpusBuilder(auditor, active_locals, active_exts, active_primary, norm_fn, num_fn).build()
# @used-by unused
def clean_line_for_number_grounding(sline: str, *, is_ticket: bool=False) -> str:
	return dfh_clean_line_for_number_grounding(sline, is_ticket=is_ticket)