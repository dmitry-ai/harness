# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sqlite3
# 2026-11-25
# "Unify handed-off turn routing and deterministic state selection across hooks":
# https://github.com/dmitry-ai/harness/issues/231
_STATUS_RANK = {
	'conflict': 1,
	'delivered': 4,
	'handed_off': 2,
	'open': 1,
	'preparation_unverified': 0,
	'prepared': 3,
}
def _collect_turn_candidates(t_dir: Path, sid: str, last_user_step: int, rows: list[dict] | None, user_text: str | None) -> tuple[tuple | None, tuple | None, tuple | None]:
	from .hook_runtime import iter_turn_state_files
	best_exact, best_secondary, best_handoff = (None, None, None)
	check_handoff = None is not rows or None is not user_text
	for _, st in iter_turn_state_files(t_dir):
		if str(st.get('conversation_id') or '').strip().lower() != sid:
			continue
		tier = _match_tier(st, sid, last_user_step)
		if 3 == tier:
			best_exact = _pick_higher(best_exact, _state_rank(st, 3), st)
		elif 2 == tier:
			best_secondary = _pick_higher(best_secondary, _state_rank(st, 2), st)
		h_rank = _handoff_rank(st, rows, last_user_step, user_text) if check_handoff else None
		if None is not h_rank:
			best_handoff = _pick_higher(best_handoff, h_rank, st)
	return (best_exact, best_secondary, best_handoff)
def _extract_step_text_from_db(conversations_dir: Path, conversation_id: str, step_idx: int) -> str | None:
	r: str | None = None
	conv_db = conversations_dir / f'{conversation_id}.db'
	if conv_db.is_file():
		conn = sqlite3.connect(conv_db.resolve().as_uri() + '?mode=ro', uri=True)
		try:
			row = conn.execute('SELECT step_payload FROM steps WHERE idx=? AND step_type=14 LIMIT 1', (step_idx,)).fetchone()
			if row and row[0]:
				from .platforms.antigravity import _extract_step_text
				r = _extract_step_text(row[0])
		except Exception:
			r = None
		finally:
			conn.close()
	return r
def _extract_user_text(rows: list[dict] | None, last_user_step: int, conversations_dir: Path | None, conversation_id: str) -> str | None:
	r: str | None = None
	for row in rows or ():
		if isinstance(row, dict) and 'USER_INPUT' == row.get('type') and last_user_step == row.get('step_index'):
			r = str(row.get('content') or '')
			break
	if None is r and None is not conversations_dir:
		r = _extract_step_text_from_db(conversations_dir, conversation_id, last_user_step)
	return r
def _handoff_rank(st: dict, rows: list[dict] | None, last_user_step: int, user_text: str | None) -> tuple[int, str, str] | None:
	r: tuple[int, str, str] | None = None
	if 'handed_off' == st.get('status'):
		start_step = st.get('native_start_step')
		if isinstance(start_step, int) and start_step <= last_user_step:
			from .stop_hook_guard import handoff_matches_user_step
			if handoff_matches_user_step(st, rows or [], last_user_step, user_text=user_text):
				r = (start_step, str(st.get('updated_at') or ''), str(st.get('key') or ''))
	return r
def _match_tier(st: dict, session_id: str, last_user_step: int) -> int:
	req_steps = {req.get('native_step') for req in st.get('requests') or () if isinstance(req, dict)}
	if st.get('native_turn_id') == f'ag-{session_id}-{last_user_step}' or last_user_step == st.get('native_start_step'):
		r = 3
	elif last_user_step in req_steps:
		r = 2
	else:
		r = 0
	return r
def _pick_higher(current: tuple | None, cand_rank: tuple, st: dict) -> tuple:
	return (cand_rank, st) if None is current or cand_rank > current[0] else current
def _select_best_turn_candidate(best_exact: tuple | None, best_secondary: tuple | None, best_handoff: tuple | None) -> dict | None:
	if None is not best_handoff and (None is best_exact or best_exact[1].get('status') not in ('prepared', 'delivered')):
		r = best_handoff[1]
	elif None is not best_exact:
		r = best_exact[1]
	else:
		r = best_secondary[1] if None is not best_secondary else None
	return r
def _state_rank(st: dict, tier: int) -> tuple[int, int, str, str]:
	return (tier, _STATUS_RANK.get(str(st.get('status') or ''), -1), str(st.get('updated_at') or ''), str(st.get('key') or ''))
def read_optional_transcript_rows(brain_dir: Path, conversation_id: str, t_path: Path | None=None) -> list[dict]:
	from .hook_runtime import _read_jsonl_dicts
	logs_dir = t_path.parent if None is not t_path else (brain_dir / conversation_id / '.system_generated/logs')
	full_t = logs_dir / 'transcript_full.jsonl'
	compact_t = logs_dir / 'transcript.jsonl'
	eff = full_t if full_t.is_file() else (t_path if None is not t_path and t_path.is_file() else compact_t)
	return _read_jsonl_dicts(eff) if eff.is_file() else []
def resolve_active_turn_state(t_dir: Path, session_id: str, last_user_step: int, *, rows: list[dict] | None=None, user_text: str | None=None) -> dict | None:
	sid = str(session_id or '').strip().lower()
	best_exact, best_secondary, best_handoff = _collect_turn_candidates(t_dir, sid, last_user_step, rows, user_text)
	return _select_best_turn_candidate(best_exact, best_secondary, best_handoff)
def resolve_handoff_target_root(t_dir: Path, session_id: str, last_user_step: int, *, brain_dir: Path | None=None, conversations_dir: Path | None=None, t_path: Path | None=None, rows: list[dict] | None=None, user_text: str | None=None) -> Path | None:
	eff_rows = rows if None is not rows else (read_optional_transcript_rows(brain_dir, session_id, t_path=t_path) if None is not brain_dir else [])
	eff_text = user_text if None is not user_text else _extract_user_text(eff_rows, last_user_step, conversations_dir, session_id)
	matched = resolve_active_turn_state(t_dir, session_id, last_user_step, rows=eff_rows, user_text=eff_text)
	r: Path | None = None
	if isinstance(matched, dict) and 'handed_off' == matched.get('status'):
		info = matched.get('handed_off_to') if isinstance(matched.get('handed_off_to'), dict) else {}
		raw_root = str(info.get('project_root') or '').strip()
		if raw_root:
			cand = Path(raw_root).resolve()
			if cand.is_dir():
				r = cand
	return r
