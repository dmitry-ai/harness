# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from Df.Harness.lib.path_resolve import dfh_load_registry
import json
import os
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_DERIVED_CACHE: dict[tuple, Any] = {}
_SETTINGS_CACHE: dict[tuple, tuple[dict, Path | None, tuple | None]] = {}
_SKIP_SHELL_VIOLATIONS: ContextVar[bool] = ContextVar('harness_skip_shell_violations', default=False)
# @used-by :func:`_compute_browser_perimeter()`
def _collect_one_session(sess: dict, ports: set[int], profile_dirs: set[str], active_port_files: set[str]) -> None:
	for ep_key in ('endpoint', 'fallback_endpoint'):
		ep_val = sess.get(ep_key)
		if isinstance(ep_val, str) and ep_val.strip():
			parsed = urlsplit(ep_val.strip())
			if parsed.port:
				ports.add(int(parsed.port))
	dap = sess.get('devtools_active_port')
	if isinstance(dap, str) and dap.strip():
		active_port_files.add(dap.strip().replace('\\', '/').rstrip('/').casefold())
	prof = sess.get('profile')
	prof_path = prof.get('path') if isinstance(prof, dict) else None
	if isinstance(prof_path, str) and prof_path.strip():
		profile_dirs.add(prof_path.strip().replace('\\', '/').rstrip('/').casefold())
# @used-by :func:`dfh_cached_addon_roots()`
def _compute_addon_roots(cfg_all: dict, expand_fn) -> tuple[Path, ...]:
	roots: list[Path] = []
	for plat_cfg in ((cfg_all or {}).get('platforms') or {}).values():
		if isinstance(plat_cfg, dict):
			_extract_platform_addon_roots(plat_cfg, expand_fn, roots)
	return tuple(dict.fromkeys(roots))
# @used-by :func:`dfh_cached_browser_perimeter()`
def _compute_browser_perimeter(cfg: dict) -> dict:
	ports: set[int] = set()
	profile_dirs: set[str] = set()
	active_port_files: set[str] = set()
	for plat_cfg in ((cfg or {}).get('platforms') or {}).values():
		browser = plat_cfg.get('browser') if isinstance(plat_cfg, dict) else None
		p = browser.get('cdp_port') if isinstance(browser, dict) else None
		if isinstance(p, int) and 0 < p < 65536:
			ports.add(p)
	sessions = ((cfg or {}).get('text') or {}).get('browser', {}).get('sessions')
	if isinstance(sessions, dict):
		for sess in sessions.values():
			if isinstance(sess, dict):
				_collect_one_session(sess, ports, profile_dirs, active_port_files)
	return {'active_port_files': sorted(active_port_files), 'ports': sorted(ports), 'profile_dirs': sorted(profile_dirs)}
# @used-by :func:`dfh_load_cached_settings()`
def _copy_json(value: Any) -> Any:
	if isinstance(value, dict):
		r: Any = {k: _copy_json(v) for k, v in value.items()}
	elif isinstance(value, list):
		r = [_copy_json(v) for v in value]
	else:
		r = value
	return r
# @used-by :func:`dfh_load_cached_settings_readonly()`
def _env_digest() -> tuple[tuple[str, str], ...]:
	return tuple(sorted(os.environ.items()))
# @used-by :func:`_compute_addon_roots()`
def _extract_platform_addon_roots(plat_cfg: dict, expand_fn, roots: list[Path]) -> None:
	addons_cfg = plat_cfg.get('addons')
	code_dir = addons_cfg.get('code_dir') if isinstance(addons_cfg, dict) else None
	if isinstance(code_dir, str) and code_dir.strip():
		roots.append(Path(expand_fn(code_dir)).resolve())
	ui_manage = plat_cfg.get('ui_manage')
	if isinstance(ui_manage, str) and ui_manage.strip():
		for anc in Path(expand_fn(ui_manage)).resolve().parents:
			if 'code' == anc.name.lower() and (anc.parent / '_').is_dir():
				roots.append(anc)
				break
# @used-by :func:`_load_uncached_settings()`
# @used-by :func:`dfh_load_cached_settings_readonly()`
def _file_stat_key(path: Path | None) -> tuple | None:
	r = None
	if None is not path:
		try:
			st = os.stat(path)
			r = (os.path.normcase(os.path.abspath(path)), st.st_mtime_ns, st.st_size)
		except OSError:
			r = None
	return r
# @used-by :func:`_safe_default_readonly()`
def _load_default_readonly(runtime_mod) -> tuple[tuple | None, dict]:
	if runtime_mod.settings is not runtime_mod._UNPATCHED_SETTINGS:
		r = (None, runtime_mod.settings())
	else:
		rt_file = runtime_mod.default_runtime_file(runtime_mod.PRIMARY, runtime_mod._CODE_ANCHOR, runtime_mod.DEFAULT_REGISTRY_FILE)
		r = dfh_load_cached_settings_readonly(rt_file, runtime_mod._validate_runtime)
	return r
# @used-by :func:`dfh_load_cached_settings_readonly()`
def _load_uncached_settings(runtime_file: Path, validate_fn) -> tuple[dict, Path | None, tuple | None]:
	raw = json.loads(runtime_file.read_text(encoding='utf-8-sig'))
	reg_rel = raw.get('paths_registry') if isinstance(raw, dict) else None
	has_custom = isinstance(reg_rel, str) and bool(reg_rel.strip())
	reg_cand = runtime_file.parent / reg_rel if has_custom else runtime_file.parent / 'paths.json'
	reg = dfh_load_registry(reg_cand if reg_cand.is_file() else None, primary=runtime_file.parent if (runtime_file.parent / 'rules').is_dir() else None)
	value = reg.expand_data(raw)
	validate_fn(value)
	custom_path = reg_cand if has_custom else None
	return (value, custom_path, _file_stat_key(custom_path))
# @used-by :func:`dfh_cached_addon_roots()`
# @used-by :func:`dfh_cached_browser_perimeter()`
def _put_derived(dkey: tuple, value: Any) -> Any:
	if 64 < len(_DERIVED_CACHE):
		_DERIVED_CACHE.clear()
	_DERIVED_CACHE[dkey] = value
	return value
# @used-by :func:`dfh_cached_addon_roots()`
# @used-by :func:`dfh_cached_browser_perimeter()`
def _safe_default_readonly(runtime_mod) -> tuple[tuple | None, dict]:
	try:
		r = _load_default_readonly(runtime_mod)
	except Exception:
		r = (None, {})
	return r
# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_touches_antigravity_addons()`
# @used-by :func:`agent_tools.runtime.sanctioned_addon_code_roots()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
# @used-by :mod:`agent_tools.runtime_cache`
def dfh_cached_addon_roots(config, runtime_mod, expand_fn) -> list[Path]:
	if None is not config:
		r = list(_compute_addon_roots(config, expand_fn))
	else:
		entry_key, cfg = _safe_default_readonly(runtime_mod)
		if None is entry_key:
			r = list(_compute_addon_roots(cfg, expand_fn))
		else:
			dkey = ('addon_roots', entry_key)
			cached = _DERIVED_CACHE.get(dkey)
			if None is cached:
				cached = _put_derived(dkey, _compute_addon_roots(cfg, expand_fn))
			r = list(cached)
	return r
# @used-by :func:`Df.Harness.lib.shell.dfh_protected_browser_perimeter()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
# @used-by :mod:`agent_tools.runtime_cache`
def dfh_cached_browser_perimeter(config, runtime_mod) -> dict:
	if None is not config:
		r = _compute_browser_perimeter(config)
	else:
		entry_key, cfg = _safe_default_readonly(runtime_mod)
		if None is entry_key:
			r = _compute_browser_perimeter(cfg)
		else:
			dkey = ('browser_perimeter', entry_key)
			cached = _DERIVED_CACHE.get(dkey)
			if None is cached:
				cached = _put_derived(dkey, _compute_browser_perimeter(cfg))
			r = {'active_port_files': list(cached['active_port_files']), 'ports': list(cached['ports']), 'profile_dirs': list(cached['profile_dirs'])}
	return r
# @used-by :func:`Df.Harness.lib.path_state.dfh_clear_path_cache()`
# @used-by :mod:`agent_tools.runtime_cache`
def dfh_clear_runtime_cache() -> None:
	_SETTINGS_CACHE.clear()
	_DERIVED_CACHE.clear()
	try:
		from agent_tools.evidence_loader import clear_observation_cache
		clear_observation_cache()
	except Exception:
		pass
# @used-by :meth:`Df.Harness.Runtime.SettingsLoader.SettingsLoader.run()`
# @used-by :mod:`agent_tools.runtime_cache`
def dfh_load_cached_settings(runtime_file: Path, validate_fn) -> dict:
	_, value = dfh_load_cached_settings_readonly(runtime_file, validate_fn)
	return _copy_json(value)
# @used-by :func:`_load_default_readonly()`
# @used-by :func:`dfh_load_cached_settings()`
# @used-by :mod:`agent_tools.runtime_cache`
def dfh_load_cached_settings_readonly(runtime_file: Path, validate_fn) -> tuple[tuple | None, dict]:
	rt_stat = _file_stat_key(runtime_file)
	if None is rt_stat:
		value, _, _ = _load_uncached_settings(runtime_file, validate_fn)
		r = (None, value)
	else:
		key = (rt_stat, _file_stat_key(runtime_file.parent / 'paths.json'), _env_digest())
		hit = _SETTINGS_CACHE.get(key)
		if None is not hit and (None is hit[1] or _file_stat_key(hit[1]) == hit[2]):
			r = (key, hit[0])
		else:
			value, custom_path, custom_stat = _load_uncached_settings(runtime_file, validate_fn)
			if 32 < len(_SETTINGS_CACHE):
				_SETTINGS_CACHE.clear()
			_SETTINGS_CACHE[key] = (value, custom_path, custom_stat)
			r = (key, value)
	return r
# @used-by :func:`Df.Harness.lib.trace_effects._record_shell_effects()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
# @used-by :mod:`agent_tools.runtime_cache`
def dfh_run_shell_violation_scan(fn, *args, **kwargs) -> None:
	if not _SKIP_SHELL_VIOLATIONS.get():
		fn(*args, **kwargs)
# @used-by :func:`Df.Harness.lib.completion_recovery._scan_readonly_turn()`
# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_runtime_cache_context_and_resolve()`
# @used-by :mod:`agent_tools.runtime_cache`
@contextmanager
def dfh_skip_shell_violations():
	token = _SKIP_SHELL_VIOLATIONS.set(True)
	try:
		yield
	finally:
		_SKIP_SHELL_VIOLATIONS.reset(token)
