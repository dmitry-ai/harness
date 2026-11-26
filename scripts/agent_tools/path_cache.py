# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
from typing import Any
import json
import os
import stat
import tempfile
import threading
import time
from Df.Core.lib.fs import df_stat_sig
# 2026-11-24
# "Accelerate project_paths and overlay link resolution with fast-path caching":
# https://github.com/dmitry-ai/harness/issues/174
CACHE_LIMIT = 4096
OVERLAY_REFRESH_TTL_S = 5.0
# 2026-11-26 "Add RLock to path_cache and migrate diff_coverage to sys.monitoring": https://github.com/dmitry-ai/harness/issues/352
_CACHE_LOCK = threading.RLock()
_FAST_PROJECT_PATHS: OrderedDict[tuple, tuple[Any, tuple, int]] = OrderedDict()
_OVERLAY_TTL_STATE: dict[str, Any] = {'expires_at': 0.0, 'reg_path': None}
_TEMP_DIR_RESOLVED = Path(tempfile.gettempdir()).resolve()
# @used-by :func:`lookup_fast_project_paths()`
# @used-by :func:`store_fast_project_paths()`
def _fast_sig(pp: Any, reg: Any) -> tuple:
	j_root = pp.journal_root_dir
	j_dir = pp.journal_dir
	j_req = pp.path('journal_req_dir')
	pjson = pp.project_json
	sw_git = pp.root / '\u2c0f/\u227b/\u2655/\u26ef/.git'
	j_dir_sig = _stat_mtime(j_dir) if j_dir != j_root else None
	return (
		_stat_mtime(pp.root),
		_stat_mtime(j_root),
		j_dir_sig,
		_stat_mtime(j_req) if None is not j_req else 0,
		_stat_mtime(pp.agent_dir),
		_stat_mtime_size(pjson),
		_stat_mtime(sw_git),
		_overlay_candidates_sig(pp.root, reg),
	)
# @used-by :func:`_fast_sig()`
def _overlay_candidates_sig(root: Path, reg: Any) -> tuple:
	root_posix = root.as_posix()
	sig: list[tuple] = []
	for rel in reg.overlay_candidates:
		p_str = f'{root_posix}/{rel}'
		try:
			st = os.lstat(p_str)
			c_hash = hash(Path(p_str).read_bytes()) if stat.S_ISREG(st.st_mode) else 0
			sig.append((rel, st.st_mtime_ns, st.st_size, c_hash))
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
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`_fast_sig()`
def _stat_mtime_size(path: Path) -> tuple[int, int]:
	return df_stat_sig(path) or (0, 0)
# 2026-11-26 "Add RLock to path_cache and migrate diff_coverage to sys.monitoring": https://github.com/dmitry-ai/harness/issues/352
# @used-by :func:`agent_tools.path_registry.clear_registry_cache()`
# @used-by :func:`agent_tools.project_rename._apply_rename_mutations()`
# @used-by :func:`agent_tools.project_rename._rollback_rename()`
# @used-by :func:`agent_tools.shadow_replay_clone._restore_shadow_registry()`
# @used-by :func:`agent_tools.shadow_replay_clone.shadow_isolation_context()`
# @used-by :func:`git_fixture_cache._clear_harness_caches()`
# @used-by :meth:`test_git_fixture_cache.GitFixtureCacheTests.test_run_harness_inprocess_executes_cli_isolates_env_cwd_and_clears_caches()`
# @used-by :meth:`test_git_fixture_cache.GitFixtureCacheTests.test_run_harness_inprocess_restores_env_and_cwd_on_system_exit_and_exception()`
# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_path_cache_rlock_handles_concurrent_eviction_and_clear()`
def clear_path_cache() -> None:
	with _CACHE_LOCK:
		_FAST_PROJECT_PATHS.clear()
		_OVERLAY_TTL_STATE['expires_at'] = 0.0
		_OVERLAY_TTL_STATE['reg_path'] = None
		# 2026-11-24
		# "Cache runtime settings and deduplicate evidence validation in hot paths":
		# https://github.com/dmitry-ai/harness/issues/227
		try:
			from .runtime_cache import clear_runtime_cache
			clear_runtime_cache()
		except Exception:
			pass
# 2026-11-24
# "Deploy immutable Harness runtime snapshots with LKG fallback":
# https://github.com/dmitry-ai/harness/issues/184
# @used-by :func:`agent_tools.runtime.settings()`
def default_runtime_file(primary: Path, code_anchor: Path, registry_file: Path) -> Path:
	snap_rt = registry_file.parent / 'runtime.json'
	if primary.resolve() == code_anchor.resolve() and (registry_file.parent / 'snapshot.json').is_file() and snap_rt.is_file():
		r = snap_rt
	else:
		r = primary / 'runtime.json'
	return r
# 2026-11-26 "Add RLock to path_cache and migrate diff_coverage to sys.monitoring": https://github.com/dmitry-ai/harness/issues/352
# @used-by :func:`agent_tools.path_registry._refresh_known_overlay_links()`
def get_ttl_overlay_links(reg: Any, default_registry_file: Path, discovery_state: dict[str, Any]) -> dict[str, Path] | None:
	with _CACHE_LOCK:
		r = None
		if reg.source_path == default_registry_file.resolve() and None is not discovery_state['fingerprint']:
			if _OVERLAY_TTL_STATE['reg_path'] == reg.source_path and time.monotonic() < _OVERLAY_TTL_STATE['expires_at']:
				r = dict(discovery_state['links'])
	return r
# @used-by :func:`resolve_reverse_map()`
def is_under_tempdir(path: Path) -> bool:
	try:
		r = path.resolve().is_relative_to(_TEMP_DIR_RESOLVED)
	except (OSError, ValueError):
		r = False
	return r
# 2026-11-26 "Add RLock to path_cache and migrate diff_coverage to sys.monitoring": https://github.com/dmitry-ai/harness/issues/352
# @used-by :func:`agent_tools.path_registry.project_paths()`
def lookup_fast_project_paths(cache_key: tuple, reg: Any, rev_len: int) -> Any | None:
	with _CACHE_LOCK:
		entry = _FAST_PROJECT_PATHS.get(cache_key)
		r = None
		if None is not entry:
			pp, saved_sig, saved_rev_len = entry
			if saved_rev_len == rev_len and _fast_sig(pp, reg) == saved_sig:
				_FAST_PROJECT_PATHS.move_to_end(cache_key)
				r = pp
			else:
				_FAST_PROJECT_PATHS.pop(cache_key, None)
	return r
# 2026-11-26 "Add RLock to path_cache and migrate diff_coverage to sys.monitoring": https://github.com/dmitry-ai/harness/issues/352
# @used-by :func:`agent_tools.path_registry.project_paths()`
# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_path_cache_rlock_handles_concurrent_eviction_and_clear()`
def lru_get(cache: OrderedDict, key: tuple) -> Any | None:
	with _CACHE_LOCK:
		hit = cache.get(key)
		if None is not hit:
			cache.move_to_end(key)
	return hit
# 2026-11-26 "Add RLock to path_cache and migrate diff_coverage to sys.monitoring": https://github.com/dmitry-ai/harness/issues/352
# @used-by :func:`agent_tools.path_registry.project_paths()`
# @used-by :func:`store_fast_project_paths()`
# @used-by :meth:`test_path_cache_and_diff_cov_perf.PathCacheAndDiffCovPerfTests.test_path_cache_rlock_handles_concurrent_eviction_and_clear()`
def lru_put(cache: OrderedDict, key: tuple, value: Any) -> None:
	with _CACHE_LOCK:
		cache[key] = value
		cache.move_to_end(key)
		while CACHE_LIMIT < len(cache):
			cache.popitem(last=False)
# 2026-11-26 "Add RLock to path_cache and migrate diff_coverage to sys.monitoring": https://github.com/dmitry-ai/harness/issues/352
# @used-by :func:`agent_tools.path_registry._refresh_known_overlay_links()`
def mark_overlay_links_refreshed(reg: Any, default_registry_file: Path) -> None:
	with _CACHE_LOCK:
		if reg.source_path == default_registry_file.resolve():
			_OVERLAY_TTL_STATE['reg_path'] = reg.source_path
			_OVERLAY_TTL_STATE['expires_at'] = time.monotonic() + OVERLAY_REFRESH_TTL_S
# @used-by :func:`agent_tools.path_registry._refresh_known_overlay_links()`
def overlay_signature_for_roots(candidate_roots: tuple[Path, ...], overlay_candidates: tuple[str, ...]) -> tuple:
	ov_sig: list[tuple] = []
	for root_p in candidate_roots:
		root_posix = root_p.as_posix()
		for rel in overlay_candidates:
			p_str = f'{root_posix}/{rel}'
			try:
				st = os.lstat(p_str)
				c_hash = hash(Path(p_str).read_bytes()) if stat.S_ISREG(st.st_mode) else 0
				ov_sig.append((p_str, st.st_mtime_ns, st.st_size, c_hash))
			except OSError:
				pass
	return tuple(ov_sig)
# 2026-11-24
# "Fix worktree scope resolution for new files in TDD classifier":
# https://github.com/dmitry-ai/harness/issues/188
# @used-by :func:`resolve_code_anchor()`
def _linked_worktree_main_repo(anchor_dir: Path) -> Path | None:
	r = None
	dot_git = anchor_dir / '.git'
	if dot_git.is_file():
		try:
			txt = dot_git.read_text(encoding='utf-8', errors='replace').strip()
			if txt.lower().startswith('gitdir:'):
				raw = txt.split(':', 1)[1].strip()
				gitdir = Path(raw)
				if not gitdir.is_absolute():
					gitdir = (anchor_dir / gitdir).resolve()
				if 'worktrees' == gitdir.parent.name and '.git' == gitdir.parent.parent.name:
					r = gitdir.parent.parent.parent.resolve()
		except OSError:
			r = None
	return r
# 2026-11-24
# "Fix worktree scope resolution for new files in TDD classifier":
# https://github.com/dmitry-ai/harness/issues/188
# @used-by :func:`agent_tools.git_ignore._is_canonical_primary()`
# @used-by :func:`agent_tools.native_profiles.shared_native_outputs()`
# @used-by :func:`agent_tools.rules_manifest.resolve_rules_primary()`
# @used-by :meth:`agent_tools.path_registry.PathRegistry.__init__()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_resolve_code_anchor_maps_linked_worktree_to_canonical_main_repo()`
# @used-by :mod:`agent_tools.path_registry`
def resolve_code_anchor(anchor_dir: Path) -> Path:
	resolved = Path(anchor_dir).resolve()
	r = resolved
	meta_file = resolved / 'snapshot.json'
	if meta_file.is_file():
		try:
			meta = json.loads(meta_file.read_text(encoding='utf-8-sig'))
			canon = meta.get('canonical_primary') if isinstance(meta, dict) else None
			if isinstance(canon, str) and canon.strip():
				r = Path(canon.strip()).resolve()
		except (OSError, ValueError):
			r = resolved
	else:
		wt_main = _linked_worktree_main_repo(resolved)
		if None is not wt_main:
			r = wt_main
	return r
# @used-by :func:`agent_tools.storage.journal_data_dir_for()`
def resolve_journal_data_dir(eff: Path) -> Path:
	from .path_registry import project_paths, workspace_override
	fast_root = None
	if '\ua66e' == eff.name and eff.parent.is_dir():
		cand = eff.parent.parent if '_' == eff.parent.name and eff.parent.parent.is_dir() else eff.parent
		if ((cand / '\ua616').is_dir() or (cand / '.agents').is_dir() or (cand / '\U0001f56e').is_dir() or (cand / '_/\ua616').is_dir()) and None is workspace_override(cand):
			fast_root = cand
	return project_paths(fast_root, exact_root=True).data_dir if None is not fast_root else project_paths(eff).data_dir
# @used-by :func:`agent_tools.path_registry.resolve_project_root()`
def resolve_reverse_map(start: Path, local_idx: int | None, local_root: Path | None, reg: Any, default_registry_file: Path, discovery_state: dict[str, Any], overlay_reverse_map: dict[str, Path], refresh_fn) -> dict[str, Path]:
	is_default_reg = reg.source_path == default_registry_file.resolve()
	if is_default_reg and is_under_tempdir(start):
		r = dict(overlay_reverse_map)
	elif None is not local_root and is_default_reg and None is not discovery_state['fingerprint']:
		r = {**discovery_state['links'], **overlay_reverse_map}
	else:
		r = {**refresh_fn(reg), **overlay_reverse_map}
	return r
# 2026-11-26 "Add RLock to path_cache and migrate diff_coverage to sys.monitoring": https://github.com/dmitry-ai/harness/issues/352
# @used-by :func:`agent_tools.path_registry.project_paths()`
def store_fast_project_paths(cache_key: tuple, pp: Any, reg: Any, rev_len: int) -> None:
	with _CACHE_LOCK:
		lru_put(_FAST_PROJECT_PATHS, cache_key, (pp, _fast_sig(pp, reg), rev_len))
