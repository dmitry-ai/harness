# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.ag_inputs import dfh_antigravity_paths
from Df.Harness.lib.path_resolve import dfh_same_project_root
from Df.Harness.lib.runtime_instances import dfh_platform_instances, dfh_platform_key_for_adapter
from Df.Harness.lib.trace_common import dfh_extract_resource_uri, dfh_local_uri_to_path, dfh_open_readonly_sqlite
import ctypes
import json
import os
import re
import sqlite3
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_PBTXT_TITLE_RE = re.compile('(?:^|\\s)title\\s*:\\s*"((?:\\\\.|[^"\\\\])*)"')
# @used-by :func:`dfh_is_live_language_server_pid()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_platform_turn_scanner_and_ag_tail()`
def _check_win32_ls_pid(pid: int) -> bool:
	r = False
	try:
		kernel32 = ctypes.windll.kernel32
		handle = kernel32.OpenProcess(0x1000, False, int(pid))
		if handle:
			try:
				code = ctypes.c_ulong(0)
				if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) and 259 == code.value:
					buf = ctypes.create_unicode_buffer(1024)
					size = ctypes.c_ulong(len(buf))
					r = 'language_server.exe' == Path(buf.value).name.lower() if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)) else True
			finally:
				kernel32.CloseHandle(handle)
	except (AttributeError, OSError):
		r = False
	return r
# @used-by :func:`dfh_discover_live_daemon()`
# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_trace_effects_review_and_clarifications()`
def _parse_daemon_file(path: Path, is_live_pid_fn) -> dict | None:
	r: dict | None = None
	try:
		data = json.loads(path.read_text(encoding='utf-8'))
	except (OSError, UnicodeDecodeError, ValueError):
		data = None
	if isinstance(data, dict):
		pid, csrf_token = (data.get('pid'), data.get('csrfToken'))
		http_port, https_port = (data.get('httpPort'), data.get('httpsPort'))
		eff_http = http_port if int is type(http_port) and 0 < http_port < 65536 else None
		eff_https = https_port if int is type(https_port) and 0 < https_port < 65536 else None
		valid_meta = int is type(pid) and 1 <= pid and isinstance(csrf_token, str) and csrf_token.strip() and (None is not eff_http or None is not eff_https)
		if valid_meta and is_live_pid_fn(pid):
			r = {'pid': pid, 'http_port': eff_http, 'https_port': eff_https, 'csrf_token': csrf_token, 'ls_version': data.get('lsVersion'), 'discovery_file': str(path)}
	return r
# @used-by :func:`dfh_read_current_conversation_title()`
def _read_db_title(db_path: Path, conversation_id: str) -> str | None:
	r: str | None = None
	if db_path.is_file():
		try:
			with dfh_open_readonly_sqlite(db_path) as conn:
				if 'title' in {row[1] for row in conn.execute('PRAGMA table_info(conversation_summaries)')}:
					row = conn.execute('SELECT title FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
					if None is not row and isinstance(row[0], str):
						r = row[0]
		except (OSError, sqlite3.Error):
			r = None
	return r
# @used-by :func:`agent_tools.platforms.antigravity._default_folders_json()`
# @used-by :func:`dfh_resolve_folders_json()`
# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_ag_and_codex_registrars_verifiers_and_title_sync()`
def dfh_default_folders_json(*, settings_fn=None, instances_fn=None) -> Path:
	load_cfg = settings_fn if None is not settings_fn else (lambda: SettingsLoader().run())
	inst_fn = instances_fn if None is not instances_fn else dfh_platform_instances
	cfg_all = load_cfg()
	ag_key = dfh_platform_key_for_adapter('antigravity', cfg_all) or 'antigravity'
	ag = (cfg_all.get('platforms') or {}).get(ag_key) or {}
	r: Path | None = None
	if isinstance(ag.get('folders_json'), str) and ag['folders_json'].strip():
		r = Path(ag['folders_json'])
	else:
		for inst in inst_fn(ag_key, config=cfg_all, include_disabled=True).values():
			if inst['system_paths'].get('folders_json'):
				r = Path(inst['system_paths']['folders_json'])
				break
	if None is r:
		raise ValueError('Antigravity folders_json is not configured in runtime.json')
	return r
# @used-by :func:`agent_tools.platforms.antigravity.discover_live_daemon()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TitleSyncer.TitleSyncer.run()`
def dfh_discover_live_daemon(backend=None, *, instance=None, conversation_id=None, paths=None, settings_fn=None, is_live_pid_fn=None) -> dict | None:
	resolved = paths or dfh_antigravity_paths(backend=backend, instance=instance, conversation_id=conversation_id, settings_fn=settings_fn)
	daemon_dir = Path(resolved['daemon_dir']) if resolved.get('daemon_dir') else (Path(resolved['backend_dir']) / 'daemon')
	check_pid = is_live_pid_fn if None is not is_live_pid_fn else dfh_is_live_language_server_pid
	r: dict | None = None
	if daemon_dir.is_dir():
		candidates: list[tuple[int, Path]] = []
		for path in daemon_dir.glob('hub_*.json'):
			try:
				candidates.append((path.stat().st_mtime_ns, path))
			except OSError:
				continue
		candidates.sort(key=lambda item: (item[0], item[1].name), reverse=True)
		for _, path in candidates:
			parsed = _parse_daemon_file(path, check_pid)
			if None is not parsed:
				r = parsed
				break
	return r
# @used-by :func:`agent_tools.platforms.antigravity._ag_ops()`
# @used-by :func:`agent_tools.platforms.antigravity.discover_live_daemon()`
# @used-by :func:`dfh_discover_live_daemon()`
# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_trace_effects_review_and_clarifications()`
def dfh_is_live_language_server_pid(pid: int) -> bool:
	if int is not type(pid) or 1 > pid:
		r = False
	elif 'win32' == sys.platform:
		r = _check_win32_ls_pid(pid)
	else:
		try:
			os.kill(pid, 0)
			r = True
		except OSError:
			r = False
	return r
# @used-by :func:`dfh_read_current_conversation_title()`
# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_trace_effects_review_and_clarifications()`
def dfh_parse_pbtxt_title(text: str) -> str | None:
	m = _PBTXT_TITLE_RE.search(text or '')
	if not m:
		r: str | None = None
	else:
		raw = m.group(1)
		try:
			r = json.loads('"' + raw + '"')
		except ValueError:
			r = raw
	return r
# @used-by :meth:`Df.Harness.Meta.ProjectIdentity.ProjectIdentity.__lookup_name_by_project_id()`
# @used-by :meth:`Df.Harness.Meta.ProjectIdentity.ProjectIdentity.__lookup_name_from_project_dirs()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__find_preferred_id()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__upsert_project_file()`
def dfh_project_item_matches_root(item: dict, root: Path) -> tuple[bool, bool]:
	resources = (item.get('projectResources') or {}).get('resources') or []
	paths_in_item = [dfh_local_uri_to_path(dfh_extract_resource_uri(res)) for res in resources if dfh_extract_resource_uri(res)]
	if any((p == root for p in paths_in_item)):
		r = (True, False)
	elif 1 == len(paths_in_item) and None is not paths_in_item[0] and (not paths_in_item[0].exists()) and dfh_same_project_root(paths_in_item[0], root):
		r = (True, True)
	else:
		r = (False, False)
	return r
# @used-by :meth:`Df.Harness.Platform.Antigravity.TitleSyncer.TitleSyncer.run()`
def dfh_read_current_conversation_title(paths: dict, conversation_id: str) -> tuple[str | None, str | None]:
	db_title = _read_db_title(Path(paths['conversations_db']), conversation_id)
	ann_dir = Path(paths['annotations_dir']) if paths.get('annotations_dir') else (Path(paths['backend_dir']) / 'annotations')
	ann_file = ann_dir / f'{conversation_id}.pbtxt'
	ann_title: str | None = None
	if ann_file.is_file():
		try:
			ann_title = dfh_parse_pbtxt_title(ann_file.read_text(encoding='utf-8', errors='replace'))
		except OSError:
			ann_title = None
	return (db_title, ann_title)
# @used-by :func:`agent_tools.platforms.antigravity._resolve_folders_json()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__resolve_folders()`
def dfh_resolve_folders_json(folders_json_path=None, sp=None, *, module_folders=None, initial_folders=None, settings_fn=None, instances_fn=None) -> Path:
	if None is not folders_json_path:
		r = Path(folders_json_path)
	elif sp and sp.get('folders_json'):
		r = Path(sp['folders_json'])
	elif module_folders != initial_folders and None is not module_folders:
		r = Path(module_folders)
	else:
		try:
			r = dfh_default_folders_json(settings_fn=settings_fn, instances_fn=instances_fn)
		except (OSError, ValueError, KeyError, TypeError):
			if None is module_folders:
				raise
			r = Path(module_folders)
	return r
