# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.storage import dfh_replace_bytes
import hashlib
import json
import re
import threading
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
MEM_CACHE: dict[tuple[str, int, int], list[dict]] = {}
MEM_LOCK = threading.RLock()
_PREFIX_BYTES = 4096
_ROW_KEYS = ('content', 'step_index', 'tool_calls', 'type')
_SAFE_CID_RE = re.compile(r'[^A-Za-z0-9_.-]+')
_TAIL_BYTES = 256
_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
# @used-by :func:`dfh_resolve_index_path()`
def _conversation_id_for(t_path: Path) -> str:
	r = ''
	for part in reversed(t_path.parts[:-1]):
		if _UUID_RE.fullmatch(part):
			r = part
			break
	if not r and 3 <= len(t_path.parents) and 'logs' == t_path.parent.name and '.system_generated' == t_path.parents[1].name:
		r = _SAFE_CID_RE.sub('-', t_path.parents[2].name).strip('-.')[:48]
	if not r:
		r = hashlib.sha256(str(t_path).casefold().encode('utf-8')).hexdigest()[:16]
	return r
# @used-by :func:`dfh_resolve_index_path()`
def _find_turns_dir(cwd: Path | None) -> Path | None:
	r: Path | None = None
	if None is not cwd:
		cur = Path(cwd).resolve()
		for anc in (cur, *cur.parents):
			v2_data = anc / '\ua616' / 'data'
			v1_data = anc / '_' / '\ua616' / 'data'
			if v2_data.is_dir():
				r = v2_data / 'turns'
				break
			if v1_data.is_dir():
				r = v1_data / 'turns'
				break
	return r
# @used-by :func:`dfh_read_from_disk()`
def _read_full_file(fh, source: str, total_bytes: int, idx_path: Path | None) -> tuple[list[dict], int]:
	fh.seek(0)
	raw = fh.read()
	parsed = dfh_parse_jsonl_bytes(raw)
	if None is parsed:
		r: list[dict] = []
	else:
		r = parsed
		_save_disk_index(idx_path, fh, source, total_bytes, r)
	return (r, len(raw))
# @used-by :func:`dfh_read_from_disk()`
def _read_incremental_tail(fh, saved_rows: list[dict], offset: int, source: str, total_bytes: int, idx_path: Path | None) -> tuple[list[dict], int]:
	fh.seek(offset)
	tail_raw = fh.read()
	added = dfh_parse_jsonl_bytes(tail_raw)
	if None is added:
		r: list[dict] = []
	else:
		r = [*saved_rows, *added]
		_save_disk_index(idx_path, fh, source, total_bytes, r)
	return (r, len(tail_raw))
# @used-by :func:`_save_disk_index()`
# @used-by :func:`_validate_disk_index()`
def _read_slice_sha256(fh, start: int, length: int) -> str:
	fh.seek(start)
	return hashlib.sha256(fh.read(length)).hexdigest() if 0 < length else ''
# @used-by :func:`_read_full_file()`
# @used-by :func:`_read_incremental_tail()`
def _save_disk_index(idx_path: Path | None, fh, source: str, total_bytes: int, rows: list[dict]) -> None:
	if None is not idx_path:
		plen = min(total_bytes, _PREFIX_BYTES)
		tlen = min(total_bytes, _TAIL_BYTES)
		payload = {'offset': total_bytes, 'prefix_len': plen, 'prefix_sha256': _read_slice_sha256(fh, 0, plen), 'rows': rows, 'source': source, 'tail_len': tlen, 'tail_sha256': _read_slice_sha256(fh, total_bytes - tlen, tlen), 'version': 1}
		try:
			dfh_replace_bytes(idx_path, (json.dumps(payload, ensure_ascii=False, indent='\t', sort_keys=True) + '\n').encode('utf-8'))
		except OSError:
			pass
# @used-by :func:`dfh_read_from_disk()`
def _validate_disk_index(fh, saved: dict | None, source: str, total_bytes: int) -> tuple[list[dict], int] | None:
	r: tuple[list[dict], int] | None = None
	if isinstance(saved, dict) and 1 == saved.get('version') and source == saved.get('source') and isinstance(saved.get('rows'), list):
		try:
			offset, plen, tlen = (int(saved.get('offset', -1)), int(saved.get('prefix_len', -1)), int(saved.get('tail_len', -1)))
		except (TypeError, ValueError):
			offset, plen, tlen = (-1, -1, -1)
		if 0 <= offset <= total_bytes and 0 <= plen <= offset and 0 <= tlen <= offset:
			if saved.get('prefix_sha256') == _read_slice_sha256(fh, 0, plen) and saved.get('tail_sha256') == _read_slice_sha256(fh, offset - tlen, tlen):
				r = (saved['rows'], offset)
	return r
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_trace_event_cache_full_incremental_and_clear()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_in_process_cache_shares_single_disk_read_across_pre_tool_gates()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_incremental_disk_cache_appends_and_invalidation()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_untracked_dir_skips_disk_index_and_stays_in_process_only()`
# @used-by :mod:`agent_tools.trace_event_cache`
def dfh_clear_in_process_trace_cache() -> None:
	with MEM_LOCK:
		MEM_CACHE.clear()
# @used-by :func:`dfh_read_from_disk()`
# @used-by :mod:`agent_tools.trace_event_cache`
def dfh_load_disk_index(idx_path: Path | None) -> dict | None:
	r: dict | None = None
	if None is not idx_path and idx_path.is_file():
		try:
			raw = json.loads(idx_path.read_text(encoding='utf-8'))
			if isinstance(raw, dict):
				r = raw
		except (OSError, ValueError):
			r = None
	return r
# @used-by :func:`_read_full_file()`
# @used-by :func:`_read_incremental_tail()`
# @used-by :mod:`agent_tools.trace_event_cache`
def dfh_parse_jsonl_bytes(raw: bytes) -> list[dict] | None:
	rows: list[dict] = []
	ok = True
	for line in raw.decode('utf-8', errors='replace').splitlines():
		if line.strip():
			try:
				obj = json.loads(line)
			except ValueError:
				ok = False
				break
			if isinstance(obj, dict):
				rows.append({k: obj[k] for k in _ROW_KEYS if k in obj})
	return rows if ok else None
# @used-by :meth:`Df.Harness.Hook.TraceEventCache.TraceEventCache.run()`
# @used-by :mod:`agent_tools.trace_event_cache`
def dfh_read_from_disk(t_path: Path, source: str, total_bytes: int, idx_path: Path | None) -> tuple[list[dict], bool, int]:
	saved = dfh_load_disk_index(idx_path)
	rows, hit, parsed_bytes = ([], False, 0)
	try:
		with open(t_path, 'rb') as fh:
			matched = _validate_disk_index(fh, saved, source, total_bytes)
			if None is matched:
				rows, parsed_bytes = _read_full_file(fh, source, total_bytes, idx_path)
			else:
				hit = True
				saved_rows, offset = matched
				rows, parsed_bytes = (list(saved_rows), 0) if offset == total_bytes else _read_incremental_tail(fh, saved_rows, offset, source, total_bytes, idx_path)
	except OSError:
		rows, hit, parsed_bytes = ([], False, 0)
	return (rows, hit, parsed_bytes)
# @used-by :meth:`Df.Harness.Hook.TraceEventCache.TraceEventCache.run()`
# @used-by :mod:`agent_tools.trace_event_cache`
def dfh_resolve_effective_transcript(transcript_path: Path) -> Path:
	t_path = Path(transcript_path)
	if 'transcript.jsonl' == t_path.name:
		full_sib = t_path.parent / 'transcript_full.jsonl'
		if full_sib.is_file():
			t_path = full_sib
	return t_path
# @used-by :meth:`Df.Harness.Hook.TraceEventCache.TraceEventCache.run()`
# @used-by :mod:`agent_tools.trace_event_cache`
def dfh_resolve_index_path(t_path: Path, cwd: Path | None) -> Path | None:
	turns_dir = _find_turns_dir(cwd)
	return None if None is turns_dir else turns_dir / f'{_conversation_id_for(t_path)}-trace-index.json'
# @used-by :meth:`Df.Harness.Hook.TraceEventCache.TraceEventCache.run()`
# @used-by :mod:`agent_tools.trace_event_cache`
def dfh_store_mem_cache(mem_key: tuple[str, int, int], rows: list[dict]) -> None:
	with MEM_LOCK:
		if 64 < len(MEM_CACHE):
			MEM_CACHE.clear()
		MEM_CACHE[mem_key] = list(rows)