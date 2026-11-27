# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Path.CacheStore import CacheStore
from Df.Harness.lib.path_state import CACHE_LIMIT, CACHE_LOCK as _CACHE_LOCK, FAST_PROJECT_PATHS as _FAST_PROJECT_PATHS, OVERLAY_REFRESH_TTL_S, OVERLAY_TTL_STATE as _OVERLAY_TTL_STATE, dfh_clear_path_cache, dfh_default_runtime_file, dfh_get_ttl_overlay_links, dfh_is_under_tempdir, dfh_lookup_fast_project_paths, dfh_lru_get, dfh_lru_put, dfh_mark_overlay_links_refreshed, dfh_overlay_signature_for_roots, dfh_resolve_reverse_map, dfh_store_fast_project_paths
# @used-by :func:`agent_tools.project_rename._apply_rename_mutations()`
# @used-by :func:`agent_tools.project_rename._rollback_rename()`
# @used-by :func:`git_fixture_cache._clear_harness_caches()`
# @used-by :meth:`test_git_fixture_cache.GitFixtureCacheTests.test_run_harness_inprocess_executes_cli_isolates_env_cwd_and_clears_caches()`
# @used-by :meth:`test_git_fixture_cache.GitFixtureCacheTests.test_run_harness_inprocess_restores_env_and_cwd_on_system_exit_and_exception()`
# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_path_cache_rlock_handles_concurrent_eviction_and_clear()`
def clear_path_cache() -> None:
	dfh_clear_path_cache()
# @used-by :func:`agent_tools.runtime.settings()`
def default_runtime_file(primary: Path, code_anchor: Path, registry_file: Path) -> Path:
	return dfh_default_runtime_file(primary, code_anchor, registry_file)
# @used-by unused
def get_ttl_overlay_links(reg: Any, default_registry_file: Path, discovery_state: dict[str, Any]) -> dict[str, Path] | None:
	return dfh_get_ttl_overlay_links(reg, default_registry_file, discovery_state)
# @used-by unused
def is_under_tempdir(path: Path) -> bool:
	return dfh_is_under_tempdir(path)
# @used-by unused
def lookup_fast_project_paths(cache_key: tuple, reg: Any, rev_len: int) -> Any | None:
	return dfh_lookup_fast_project_paths(cache_key, reg, rev_len)
# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_path_cache_rlock_handles_concurrent_eviction_and_clear()`
def lru_get(cache: OrderedDict, key: tuple) -> Any | None:
	return dfh_lru_get(cache, key)
# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_path_cache_rlock_handles_concurrent_eviction_and_clear()`
def lru_put(cache: OrderedDict, key: tuple, value: Any) -> None:
	dfh_lru_put(cache, key, value, limit=CACHE_LIMIT)
# @used-by unused
def mark_overlay_links_refreshed(reg: Any, default_registry_file: Path) -> None:
	dfh_mark_overlay_links_refreshed(reg, default_registry_file)
# @used-by unused
def overlay_signature_for_roots(candidate_roots: tuple[Path, ...], overlay_candidates: tuple[str, ...]) -> tuple:
	return dfh_overlay_signature_for_roots(candidate_roots, overlay_candidates)
# @used-by :func:`agent_tools.git_ignore._is_canonical_primary()`
# @used-by :func:`agent_tools.rules_manifest.resolve_rules_primary()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_resolve_code_anchor_maps_linked_worktree_to_canonical_main_repo()`
# @used-by :mod:`agent_tools.path_registry`
def resolve_code_anchor(anchor_dir: Path) -> Path:
	return CacheStore(anchor_dir).run()
# @used-by unused
def resolve_journal_data_dir(eff: Path) -> Path:
	from Df.Harness.lib.path_resolve import dfh_resolve_journal_data_dir
	return dfh_resolve_journal_data_dir(eff)
# @used-by unused
def resolve_reverse_map(start: Path, local_idx: int | None, local_root: Path | None, reg: Any, default_registry_file: Path, discovery_state: dict[str, Any], overlay_reverse_map: dict[str, Path], refresh_fn) -> dict[str, Path]:
	return dfh_resolve_reverse_map(start, local_idx, local_root, reg, default_registry_file, discovery_state, overlay_reverse_map, refresh_fn)
# @used-by unused
def store_fast_project_paths(cache_key: tuple, pp: Any, reg: Any, rev_len: int) -> None:
	dfh_store_fast_project_paths(cache_key, pp, reg, rev_len, limit=CACHE_LIMIT)
