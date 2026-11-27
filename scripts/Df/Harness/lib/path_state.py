# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
from typing import Any
from Df.Core.lib.fs import df_stat_sig
from Df.Harness.Path.CacheStore import CacheStore
import os
import stat
import tempfile
import threading
import time
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
CACHE_LIMIT = 4096
CACHE_LOCK = threading.RLock()
CODE_ANCHOR = CacheStore(Path(__file__).resolve().parents[4]).run()
DEFAULT_REGISTRY_FILE = Path(__file__).resolve().parents[4] / 'paths.json'
DISCOVERY_STATE: dict[str, Any] = {'candidate_roots': (), 'fingerprint': None, 'links': {}, 'roots_key': None, 'similar_links': {}}
FAST_PROJECT_PATHS: OrderedDict[tuple, tuple[Any, tuple, int]] = OrderedDict()
OVERLAY_REFRESH_TTL_S = 5.0
OVERLAY_REVERSE_MAP: dict[str, Path] = {}
OVERLAY_TTL_STATE: dict[str, Any] = {'expires_at': 0.0, 'reg_path': None}
PROJECT_PATHS_CACHE: OrderedDict[tuple, Any] = OrderedDict()
REGISTRY_CACHE: dict[tuple, Any] = {}
SHADOW_LOAD_HOOK: list[Any] = [None]
SIMILAR_REVERSE_MAP: dict[tuple[str, str], list[Path]] = {}
_TEMP_DIR_RESOLVED = Path(tempfile.gettempdir()).resolve()
# @used-by :func:`dfh_lookup_fast_project_paths()`
# @used-by :func:`dfh_store_fast_project_paths()`
def _fast_sig(pp: Any, reg: Any) -> tuple:
	j_root, j_dir, j_req = (pp.journal_root_dir, pp.journal_dir, pp.path('journal_req_dir'))
	j_dir_sig = _stat_mtime(j_dir) if j_dir != j_root else None
	return (_stat_mtime(pp.root), _stat_mtime(j_root), j_dir_sig, _stat_mtime(j_req) if None is not j_req else 0, _stat_mtime(pp.agent_dir), df_stat_sig(pp.project_json) or (0, 0), _stat_mtime(pp.root / '\u2c0f/\u227b/\u2655/\u26ef/.git'), _overlay_candidates_sig(pp.root, reg))
# @used-by :func:`_fast_sig()`
def _overlay_candidates_sig(root: Path, reg: Any) -> tuple:
	root_posix = root.as_posix()
	sig: list[tuple] = []
	for rel in reg.overlay_candidates:
		p_str = f'{root_posix}/{rel}'
		try:
			st = os.lstat(p_str)
			sig.append((rel, st.st_mtime_ns, st.st_size, hash(Path(p_str).read_bytes()) if stat.S_ISREG(st.st_mode) else 0))
		except OSError:
			sig.append((rel, 0, 0, 0))
	return tuple(sig)
# @used-by :func:`_fast_sig()`
def _stat_mtime(path: Path) -> int:
	try:
		r = os.stat(path).st_mtime_ns
	except OSError:
		r = 0
	return r
# @used-by :func:`Df.Harness.lib.shadow_clone.dfh_shadow_isolation_context()`
# @used-by :func:`agent_tools.path_cache.clear_path_cache()`
# @used-by :func:`dfh_clear_registry_cache()`
def dfh_clear_path_cache() -> None:
	with CACHE_LOCK:
		FAST_PROJECT_PATHS.clear()
		OVERLAY_TTL_STATE['expires_at'] = 0.0
		OVERLAY_TTL_STATE['reg_path'] = None
		try:
			from Df.Harness.lib.runtime_cache import dfh_clear_runtime_cache
			dfh_clear_runtime_cache()
		except Exception:
			pass
# @used-by :func:`Df.Harness.lib.journal_upgrade._execute_upgrade()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._sync_overlay_journal_slot()`
# @used-by :func:`Df.Harness.lib.shadow_clone.dfh_shadow_isolation_context()`
# @used-by :func:`agent_tools.path_registry.clear_registry_cache()`
def dfh_clear_registry_cache() -> None:
	REGISTRY_CACHE.clear()
	PROJECT_PATHS_CACHE.clear()
	OVERLAY_REVERSE_MAP.clear()
	SIMILAR_REVERSE_MAP.clear()
	DISCOVERY_STATE.update({'candidate_roots': (), 'fingerprint': None, 'links': {}, 'roots_key': None, 'similar_links': {}})
	dfh_clear_path_cache()
	try:
		from agent_tools.issues.repo_locator import clear_repo_locator_cache
		clear_repo_locator_cache()
	except Exception:
		pass
# @used-by :func:`agent_tools.path_cache.default_runtime_file()`
# @used-by :meth:`Df.Harness.Runtime.SettingsLoader.SettingsLoader.__resolve_file()`
def dfh_default_runtime_file(primary: Path, code_anchor: Path, registry_file: Path) -> Path:
	snap_rt = registry_file.parent / 'runtime.json'
	return snap_rt if primary.resolve() == code_anchor.resolve() and (registry_file.parent / 'snapshot.json').is_file() and snap_rt.is_file() else primary / 'runtime.json'
# @used-by :func:`Df.Harness.lib.path_discovery.dfh_refresh_known_overlay_links()`
# @used-by :func:`agent_tools.path_cache.get_ttl_overlay_links()`
def dfh_get_ttl_overlay_links(reg: Any, default_registry_file: Path, discovery_state: dict[str, Any]) -> dict[str, Path] | None:
	with CACHE_LOCK:
		r = None
		if reg.source_path == default_registry_file.resolve() and None is not discovery_state['fingerprint']:
			if OVERLAY_TTL_STATE['reg_path'] == reg.source_path and time.monotonic() < OVERLAY_TTL_STATE['expires_at']:
				r = dict(discovery_state['links'])
	return r
# @used-by :func:`agent_tools.path_cache.is_under_tempdir()`
# @used-by :func:`dfh_resolve_reverse_map()`
def dfh_is_under_tempdir(path: Path) -> bool:
	try:
		r = path.resolve().is_relative_to(_TEMP_DIR_RESOLVED)
	except (OSError, ValueError):
		r = False
	return r
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_project_paths()`
# @used-by :func:`agent_tools.path_cache.lookup_fast_project_paths()`
def dfh_lookup_fast_project_paths(cache_key: tuple, reg: Any, rev_len: int) -> Any | None:
	with CACHE_LOCK:
		entry = FAST_PROJECT_PATHS.get(cache_key)
		r = None
		if None is not entry:
			pp, saved_sig, saved_rev_len = entry
			if saved_rev_len == rev_len and _fast_sig(pp, reg) == saved_sig:
				FAST_PROJECT_PATHS.move_to_end(cache_key)
				r = pp
			else:
				FAST_PROJECT_PATHS.pop(cache_key, None)
	return r
# @used-by :func:`Df.Harness.lib.path_resolve._build_or_fetch_project_paths()`
# @used-by :func:`agent_tools.path_cache.lru_get()`
def dfh_lru_get(cache: OrderedDict, key: tuple) -> Any | None:
	with CACHE_LOCK:
		hit = cache.get(key)
		if None is not hit:
			cache.move_to_end(key)
	return hit
# @used-by :func:`Df.Harness.lib.path_resolve._build_or_fetch_project_paths()`
# @used-by :func:`agent_tools.path_cache.lru_put()`
# @used-by :func:`dfh_store_fast_project_paths()`
def dfh_lru_put(cache: OrderedDict, key: tuple, value: Any, *, limit: int | None=None) -> None:
	cap = CACHE_LIMIT if None is limit else limit
	with CACHE_LOCK:
		cache[key] = value
		cache.move_to_end(key)
		while cap < len(cache):
			cache.popitem(last=False)
# @used-by :func:`Df.Harness.lib.path_discovery.dfh_refresh_known_overlay_links()`
# @used-by :func:`agent_tools.path_cache.mark_overlay_links_refreshed()`
def dfh_mark_overlay_links_refreshed(reg: Any, default_registry_file: Path) -> None:
	with CACHE_LOCK:
		if reg.source_path == default_registry_file.resolve():
			OVERLAY_TTL_STATE['reg_path'] = reg.source_path
			OVERLAY_TTL_STATE['expires_at'] = time.monotonic() + OVERLAY_REFRESH_TTL_S
# @used-by :func:`Df.Harness.lib.path_discovery.dfh_refresh_known_overlay_links()`
# @used-by :func:`agent_tools.path_cache.overlay_signature_for_roots()`
def dfh_overlay_signature_for_roots(candidate_roots: tuple[Path, ...], overlay_candidates: tuple[str, ...]) -> tuple:
	ov_sig: list[tuple] = []
	for root_p in candidate_roots:
		root_posix = root_p.as_posix()
		for rel in overlay_candidates:
			p_str = f'{root_posix}/{rel}'
			try:
				st = os.lstat(p_str)
				ov_sig.append((p_str, st.st_mtime_ns, st.st_size, hash(Path(p_str).read_bytes()) if stat.S_ISREG(st.st_mode) else 0))
			except OSError:
				pass
	return tuple(ov_sig)
# @used-by :func:`Df.Harness.lib.path_resolve._resolve_from_markers_or_reverse()`
# @used-by :func:`agent_tools.path_cache.resolve_reverse_map()`
def dfh_resolve_reverse_map(start: Path, local_idx: int | None, local_root: Path | None, reg: Any, default_registry_file: Path, discovery_state: dict[str, Any], overlay_reverse_map: dict[str, Path], refresh_fn) -> dict[str, Path]:
	is_default = reg.source_path == default_registry_file.resolve()
	if is_default and dfh_is_under_tempdir(start):
		r = dict(overlay_reverse_map)
	elif None is not local_root and is_default and None is not discovery_state['fingerprint']:
		r = {**discovery_state['links'], **overlay_reverse_map}
	else:
		r = {**refresh_fn(reg), **overlay_reverse_map}
	return r
# @used-by :func:`Df.Harness.lib.path_resolve.dfh_project_paths()`
# @used-by :func:`agent_tools.path_cache.store_fast_project_paths()`
def dfh_store_fast_project_paths(cache_key: tuple, pp: Any, reg: Any, rev_len: int, *, limit: int | None=None) -> None:
	with CACHE_LOCK:
		dfh_lru_put(FAST_PROJECT_PATHS, cache_key, (pp, _fast_sig(pp, reg), rev_len), limit=limit)
