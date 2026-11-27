# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.runtime_instances import dfh_extract_platform_instances, dfh_platform_adapter_name, dfh_resolve_platform_cfg
from Df.Harness.lib.runtime_validate import dfh_resolve_glob_paths
import re
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_antigravity_backend_has_conversation()`
def _ag_has_local_conv_files(brain_dir: Path | None, conv_dir: Path | None, conversation_id: str) -> bool:
	in_brain = bool(brain_dir and (brain_dir / conversation_id).is_dir())
	in_conv = bool(conv_dir and ((conv_dir / f'{conversation_id}.pb').is_file() or (conv_dir / f'{conversation_id}.db').is_file()))
	return in_brain or in_conv
# @used-by :func:`_find_ag_conversation()`
def _ag_trace_file(brain_root: Path | None, conversation_id: str) -> Path | None:
	r: Path | None = None
	if brain_root:
		logs_dir = brain_root / conversation_id / '.system_generated/logs'
		full_t, comp_t = (logs_dir / 'transcript_full.jsonl', logs_dir / 'transcript.jsonl')
		r = full_t if full_t.is_file() else (comp_t if comp_t.is_file() else None)
	return r
# @used-by :func:`dfh_codex_home_conversation_trace()`
def _codex_db_files(home: Path | None, sp: dict) -> list[Path]:
	glob_raw = sp.get('state_db_glob')
	if glob_raw:
		r = [p for p in dfh_resolve_glob_paths(glob_raw, home) if p.is_file()]
	else:
		r = [p for p in sorted(home.glob('state_*.sqlite')) if p.is_file()] if home else []
	return r
# @used-by :func:`dfh_codex_home_conversation_trace()`
def _codex_session_trace(home: Path | None, sp: dict, conversation_id: str) -> str | None:
	sessions = Path(sp['sessions_dir']) if sp.get('sessions_dir') else (home / 'sessions' if home else None)
	matches = sorted(sessions.rglob(f'*{conversation_id}*.jsonl')) if sessions and sessions.is_dir() else []
	return str(matches[0]) if matches else None
# @used-by :func:`dfh_find_conversation_instance()`
def _find_ag_conversation(plat_id: str, iid: str, item: dict, conversation_id: str) -> dict | None:
	sp = item['system_paths']
	backend_str = sp.get('backend_dir')
	has_loc = bool(backend_str or sp.get('brain_dir') or sp.get('conversations_dir') or sp.get('conversations_db'))
	r: dict | None = None
	if has_loc and dfh_antigravity_backend_has_conversation(backend_str, conversation_id, system_paths=sp):
		backend = Path(backend_str) if backend_str else None
		brain_root = Path(sp['brain_dir']) if sp.get('brain_dir') else (backend / 'brain' if backend else None)
		trace = _ag_trace_file(brain_root, conversation_id)
		r = {'backend_dir': str(backend) if backend else None, 'enabled': item['enabled'], 'id': iid, 'platform': plat_id, 'system_paths': sp, 'trace_file': str(trace) if trace else None}
	return r
# @used-by :func:`dfh_find_conversation_instance()`
def _find_codex_conversation(plat_id: str, iid: str, item: dict, conversation_id: str) -> dict | None:
	sp = item['system_paths']
	home_str = sp.get('home')
	r: dict | None = None
	if home_str or sp.get('state_db_glob') or sp.get('sessions_dir'):
		trace = dfh_codex_home_conversation_trace(home_str, conversation_id, system_paths=sp)
		if trace:
			r = {'backend_dir': str(Path(home_str)) if home_str else None, 'enabled': item['enabled'], 'id': iid, 'platform': plat_id, 'system_paths': sp, 'trace_file': trace}
	return r
# @used-by :func:`dfh_antigravity_backend_has_conversation()`
# @used-by :func:`dfh_codex_home_conversation_trace()`
def _query_sqlite_first(db_file: Path, sql: str, params: tuple[Any, ...]) -> tuple | None:
	r: tuple | None = None
	try:
		conn = sqlite3.connect(db_file.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
		try:
			r = conn.execute(sql, params).fetchone()
		finally:
			conn.close()
	except sqlite3.Error:
		r = None
	return r
# @used-by :func:`dfh_antigravity_backend_has_conversation()`
def _resolve_ag_subpath(sp: dict, key: str, backend: Path | None, rel: str) -> Path | None:
	if sp.get(key):
		r: Path | None = Path(sp[key])
	else:
		r = backend / rel if backend else None
	return r
# @used-by :func:`Df.Harness.lib.runtime_resolve.dfh_resolve_antigravity_paths()`
# @used-by :func:`Df.Harness.lib.runtime_resolve.dfh_resolve_codex_home()`
# @used-by :func:`Df.Harness.lib.runtime_resolve.dfh_resolve_codex_paths()`
# @used-by :func:`dfh_find_conversation_instance()`
def dfh_safe_load_cfg(config: dict | None, settings_fn: Any, *, reraise: bool=False) -> dict | None:
	r = config
	if None is r:
		try:
			if None is not settings_fn:
				r = settings_fn()
			else:
				from Df.Harness.Runtime.SettingsLoader import SettingsLoader
				r = SettingsLoader().run()
		except (OSError, ValueError):
			if reraise:
				raise
			r = None
	return r
# @used-by :func:`Df.Harness.lib.runtime_resolve._disambiguate_ag_matches()`
# @used-by :func:`_find_ag_conversation()`
def dfh_antigravity_backend_has_conversation(backend_dir: Any, conversation_id: str, *, system_paths: dict | None=None) -> bool:
	r = False
	if re.fullmatch('[a-f0-9-]{36}', str(conversation_id or '')):
		backend = Path(backend_dir) if backend_dir else None
		sp = system_paths or {}
		brain_dir = _resolve_ag_subpath(sp, 'brain_dir', backend, 'brain')
		conv_dir = _resolve_ag_subpath(sp, 'conversations_dir', backend, 'conversations')
		if _ag_has_local_conv_files(brain_dir, conv_dir, conversation_id):
			r = True
		else:
			db_path = _resolve_ag_subpath(sp, 'conversations_db', backend, 'conversation_summaries.db')
			r = bool(db_path and db_path.is_file() and _query_sqlite_first(db_path, 'SELECT 1 FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)))
	return r
# @used-by :func:`Df.Harness.lib.runtime_resolve._codex_match_by_home_dir()`
# @used-by :func:`_find_codex_conversation()`
# @used-by :func:`agent_tools.meta.builders._collect_codex_issue_ctx()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_default_system_paths_overrides_and_nested_codex_globs()`
def dfh_codex_home_conversation_trace(home_dir: Any, conversation_id: str, *, system_paths: dict | None=None) -> str | None:
	r: str | None = None
	if re.fullmatch('[a-f0-9-]{36}', str(conversation_id or '')):
		home = Path(home_dir) if home_dir else None
		sp = system_paths or {}
		for db_file in _codex_db_files(home, sp):
			row = _query_sqlite_first(db_file, 'SELECT rollout_path FROM threads WHERE id=?', (conversation_id,))
			if row and row[0]:
				r = str(Path(row[0]))
				break
		if None is r:
			r = _codex_session_trace(home, sp, conversation_id)
	return r
# @used-by :func:`Df.Harness.lib.runtime_resolve._codex_entry_from_auto()`
# @used-by :func:`Df.Harness.lib.runtime_resolve._match_ag_conversation()`
# @used-by :func:`Df.Harness.lib.runtime_resolve._resolve_codex_home_by_conv_or_profile()`
# @used-by :func:`agent_tools.runtime.find_conversation_instance()`
def dfh_find_conversation_instance(conversation_id: str, *, platform: str | None=None, config: dict | None=None, include_disabled: bool=True, settings_fn: Any=None) -> list[dict]:
	cfg_all = dfh_safe_load_cfg(config, settings_fn, reraise=True) or {}
	if platform:
		resolved_id, resolved_cfg = dfh_resolve_platform_cfg(platform, config=cfg_all, settings_fn=settings_fn)
		if None is resolved_cfg:
			raise ValueError(f'Unknown Upwork platform: {platform}')
		targets = [resolved_id]
	else:
		targets = list(cfg_all['platforms'])
	found: list[dict] = []
	for plat_id in targets:
		plat_cfg = cfg_all['platforms'][plat_id]
		kind = dfh_platform_adapter_name(plat_id, plat_cfg)
		for iid, item in dfh_extract_platform_instances(plat_cfg, platform=plat_id, include_disabled=include_disabled).items():
			hit = _find_ag_conversation(plat_id, iid, item, conversation_id) if 'antigravity' == kind else (_find_codex_conversation(plat_id, iid, item, conversation_id) if 'codex' == kind else None)
			if None is not hit:
				found.append(hit)
	return found
