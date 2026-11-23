# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Accelerate project_paths and overlay link resolution with fast-path caching":
# https://github.com/dmitry-ai/harness/issues/174
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
from typing import Any
import os
import stat
import tempfile
import time
CACHE_LIMIT = 4096
OVERLAY_REFRESH_TTL_S = 5.0
_FAST_PROJECT_PATHS: OrderedDict[tuple, tuple[Any, tuple, int]] = OrderedDict()
_OVERLAY_TTL_STATE: dict[str, Any] = {'expires_at': 0.0, 'reg_path': None}
_TEMP_DIR_RESOLVED = Path(tempfile.gettempdir()).resolve()
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
def _stat_mtime(path: Path) -> int:
	try:
		r = os.stat(path).st_mtime_ns
	except OSError:
		r = 0
	return r
def _stat_mtime_size(path: Path) -> tuple[int, int]:
	try:
		st = os.stat(path)
		r = (st.st_mtime_ns, st.st_size)
	except OSError:
		r = (0, 0)
	return r
def clear_path_cache() -> None:
	_FAST_PROJECT_PATHS.clear()
	_OVERLAY_TTL_STATE['expires_at'] = 0.0
	_OVERLAY_TTL_STATE['reg_path'] = None
def get_ttl_overlay_links(reg: Any, default_registry_file: Path, discovery_state: dict[str, Any]) -> dict[str, Path] | None:
	r = None
	if reg.source_path == default_registry_file.resolve() and None is not discovery_state['fingerprint']:
		if _OVERLAY_TTL_STATE['reg_path'] == reg.source_path and time.monotonic() < _OVERLAY_TTL_STATE['expires_at']:
			r = dict(discovery_state['links'])
	return r
def is_under_tempdir(path: Path) -> bool:
	try:
		r = path.resolve().is_relative_to(_TEMP_DIR_RESOLVED)
	except (OSError, ValueError):
		r = False
	return r
def lookup_fast_project_paths(cache_key: tuple, reg: Any, rev_len: int) -> Any | None:
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
def lru_get(cache: OrderedDict, key: tuple) -> Any | None:
	hit = cache.get(key)
	if None is not hit:
		cache.move_to_end(key)
	return hit
def lru_put(cache: OrderedDict, key: tuple, value: Any) -> None:
	cache[key] = value
	cache.move_to_end(key)
	while CACHE_LIMIT < len(cache):
		cache.popitem(last=False)
def mark_overlay_links_refreshed(reg: Any, default_registry_file: Path) -> None:
	if reg.source_path == default_registry_file.resolve():
		_OVERLAY_TTL_STATE['reg_path'] = reg.source_path
		_OVERLAY_TTL_STATE['expires_at'] = time.monotonic() + OVERLAY_REFRESH_TTL_S
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
def resolve_journal_data_dir(eff: Path) -> Path:
	from .path_registry import project_paths, workspace_override
	fast_root = None
	if '\ua66e' == eff.name and eff.parent.is_dir():
		cand = eff.parent.parent if '_' == eff.parent.name and eff.parent.parent.is_dir() else eff.parent
		if ((cand / '\ua616').is_dir() or (cand / '.agents').is_dir() or (cand / '\U0001f56e').is_dir() or (cand / '_/\ua616').is_dir()) and None is workspace_override(cand):
			fast_root = cand
	return project_paths(fast_root, exact_root=True).data_dir if None is not fast_root else project_paths(eff).data_dir
def resolve_reverse_map(start: Path, local_idx: int | None, local_root: Path | None, reg: Any, default_registry_file: Path, discovery_state: dict[str, Any], overlay_reverse_map: dict[str, Path], refresh_fn) -> dict[str, Path]:
	is_default_reg = reg.source_path == default_registry_file.resolve()
	if is_default_reg and is_under_tempdir(start):
		r = dict(overlay_reverse_map)
	elif None is not local_root and is_default_reg and None is not discovery_state['fingerprint']:
		r = {**discovery_state['links'], **overlay_reverse_map}
	else:
		r = {**refresh_fn(reg), **overlay_reverse_map}
	return r
def store_fast_project_paths(cache_key: tuple, pp: Any, reg: Any, rev_len: int) -> None:
	lru_put(_FAST_PROJECT_PATHS, cache_key, (pp, _fast_sig(pp, reg), rev_len))
