# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sqlite3
import time
from .trace_common import open_readonly_sqlite, read_jsonl_objects
# 2026-11-24
# "Clarify verbatim target_claim contract and add native-review-proof wait timeout":
# https://github.com/dmitry-ai/harness/issues/212
MAX_REVIEW_WAIT_SECONDS = 300.0
_TERMINAL_SUMMARY_STATES = frozenset({'CASCADE_RUN_STATUS_IDLE', 'IDLE', 'COMPLETED', 'FAILED', 'ERROR', 'CANCELED', 'CANCELLED', 'KILLED'})
class RetryableReviewProofError(ValueError):
	def __init__(self, message: str) -> None:
		super().__init__(message)
		self.retryable = True
# 2026-11-24
# "Verify reused reviewer package assignments and tolerate volatile executor metadata":
# https://github.com/dmitry-ai/harness/issues/222
def _is_incoming_assignment_row(idx: int, row: dict, parent_id: str | None) -> bool:
	rtype = row.get('type')
	content = str(row.get('content') or '')
	if 0 == idx and rtype in ('USER_INPUT', 'SYSTEM_MESSAGE', None):
		r = True
	elif 'USER_INPUT' == rtype:
		r = True
	elif 'SYSTEM_MESSAGE' == rtype:
		r = (not parent_id) or (f'sender={parent_id}' in content)
	else:
		r = False
	return r
# 2026-11-24
# "Clarify verbatim target_claim contract and add native-review-proof wait timeout":
# https://github.com/dmitry-ai/harness/issues/212
def _is_reviewer_in_flight(conversations_db: Path, reviewer_id: str) -> bool:
	r = False
	if conversations_db.is_file():
		try:
			with open_readonly_sqlite(conversations_db) as conn:
				cols = {row[1] for row in conn.execute('PRAGMA table_info(conversation_summaries)')}
				sel_st = 'status' if 'status' in cols else "''"
				sel_nfi = 'not_fully_idle' if 'not_fully_idle' in cols else '0'
				row = conn.execute(f'SELECT {sel_st},{sel_nfi} FROM conversation_summaries WHERE conversation_id=?', (reviewer_id,)).fetchone()
				if row:
					st = str(row[0] or '').strip().upper()
					r = (0 != int(row[1] or 0)) or (bool(st) and st not in _TERMINAL_SUMMARY_STATES)
		except sqlite3.Error:
			r = False
	return r
# 2026-11-24
# "Clarify verbatim target_claim contract and add native-review-proof wait timeout":
# https://github.com/dmitry-ai/harness/issues/212
def _probe_reviewer_final(paths: dict, backend: Path, reviewer_id: str, *, transcript_path_fn, db_path_fn, completed_statuses) -> tuple[tuple | None, str, bool]:
	log = transcript_path_fn(paths['brain_dir'], reviewer_id)
	raw = log.read_bytes()
	rows = read_jsonl_objects(raw)
	last = rows[-1] if rows else {}
	if 'PLANNER_RESPONSE' != last.get('type') or last.get('tool_calls') or (not str(last.get('content') or '').strip()):
		r = (None, 'Reviewer has no successful final response in the native trace', True)
	else:
		with open_readonly_sqlite(db_path_fn(backend, reviewer_id, paths=paths)) as conn:
			final = conn.execute('SELECT idx,step_type,status FROM steps ORDER BY idx DESC LIMIT 1').fetchone()
		if not final or final[0] != last['step_index'] or 15 != final[1] or (final[2] not in completed_statuses):
			r = (None, 'Native database reports an unfinished/failed later reviewer step', True)
		else:
			r = ((log, raw, rows, last), '', False)
	return r
# 2026-11-24
# "Use canonical native inputs and strip USER_REQUEST in native_review_proof":
# https://github.com/dmitry-ai/harness/issues/210
def resolve_parent_binding_inputs(backend, parent_id, parent_inputs, *, paths, native_inputs_fn, extract_transcript_fn):
	try:
		loaded = native_inputs_fn(backend, parent_id, paths=paths, include_meta=True)
	except (OSError, sqlite3.Error, ValueError):
		loaded = None
	if loaded:
		r = loaded
	else:
		r = [(item.get('step_index', idx), extract_transcript_fn(item)) for idx, item in enumerate(parent_inputs) if 'USER_INPUT' == item.get('type') and isinstance(item.get('content'), str)]
	return r
# 2026-11-24
# "Verify reused reviewer package assignments and tolerate volatile executor metadata":
# https://github.com/dmitry-ai/harness/issues/222
def reviewer_assigned_package(native_log: str | Path, package: str, *, parent_id: str | None=None, final_step: int | None=None) -> bool:
	rows = read_jsonl_objects(Path(native_log))
	r = False
	for idx, row in enumerate(rows):
		if not isinstance(row, dict):
			continue
		step_idx = row.get('step_index')
		if None is not final_step and isinstance(step_idx, int) and step_idx >= final_step:
			continue
		if _is_incoming_assignment_row(idx, row, parent_id) and package in str(row.get('content') or ''):
			r = True
			break
	return r
# 2026-11-24
# "Clarify verbatim target_claim contract and add native-review-proof wait timeout":
# https://github.com/dmitry-ai/harness/issues/212
def wait_for_reviewer_final_step(paths: dict, backend: Path, reviewer_id: str, *, wait_timeout: float=0.0, poll_interval: float=0.2, transcript_path_fn, db_path_fn, completed_statuses):
	budget = min(max(0.0, float(wait_timeout or 0.0)), MAX_REVIEW_WAIT_SECONDS)
	deadline = time.monotonic() + budget
	conv_db = Path(paths['conversations_db'])
	while True:
		result, err_msg, maybe_pending = _probe_reviewer_final(paths, backend, reviewer_id, transcript_path_fn=transcript_path_fn, db_path_fn=db_path_fn, completed_statuses=completed_statuses)
		if None is not result:
			return result
		in_flight = maybe_pending and _is_reviewer_in_flight(conv_db, reviewer_id)
		rem = deadline - time.monotonic()
		if (not in_flight and 0.0 >= rem) or 0.0 >= rem:
			if in_flight:
				raise RetryableReviewProofError(f'{err_msg} (reviewer still streaming; retry or pass --wait-timeout <S>)')
			raise ValueError(err_msg)
		time.sleep(min(max(0.05, float(poll_interval)), rem))
