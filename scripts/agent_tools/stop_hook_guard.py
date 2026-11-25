# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify handed-off turn routing and deterministic state selection across hooks":
# https://github.com/dmitry-ai/harness/issues/231
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Preserve multi-turn handed-off Stop Gate routing and stateful loop guard":
# https://github.com/dmitry-ai/harness/issues/224
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Align check_stop_gate with Antigravity 2.0 conversationId contract and continuation loop guard":
# https://github.com/dmitry-ai/harness/issues/197
from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib
import json
import re
from .storage import replace_bytes
MAX_TOTAL_CONTINUATIONS = 3
_OPT_OUT_RE = re.compile(r'(?i)(?:\b(?:skip\s+journaling|do\s+not\s+journal|don\'t\s+journal|no\s+journal(?:ing)?|without\s+journaling|opt[\s-]+out\s+of\s+journaling)\b|\b(?:\u0431\u0435\u0437\s+\u0436\u0443\u0440\u043d\u0430\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u0438\w*|\u043d\u0435\s+\u0436\u0443\u0440\u043d\u0430\u043b\u0438\u0440\u0443\w*|\u043d\u0435\s+\u0437\u0430\u043f\u0438\u0441\u044b\u0432\u0430\w*\s+\u0432\s+\u0436\u0443\u0440\u043d\u0430\u043b|\u043e\u0442\u043c\u0435\u043d\u0438\w*\s+\u0436\u0443\u0440\u043d\u0430\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u0438\w*)\b)')
_TRANSCRIPT_UUID_RE = re.compile(r'(?:^|[/\\])brain[/\\]([a-f0-9-]{36})(?:[/\\]|$)', re.IGNORECASE)
_UUID_RE = re.compile(r'[a-f0-9-]{36}')
def _evaluate_continuation_reentry(gfile: Path, fp: str, last_user_step: int, last_step: int | None, prev: dict[str, Any], decision: dict, payload: dict) -> dict:
	exec_raw = payload.get('executionNum')
	exec_num = exec_raw if isinstance(exec_raw, int) and (not isinstance(exec_raw, bool)) else 0
	prev_fp, prev_total = (str(prev.get('fingerprint') or ''), int(prev.get('total_count') or 0))
	if (prev_fp and prev_fp == fp) or MAX_TOTAL_CONTINUATIONS <= prev_total or MAX_TOTAL_CONTINUATIONS <= exec_num:
		r = {'decision': 'allow'}
	else:
		_save_guard(gfile, {'fingerprint': fp, 'last_user_step': last_user_step, 'last_step': last_step, 'unchanged_count': 1, 'total_count': prev_total + 1})
		r = decision
	return r
def _failure_fingerprint(matched_state: dict | None, decision: dict, last_user_step: int) -> str:
	st = matched_state if isinstance(matched_state, dict) else {}
	rc = st.get('readiness_check') if isinstance(st.get('readiness_check'), dict) else {}
	parts = [
		str(decision.get('reason') or ''),
		str(st.get('status') or ''),
		str(rc.get('gate_id') or ''),
		str(rc.get('detail') or ''),
		str(rc.get('checked_at') or ''),
		str(last_user_step),
	]
	return hashlib.sha256('\x1f'.join(parts).encode('utf-8')).hexdigest()
def _guard_file_path(t_dir: Path, session_id: str, last_user_step: int, matched_state: dict | None) -> Path:
	raw_key = str((matched_state or {}).get('key') or f'{session_id}-{last_user_step}')
	safe_key = re.sub(r'[^A-Za-z0-9_.-]+', '_', raw_key).strip('_') or 'stop'
	return t_dir / 'stop-guards' / f'{safe_key}.json'
def _is_continuation_reentry(payload: dict, prev: dict[str, Any], last_user_step: int, last_step: int | None) -> bool:
	same_turn = bool(prev) and (prev.get('last_user_step') in (None, last_user_step))
	step_advanced = same_turn and isinstance(last_step, int) and isinstance(prev.get('last_step'), int) and (last_step > prev['last_step'])
	return bool(payload.get('continuationActive')) or step_advanced
def _load_guard(path: Path) -> dict[str, Any]:
	r: dict[str, Any] = {}
	if path.is_file():
		try:
			data = json.loads(path.read_text(encoding='utf-8'))
			if isinstance(data, dict):
				r = data
		except (OSError, ValueError):
			r = {}
	return r
def _max_segment_step(segment: list[dict] | None, last_user_step: int) -> int | None:
	r = None
	if None is not segment:
		steps = [row['step_index'] for row in segment if isinstance(row, dict) and isinstance(row.get('step_index'), int)]
		r = max(steps) if steps else last_user_step
	return r
def _save_guard(path: Path, data: dict[str, Any]) -> None:
	try:
		path.parent.mkdir(parents=True, exist_ok=True)
		replace_bytes(path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
	except OSError:
		pass
def _unlink_guard(path: Path) -> None:
	try:
		path.unlink(missing_ok=True)
	except OSError:
		pass
def apply_continuation_guard(t_dir: Path, session_id: str, last_user_step: int, matched_state: dict | None, decision: dict, payload: dict, *, segment: list[dict] | None=None) -> dict:
	gfile = _guard_file_path(t_dir, session_id, last_user_step, matched_state)
	if 'continue' != decision.get('decision'):
		_unlink_guard(gfile)
		r = decision
	else:
		prev = _load_guard(gfile)
		fp = _failure_fingerprint(matched_state, decision, last_user_step)
		last_step = _max_segment_step(segment, last_user_step)
		if not _is_continuation_reentry(payload, prev, last_user_step, last_step):
			_save_guard(gfile, {'fingerprint': fp, 'last_user_step': last_user_step, 'last_step': last_step, 'unchanged_count': 1, 'total_count': 1})
			r = decision
		else:
			r = _evaluate_continuation_reentry(gfile, fp, last_user_step, last_step, prev, decision, payload)
	return r
def extract_stop_context(payload: dict) -> tuple[str, str, str]:
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
def handoff_matches_user_step(st: dict, rows: list[dict], last_user_step: int, *, user_text: str | None=None) -> bool:
	from .platforms.request_binding import _extract_leading_upwork_init_ids
	r = True
	target_job = str((st.get('handed_off_to') or {}).get('job_id') or '').strip()
	if target_job:
		matched_text = next((str(row.get('content') or '') for row in rows if isinstance(row, dict) and 'USER_INPUT' == row.get('type') and last_user_step == row.get('step_index')), user_text)
		if matched_text:
			new_ids = _extract_leading_upwork_init_ids(matched_text)
			if new_ids and target_job not in new_ids:
				r = False
	return r
def is_journal_opt_out(payload: dict, rows: list[dict], last_user_step: int, matched_state: dict | None) -> bool:
	if isinstance(matched_state, dict) and False is matched_state.get('journal_required'):
		r = True
	else:
		texts = [str(payload.get('lastUserInput') or '')]
		for row in rows:
			if isinstance(row, dict) and 'USER_INPUT' == row.get('type') and last_user_step == row.get('step_index'):
				texts.append(str(row.get('content') or ''))
		r = any((bool(_OPT_OUT_RE.search(t)) for t in texts if t))
	return r