# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_resolve import dfh_project_paths
from Df.Harness.lib.storage import dfh_replace_bytes
import hashlib
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_write_compaction_index_file()`
def _build_compaction_index_payload(root: Path, key: str, comp_check: dict, raw_recs: list[dict], now_fn, hash_fn) -> dict[str, Any]:
	pre_reads = list(comp_check.get('pre_checkpoint_read_files') or [])
	post_reads = list(comp_check.get('post_checkpoint_read_files') or [])
	evicted = list(comp_check.get('evicted_unreread_files') or [])
	return {
		'schema_version': 1,
		'turn_key': key,
		'updated_at': now_fn(),
		'covered_checkpoint_step': comp_check.get('last_checkpoint_step'),
		'checkpoint_steps': list(comp_check.get('checkpoint_steps') or []),
		'pre_checkpoint_tool_steps': list(comp_check.get('pre_checkpoint_tool_steps') or []),
		'post_checkpoint_recovery_steps': list(comp_check.get('post_checkpoint_recovery_steps') or []),
		'pre_checkpoint_read_files': pre_reads,
		'post_checkpoint_read_files': post_reads,
		'post_checkpoint_written_files': list(comp_check.get('post_checkpoint_written_files') or []),
		'evicted_unreread_files': evicted,
		'unreread_analysis_sources': list(comp_check.get('unreread_analysis_sources') or []),
		'file_index': dfh_build_compaction_file_index(root, pre_reads, post_reads, evicted, hash_fn=hash_fn),
		'pre_checkpoint_records': raw_recs,
	}
# @used-by :func:`dfh_build_compaction_file_index()`
def _build_file_index_entry(root: Path, raw_p: str, ev_set: set[str], post_set: set[str], hash_fn) -> dict[str, Any]:
	pk = raw_p.replace('\\', '/').lower()
	p_obj = Path(raw_p)
	if not p_obj.is_absolute():
		p_obj = (root / p_obj).resolve()
	exists, sha, byte_len, line_cnt = _stat_and_hash_file(p_obj, hash_fn)
	is_ev = pk in ev_set
	reread_req = bool(is_ev and (pk.endswith('/kb/source.md') or '/source/' in pk or '/res/' in pk or '/\u227a/' in pk or '/kb/' in pk))
	rel_p = p_obj.relative_to(root).as_posix() if p_obj.is_relative_to(root) else p_obj.as_posix()
	return {'path': rel_p, 'exists': exists, 'sha256': sha, 'bytes': byte_len, 'lines': line_cnt, 'evicted_unreread': is_ev, 'reread_after_checkpoint': pk in post_set, 'reread_required_if_cited': reread_req}
# @used-by :func:`dfh_compaction_status()`
def _collect_unreread_analysis_sources(post_writes: list[str], evicted_lower: dict[str, str], ev_prefix: str, root: Path, is_deliv_fn) -> list[str]:
	unreread: list[str] = []
	writes_deliv = False
	for w in post_writes:
		wnorm = w.replace('\\', '/')
		wlow = wnorm.lower()
		if wlow.endswith('/kb/analysis.md'):
			sib = (Path(wnorm).parent / 'source.md').as_posix().lower()
			if sib in evicted_lower and evicted_lower[sib] not in unreread:
				unreread.append(evicted_lower[sib])
		elif is_deliv_fn(wlow, root):
			writes_deliv = True
	if writes_deliv:
		for ev_l, ev_orig in evicted_lower.items():
			if ('/.system_generated/steps/' in ev_l or ev_l.endswith('/kb/source.md') or '/source/' in ev_l or '/\ua616/kb/evidence/' in ev_l or ev_l.startswith(ev_prefix)) and ev_orig not in unreread:
				unreread.append(ev_orig)
	return unreread
# @used-by :func:`dfh_find_evicted_cited_files()`
def _is_pre_checkpoint_authored(pp: Any, turn_key: str | None, comp_check: dict, response: str) -> bool:
	r = False
	if turn_key:
		scratch_ans = pp.scratch_dir / f'answer-{turn_key}.md'
		post_cp_w_low = {str(w).replace('\\', '/').lower() for w in (comp_check.get('post_checkpoint_written_files') or [])}
		if scratch_ans.is_file() and scratch_ans.resolve().as_posix().lower() not in post_cp_w_low:
			try:
				r = scratch_ans.read_text(encoding='utf-8') == response
			except OSError:
				r = False
	return r
# @used-by :func:`dfh_compaction_status()`
def _recovered_via_receipt(receipt_path: Path, last_cp: Any, read_fn) -> bool:
	r = False
	if receipt_path.is_file():
		try:
			cov = read_fn(receipt_path).get('covered_checkpoint_step')
			r = None is last_cp or (isinstance(cov, int) and cov >= last_cp)
		except (OSError, ValueError):
			r = False
	return r
# @used-by :func:`_build_file_index_entry()`
def _stat_and_hash_file(p_obj: Path, hash_fn) -> tuple[bool, str | None, int | None, int | None]:
	exists, sha, byte_len, line_cnt = (False, None, None, None)
	try:
		if p_obj.is_file():
			exists = True
			byte_len = p_obj.stat().st_size
			if byte_len <= 16 * 1024 * 1024:
				raw_b = p_obj.read_bytes()
				sha = hash_fn(raw_b)
				line_cnt = max(1, raw_b.count(b'\n') + (0 if raw_b.endswith(b'\n') or (not raw_b) else 1))
	except OSError:
		pass
	return (exists, sha, byte_len, line_cnt)
# @used-by :func:`dfh_write_compaction_index_file()`
def _summarize_pre_checkpoint_records(root: Path, rec_dir: Path, turn: dict) -> list[dict]:
	raw_recs: list[dict] = []
	for rec in ((turn.get('compaction') or {}).get('pre_checkpoint_records')) or []:
		st = rec.get('step')
		outs = list(rec.get('outputs') or [])
		step_file = rec_dir / f'step-{st}.txt'
		if step_file.is_file():
			rel_step = step_file.relative_to(root).as_posix() if step_file.is_relative_to(root) else str(step_file)
			raw_recs.append({'step': st, 'tools': list(rec.get('tools') or []), 'output_file': rel_step, 'output_preview': [o[:200] for o in outs[:2]]})
		else:
			raw_recs.append(rec)
	return raw_recs
# @used-by :func:`Df.Harness.lib.completion_recovery._build_dry_run_checkpoint()`
# @used-by :func:`_build_compaction_index_payload()`
# @used-by :func:`agent_tools.completion._build_compaction_file_index()`
def dfh_build_compaction_file_index(root: Path, pre_reads: list[str], post_reads: list[str], evicted_unreread: list[str], *, hash_fn=None) -> list[dict]:
	h_fn = hash_fn if None is not hash_fn else (lambda b: hashlib.sha256(b).hexdigest())
	ev_set = {str(p).replace('\\', '/').lower() for p in (evicted_unreread or ())}
	post_set = {str(p).replace('\\', '/').lower() for p in (post_reads or ())}
	seen: set[str] = set()
	ordered: list[str] = []
	for p in [*(pre_reads or ()), *(evicted_unreread or ())]:
		ps = str(p or '').strip()
		pk = ps.replace('\\', '/').lower()
		if ps and pk not in seen:
			seen.add(pk)
			ordered.append(ps)
	return [_build_file_index_entry(root, raw_p, ev_set, post_set, h_fn) for raw_p in ordered]
# @used-by :func:`Df.Harness.lib.completion_commands._build_begin_result()`
# @used-by :func:`Df.Harness.lib.completion_recovery._build_dry_run_checkpoint()`
# @used-by :func:`Df.Harness.lib.completion_recovery._execute_checkpoint_recovery()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__finalize_prepared_state()`
def dfh_compact_compaction_check(comp_check: dict, *, index_file: str | None=None) -> dict:
	occurred = bool(comp_check.get('occurred'))
	eff_idx = (index_file if None is not index_file else comp_check.get('index_file')) if occurred else None
	return {
		'verified': bool(comp_check.get('verified')),
		'occurred': occurred,
		'checkpoint_steps': list(comp_check.get('checkpoint_steps') or []),
		'last_checkpoint_step': comp_check.get('last_checkpoint_step'),
		'recovered_in_trace': bool(comp_check.get('recovered_in_trace')),
		'recovered_via_receipt': bool(comp_check.get('recovered_via_receipt')),
		'pre_checkpoint_tool_step_count': len(comp_check.get('pre_checkpoint_tool_steps') or []),
		'pre_checkpoint_read_count': len(comp_check.get('pre_checkpoint_read_files') or []),
		'post_checkpoint_read_count': len(comp_check.get('post_checkpoint_read_files') or []),
		'post_checkpoint_write_count': len(comp_check.get('post_checkpoint_written_files') or []),
		'evicted_unreread_count': len(comp_check.get('evicted_unreread_files') or []),
		'index_file': eff_idx,
		'unreread_analysis_sources': list(comp_check.get('unreread_analysis_sources') or []),
	}
# @used-by :func:`Df.Harness.lib.completion_commands._child_check_value()`
# @used-by :func:`Df.Harness.lib.completion_recovery._build_dry_run_checkpoint()`
# @used-by :func:`Df.Harness.lib.completion_state._refresh_core_checks()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`agent_tools.completion._compaction_status()`
def dfh_compaction_status(root: Path, key: str | None, turn: dict, *, folder_fn, read_fn, is_deliv_fn) -> dict:
	pp = dfh_project_paths(root, exact_root=True)
	ev_prefix = pp.evidence_dir.as_posix().lower().rstrip('/') + '/'
	comp = dict(turn.get('compaction') or {})
	occurred, last_cp = (bool(comp.get('occurred')), comp.get('last_checkpoint_step'))
	pre_steps, post_rec = (list(comp.get('pre_checkpoint_tool_steps') or []), list(comp.get('post_checkpoint_recovery_steps') or []))
	pre_reads, post_reads, post_writes = (list(comp.get('pre_checkpoint_read_files') or []), list(comp.get('post_checkpoint_read_files') or []), list(comp.get('post_checkpoint_written_files') or []))
	evicted_unreread = list(comp.get('evicted_unreread_files') or [])
	evicted_lower = {p.replace('\\', '/').lower(): p for p in evicted_unreread}
	unreread_src = _collect_unreread_analysis_sources(post_writes, evicted_lower, ev_prefix, root, is_deliv_fn)
	recovered_in_trace = bool(comp.get('recovered_in_trace', True))
	rec_via = _recovered_via_receipt(folder_fn(root) / f'{key}-checkpoint-recovery.json', last_cp, read_fn)
	verified = bool((not occurred or not pre_steps or recovered_in_trace or rec_via) and (not unreread_src))
	idx_path = (folder_fn(root) / f'{key}-recovery/index.json') if key else None
	idx_rel = (idx_path.relative_to(root).as_posix() if idx_path.is_relative_to(root) else str(idx_path)) if None is not idx_path and occurred and idx_path.is_file() else None
	return {'verified': verified, 'occurred': occurred, 'checkpoint_steps': list(comp.get('checkpoint_steps') or []), 'last_checkpoint_step': last_cp, 'pre_checkpoint_tool_steps': pre_steps, 'post_checkpoint_recovery_steps': post_rec, 'recovered_in_trace': recovered_in_trace, 'recovered_via_receipt': rec_via, 'pre_checkpoint_read_files': pre_reads, 'post_checkpoint_read_files': post_reads, 'post_checkpoint_written_files': post_writes, 'evicted_unreread_files': evicted_unreread, 'unreread_analysis_sources': unreread_src, 'index_file': idx_rel}
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__check_evicted_citations()`
def dfh_find_evicted_cited_files(root: Path, pp: Any, turn_key: str | None, compaction_check: dict, response: str) -> list[str]:
	unreread_cited: list[str] = []
	if compaction_check.get('occurred') and compaction_check.get('evicted_unreread_files') and (not _is_pre_checkpoint_authored(pp, turn_key, compaction_check, response)):
		from agent_tools.source_grounding import extract_block_links, markdown_parser
		ev_map = {p.replace('\\', '/').lower(): p for p in compaction_check['evicted_unreread_files']}
		for blk in markdown_parser().parse(response):
			if 'inline' == blk.type:
				for rp in extract_block_links(blk, root, None)[0]:
					rlow = rp.as_posix().lower()
					if rlow in ev_map and (rlow.endswith('/kb/source.md') or '/source/' in rlow or '/res/' in rlow or '/\u227a/' in rlow or '/kb/' in rlow) and ev_map[rlow] not in unreread_cited:
						unreread_cited.append(ev_map[rlow])
		for ev_low, ev_orig in ev_map.items():
			m_res = re.search('/(?:res|\\u227a)/(?:\\d+[-\\u2013]\\d+/)?(\\d+\\.md)$', ev_low)
			if m_res and re.search(f'(?:\\bres|\\u227a)/(?:\\d+[-\\u2013]\\d+/)?{re.escape(m_res.group(1))}\\b', response, re.I) and ev_orig not in unreread_cited:
				unreread_cited.append(ev_orig)
	return unreread_cited
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_recovery._execute_checkpoint_recovery()`
# @used-by :func:`agent_tools.completion._write_compaction_index_file()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__finalize_prepared_state()`
def dfh_write_compaction_index_file(root: Path, key: str, turn: dict, comp_check: dict, *, folder_fn, now_fn, json_fn, hash_fn=None, step_records: list[dict] | None=None) -> str:
	rec_dir = folder_fn(root) / f'{key}-recovery'
	rec_dir.mkdir(parents=True, exist_ok=True)
	idx_path = rec_dir / 'index.json'
	raw_recs = step_records if None is not step_records else _summarize_pre_checkpoint_records(root, rec_dir, turn)
	payload = _build_compaction_index_payload(root, key, comp_check, raw_recs, now_fn, hash_fn)
	dfh_replace_bytes(idx_path, json_fn(payload))
	return idx_path.relative_to(root).as_posix() if idx_path.is_relative_to(root) else str(idx_path)