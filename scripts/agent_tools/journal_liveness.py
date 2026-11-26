# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reconcile idle prepared turns and verify liveness for orphaned reservations":
# https://github.com/dmitry-ai/harness/issues/295
from __future__ import annotations
from typing import Any
import sqlite3
from .journal_sync_all import _resolve_ag_summary_db
from .platforms.trace_common import open_readonly_sqlite
from .runtime import platform_adapter_name
# @used-by :func:`classify_reservation_entry()`
# @used-by :mod:`agent_tools.journal_liveness`
def is_conversation_running_live(r_key: str, entry: dict[str, Any], by_key: dict[str, dict[str, Any]]) -> bool:
	st = by_key.get(r_key)
	cid = str(entry.get('conversation_id') or (st.get('conversation_id') if isinstance(st, dict) else '') or '').strip()
	r = False
	if isinstance(st, dict) and cid and 'open' == st.get('status'):
		rec = st.get('native_reconciliation')
		if not (isinstance(rec, dict) and False is rec.get('valid')) and 'antigravity' == platform_adapter_name(st.get('platform')):
			db_path = _resolve_ag_summary_db(st, cid)
			if None is not db_path and db_path.is_file():
				try:
					with open_readonly_sqlite(db_path) as conn:
						row = conn.execute('SELECT status, killed FROM conversation_summaries WHERE conversation_id=?', (cid,)).fetchone()
					r = None is not row and 'CASCADE_RUN_STATUS_RUNNING' == row[0] and (not row[1])
				except (OSError, sqlite3.Error):
					r = False
	return r
# @used-by :func:`agent_tools.journal_integrity._reservation_orphan_reason()`
# @used-by :func:`agent_tools.journal_integrity.classify_reservations()`
# @used-by :mod:`agent_tools.journal_liveness`
def classify_reservation_entry(r_key: str, entry: dict[str, Any], max_existing: int, committed_rids: set[str], by_key: dict[str, dict[str, Any]], max_start_by_cid: dict[str, int], *, require_empty: bool, turn_reason_fn) -> tuple[str | None, dict[str, Any] | None]:
	cid = str(entry.get('conversation_id') or '').strip().lower()
	e_steps = [s for s in (entry.get('steps') or ()) if int is type(s) and 1 <= s]
	e_reqs = [rid for rid in (entry.get('request_ids') or ()) if isinstance(rid, str) and rid]
	st = by_key.get(r_key)
	err, live = (None, None)
	if require_empty:
		err = f'dangling reservation {r_key} (steps={e_steps}) remains for finalized conversation'
	elif any((rid in committed_rids for rid in e_reqs)):
		err = f'orphaned reservation {r_key} references already-committed request_ids'
	elif isinstance(st, dict) and None is not turn_reason_fn(r_key, st, cid, max_start_by_cid):
		err = turn_reason_fn(r_key, st, cid, max_start_by_cid)
	elif any((s <= max_existing for s in e_steps)):
		if is_conversation_running_live(r_key, entry, by_key):
			live = {'turn_key': r_key, 'conversation_id': cid, 'steps': e_steps, 'classification': 'active_parallel_reservation'}
		else:
			err = f'orphaned reservation {r_key} holds steps {e_steps} <= committed max step {max_existing}'
	return (err, live)
__all__ = ['classify_reservation_entry', 'is_conversation_running_live']