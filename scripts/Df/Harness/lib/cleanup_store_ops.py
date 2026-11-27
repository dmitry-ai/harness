# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from Df.Harness.Cleanup.LifecycleEvaluator import LifecycleEvaluator
from Df.Harness.lib.cleanup_lifecycle_ops import dfh_count_project_conversations, dfh_load_codex_history_rows
from Df.Harness.lib.path_resolve import dfh_store_path, dfh_var_value
import base64
import json
import re
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
ACTIVE_CODEX_GLOBS: ContextVar = ContextVar('upwork_cleanup_codex_globs', default=None)
ACTIVE_READONLY_HISTORY: ContextVar = ContextVar('upwork_cleanup_readonly_history', default=None)
STATUS_NAMES = ('recent', 'preserved', 'eligible', 'removed', 'pending', 'blocked', 'already-absent')
# @used-by :func:`dfh_legacy_initialization()`
def _check_legacy_manifests(agents: Path, manifests: list[Path]) -> bool:
	primary = Path(dfh_var_value('HARNESS_CODE')).resolve()
	legacy_primary = dfh_store_path('legacy_primary')
	r = True
	for kind, manifest in zip(('rules', 'skills', 'agents'), manifests):
		allowed = {(primary / kind).resolve(), (legacy_primary / kind).resolve()}
		if not _manifest_points_to_harness(agents, manifest, allowed):
			r = False
			break
	return r
# @used-by :func:`dfh_candidates()`
def _evaluate_candidate(root: Path, daily: Path, config: dict, now: datetime) -> dict | None:
	marker = root / '\ua616/project.json'
	if dfh_linked(marker) or (not root.resolve().is_relative_to(daily)):
		raise ValueError('Linked or escaped archive entry preserved')
	state = dfh_read_store_json(marker) if marker.exists() else dfh_legacy_initialization(root)
	r: dict | None = None
	if None is not state and True is state.get('initialized') and re.fullmatch('~\\d+', state.get('job_id', '')):
		created, _ = dfh_base_age(root, state, config)
		effective, basis = dfh_age(root, state, config)
		r = {'root': str(root.resolve()), 'job_id': state['job_id'], 'initialization_basis': 'project.json' if marker.exists() else 'legacy-manifests-rule-and-kb', 'created_at': created.isoformat(), 'effective_activity_at': effective.isoformat(), 'age_basis': basis, 'old_enough': now - effective > timedelta(days=3)}
	return r
# @used-by :func:`dfh_legacy_initialization()`
def _extract_legacy_job_id(rule: Path, kb: Path) -> str:
	if dfh_linked(rule) or dfh_linked(kb):
		raise ValueError('Linked legacy initialization evidence preserved')
	pattern = 'https?://(?:www\\.)?upwork\\.com/jobs/[^\\s`"<>]*?(~[A-Za-z0-9]+)'
	ids = set(re.findall(pattern, rule.read_text(encoding='utf-8-sig')))
	current = re.search('^#\\s*2\\.\\s*(?:Current Client Project|\\u0422\\u0435\\u043a\\u0443\\u0449\\u0438\\u0439 \\u043f\\u0440\\u043e\\u0435\\u043a\\u0442 \\u043a\\u043b\\u0438\\u0435\\u043d\\u0442\\u0430)[^\\n]*\\n(.*?)(?=^#\\s|\\Z)', kb.read_text(encoding='utf-8-sig'), re.M | re.S)
	current_ids = re.findall(pattern, current.group(1)) if current else []
	if 1 != len(ids) or (not current_ids) or current_ids[0] not in ids:
		raise ValueError('Legacy project rule and current-job KB do not establish one job ID')
	if not re.fullmatch('~\\d+', current_ids[0]):
		raise ValueError('Unsupported historical job ID preserved without cleanup')
	return current_ids[0]
# @used-by :func:`_check_legacy_manifests()`
def _manifest_points_to_harness(agents: Path, manifest: Path, allowed: set[Path]) -> bool:
	entries = dfh_read_store_json(manifest).get('entries')
	if not isinstance(entries, list):
		raise ValueError('Legacy discovery manifest requires entries[]')
	paths = [Path(e['path']) for e in entries if isinstance(e, dict) and isinstance(e.get('path'), str)]
	return any(((p if p.is_absolute() else agents / p).resolve() in allowed for p in paths))
# @used-by :func:`dfh_antigravity_projects()`
def _match_ag_project_file(path: Path, target_key: str) -> dict | None:
	from Df.Harness.lib.trace_common import dfh_extract_resource_uri
	value = dfh_read_store_json(path)
	resources = (value.get('projectResources') or {}).get('resources') or []
	roots = [dfh_path_key(dfh_extract_resource_uri(res)) for res in resources if dfh_extract_resource_uri(res)]
	r: dict | None = None
	if target_key in roots:
		if roots != [target_key]:
			raise ValueError('Antigravity multi-root project preserved')
		if not value.get('id') or path.stem != value['id']:
			raise ValueError('Antigravity project identity is ambiguous')
		r = {'id': value['id'], 'file': str(path), 'sha': path.read_bytes()}
	return r
# @used-by :func:`dfh_antigravity_projects()`
def _parse_pending_ag_entry(directory: Path, target_key: str, saved: dict, found: list[dict]) -> dict | None:
	from Df.Harness.lib.trace_common import dfh_extract_resource_uri
	ident = saved['id']
	if not isinstance(ident, str) or (not re.fullmatch('[a-f0-9-]{36}', ident)):
		raise ValueError('Invalid pending Antigravity cleanup identity')
	path = directory / (ident + '.json')
	r: dict | None = None
	if not any((p['id'] == ident for p in found)):
		if path.exists():
			raise ValueError('Pending Antigravity project changed its workspace')
		payload = base64.b64decode(saved['payload'], validate=True)
		restored = json.loads(payload.decode('utf-8-sig'))
		roots = [dfh_path_key(dfh_extract_resource_uri(res)) for res in restored['projectResources']['resources'] if dfh_extract_resource_uri(res)]
		if restored.get('id') != ident or roots != [target_key]:
			raise ValueError('Pending Antigravity payload changed identity')
		r = {'id': ident, 'file': str(path), 'sha': None, 'restore': payload}
	return r
# @used-by :func:`dfh_load_conversation_index()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_cleanup_resolvers()`
def _read_ag_entry(b_info) -> list:
	if isinstance(b_info, tuple):
		r = _read_ag_rows(b_info[0], allow_missing=b_info[1], db_path=b_info[2] if 3 <= len(b_info) else None)
	else:
		r = _read_ag_rows(b_info, allow_missing=False)
	return r
# @used-by :func:`_read_ag_entry()`
# @used-by :func:`dfh_load_conversation_index()`
def _read_ag_rows(backend_dir, *, allow_missing=False, db_path=None) -> list:
	from Df.Harness.lib.trace_common import dfh_open_readonly_sqlite
	db = Path(db_path) if None is not db_path else Path(backend_dir) / 'conversation_summaries.db'
	ag_rows = []
	if not (allow_missing and (not db.exists()) and (not db.is_symlink())):
		with dfh_open_readonly_sqlite(db, guard=dfh_guard_history_db, query_only=True, row_factory=sqlite3.Row, timeout=5) as conn:
			for row in conn.execute('SELECT project_id, workspace_uris FROM conversation_summaries'):
				uris = json.loads(row['workspace_uris']) if row['workspace_uris'] else []
				if not isinstance(uris, list):
					raise ValueError('Unknown Antigravity workspace_uris format')
				ag_rows.append((row['project_id'], uris))
	return ag_rows
# @used-by :func:`dfh_catalog_projects()`
def _validate_catalog_header(catalog, homes: dict) -> None:
	if not isinstance(catalog, dict) or (not isinstance(catalog.get('projects'), dict)) or (not isinstance(catalog.get('profiles'), dict)):
		raise ValueError('Shared-Projects catalogue unavailable')
	if not set(homes).issubset(set(catalog['profiles'])):
		raise ValueError('Configured Codex profiles differ from Shared-Projects')
# @used-by :func:`dfh_catalog_projects()`
def _validate_catalog_project(ident: str, project: dict, target_key: str, homes: dict, profiles: dict) -> dict | None:
	roots = [dfh_path_key(path) for path in project['rootPaths']]
	r: dict | None = None
	if target_key in roots:
		if roots != [target_key]:
			raise ValueError('Codex multi-root project preserved')
		bindings = {}
		for profile in homes:
			binding = profiles[profile]['bindings'].get(ident)
			if not binding or (not binding.get('desktopId')):
				raise ValueError('Codex profile binding is missing')
			bindings[profile] = binding['desktopId']
		r = {'id': ident, 'bindings': bindings, 'cleanup_hold': bool(project.get('cleanupHold'))}
	return r
# @used-by :func:`_evaluate_candidate()`
# @used-by :func:`agent_tools.cleanup._age()`
def dfh_age(root, state, config):
	created, basis = dfh_base_age(root, state, config)
	return LifecycleEvaluator(root, state, config, created, basis, dfh_path_key).run()
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops._restore_pending_files()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_remove_antigravity()`
# @used-by :func:`agent_tools.cleanup.antigravity_projects()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__collect_ag_projects()`
def dfh_antigravity_projects(directory: Path, root) -> list[dict]:
	target_key = dfh_path_key(root)
	r: list[dict] = []
	for path in sorted(directory.glob('*.json')):
		matched = _match_ag_project_file(path, target_key)
		if None is not matched:
			r.append(matched)
	pending_file = directory / '\ua616/data/cleanup-pending.json'
	pending = dfh_read_store_json(pending_file) if pending_file.exists() else {}
	for saved in pending.get(target_key, {}).get('projects', []):
		parsed = _parse_pending_ag_entry(directory, target_key, saved, r)
		if None is not parsed:
			r.append(parsed)
	return r
# @used-by :func:`_evaluate_candidate()`
# @used-by :func:`agent_tools.cleanup._base_age()`
# @used-by :func:`dfh_age()`
def dfh_base_age(root, state, config):
	if state.get('created_at'):
		created = datetime.fromisoformat(state['created_at'].replace('Z', '+00:00'))
		if None is created.tzinfo:
			raise ValueError('created_at must include its timezone')
		r = (created, 'project.created_at')
	else:
		day = datetime.fromisoformat(state['request_date']).replace(tzinfo=ZoneInfo(config['timezone']))
		birth = getattr(root.stat(), 'st_birthtime', None)
		r = (max(day, datetime.fromtimestamp(birth, timezone.utc)), 'legacy-directory-birthtime') if None is not birth else (day + timedelta(days=1), 'legacy-request-day-upper-bound')
	return r
# @used-by :func:`agent_tools.cleanup._belongs_cached()`
# @used-by :func:`dfh_count_indexed_conversations()`
def dfh_belongs_cached(raw_path, wanted, prefix, key_cache):
	key = key_cache.get(raw_path) if isinstance(raw_path, str) else None
	if None is key:
		key = dfh_path_key(raw_path)
		if isinstance(raw_path, str):
			key_cache[raw_path] = key
	return key == wanted or key.startswith(prefix)
# @used-by :func:`agent_tools.cleanup.candidates()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.run()`
def dfh_candidates(daily: Path, config: dict, now: datetime) -> tuple[list[dict], list[dict]]:
	values, issues = ([], [])
	for root in sorted(daily.glob('????/??/??/*')):
		if not root.is_dir():
			continue
		try:
			cand = _evaluate_candidate(root, daily, config, now)
			if None is not cand:
				values.append(cand)
		except (OSError, ValueError, TypeError, KeyError) as exc:
			issues.append({'root': str(root), 'error': str(exc)})
	return (values, issues)
# @used-by :func:`agent_tools.cleanup.catalog_projects()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__evaluate_candidate_entry()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__recover_preserved()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__try_preserve_unresolved()`
def dfh_catalog_projects(catalog, root, homes: dict) -> list[dict]:
	r: list[dict] = []
	if homes:
		_validate_catalog_header(catalog, homes)
		target_key = dfh_path_key(root)
		for ident, project in catalog['projects'].items():
			item = _validate_catalog_project(ident, project, target_key, homes, catalog['profiles'])
			if None is not item:
				r.append(item)
		if 1 < len(r):
			raise ValueError('Ambiguous Shared-Projects root')
	return r
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.run()`
@contextmanager
def dfh_codex_glob_scope(globs, readonly_history=None):
	token = ACTIVE_CODEX_GLOBS.set(globs or {})
	ro_token = ACTIVE_READONLY_HISTORY.set(readonly_history or {})
	try:
		yield
	finally:
		ACTIVE_READONLY_HISTORY.reset(ro_token)
		ACTIVE_CODEX_GLOBS.reset(token)
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__discover_conversations()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__handle_eligible()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__record_candidate_error()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_cleanup_resolvers()`
def dfh_conversations(root, ag_projects, backend, homes, catalog):
	return dfh_count_indexed_conversations(root, ag_projects, homes, catalog, dfh_load_conversation_index(backend, homes))
# @used-by :func:`agent_tools.cleanup._count_indexed_conversations()`
# @used-by :func:`dfh_conversations()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__discover_conversations()`
def dfh_count_indexed_conversations(root, ag_projects, homes, catalog, index):
	return dfh_count_project_conversations(root, ag_projects, homes, catalog, index, dfh_path_key, dfh_belongs_cached)
# @used-by :func:`_read_ag_rows()`
# @used-by :func:`dfh_load_conversation_index()`
def dfh_guard_history_db(database: Path) -> None:
	if not database.is_file() or dfh_linked(database):
		raise ValueError(f'Native history unavailable: {database}')
# @used-by :func:`_evaluate_candidate()`
# @used-by :func:`agent_tools.cleanup.legacy_initialization()`
def dfh_legacy_initialization(root: Path) -> dict | None:
	agents = root / '.agents'
	rule = agents / 'rules/90-project.md'
	kb = next((p for p in (root / '\U0001f56e/Project.md', root / 'KB/Project.md') if p.is_file()), root / 'KB/Project.md')
	manifests = [agents / (kind + '.json') for kind in ('rules', 'skills', 'agents')]
	r: dict | None = None
	if all((p.is_file() for p in [rule, kb, *manifests])) and _check_legacy_manifests(agents, manifests):
		job_id = _extract_legacy_job_id(rule, kb)
		day = datetime(int(root.parents[2].name), int(root.parents[1].name), int(root.parent.name)).date()
		r = {'job_id': job_id, 'initialized': True, 'request_date': day.isoformat()}
	return r
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops._restore_pending_files()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops._unlink_ag_projects()`
# @used-by :func:`_evaluate_candidate()`
# @used-by :func:`_extract_legacy_job_id()`
# @used-by :func:`agent_tools.cleanup.linked()`
# @used-by :func:`dfh_guard_history_db()`
# @used-by :func:`dfh_read_store_json()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__init__()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__try_preserve_unresolved()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.run()`
# @used-by :meth:`Df.Harness.Cleanup.StoreResolver.StoreResolver.__resolve_ag_single()`
# @used-by :meth:`Df.Harness.Cleanup.StoreResolver.StoreResolver.__resolve_folder_file()`
# @used-by :meth:`Df.Harness.Cleanup.StoreResolver.StoreResolver.__validate_ag_instance()`
def dfh_linked(path: Path) -> bool:
	return any((p.is_symlink() or p.is_junction() for p in (path, *path.parents)))
# @used-by :func:`agent_tools.cleanup._load_conversation_index()`
# @used-by :func:`dfh_conversations()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__discover_conversations()`
def dfh_load_conversation_index(backend, homes):
	ro = ACTIVE_READONLY_HISTORY.get() or {}
	if isinstance(backend, dict):
		merged_ag = {**backend, **(ro.get('ag_backend') or {})}
		ag_rows = {iid: _read_ag_entry(b_info) for iid, b_info in merged_ag.items()}
	else:
		ag_rows = _read_ag_rows(backend, allow_missing=False)
	codex_globs = {**(ACTIVE_CODEX_GLOBS.get() or {}), **(ro.get('codex_globs') or {})}
	merged_homes = {**homes, **(ro.get('codex_homes') or {})}
	codex_rows = dfh_load_codex_history_rows(merged_homes, codex_globs, dfh_guard_history_db)
	return (ag_rows, codex_rows, {})
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops._save_pending_snapshot()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_finish_pending()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_restore_antigravity()`
# @used-by :func:`_match_ag_project_file()`
# @used-by :func:`_parse_pending_ag_entry()`
# @used-by :func:`_validate_catalog_project()`
# @used-by :func:`agent_tools.cleanup.path_key()`
# @used-by :func:`dfh_age()`
# @used-by :func:`dfh_antigravity_projects()`
# @used-by :func:`dfh_belongs_cached()`
# @used-by :func:`dfh_catalog_projects()`
# @used-by :func:`dfh_count_indexed_conversations()`
def dfh_path_key(value) -> str:
	from Df.Harness.lib.trace_common import dfh_local_uri_to_path
	return str(dfh_local_uri_to_path(value, require_absolute=True)).replace('\\', '/').rstrip('/').casefold()
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops._restore_pending_folders()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops._save_pending_snapshot()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_finish_pending()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_remove_antigravity()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_restore_antigravity()`
# @used-by :func:`_evaluate_candidate()`
# @used-by :func:`_manifest_points_to_harness()`
# @used-by :func:`_match_ag_project_file()`
# @used-by :func:`dfh_antigravity_projects()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__prepare_stores()`
def dfh_read_store_json(path: Path) -> dict:
	if dfh_linked(path):
		raise ValueError(f'Linked store preserved: {path}')
	r = json.loads(path.read_text(encoding='utf-8-sig'))
	if not isinstance(r, dict):
		raise ValueError(f'Expected a JSON object: {path}')
	return r
