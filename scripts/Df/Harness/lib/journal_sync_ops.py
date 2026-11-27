# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from Df.Harness.lib.journal_integrity_ops import dfh_prune_terminal_conflict_reservations, dfh_resolve_ag_summary_db
from Df.Harness.lib.journal_reservations import dfh_iter_turn_reservations
from Df.Harness.lib.runtime_instances import dfh_platform_adapter_name
from Df.Harness.lib.storage import dfh_replace_bytes
import json
import sqlite3
import time
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
DEFAULT_FOREIGN_MAX_ENTRIES = 5
DEFAULT_FOREIGN_TIME_BUDGET_S = 2.5
PENDING_INDEX_FILE = 'pending-sync.json'
# @used-by :func:`_is_native_idle_for_sync()`
def _antigravity_summary_is_idle(st: dict[str, Any], cid: str) -> bool:
	r = False
	db_path = dfh_resolve_ag_summary_db(st, cid)
	if None is not db_path and db_path.is_file():
		try:
			conn = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
			try:
				row = conn.execute('SELECT status, not_fully_idle, killed FROM conversation_summaries WHERE conversation_id=?', (cid,)).fetchone()
			finally:
				conn.close()
			r = None is not row and 'CASCADE_RUN_STATUS_IDLE' == row[0] and 0 == row[1] and (not row[2])
		except (OSError, sqlite3.Error):
			r = False
	return r
# @used-by :func:`dfh_run_all_open_sweep()`
def _collect_all_open_candidates(root: Path, jdir: Path, *, folder_fn: Any, read_fn: Any) -> list[tuple[str, dict[str, Any]]]:
	entries: dict[str, dict[str, Any]] = dict(dfh_iter_turn_reservations(jdir))
	for k, v in _iter_idle_prepared_candidates(root, folder_fn=folder_fn, read_fn=read_fn).items():
		entries.setdefault(k, v)
	turns_dir = folder_fn(root)
	if turns_dir.is_dir():
		for path in sorted(turns_dir.glob('*.json')):
			if '-' not in path.stem and path.stem not in entries:
				st = _load_turn_state_safe(path, read_fn)
				if isinstance(st, dict) and st.get('conversation_id') and st.get('status') in ('open', 'conflict'):
					entries[path.stem] = {'conversation_id': str(st['conversation_id'])}
	return sorted(entries.items())
# @used-by :func:`dfh_scan_prepared_dir()`
# @used-by :func:`dfh_update_index_for_turn()`
def _entry_from_state(path: Path, st: dict[str, Any]) -> dict[str, Any]:
	try:
		mtime = path.stat().st_mtime
	except OSError:
		mtime = 0.0
	return {'conversation_id': str(st['conversation_id']), 'mtime': mtime, 'updated_at': str(st.get('updated_at') or '')}
# @used-by :func:`_try_sync_foreign_entry()`
def _is_foreign_open_eligible(st: dict[str, Any], *, adopt_conflict: bool=False) -> tuple[bool, str]:
	recorded = any((isinstance(st.get(k), dict) and 'journal_steps' in st[k] for k in ('prepared', 'journal_record', 'delivery')))
	status = str(st.get('status') or '')
	if 'prepared' == status and None is st.get('delivery'):
		r = (True, '')
	elif recorded:
		r = (False, 'already_recorded')
	elif adopt_conflict and status in ('open', 'conflict'):
		r = (True, '')
	elif 'open' != status:
		st_lbl = status or 'unknown'
		r = (False, f'status_{st_lbl}')
	elif st.get('admission_failure') or False is (st.get('readiness_check') or {}).get('verified'):
		r = (False, 'failed_readiness_or_admission')
	else:
		r = (True, '')
	return r
# @used-by :func:`_try_sync_foreign_entry()`
def _is_native_idle_for_sync(st: dict[str, Any], cid: str) -> bool:
	kind = dfh_platform_adapter_name(st.get('platform'))
	return _antigravity_summary_is_idle(st, cid) if 'antigravity' == kind else ('codex' == kind)
# @used-by :func:`_collect_all_open_candidates()`
def _iter_idle_prepared_candidates(root: Path, *, folder_fn: Any, read_fn: Any) -> dict[str, dict[str, Any]]:
	out: dict[str, dict[str, Any]] = {}
	turns_dir = folder_fn(root)
	if turns_dir.is_dir():
		for path in sorted(turns_dir.glob('*.json')):
			if '-' not in path.stem:
				try:
					raw = path.read_bytes()
				except OSError:
					continue
				if b'"prepared"' in raw and b'"delivery": null' in raw:
					st = _load_turn_state_safe(path, read_fn)
					if dfh_is_pending_prepared(st):
						out[path.stem] = {'conversation_id': str(st['conversation_id'])}
	return out
# @used-by :func:`_collect_all_open_candidates()`
# @used-by :func:`_iter_idle_prepared_candidates()`
# @used-by :func:`_try_sync_foreign_entry()`
# @used-by :func:`dfh_scan_prepared_dir()`
def _load_turn_state_safe(path: Path, read_fn: Any) -> dict[str, Any] | None:
	r: dict[str, Any] | None = None
	if path.is_file():
		try:
			data = read_fn(path)
			if isinstance(data, dict):
				r = data
		except (OSError, ValueError):
			r = None
	return r
# @used-by :func:`dfh_candidate_recency()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_journal_tail()`
def _parse_iso_epoch(raw: Any) -> float:
	r = 0.0
	if isinstance(raw, str) and raw.strip():
		norm = raw.strip().replace(' ', 'T')
		norm = norm[:-1] + '+00:00' if norm.endswith('Z') else norm
		try:
			dt = datetime.fromisoformat(norm)
			r = (dt.replace(tzinfo=timezone.utc) if None is dt.tzinfo else dt).timestamp()
		except ValueError:
			r = 0.0
	return r
# @used-by :func:`dfh_reconcile_before_begin()`
def _reconcile_current_earlier(root: Path, native: dict[str, Any], turn: dict[str, Any], key: str, journal_directory: Any, *, folder_fn: Any, dir_fn: Any, read_fn: Any, sync_fn: Any, key_fn: Any) -> dict[str, Any] | None:
	earlier = any((t.get('owned') and t.get('completed') and (not t.get('aborted')) and (t.get('start_step', 0) <= turn['start_step']) and key_fn(native, t) != key for t in native.get('turns', [])))
	r: dict[str, Any] | None = None
	if earlier:
		sync_j = _resolve_current_sync_journal(root, key, journal_directory, folder_fn=folder_fn, dir_fn=dir_fn, read_fn=read_fn)
		try:
			r = sync_fn(root, native['conversation_id'], platform=native['platform'], backend=native['native_backend'], journal_directory=sync_j, _preloaded_native=native)
		except (OSError, ValueError, sqlite3.Error) as exc:
			r = {'error': str(exc), 'valid': False}
	return r
# @used-by :func:`_reconcile_current_earlier()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_journal_sync_and_upgrade()`
def _resolve_current_sync_journal(root: Path, key: str, journal_directory: Any, *, folder_fn: Any, dir_fn: Any, read_fn: Any) -> Any:
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
# @used-by :func:`dfh_reconcile_foreign_open_reservations()`
def _sync_foreign_batch(root: Path, ordered: list[tuple[str, dict[str, Any]]], cur_low: str, journal_directory: Any, *, folder_fn: Any, read_fn: Any, sync_fn: Any, max_entries: int, time_budget_s: float) -> tuple[list[dict[str, Any]], set[str]]:
	started = time.monotonic()
	synced: list[dict[str, Any]] = []
	seen_cids: set[str] = set()
	checked: set[str] = set()
	for turn_key, entry in ordered:
		if (0 < max_entries and max_entries <= len(synced)) or (0.0 < time_budget_s and time_budget_s <= time.monotonic() - started):
			break
		cid = str(entry.get('conversation_id') or '').strip()
		if cid and cid.lower() != cur_low and cid.lower() not in seen_cids:
			checked.add(turn_key)
			hit, _ = _try_sync_foreign_entry(root, turn_key, entry, journal_directory, folder_fn=folder_fn, read_fn=read_fn, sync_fn=sync_fn)
			if None is not hit:
				seen_cids.add(cid.lower())
				synced.append(hit)
	return (synced, checked)
# @used-by :func:`_sync_foreign_batch()`
# @used-by :func:`dfh_run_all_open_sweep()`
def _try_sync_foreign_entry(root: Path, turn_key: str, entry: dict[str, Any], journal_directory: Any, *, folder_fn: Any, read_fn: Any, sync_fn: Any, adopt_conflict: bool=False, from_step: int=0) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
	cid = str(entry.get('conversation_id') or '').strip()
	st = _load_turn_state_safe(folder_fn(root) / f'{turn_key}.json', read_fn) if cid else None
	if None is st:
		r: tuple[dict[str, Any] | None, dict[str, Any] | None] = (None, {'conversation_id': cid, 'reason': 'missing_or_unreadable_state', 'turn_key': turn_key})
	else:
		ok_elig, why = _is_foreign_open_eligible(st, adopt_conflict=adopt_conflict)
		if not ok_elig:
			r = (None, {'conversation_id': cid, 'reason': why, 'turn_key': turn_key})
		elif not _is_native_idle_for_sync(st, cid):
			r = (None, {'conversation_id': cid, 'reason': 'conversation_not_idle', 'turn_key': turn_key})
		else:
			try:
				res = sync_fn(root, cid, platform=st.get('platform'), backend=st.get('native_backend'), from_step=from_step, journal_directory=st.get('journal') or journal_directory, adopt_conflict=adopt_conflict)
				r = ({'conversation_id': cid, 'result': res, 'turn_key': turn_key}, None)
			except (OSError, ValueError, sqlite3.Error) as exc:
				r = (None, {'conversation_id': cid, 'error': str(exc), 'reason': 'sync_error', 'turn_key': turn_key})
	return r
# @used-by :func:`dfh_order_candidates_by_recency()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_journal_tail()`
# @used-by :mod:`agent_tools.journal_pending_index`
def dfh_candidate_recency(turns_dir: Path, turn_key: str, entry: dict[str, Any]) -> float:
	ts = _parse_iso_epoch(entry.get('updated_at'))
	if 0.0 < ts:
		r = ts
	elif isinstance(entry.get('mtime'), (int, float)) and 0.0 < float(entry['mtime']):
		r = float(entry['mtime'])
	else:
		fp = turns_dir / f'{turn_key}.json'
		try:
			r = fp.stat().st_mtime if fp.is_file() else 0.0
		except OSError:
			r = 0.0
	return r
# @used-by :func:`_iter_idle_prepared_candidates()`
# @used-by :func:`dfh_prune_resolved_from_index()`
# @used-by :func:`dfh_scan_prepared_dir()`
# @used-by :func:`dfh_update_index_for_turn()`
# @used-by :mod:`agent_tools.journal_pending_index`
def dfh_is_pending_prepared(st: Any) -> bool:
	return isinstance(st, dict) and 'prepared' == st.get('status') and None is st.get('delivery') and bool(st.get('conversation_id'))
# @used-by :func:`dfh_reconcile_foreign_open_reservations()`
# @used-by :mod:`agent_tools.journal_pending_index`
def dfh_order_candidates_by_recency(turns_dir: Path, candidates: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
	return sorted(candidates.items(), key=lambda item: (-dfh_candidate_recency(turns_dir, item[0], item[1]), item[0]))
# @used-by :func:`Df.Harness.lib.completion_core.dfh_persist()`
# @used-by :meth:`test_bounded_foreign_sync.BoundedForeignSyncTests.test_pending_sync_index_does_not_create_unbootstrapped_file_on_persist()`
# @used-by :mod:`agent_tools.journal_pending_index`
# @used-by :mod:`agent_tools.journal_sync_all`
def dfh_persist_turn_state(path: Path, raw: bytes, value: dict[str, Any]) -> None:
	dfh_replace_bytes(path, raw)
	if isinstance(value, dict) and '-' not in path.stem and PENDING_INDEX_FILE != path.name:
		try:
			dfh_update_index_for_turn(path, value)
		except (OSError, ValueError):
			pass
# @used-by :func:`dfh_reconcile_foreign_open_reservations()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_journal_sync_and_upgrade()`
# @used-by :mod:`agent_tools.journal_pending_index`
def dfh_prune_resolved_from_index(turns_dir: Path, pending_entries: dict[str, dict[str, Any]], checked_keys: set[str], *, read_fn: Any, had_entries: bool) -> None:
	for tk in checked_keys:
		if tk in pending_entries:
			fp = turns_dir / f'{tk}.json'
			try:
				st = read_fn(fp) if fp.is_file() else None
			except (OSError, ValueError):
				st = None
			if not dfh_is_pending_prepared(st):
				pending_entries.pop(tk, None)
	dfh_write_index_doc(turns_dir, pending_entries, bootstrapped=True, create_if_empty=had_entries)
# @used-by :func:`dfh_rebuild_pending_index()`
# @used-by :func:`dfh_update_index_for_turn()`
# @used-by :meth:`Df.Harness.Journal.PendingIndex.PendingIndex.run()`
def dfh_read_index_doc(turns_dir: Path) -> dict[str, Any] | None:
	idx_path = turns_dir / PENDING_INDEX_FILE
	r: dict[str, Any] | None = None
	if idx_path.is_file():
		try:
			data = json.loads(idx_path.read_text(encoding='utf-8'))
			if isinstance(data, dict) and isinstance(data.get('entries'), dict):
				r = data
		except (OSError, ValueError):
			r = None
	return r
# @used-by :meth:`Df.Harness.Journal.OpenTurnSyncer.OpenTurnSyncer.run()`
# @used-by :mod:`agent_tools.journal_pending_index`
def dfh_rebuild_pending_index(root: Path, *, folder_fn: Any, read_fn: Any) -> dict[str, dict[str, Any]]:
	turns_dir = folder_fn(root)
	had_doc = None is not dfh_read_index_doc(turns_dir)
	entries = dfh_scan_prepared_dir(turns_dir, read_fn=read_fn)
	dfh_write_index_doc(turns_dir, entries, bootstrapped=True, create_if_empty=had_doc)
	return entries
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :mod:`agent_tools.journal_sync_all`
def dfh_reconcile_before_begin(root: Path, native: dict[str, Any], turn: dict[str, Any], key: str, journal_directory: Any, *, folder_fn: Any, dir_fn: Any, read_fn: Any, sync_fn: Any, key_fn: Any) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
	cur_rec = _reconcile_current_earlier(root, native, turn, key, journal_directory, folder_fn=folder_fn, dir_fn=dir_fn, read_fn=read_fn, sync_fn=sync_fn, key_fn=key_fn)
	foreign = dfh_reconcile_foreign_open_reservations(root, native['conversation_id'], journal_directory=journal_directory, folder_fn=folder_fn, dir_fn=dir_fn, read_fn=read_fn, sync_fn=sync_fn)
	return (cur_rec, foreign)
# @used-by :func:`dfh_reconcile_before_begin()`
# @used-by :meth:`test_bounded_foreign_sync.BoundedForeignSyncTests.test_reconcile_foreign_does_not_create_index_when_only_own_turn_prepared()`
# @used-by :meth:`test_bounded_foreign_sync.BoundedForeignSyncTests.test_reconcile_foreign_enforces_batch_cap_recency_order_and_index()`
# @used-by :meth:`test_bounded_foreign_sync.BoundedForeignSyncTests.test_reconcile_foreign_stops_on_time_budget_while_all_open_sweeps_all()`
# @used-by :mod:`agent_tools.journal_sync_all`
def dfh_reconcile_foreign_open_reservations(root: Path, current_cid: str | None, *, journal_directory: Any=None, folder_fn: Any, dir_fn: Any, read_fn: Any, sync_fn: Any, max_entries: int=DEFAULT_FOREIGN_MAX_ENTRIES, time_budget_s: float=DEFAULT_FOREIGN_TIME_BUDGET_S) -> list[dict[str, Any]]:
	from Df.Harness.Journal.PendingIndex import PendingIndex
	jdir = dir_fn(root, journal_directory)
	dfh_prune_terminal_conflict_reservations(root, jdir, folder_fn=folder_fn, read_fn=read_fn)
	turns_dir = folder_fn(root)
	prepared, had_index = PendingIndex(turns_dir, read_fn=read_fn).run()
	candidates = dict(dfh_iter_turn_reservations(jdir))
	for k, v in prepared.items():
		candidates.setdefault(k, v)
	ordered = dfh_order_candidates_by_recency(turns_dir, candidates)
	synced, checked = _sync_foreign_batch(root, ordered, str(current_cid or '').strip().lower(), journal_directory, folder_fn=folder_fn, read_fn=read_fn, sync_fn=sync_fn, max_entries=max_entries, time_budget_s=time_budget_s)
	if had_index or checked:
		dfh_prune_resolved_from_index(turns_dir, prepared, checked, read_fn=read_fn, had_entries=True)
	return synced
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__complete_turn_delivery()`
# @used-by :mod:`agent_tools.journal_sync_all`
def dfh_resolve_sync_provenance(value: dict[str, Any], *, adopt_conflict: bool) -> str:
	if value.get('prepared') and (not adopt_conflict):
		r = 'prepared'
	elif 'stop_gate_emergency_capture' == value.get('completion_provenance') and (not adopt_conflict):
		r = 'stop_gate_emergency_capture'
	elif value.get('recovered_after_delivery'):
		r = 'recovered_native'
	else:
		r = 'existing_journal'
	return r
# @used-by :meth:`Df.Harness.Journal.OpenTurnSyncer.OpenTurnSyncer.run()`
def dfh_run_all_open_sweep(root_p: Path, jdir: Path, journal_directory: Any, *, adopt_conflict: bool, from_step: int, folder_fn: Any, read_fn: Any, sync_fn: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
	return (synced, skipped)
# @used-by :func:`dfh_rebuild_pending_index()`
# @used-by :meth:`Df.Harness.Journal.PendingIndex.PendingIndex.run()`
def dfh_scan_prepared_dir(turns_dir: Path, *, read_fn: Any) -> dict[str, dict[str, Any]]:
	out: dict[str, dict[str, Any]] = {}
	if turns_dir.is_dir():
		for path in sorted(turns_dir.glob('*.json')):
			if '-' not in path.stem:
				try:
					raw = path.read_bytes()
				except OSError:
					continue
				if b'"prepared"' in raw and b'"delivery": null' in raw:
					st = _load_turn_state_safe(path, read_fn)
					if dfh_is_pending_prepared(st):
						out[path.stem] = _entry_from_state(path, st)
	return out
# @used-by :func:`dfh_persist_turn_state()`
# @used-by :mod:`agent_tools.journal_pending_index`
def dfh_update_index_for_turn(path: Path, value: dict[str, Any]) -> None:
	turns_dir = path.parent
	doc = dfh_read_index_doc(turns_dir)
	if None is not doc and bool(doc.get('bootstrapped')):
		entries = {str(k): dict(v) for k, v in (doc.get('entries') or {}).items() if isinstance(v, dict)}
		if dfh_is_pending_prepared(value):
			entries[path.stem] = _entry_from_state(path, value)
			dfh_write_index_doc(turns_dir, entries, bootstrapped=True, create_if_empty=True)
		elif path.stem in entries:
			entries.pop(path.stem, None)
			dfh_write_index_doc(turns_dir, entries, bootstrapped=True, create_if_empty=True)
# @used-by :func:`dfh_prune_resolved_from_index()`
# @used-by :func:`dfh_rebuild_pending_index()`
# @used-by :func:`dfh_update_index_for_turn()`
def dfh_write_index_doc(turns_dir: Path, entries: dict[str, dict[str, Any]], *, bootstrapped: bool, create_if_empty: bool=False) -> None:
	idx_path = turns_dir / PENDING_INDEX_FILE
	if entries or create_if_empty or idx_path.is_file():
		raw = json.dumps({'bootstrapped': bool(bootstrapped), 'entries': entries, 'version': 1}, ensure_ascii=False, indent='\t', sort_keys=True).encode('utf-8') + b'\n'
		same = False
		if idx_path.is_file():
			try:
				same = raw == idx_path.read_bytes()
			except OSError:
				same = False
		if not same:
			dfh_replace_bytes(idx_path, raw)
