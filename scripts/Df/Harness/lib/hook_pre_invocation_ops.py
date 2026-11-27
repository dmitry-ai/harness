# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from Df.Harness.lib import journal as dfh_journal
from Df.Harness.lib.path_resolve import dfh_project_paths
from Df.Harness.lib.runtime_context import dfh_default_user_locale
import hashlib
import json
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_binding_violation_message()`
def _diagnose_no_active_turn(msg: str, canon_root: Path, conversation_id: str, backend: Path) -> str | None:
	r: str | None = None
	try:
		from Df.Harness.Platform.Antigravity.TurnScanner import TurnScanner
		from Df.Harness.lib.request_binding import dfh_format_binding_diagnostic
		native = TurnScanner(canon_root, conversation_id, backend=backend).scan()
		if any((not t.get('completed') and (not t.get('aborted')) for t in native.get('turns') or [])):
			if '(binding=' not in msg:
				diag = native.get('binding_diagnostic') if isinstance(native.get('binding_diagnostic'), dict) else {}
				detail = dfh_format_binding_diagnostic(diag.get('expected_root') or str(canon_root), diag.get('binding'), expected_job_id=diag.get('expected_job_id'))
				r = f'{msg} ({detail})' if detail else msg
			else:
				r = msg
	except Exception:
		r = None
	return r
# @used-by :func:`dfh_pre_flush_begin_context()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_verif_pre_invocation_and_crash_ops()`
def _has_planner_steps(conversations_dir: Path, conversation_id: str) -> bool:
	conv_db = conversations_dir / f'{conversation_id}.db'
	r = False
	if conv_db.is_file():
		conn = sqlite3.connect(conv_db.resolve().as_uri() + '?mode=ro', uri=True)
		try:
			r = None is not conn.execute('SELECT 1 FROM steps WHERE step_type=15 LIMIT 1').fetchone()
		except Exception:
			r = False
		finally:
			conn.close()
	return r
# @used-by :func:`check_pre_invocation._binding_violation_message()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__run_begin()`
def dfh_binding_violation_message(exc: ValueError, canon_root: Path, conversation_id: str, backend: Path) -> str | None:
	msg = str(exc)
	if any((tok in msg for tok in ('partial record', 'primary/child identity is unavailable', 'Exact current native conversation UUID required', 'Exact native Antigravity conversation UUID required'))):
		r: str | None = None
	elif any((tok in msg for tok in ('do not identify', 'bound to another project', 'already has a different journal', 'different native owner', 'exists in multiple Antigravity instances', 'A prepared answer does not cover'))):
		r = msg
	elif 'No active native user turn belonging entirely to this project' in msg:
		r = _diagnose_no_active_turn(msg, canon_root, conversation_id, backend)
	else:
		r = None
	return r
# @used-by :func:`check_pre_invocation._expected_turn_key()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_verif_pre_invocation_and_crash_ops()`
def dfh_expected_turn_key(backend: Path, conversation_id: str, start_step: int) -> str:
	identity = ['antigravity', str(backend.resolve()), conversation_id, f'ag-{conversation_id}-{start_step}']
	raw = (json.dumps(identity, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
	return hashlib.sha256(raw).hexdigest()[:40]
# @used-by :func:`check_pre_invocation._format_turn_begin_message()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__run_begin()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_verif_pre_invocation_and_crash_ops()`
def dfh_format_turn_begin_message(canon_root: Path, res: dict) -> dict:
	from Df.Harness.lib.hook_addon_ops import dfh_format_pre_invocation_companion_warning
	turn_key = str(res['turn_key'])
	scratch_ans = dfh_scratch_answer_path(canon_root, turn_key)
	title_info = res.get('conversation_title_sync') if isinstance(res.get('conversation_title_sync'), dict) else {}
	title_val = title_info.get('title')
	title_part = f', journal_title={title_val}' if title_val else ''
	sim_peers = [str(p) for p in (res.get('similar_project_repos') or res.get('similar_projects') or ()) if str(p).strip()]
	peers_csv = ','.join(sim_peers)
	peer_part = f', similar_peers={peers_csv}' if sim_peers else ''
	def_loc = dfh_default_user_locale()
	loc_part = f', user_default_locale={def_loc}' if def_loc else ''
	comp_part = dfh_format_pre_invocation_companion_warning()
	return {'injectSteps': [{'systemMessage': {'systemMessage': f'Harness PreInvocation: turn-begin initialized (turn_key={turn_key}{title_part}{peer_part}{loc_part}{comp_part}, scratch_answer={scratch_ans}).'}}]}
# @used-by :func:`check_pre_invocation._latest_completed_user_step()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__resolve_target()`
def dfh_latest_completed_user_step(conversations_dir: Path, conversation_id: str) -> int | None:
	conv_db = conversations_dir / f'{conversation_id}.db'
	r: int | None = None
	if conv_db.is_file():
		conn = sqlite3.connect(conv_db.resolve().as_uri() + '?mode=ro', uri=True)
		try:
			row = conn.execute('SELECT MAX(idx) FROM steps WHERE step_type=14 AND status IN (3,5)').fetchone()
			r = int(row[0]) if row and None is not row[0] else None
		except Exception:
			r = None
		finally:
			conn.close()
	return r
# @used-by :func:`check_pre_invocation._pre_flush_begin_context()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__run_begin()`
@contextmanager
def dfh_pre_flush_begin_context(brain_dir: Path, conversations_dir: Path, conversation_id: str):
	logs_dir = brain_dir / conversation_id / '.system_generated/logs'
	full_t, comp_t = (logs_dir / 'transcript_full.jsonl', logs_dir / 'transcript.jsonl')
	if full_t.is_file() or comp_t.is_file() or _has_planner_steps(conversations_dir, conversation_id):
		yield
	else:
		from Df.Harness.lib.trace_common import PRE_FLUSH_READER_HOOK, dfh_read_jsonl_objects
		prev_hook = PRE_FLUSH_READER_HOOK[0]
		allowed = {full_t.resolve(), comp_t.resolve()}
		# @used-by :func:`dfh_pre_flush_begin_context()`
		def _empty_if_unflushed(source, *, partial_error=None):
			if not isinstance(source, (bytes, bytearray)) and (not Path(source).is_file()) and Path(source).resolve() in allowed:
				r: list = []
			else:
				PRE_FLUSH_READER_HOOK[0] = prev_hook
				try:
					r = dfh_read_jsonl_objects(source, partial_error=partial_error)
				finally:
					PRE_FLUSH_READER_HOOK[0] = _empty_if_unflushed
			return r
		PRE_FLUSH_READER_HOOK[0] = _empty_if_unflushed
		try:
			yield
		finally:
			PRE_FLUSH_READER_HOOK[0] = prev_hook
# @used-by :func:`check_pre_invocation._resolve_root()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__resolve_invocation()`
def dfh_resolve_hook_root(payload: dict) -> Path | None:
	from Df.Harness.lib.trace_common import dfh_local_uri_to_path
	cwd_raw = str(payload.get('cwd') or '').strip()
	r: Path | None = None
	if cwd_raw:
		cand = dfh_local_uri_to_path(cwd_raw) if cwd_raw.lower().startswith('file://') else Path(cwd_raw)
		r = Path(cand).resolve()
	else:
		ws = payload.get('workspacePaths')
		if isinstance(ws, list) and 1 == len(ws) and isinstance(ws[0], str) and ws[0].strip():
			raw = ws[0].strip()
			cand = dfh_local_uri_to_path(raw) if raw.lower().startswith('file://') else Path(raw)
			r = Path(cand).resolve()
	return r
# @used-by :func:`check_pre_invocation._resolve_pre_invocation_target()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__resolve_target()`
def dfh_resolve_pre_invocation_target(canon_root: Path, backend: Path, conversation_id: str, max_user_step: int, brain_dir: Path, conversations_dir: Path, t_path: Path | None) -> Path | None:
	from Df.Harness.lib.turn_routing_ops import dfh_resolve_active_turn_state
	orig_st = dfh_resolve_active_turn_state(dfh_journal.dfh_turns_dir(canon_root, explicit_only=True), conversation_id, max_user_step)
	if isinstance(orig_st, dict) and 'handed_off' == orig_st.get('status'):
		r: Path | None = None
	else:
		routed = dfh_routed_pre_invocation_root(canon_root, conversation_id, max_user_step, brain_dir, conversations_dir, t_path)
		r = None if dfh_turn_step_already_covered(dfh_journal.dfh_turns_dir(routed, explicit_only=True), backend, conversation_id, max_user_step) else routed
	return r
# @used-by :func:`check_pre_invocation._routed_pre_invocation_root()`
# @used-by :func:`dfh_resolve_pre_invocation_target()`
def dfh_routed_pre_invocation_root(canon_root: Path, conversation_id: str, max_user_step: int, brain_dir: Path, conversations_dir: Path, t_path: Path | None) -> Path:
	from Df.Harness.lib.turn_routing_ops import dfh_resolve_handoff_target_root
	routed = dfh_resolve_handoff_target_root(dfh_journal.dfh_turns_dir(canon_root, explicit_only=True), conversation_id, max_user_step, brain_dir=brain_dir, conversations_dir=conversations_dir, t_path=t_path)
	return routed if None is not routed else canon_root
# @used-by :func:`check_pre_invocation._scratch_answer_path()`
# @used-by :func:`dfh_format_turn_begin_message()`
def dfh_scratch_answer_path(canon_root: Path, turn_key: str) -> str:
	try:
		r = (dfh_project_paths(canon_root, exact_root=True).scratch_dir / f'answer-{turn_key}.md').as_posix()
	except Exception:
		r = (canon_root / '\ua616/data/scratch' / f'answer-{turn_key}.md').as_posix()
	return r
# @used-by :func:`check_pre_invocation._summary_primary_status()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__resolve_target()`
def dfh_summary_primary_status(conversations_db: Path, conversation_id: str) -> str:
	r = 'unavailable'
	if conversations_db.is_file():
		conn = sqlite3.connect(conversations_db.resolve().as_uri() + '?mode=ro', uri=True)
		try:
			row = conn.execute('SELECT parent_conversation_id FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
			if None is not row:
				r = 'child' if bool(row[0]) else 'primary'
		except Exception:
			r = 'unavailable'
		finally:
			conn.close()
	return r
# @used-by :func:`check_pre_invocation._terminate_error()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__resolve_ag_context()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__run_begin()`
def dfh_terminate_error(message: str) -> dict:
	return {'injectSteps': [{'errorMessage': {'userMessage': f'Harness PreInvocation turn-begin blocked: {message}'}}], 'terminationBehavior': 'terminate'}
# @used-by :func:`check_pre_invocation._turn_step_already_covered()`
# @used-by :func:`dfh_resolve_pre_invocation_target()`
def dfh_turn_step_already_covered(t_dir: Path, backend: Path, conversation_id: str, max_user_step: int) -> bool:
	from Df.Harness.lib.turn_routing_ops import dfh_resolve_active_turn_state
	st = dfh_resolve_active_turn_state(t_dir, conversation_id, max_user_step)
	return isinstance(st, dict) and st.get('status') in ('open', 'prepared', 'delivered', 'conflict', 'handed_off')