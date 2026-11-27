# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Hook.TraceEventCache import TraceEventCache
from Df.Harness.lib.hook_trace_cache import MEM_CACHE as _MEM_CACHE, MEM_LOCK as _MEM_LOCK, dfh_clear_in_process_trace_cache as clear_in_process_trace_cache, dfh_load_disk_index as _load_disk_index, dfh_parse_jsonl_bytes as _parse_jsonl_bytes, dfh_read_from_disk as _read_from_disk, dfh_resolve_effective_transcript as resolve_effective_transcript, dfh_resolve_index_path as _resolve_index_path, dfh_store_mem_cache as _store_mem_cache
# @used-by :func:`agent_tools.issue_first_gate.extract_antigravity_issue_first_events()`
# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.__load_transcript_rows()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_incremental_disk_cache_appends_and_invalidation()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_untracked_dir_skips_disk_index_and_stays_in_process_only()`
# @used-by :mod:`agent_tools.trace_event_cache`
def load_transcript_rows_cached(transcript_path: Path, *, cwd: Path | None=None, return_stats: bool=False) -> list[dict] | tuple[list[dict], dict[str, Any]]:
	return TraceEventCache(transcript_path, cwd=cwd, return_stats=return_stats).run()
__all__ = ['_MEM_CACHE', '_MEM_LOCK', '_load_disk_index', '_parse_jsonl_bytes', '_read_from_disk', '_resolve_index_path', '_store_mem_cache', 'clear_in_process_trace_cache', 'load_transcript_rows_cached', 'resolve_effective_transcript']