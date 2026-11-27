# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from pathlib import Path
from typing import Any
from Df.Harness.lib.completion_checks import dfh_is_client_deliverable_path, dfh_issue_first_status, dfh_tdd_status
from Df.Harness.lib.completion_child_trace import dfh_scan_child_trace_turn
from Df.Harness.lib.completion_compaction import dfh_build_compaction_file_index, dfh_compact_compaction_check, dfh_compaction_status, dfh_write_compaction_index_file
from Df.Harness.lib.completion_core import NON_TURN_STATE_SUFFIXES, dfh_active_turn, dfh_conversation_journal_steps, dfh_format_conversation_journal_title, dfh_hash, dfh_journal_dir, dfh_json, dfh_native_scan, dfh_now, dfh_persist, dfh_read_meta, dfh_recorded, dfh_sync_antigravity_conversation_title, dfh_turn_key, dfh_turn_lock, dfh_turns_folder
from Df.Harness.lib.completion_state import dfh_load_turn_state, dfh_persist_turn_recovery
from Df.Harness.lib.hook_crash_ops import dfh_build_violation_recovery_receipt
from Df.Harness.lib.journal_integrity_ops import dfh_collect_handed_off_conversations, dfh_turn_matches_handoff
from Df.Harness.lib.journal_reservations import dfh_release_turn_steps
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_project_paths, dfh_same_project_root
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
from Df.Harness.lib.request_binding import dfh_explicit
from Df.Harness.lib.runtime_cache import dfh_skip_shell_violations
from Df.Harness.lib.runtime_context import dfh_platform_name
from Df.Harness.lib.storage import dfh_locked, dfh_replace_bytes
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_similar_project_exempt()`
def _allowed_similar_peers(root_p: Path, reg: Any) -> list[Path]:
	pp = dfh_project_paths(root_p, registry=reg, exact_root=True)
	allowed: list[Path] = []
	seen: set[str] = set()
	candidates = [*pp.similar_projects, *(Path(mem['project']) for grp in reg.similar_project_groups for mem in grp.get('members') or ())]
	for cand in candidates:
		cp = dfh_canonicalize_root_dir(cand, reg)
		ck = cp.as_posix().lower()
		if cp != root_p and ck not in seen:
			seen.add(ck)
			allowed.append(cp)
	return allowed
# @used-by :func:`dfh_recover_checkpoint()`
def _build_dry_run_checkpoint(root_p: Path, key: str, turn: dict[str, Any], ops: dict[str, Any]) -> dict[str, Any]:
	comp = dict(turn.get('compaction') or {})
	folder_fn = ops.get('folder') or dfh_turns_folder
	read_fn = ops.get('read') or dfh_read_meta
	comp_fn = ops.get('compaction_status') or (lambda r, k, t: dfh_compaction_status(r, k, t, folder_fn=folder_fn, read_fn=read_fn, is_deliv_fn=dfh_is_client_deliverable_path))
	comp_check = comp_fn(root_p, key, turn)
	raw_records = list(comp.get('pre_checkpoint_records') or [])
	file_index = dfh_build_compaction_file_index(root_p, list(comp.get('pre_checkpoint_read_files') or []), list(comp.get('post_checkpoint_read_files') or []), list(comp.get('evicted_unreread_files') or []), hash_fn=ops.get('hash') or dfh_hash)
	file_index.sort(key=lambda it: (not it['reread_required_if_cited'], not it['evicted_unreread'], it['path']))
	tool_counts = dict(Counter((t for rec in raw_records for t in (rec.get('tools') or ()))))
	step_summary = [{'step': rec.get('step'), 'tools': list(rec.get('tools') or []), 'output_chars': sum((len(str(o)) for o in (rec.get('outputs') or [])))} for rec in raw_records[-10:]]
	return {'turn_key': key, 'dry_run': True, 'covered_checkpoint_step': comp.get('last_checkpoint_step'), 'checkpoint_steps': list(comp.get('checkpoint_steps') or []), 'file_index_count': len(file_index), 'file_index': file_index[:30], 'file_index_truncated': 30 < len(file_index), 'pre_checkpoint_record_count': len(raw_records), 'tool_counts': tool_counts, 'step_summary': step_summary, 'step_summary_truncated': 10 < len(raw_records), 'compaction_check': dfh_compact_compaction_check(comp_check)}
# @used-by :func:`_execute_checkpoint_recovery()`
def _checkpoint_receipt(key: str, comp: dict[str, Any], compact_mode: bool, rel_dir: str, now_fn: Any) -> dict[str, Any]:
	return {'turn_key': key, 'recovered_at': now_fn(), 'compact_mode': compact_mode, 'covered_checkpoint_step': comp.get('last_checkpoint_step'), 'checkpoint_steps': list(comp.get('checkpoint_steps') or []), 'pre_checkpoint_tool_steps': list(comp.get('pre_checkpoint_tool_steps') or []), 'pre_checkpoint_read_files': list(comp.get('pre_checkpoint_read_files') or []), 'post_checkpoint_read_files': list(comp.get('post_checkpoint_read_files') or []), 'evicted_unreread_files': list(comp.get('evicted_unreread_files') or []), 'recovery_dir': rel_dir}
# @used-by :func:`dfh_recover_checkpoint()`
def _execute_checkpoint_recovery(root_p: Path, native: dict[str, Any], turn: dict[str, Any], key: str, ops: dict[str, Any]) -> dict[str, Any]:
	comp = dict(turn.get('compaction') or {})
	raw_records = list(comp.get('pre_checkpoint_records') or [])
	folder_fn, now_fn, json_fn = (ops.get('folder') or dfh_turns_folder, ops.get('now') or dfh_now, ops.get('json') or dfh_json)
	rec_dir, receipt_path, compact_mode = (folder_fn(root_p) / f'{key}-recovery', folder_fn(root_p) / f'{key}-checkpoint-recovery.json', 5 < len(raw_records))
	rel_dir = rec_dir.relative_to(root_p).as_posix() if rec_dir.is_relative_to(root_p) else str(rec_dir)
	with (ops.get('locked') or dfh_locked)(dfh_turn_lock(root_p, key, ops=ops)):
		rec_dir.mkdir(parents=True, exist_ok=True)
		indexed_records, inline_records = _write_recovery_records(rec_dir, root_p, raw_records, compact_mode)
		receipt = _checkpoint_receipt(key, comp, compact_mode, rel_dir, now_fn)
		dfh_replace_bytes(receipt_path, json_fn(receipt))
		path, value = (ops.get('state') or (lambda r, n, t: dfh_load_turn_state(r, n, t, ops=ops)))(root_p, native, turn)
		value.pop('admission_failure', None)
		idx_rel = dfh_write_compaction_index_file(root_p, key, turn, value['compaction_check'], folder_fn=folder_fn, now_fn=now_fn, json_fn=json_fn, hash_fn=ops.get('hash') or dfh_hash, step_records=indexed_records)
		value['compaction_check']['index_file'] = idx_rel
		(ops.get('persist') or (lambda p, v: dfh_persist(p, v, ops=ops)))(path, value)
	rel_file = receipt_path.relative_to(root_p).as_posix() if receipt_path.is_relative_to(root_p) else str(receipt_path)
	rec_key, rec_val = ('pre_checkpoint_records_preview', indexed_records[-5:]) if compact_mode else ('pre_checkpoint_records', inline_records)
	return {'turn_key': key, 'recovered_at': receipt['recovered_at'], 'compact_mode': compact_mode, 'covered_checkpoint_step': receipt['covered_checkpoint_step'], 'checkpoint_steps': receipt['checkpoint_steps'], 'recovery_dir': rel_dir, 'recovery_file': rel_file, 'index_file': idx_rel, 'pre_checkpoint_record_count': len(raw_records), 'compaction_check': dfh_compact_compaction_check(value['compaction_check'], index_file=idx_rel), rec_key: rec_val}
# @used-by :func:`dfh_handoff_launcher_turn()`
def _handoff_single_turn(sf: Path, launcher_p: Path, target_p: Path, job_str: str | None, ops: dict[str, Any]) -> dict[str, Any] | None:
	cur = _safe_read_open_turn(sf, ops.get('read') or dfh_read_meta)
	r: dict[str, Any] | None = None
	if None is not cur:
		key = str(cur.get('key') or sf.stem)
		req_ids = [it['id'] for it in (cur.get('requests') or ()) if isinstance(it, dict) and it.get('id')]
		try:
			dfh_release_turn_steps((ops.get('directory') or dfh_journal_dir)(launcher_p, cur.get('journal')), key, request_ids=req_ids)
		except (OSError, ValueError):
			pass
		cur.pop('reserved_journal_steps', None)
		cur['status'] = 'handed_off'
		cur['handed_off_to'] = {'project_root': str(target_p), 'job_id': job_str, 'handed_off_at': (ops.get('now') or dfh_now)()}
		(ops.get('persist') or (lambda p, v: dfh_persist(p, v, ops=ops)))(sf, cur)
		r = {'turn_key': key, 'conversation_id': cur.get('conversation_id'), 'launcher_root': str(launcher_p), 'target_root': str(target_p), 'job_id': job_str, 'status': 'handed_off'}
	return r
# @used-by :func:`dfh_handoff_launcher_turn()`
def _is_handoff_candidate(sf: Path, cid_filter: str | None, job_str: str | None, prior_cids: set[str], read_fn: Any) -> str | None:
	r: str | None = None
	if not sf.name.endswith(NON_TURN_STATE_SUFFIXES):
		st = _safe_read_open_turn(sf, read_fn)
		if None is not st:
			st_cid = str(st.get('conversation_id') or '').strip().lower()
			if (None is cid_filter or st_cid == cid_filter) and dfh_turn_matches_handoff(st, st_cid, job_str, prior_cids, dfh_explicit):
				r = str(st.get('key') or sf.stem)
	return r
# @used-by :func:`dfh_sync_conversation_title()`
def _latest_conversation_journal(t_dir: Path, cid_low: str, read_fn: Any) -> Any:
	r = None
	if t_dir.is_dir():
		for sf in sorted(t_dir.glob('*.json'), key=lambda p: p.stat().st_mtime_ns, reverse=True):
			if sf.name.endswith(NON_TURN_STATE_SUFFIXES):
				continue
			try:
				st_obj = read_fn(sf)
			except (OSError, ValueError):
				continue
			if str(st_obj.get('conversation_id') or '').strip().lower() == cid_low and st_obj.get('journal'):
				r = st_obj['journal']
				break
	return r
# @used-by :func:`dfh_ratchet_ok()`
# @used-by :func:`dfh_recover_checkpoint()`
# @used-by :func:`dfh_similar_project_exempt()`
def _load_active_turn(root_p: Path, conversation: Any, platform: Any, backend: Any, err_msg: str, ops: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
	native_fn = ops.get('native') or (lambda r, c, **kw: dfh_native_scan(r, c, ops=ops, **kw))
	native = native_fn(root_p, conversation, platform=platform, backend=backend)
	turn = dfh_active_turn(native)
	if None is turn:
		raise ValueError(err_msg)
	key = (ops.get('key') or dfh_turn_key)(native, turn)
	return (native, turn, key)
# @used-by :func:`dfh_similar_project_exempt()`
def _match_similar_peer(peer_raw: str, allowed_peers: list[Path], reg: Any) -> tuple[Path, list[str]]:
	from agent_tools.issue_lifecycle import similar_project_repo_slugs
	peer_norm_path = _normalize_peer_path(peer_raw, reg)
	target_norm = peer_norm_path or peer_raw.replace('\\', '/').rstrip('/').lower()
	matched_peer, matched_slugs = (None, [])
	for cand in allowed_peers:
		cand_slugs = similar_project_repo_slugs(cand, registry=reg)
		if peer_raw.lower() in {s.lower() for s in cand_slugs} or cand.as_posix().lower() == target_norm:
			matched_peer, matched_slugs = (cand, cand_slugs)
			break
	if None is matched_peer:
		raise ValueError(f'Unknown or undeclared similar peer project: {peer_raw}')
	return (matched_peer, matched_slugs)
# @used-by :func:`_match_similar_peer()`
def _normalize_peer_path(peer_raw: str, reg: Any) -> str | None:
	r: str | None = None
	if '\\' in peer_raw or ':' in peer_raw or Path(peer_raw).is_absolute() or Path(peer_raw).is_dir():
		try:
			r = dfh_canonicalize_root_dir(peer_raw, reg).as_posix().lower()
		except (OSError, ValueError):
			r = None
	return r
# @used-by :func:`dfh_similar_project_exempt()`
def _persist_similar_exemption(root_p: Path, native: dict[str, Any], turn: dict[str, Any], key: str, ex_path: Path, entry: dict[str, Any], ops: dict[str, Any]) -> dict[str, Any]:
	read_fn, json_fn = (ops.get('read') or dfh_read_meta, ops.get('json') or dfh_json)
	with (ops.get('locked') or dfh_locked)(dfh_turn_lock(root_p, key, ops=ops)):
		items = _read_list_items(ex_path, 'exemptions', read_fn, 'peer_root', entry['peer_root'].lower())
		items.append(entry)
		dfh_replace_bytes(ex_path, json_fn({'turn_key': key, 'exemptions': items}))
		path, value = (ops.get('state') or (lambda r, n, t: dfh_load_turn_state(r, n, t, ops=ops)))(root_p, native, turn)
		if value.get('code_lifecycle_check', {}).get('verified'):
			value.pop('admission_failure', None)
		(ops.get('persist') or (lambda p, v: dfh_persist(p, v, ops=ops)))(path, value)
	return value
# @used-by :func:`_persist_similar_exemption()`
# @used-by :func:`dfh_ratchet_ok()`
def _read_list_items(path: Path, field: str, read_fn: Any, skip_key: str, skip_val: str) -> list[dict[str, Any]]:
	r: list[dict[str, Any]] = []
	if path.is_file():
		try:
			raw_loaded = read_fn(path)
			raw_list = raw_loaded.get(field) if isinstance(raw_loaded, dict) else raw_loaded
			if isinstance(raw_list, list):
				r = [it for it in raw_list if isinstance(it, dict) and str(it.get(skip_key) or '').replace('\\', '/').lower() != skip_val]
		except (OSError, ValueError):
			r = []
	return r
# @used-by :func:`_handoff_single_turn()`
# @used-by :func:`_is_handoff_candidate()`
def _safe_read_open_turn(sf: Path, read_fn: Any) -> dict[str, Any] | None:
	r: dict[str, Any] | None = None
	if sf.is_file():
		try:
			cur = read_fn(sf)
		except (OSError, ValueError):
			cur = None
		if isinstance(cur, dict) and 'open' == cur.get('status') and (not dfh_recorded(cur)):
			r = cur
	return r
# @used-by :func:`dfh_issue_first_check_turn()`
# @used-by :func:`dfh_tdd_check_turn()`
def _scan_readonly_turn(root: Any, conversation: Any, platform: Any, backend: Any, ops: dict[str, Any]) -> tuple[Path, str, str, dict[str, Any]]:
	from agent_tools.source_grounding import read_only_grounding
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	plat_fn = ops.get('platform_name') or (lambda p: dfh_platform_name(p, settings_fn=ops.get('settings')))
	eff_plat = plat_fn(platform)
	eff_conv = conversation or (os.environ.get('CODEX_THREAD_ID') if 'codex' == eff_plat else None)
	native_fn = ops.get('native') or (lambda r, c, **kw: dfh_native_scan(r, c, ops=ops, **kw))
	with read_only_grounding(), dfh_skip_shell_violations():
		native = native_fn(root_p, eff_conv, platform=eff_plat, backend=backend)
		role = 'primary' if native['primary'] else 'child'
		turn_obj = dfh_active_turn(native) if native['primary'] else dfh_scan_child_trace_turn(root_p, eff_conv, native)
		turn_key = (ops.get('key') or dfh_turn_key)(native, turn_obj)
	return (root_p, role, turn_key, turn_obj)
# @used-by :func:`_execute_checkpoint_recovery()`
def _write_recovery_records(rec_dir: Path, root_p: Path, raw_records: list[dict[str, Any]], compact_mode: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
	indexed, inline = ([], [])
	for rec in raw_records:
		st, outs = (rec.get('step'), list(rec.get('outputs') or []))
		step_file = rec_dir / f'step-{st}.txt'
		if outs:
			dfh_replace_bytes(step_file, ('\n--- OUTPUT ---\n'.join(outs) + '\n').encode('utf-8'))
		rel_step = step_file.relative_to(root_p).as_posix() if step_file.is_relative_to(root_p) else str(step_file)
		indexed.append({'step': st, 'tools': list(rec.get('tools') or []), 'output_file': rel_step if outs else None, 'output_preview': [o[:200] for o in outs[:2]]})
		if not compact_mode:
			inline.append({**rec, 'output_file': rel_step if outs else None})
	return (indexed, inline)
# @used-by :func:`Df.Harness.lib.completion_commands._try_launcher_handoff()`
# @used-by :func:`agent_tools.completion.handoff_launcher_turn()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_recovery_validation_and_empty_handoff()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_env_isolation_auditor_and_recovery_ops()`
def dfh_handoff_launcher_turn(launcher_root: Any, target_root: Any, job_id: Any, *, conversation_id: Any=None, ops: dict[str, Any] | None=None) -> list[dict[str, Any]]:
	eff_ops = ops or {}
	r: list[dict[str, Any]] = []
	if launcher_root and target_root:
		reg = dfh_load_registry()
		launcher_p, target_p = (dfh_canonicalize_root_dir(launcher_root, reg), dfh_canonicalize_root_dir(target_root, reg))
		t_dir = (eff_ops.get('folder') or dfh_turns_folder)(launcher_p)
		cid_filter, job_str = (str(conversation_id or '').strip().lower() or None, str(job_id or '').strip() or None)
		if (not dfh_same_project_root(launcher_p, target_p)) and t_dir.is_dir() and (cid_filter or job_str):
			read_fn, lock_fn = (eff_ops.get('read') or dfh_read_meta, eff_ops.get('locked') or dfh_locked)
			prior_cids = dfh_collect_handed_off_conversations(t_dir, target_p, read_fn=read_fn, same_root_fn=dfh_same_project_root)
			for sf in sorted(t_dir.glob('*.json')):
				key = _is_handoff_candidate(sf, cid_filter, job_str, prior_cids, read_fn)
				if None is not key:
					with lock_fn(dfh_turn_lock(launcher_p, key, ops=eff_ops)):
						entry = _handoff_single_turn(sf, launcher_p, target_p, job_str, eff_ops)
						if None is not entry:
							r.append(entry)
	return r
# @used-by :func:`Df.Harness.lib.completion_commands._dispatch_completion_table()`
# @used-by :func:`agent_tools.completion.issue_first_check_turn()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_recovery_validation_and_empty_handoff()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_env_isolation_auditor_and_recovery_ops()`
def dfh_issue_first_check_turn(root: Any, conversation: Any=None, *, platform: Any=None, backend: Any=None, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	root_p, role, turn_key, turn_obj = _scan_readonly_turn(root, conversation, platform, backend, eff_ops)
	if_chk = (eff_ops.get('issue_first_status') or dfh_issue_first_status)(root_p, turn_obj)
	return {'valid': bool(if_chk.get('verified', True)), 'read_only': True, 'role': role, 'turn_key': turn_key, 'issue_first_check': if_chk, 'event_count': len(turn_obj.get('issue_first_events') or [])}
# @used-by :func:`Df.Harness.lib.completion_commands._dispatch_completion_table()`
# @used-by :func:`agent_tools.completion.ratchet_ok()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_recovery_validation_and_empty_handoff()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_env_isolation_auditor_and_recovery_ops()`
def dfh_ratchet_ok(root: Any, file_path: Any, reason: Any, conversation: Any=None, *, platform: Any=None, backend: Any=None, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	from agent_tools.tdd_gate import validate_ratchet_reason
	eff_ops = ops or {}
	file_clean = (file_path or '').strip()
	if not file_clean:
		raise ValueError('Provide --file identifying the test file whose expectation is intentionally changing')
	ok_r, err_r = validate_ratchet_reason(reason)
	if not ok_r:
		raise ValueError(err_r)
	reason_clean = ' '.join((reason or '').strip().split())
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	_, _, key = _load_active_turn(root_p, conversation, platform, backend, 'No active primary native turn to record RATCHET-OK approval', eff_ops)
	rc_path = (eff_ops.get('folder') or dfh_turns_folder)(root_p) / f'{key}-ratchet-ok.json'
	entry = {'file': file_clean, 'reason': reason_clean, 'recorded_at': (eff_ops.get('now') or dfh_now)()}
	with (eff_ops.get('locked') or dfh_locked)(dfh_turn_lock(root_p, key, ops=eff_ops)):
		items = _read_list_items(rc_path, 'approvals', eff_ops.get('read') or dfh_read_meta, 'file', file_clean.replace('\\', '/').lower())
		items.append(entry)
		dfh_replace_bytes(rc_path, (eff_ops.get('json') or dfh_json)({'turn_key': key, 'approvals': items}))
	rel_file = rc_path.relative_to(root_p).as_posix() if rc_path.is_relative_to(root_p) else str(rc_path)
	return {'turn_key': key, 'file': file_clean, 'reason': reason_clean, 'receipt_file': rel_file, 'approvals': items}
# @used-by :func:`Df.Harness.lib.completion_commands._dispatch_completion_table()`
# @used-by :func:`agent_tools.completion.recover_checkpoint()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_recovery_validation_and_empty_handoff()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_env_isolation_auditor_and_recovery_ops()`
def dfh_recover_checkpoint(root: Any, conversation: Any=None, *, platform: Any=None, backend: Any=None, dry_run: bool=False, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	if dry_run:
		from agent_tools.source_grounding import read_only_grounding
		with read_only_grounding():
			_, turn, key = _load_active_turn(root_p, conversation, platform, backend, 'No active primary native turn to recover', eff_ops)
			r = _build_dry_run_checkpoint(root_p, key, turn, eff_ops)
	else:
		native, turn, key = _load_active_turn(root_p, conversation, platform, backend, 'No active primary native turn to recover', eff_ops)
		r = _execute_checkpoint_recovery(root_p, native, turn, key, eff_ops)
	return r
# @used-by :func:`Df.Harness.lib.completion_commands._dispatch_completion_table()`
# @used-by :func:`agent_tools.completion.recover_turn_violation()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_recovery_validation_and_empty_handoff()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_env_isolation_auditor_and_recovery_ops()`
def dfh_recover_turn_violation(root: Any, conversation: Any=None, *, reason: Any=None, platform: Any=None, backend: Any=None, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	now_fn = eff_ops.get('now') or dfh_now
	return dfh_persist_turn_recovery(root, conversation, 'violation-recovery', lambda rp, k, t, nat: dfh_build_violation_recovery_receipt(rp, k, t, reason, now_fn, native=nat), platform=platform, backend=backend, ops=eff_ops)
# @used-by :func:`Df.Harness.lib.completion_commands._dispatch_completion_table()`
# @used-by :func:`agent_tools.completion.similar_project_exempt()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_recovery_validation_and_empty_handoff()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_env_isolation_auditor_and_recovery_ops()`
def dfh_similar_project_exempt(root: Any, peer: Any, reason: Any, conversation: Any=None, *, platform: Any=None, backend: Any=None, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	reason_clean = (reason or '').strip()
	if 30 > len(reason_clean):
		raise ValueError('Exemption reason must be an explicit technical justification of at least 30 characters')
	peer_raw = (peer or '').strip()
	if not peer_raw:
		raise ValueError('Select a declared --peer project root or GitHub owner/repo slug')
	reg = dfh_load_registry()
	root_p = dfh_canonicalize_root_dir(root, reg)
	matched_peer, matched_slugs = _match_similar_peer(peer_raw, _allowed_similar_peers(root_p, reg), reg)
	native, turn, key = _load_active_turn(root_p, conversation, platform, backend, 'No active primary native turn to record similar-project exemption', eff_ops)
	ex_path = (eff_ops.get('folder') or dfh_turns_folder)(root_p) / f'{key}-similar-exemptions.json'
	entry = {'peer': peer_raw, 'peer_root': matched_peer.as_posix(), 'peer_repos': matched_slugs, 'reason': reason_clean, 'recorded_at': (eff_ops.get('now') or dfh_now)()}
	value = _persist_similar_exemption(root_p, native, turn, key, ex_path, entry, eff_ops)
	rel_file = ex_path.relative_to(root_p).as_posix() if ex_path.is_relative_to(root_p) else str(ex_path)
	return {'turn_key': key, 'peer_root': matched_peer.as_posix(), 'peer_repos': matched_slugs, 'reason': reason_clean, 'exemption_file': rel_file, 'code_lifecycle_check': value['code_lifecycle_check']}
# @used-by :func:`Df.Harness.lib.completion_commands._dispatch_completion_table()`
# @used-by :func:`agent_tools.completion.sync_conversation_title()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_recovery_validation_and_empty_handoff()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_env_isolation_auditor_and_recovery_ops()`
def dfh_sync_conversation_title(root: Any, conversation: Any=None, *, platform: Any=None, backend: Any=None, journal_directory: Any=None, dry_run: bool=False, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	native = (eff_ops.get('native') or (lambda r, c, **kw: dfh_native_scan(r, c, ops=eff_ops, **kw)))(root_p, conversation, platform=platform, backend=backend)
	if not native.get('primary'):
		raise ValueError('A child executor has no primary conversation title to synchronize')
	eff_j = journal_directory
	if None is eff_j:
		eff_j = _latest_conversation_journal((eff_ops.get('folder') or dfh_turns_folder)(root_p), str(native.get('conversation_id') or '').strip().lower(), eff_ops.get('read') or dfh_read_meta)
	jdir = (eff_ops.get('directory') or dfh_journal_dir)(root_p, eff_j)
	res = dfh_sync_antigravity_conversation_title(root_p, native, jdir, dry_run=dry_run, ops=eff_ops)
	if None is res:
		steps = dfh_conversation_journal_steps(root_p, jdir, native.get('conversation_id') or '', ops=eff_ops)
		res = {'synced': False, 'changed': False, 'title': dfh_format_conversation_journal_title(steps), 'steps': steps, 'conversation_id': native.get('conversation_id'), 'reason': 'unsupported_platform'}
	return {**res, 'platform': native['platform'], 'journal': str(jdir)}
# @used-by :func:`Df.Harness.lib.completion_commands._dispatch_completion_table()`
# @used-by :func:`agent_tools.completion.tdd_check_turn()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion.DfHarnessS11Wave2DCompletionTests.test_completion_recovery_validation_and_empty_handoff()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_env_isolation_auditor_and_recovery_ops()`
def dfh_tdd_check_turn(root: Any, conversation: Any=None, *, platform: Any=None, backend: Any=None, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	from agent_tools.tdd.diff_coverage import enrich_tdd_check_report
	eff_ops = ops or {}
	root_p, role, turn_key, turn_obj = _scan_readonly_turn(root, conversation, platform, backend, eff_ops)
	return enrich_tdd_check_report(root_p, role, turn_key, turn_obj, (eff_ops.get('tdd_status') or dfh_tdd_status)(root_p, turn_obj))
