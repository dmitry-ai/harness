# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from .formatting import _split_model_and_effort
import json
import sqlite3
# 2026-11-24
# "Decompose metadata.py into modular metadata collection package":
# https://github.com/dmitry-ai/harness/issues/170
_EMPTY_TRANSCRIPT_KEYS = ('request_timestamp', 'response_timestamp', 'model', 'effort', 'turn_index')
# 2026-11-25
# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
# https://github.com/dmitry-ai/harness/issues/239
_SKIP_STATE_SUFFIXES = ('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json', '-mechanical-exempt.json')
def _ag_transcript_file(ag_paths: dict[str, Any] | None, conversation_id: str) -> Path | None:
	if not isinstance(ag_paths, dict) or not ag_paths.get('brain_dir'):
		r: Path | None = None
	else:
		logs = Path(ag_paths['brain_dir']) / conversation_id / '.system_generated/logs'
		full_t = logs / 'transcript_full.jsonl'
		compact_t = logs / 'transcript.jsonl'
		r = full_t.resolve() if full_t.is_file() else (compact_t.resolve() if compact_t.is_file() else full_t.resolve())
	return r
def _apply_codex_context(obj: dict[str, Any], state: dict[str, Any], turn_id: str | None) -> None:
	if 'turn_context' == obj.get('type'):
		payload = obj.get('payload') if isinstance(obj.get('payload'), dict) else {}
		m_val = payload.get('model') if isinstance(payload.get('model'), str) else None
		e_val = payload.get('effort') if isinstance(payload.get('effort'), str) else None
		if m_val or e_val:
			state['last_ctx'] = (m_val, e_val)
			if turn_id and payload.get('turn_id') == turn_id:
				state['matched_ctx'] = (m_val, e_val)
def _apply_codex_event(idx: int, obj: dict[str, Any], info: dict[str, Any], turn_ids: list[str], turn_id: str | None, start_step: int | None, final_step: int | None) -> None:
	kind = obj.get('type')
	payload = obj.get('payload') if isinstance(obj.get('payload'), dict) else {}
	ts = obj.get('timestamp') if isinstance(obj.get('timestamp'), str) else None
	if 'event_msg' == kind and 'task_started' == payload.get('type'):
		_record_codex_task_started(payload, ts, info, turn_ids, turn_id)
	if None is not start_step and idx == start_step and ts and None is info['request_timestamp']:
		info['request_timestamp'] = ts
	if None is not final_step and idx == final_step and ts:
		info['response_timestamp'] = ts
	if 'event_msg' == kind and 'task_complete' == payload.get('type') and turn_id and payload.get('turn_id') == turn_id and ts:
		info['response_timestamp'] = ts
def _empty_transcript_info() -> dict[str, Any]:
	return dict.fromkeys(_EMPTY_TRANSCRIPT_KEYS, None)
def _extract_ag_transcript_info(transcript_path: str | Path | None, *, start_step: int | None=None, end_step: int | None=None, final_step: int | None=None) -> dict[str, Any]:
	info = _empty_transcript_info()
	tp = Path(transcript_path) if transcript_path else None
	if None is not tp and tp.is_file():
		state: dict[str, list[Any]] = {'all_models': [], 'slice_models': [], 'user_steps': []}
		for row in _read_ag_rows(tp):
			if isinstance(row, dict):
				_record_ag_row(row, info, state, start_step, end_step, final_step)
		_finalize_ag_info(info, state, start_step)
	return info
def _extract_codex_transcript_info(rollout_path: str | Path | None, *, turn_id: str | None=None, start_step: int | None=None, final_step: int | None=None) -> dict[str, Any]:
	info = _empty_transcript_info()
	rp = Path(rollout_path) if rollout_path else None
	if None is not rp and rp.is_file():
		turn_ids: list[str] = []
		ctx_state: dict[str, Any] = {'last_ctx': None, 'matched_ctx': None}
		for idx, obj in _iter_indexed_jsonl_dicts(rp):
			_apply_codex_event(idx, obj, info, turn_ids, turn_id, start_step, final_step)
			_apply_codex_context(obj, ctx_state, turn_id)
		if turn_id and turn_id in turn_ids:
			info['turn_index'] = turn_ids.index(turn_id) + 1
		elif turn_ids:
			info['turn_index'] = len(turn_ids)
		chosen = ctx_state['matched_ctx'] or ctx_state['last_ctx']
		if chosen:
			info['model'], info['effort'] = _split_model_and_effort(chosen[0], chosen[1])
	return info
def _extract_turn_steps_from_state(state: dict[str, Any]) -> list[int]:
	r: list[int] = []
	for slot in ('prepared', 'journal_record', 'delivery'):
		rec = state.get(slot)
		if isinstance(rec, dict) and isinstance(rec.get('journal_steps'), list):
			valid = [st for st in rec['journal_steps'] if int is type(st) and 1 <= st]
			if valid:
				r = sorted(set(valid))
				break
	if not r and isinstance(state.get('reserved_journal_steps'), list):
		r = sorted({st for st in state['reserved_journal_steps'] if int is type(st) and 1 <= st})
	return r
def _finalize_ag_info(info: dict[str, Any], state: dict[str, list[Any]], start_step: int | None) -> None:
	user_steps = state['user_steps']
	if None is not start_step and user_steps:
		uniq_steps = sorted(set(user_steps))
		if start_step in uniq_steps:
			info['turn_index'] = uniq_steps.index(start_step) + 1
	elif user_steps:
		info['turn_index'] = len(set(user_steps))
	chosen_model = state['slice_models'][-1] if state['slice_models'] else (state['all_models'][-1] if state['all_models'] else None)
	if chosen_model:
		info['model'], info['effort'] = _split_model_and_effort(chosen_model)
def _find_turn_state_for_conversation(turns_dir: Path, conversation_id: str) -> tuple[Path, dict[str, Any]] | None:
	r: tuple[Path, dict[str, Any]] | None = None
	if turns_dir.is_dir() and conversation_id:
		cid_low = conversation_id.strip().lower()
		raw_cands = (_turn_state_candidate(sf, cid_low) for sf in turns_dir.glob('*.json'))
		candidates = [cand for cand in raw_cands if None is not cand]
		if candidates:
			candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
			r = (candidates[0][2], candidates[0][3])
	return r
def _iter_indexed_jsonl_dicts(path: Path) -> list[tuple[int, dict[str, Any]]]:
	r: list[tuple[int, dict[str, Any]]] = []
	try:
		lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
	except OSError:
		lines = []
	for idx, ln in enumerate(lines):
		if ln.strip():
			try:
				obj = json.loads(ln)
			except ValueError:
				obj = None
			if isinstance(obj, dict):
				r.append((idx, obj))
	return r
def _parse_antigravity_source_metadata(env: dict[str, str]) -> tuple[str | None, int | None]:
	raw = str(env.get('ANTIGRAVITY_SOURCE_METADATA') or '').strip()
	try:
		parsed = json.loads(raw) if raw else None
	except ValueError:
		parsed = None
	tool_obj = parsed.get('tool') if isinstance(parsed, dict) and isinstance(parsed.get('tool'), dict) else {}
	cid = str(tool_obj.get('conversationId') or '').strip().lower() or None
	sidx = tool_obj.get('stepIndex')
	step_idx = sidx if int is type(sidx) and 0 <= sidx else None
	return (cid, step_idx)
def _read_ag_rows(tp: Path) -> list[Any]:
	try:
		from ..platforms.trace_common import read_jsonl_objects
		r: list[Any] = read_jsonl_objects(tp)
	except Exception:
		r = [obj for _, obj in _iter_indexed_jsonl_dicts(tp)]
	return r
def _read_ag_summary_row(ag_paths: dict[str, Any] | None, conversation_id: str) -> dict[str, Any] | None:
	r: dict[str, Any] | None = None
	db_p = Path(ag_paths['conversations_db']) if isinstance(ag_paths, dict) and ag_paths.get('conversations_db') else None
	if None is not db_p and db_p.is_file():
		try:
			from ..platforms.trace_common import open_readonly_sqlite
			with open_readonly_sqlite(db_p, row_factory=sqlite3.Row) as conn:
				row = conn.execute('SELECT * FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
				r = dict(row) if None is not row else None
		except (OSError, sqlite3.Error):
			r = None
	return r
def _record_ag_row(row: dict[str, Any], info: dict[str, Any], state: dict[str, list[Any]], start_step: int | None, end_step: int | None, final_step: int | None) -> None:
	sidx = row.get('step_index')
	rtype = row.get('type')
	created = row.get('created_at')
	if 'USER_INPUT' == rtype and isinstance(sidx, int):
		state['user_steps'].append(sidx)
		if None is not start_step and sidx == start_step and isinstance(created, str) and created.strip():
			info['request_timestamp'] = created.strip()
	if None is not final_step and sidx == final_step and isinstance(created, str) and created.strip():
		info['response_timestamp'] = created.strip()
	if 'PLANNER_RESPONSE' == rtype and isinstance(row.get('model'), str) and row['model'].strip():
		raw_m = row['model'].strip()
		state['all_models'].append(raw_m)
		if isinstance(sidx, int) and (None is start_step or sidx > start_step) and (None is end_step or sidx < end_step):
			state['slice_models'].append(raw_m)
def _record_codex_task_started(payload: dict[str, Any], ts: str | None, info: dict[str, Any], turn_ids: list[str], turn_id: str | None) -> None:
	tid = payload.get('turn_id')
	if isinstance(tid, str) and tid:
		if tid not in turn_ids:
			turn_ids.append(tid)
		if turn_id == tid and ts and None is info['request_timestamp']:
			info['request_timestamp'] = ts
def _resolve_ag_model_and_effort(ag_paths: dict[str, Any] | None, conversation_id: str, *, transcript_path: str | Path | None=None, start_step: int | None=None, end_step: int | None=None) -> tuple[str | None, str | None]:
	t_info = _extract_ag_transcript_info(transcript_path, start_step=start_step, end_step=end_step)
	model, effort = (t_info.get('model'), t_info.get('effort'))
	if (not model or not effort) and isinstance(ag_paths, dict) and ag_paths.get('backend_dir'):
		try:
			from ..platforms.antigravity import _model_metadata
			observed, _, _ = _model_metadata(Path(ag_paths['backend_dir']), conversation_id, paths=ag_paths)
			if None is model and observed.get('model'):
				model, parsed_eff = _split_model_and_effort(observed.get('model'), observed.get('effort'))
				effort = effort or parsed_eff
			elif None is effort and observed.get('effort'):
				effort = observed.get('effort')
		except Exception:
			pass
	return (model, effort)
def _turn_state_candidate(sf: Path, cid_low: str) -> tuple[int, int, Path, dict[str, Any]] | None:
	r: tuple[int, int, Path, dict[str, Any]] | None = None
	if not sf.name.endswith(_SKIP_STATE_SUFFIXES):
		try:
			data = json.loads(sf.read_text(encoding='utf-8'))
			mtime_ns = sf.stat().st_mtime_ns
		except (OSError, ValueError):
			data, mtime_ns = (None, 0)
		if isinstance(data, dict) and str(data.get('conversation_id') or '').strip().lower() == cid_low:
			r = (1 if 'open' == data.get('status') else 0, mtime_ns, sf.resolve(), data)
	return r
