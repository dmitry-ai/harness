# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.hook_trace_cache import MEM_CACHE, MEM_LOCK, dfh_read_from_disk, dfh_resolve_effective_transcript, dfh_resolve_index_path, dfh_store_mem_cache
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class TraceEventCache:
	# @used-by :func:`agent_tools.trace_event_cache.load_transcript_rows_cached()`
	# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_trace_event_cache_full_incremental_and_clear()`
	def __init__(self, transcript_path: Path, *, cwd: Path | None=None, return_stats: bool=False) -> None:
		self.__transcript_path = transcript_path
		self.__cwd = cwd
		self.__return_stats = return_stats
	# @used-by :func:`agent_tools.trace_event_cache.load_transcript_rows_cached()`
	# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_trace_event_cache_full_incremental_and_clear()`
	def run(self) -> list[dict] | tuple[list[dict], dict[str, Any]]:
		t_path = dfh_resolve_effective_transcript(self.__transcript_path)
		rows, stats = ([], {'cache_hit': False, 'in_process_hit': False, 'index_path': None, 'parsed_bytes': 0, 'total_bytes': 0})
		if t_path.is_file():
			resolved = t_path.resolve()
			st = resolved.stat()
			mem_key = (str(resolved), st.st_size, st.st_mtime_ns)
			idx_path = dfh_resolve_index_path(resolved, self.__cwd)
			stats.update(index_path=idx_path.as_posix() if None is not idx_path else None, total_bytes=st.st_size)
			with MEM_LOCK:
				cached = MEM_CACHE.get(mem_key)
			if None is not cached:
				rows = list(cached)
				stats.update(cache_hit=True, in_process_hit=True)
			else:
				rows, hit, parsed_bytes = dfh_read_from_disk(resolved, str(resolved), st.st_size, idx_path)
				stats.update(cache_hit=hit, parsed_bytes=parsed_bytes)
				dfh_store_mem_cache(mem_key, rows)
		return (rows, stats) if self.__return_stats else rows