# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Bound synchronous foreign turn reconciliation with pending-sync index":
# https://github.com/dmitry-ai/harness/issues/341
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
from .storage import replace_bytes
PENDING_INDEX_FILE = 'pending-sync.json'
# @used-by :func:`_scan_prepared_dir()`
# @used-by :func:`update_index_for_turn()`
def _entry_from_state(path: Path, st: dict[str, Any]) -> dict[str, Any]:
	try:
		mtime = path.stat().st_mtime
	except OSError:
		mtime = 0.0
	return {'conversation_id': str(st['conversation_id']), 'updated_at': str(st.get('updated_at') or ''), 'mtime': mtime}
# @used-by :func:`candidate_recency()`
def _parse_iso_epoch(raw: Any) -> float:
	r = 0.0
	if isinstance(raw, str) and raw.strip():
		norm = raw.strip().replace(' ', 'T')
		norm = norm[:-1] + '+00:00' if norm.endswith('Z') else norm
		try:
			dt = datetime.fromisoformat(norm)
			if None is dt.tzinfo:
				dt = dt.replace(tzinfo=timezone.utc)
			r = dt.timestamp()
		except ValueError:
			r = 0.0
	return r
# @used-by :func:`collect_pending_prepared()`
# @used-by :func:`rebuild_pending_index()`
# @used-by :func:`update_index_for_turn()`
def _read_index_doc(turns_dir: Path) -> dict[str, Any] | None:
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
# @used-by :func:`collect_pending_prepared()`
# @used-by :func:`rebuild_pending_index()`
def _scan_prepared_dir(turns_dir: Path, *, read_fn) -> dict[str, dict[str, Any]]:
	out: dict[str, dict[str, Any]] = {}
	if turns_dir.is_dir():
		for path in sorted(turns_dir.glob('*.json')):
			if '-' in path.stem:
				continue
			try:
				raw = path.read_bytes()
			except OSError:
				continue
			if b'"prepared"' in raw and b'"delivery": null' in raw:
				try:
					st = read_fn(path)
				except (OSError, ValueError):
					st = None
				if is_pending_prepared(st):
					out[path.stem] = _entry_from_state(path, st)
	return out
# @used-by :func:`prune_resolved_from_index()`
# @used-by :func:`rebuild_pending_index()`
# @used-by :func:`update_index_for_turn()`
def _write_index_doc(turns_dir: Path, entries: dict[str, dict[str, Any]], *, bootstrapped: bool, create_if_empty: bool=False) -> None:
	idx_path = turns_dir / PENDING_INDEX_FILE
	if entries or create_if_empty or idx_path.is_file():
		payload = {'version': 1, 'bootstrapped': bool(bootstrapped), 'entries': entries}
		raw = json.dumps(payload, ensure_ascii=False, indent='\t', sort_keys=True).encode('utf-8') + b'\n'
		same = False
		if idx_path.is_file():
			try:
				same = raw == idx_path.read_bytes()
			except OSError:
				same = False
		if not same:
			replace_bytes(idx_path, raw)
# @used-by :func:`order_candidates_by_recency()`
# @used-by :mod:`agent_tools.journal_pending_index`
def candidate_recency(turns_dir: Path, turn_key: str, entry: dict[str, Any]) -> float:
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
# @used-by :func:`agent_tools.journal_sync_all.reconcile_foreign_open_reservations()`
# @used-by :mod:`agent_tools.journal_pending_index`
def collect_pending_prepared(root: Path, *, folder_fn, read_fn) -> tuple[dict[str, dict[str, Any]], bool]:
	turns_dir = folder_fn(root)
	doc = _read_index_doc(turns_dir)
	if None is not doc and bool(doc.get('bootstrapped')):
		entries = {str(k): dict(v) for k, v in doc['entries'].items() if isinstance(v, dict) and v.get('conversation_id')}
		r = (entries, True)
	else:
		scanned = _scan_prepared_dir(turns_dir, read_fn=read_fn)
		r = (scanned, None is not doc)
	return r
# @used-by :func:`_scan_prepared_dir()`
# @used-by :func:`prune_resolved_from_index()`
# @used-by :func:`update_index_for_turn()`
# @used-by :mod:`agent_tools.journal_pending_index`
def is_pending_prepared(st: Any) -> bool:
	return isinstance(st, dict) and 'prepared' == st.get('status') and None is st.get('delivery') and bool(st.get('conversation_id'))
# @used-by :func:`agent_tools.journal_sync_all.reconcile_foreign_open_reservations()`
# @used-by :mod:`agent_tools.journal_pending_index`
def order_candidates_by_recency(turns_dir: Path, candidates: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
	return sorted(candidates.items(), key=lambda item: (-candidate_recency(turns_dir, item[0], item[1]), item[0]))
# @used-by :func:`agent_tools.completion._persist()`
# @used-by :meth:`test_bounded_foreign_sync.BoundedForeignSyncTests.test_pending_sync_index_does_not_create_unbootstrapped_file_on_persist()`
# @used-by :mod:`agent_tools.journal_pending_index`
# @used-by :mod:`agent_tools.journal_sync_all`
def persist_turn_state(path: Path, raw: bytes, value: dict[str, Any]) -> None:
	replace_bytes(path, raw)
	if isinstance(value, dict) and '-' not in path.stem and PENDING_INDEX_FILE != path.name:
		try:
			update_index_for_turn(path, value)
		except (OSError, ValueError):
			pass
# @used-by :func:`agent_tools.journal_sync_all.reconcile_foreign_open_reservations()`
# @used-by :mod:`agent_tools.journal_pending_index`
def prune_resolved_from_index(turns_dir: Path, pending_entries: dict[str, dict[str, Any]], checked_keys: set[str], *, read_fn, had_entries: bool) -> None:
	for tk in checked_keys:
		if tk in pending_entries:
			fp = turns_dir / f'{tk}.json'
			try:
				st = read_fn(fp) if fp.is_file() else None
			except (OSError, ValueError):
				st = None
			if not is_pending_prepared(st):
				pending_entries.pop(tk, None)
	_write_index_doc(turns_dir, pending_entries, bootstrapped=True, create_if_empty=had_entries)
# @used-by :func:`agent_tools.journal_sync_all.sync_all_open()`
# @used-by :mod:`agent_tools.journal_pending_index`
def rebuild_pending_index(root: Path, *, folder_fn, read_fn) -> dict[str, dict[str, Any]]:
	turns_dir = folder_fn(root)
	had_doc = None is not _read_index_doc(turns_dir)
	entries = _scan_prepared_dir(turns_dir, read_fn=read_fn)
	_write_index_doc(turns_dir, entries, bootstrapped=True, create_if_empty=had_doc)
	return entries
# @used-by :func:`persist_turn_state()`
# @used-by :mod:`agent_tools.journal_pending_index`
def update_index_for_turn(path: Path, value: dict[str, Any]) -> None:
	turns_dir = path.parent
	doc = _read_index_doc(turns_dir)
	if None is not doc and bool(doc.get('bootstrapped')):
		entries = {str(k): dict(v) for k, v in (doc.get('entries') or {}).items() if isinstance(v, dict)}
		if is_pending_prepared(value):
			entries[path.stem] = _entry_from_state(path, value)
			_write_index_doc(turns_dir, entries, bootstrapped=True, create_if_empty=True)
		elif path.stem in entries:
			entries.pop(path.stem, None)
			_write_index_doc(turns_dir, entries, bootstrapped=True, create_if_empty=True)
__all__ = ['PENDING_INDEX_FILE', 'candidate_recency', 'collect_pending_prepared', 'is_pending_prepared', 'order_candidates_by_recency', 'persist_turn_state', 'prune_resolved_from_index', 'rebuild_pending_index', 'update_index_for_turn']
