# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Skip blocking grounding on scratch drafts and add line locations to diagnostics":
# https://github.com/dmitry-ai/harness/issues/214
from __future__ import annotations
def _tag_new_errors(errors: list[str], start_idx: int, line_no: int | None) -> None:
	if None is not line_no:
		suffix = f' (line {line_no})'
		for idx in range(start_idx, len(errors)):
			if '(line ' not in errors[idx]:
				errors[idx] = errors[idx] + suffix
def audit_block_lines(auditor, block, infos: list[dict], combined_raw: str, combined_norm: str, ev_nums: set[str], src_label: str) -> None:
	bmap = getattr(block, 'map', None)
	base_line = (int(bmap[0]) + 1) if isinstance(bmap, (list, tuple)) and bmap else None
	if 0 < auditor.quote_depth:
		before = len(auditor.errors)
		auditor._check_blockquote(block.content, combined_norm, src_label)
		_tag_new_errors(auditor.errors, before, base_line)
	else:
		ticket_infos = [inf for inf in infos if inf['is_ticket_source']]
		valid_msg_nums = {n for inf in ticket_infos for n in inf['msg_nums']}
		bound_ticket_ids = {inf['ticket_id'] for inf in ticket_infos if inf['ticket_id']}
		any_cyrillic_source = any((inf['has_cyrillic'] for inf in infos))
		for offset, line in enumerate(block.content.split('\n')):
			before = len(auditor.errors)
			auditor._check_prose_line(line.strip(), infos, combined_raw, combined_norm, ev_nums, src_label, ticket_infos, valid_msg_nums, bound_ticket_ids, any_cyrillic_source)
			_tag_new_errors(auditor.errors, before, None if None is base_line else base_line + offset)
