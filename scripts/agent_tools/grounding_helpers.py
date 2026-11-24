# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Cache normalized text and numeric tokens in LocalSourceGroundingAuditor corpus":
# https://github.com/dmitry-ai/harness/issues/216
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Skip blocking grounding on scratch drafts and add line locations to diagnostics":
# https://github.com/dmitry-ai/harness/issues/214
from __future__ import annotations
from pathlib import Path
from urllib.parse import urldefrag
def _assemble_corpus(infos: list[dict], ext_entries: list[tuple[str, str, set[str]]]) -> tuple[list[dict], str, str, set[str]]:
	raw_parts: list[str] = []
	norm_parts: list[str] = []
	ev_nums: set[str] = set()
	for inf in infos:
		raw_parts.append(inf['raw'])
		if inf['norm']:
			norm_parts.append(inf['norm'])
		ev_nums.update(inf['nums'])
	for raw, norm, nums in ext_entries:
		if raw:
			raw_parts.append(raw)
		if norm:
			norm_parts.append(norm)
		ev_nums.update(nums)
	return (infos, '\n'.join(raw_parts), ' '.join(norm_parts), ev_nums)
def _load_ext_url_entry(bucket: dict, nu: str, norm_fn, num_fn) -> tuple[str, str, set[str]]:
	r = bucket['urls'].get(nu)
	if None is r:
		blobs = [str(t) for t in ((bucket['obs'] or {}).get(nu) or ()) if t]
		raw = '\n'.join(blobs)
		r = (raw, norm_fn(raw) if raw else '', num_fn(raw) if raw else set())
		bucket['urls'][nu] = r
	return r
def _norm_ext_urls(active_exts: list[str]) -> tuple[str, ...]:
	seen: list[str] = []
	for u in active_exts:
		s = (u or '').strip()
		if s:
			nu = urldefrag(s)[0].rstrip('/')
			if nu not in seen:
				seen.append(nu)
	return tuple(seen)
def _obs_bucket(cache: dict, observed_texts: dict | None) -> dict:
	store = cache.setdefault('__obs_buckets__', {})
	oid = 0 if None is observed_texts else id(observed_texts)
	bucket = store.get(oid)
	if None is bucket or bucket['obs'] is not observed_texts:
		bucket = {'obs': observed_texts, 'urls': {}, 'corpora': {}}
		store[oid] = bucket
	return bucket
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
def build_active_corpus_cached(auditor, active_locals: list[Path], active_exts: list[str], active_primary: list[Path], norm_fn, num_fn) -> tuple[list[dict], str, str, set[str], str]:
	norm_exts = _norm_ext_urls(active_exts)
	bucket = _obs_bucket(auditor.cache, auditor.observed_texts)
	ckey = (tuple(active_locals), norm_exts)
	cached = bucket['corpora'].get(ckey)
	if None is cached:
		infos = [auditor.index.load_source_info(p, auditor.cache) for p in active_locals]
		ext_entries = [_load_ext_url_entry(bucket, nu, norm_fn, num_fn) for nu in norm_exts] if auditor.observed_texts else []
		cached = _assemble_corpus(infos, ext_entries)
		bucket['corpora'][ckey] = cached
	infos, combined_raw, combined_norm, ev_nums = cached
	label = ', '.join((auditor.index.locator_for(p) for p in active_primary[:2]))
	return (infos, combined_raw, combined_norm, ev_nums, label)
