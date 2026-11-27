# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Core.lib.sha256 import df_sha256_file, df_sha256_text
from Df.Harness.Journal.Publisher import Publisher
from Df.Harness.lib import journal as dfh_journal
from Df.Harness.lib.admission_ops import dfh_admission_binding, dfh_capture_admission
from Df.Harness.lib.journal_core import dfh_journal_pair_dirs, dfh_state_dir, dfh_step_file
from Df.Harness.lib.journal_reservations import dfh_release_turn_steps, dfh_reserve_turn_steps
from Df.Harness.lib.journal_upgrade import dfh_ensure_project_journal_upgraded
from Df.Harness.lib.path_discovery import dfh_default_platform_paths
from Df.Harness.lib.path_resolve import dfh_is_tracked_workspace
from Df.Harness.lib.runtime_instances import dfh_platform_instances
from Df.Harness.lib.runtime_resolve import dfh_resolve_antigravity_paths
from Df.Harness.lib.storage import dfh_replace_bytes
import hashlib
import json
import re
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
MAX_TOTAL_CONTINUATIONS = 3
_OPT_OUT_RE = re.compile(r'(?i)(?:\b(?:skip\s+journaling|do\s+not\s+journal|don\'t\s+journal|no\s+journal(?:ing)?|without\s+journaling|opt[\s-]+out\s+of\s+journaling)\b|\b(?:\u0431\u0435\u0437\s+\u0436\u0443\u0440\u043d\u0430\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u0438\w*|\u043d\u0435\s+\u0436\u0443\u0440\u043d\u0430\u043b\u0438\u0440\u0443\w*|\u043d\u0435\s+\u0437\u0430\u043f\u0438\u0441\u044b\u0432\u0430\w*\s+\u0432\s+\u0436\u0443\u0440\u043d\u0430\u043b|\u043e\u0442\u043c\u0435\u043d\u0438\w*\s+\u0436\u0443\u0440\u043d\u0430\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u0438\w*)\b)')
_TRANSCRIPT_UUID_RE = re.compile(r'(?:^|[/\\])brain[/\\]([a-f0-9-]{36})(?:[/\\]|$)', re.IGNORECASE)
_UUID_RE = re.compile(r'[a-f0-9-]{36}')
# @used-by :func:`_record_emergency_files()`
def _build_emergency_response(root: Path, native: dict[str, Any], turn: dict[str, Any], raw_text: str, reason: str, *, jdir: Path, steps: list[int], turn_key: str, state_path: Path, group_file: Path, conv_steps: list[int]) -> str:
	from agent_tools.metadata import build_journal_metadata, prepend_metadata_header
	meta = build_journal_metadata(root, native, turn, journal_dir=jdir, steps=steps, turn_key=turn_key, turn_state_path=state_path, group_file=group_file, conversation_steps=conv_steps)
	j_sec = meta.setdefault('Journal', {})
	j_sec['Provenance'] = 'stop_gate_emergency_capture'
	j_sec['Preparation Verified'] = False
	j_sec['FILE-3 Warning'] = reason
	return prepend_metadata_header(raw_text, meta)
# @used-by :func:`dfh_resolve_ag_hook_paths()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_stop_gate_continuation_guard_and_emergency_capture()`
def _fallback_ag_hook_paths(t_path: Path | None, backend_override: Path | None, *, swallow_errors: bool) -> tuple[Path, Path, Path, Path, Path]:
	if None is not backend_override:
		backend = Path(backend_override).resolve()
		r = (backend, backend / 'brain', backend / 'conversation_summaries.db', backend / 'conversations', backend.parent / 'config/projects')
	elif None is not t_path:
		if 5 <= len(t_path.parents) and 'brain' == t_path.parents[3].name:
			backend, brain_dir = (t_path.parents[4].resolve(), t_path.parents[3].resolve())
		elif 4 <= len(t_path.parents):
			backend = t_path.parents[3].resolve()
			brain_dir = backend / 'brain'
		else:
			backend = t_path.parent.resolve()
			brain_dir = backend / 'brain'
		r = (backend, brain_dir, backend / 'conversation_summaries.db', backend / 'conversations', backend.parent / 'config/projects')
	else:
		r = _fallback_default_ag_paths(swallow_errors)
	return r
# @used-by :func:`_fallback_ag_hook_paths()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_stop_gate_continuation_guard_and_emergency_capture()`
def _fallback_default_ag_paths(swallow_errors: bool) -> tuple[Path, Path, Path, Path, Path]:
	try:
		defaults = dfh_default_platform_paths('antigravity')
		backend = Path(defaults['backend_dir']).resolve()
		projects_dir = Path(defaults['projects_dir']).resolve() if defaults.get('projects_dir') else (backend.parent / 'config/projects')
	except Exception:
		if not swallow_errors:
			raise
		backend = (Path.home() / '.gemini/antigravity').resolve()
		projects_dir = backend.parent / 'config/projects'
	return (backend, backend / 'brain', backend / 'conversation_summaries.db', backend / 'conversations', projects_dir)
# @used-by :func:`_resolve_ag_from_settings()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_stop_gate_continuation_guard_and_emergency_capture()`
def _match_ag_instance_by_transcript(t_res: Path, ag_insts: dict, conversation_id: str, cfg: dict) -> dict | None:
	r: dict | None = None
	for inst in ag_insts.values():
		sp = inst['system_paths']
		for key in ('brain_dir', 'backend_dir'):
			val = sp.get(key)
			if val and t_res.is_relative_to(Path(val).resolve()):
				r = dfh_resolve_antigravity_paths(backend=sp.get('backend_dir'), instance=inst['id'], conversation_id=conversation_id, config=cfg)
				break
		if None is not r:
			break
	return r
# @used-by :func:`dfh_record_emergency_locked()`
def _persist_emergency_state(path: Path, value: dict[str, Any], recorded: dict[str, Any], *, reason: str, jdir: Path, request_ids: list[str]) -> dict[str, Any]:
	from Df.Harness.lib.completion_core import dfh_persist
	value['prepared'] = None
	value['journal_record'] = recorded
	value['completion_provenance'] = 'stop_gate_emergency_capture'
	value['preparation_verified'] = False
	value['recovered_after_delivery'] = True
	value['emergency_capture'] = {'captured_at': recorded['recorded_at'], 'journal_steps': list(recorded['journal_steps']), 'reason': reason}
	value.pop('reserved_journal_steps', None)
	dfh_persist(path, value)
	dfh_release_turn_steps(jdir, value['key'], request_ids=request_ids)
	return {'captured': True, 'journal_steps': list(recorded['journal_steps']), 'turn_key': value['key']}
# @used-by :func:`dfh_record_emergency_locked()`
def _record_emergency_files(root: Path, native: dict[str, Any], turn: dict[str, Any], raw_text: str, reason: str, *, jdir: Path, turn_key: str, state_path: Path) -> tuple[dict[str, Any], list[str]] | None:
	from Df.Harness.lib.completion_core import dfh_conversation_journal_steps, dfh_now, dfh_read_meta
	from Df.Harness.lib.completion_record import dfh_group
	from agent_tools.metadata import strip_leading_metadata_header
	r = None
	token, request_ids = dfh_group(root, native, turn, raw_text, jdir)
	group_file = dfh_state_dir(jdir) / 'answer-groups' / (token + '.json')
	if not (group_file.exists() and 'complete' == dfh_read_meta(group_file).get('status')):
		steps_res = dfh_reserve_turn_steps(jdir, turn_key, native['conversation_id'], request_ids)
		eff_resp = _build_emergency_response(root, native, turn, raw_text, reason, jdir=jdir, steps=steps_res, turn_key=turn_key, state_path=state_path, group_file=group_file, conv_steps=dfh_conversation_journal_steps(root, jdir, native['conversation_id']))
		eff_reqs = [req['text'] for req in turn['requests']]
		cap = dfh_capture_admission([root, jdir], eff_reqs, eff_resp, dfh_admission_binding(jdir, eff_reqs, eff_resp, token, request_ids))
		steps = Publisher(jdir, eff_reqs, eff_resp, token, request_ids, admission=cap, reserved_turn_key=turn_key).run()
		_, res_dir = dfh_journal_pair_dirs(jdir)
		rec = {'admission': cap.reference, 'body_sha256': df_sha256_text(strip_leading_metadata_header(raw_text)), 'group_file': str(group_file), 'group_sha256': df_sha256_file(group_file), 'journal_steps': steps, 'recorded_at': dfh_now(), 'response_file': str(dfh_step_file(res_dir, steps[0], directory=jdir)), 'response_sha256': df_sha256_text(eff_resp), 'reused_complete_journal_group': False}
		r = (rec, request_ids)
	return r
# @used-by :func:`dfh_resolve_ag_hook_paths()`
def _resolve_ag_from_settings(conversation_id: str, t_path: Path | None, backend_override: Path | None, *, settings_fn=None) -> dict | None:
	from Df.Harness.Runtime.SettingsLoader import SettingsLoader
	load_cfg = settings_fn if None is not settings_fn else (lambda: SettingsLoader().run())
	resolved = None
	if None is not backend_override:
		resolved = dfh_resolve_antigravity_paths(backend=backend_override, conversation_id=conversation_id, settings_fn=load_cfg)
	elif None is not t_path:
		cfg = load_cfg()
		ag_insts = dfh_platform_instances('antigravity', config=cfg, include_disabled=True) if 'antigravity' in (cfg.get('platforms') or {}) else {}
		resolved = _match_ag_instance_by_transcript(t_path.resolve(), ag_insts, conversation_id, cfg)
	if None is resolved and None is t_path:
		resolved = dfh_resolve_antigravity_paths(conversation_id=conversation_id, settings_fn=load_cfg)
	return resolved
# @used-by :meth:`Df.Harness.Hook.ContinuationGuard.ContinuationGuard.run()`
# @used-by :mod:`agent_tools.stop_hook_guard`
def dfh_evaluate_continuation_reentry(gfile: Path, fp: str, last_user_step: int, last_step: int | None, prev: dict[str, Any], decision: dict, payload: dict, *, session_id: str='', matched_state: dict | None=None, emergency_ctx: dict[str, Any] | None=None) -> dict:
	from Df.Harness.Hook.EmergencyCapturer import EmergencyCapturer
	exec_raw = payload.get('executionNum')
	exec_num = exec_raw if isinstance(exec_raw, int) and (not isinstance(exec_raw, bool)) else 0
	prev_fp, prev_total = (str(prev.get('fingerprint') or ''), int(prev.get('total_count') or 0))
	if (prev_fp and prev_fp == fp) or MAX_TOTAL_CONTINUATIONS <= prev_total or MAX_TOTAL_CONTINUATIONS <= exec_num:
		EmergencyCapturer(gfile.parents[1], session_id, last_user_step, matched_state, decision, emergency_ctx).run()
		r = {'decision': 'allow'}
	else:
		dfh_save_guard(gfile, {'fingerprint': fp, 'last_step': last_step, 'last_user_step': last_user_step, 'total_count': prev_total + 1, 'unchanged_count': 1})
		r = decision
	return r
# @used-by :func:`check_stop_gate._evaluate_prepared_match()`
# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__evaluate_matched_state()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_stop_gate_continuation_guard_and_emergency_capture()`
def dfh_evaluate_prepared_match(matched_state: dict, last_planner_text: str) -> dict:
	r = {'decision': 'allow'}
	prep = matched_state.get('prepared')
	if last_planner_text and isinstance(prep, dict):
		sha = hashlib.sha256(last_planner_text.encode('utf-8')).hexdigest()
		if sha != prep.get('response_sha256') and sha != prep.get('body_sha256'):
			res_file = Path(prep.get('response_file') or '')
			prep_text = res_file.read_text(encoding='utf-8', errors='replace') if res_file.is_file() else ''
			try:
				from agent_tools.metadata import strip_leading_metadata_header
				prep_body = strip_leading_metadata_header(prep_text)
			except Exception:
				prep_body = prep_text
			if not prep_text or (dfh_journal.dfh_strip_local_file_scheme(prep_text) != dfh_journal.dfh_strip_local_file_scheme(last_planner_text) and dfh_journal.dfh_strip_local_file_scheme(prep_body) != dfh_journal.dfh_strip_local_file_scheme(last_planner_text)):
				r = {'decision': 'continue', 'reason': 'FILE-3 Stop Gate: Final response text does not match the prepared response in \u227a/<range>/<N>.md (or legacy res/<N>.md). Read back the prepared response file and output its exact bytes without post-prepare edits.'}
	return r
# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__resolve_tracked_context()`
# @used-by :mod:`agent_tools.stop_hook_guard`
def dfh_extract_stop_context(payload: dict) -> tuple[str, str, str]:
	t_path_raw = str(payload.get('transcriptPath') or '').strip()
	cwd_raw = str(payload.get('cwd') or '').strip()
	if not cwd_raw:
		ws_paths = payload.get('workspacePaths')
		if isinstance(ws_paths, list) and 1 == len(ws_paths) and isinstance(ws_paths[0], str):
			cwd_raw = ws_paths[0].strip()
	cand_id = str(payload.get('conversationId') or payload.get('sessionId') or '').strip().lower()
	if not _UUID_RE.fullmatch(cand_id) and t_path_raw:
		m = _TRANSCRIPT_UUID_RE.search(t_path_raw)
		cand_id = m.group(1).lower() if m else ''
	session_id = cand_id if _UUID_RE.fullmatch(cand_id) else ''
	return (cwd_raw, session_id, t_path_raw)
# @used-by :meth:`Df.Harness.Hook.ContinuationGuard.ContinuationGuard.run()`
# @used-by :mod:`agent_tools.stop_hook_guard`
def dfh_failure_fingerprint(matched_state: dict | None, decision: dict, last_user_step: int) -> str:
	st = matched_state if isinstance(matched_state, dict) else {}
	rc = st.get('readiness_check') if isinstance(st.get('readiness_check'), dict) else {}
	parts = [str(decision.get('reason') or ''), str(st.get('status') or ''), str(rc.get('gate_id') or ''), str(rc.get('detail') or ''), str(rc.get('checked_at') or ''), str(last_user_step)]
	return hashlib.sha256('\x1f'.join(parts).encode('utf-8')).hexdigest()
# @used-by :meth:`Df.Harness.Hook.EmergencyCapturer.EmergencyCapturer.run()`
# @used-by :mod:`agent_tools.stop_emergency_capture`
def dfh_find_target_turn(native: dict[str, Any], last_user_step: int) -> dict[str, Any] | None:
	r = None
	owned = [item for item in reversed(native.get('turns') or ()) if item.get('owned')]
	for item in owned:
		if last_user_step == item.get('start_step') or any((last_user_step == req.get('native_step') for req in item.get('requests') or ())):
			r = item
			break
	if None is r and owned:
		r = owned[0]
	return r
# @used-by :func:`check_stop_gate._find_turn_state()`
# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__evaluate_handoff()`
# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__load_state_context()`
def dfh_find_turn_state(t_dir: Path, session_id: str, last_user_step: int, *, rows: list | None=None) -> dict | None:
	from Df.Harness.lib.turn_routing_ops import dfh_resolve_active_turn_state
	return dfh_resolve_active_turn_state(t_dir, session_id, last_user_step, rows=rows)
# @used-by :meth:`Df.Harness.Hook.ContinuationGuard.ContinuationGuard.run()`
# @used-by :mod:`agent_tools.stop_hook_guard`
def dfh_guard_file_path(t_dir: Path, session_id: str, last_user_step: int, matched_state: dict | None) -> Path:
	raw_key = str((matched_state or {}).get('key') or f'{session_id}-{last_user_step}')
	safe_key = re.sub(r'[^A-Za-z0-9_.-]+', '_', raw_key).strip('_') or 'stop'
	return t_dir / 'stop-guards' / f'{safe_key}.json'
# @used-by :func:`Df.Harness.lib.turn_routing_ops._handoff_rank()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_stop_gate_continuation_guard_and_emergency_capture()`
# @used-by :mod:`agent_tools.stop_hook_guard`
def dfh_handoff_matches_user_step(st: dict, rows: list[dict], last_user_step: int, *, user_text: str | None=None) -> bool:
	from Df.Harness.lib.request_binding import dfh_extract_leading_upwork_init_ids
	r = True
	target_job = str((st.get('handed_off_to') or {}).get('job_id') or '').strip()
	if target_job:
		matched_text = next((str(row.get('content') or '') for row in rows if isinstance(row, dict) and 'USER_INPUT' == row.get('type') and last_user_step == row.get('step_index')), user_text)
		if matched_text:
			new_ids = dfh_extract_leading_upwork_init_ids(matched_text)
			if new_ids and target_job not in new_ids:
				r = False
	return r
# @used-by :func:`check_stop_gate._is_child_conversation()`
# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__resolve_tracked_context()`
def dfh_is_child_conversation(backend: Path, conversation_id: str, *, conversations_db: Path | None=None) -> bool:
	db_path = Path(conversations_db) if None is not conversations_db else Path(backend) / 'conversation_summaries.db'
	r = False
	if db_path.is_file():
		conn = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)
		try:
			row = conn.execute('SELECT parent_conversation_id FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
			r = bool(row and row[0])
		except Exception:
			r = False
		finally:
			conn.close()
	return r
# @used-by :meth:`Df.Harness.Hook.ContinuationGuard.ContinuationGuard.run()`
# @used-by :mod:`agent_tools.stop_hook_guard`
def dfh_is_continuation_reentry(payload: dict, prev: dict[str, Any], last_user_step: int, last_step: int | None) -> bool:
	same_turn = bool(prev) and (prev.get('last_user_step') in (None, last_user_step))
	step_advanced = same_turn and isinstance(last_step, int) and isinstance(prev.get('last_step'), int) and (last_step > prev['last_step'])
	return bool(payload.get('continuationActive')) or step_advanced
# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__load_state_context()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_stop_gate_continuation_guard_and_emergency_capture()`
# @used-by :mod:`agent_tools.stop_hook_guard`
def dfh_is_journal_opt_out(payload: dict, rows: list[dict], last_user_step: int, matched_state: dict | None) -> bool:
	if isinstance(matched_state, dict) and False is matched_state.get('journal_required'):
		r = True
	else:
		texts = [str(payload.get('lastUserInput') or '')]
		for row in rows:
			if isinstance(row, dict) and 'USER_INPUT' == row.get('type') and last_user_step == row.get('step_index'):
				texts.append(str(row.get('content') or ''))
		r = any((bool(_OPT_OUT_RE.search(t)) for t in texts if t))
	return r
# @used-by :meth:`Df.Harness.Hook.ContinuationGuard.ContinuationGuard.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_stop_gate_continuation_guard_and_emergency_capture()`
# @used-by :mod:`agent_tools.stop_hook_guard`
def dfh_load_guard(path: Path) -> dict[str, Any]:
	r: dict[str, Any] = {}
	if path.is_file():
		try:
			data = json.loads(path.read_text(encoding='utf-8'))
			if isinstance(data, dict):
				r = data
		except (OSError, ValueError):
			r = {}
	return r
# @used-by :meth:`Df.Harness.Hook.ContinuationGuard.ContinuationGuard.run()`
# @used-by :mod:`agent_tools.stop_hook_guard`
def dfh_max_segment_step(segment: list[dict] | None, last_user_step: int) -> int | None:
	r = None
	if None is not segment:
		steps = [row['step_index'] for row in segment if isinstance(row, dict) and isinstance(row.get('step_index'), int)]
		r = max(steps) if steps else last_user_step
	return r
# @used-by :meth:`Df.Harness.Hook.EmergencyCapturer.EmergencyCapturer.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_hook_emergency_and_path_tail()`
# @used-by :mod:`agent_tools.stop_emergency_capture`
def dfh_record_emergency_locked(root: Path, native: dict[str, Any], turn: dict[str, Any], raw_text: str, reason: str) -> dict[str, Any] | None:
	from Df.Harness.lib.completion_core import dfh_journal_dir, dfh_recorded
	from Df.Harness.lib.completion_state import dfh_load_turn_state
	r = None
	path, value = dfh_load_turn_state(root, native, turn, recovered=True, allow_extended=True)
	if None is dfh_recorded(value) and 'handed_off' != value.get('status'):
		jdir = dfh_journal_dir(root, value['journal'])
		dfh_ensure_project_journal_upgraded(root, selected=jdir)
		written = _record_emergency_files(root, native, turn, raw_text, reason, jdir=jdir, turn_key=value['key'], state_path=path)
		if None is not written:
			r = _persist_emergency_state(path, value, written[0], reason=reason, jdir=jdir, request_ids=written[1])
	return r
# @used-by :func:`check_pre_invocation._resolve_ag_paths()`
# @used-by :func:`check_stop_gate._resolve_stop_paths()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__resolve_ag_context()`
# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__resolve_tracked_context()`
def dfh_resolve_ag_hook_paths(conversation_id: str, t_path: Path | None=None, backend_override: Path | None=None, *, swallow_errors: bool=False, settings_fn=None) -> tuple[Path, Path, Path, Path, Path]:
	resolved = None
	try:
		resolved = _resolve_ag_from_settings(conversation_id, t_path, backend_override, settings_fn=settings_fn)
	except Exception:
		if not swallow_errors:
			raise
		resolved = None
	if None is not resolved:
		r = (Path(resolved['backend_dir']).resolve(), Path(resolved['brain_dir']).resolve(), Path(resolved['conversations_db']).resolve(), Path(resolved['conversations_dir']).resolve(), Path(resolved['projects_dir']).resolve())
	else:
		r = _fallback_ag_hook_paths(t_path, backend_override, swallow_errors=swallow_errors)
	return r
# @used-by :func:`dfh_evaluate_continuation_reentry()`
# @used-by :meth:`Df.Harness.Hook.ContinuationGuard.ContinuationGuard.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_stop_gate_continuation_guard_and_emergency_capture()`
# @used-by :mod:`agent_tools.stop_hook_guard`
def dfh_save_guard(path: Path, data: dict[str, Any]) -> None:
	try:
		path.parent.mkdir(parents=True, exist_ok=True)
		dfh_replace_bytes(path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
	except OSError:
		pass
# @used-by :func:`check_pre_invocation._is_tracked_and_non_umbrella()`
# @used-by :func:`check_stop_gate._tracked_workspace()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__resolve_ag_context()`
# @used-by :meth:`Df.Harness.Hook.PreInvocationGate.PreInvocationGate.__resolve_target()`
# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__resolve_tracked_context()`
def dfh_tracked_workspace(root: Path, *, projects_dirs=None) -> tuple[bool, Path]:
	try:
		r = dfh_is_tracked_workspace(root, projects_dirs=projects_dirs)
	except Exception:
		tracked = (root / '\ua616/project.json').is_file() or (root / '_/\ua66e').is_dir() or (root / '\ua66e').is_dir()
		r = (tracked, root)
	return r
# @used-by :meth:`Df.Harness.Hook.ContinuationGuard.ContinuationGuard.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_stop_gate_continuation_guard_and_emergency_capture()`
# @used-by :mod:`agent_tools.stop_hook_guard`
def dfh_unlink_guard(path: Path) -> None:
	try:
		path.unlink(missing_ok=True)
	except OSError:
		pass