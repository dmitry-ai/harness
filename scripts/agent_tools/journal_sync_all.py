# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Exempt service finalization calls from EXEC-2-TDD-GATE and add journal-sync --all-open":
# https://github.com/dmitry-ai/harness/issues/256
# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Persist emergency journal capture on Stop Gate fail-open and sync idle foreign reservations in turn-begin":
# https://github.com/dmitry-ai/harness/issues/255
from __future__ import annotations
from pathlib import Path
from typing import Any
import sqlite3
from . import journal
from .path_registry import canonicalize_root_dir
from .platforms.trace_common import open_readonly_sqlite
from .runtime import platform_adapter_name, resolve_antigravity_paths
def _antigravity_summary_is_idle(st: dict[str, Any], cid: str) -> bool:
	r = False
	db_path = _resolve_ag_summary_db(st, cid)
	if None is not db_path and db_path.is_file():
		try:
			with open_readonly_sqlite(db_path) as conn:
				row = conn.execute('SELECT status, not_fully_idle, killed FROM conversation_summaries WHERE conversation_id=?', (cid,)).fetchone()
			r = None is not row and 'CASCADE_RUN_STATUS_IDLE' == row[0] and 0 == row[1] and (not row[2])
		except (OSError, sqlite3.Error):
			r = False
	return r
def _collect_all_open_candidates(root: Path, jdir: Path, *, folder_fn, read_fn) -> list[tuple[str, dict[str, Any]]]:
	entries: dict[str, dict[str, Any]] = dict(journal.iter_turn_reservations(jdir))
	turns_dir = folder_fn(root)
	if turns_dir.is_dir():
		for path in sorted(turns_dir.glob('*.json')):
			if '-' not in path.stem and path.stem not in entries:
				st = _load_turn_state_safe(path, read_fn)
				if isinstance(st, dict) and st.get('conversation_id') and st.get('status') in ('open', 'conflict'):
					entries[path.stem] = {'conversation_id': str(st['conversation_id'])}
	return sorted(entries.items())
def _is_foreign_open_eligible(st: dict[str, Any], *, adopt_conflict: bool=False) -> tuple[bool, str]:
	recorded = any((isinstance(st.get(k), dict) and 'journal_steps' in st[k] for k in ('prepared', 'journal_record', 'delivery')))
	status = str(st.get('status') or '')
	if recorded:
		r = (False, 'already_recorded')
	elif adopt_conflict and status in ('open', 'conflict'):
		r = (True, '')
	elif 'open' != status:
		r = (False, f'status_{status or "unknown"}')
	elif st.get('admission_failure') or False is (st.get('readiness_check') or {}).get('verified'):
		r = (False, 'failed_readiness_or_admission')
	else:
		r = (True, '')
	return r
def _is_native_idle_for_sync(st: dict[str, Any], cid: str) -> bool:
	adapter_kind = platform_adapter_name(st.get('platform'))
	if 'antigravity' == adapter_kind:
		r = _antigravity_summary_is_idle(st, cid)
	else:
		r = 'codex' == adapter_kind
	return r
def _reconcile_current_earlier(root: Path, native: dict[str, Any], turn: dict[str, Any], key: str, journal_directory: Any, *, folder_fn, dir_fn, read_fn, sync_fn, key_fn) -> dict[str, Any] | None:
	earlier = any((t.get('owned') and t.get('completed') and (not t.get('aborted')) and (t.get('start_step', 0) <= turn['start_step']) and key_fn(native, t) != key for t in native.get('turns', [])))
	r: dict[str, Any] | None = None
	if earlier:
		sync_j = _resolve_current_sync_journal(root, key, journal_directory, folder_fn=folder_fn, dir_fn=dir_fn, read_fn=read_fn)
		try:
			r = sync_fn(root, native['conversation_id'], platform=native['platform'], backend=native['native_backend'], journal_directory=sync_j, _preloaded_native=native)
		except (OSError, ValueError, sqlite3.Error) as exc:
			r = {'valid': False, 'error': str(exc)}
	return r
def _resolve_ag_summary_db(st: dict[str, Any], cid: str) -> Path | None:
	backend_raw = str(st.get('native_backend') or '').strip()
	r: Path | None = None
	if backend_raw:
		cand = Path(backend_raw) / 'conversation_summaries.db'
		r = cand if cand.is_file() else None
	if None is r:
		try:
			paths = resolve_antigravity_paths(backend=backend_raw or None, conversation_id=cid)
			cand2 = Path(paths['conversations_db'])
			r = cand2 if cand2.is_file() else None
		except (OSError, ValueError, KeyError):
			r = None
	return r
def _resolve_current_sync_journal(root: Path, key: str, journal_directory: Any, *, folder_fn, dir_fn, read_fn) -> Any:
	existing_path = folder_fn(root) / (key + '.json')
	sync_j = journal_directory
	if existing_path.is_file():
		try:
			saved_j = read_fn(existing_path).get('journal')
			if saved_j:
				if None is not journal_directory and dir_fn(root, saved_j) != dir_fn(root, journal_directory):
					raise ValueError('The native turn already has a different journal; preserve its original binding')
				sync_j = saved_j
		except (OSError, ValueError) as exc:
			if 'already has a different journal' in str(exc):
				raise
	return sync_j
def _load_turn_state_safe(path: Path, read_fn) -> dict[str, Any] | None:
	r: dict[str, Any] | None = None
	if path.is_file():
		try:
			data = read_fn(path)
			if isinstance(data, dict):
				r = data
		except (OSError, ValueError):
			r = None
	return r
def _try_sync_foreign_entry(root: Path, turn_key: str, entry: dict[str, Any], journal_directory: Any, *, folder_fn, read_fn, sync_fn, adopt_conflict: bool=False, from_step: int=0) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
	cid = str(entry.get('conversation_id') or '').strip()
	st = _load_turn_state_safe(folder_fn(root) / f'{turn_key}.json', read_fn) if cid else None
	if None is st:
		r = (None, {'turn_key': turn_key, 'conversation_id': cid, 'reason': 'missing_or_unreadable_state'})
	else:
		ok_elig, why = _is_foreign_open_eligible(st, adopt_conflict=adopt_conflict)
		if not ok_elig:
			r = (None, {'turn_key': turn_key, 'conversation_id': cid, 'reason': why})
		elif not _is_native_idle_for_sync(st, cid):
			r = (None, {'turn_key': turn_key, 'conversation_id': cid, 'reason': 'conversation_not_idle'})
		else:
			try:
				res = sync_fn(root, cid, platform=st.get('platform'), backend=st.get('native_backend'), from_step=from_step, journal_directory=st.get('journal') or journal_directory, adopt_conflict=adopt_conflict)
				r = ({'turn_key': turn_key, 'conversation_id': cid, 'result': res}, None)
			except (OSError, ValueError, sqlite3.Error) as exc:
				r = (None, {'turn_key': turn_key, 'conversation_id': cid, 'reason': 'sync_error', 'error': str(exc)})
	return r
def reconcile_before_begin(root: Path, native: dict[str, Any], turn: dict[str, Any], key: str, journal_directory: Any, *, folder_fn, dir_fn, read_fn, sync_fn, key_fn) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
	cur_rec = _reconcile_current_earlier(root, native, turn, key, journal_directory, folder_fn=folder_fn, dir_fn=dir_fn, read_fn=read_fn, sync_fn=sync_fn, key_fn=key_fn)
	foreign = reconcile_foreign_open_reservations(root, native['conversation_id'], journal_directory=journal_directory, folder_fn=folder_fn, dir_fn=dir_fn, read_fn=read_fn, sync_fn=sync_fn)
	return (cur_rec, foreign)
def reconcile_foreign_open_reservations(root: Path, current_cid: str | None, *, journal_directory: Any=None, folder_fn, dir_fn, read_fn, sync_fn) -> list[dict[str, Any]]:
	jdir = dir_fn(root, journal_directory)
	cur_low = str(current_cid or '').strip().lower()
	synced: list[dict[str, Any]] = []
	seen_cids: set[str] = set()
	for turn_key, entry in sorted(journal.iter_turn_reservations(jdir).items()):
		cid = str(entry.get('conversation_id') or '').strip()
		if cid and cid.lower() != cur_low and cid.lower() not in seen_cids:
			hit, _ = _try_sync_foreign_entry(root, turn_key, entry, journal_directory, folder_fn=folder_fn, read_fn=read_fn, sync_fn=sync_fn)
			if None is not hit:
				seen_cids.add(cid.lower())
				synced.append(hit)
	return synced
def resolve_sync_provenance(value: dict[str, Any], *, adopt_conflict: bool) -> str:
	if value.get('prepared') and (not adopt_conflict):
		r = 'prepared'
	elif 'stop_gate_emergency_capture' == value.get('completion_provenance') and (not adopt_conflict):
		r = 'stop_gate_emergency_capture'
	elif value.get('recovered_after_delivery'):
		r = 'recovered_native'
	else:
		r = 'existing_journal'
	return r
def sync_all_open(root: Path, *, journal_directory: Any=None, adopt_conflict: bool=False, from_step: int=0, folder_fn, dir_fn, read_fn, sync_fn) -> dict[str, Any]:
	root_p = canonicalize_root_dir(root)
	jdir = dir_fn(root_p, journal_directory)
	synced: list[dict[str, Any]] = []
	skipped: list[dict[str, Any]] = []
	seen_cids: set[str] = set()
	for turn_key, entry in _collect_all_open_candidates(root_p, jdir, folder_fn=folder_fn, read_fn=read_fn):
		cid_low = str(entry.get('conversation_id') or '').strip().lower()
		if cid_low and cid_low in seen_cids:
			continue
		hit, miss = _try_sync_foreign_entry(root_p, turn_key, entry, journal_directory, folder_fn=folder_fn, read_fn=read_fn, sync_fn=sync_fn, adopt_conflict=adopt_conflict, from_step=from_step)
		if None is not hit:
			seen_cids.add(cid_low)
			synced.append(hit)
		elif None is not miss:
			skipped.append(miss)
	valid = all((bool((item.get('result') or {}).get('valid')) for item in synced))
	return {'valid': valid, 'all_open': True, 'adopt_conflict': bool(adopt_conflict), 'journal': str(jdir), 'synced_count': len(synced), 'skipped_count': len(skipped), 'synced': synced, 'skipped': skipped}
__all__ = ['reconcile_before_begin', 'reconcile_foreign_open_reservations', 'resolve_sync_provenance', 'sync_all_open']
